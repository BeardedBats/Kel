"""Phase 5.6: the learning loop (shadow) — workforce-os docs 11 §1-6 and 15 §5.6.

The workforce compounds institutional knowledge without self-modification:

* Learnings are **memory records** with a workforce `source_type` (doc 11 §1-2): they are
  written through the existing V1.3 memory store, so provenance, the trust ladder, supersede
  chains, conflict handling, secret scanning and forget semantics apply unchanged. No second
  memory system, no new storage surface for learnings.
* History reuses the **team activity stream** (doc 11 §1): `learning.recorded`,
  `retro.drafted`, `staffing.proposed` and `proposal.queued` are append-only events on the
  ledger the team system already maintains.
* Performance stats and validation metrics are **derived views** (doc 11 §3, doc 13 §4),
  computed from findings, contracts, budgets and mission streams — never fabricated sampling.
* **Shadow first** (doc 11 §5): every automatic write path is gated by
  `workforce.learning.shadow` (default off); nothing here applies to live staffing, gating or
  ceremony. Explicit user corrections are user actions and are never gated — exactly like every
  other memory correction. Anything above the auto-approval confidence cap is stored capped and
  queued for promotion. Preferences are recorded only from explicit user confirmation;
  everything else stays advisory and inspectable.

Learnings carry confidence 1-10 (mirrored into the memory confidence column as 0..1).
Observed, inferred and cross-model learnings decay one point per 30 days without
re-observation (computed at read time; user-stated learnings never decay). A corrected
learning becomes user-stated — the user just restated it.
"""
import contextlib
import json
import re
import sqlite3
import time

from .assignment import flags_snapshot
from .core import PolicyError
from .memory import Memory
from .team import Team
from .workforce import assert_safe, require_integer, require_text

LEARNING_TYPES = ('pattern', 'pitfall', 'preference', 'architecture', 'tool')
LEARNING_SOURCES = ('observed', 'user-stated', 'inferred', 'cross-model')

# Learning type -> the memory type it is stored as (1:1 by design, so the memory store's
# (type, topic) uniqueness maps exactly to the learning (type, key) identity).
TYPE_TO_MEMORY = {'pattern': 'convention', 'pitfall': 'limitation', 'preference': 'preference',
                  'architecture': 'component', 'tool': 'workflow'}

# Learning source -> the workforce memory source_type (doc 11 §2: trust follows source;
# observed and cross-model outrank inference, and user-stated rides the existing
# user-confirmation trust level 2).
SOURCE_TO_SOURCE_TYPE = {'observed': 'workforce_observed', 'cross-model': 'workforce_cross_model',
                         'inferred': 'workforce_inferred', 'user-stated': 'user_confirmation'}
WORKFORCE_SOURCE_TYPES = ('workforce_observed', 'workforce_cross_model', 'workforce_inferred')

AUTO_CONFIDENCE_CAP = 5   # auto-approved confidence; anything above enters the promotion queue
DECAY_DAYS = 30           # observed/inferred learnings decay 1 point per 30 days (doc 11 §2)
KEY_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{1,159}$')
LEARNING_SCHEMA = 'learning.v1'
RETRO_SCHEMA = 'retro.v1'

# V2-10: nothing is *suggested* from fewer than this many independent observations. The threshold
# applies to suggestions (reviewable proposals), never to a single explicit observation.
SUGGEST_MIN_EVIDENCE = 3
SUGGEST_WINDOW_DAYS = 30

# V2-10: the authority fence (roadmap: never silently learn permission grants, spending authority,
# filesystem access or irreversible authority). A non-user source that asserts any of those is
# refused outright — not stored, not even proposed. The person's own statement is theirs to make.
AUTHORITY_RE = re.compile(
    r'\b(?:grant|give|allow|permit|authorize)\b[^.\n]{0,80}\b(?:kel|you|it|me|yourself)\b'
    r'|\b(?:kel|you)\s+(?:may|can|is allowed to|are allowed to|has permission to)\s+'
    r'(?:spend|pay|purchase|buy|delete|remove|install|publish|send|write|modify)\b'
    r'|\b(?:spend|spending|budget|payment|purchase)\b[^.\n]{0,60}'
    r'\b(?:authority|limit|without asking|automatically|up to)\b'
    r'|\b(?:filesystem|file system|disk|drive|folder|directory)\b[^.\n]{0,60}'
    r'\b(?:access|write access|read access|full access|permission)\b'
    r'|\b(?:irreversible|without (?:asking|confirmation|approval)|no (?:approval|confirmation) needed)\b',
    re.IGNORECASE)


def authority_refusal(insight):
    """None when the text is fine; a plain sentence when it tries to learn authority."""
    if AUTHORITY_RE.search(str(insight or '')):
        return ('Kel never records authority that way: permissions, spending, file access and '
                'irreversible actions are yours to decide, every time.')
    return None


def _off(reason='workforce.learning.shadow is off', snapshot=None):
    return {'applied': False, 'recorded': False, 'reason': reason,
            'flags': snapshot if snapshot is not None else flags_snapshot()}


def _shadow(snapshot):
    return bool((snapshot or {}).get('workforce.learning.shadow'))


def _slug(value):
    return re.sub(r'[^a-z0-9._-]+', '-', str(value).lower()).strip('-')[:120] or 'item'


def _decode(row, field):
    raw = row[field] if row is not None else None
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _rows(store, sql, args=()):
    """Read rows; only a missing optional table degrades to an empty read.

    A locked or failing database must surface as an error — a retro that silently reads as
    "nothing went wrong" because the connection failed is exactly the false-honesty this loop
    must not produce (audit 23, F23-4).
    """
    with contextlib.closing(store.connect()) as db:
        try:
            return [dict(row) for row in db.execute(sql, args).fetchall()]
        except sqlite3.OperationalError as exc:
            if 'no such table' in str(exc).lower():
                return []
            raise


