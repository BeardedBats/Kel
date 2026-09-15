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
import json
import re
import sqlite3
import time

from .core import PolicyError, uid

MIGRATION_VERSION = 1
MIGRATION_NAME = 'v13-memory'

TYPES = ('fact', 'decision', 'convention', 'preference', 'command', 'path', 'component',
         'relationship', 'limitation', 'workflow', 'question', 'observation')

SOURCE_TRUST = {
    'user_instruction': 2,
    'user_confirmation': 2,
    'repo_inspection': 3,
    'config_inspection': 3,
    'system': 4,
    'worker_evidence': 5,
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
        probe = ensure_schema(store)
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
                db.execute('INSERT INTO memory_conflicts VALUES(?,?,?,?,?,?,?,?,?)',
                           (uid(), project_id, peer_id, memory_id,
                            'open' if is_open else 'resolved',
                            None if is_open else resolution,
                            None if is_open else 'kel',
                            now, None if is_open else now))
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
        """Purge content and keep a content-free tombstone plus an audit event."""
        with self.store.transaction() as db:
            row = self._get(db, memory_id)
            db.execute('UPDATE memories SET value=?, summary=?, status=?, updated=? WHERE id=?',
                       ('', '', 'retracted', time.time(), memory_id))
            if self.fts:
                db.execute('DELETE FROM memories_fts WHERE mid=?', (memory_id,))
            self._event(db, row['project_id'], memory_id, 'forgotten', actor, None)
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
        if type(limit) is not int or not 1 <= limit <= 1000:
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
