"""Workforce message protocol (v1): typed, bounded, artifact-referencing (Phase 5.0).

Design: `ux-audit/workforce-os/07_INTER_AGENT_PROTOCOL.md`. Messages are action-requiring
deltas only — no STATUS chatter, no acknowledgements, no findings (those live in the
findings store; a message only points at them). They carry the same prohibitions as
team_events: no hidden reasoning, no prompts, no secrets.

Dispatch-time enforcement (pair/task message caps, receiver-state checks, duplicate
fingerprints) arrives with the pod increments; this module owns the schema contract.
"""
from .core import PolicyError
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
    sender = require_text(message.get('from'), 'from')
    if sender != 'cmd' and not sender.startswith(('asn_', 'pod_')):
        raise PolicyError('Message senders are assignments (asn_/pod_) or cmd')
    recipient = require_text(message.get('to'), 'to')
    if recipient != 'cmd' and not recipient.startswith(('asn_', 'pod_')):
        raise PolicyError('Message recipients are cmd, an assignment or a pod')
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