# ---- learnings: memory records with a workforce source_type (doc 11 §1-2) -------------------

def record_learning(store, *, project_id, key, type, insight, confidence, source,
                    evidence=(), mission_id=None, task_id=None, confirmed_by=None,
                    flags=None):
    """Record one learning observation (append-only; the memory store resolves chains).

    Same (key, type): the memory ladder decides — stronger trust supersedes, equal trust takes
    the newest observation, and a conflict on an authoritative type is queued for the user.
    `source='user-stated'` requires `confirmed_by='user'`; preferences require it and nothing
    else (doc 11 §2). Non-user confidence above `AUTO_CONFIDENCE_CAP` is stored capped and the
    full request enters the promotion queue (doc 11 §4.3).
    """
    snapshot = flags_snapshot() if flags is None else dict(flags)
    if not _shadow(snapshot):
        return _off(snapshot=snapshot)
    if type not in LEARNING_TYPES:
        raise PolicyError('Learning types are %s' % ', '.join(LEARNING_TYPES))
    if source not in LEARNING_SOURCES:
        raise PolicyError('Learning sources are %s' % ', '.join(LEARNING_SOURCES))
    if not isinstance(key, str) or not KEY_RE.match(key):
        raise PolicyError('A learning key is a stable slug (lowercase, dots/dashes)')
    require_text(insight, 'insight')
    if len(insight) > 1000:
        raise PolicyError('An insight stays under 1000 characters')
    confidence = require_integer(confidence, 'confidence', lo=1, hi=10)
    if not isinstance(evidence, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip() or len(item) > 200 for item in evidence):
        raise PolicyError('Evidence is a list of short reference strings')
    if len(evidence) > 24:
        raise PolicyError('At most 24 evidence references per learning')
    assert_safe({'key': key, 'insight': insight, 'evidence': list(evidence)}, path='learning')
    refusal = authority_refusal(insight)
    if refusal and source != 'user-stated':
        raise PolicyError(refusal)
    if type == 'preference':
        if source != 'user-stated' or confirmed_by != 'user':
            raise PolicyError('Preferences are recorded only from explicit user confirmation '
                              '(doc 11 §2)')
    elif source == 'user-stated' and confirmed_by != 'user':
        raise PolicyError('A user-stated learning requires confirmed_by="user"')
    requested = confidence
    stored = confidence
    queued = False
    if source != 'user-stated' and confidence > AUTO_CONFIDENCE_CAP:
        stored = AUTO_CONFIDENCE_CAP
        queued = True
    value = {'schema': LEARNING_SCHEMA, 'key': key, 'type': type, 'insight': insight,
             'confidence': stored, 'requested_confidence': requested, 'source': source,
             'evidence': list(evidence), 'scope': 'project', 'mission_id': mission_id,
             'task_id': task_id}
    memory = Memory(store)
    memory_id = memory.record(project_id, TYPE_TO_MEMORY[type], key, value, insight,
                              source_type=SOURCE_TO_SOURCE_TYPE[source],
                              source_ref='workforce:%s' % (mission_id or project_id),
                              actor='user' if source == 'user-stated' else 'kel',
                              confidence=stored / 10.0,
                              user_confirmed=1 if source == 'user-stated' else 0)
    team = Team(store)
    event = team.record_mission_activity(
        'learning.recorded',
        detail={'key': key, 'type': type, 'source': source, 'confidence': stored,
                'cap_applied': queued, 'memory_id': memory_id},
        refs={'project_id': project_id, 'mission_id': mission_id})
    if queued:
        queue_promotion(store, project_id=project_id,
                        proposal_kind='learning.promotion', subject=key,
                        requested={'type': type, 'source': source, 'confidence': requested},
                        basis={'cap': AUTO_CONFIDENCE_CAP, 'memory_id': memory_id},
                        flags=snapshot)
    return {'recorded': True, 'memory_id': memory_id, 'key': key, 'type': type,
            'source': source, 'stored_confidence': stored, 'cap_applied': queued,
            'seq': event.get('seq')}


