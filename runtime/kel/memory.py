"""Project memory: structured, provenance-aware, project-scoped (V1.3 migration 001).

Approved design: docs/v1.3/KEL_V1.3_MEMORY_MODEL.md.

Trust levels (lower = stronger):
  1 current explicit user instruction (turn-scoped; never stored as a record)
  2 user-confirmed decision/preference
  3 verified repository/configuration fact
  4 previously accepted project decision
  5 reviewed worker evidence
  6 model inference
  7 untrusted external content (README text, webpages, raw worker output)

Hard rules: project isolation on every read/write; secret-like values refused;
external content can never become authoritative; preference records only from explicit
user confirmation; conflicts are recorded, never silently overwritten; history is
preserved through supersession; nothing is hard-deleted except `forget` content purges.
"""
import contextlib
import hashlib
import json
import re
import sqlite3
import time

from .core import PolicyError, uid

MIGRATION_VERSION = 1
MIGRATION_NAME = 'v13-memory'
PROPOSALS_VERSION = 15
PROPOSALS_NAME = 'v16-memory-proposals'
PROPOSAL_KINDS = ('user_change', 'vetting', 'repo_state', 'stale', 'correction', 'conflict')
PROPOSAL_STATES = ('pending', 'accepted', 'rejected', 'deferred', 'superseded')

TYPES = ('fact', 'decision', 'convention', 'preference', 'command', 'path', 'component',
         'relationship', 'limitation', 'workflow', 'question', 'observation')

SOURCE_TRUST = {
    'user_instruction': 2,
    'user_confirmation': 2,
    'repo_inspection': 3,
    'config_inspection': 3,
    'system': 4,
    'worker_evidence': 5,
    # Workforce learning sources (Phase 5.6, doc 11 §2): observed and cross-model evidence
    # outrank inference; the learning layer maps its own source vocabulary onto these.
    'workforce_observed': 5,
    'workforce_cross_model': 5,
    'workforce_inferred': 6,
    'model_inference': 6,
    'external_document': 7,
    'web': 7,
}
UNTRUSTED_SOURCES = ('external_document', 'web')
AUTHORITATIVE_TYPES = ('decision', 'preference')

