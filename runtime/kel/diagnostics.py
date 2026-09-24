"""Diagnostics, maintenance, and performance measurement (V1.4 migration 009).

Design: docs/v1.4/KEL_V1.4_ARCHITECTURE.md §2 (diagnostics tables) and the sanitizer rules in
KEL_V1.4_SECURITY_MODEL.md §5. Everything here is measured from real state — process liveness from
`native_processes`, run health from the `runs` table and its fence, provider state from `providers`,
database health from SQLite pragmas. The export is built from an ALLOWLIST, never by filtering a dump.
"""
import contextlib
import json
import os
import sqlite3
import time
from pathlib import Path

from .core import PolicyError, encode, uid
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 9
MIGRATION_NAME = 'v14-diagnostics'

DDL = """
CREATE TABLE IF NOT EXISTS startup_spans(
  id TEXT PRIMARY KEY, at REAL NOT NULL, engine_version TEXT, phase TEXT NOT NULL,
  duration_ms REAL NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS health_observations(
  id TEXT PRIMARY KEY, at REAL NOT NULL, subject TEXT NOT NULL, state TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS process_observations(
  id TEXT PRIMARY KEY, at REAL NOT NULL, pid INTEGER, kind TEXT NOT NULL, owned INTEGER NOT NULL,
  alive INTEGER NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS performance_measurements(
  id TEXT PRIMARY KEY, at REAL NOT NULL, name TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
  basis TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS retention_settings(
  key TEXT PRIMARY KEY, days REAL NOT NULL, updated REAL NOT NULL);
"""

RETENTION_KEYS = ('events', 'health_observations', 'process_observations', 'performance_measurements',
                  'provider_observations', 'startup_spans')
DEFAULT_RETENTION = {'events': 30.0, 'health_observations': 14.0, 'process_observations': 7.0,
                     'performance_measurements': 30.0, 'provider_observations': 30.0,
                     'startup_spans': 14.0}

# Everything the export is allowed to carry. Nothing else is ever included.
EXPORT_ALLOWLIST = (
    'schema', 'generated_at', 'engine_version', 'counts', 'database', 'runs', 'jobs', 'providers',
    'processes', 'performance', 'retention', 'receipt',
)
EXPORT_EXCLUSIONS = (
    'prompts and message bodies', 'conversation transcripts', 'file contents and workspace paths',
    'credentials, tokens and API keys', 'environment dumps', 'memory record values',
    'task artifacts and evidence bodies', 'screenshots',
)
SECRET_MARKERS = ('sk-', 'bearer ', 'api_key', 'apikey', 'token=', 'password', '-----begin')


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return True
        first = not _table(db, 'schema_migrations')
        if first:
            if not _is_fresh_database(db):
                _backup(store, db)
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        db.executescript(DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), 'tables=5'))
        return True


def _pid_alive(pid):
    """Inspect a recorded process without sending a signal on Windows."""
    try:
        pid = int(pid)
    except (ValueError, TypeError, OverflowError):
        return False
    if pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        if pid > 0xffffffff:
            return False
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # Access denied still indicates a process.
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False
    except (ValueError, TypeError):
        return False


def _policy_summary(db):
    """V1.5 authorization posture: policy version, decision roll-up, and a bounded recent tail.

    Degrades to empty results on a database that predates the authorization migration and never
    raises: the snapshot is the one surface a user consults when something is wrong."""
    try:
        from .authorize import POLICY_VERSION
        if not _table(db, 'guardrail_decisions'):
            return {'version': POLICY_VERSION, 'by_decision': {}, 'recent': []}
        by_decision = {decision: count for decision, count in db.execute(
            'SELECT decision, COUNT(*) FROM guardrail_decisions GROUP BY decision').fetchall()}
        recent = [{'at': row['at'], 'decision': row['decision'], 'rule': row['rule'],
                   'reason': row['reason'], 'actor': row['actor'], 'job_id': row['job_id'],
                   'action_kind': row['action_kind'], 'policy_version': row['policy_version']}
                  for row in db.execute(
                      'SELECT * FROM guardrail_decisions ORDER BY at DESC LIMIT 10').fetchall()]
        return {'version': POLICY_VERSION, 'by_decision': by_decision, 'recent': recent}
    except Exception as exc:  # pragma: no cover - defensive; a broken snapshot helps nobody
        return {'version': None, 'by_decision': {}, 'recent': [], 'error': str(exc)}


