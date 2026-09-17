"""Workforce message protocol (v1): typed, bounded, artifact-referencing (Phase 5.0).

Design: `ux-audit/workforce-os/07_INTER_AGENT_PROTOCOL.md`. Messages are action-requiring
deltas only — no STATUS chatter, no acknowledgements, no findings (those live in the
findings store; a message only points at them). They carry the same prohibitions as
team_events: no hidden reasoning, no prompts, no secrets. The Commander sends as
`from: cmd` (it is Kel itself, never an assignment); all other senders and recipients are
assignment or pod ids.

Dispatch-time enforcement (pair/task message caps, receiver-state checks, duplicate
fingerprints) arrives with the pod increments; this module owns the schema contract.
"""
import contextlib
import json
import time
import uuid

from .core import PolicyError, digest, uid
from .workforce import assert_safe, require_number, require_text

SCHEMA_VERSION = 1
MESSAGE_TYPES = ('REQUEST', 'FINDING', 'CHALLENGE', 'HANDOFF', 'BLOCKER',
                 'DECISION_PROPOSAL', 'EVIDENCE', 'STAFFING_REQUEST', 'REPLAN_REQUEST')
SUMMARY_MAX = 400
DETAILS_MAX = 2000
PAIR_MESSAGE_BUDGET = 6   # per task pair; beyond that the conversation becomes a ledger escalation
TASK_MESSAGE_BUDGET = 12  # per task overall; beyond that the task goes to mandatory Commander review
MESSAGE_FIELDS = ('id', 'schema_version', 'mission_id', 'task_id', 'from', 'to', 'type',
                  'summary', 'refs', 'required_action', 'deadline', 'budget_impact', 'details',
                  'supersedes', 'at')


# Real assignment ids are `uid()` values (the V1.4 convention); the design's `asn_`/`pod_`
# prefixes are accepted too, so both vocabularies validate.
def _identity(value, what):
    """A message party: `cmd`, a prefixed assignment/pod id, or a uid() id."""
    text = require_text(value, what)
    if text == 'cmd' or text.startswith(('asn_', 'pod_')):
        return text
    try:
        uuid.UUID(text)
    except (ValueError, AttributeError):
        raise PolicyError('%s is an assignment id, a pod id or cmd' % what)
    return text


def validate_message(message):
    """Refuse a malformed workforce message (doc 07 §2, schema v1)."""
    if not isinstance(message, dict):
        raise PolicyError('A workforce message is an object')
    unknown = sorted(set(message) - set(MESSAGE_FIELDS))
    if unknown:
        raise PolicyError('A workforce message has unknown fields: %s' % ', '.join(unknown))
    if message.get('schema_version') != SCHEMA_VERSION:
        raise PolicyError('Message schema_version must be %d' % SCHEMA_VERSION)
    require_text(message.get('id'), 'message id')
    require_text(message.get('mission_id'), 'mission_id')
    require_text(message.get('task_id'), 'task_id')
    _identity(message.get('from'), 'from')
    _identity(message.get('to'), 'to')
    if message.get('type') not in MESSAGE_TYPES:
        raise PolicyError('Message types are %s (STATUS is deliberately not a message type)'
                          % ', '.join(MESSAGE_TYPES))
    require_text(message.get('summary'), 'summary', max_len=SUMMARY_MAX)
    refs = message.get('refs')
    if not isinstance(refs, list) or not refs or any(not isinstance(item, str) or not item.strip()
                                                     for item in refs):
        raise PolicyError('Every message carries artifact/evidence references; '
                          'a message without refs is malformed')
    require_text(message.get('required_action'), 'required_action')
    if message.get('deadline') is not None:
        require_number(message['deadline'], 'deadline')
    impact = message.get('budget_impact')
    if message.get('type') == 'STAFFING_REQUEST':
        if not isinstance(impact, dict):
            raise PolicyError('A staffing request states its budget impact')
        for key in ('tokens', 'wallclock_s'):
            value = impact.get(key)
            if type(value) is not int or value < 0:
                raise PolicyError('budget_impact.%s is a non-negative integer' % key)
    elif impact is not None and not isinstance(impact, dict):
        raise PolicyError('budget_impact is an object when present')
    details = message.get('details')
    if details is not None:
        if not isinstance(details, str) or len(details) > DETAILS_MAX:
            raise PolicyError('Message details are capped at %d characters' % DETAILS_MAX)
    if message.get('supersedes') is not None:
        require_text(message['supersedes'], 'supersedes')
    if message.get('at') is not None:
        require_number(message['at'], 'at')
    assert_safe(message, path='message')
    return message