def learnings_view(store, *, project_id, include_stale=False, include_disabled=False, now=None):
    """The learnings view (doc 11 §2): latest non-superseded record per key, with decay.

    Decay is computed, never written: observed/inferred/cross-model learnings lose one point
    per 30 days since their last observation; user-stated learnings do not decay. Stale
    learnings leave default retrieval but stay inspectable via `include_stale=True`.
    """
    moment = time.time() if now is None else now
    rows = _rows(store, 'SELECT * FROM memories WHERE project_id=? ORDER BY updated ASC',
                 (project_id,))
    current = {}
    for row in rows:
        if row['source_type'] not in WORKFORCE_SOURCE_TYPES and row['source_type'] != 'user_confirmation':
            continue
        if row['status'] == 'superseded':
            continue
        try:
            value = json.loads(row['value'])
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict) or value.get('schema') != LEARNING_SCHEMA:
            continue
        # Identity is (learning type, key) — two live learnings may share a key across types
        # (their memory types differ by the 1:1 map), so never collapse by key alone
        # (audit 23, F23-5).
        current[(value.get('type') or 'unknown', value.get('key') or row['topic'])] = (row, value)
    items = []
    for _type, key in sorted(current):
        row, value = current[(_type, key)]
        confidence = int(value.get('confidence') or 1)
        source = value.get('source') or 'observed'
        if source == 'user-stated':
            effective = confidence
        else:
            # Decay runs from the record's OWN creation: a losing weaker write bumps the
            # winner's `updated` in the memory store, and that must never reset its decay
            # clock without a real re-observation (audit 23, F23-3).
            born = float(row['created'] or row['updated'] or moment)
            months = int(max(0.0, moment - born) // (DECAY_DAYS * 86400))
            effective = max(0, confidence - months)
        stale = effective < 1
        if stale and not include_stale:
            continue
        # V2-10: a learning the person switched off leaves context and default views but stays
        # inspectable, and it is never deleted — `include_disabled` is what the inspect surface asks for.
        enabled = value.get('enabled') is not False
        if not enabled and not include_disabled:
            continue
        items.append({'key': key, 'type': value.get('type'), 'insight': value.get('insight'),
                      'confidence': confidence, 'effective_confidence': effective,
                      'enabled': enabled,
                      'stale': stale, 'source': source, 'evidence': value.get('evidence') or [],
                      'mission_id': value.get('mission_id'), 'task_id': value.get('task_id'),
                      'memory_id': row['id'], 'status': row['status'],
                      'updated': row['updated']})
    return items


def correct_learning(store, memory_id, *, insight=None, confidence=None, actor='user'):
    """Inspectable and correctable (doc 11 §5): a user correction supersedes the record.

    The memory store preserves the append-only chain; the corrected record becomes
    user-stated (trust 2) because the user just restated it. Corrections are explicit user
    actions and are never gated by the shadow flag — exactly like every other memory
    correction (audit 23, F23-1).
    """
    if insight is None and confidence is None:
        raise PolicyError('Nothing to correct: pass insight and/or confidence')
    memory = Memory(store)
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM memories WHERE id=?', (memory_id,)).fetchone()
    if row is None:
        raise PolicyError('Unknown learning record: %s' % memory_id)
    try:
        value = json.loads(row['value'])
    except (TypeError, ValueError):
        value = None
    if not isinstance(value, dict) or value.get('schema') != LEARNING_SCHEMA:
        raise PolicyError('That record is not a learning')
    updated = dict(value)
    if insight is not None:
        require_text(insight, 'insight')
        assert_safe({'insight': insight}, path='learning')
        updated['insight'] = insight
    if confidence is not None:
        updated['confidence'] = require_integer(confidence, 'confidence', lo=1, hi=10)
    updated['source'] = 'user-stated'
    new_id = memory.correct(memory_id, value=updated, summary=updated['insight'], actor=actor)
    return {'corrected': True, 'memory_id': new_id, 'supersedes': memory_id}


# ---- V2-10: the person's side of learning — off/on, explain, and evidence-thresholded suggestions --

def set_enabled(store, memory_id, enabled, *, actor='user'):
    """Turn one learning off (or back on) without deleting it (V2-10).

    The record is superseded by an equal-trust copy carrying `enabled`, so the append-only chain and
    the trust of the original content are preserved: switching a learning off is the person's action,
    not a new belief about the world. A disabled learning leaves model context and default views; it
    stays inspectable and one call brings it back. Records that are not current learnings are refused
    in plain words.
    """
    if not isinstance(enabled, bool):
        raise PolicyError('enabled is true or false')
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM memories WHERE id=?', (memory_id,)).fetchone()
    if row is None or row['status'] not in ('active', 'stale'):
        raise PolicyError('That learning is not current any more')
    try:
        value = json.loads(row['value'])
    except (TypeError, ValueError):
        value = None
    if not isinstance(value, dict) or value.get('schema') != LEARNING_SCHEMA:
        raise PolicyError('That record is not a learning')
    updated = dict(value)
    updated['enabled'] = bool(enabled)
    confidence = None
    if row['trust'] == 6:
        confidence = (int(value.get('confidence') or AUTO_CONFIDENCE_CAP)) / 10.0
    memory = Memory(store)
    new_id = memory.record(row['project_id'], row['type'], row['topic'], updated, row['summary'],
                           source_type=row['source_type'], source_ref=row['source_ref'],
                           actor=actor, trust=row['trust'], confidence=confidence,
                           user_confirmed=row['user_confirmed'])
    return {'enabled': bool(enabled), 'memory_id': new_id, 'supersedes': memory_id}


def explain_learning(store, memory_id, *, now=None):
    """Everything Kel knows about one learning: what it says, where it came from, what it changes.

    `effect` states the boundary in plain words: a learning is advisory only — it never grants
    permission, spending, file access or any irreversible authority (roadmap V2-10).
    """
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM memories WHERE id=?', (memory_id,)).fetchone()
    if row is None:
        raise PolicyError('Unknown learning record: %s' % memory_id)
    try:
        value = json.loads(row['value'])
    except (TypeError, ValueError):
        value = None
    if not isinstance(value, dict) or value.get('schema') != LEARNING_SCHEMA:
        raise PolicyError('That record is not a learning')
    view = {item['memory_id']: item for item in
            learnings_view(store, project_id=row['project_id'], include_stale=True,
                           include_disabled=True, now=now)}
    item = view.get(memory_id)
    queued = [entry for entry in promotion_queue(store, project_id=row['project_id'])
              if entry.get('subject') == value.get('key')]
    enabled = value.get('enabled') is not False
    effect = ('Advisory only. A learning never grants permission, spending, file access or any '
              'irreversible authority — those stay your decision every time.')
    if not enabled:
        effect += ' It is switched off, so it never reaches Kel\'s context.'
    elif item and item.get('stale'):
        effect += ' It has decayed out of context until it is observed again.'
    return {'memory_id': memory_id, 'key': value.get('key'), 'type': value.get('type'),
            'insight': value.get('insight'), 'source': value.get('source'),
            'trust': row['trust'],
            'confidence': (item or {}).get('confidence', value.get('confidence')),
            'effective_confidence': (item or {}).get('effective_confidence'),
            'stale': (item or {}).get('stale'), 'enabled': enabled,
            'evidence': value.get('evidence') or [],
            'provenance': {'mission_id': value.get('mission_id'), 'task_id': value.get('task_id'),
                           'source_ref': row['source_ref'], 'recorded': row['created']},
            'supersedes': row['supersedes'], 'superseded_by': row['superseded_by'],
            'history': Memory(store).history(memory_id),
            'promotions_queued': queued, 'effect': effect}


def suggest_learnings(store, *, project_id, now=None, minimum=None):
    """Evidence-thresholded suggestions from what actually happened (V2-10). Never applied.

    Three bounded sources, each needing `minimum` independent observations before anything is
    suggested: decided runs (model-by-task, read from the V2-09 evidence store), repeated user
    corrections (the wording the person keeps fixing), and repeated Connection use. Every suggestion
    goes through the existing memory proposal queue, so accept/reject/defer, dedupe-by-evidence and
    review behave exactly as V1.6 built them — a rejected suggestion never re-appears until its
    evidence changes. Nothing here is ever applied, and nothing here is authority: the fence above
    refuses authority-shaped text outright, and the proposal types below are never decisions or
    preferences (those come only from the person).
    """
    minimum = SUGGEST_MIN_EVIDENCE if minimum is None else require_integer(minimum, 'minimum',
                                                                          lo=2, hi=24)
    moment = time.time() if now is None else now
    floor = moment - SUGGEST_WINDOW_DAYS * 86400
    memory = Memory(store)
    considered = {'runs': 0, 'corrections': 0, 'connections': 0}
    created = []

    def offer(kind, type, topic, key, insight, evidence, why):
        refusal = authority_refusal(insight)
        if refusal:
            created.append({'key': key, 'topic': topic, 'state': 'refused', 'id': None,
                            'suppressed': False, 'reason': refusal})
            return
        value = {'schema': LEARNING_SCHEMA, 'key': key, 'type': type, 'insight': insight,
                 'confidence': 5, 'requested_confidence': 5, 'source': 'observed',
                 'evidence': list(evidence.get('refs') or []), 'scope': 'project'}
        result = memory.propose_change(project_id, kind=kind, type=TYPE_TO_MEMORY[type],
                                       topic=topic, value=value, summary=insight, why=why,
                                       evidence=evidence, source_ref='v2-10:suggest')
        created.append({'key': key, 'topic': topic, 'state': result.get('state'),
                        'id': result.get('id'), 'suppressed': bool(result.get('suppressed'))})

    # 1. Model-by-task: decided runs (routing_outcomes — the V2-09 evidence store).
    rows = _rows(store, 'SELECT * FROM routing_outcomes WHERE at>=? AND job_kind IS NOT NULL',
                 (floor,))
    stats = {}
    for row in rows:
        if row['verdict'] not in ('VERIFIED', 'FAILED'):
            continue
        slot = stats.setdefault((row['job_kind'], row['provider']), {'n': 0, 'ok': 0})
        slot['n'] += 1
        slot['ok'] += 1 if row['verdict'] == 'VERIFIED' else 0
    for (job_kind, provider), slot in sorted(stats.items()):
        considered['runs'] += slot['n']
        if slot['n'] < minimum or slot['ok'] / slot['n'] < 0.75:
            continue
        key = 'model.%s.%s' % (_slug(job_kind), _slug(provider))
        insight = ('%s completes %s work reliably here (verified in %d of %d recent runs, %d days).'
                   % (provider, job_kind, slot['ok'], slot['n'], SUGGEST_WINDOW_DAYS))
        offer('user_change', 'pattern', 'model for %s work' % job_kind, key, insight,
              {'source': 'routing', 'job_kind': job_kind, 'provider': provider,
               'runs': slot['n'], 'verified': slot['ok'],
               'share_pct': round(100 * slot['ok'] / slot['n']),
               'window_days': SUGGEST_WINDOW_DAYS,
               'sig': 'routing|%s|%s|%d|%d' % (job_kind, provider, slot['n'], slot['ok']),
               'refs': ['routing_outcomes:%s:%s' % (job_kind, provider)]},
              'Recent measured runs favour this; review it before Kel treats it as the way here.')

    # 2. Repeated user corrections: the wording the person keeps fixing.
    for topic, slot in sorted(_correction_evidence(store, project_id).items()):
        considered['corrections'] += slot['count']
        if slot['count'] < minimum:
            continue
        key = 'correction.%s' % _slug(topic)
        insight = ('You have corrected "%s" %d times; keep your latest wording as the convention.'
                   % (topic, slot['count']))
        offer('user_change', 'pattern', topic, key, insight,
              {'source': 'corrections', 'topic': topic, 'corrections': slot['count'],
               'memory_ids': slot['ids'][-6:],
               'sig': 'corrections|%s|%d' % (topic, slot['count']),
               'refs': ['memory_event:%s' % mid for mid in slot['ids'][-6:]]},
              'You corrected this repeatedly; a convention would stop the repetition.')

    # 3. Frequent Connection use: the tools this work actually leans on.
    for row in _rows(store, 'SELECT connection_id, action, COUNT(*) AS n FROM connection_events'
                            ' WHERE at>=? GROUP BY connection_id, action ORDER BY n DESC LIMIT 3',
                     (floor,)):
        considered['connections'] += row['n']
        if row['n'] < minimum:
            continue
        key = 'connection.%s.%s' % (_slug(row['connection_id']), _slug(row['action']))
        insight = ('You use "%s" for %s often (%d calls in %d days); it is part of how work gets '
                   'done here.' % (row['connection_id'], row['action'], row['n'],
                                   SUGGEST_WINDOW_DAYS))
        offer('user_change', 'tool', 'connection %s' % row['connection_id'], key, insight,
              {'source': 'connections', 'connection_id': row['connection_id'],
               'action': row['action'], 'calls': row['n'],
               'window_days': SUGGEST_WINDOW_DAYS, 'scope': 'engine',
               'sig': 'connections|%s|%s|%d' % (row['connection_id'], row['action'], row['n']),
               'refs': ['connection_events:%s:%s' % (row['connection_id'], row['action'])]},
              'A frequently used connection; a note keeps it in reach.')

    return {'minimum': minimum, 'window_days': SUGGEST_WINDOW_DAYS, 'considered': considered,
            'suggested': created,
            'note': 'Nothing is applied. Accept or reject each suggestion in the review queue.'}


# ---- the promotion queue (doc 11 §4.5): recorded, never applied -----------------------------

def queue_promotion(store, *, project_id, proposal_kind, subject, requested, basis=None,
                    flags=None):
    """Queue a promotion request (cross-project scope, playbook/role edits, high confidence).

    Recorded with the request and its basis; nothing is applied — promotion is gated on the
    doc-13 evaluation campaign and explicit user judgment (doc 11 §5)."""
    snapshot = flags_snapshot() if flags is None else dict(flags)
    if not _shadow(snapshot):
        return _off(snapshot=snapshot)
    require_text(proposal_kind, 'proposal_kind')
    require_text(subject, 'subject')
    assert_safe({'proposal_kind': proposal_kind, 'subject': subject}, path='promotion')
    team = Team(store)
    event = team.record_mission_activity(
        'proposal.queued',
        detail={'proposal_kind': proposal_kind, 'subject': subject,
                'requested': requested or {}, 'basis': basis or {}, 'state': 'queued'},
        refs={'project_id': project_id})
    return {'recorded': True, 'seq': event.get('seq'), 'proposal_kind': proposal_kind,
            'subject': subject, 'state': 'queued'}


def promotion_queue(store, *, project_id=None):
    """Read the queue back (oldest first). Nothing here has been applied."""
    items = []
    for row in _rows(store, "SELECT * FROM team_events WHERE kind='proposal.queued' ORDER BY seq"):
        refs = _decode(row, 'refs')
        if project_id and refs.get('project_id') != project_id:
            continue
        detail = _decode(row, 'detail')
        items.append({'seq': row['seq'], 'at': row['at'],
                      'proposal_kind': detail.get('proposal_kind'),
                      'subject': detail.get('subject'), 'requested': detail.get('requested'),
                      'basis': detail.get('basis'), 'state': detail.get('state', 'queued'),
                      'project_id': refs.get('project_id')})
    return items


# ---- shadow staffing proposals (doc 11 §5): recorded with predictions -----------------------

def shadow_proposal(store, *, project_id, mission_id, proposal, prediction, confidence,
                    basis=(), flags=None):
    """Record one shadow staffing proposal with its prediction. Never applied."""
    snapshot = flags_snapshot() if flags is None else dict(flags)
    if not _shadow(snapshot):
        return _off(snapshot=snapshot)
    if not isinstance(proposal, dict) or not proposal:
        raise PolicyError('A shadow proposal is a nonempty object')
    if not isinstance(prediction, dict) or not prediction:
        raise PolicyError('A shadow proposal carries a prediction object')
    if confidence not in ('low', 'medium', 'high'):
        raise PolicyError('Shadow confidence is low, medium or high')
    assert_safe({'proposal': proposal, 'prediction': prediction}, path='proposal')
    team = Team(store)
    event = team.record_mission_activity(
        'staffing.proposed',
        detail={'proposal': proposal, 'prediction': prediction, 'confidence': confidence,
                'basis': list(basis), 'state': 'shadow'},
        refs={'project_id': project_id, 'mission_id': mission_id})
    return {'recorded': True, 'seq': event.get('seq'), 'state': 'shadow',
            'mission_id': mission_id}


def shadow_proposals(store, *, project_id=None, mission_id=None):
    """Read shadow proposals back (oldest first)."""
    items = []
    for row in _rows(store, "SELECT * FROM team_events WHERE kind='staffing.proposed' ORDER BY seq"):
        refs = _decode(row, 'refs')
        if project_id and refs.get('project_id') != project_id:
            continue
        if mission_id and refs.get('mission_id') != mission_id:
            continue
        detail = _decode(row, 'detail')
        items.append({'seq': row['seq'], 'at': row['at'], 'mission_id': refs.get('mission_id'),
                      'proposal': detail.get('proposal'), 'prediction': detail.get('prediction'),
                      'confidence': detail.get('confidence'), 'basis': detail.get('basis'),
                      'state': detail.get('state', 'shadow')})
    return items


# ---- derived facts over existing streams ----------------------------------------------------

def _finding_rows(store, missions=None):
    if missions:
        marks = ','.join('?' * len(missions))
        return _rows(store, 'SELECT * FROM findings WHERE mission_id IN (%s)' % marks,
                     tuple(missions))
    return _rows(store, 'SELECT * FROM findings')


def _lens_evidence(rows):
    evidence = {}
    for row in rows:
        item = evidence.setdefault(row['lens'], {'raised': 0, 'dismissed': 0, 'confirmed': 0,
                                                 'open': 0, 'ids_confirmed': [], 'ids_dismissed': []})
        item['raised'] += 1
        status = row['status']
        if status == 'dismissed':
            item['dismissed'] += 1
            item['ids_dismissed'].append(row['id'])
        elif status in ('confirmed', 'fixed'):
            item['confirmed'] += 1
            item['ids_confirmed'].append(row['id'])
        else:
            item['open'] += 1
    return evidence


def _correction_evidence(store, project_id):
    rows = _rows(store,
                 "SELECT e.memory_id AS memory_id, m.topic AS topic, m.type AS type"
                 " FROM memory_events e JOIN memories m ON m.id = e.memory_id"
                 " WHERE e.project_id=? AND e.action='corrected' AND e.actor='user'"
                 " ORDER BY e.seq", (project_id,))
    items = {}
    for row in rows:
        slot = items.setdefault(row['topic'], {'count': 0, 'types': set(), 'ids': []})
        slot['count'] += 1
        slot['types'].add(row['type'])
        slot['ids'].append(row['memory_id'])
    return items


def _mission_events(store, kinds):
    rows = _rows(store, 'SELECT * FROM team_events ORDER BY seq')
    return [row for row in rows if row['kind'] in kinds]


def _mission_tiers(store):
    """mission_id -> tier, joined through contract.issued / staffing.decided events."""
    with contextlib.closing(store.connect()) as db:
        try:
            task_to_mission = {row['task_id']: row['mission_id']
                               for row in db.execute('SELECT mission_id, task_id FROM task_contracts')}
        except sqlite3.OperationalError as exc:
            if 'no such table' in str(exc).lower():
                return {}
            raise
    issued, assigned = {}, {}
    for row in _mission_events(store, ('contract.issued', 'staffing.decided')):
        # Only assignment-scoped events join a tier to a task; mission-scoped rows (NULL
        # assignment ids) would collapse onto one key and could attach a tier to the wrong
        # mission (audit 23, F23-6).
        if row['assignment_id'] is None:
            continue
        detail = _decode(row, 'detail')
        if row['kind'] == 'contract.issued' and detail.get('task_id'):
            issued[row['assignment_id']] = detail['task_id']
        elif row['kind'] == 'staffing.decided' and detail.get('tier'):
            assigned[row['assignment_id']] = detail['tier']
    tiers = {}
    for assignment_id, task_id in issued.items():
        mission_id = task_to_mission.get(task_id)
        tier = assigned.get(assignment_id)
        if mission_id and tier and mission_id not in tiers:
            tiers[mission_id] = tier
    return tiers


def _conflict_summary(store, mission_id):
    """Mission conflicts, or None when the parallel tables were never created."""
    from .parallel import conflict_metrics
    try:
        return conflict_metrics(store, mission_id)
    except sqlite3.OperationalError as exc:
        if 'no such table' in str(exc).lower():
            return None
        raise


def _derive_shadow_proposal(*, tier, findings, conflicts):
    """One deterministic proposal per mission from recorded facts (recorded, never applied)."""
    live = [item for item in findings if item['status'] != 'dismissed']
    blockers = [item for item in live if item['severity'] in ('blocker', 'critical')]
    conflicted = bool(conflicts and (conflicts.get('actual_overlaps')
                                     or conflicts.get('undeclared_count')))
    if tier and blockers:
        return {'proposal': {'change': 'keep or raise the tier for comparable missions: the '
                                       'gate recorded %d blocker/critical finding(s)' % len(blockers)},
                'prediction': {'escaped_defects_delta': 0, 'cost_delta_pct': 0},
                'confidence': 'low', 'basis': [item['id'] for item in blockers][:6]}
    if tier and not findings and not conflicted:
        return {'proposal': {'change': 'consider one lower tier for a comparable next mission '
                                       '(%s -> next down)' % tier},
                'prediction': {'wallclock_saved_pct': 25, 'escaped_defects_delta': 0},
                'confidence': 'low', 'basis': ['no findings recorded for this mission']}
    return None


# ---- retro (doc 11 §6) ----------------------------------------------------------------------

def draft_retro(store, *, project_id, mission_id, learnings=(), proposals=(), conflicts=None,
                flags=None, now=None):
    """Auto-draft the mission retro and append it to the activity stream.

    What shipped, what it cost, what went wrong, what was learned, which proposals the
    curator queued (doc 11 §6). Skimmable by design; user-visible surfaces decide their own
    presentation later."""
    snapshot = flags_snapshot() if flags is None else dict(flags)
    if not _shadow(snapshot):
        return _off(snapshot=snapshot)
    moment = time.time() if now is None else now
    task_ids = [row['task_id'] for row in _rows(
        store, 'SELECT task_id FROM task_contracts WHERE mission_id=?', (mission_id,))]
    issued = {}
    closed = []
    for row in _mission_events(store, ('contract.issued', 'task.closed')):
        detail = _decode(row, 'detail')
        if row['kind'] == 'contract.issued' and detail.get('task_id') in task_ids:
            issued[row['assignment_id']] = detail['task_id']
        elif row['kind'] == 'task.closed' and detail.get('task_id') in task_ids:
            closed.append({'task_id': detail.get('task_id'), 'outcome': detail.get('outcome'),
                           'violations': detail.get('violations') or []})
    reservations = _rows(store, 'SELECT * FROM budget_reservations')
    cost = {'reserved': 0, 'consumed': 0, 'released': 0, 'tokens': 0, 'cost_units': 0.0}
    for row in reservations:
        if row.get('assignment_id') in issued:
            state = row.get('state') or 'reserved'
            cost[state] = cost.get(state, 0) + 1
            cost['tokens'] += int(row.get('tokens') or 0)
            cost['cost_units'] += float(row.get('cost') or 0.0)
    if conflicts is None:
        conflicts = _conflict_summary(store, mission_id)
    findings = _finding_rows(store, missions=[mission_id])
    went_wrong = []
    for item in findings:
        if item['status'] != 'dismissed' and item['severity'] in ('blocker', 'critical'):
            went_wrong.append('%s %s (%s): %s' % (item['severity'], item['id'], item['lens'],
                                                  item['summary'][:160]))
    for item in closed:
        went_wrong.extend(str(problem)[:160] for problem in item['violations'][:4])
    if conflicts:
        if conflicts.get('actual_overlaps'):
            went_wrong.append('integration: %d real overlap(s) between streams'
                              % len(conflicts['actual_overlaps']))
        if conflicts.get('undeclared_count'):
            went_wrong.append('integration: %d undeclared write(s) detected'
                              % conflicts['undeclared_count'])
    retro = {'schema': RETRO_SCHEMA, 'mission_id': mission_id, 'project_id': project_id,
             'shipped': closed, 'cost': cost, 'went_wrong': went_wrong,
             'learned': list(learnings), 'proposals': list(proposals), 'at': moment}
    team = Team(store)
    event = team.record_mission_activity('retro.drafted', detail=retro,
                                         refs={'project_id': project_id,
                                               'mission_id': mission_id})
    retro['seq'] = event.get('seq')
    return retro


def retro_for(store, *, mission_id):
    """The latest drafted retro for a mission, or None."""
    latest = None
    for row in _rows(store, "SELECT * FROM team_events WHERE kind='retro.drafted' ORDER BY seq"):
        refs = _decode(row, 'refs')
        if refs.get('mission_id') == mission_id:
            latest = _decode(row, 'detail')
    return latest


# ---- the curator (doc 11 §4): post-mission, bounded, deterministic --------------------------

def curate(store, *, project_id, mission_id, missions=None, now=None, flags=None):
    """Run the post-mission curator pipeline in shadow mode.

    Collect -> dedup -> score -> propose (\"would the system catch this next time?\" is encoded
    as a concrete, testable rule per candidate) -> record within confidence caps; preferences
    only from explicit user confirmation; promotions queued, never applied. With
    `workforce.learning.shadow` off this performs zero writes (B-config parity by
    construction). Lens evidence is scoped by the `missions` the caller attributes to this
    project (the engine records no findings->project link); without it the insight text says
    "the recorded evidence" instead of claiming project scope (audit 23, F23-2)."""
    snapshot = flags_snapshot() if flags is None else dict(flags)
    if not _shadow(snapshot):
        return {'applied': False, 'reason': 'workforce.learning.shadow is off', 'flags': snapshot}
    moment = time.time() if now is None else now
    scope = list(missions) if missions else None
    scope_label = 'this project' if scope else 'the recorded evidence'
    candidates = []
    for lens, counts in sorted(_lens_evidence(_finding_rows(store, missions=scope)).items()):
        if counts['dismissed'] >= 2:
            candidates.append({'key': 'lens.%s.false-positive' % lens, 'type': 'pitfall',
                               'insight': 'The %s lens over-fires: %d dismissed findings across '
                                          '%s.' % (lens, counts['dismissed'], scope_label),
                               'confidence': min(10, 2 + counts['dismissed']),
                               'source': 'observed', 'evidence': counts['ids_dismissed'][:12]})
        if counts['confirmed'] >= 2:
            candidates.append({'key': 'lens.%s.proven' % lens, 'type': 'pattern',
                               'insight': 'The %s lens repeatedly finds real defects: %d '
                                          'confirmed findings across %s.'
                                          % (lens, counts['confirmed'], scope_label),
                               'confidence': min(10, 2 + counts['confirmed']),
                               'source': 'observed', 'evidence': counts['ids_confirmed'][:12]})
    for topic, slot in sorted(_correction_evidence(store, project_id).items()):
        if slot['count'] >= 2:
            candidates.append({'key': 'correction.%s' % _slug(topic),
                               'type': 'preference' if 'preference' in slot['types'] else 'pitfall',
                               'insight': 'The user corrected "%s" %d times — record the '
                                          'corrected outcome so it stops repeating.'
                                          % (topic, slot['count']),
                               'confidence': min(9, 3 + slot['count']), 'source': 'user-stated',
                               'confirmed_by': 'user', 'evidence': slot['ids'][:12]})
    conflicts = _conflict_summary(store, mission_id)
    if conflicts and conflicts.get('undeclared_count'):
        evidence = ['%s:%s' % (stream_id, path)
                    for stream_id, paths in sorted((conflicts.get('undeclared_writes') or {}).items())
                    for path in paths][:12]
        candidates.append({'key': 'parallel.undeclared-writes', 'type': 'pitfall',
                           'insight': 'A parallel stream wrote outside its declared paths '
                                      '(%d write(s) detected); tighten scope boundaries before '
                                      'the next parallel mission.' % conflicts['undeclared_count'],
                           'confidence': min(10, 2 + conflicts['undeclared_count']),
                           'source': 'observed', 'evidence': evidence})
    if conflicts and conflicts.get('actual_overlaps'):
        candidates.append({'key': 'parallel.integration-overlap', 'type': 'pitfall',
                           'insight': 'Two parallel streams changed the same path (%d real '
                                      'overlap(s)); keep write sets disjoint or serialise.'
                                      % len(conflicts['actual_overlaps']),
                           'confidence': min(10, 2 + len(conflicts['actual_overlaps'])),
                           'source': 'observed',
                           'evidence': [str(item.get('paths'))[:120]
                                        for item in conflicts['actual_overlaps']][:12]})
    recorded = []
    for candidate in candidates:
        recorded.append(record_learning(
            store, project_id=project_id, key=candidate['key'], type=candidate['type'],
            insight=candidate['insight'], confidence=candidate['confidence'],
            source=candidate['source'], evidence=candidate.get('evidence', ()),
            mission_id=mission_id, confirmed_by=candidate.get('confirmed_by'),
            flags=snapshot))
    tier = _mission_tiers(store).get(mission_id)
    findings = _finding_rows(store, missions=[mission_id])
    proposal = _derive_shadow_proposal(tier=tier, findings=findings, conflicts=conflicts)
    proposal_result = None
    if proposal:
        proposal_result = shadow_proposal(store, project_id=project_id, mission_id=mission_id,
                                          proposal=proposal['proposal'],
                                          prediction=proposal['prediction'],
                                          confidence=proposal['confidence'],
                                          basis=proposal['basis'], flags=snapshot)
    retro = draft_retro(store, project_id=project_id, mission_id=mission_id,
                        learnings=[item['key'] for item in recorded if item.get('recorded')],
                        proposals=[proposal_result['seq']] if proposal_result
                        and proposal_result.get('recorded') else [],
                        conflicts=conflicts, flags=snapshot, now=moment)
    return {'applied': True, 'mission_id': mission_id, 'candidate_count': len(candidates),
            'learnings': recorded, 'proposal': proposal_result, 'retro': retro,
            'validation': validation_metrics(store, now=moment), 'flags': snapshot}


# ---- derived performance stats and validation metrics (doc 11 §3, doc 13 §4) ----------------

def performance_stats(store, *, missions=None, now=None):
    """Derived performance views over existing streams — inspectable, never gating.

    Small samples stay honest: rates carry their `n`, and below three verified outcomes the
    rate is reported as insufficient (doc 11 §3 rule)."""
    moment = time.time() if now is None else now
    evidence = _lens_evidence(_finding_rows(store, missions=missions))
    lens_stats = {}
    for lens, counts in sorted(evidence.items()):
        raised = counts['raised']
        dismissed = counts['dismissed']
        confirmed = counts['confirmed']
        lens_stats[lens] = {
            'raised': raised, 'confirmed': confirmed, 'dismissed': dismissed,
            'open': counts['open'],
            'false_positive_rate': (round(dismissed / raised, 3) if raised else None),
            'hit_rate': (round(confirmed / raised, 3) if raised else None),
            'basis': 'insufficient (n<3)' if raised < 3 else 'n=%d' % raised}
    contracts = _rows(store, 'SELECT mission_id, task_id FROM task_contracts')
    closed_outcomes = {}
    for row in _mission_events(store, ('task.closed',)):
        detail = _decode(row, 'detail')
        outcome = detail.get('outcome') or 'unknown'
        closed_outcomes[outcome] = closed_outcomes.get(outcome, 0) + 1
    reservations = _rows(store, 'SELECT state, tokens, wallclock, cost FROM budget_reservations')
    budget = {'reservations': len(reservations), 'tokens': 0, 'wallclock': 0, 'cost': 0.0,
              'by_state': {}}
    for row in reservations:
        state = row.get('state') or 'reserved'
        budget['by_state'][state] = budget['by_state'].get(state, 0) + 1
        budget['tokens'] += int(row.get('tokens') or 0)
        budget['wallclock'] += int(row.get('wallclock') or 0)
        budget['cost'] += float(row.get('cost') or 0.0)
    conflicts = {'missions_with_streams': 0, 'actual_overlaps': 0, 'undeclared_writes': 0}
    mission_ids = sorted({row['mission_id'] for row in contracts if row.get('mission_id')})
    for mission_id in mission_ids:
        summary = _conflict_summary(store, mission_id)
        if not summary:
            continue
        conflicts['missions_with_streams'] += 1
        conflicts['actual_overlaps'] += len(summary.get('actual_overlaps') or [])
        conflicts['undeclared_writes'] += int(summary.get('undeclared_count') or 0)
    return {'as_of': moment, 'lens': lens_stats, 'contracts': len(contracts),
            'closed_outcomes': closed_outcomes, 'budget': budget, 'conflicts': conflicts,
            'basis': 'derived from findings/contracts/budget/mission streams; no sampling'}


def validation_metrics(store, *, now=None):
    """The shadow validation metrics (doc 11 §5, doc 13 §4): gating precision + false-skip.

    Gating precision: confirmed / (confirmed + dismissed) over recorded findings.
    False-skip: recompute the deterministic gating plan for each recorded mission tier and
    check whether a lens the plan skipped nonetheless produced live findings — the skip signal
    that would have caught them earlier. Small samples stay labelled, never averaged away."""
    moment = time.time() if now is None else now
    from .assurance import lenses_for
    findings = _finding_rows(store)
    evidence = _lens_evidence(findings)
    confirmed_total = sum(item['confirmed'] for item in evidence.values())
    dismissed_total = sum(item['dismissed'] for item in evidence.values())
    judged = confirmed_total + dismissed_total
    per_lens = {}
    for lens, counts in sorted(evidence.items()):
        lens_judged = counts['confirmed'] + counts['dismissed']
        per_lens[lens] = {'precision': (round(counts['confirmed'] / lens_judged, 3)
                                        if lens_judged else None),
                          'confirmed': counts['confirmed'], 'dismissed': counts['dismissed']}
    precision = {'value': (round(confirmed_total / judged, 3) if judged else None),
                 'confirmed': confirmed_total, 'dismissed': dismissed_total,
                 'basis': 'insufficient (n<3)' if judged < 3 else 'n=%d' % judged}
    live_by_mission = {}
    for item in findings:
        if item['status'] != 'dismissed':
            live_by_mission.setdefault(item['mission_id'], set()).add(item['lens'])
    tiers = _mission_tiers(store)
    skipped_total, misses = 0, []
    for mission_id, tier in sorted(tiers.items()):
        try:
            plan = lenses_for(tier)
        except PolicyError:
            continue
        for lens in plan['skipped']:
            skipped_total += 1
            if lens in live_by_mission.get(mission_id, set()):
                misses.append({'mission_id': mission_id, 'tier': tier, 'lens': lens})
    false_skip = {'rate': (round(len(misses) / skipped_total, 3) if skipped_total else None),
                  'misses': misses[:24], 'skipped_total': skipped_total,
                  'basis': ('insufficient (n<3)' if skipped_total < 3
                            else 'recomputed gating plans over %d mission(s)' % len(tiers))}
    return {'as_of': moment, 'gating_precision': precision, 'per_lens': per_lens,
            'false_skip': false_skip,
            'note': 'shadow metrics only; nothing here gates or changes live behavior'}