_SECRET_PATTERNS = (
    ('anthropic-key', re.compile(r'sk-ant-[A-Za-z0-9\-_]{16,}')),
    ('api-key', re.compile(r'sk-[A-Za-z0-9]{20,}')),
    ('github-token', re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}')),
    ('github-pat', re.compile(r'github_pat_[A-Za-z0-9_]{20,}')),
    ('aws-key', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('google-key', re.compile(r'AIza[0-9A-Za-z_\-]{30,}')),
    ('slack-token', re.compile(r'xox[baprs]-[A-Za-z0-9\-]{10,}')),
    ('private-key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('bearer-header', re.compile(r'(?i)authorization\s*:\s*bearer\s+\S{8,}')),
    ('credential-assignment',
     re.compile(r'(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\s*[:=]\s*\S{12,}')),
)

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
    version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS memories(
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    type TEXT NOT NULL,
    topic TEXT NOT NULL,
    value TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL,
    trust INTEGER NOT NULL,
    confidence REAL,
    user_confirmed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    supersedes TEXT,
    superseded_by TEXT,
    source_digest TEXT,
    created REAL NOT NULL,
    updated REAL NOT NULL,
    checked_at REAL);
CREATE INDEX IF NOT EXISTS memories_by_project ON memories(project_id, status, type, topic);
CREATE TABLE IF NOT EXISTS memory_events(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT UNIQUE NOT NULL,
    project_id TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    detail TEXT,
    at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS memory_conflicts(
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    memory_a TEXT NOT NULL,
    memory_b TEXT NOT NULL,
    state TEXT NOT NULL,
    resolution TEXT,
    resolved_by TEXT,
    at REAL NOT NULL,
    resolved_at REAL);
CREATE INDEX IF NOT EXISTS conflicts_open ON memory_conflicts(project_id, state);
"""

FTS_DDL = "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(topic, summary, value, mid UNINDEXED)"

# The memory review surface (v1.6): a durable queue of changes Kel believes the project's saved
# knowledge needs, each waiting for explicit user judgment before any record is touched.
PROPOSALS_DDL = """
CREATE TABLE IF NOT EXISTS memory_proposals(
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    type TEXT NOT NULL,
    topic TEXT NOT NULL,
    value TEXT NOT NULL,
    summary TEXT NOT NULL,
    why TEXT NOT NULL,
    current_id TEXT,
    current_snapshot TEXT,
    evidence TEXT,
    dedupe_key TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    source_ref TEXT NOT NULL DEFAULT '',
    created REAL NOT NULL,
    updated REAL NOT NULL,
    decided_at REAL,
    decided_by TEXT,
    note TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS proposals_by_project ON memory_proposals(project_id, state, updated);
CREATE INDEX IF NOT EXISTS proposals_by_key ON memory_proposals(dedupe_key, state);
"""


def _has_version(store, version):
    with contextlib.closing(store.connect()) as db:
        return bool(_table(db, 'schema_migrations')) and bool(
            db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (version,)).fetchone())


def ensure_proposals(store, v13_in_same_init=False):
    """Create the proposal table (additive, idempotent; one backup before the first use).

    v13_in_same_init: the V1.3 memory migration just ran in the same constructor call and made the
    upgrade backup for this store; the proposals step then rides along without a second backup.
    """
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (PROPOSALS_VERSION,)).fetchone():
            return
        if not _table(db, 'schema_migrations'):
            db.executescript(DDL.split('CREATE TABLE IF NOT EXISTS memories(')[0])
        if (not _table(db, 'memory_proposals') and not _is_fresh_database(db)
                and not v13_in_same_init):
            _backup(store, db)  # one backup before the first proposals mutation of existing data
        db.executescript(PROPOSALS_DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (PROPOSALS_VERSION, PROPOSALS_NAME, time.time(), ''))


def scan_secret(text):
    """Return the name of the first secret-like pattern found, or None."""
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return name
    return None


def _table(db, name):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _is_fresh_database(db):
    return not _table(db, 'jobs')


def _create_fts(db):
    try:
        db.execute(FTS_DDL)
        return True
    except sqlite3.OperationalError:
        return False


def _fts_present(db):
    return _table(db, 'memories_fts')


def _backup(store, db):
    folder = store.root / 'backups'
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PolicyError('Memory migration refused: cannot create backup folder (%s)' % exc)
    target = folder / ('pre-v13-%s.sqlite3' % time.strftime('%Y%m%d-%H%M%S'))
    dest = sqlite3.connect(str(target))
    try:
        db.backup(dest)
        if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise PolicyError('Memory migration refused: backup failed its integrity check')
    except PolicyError:
        raise
    except sqlite3.Error as exc:
        raise PolicyError('Memory migration refused: backup failed (%s)' % exc)
    finally:
        dest.close()
    receipt = {
        'from_version': 'v1.2',
        'migration': '001-%s' % MIGRATION_NAME,
        'backup': str(target.relative_to(store.root)).replace('\\', '/'),
        'integrity': 'ok',
        'state': 'READY',
        'created': time.time(),
    }
    path = store.root / 'migration-receipt.json'
    if path.exists():
        (store.root / 'migration-receipt-legacy.json').write_text(
            path.read_text(encoding='utf-8'), encoding='utf-8')
    path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


def ensure_schema(store):
    """Create the V1.3 memory tables (idempotent, additive). Returns FTS availability."""
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return _fts_present(db)
        first = not _table(db, 'schema_migrations')
        if first and not _is_fresh_database(db):
            _backup(store, db)  # one backup before the first V1.3 mutation of V1.2 data
        db.executescript(DDL)
        fts = _create_fts(db)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'fts5=%s' % ('on' if fts else 'off')))
        return fts


class Memory:
    """Project memory store. Every read/write is scoped to one project id."""

    def __init__(self, store, use_fts=None):
        self.store = store
        v13_before = _has_version(store, MIGRATION_VERSION)
        probe = ensure_schema(store)
        ensure_proposals(store, v13_in_same_init=not v13_before)
        if use_fts is None:
            self.fts = probe
        elif use_fts:
            if not probe:
                raise PolicyError('FTS5 search requested but unavailable for this database')
            self.fts = True
        else:
            self.fts = False  # deterministic fallback mode (LIKE search)

    # ---- internals -------------------------------------------------------

    def _event(self, db, project_id, memory_id, action, actor='kel', detail=None):
        db.execute('INSERT INTO memory_events(id,project_id,memory_id,action,actor,detail,at)'
                   ' VALUES(?,?,?,?,?,?,?)',
                   (uid(), project_id, memory_id, action, actor,
                    json.dumps(detail, sort_keys=True) if detail else None, time.time()))
        aggregate = 'memory:' + memory_id
        revision = db.execute(
            'SELECT COALESCE(MAX(revision),0)+1 FROM events WHERE aggregate_id=?',
            (aggregate,)).fetchone()[0]
        payload = {'schema_version': 1,
                   'memory': {'id': memory_id, 'project': project_id, 'action': action,
                              'actor': actor, 'detail': detail or {}}}
        db.execute('INSERT INTO events(id,aggregate_id,revision,type,at,payload,dedupe)'
                   ' VALUES(?,?,?,?,?,?,NULL)',
                   (uid(), aggregate, revision, 'memory.' + action, time.time(),
                    json.dumps(payload, sort_keys=True)))

    def _require_project(self, db, project_id):
        if not isinstance(project_id, str) or not project_id:
            raise PolicyError('Memory requires a project id')
        if db.execute('SELECT 1 FROM projects WHERE id=?', (project_id,)).fetchone() is None:
            raise PolicyError('Project missing')

    def _get(self, db, memory_id):
        row = db.execute('SELECT * FROM memories WHERE id=?', (memory_id,)).fetchone()
        if not row:
            raise PolicyError('Memory not found')
        return row

    def _refuse(self, project_id, actor, scan):
        with self.store.transaction() as db:
            self._require_project(db, project_id)
            self._event(db, project_id, '', 'refused', actor, {'scan': scan})
        raise PolicyError('Memory refused: the content looks like a secret (pattern: %s)' % scan)

    # ---- writes ----------------------------------------------------------

    def record(self, project_id, type, topic, value, summary, *, source_type,
               source_ref='', actor='kel', trust=None, confidence=None,
               user_confirmed=0, source_digest=None):
        if type not in TYPES:
            raise PolicyError('Unknown memory type')
        if source_type not in SOURCE_TRUST:
            raise PolicyError('Unknown memory source type')
        if trust is None:
            trust = SOURCE_TRUST[source_type]
        if trust not in (1, 2, 3, 4, 5, 6, 7):
            raise PolicyError('Trust must be 1..7 (1 strongest)')
        if type == 'preference' and (trust != 2 or source_type not in
                                     ('user_instruction', 'user_confirmation')):
            raise PolicyError('Preferences are stored only from explicit user confirmation')
        if type == 'decision' and not (trust <= 2 or (trust == 4 and source_type == 'system')):
            raise PolicyError('Decisions come only from explicit user confirmation or accepted work')
        if source_type in UNTRUSTED_SOURCES and trust != 7:
            raise PolicyError('External content always stays untrusted evidence')
        if trust == 6 and confidence is None:
            raise PolicyError('Model inference records need a confidence value')
        if not isinstance(topic, str) or not topic.strip() or len(topic) > 200:
            raise PolicyError('Topic must be 1 to 200 characters')
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
            raise PolicyError('Summary must be 1 to 2000 characters')
        if not isinstance(source_ref, str) or len(source_ref) > 2000:
            raise PolicyError('Source reference must be a string up to 2000 characters')
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                raise PolicyError('Confidence must be a number between 0 and 1')
            if not 0.0 <= confidence <= 1.0:
                raise PolicyError('Confidence must be between 0 and 1')
        try:
            raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            raise PolicyError('Memory value must be JSON-serializable')
        if len(raw.encode('utf-8')) > 20000:
            raise PolicyError('Memory value is too large')
        for text in (raw, summary, topic, source_ref):
            scan = scan_secret(text)
            if scan:
                self._refuse(project_id, actor, scan)
        user_confirmed = int(bool(user_confirmed))
        now = time.time()
        memory_id = uid()
        with self.store.transaction() as db:
            self._require_project(db, project_id)
            peer = db.execute(
                "SELECT * FROM memories WHERE project_id=? AND type=? AND topic=?"
                " AND status='active' AND value<>? ORDER BY updated DESC LIMIT 1",
                (project_id, type, topic, raw)).fetchone()
            status, supersedes, superseded_by, conflict = 'active', None, None, None
            if peer is not None:
                if peer['trust'] < trust:
                    status, superseded_by = 'superseded', peer['id']
                    conflict = ('a_wins', peer['id'])
                elif peer['trust'] > trust:
                    supersedes = peer['id']
                    conflict = ('b_wins', peer['id'])
                elif peer['user_confirmed'] and not user_confirmed:
                    status, superseded_by = 'superseded', peer['id']
                    conflict = ('a_wins', peer['id'])
                elif not peer['user_confirmed'] and user_confirmed:
                    supersedes = peer['id']
                    conflict = ('b_wins', peer['id'])
                elif type in AUTHORITATIVE_TYPES:
                    conflict = ('open', peer['id'])
                else:
                    supersedes = peer['id']
                    conflict = ('b_wins', peer['id'])
            db.execute('INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (memory_id, project_id, type, topic, raw, summary, source_type,
                        source_ref, actor, trust, confidence, user_confirmed,
                        status, supersedes, superseded_by, source_digest, now, now, None))
            if self.fts:
                db.execute('INSERT INTO memories_fts(topic,summary,value,mid) VALUES(?,?,?,?)',
                           (topic, summary, raw, memory_id))
            if supersedes:
                db.execute('UPDATE memories SET status=?, superseded_by=?, updated=? WHERE id=?',
                           ('superseded', memory_id, now, supersedes))
                self._event(db, project_id, supersedes, 'superseded', actor,
                            {'superseded_by': memory_id, 'reason': 'replaced'})
            if status == 'superseded':
                db.execute('UPDATE memories SET supersedes=COALESCE(supersedes,?), updated=?'
                           ' WHERE id=?',
                           (memory_id, now, peer['id']))
                self._event(db, project_id, memory_id, 'superseded', actor,
                            {'superseded_by': peer['id'], 'reason': 'less authority'})
            if conflict:
                resolution, peer_id = conflict
                is_open = resolution == 'open'
                conflict_id = uid()
                db.execute('INSERT INTO memory_conflicts VALUES(?,?,?,?,?,?,?,?,?)',
                           (conflict_id, project_id, peer_id, memory_id,
                            'open' if is_open else 'resolved',
                            None if is_open else resolution,
                            None if is_open else 'kel',
                            now, None if is_open else now))
                if is_open:
                    # A durable disagreement only the user can settle: queue it on the review surface.
                    # The evidence signature is content-based, so the same pair of statements never
                    # asks again after a rejection; a genuinely different value gets a new key.
                    peer_row = db.execute('SELECT value FROM memories WHERE id=?', (peer_id,)).fetchone()
                    pair_sig = hashlib.sha256(
                        ((peer_row['value'] if peer_row else '') + '|' + raw).encode('utf-8')).hexdigest()
                    self._propose_db(db, project_id, kind='conflict', type=type, topic=topic,
                                     value=json.loads(raw), summary=summary,
                                     why='Two saved choices disagree — pick the one that should stand.',
                                     current_id=peer_id,
                                     evidence={'conflict_id': conflict_id, 'peer': peer_id,
                                               'proposed': memory_id, 'sig': pair_sig},
                                     source_ref='conflict:' + conflict_id)
            self._event(db, project_id, memory_id, 'created', actor,
                        {'type': type, 'trust': trust, 'source': source_type})
        return memory_id

    def propose(self, project_id, type, topic, value, summary, *, confidence,
                source_ref='', actor='kel'):
        """Low-trust proposal (never promoted without explicit user confirmation)."""
        if type in AUTHORITATIVE_TYPES:
            raise PolicyError('Decisions and preferences are never proposed; they need the user')
        return self.record(project_id, type, topic, value, summary,
                           source_type='model_inference', source_ref=source_ref,
                           actor=actor, confidence=confidence)

    def confirm(self, memory_id, actor='user'):
        """Explicit user confirmation promotes a record to level 2."""
        with self.store.transaction() as db:
            row = self._get(db, memory_id)
            if row['status'] != 'active':
                raise PolicyError('Only an active memory can be confirmed')
            if row['trust'] == 7:
                raise PolicyError('External content cannot be confirmed as your own decision;'
                                  ' restate it as a decision instead')
            db.execute('UPDATE memories SET user_confirmed=1, trust=2, updated=? WHERE id=?',
                       (time.time(), memory_id))
            self._event(db, row['project_id'], memory_id, 'confirmed', actor,
                        {'trust_before': row['trust']})
        return memory_id
    def correct(self, memory_id, *, value=None, summary=None, actor='user'):
        """User edit: a new record supersedes the old one; the history chain is preserved."""
        with contextlib.closing(self.store.connect()) as db:
            old = self._get(db, memory_id)
            if old['status'] != 'active':
                raise PolicyError('Only an active memory can be corrected')
        new_summary = summary if summary is not None else old['summary']
        if not isinstance(new_summary, str) or not new_summary.strip():
            raise PolicyError('Summary must be nonempty')
        if value is None:
            new_value = old['value']
        else:
            try:
                new_value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            except (TypeError, ValueError):
                raise PolicyError('Memory value must be JSON-serializable')
        for text in (new_value, new_summary):
            scan = scan_secret(text)
            if scan:
                self._refuse(old['project_id'], actor, scan)
        now = time.time()
        new_id = uid()
        with self.store.transaction() as db:
            current = self._get(db, memory_id)
            if current['status'] != 'active':
                raise PolicyError('Memory changed while correcting; retry')
            db.execute('INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (new_id, old['project_id'], old['type'], old['topic'], new_value,
                        new_summary, 'user_confirmation', old['source_ref'], actor, 2, None, 1,
                        'active', old['id'], None, None, now, now, None))
            db.execute('UPDATE memories SET status=?, superseded_by=?, updated=? WHERE id=?',
                       ('superseded', new_id, now, memory_id))
            if self.fts:
                db.execute('INSERT INTO memories_fts(topic,summary,value,mid) VALUES(?,?,?,?)',
                           (old['topic'], new_summary, new_value, new_id))
            self._event(db, old['project_id'], memory_id, 'corrected', actor,
                        {'superseded_by': new_id})
            self._event(db, old['project_id'], new_id, 'created', actor,
                        {'corrects': memory_id})
        return new_id

    def retract(self, memory_id, *, reason='', actor='user'):
        with self.store.transaction() as db:
            row = self._get(db, memory_id)
            if row['status'] not in ('active', 'stale'):
                raise PolicyError('Only an active or stale memory can be retracted')
            db.execute('UPDATE memories SET status=?, updated=? WHERE id=?',
                       ('retracted', time.time(), memory_id))
            self._event(db, row['project_id'], memory_id, 'retracted', actor,
                        {'reason': str(reason)[:500]} if reason else None)
        return memory_id

    def forget(self, memory_id, actor='user'):
        """Purge content and keep a content-free tombstone plus an audit event.

        Purge is physical as well as logical: `secure_delete` zeroes the freed cells, the FTS row
        is removed and its segments merged, and the WAL is checkpointed so pre-forget pages are
        not retained (best effort under concurrent readers). The tombstone and its audit event
        stay; neither carries content.
        """
        with self.store.transaction() as db:
            row = self._get(db, memory_id)
            db.execute('UPDATE memories SET value=?, summary=?, status=?, updated=? WHERE id=?',
                       ('', '', 'retracted', time.time(), memory_id))
            if self.fts:
                db.execute('DELETE FROM memories_fts WHERE mid=?', (memory_id,))
                db.execute("INSERT INTO memories_fts(memories_fts) VALUES('optimize')")
            self._event(db, row['project_id'], memory_id, 'forgotten', actor, None)
        try:
            with contextlib.closing(self.store.connect()) as db:
                db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        except sqlite3.OperationalError:
            pass  # a busy reader delays the scrub; the logical purge is already durable
        return memory_id

    def resolve_conflict(self, conflict_id, choice, actor='user'):
        if choice not in ('a', 'b', 'dismiss'):
            raise PolicyError('Choose a, b, or dismiss (merge is not supported)')
        with self.store.transaction() as db:
            c = db.execute('SELECT * FROM memory_conflicts WHERE id=?', (conflict_id,)).fetchone()
            if not c or c['state'] != 'open':
                raise PolicyError('No open conflict with that id')
            now = time.time()
            if choice == 'dismiss':
                db.execute("UPDATE memory_conflicts SET state='resolved',"
                           " resolution='dismissed', resolved_by=?, resolved_at=? WHERE id=?",
                           (actor, now, conflict_id))
                return 'dismissed'
            winner = c['memory_a'] if choice == 'a' else c['memory_b']
            loser = c['memory_b'] if choice == 'a' else c['memory_a']
            db.execute("UPDATE memories SET status='superseded', superseded_by=?, updated=?"
                       " WHERE id=? AND status='active'", (winner, now, loser))
            db.execute('UPDATE memories SET supersedes=COALESCE(supersedes,?), updated=?'
                       ' WHERE id=?', (loser, now, winner))
            db.execute("UPDATE memory_conflicts SET state='resolved',"
                       " resolution='user_choice', resolved_by=?, resolved_at=? WHERE id=?",
                       (actor, now, conflict_id))
            self._event(db, c['project_id'], loser, 'superseded', actor,
                        {'conflict': conflict_id, 'winner': winner})
        return 'user_choice'

    # ---- memory proposals (v1.6 review surface) --------------------------

    def _proposal_key(self, kind, type, topic, value_json, evidence_sig):
        raw = '|'.join((kind, type, topic, value_json, str(evidence_sig or '')))
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def _propose_db(self, db, project_id, *, kind, type, topic, value, summary, why,
                    current_id=None, evidence=None, source_ref='', actor='kel'):
        """Queue a proposed change (runs inside the caller's transaction).

        The dedupe key covers the exact proposed change plus an evidence signature, so a rejected
        proposal never re-appears from identical, unchanged evidence; when the evidence changes
        (a new digest, a new statement) the key changes and a fresh proposal is allowed.
        """
        now = time.time()
        value_json = json.dumps(value, ensure_ascii=False, sort_keys=True)
        evidence = evidence or {}
        key = self._proposal_key(kind, type, topic, value_json, evidence.get('sig'))
        existing = db.execute('SELECT * FROM memory_proposals WHERE dedupe_key=?'
                              ' ORDER BY updated DESC LIMIT 1', (key,)).fetchone()
        if existing is not None:
            if existing['state'] in ('pending', 'deferred', 'accepted', 'rejected'):
                return {'id': existing['id'], 'state': existing['state'],
                        'suppressed': existing['state'] == 'rejected'}
        snapshot = None
        if current_id:
            row = db.execute('SELECT * FROM memories WHERE id=? AND project_id=?',
                             (current_id, project_id)).fetchone()
            if row is None:
                raise PolicyError('Proposal target is not in this project')
            if row['status'] not in ('active', 'stale'):
                return {'id': None, 'state': 'no_target'}
            if kind not in ('stale', 'conflict') and row['value'] == value_json:
                return {'id': None, 'state': 'no_change'}
            snapshot = json.dumps({'summary': row['summary'], 'value': row['value'],
                                   'status': row['status'], 'updated': row['updated']}, sort_keys=True)
        db.execute("UPDATE memory_proposals SET state='superseded', updated=?,"
                   " note='a newer proposal replaced this one'"
                   ' WHERE project_id=? AND type=? AND topic=? AND state IN (?,?) AND dedupe_key<>?',
                   (now, project_id, type, topic, 'pending', 'deferred', key))
        proposal_id = uid()
        db.execute('INSERT INTO memory_proposals(id,project_id,kind,type,topic,value,summary,why,'
                   'current_id,current_snapshot,evidence,dedupe_key,state,source_ref,created,updated,'
                   'decided_at,decided_by,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (proposal_id, project_id, kind, type, topic, value_json, summary, why,
                    current_id, snapshot, json.dumps(evidence, sort_keys=True), key, 'pending',
                    source_ref, now, now, None, None, ''))
        self._event(db, project_id, proposal_id, 'proposed', actor,
                    {'kind': kind, 'topic': topic, 'why': why[:300]})
        return {'id': proposal_id, 'state': 'pending', 'suppressed': False}

    def propose_change(self, project_id, *, kind, type, topic, value, summary, why,
                       current_id=None, evidence=None, source_ref='', actor='kel'):
        """Queue a change for the user's review; nothing is applied until it is accepted."""
        if kind not in PROPOSAL_KINDS:
            raise PolicyError('Unknown proposal kind')
        if type not in TYPES:
            raise PolicyError('Unknown memory type')
        if not isinstance(topic, str) or not topic.strip() or len(topic) > 200:
            raise PolicyError('Topic must be 1 to 200 characters')
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
            raise PolicyError('Summary must be 1 to 2000 characters')
        if not isinstance(why, str) or not why.strip() or len(why) > 500:
            raise PolicyError('A proposal needs a plain-language reason (up to 500 characters)')
        if not isinstance(source_ref, str) or len(source_ref) > 2000:
            raise PolicyError('Source reference must be a string up to 2000 characters')
        evidence = evidence or {}
        if not isinstance(evidence, dict):
            raise PolicyError('Proposal evidence must be a JSON object')
        try:
            raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            raise PolicyError('Memory value must be JSON-serializable')
        if len(raw.encode('utf-8')) > 20000:
            raise PolicyError('Memory value is too large')
        if len(json.dumps(evidence, sort_keys=True).encode('utf-8')) > 4000:
            raise PolicyError('Proposal evidence is too large')
        for text in (raw, summary, topic, why):
            scan = scan_secret(text)
            if scan:
                self._refuse(project_id, actor, scan)
        with self.store.transaction() as db:
            self._require_project(db, project_id)
            return self._propose_db(db, project_id, kind=kind, type=type, topic=topic,
                                    value=value, summary=summary, why=why,
                                    current_id=current_id, evidence=evidence,
                                    source_ref=source_ref, actor=actor)

    def _proposal_dict(self, row):
        item = dict(row)
        item['evidence'] = json.loads(row['evidence']) if row['evidence'] else {}
        item['current'] = json.loads(row['current_snapshot']) if row['current_snapshot'] else None
        item['value'] = json.loads(row['value']) if row['value'] else None
        return item

    def proposal(self, proposal_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM memory_proposals WHERE id=?',
                             (proposal_id,)).fetchone()
        if not row:
            raise PolicyError('Proposal not found')
        return self._proposal_dict(row)

    def _sync_proposals(self, project_id):
        """Deferred/pending proposals whose target no longer applies become superseded."""
        now = time.time()
        with self.store.transaction() as db:
            rows = db.execute("SELECT * FROM memory_proposals WHERE project_id=?"
                              " AND state IN (?,?)", (project_id, 'pending', 'deferred')).fetchall()
            for row in rows:
                reason = None
                evidence = json.loads(row['evidence']) if row['evidence'] else {}
                if row['kind'] == 'conflict':
                    c = db.execute('SELECT state FROM memory_conflicts WHERE id=?',
                                   (evidence.get('conflict_id'),)).fetchone()
                    if not c or c['state'] != 'open':
                        reason = 'the disagreement was already settled'
                if row['current_id']:
                    cur = db.execute('SELECT * FROM memories WHERE id=?',
                                     (row['current_id'],)).fetchone()
                    if not cur or cur['status'] not in ('active', 'stale'):
                        reason = 'the record it referred to is no longer current'
                    elif row['current_snapshot']:
                        old = json.loads(row['current_snapshot'])
                        if (str(cur['summary']) != str(old.get('summary'))
                                or str(cur['value']) != str(old.get('value'))):
                            reason = 'the record changed after this proposal was made'
                if reason:
                    db.execute("UPDATE memory_proposals SET state='superseded', updated=?,"
                               ' note=? WHERE id=?', (now, reason, row['id']))

    def proposals(self, project_id, *, state=None, limit=200):
        """The review queue for one project (newest first). `state='open'` = pending + deferred."""
        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise PolicyError('Limit must be 1 to 1000')
        self._sync_proposals(project_id)
        with contextlib.closing(self.store.connect()) as db:
            sql = 'SELECT * FROM memory_proposals WHERE project_id=?'
            args = [project_id]
            if state == 'open':
                sql += ' AND state IN (?,?)'
                args += ['pending', 'deferred']
            elif state:
                sql += ' AND state=?'
                args.append(state)
            sql += ' ORDER BY updated DESC, id ASC LIMIT ?'
            args.append(limit)
            return [self._proposal_dict(r) for r in db.execute(sql, args)]

    def _reconfirm(self, memory_id, evidence, actor='user'):
        """Accept a 'still true' judgment for a stale record: a refreshed record supersedes it."""
        now = time.time()
        with contextlib.closing(self.store.connect()) as db:
            old = self._get(db, memory_id)
            if old['status'] not in ('active', 'stale'):
                raise PolicyError('Only an active or stale memory can be re-confirmed')
        digest = str((evidence or {}).get('digest') or '')[:128] or old['source_digest']
        new_id = uid()
        with self.store.transaction() as db:
            db.execute('INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (new_id, old['project_id'], old['type'], old['topic'], old['value'],
                        old['summary'], 'user_confirmation', old['source_ref'], actor, 2, None, 1,
                        'active', old['id'], None, digest, now, now, None))
            db.execute("UPDATE memories SET status='superseded', superseded_by=?, updated=?"
                       ' WHERE id=?', (new_id, now, memory_id))
            if self.fts:
                db.execute('INSERT INTO memories_fts(topic,summary,value,mid) VALUES(?,?,?,?)',
                           (old['topic'], old['summary'], old['value'], new_id))
            self._event(db, old['project_id'], old['id'], 'revalidated', actor,
                        {'state': 'confirmed'})
            self._event(db, old['project_id'], new_id, 'created', actor, {'reconfirms': memory_id})
        return new_id

    def accept_proposal(self, proposal_id, actor='user', note=''):
        """Apply a proposed change through the normal trust model; preserves the previous value."""
        row = self.proposal(proposal_id)
        if row['state'] not in ('pending', 'deferred'):
            raise PolicyError('This proposal is already %s' % row['state'])
        project_id = row['project_id']
        self._sync_proposals(project_id)
        row = self.proposal(proposal_id)
        if row['state'] not in ('pending', 'deferred'):
            return {'state': row['state'], 'note': row['note']}
        kind = row['kind']
        evidence = row['evidence'] or {}
        if kind == 'conflict':
            try:
                resolution = self.resolve_conflict(evidence.get('conflict_id'), 'b', actor=actor)
            except PolicyError:
                self._sync_proposals(project_id)
                return {'state': 'superseded'}
            decision = {'state': 'accepted', 'kind': kind, 'resolution': resolution}
        else:
            target = row['current_id']
            if target:
                with contextlib.closing(self.store.connect()) as db:
                    cur = db.execute('SELECT * FROM memories WHERE id=?', (target,)).fetchone()
                if not cur or cur['status'] not in ('active', 'stale'):
                    self._sync_proposals(project_id)
                    return {'state': 'superseded'}
                if kind == 'stale':
                    new_id = self._reconfirm(target, evidence, actor)
                elif cur['status'] != 'active':
                    with self.store.transaction() as db:
                        db.execute("UPDATE memory_proposals SET state='superseded', updated=?,"
                                   " note='the record needs re-checking first' WHERE id=?",
                                   (time.time(), proposal_id))
                    return {'state': 'superseded'}
                elif cur['value'] == json.dumps(row['value'], ensure_ascii=False, sort_keys=True):
                    new_id = target  # the record already says exactly this; nothing to change
                else:
                    new_id = self.correct(target, value=row['value'], summary=row['summary'],
                                          actor=actor)
            else:
                new_id = self.record(project_id, row['type'], row['topic'], row['value'],
                                     row['summary'], source_type='user_confirmation', actor=actor,
                                     user_confirmed=1, source_ref=row['source_ref'])
            decision = {'state': 'accepted', 'kind': kind, 'memory': new_id}
        now = time.time()
        with self.store.transaction() as db:
            db.execute("UPDATE memory_proposals SET state='accepted', updated=?, decided_at=?,"
                       ' decided_by=?, note=? WHERE id=? AND state IN (?,?)',
                       (now, now, actor, note or '', proposal_id, 'pending', 'deferred'))
            self._event(db, project_id, proposal_id, 'proposal_accepted', actor,
                        {'kind': kind, 'topic': row['topic'],
                         'memory': decision.get('memory') or decision.get('resolution')})
        return decision

    def reject_proposal(self, proposal_id, actor='user', reason=''):
        """Turn a change down. The same evidence will not ask again until it changes."""
        row = self.proposal(proposal_id)
        if row['state'] not in ('pending', 'deferred'):
            raise PolicyError('This proposal is already %s' % row['state'])
        if row['kind'] == 'conflict':
            # "Keep both as they are": settle the disagreement as dismissed; memory is unchanged.
            try:
                self.resolve_conflict((row['evidence'] or {}).get('conflict_id'), 'dismiss', actor=actor)
            except PolicyError:
                pass  # it was settled elsewhere in the meantime
        now = time.time()
        with self.store.transaction() as db:
            db.execute("UPDATE memory_proposals SET state='rejected', updated=?, decided_at=?,"
                       ' decided_by=?, note=? WHERE id=?',
                       (now, now, actor, str(reason)[:500], proposal_id))
            self._event(db, row['project_id'], proposal_id, 'proposal_rejected', actor,
                        {'kind': row['kind'], 'topic': row['topic']})
        return proposal_id

    def defer_proposal(self, proposal_id, actor='user', note=''):
        row = self.proposal(proposal_id)
        if row['state'] not in ('pending', 'deferred'):
            raise PolicyError('This proposal is already %s' % row['state'])
        now = time.time()
        with self.store.transaction() as db:
            db.execute("UPDATE memory_proposals SET state='deferred', updated=?, note=? WHERE id=?",
                       (now, str(note)[:500], proposal_id))
            self._event(db, row['project_id'], proposal_id, 'proposal_deferred', actor,
                        {'kind': row['kind'], 'topic': row['topic']})
        return proposal_id

    def history_view(self, project_id, *, limit=50):
        """Plain-language project timeline: what changed in Kel's understanding of this project."""
        if not isinstance(limit, int) or not 1 <= limit <= 200:
            raise PolicyError('Limit must be 1 to 200')
        summaries = {}

        def summarize(mid):
            if mid not in summaries:
                with contextlib.closing(self.store.connect()) as db:
                    found = db.execute('SELECT summary FROM memories WHERE id=?', (mid,)).fetchone()
                summaries[mid] = found['summary'] if found else 'a record'
            return summaries[mid]

        def proposal_summary(pid):
            with contextlib.closing(self.store.connect()) as db:
                found = db.execute('SELECT summary FROM memory_proposals WHERE id=?', (pid,)).fetchone()
            return found['summary'] if found else 'a change'

        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT * FROM memory_events WHERE project_id=? ORDER BY seq DESC LIMIT 400',
                              (project_id,)).fetchall()
        entries = []
        for e in rows:
            if len(entries) >= limit:
                break
            action = e['action']
            detail = json.loads(e['detail']) if e['detail'] else {}
            text = None
            if action == 'created':
                if detail.get('reconfirms'):
                    text = 'You re-confirmed “%s”' % summarize(e['memory_id'])
                elif not detail.get('corrects'):
                    text = 'Added “%s”' % summarize(e['memory_id'])
            elif action == 'confirmed':
                text = 'You confirmed “%s”' % summarize(e['memory_id'])
            elif action == 'corrected':
                text = 'You changed “%s” to “%s”' % (summarize(e['memory_id']),
                                                     summarize(detail.get('superseded_by', '')))
            elif action == 'superseded':
                text = 'Replaced “%s” with “%s”' % (summarize(e['memory_id']),
                                                    summarize(detail.get('superseded_by', '')))
            elif action == 'retracted':
                text = 'Marked as wrong: “%s”' % summarize(e['memory_id'])
            elif action == 'forgotten':
                text = 'Forgotten a record (content removed)'
            elif action == 'stale':
                text = 'Out of date: “%s”' % summarize(e['memory_id'])
            elif action == 'proposal_accepted':
                text = 'You accepted the change: “%s”' % proposal_summary(e['memory_id'])
            elif action == 'proposal_rejected':
                text = 'You turned the change down: “%s”' % proposal_summary(e['memory_id'])
            if text:
                entries.append({'at': e['at'], 'text': text, 'action': action,
                                'memory_id': e['memory_id']})
        return entries
    def revalidate(self, project_id, digest_map):
        """Compare stored source digests to current digests; mark changed records stale."""
        if not isinstance(digest_map, dict):
            raise PolicyError('Digest map must map source references to digests')
        stale = []
        now = time.time()
        with self.store.transaction() as db:
            rows = db.execute(
                "SELECT * FROM memories WHERE project_id=? AND status='active'"
                ' AND source_digest IS NOT NULL', (project_id,)).fetchall()
            for row in rows:
                current = digest_map.get(row['source_ref'])
                if current is None:
                    continue
                if current == row['source_digest']:
                    db.execute('UPDATE memories SET checked_at=? WHERE id=?', (now, row['id']))
                    self._event(db, project_id, row['id'], 'revalidated', 'kel', {'state': 'ok'})
                else:
                    db.execute("UPDATE memories SET status='stale', checked_at=?, updated=?"
                               ' WHERE id=?', (now, now, row['id']))
                    self._event(db, project_id, row['id'], 'stale', 'kel',
                                {'reason': 'source changed',
                                 'was': str(row['source_digest'])[:16],
                                 'now': str(current)[:16]})
                    self._propose_db(db, project_id, kind='stale', type=row['type'],
                                     topic=row['topic'], value=json.loads(row['value']),
                                     summary=row['summary'],
                                     why='The source behind this knowledge changed — confirm it is still true.',
                                     current_id=row['id'],
                                     evidence={'digest': str(current)[:128],
                                               'source_ref': row['source_ref'],
                                               'sig': str(current)[:128]},
                                     source_ref=row['source_ref'])
                    stale.append(row['id'])
        return stale

    def _search_ids(self, db, query):
        phrase = '"' + str(query).replace('"', '""')[:200] + '"'
        try:
            rows = db.execute('SELECT mid FROM memories_fts WHERE memories_fts MATCH ?',
                              (phrase,)).fetchall()
        except sqlite3.OperationalError:
            return None  # malformed query or no FTS table: caller falls back to LIKE
        return [r['mid'] for r in rows]

    def select(self, project_id, *, purpose='context', query=None, types=None, topic=None,
               limit=12, max_chars=6000, include_unconfirmed=False):
        """Authority-ordered, project-scoped selection for context assembly."""
        if not isinstance(purpose, str) or not purpose:
            raise PolicyError('Select needs a purpose')
        if type(limit) is not int or not 1 <= limit <= 100:
            raise PolicyError('Limit must be 1 to 100')
        if type(max_chars) is not int or not 1 <= max_chars <= 100000:
            raise PolicyError('Size budget must be 1 to 100000')
        with contextlib.closing(self.store.connect()) as db:
            sql = "SELECT * FROM memories WHERE project_id=? AND status='active'"
            args = [project_id]
            if types:
                types = list(types)
                sql += ' AND type IN (' + ','.join('?' * len(types)) + ')'
                args += types
            if topic:
                sql += ' AND topic=?'
                args.append(topic)
            if not include_unconfirmed:
                sql += ' AND trust<=5'
            if query:
                ids = self._search_ids(db, query) if self.fts else None
                if ids is None:
                    escaped = str(query).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                    like = '%' + escaped[:200] + '%'
                    sql += " AND (topic LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\'"
                    sql += " OR value LIKE ? ESCAPE '\\')"
                    args += [like, like, like]
                elif not ids:
                    return []
                else:
                    sql += ' AND id IN (' + ','.join('?' * len(ids)) + ')'
                    args += ids
            sql += ' ORDER BY trust ASC, updated DESC, id ASC LIMIT 200'
            candidates = db.execute(sql, args).fetchall()
        chosen, used = [], 0
        for row in candidates:
            if len(chosen) >= limit:
                break
            size = len(row['summary']) + len(row['value'])
            if chosen and used + size > max_chars:
                break
            used += size
            chosen.append(dict(row))
        return chosen

    def history(self, memory_id):
        """Full supersession chain (both directions), oldest first."""
        with contextlib.closing(self.store.connect()) as db:
            seen, order, stack = set(), [], [memory_id]
            while stack:
                mid = stack.pop()
                if mid in seen:
                    continue
                row = db.execute('SELECT * FROM memories WHERE id=?', (mid,)).fetchone()
                if not row:
                    continue
                seen.add(mid)
                order.append(dict(row))
                if row['supersedes']:
                    stack.append(row['supersedes'])
                if row['superseded_by']:
                    stack.append(row['superseded_by'])
            order.sort(key=lambda item: item['created'])
            return order

    def conflicts(self, project_id, *, state='open'):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(r) for r in db.execute(
                'SELECT * FROM memory_conflicts WHERE project_id=? AND state=? ORDER BY at DESC',
                (project_id, state))]

    def records(self, project_id, *, status=None, type=None, limit=200):
        """Inspection listing (newest first); used by the Work-context surface."""
        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise PolicyError('Limit must be 1 to 1000')
        with contextlib.closing(self.store.connect()) as db:
            sql = 'SELECT * FROM memories WHERE project_id=?'
            args = [project_id]
            if status:
                sql += ' AND status=?'
                args.append(status)
            if type:
                sql += ' AND type=?'
                args.append(type)
            sql += ' ORDER BY updated DESC, id ASC LIMIT ?'
            args.append(limit)
            return [dict(r) for r in db.execute(sql, args)]