def message_fingerprint(message):
    """The dedup fingerprint (doc 07 §4): same refs + same required_action => duplicate."""
    return digest({'refs': list(message.get('refs') or []),
                   'required_action': message.get('required_action')})


def send_message(store, message, *, now=None):
    """Dispatch-time enforcement for the v1 protocol (doc 07 §3-4).

    Validates the schema, applies the anti-chatter budgets (per pair <= 6, per task <= 12),
    rejects duplicates by fingerprint (same refs + required_action), refuses receivers whose
    assignment state cannot change (v1: cancelled assignments), and appends the row.
    """
    message = dict(message)
    message.setdefault('id', 'msg_' + uid())
    validate_message(message)
    stamp = time.time() if now is None else now
    task_id = message['task_id']
    sender, recipient = message['from'], message['to']
    fingerprint = message_fingerprint(message)
    with contextlib.closing(store.connect()) as db:
        task_count = db.execute('SELECT count(*) FROM workforce_messages WHERE task_id=?',
                                (task_id,)).fetchone()[0]
        if task_count >= TASK_MESSAGE_BUDGET:
            raise PolicyError('Task message budget exhausted (%d); the task needs Commander '
                              'review before more messages' % TASK_MESSAGE_BUDGET)
        if 'cmd' not in (sender, recipient):
            # Worker-pair budget only; reaching cmd is the sanctioned escalation channel
            # (the task-wide cap below still bounds it).
            pair_count = db.execute(
                'SELECT count(*) FROM workforce_messages WHERE task_id=? AND ((sender=? AND '
                'recipient=?) OR (sender=? AND recipient=?))',
                (task_id, sender, recipient, recipient, sender)).fetchone()[0]
            if pair_count >= PAIR_MESSAGE_BUDGET:
                raise PolicyError('Pair message budget exhausted (%d); escalate with a BLOCKER '
                                  'or DECISION_PROPOSAL to cmd' % PAIR_MESSAGE_BUDGET)
        for row in db.execute('SELECT id, refs, required_action FROM workforce_messages'
                              ' WHERE task_id=?', (task_id,)):
            existing = {'refs': json.loads(row['refs']),
                        'required_action': row['required_action']}
            if digest(existing) == fingerprint:
                raise PolicyError('Duplicate message rejected (same refs and required_action '
                                  'as %s)' % row['id'])
        if recipient != 'cmd':
            state_row = db.execute('SELECT state FROM team_assignments WHERE assignment_id=?',
                                   (recipient,)).fetchone()
            if state_row is not None and state_row['state'] == 'CANCELLED':
                raise PolicyError('Receiver state cannot change (CANCELLED); message rejected')
        db.execute('INSERT INTO workforce_messages(id,schema_version,mission_id,task_id,sender,'
                   'recipient,type,summary,refs,required_action,deadline,budget_impact,details,'
                   'supersedes,at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (message['id'], message['schema_version'], message['mission_id'], task_id,
                    sender, recipient, message['type'], message['summary'],
                    json.dumps(list(message['refs'])), message['required_action'],
                    message.get('deadline'),
                    json.dumps(message.get('budget_impact'))
                    if message.get('budget_impact') is not None else None,
                    message.get('details'), message.get('supersedes'), stamp))
    record = dict(message)
    record['at'] = stamp
    record['fingerprint'] = fingerprint
    return record


def messages(store, *, task_id=None, mission_id=None):
    """Read-only message ledger (decoded refs/budget_impact)."""
    query = 'SELECT * FROM workforce_messages'
    clauses, args = [], []
    if task_id:
        clauses.append('task_id=?')
        args.append(task_id)
    if mission_id:
        clauses.append('mission_id=?')
        args.append(mission_id)
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY at'
    with contextlib.closing(store.connect()) as db:
        rows = [dict(row) for row in db.execute(query, tuple(args))]
    for row in rows:
        row['refs'] = json.loads(row['refs'])
        if row['budget_impact'] is not None:
            row['budget_impact'] = json.loads(row['budget_impact'])
    return rows