def _lease_summary(db):
    """Live capability-lease states, for the same reason as the policy summary."""
    if not _table(db, 'capability_leases'):
        return {}
    return {state: count for state, count in db.execute(
        'SELECT state, COUNT(*) FROM capability_leases GROUP BY state').fetchall()}


def _migrations(db):
    if not _table(db, 'schema_migrations'):
        return []
    return [{'version': row['version'], 'name': row['name']}
            for row in db.execute(
                'SELECT version, name FROM schema_migrations ORDER BY version').fetchall()]


class Diagnostics:
    def __init__(self, store, engine_version=''):
        self.store = store
        ensure_schema(store)
        self.engine_version = engine_version

    # -- recording -------------------------------------------------------------------------------
    def record_startup(self, phase, duration_ms, detail=None):
        phase = str(phase or '').strip()
        if not phase:
            raise PolicyError('A startup span needs a phase name')
        with self.store.transaction() as db:
            db.execute('INSERT INTO startup_spans VALUES(?,?,?,?,?,?)',
                       (uid(), time.time(), self.engine_version, phase, float(duration_ms),
                        encode(detail) if detail else None))
        return {'phase': phase, 'duration_ms': float(duration_ms)}

    def measure(self, name, value, unit='ms', basis='measured', detail=None):
        name = str(name or '').strip()
        if not name:
            raise PolicyError('A measurement needs a name')
        if basis not in ('measured', 'estimated', 'unknown'):
            raise PolicyError('Basis must be measured, estimated or unknown')
        with self.store.transaction() as db:
            db.execute('INSERT INTO performance_measurements VALUES(?,?,?,?,?,?,?)',
                       (uid(), time.time(), name, float(value), unit, basis,
                        encode(detail) if detail else None))
        return {'name': name, 'value': float(value), 'unit': unit, 'basis': basis}

    def observe(self, subject='overall'):
        snapshot = self.snapshot()
        state = 'ok' if not snapshot['database']['problems'] and not snapshot['runs']['expired_unfenced'] else 'attention'
        with self.store.transaction() as db:
            db.execute('INSERT INTO health_observations VALUES(?,?,?,?,?)',
                       (uid(), time.time(), subject, state, encode(snapshot)))
        return {'subject': subject, 'state': state, 'snapshot': snapshot}

    # -- measurement -----------------------------------------------------------------------------
    def snapshot(self):
        with contextlib.closing(self.store.connect()) as db:
            integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
            page_size = db.execute('PRAGMA page_size').fetchone()[0]
            page_count = db.execute('PRAGMA page_count').fetchone()[0]
            freelist = db.execute('PRAGMA freelist_count').fetchone()[0]
            policy = _policy_summary(db)
            leases = _lease_summary(db)
            migrations = _migrations(db)
            # Jobs keep their state inside the JSON payload (jobs(id, revision, data)), unlike runs.
            jobs = {}
            for row in db.execute('SELECT data FROM jobs').fetchall():
                state = json.loads(row['data']).get('state', 'UNKNOWN')
                jobs[state] = jobs.get(state, 0) + 1
            runs = dict(db.execute('SELECT state, COUNT(*) FROM runs GROUP BY state').fetchall())
            expired = db.execute('SELECT COUNT(*) FROM runs WHERE state IN '
                                 "('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED') AND expires<?",
                                 (time.time(),)).fetchone()[0]
            # native_processes is created lazily by the runner, so a snapshot must work without it.
            if _table(db, 'native_processes'):
                processes = [dict(row) for row in db.execute(
                    'SELECT run_id, pid, identity, deadline FROM native_processes').fetchall()]
            else:
                processes = []
            providers = {}
        for row in processes:
            row['alive'] = _pid_alive(row['pid'])
            row['past_deadline'] = bool(row['deadline'] and row['deadline'] < time.time())
        try:
            providers = {name: {'failures': state.get('failures', 0),
                                'circuit_until': state.get('circuit_until', 0),
                                'quota': state.get('quota'),
                                'quota_unit': state.get('quota_unit'),
                                'quota_observed_at': state.get('quota_observed_at'),
                                'quota_reset': state.get('quota_reset'),
                                'quota_source': state.get('quota_source'),
                                'latency': state.get('latency'),
                                'quality': state.get('quality')}
                         for name, state in (self.store.provider_states() or {}).items()}
        except Exception:
            providers = {}
        db_path = Path(self.store.root) / 'kel.sqlite3'
        wal_path = Path(str(db_path) + '-wal')
        problems = []
        if integrity != 'ok':
            problems.append('integrity_check: %s' % integrity)
        if expired:
            problems.append('%d run(s) past their fence (orphan candidates)' % expired)
        if any(not row['alive'] for row in processes):
            problems.append('%d recorded process(es) are no longer alive' % sum(
                1 for row in processes if not row['alive']))
        return {
            'engine_version': self.engine_version,
            'counts': {'jobs': sum(jobs.values()), 'runs': sum(runs.values())},
            'database': {
                'integrity': integrity,
                'size_bytes': db_path.stat().st_size if db_path.exists() else 0,
                'wal_bytes': wal_path.stat().st_size if wal_path.exists() else 0,
                'page_size': page_size,
                'page_count': page_count,
                'freelist_pages': freelist,
                'fragmentation_percent': round((freelist / page_count) * 100, 2) if page_count else 0.0,
                'problems': problems,
            },
            'jobs': jobs,
            'runs': {'by_state': runs, 'expired_unfenced': expired},
            'policy': policy,
            'leases': leases,
            'migrations': migrations,
            'providers': providers,
            'processes': processes,
        }

    def performance(self, limit=50):
        with contextlib.closing(self.store.connect()) as db:
            spans = [dict(row) for row in db.execute(
                'SELECT at, phase, duration_ms, engine_version FROM startup_spans '
                'ORDER BY at DESC LIMIT ?', (limit,)).fetchall()]
            measurements = [dict(row) for row in db.execute(
                'SELECT at, name, value, unit, basis FROM performance_measurements '
                'ORDER BY at DESC LIMIT ?', (limit,)).fetchall()]
        startup = {}
        for span in spans:
            startup[span['phase']] = min(startup.get(span['phase'], span['duration_ms']),
                                         span['duration_ms'])
        return {
            'startup_spans': spans,
            'slowest_phase_ms': startup,
            'measurements': measurements,
            'basis': 'measured from recorded spans; phases not recorded are simply unknown',
        }

    # -- retention and maintenance ---------------------------------------------------------------
    def retention(self):
        with contextlib.closing(self.store.connect()) as db:
            rows = {row['key']: row['days'] for row in db.execute(
                'SELECT key, days FROM retention_settings').fetchall()}
        return {key: rows.get(key, DEFAULT_RETENTION[key]) for key in RETENTION_KEYS}

    def set_retention(self, key, days):
        if key not in RETENTION_KEYS:
            raise PolicyError('Unknown retention key: %s' % key)
        days = float(days)
        if days < 0:
            raise PolicyError('Retention days cannot be negative')
        with self.store.transaction() as db:
            db.execute('INSERT INTO retention_settings VALUES(?,?,?) '
                       'ON CONFLICT(key) DO UPDATE SET days=excluded.days, updated=excluded.updated',
                       (key, days, time.time()))
        return {key: days}

    def purge(self):
        """Delete observation rows past their window. Jobs, runs, memories, approvals, receipts and
        artifacts are never touched — only the diagnostic streams this module owns."""
        windows = self.retention()
        removed = {}
        with self.store.transaction() as db:
            for key in RETENTION_KEYS:
                days = windows[key]
                if days <= 0:
                    removed[key] = 0
                    continue
                cutoff = time.time() - days * 86400
                table = key
                if not _table(db, table):
                    removed[key] = 0
                    continue
                column = 'at'
                before = db.execute('SELECT COUNT(*) FROM %s WHERE %s<?' % (table, column),
                                    (cutoff,)).fetchone()[0]
                db.execute('DELETE FROM %s WHERE %s<?' % (table, column), (cutoff,))
                removed[key] = before
            db.execute('DELETE FROM events WHERE at<?', (time.time() - windows['events'] * 86400,))
            removed['events'] = removed.get('events', 0)
        return {'removed': removed, 'retention_days': windows}

    def compact(self):
        """VACUUM after a backup — never the only copy of anything."""
        before = self.snapshot()['database']
        # The connection handed to _backup must be closed: a lingering handle keeps the database
        # locked on Windows and would block the next vacuum or backup.
        with contextlib.closing(self.store.connect()) as handle:
            _backup(self.store, handle)
        with contextlib.closing(sqlite3.connect(str(Path(self.store.root) / 'kel.sqlite3'))) as db:
            db.execute('VACUUM')
            db.execute('PRAGMA optimize')
        after = self.snapshot()['database']
        return {'before_bytes': before['size_bytes'], 'after_bytes': after['size_bytes'],
                'integrity': after['integrity'], 'backup': 'written before vacuum'}

    # -- export and issue report ------------------------------------------------------------------
    def _sanitize(self, value, trail=()):
        if isinstance(value, str):
            lowered = value.lower()
            for marker in SECRET_MARKERS:
                if marker in lowered:
                    raise PolicyError('Refusing to export a value that looks like a secret (%s)' % marker)
            return value
        if isinstance(value, dict):
            clean = {}
            for key, item in value.items():
                if key not in EXPORT_ALLOWLIST and trail and trail[0] != 'providers':
                    continue
                if any(marker in str(key).lower() for marker in SECRET_MARKERS):
                    raise PolicyError('Refusing to export a field named like a secret (%s)' % key)
                clean[key] = self._sanitize(item, trail + (key,))
            return clean
        if isinstance(value, (list, tuple)):
            return [self._sanitize(item, trail) for item in value]
        return value

    def export(self):
        snapshot = self.snapshot()
        payload = self._sanitize({
            'engine_version': self.engine_version,
            'counts': snapshot['counts'],
            'database': snapshot['database'],
            'runs': snapshot['runs'],
            'jobs': snapshot['jobs'],
            'providers': snapshot['providers'],
            'processes': snapshot['processes'],
            'performance': {'slowest_phase_ms': self.performance()['slowest_phase_ms']},
            'retention': self.retention(),
        })
        receipt = {'included': sorted(payload.keys()), 'excluded': list(EXPORT_EXCLUSIONS),
                   'generated_at': time.time(), 'basis': 'allowlist; sanity-checked for secret shapes'}
        payload['receipt'] = receipt
        payload['schema'] = 1
        return payload

    def _redact_note(self, note):
        """A report is meant to be shareable: redact secret-shaped tokens in the user's own note
        instead of refusing to write the file (the export path raises; this path salvages)."""
        changed = False
        tokens = []
        for token in str(note).split(' '):
            if any(marker in token.lower() for marker in SECRET_MARKERS):
                tokens.append('[redacted]')
                changed = True
            else:
                tokens.append(token)
        return ' '.join(tokens), changed

    def issue_report(self, note='', folder=None):
        payload = self.export()
        stamp = time.strftime('%Y%m%d-%H%M%S')
        target = Path(folder) if folder else (Path(self.store.root) / 'diagnostics')
        target.mkdir(parents=True, exist_ok=True)
        path = target / ('issue-report-%s.md' % stamp)
        safe_note, redacted = self._redact_note(note)
        lines = ['# Kel issue report', '', 'Generated locally: %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
                 '', '## Your note', '', safe_note.strip() or '(none)']
        if redacted:
            lines += ['', 'Secret-shaped text in your note was redacted before writing this file.']
        lines += ['', '## Diagnostics (sanitized)',
                  '', '```json', json.dumps(payload, indent=2, default=str), '```', '',
                  'Nothing here is sent anywhere: this file stays in your Kel data folder.']
        path.write_text('\n'.join(lines), encoding='utf-8')
        return {'path': str(path), 'bytes': path.stat().st_size, 'redacted': redacted,
                'excluded': payload['receipt']['excluded']}

    # -- service envelope -------------------------------------------------------------------------
    def apply(self, data):
        action = data.get('action')
        if action == 'observe':
            return self.observe(data.get('subject', 'overall'))
        if action == 'snapshot':
            return self.snapshot()
        if action == 'performance':
            return self.performance()
        if action == 'retention':
            return {'retention_days': self.retention()}
        if action == 'set_retention':
            return self.set_retention(data['key'], data['days'])
        if action == 'purge':
            return self.purge()
        if action == 'compact':
            return self.compact()
        if action == 'export':
            return self.export()
        if action == 'report':
            return self.issue_report(data.get('note', ''))
        if action == 'measure':
            return self.measure(data['name'], data['value'], data.get('unit', 'ms'),
                                data.get('basis', 'measured'), data.get('detail'))
        if action == 'startup':
            return self.record_startup(data['phase'], data['duration_ms'], data.get('detail'))
        raise PolicyError('Unknown diagnostics action: %s' % action)
