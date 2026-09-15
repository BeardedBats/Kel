"""Capability leases, boundary expansion, and guardrail enforcement (V1.4 migration 008).

Design: docs/v1.4/KEL_V1.4_AUTONOMY_POLICY.md. Rules enforced here, not by convention:

- A lease can only be issued for a **reviewed plan** (`review_ref` is required).
- Every check **fails closed**: unknown lease, expired lease, unknown kind, blocked kind, frozen path,
  or a target outside the granted scope is denied and recorded in `lease_events`.
- Registry / OS-critical / credential / GitHub-admin kinds are refused unconditionally with the matching
  guardrail rule id.
- Destructive actions require a snapshot reference (the rollback exists before the action runs).
- Boundary expansion is asked **once** and resolved only by the user (`actor='user'`).
- `assert_intact()` detects any tampering with `kel.guardrails.RULES`.
"""
import contextlib
import hashlib
import json
import time
from pathlib import Path

from .core import PolicyError, encode, uid
from .guardrails import RULES, locked_block
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 8
MIGRATION_NAME = 'v14-autonomy'

DDL = """
CREATE TABLE IF NOT EXISTS capability_leases(
  lease_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, project_id TEXT NOT NULL,
  profile TEXT NOT NULL, review_ref TEXT NOT NULL, issued_at REAL NOT NULL,
  expires_at REAL NOT NULL, state TEXT NOT NULL, revoked_at REAL, reason TEXT);
CREATE TABLE IF NOT EXISTS lease_scope(
  lease_id TEXT NOT NULL, kind TEXT NOT NULL, value TEXT NOT NULL,
  uses_remaining INTEGER NOT NULL DEFAULT -1, expires_at REAL NOT NULL DEFAULT 0,
  PRIMARY KEY(lease_id, kind, value));
CREATE TABLE IF NOT EXISTS lease_events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, lease_id TEXT,
  kind TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS boundary_expansion_requests(
  request_id TEXT PRIMARY KEY, lease_id TEXT NOT NULL, scope TEXT NOT NULL, target TEXT NOT NULL,
  what TEXT, why TEXT, benefit TEXT, fallback TEXT, risk TEXT, status TEXT NOT NULL,
  grant_kind TEXT, created REAL NOT NULL, resolved_at REAL, actor TEXT);
"""

KINDS = ('read', 'write', 'repo', 'browser', 'tool', 'external', 'destructive')
BLOCKED_KINDS = {
    'registry': 'no-registry-write',
    'system': 'no-os-critical-write',
    'credential': 'credential-boundary',
    'identity': 'no-identity-change',
    'persistence': 'no-covert-persistence',
    'machine_op': 'no-destructive-machine-op',
    'github_admin': 'github-admin-redline',
    'purchase': 'no-purchase-or-communication',
    'policy': 'policy-immutable',
}
FROZEN_MARKERS = ('kel releases', 'kel-v1-frozen', 'kel-v1.1-frozen', 'kel-v1.2-frozen',
                  'kel-v1.3-frozen', 'frozen')
SYSTEM_PREFIXES = ('c:\\windows', 'c:\\program files', 'c:\\program files (x86)', 'c:\\programdata')
GUARDRAIL_DIGEST = hashlib.sha256(json.dumps(RULES, sort_keys=True).encode('utf-8')).hexdigest()


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
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), 'tables=4'))
        return True


def _text(value, label, limit=2000):
    value = str(value or '').strip()
    if not value:
        raise PolicyError('%s is required' % label)
    if len(value) > limit:
        raise PolicyError('%s is too long' % label)
    return value


def _norm(path):
    return str(path or '').replace('/', '\\').lower()


def _frozen(target):
    text = _norm(target)
    return any(marker in text for marker in FROZEN_MARKERS)


def _system(target):
    return any(_norm(target).startswith(prefix) for prefix in SYSTEM_PREFIXES)


class Autonomy:
    def __init__(self, store):
        self.store = store
        ensure_schema(store)

    # ---- guards --------------------------------------------------------------
    def assert_intact(self):
        digest_now = hashlib.sha256(json.dumps(RULES, sort_keys=True).encode('utf-8')).hexdigest()
        if digest_now != GUARDRAIL_DIGEST:
            raise PolicyError('Locked guardrails were modified; refusing to continue')
        return True

    def guardrails(self):
        self.assert_intact()
        return locked_block()

    def _event(self, db, lease_id, kind, detail):
        db.execute('INSERT INTO lease_events(at, lease_id, kind, detail) VALUES(?,?,?,?)',
                   (time.time(), lease_id, kind, encode(detail)))

    def _lease(self, db, lease_id):
        row = db.execute('SELECT * FROM capability_leases WHERE lease_id=?', (lease_id,)).fetchone()
        if not row:
            return None
        return dict(row)

    # ---- issuing -------------------------------------------------------------
    def issue(self, job_id, project_id='default', profile='broad', review_ref='',
              roots=(), repositories=(), domains=(), tools=(), external_actions=(),
              seconds=86400, actor='kel'):
        self.assert_intact()
        _text(job_id, 'job_id')
        review_ref = _text(review_ref, 'review_ref (a reviewed plan is required before a lease exists)')
        resolved = []
        for root in roots:
            path = Path(str(root))
            if not path.exists() or not path.is_dir():
                raise PolicyError('Lease root does not exist: %s' % root)
            if _frozen(root):
                raise PolicyError('Frozen releases are read-only and cannot be leased: %s' % root)
            if _system(root):
                raise PolicyError('System locations cannot be leased: %s' % root)
            resolved.append(str(path.resolve()))
        if not resolved:
            raise PolicyError('A lease needs at least one root')
        lease_id = uid()
        now = time.time()
        with self.store.transaction() as db:
            db.execute('INSERT INTO capability_leases VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (lease_id, job_id, project_id, profile, review_ref, now, now + float(seconds),
                        'ACTIVE', None, None))
            for kind, values in (('root', resolved), ('repo', tuple(repositories)),
                                 ('domain', tuple(domains)), ('tool', tuple(tools)),
                                 ('external', tuple(external_actions))):
                for value in values:
                    db.execute('INSERT OR REPLACE INTO lease_scope VALUES(?,?,?,?,?)',
                               (lease_id, kind, str(value), -1, 0))
            self._event(db, lease_id, 'issued',
                        {'profile': profile, 'review_ref': review_ref, 'roots': resolved,
                         'tools': list(tools), 'domains': list(domains), 'actor': actor})
        return {'lease_id': lease_id, 'expires_at': now + float(seconds), 'roots': resolved}

    def revoke(self, lease_id, reason=''):
        with self.store.transaction() as db:
            if not self._lease(db, lease_id):
                raise PolicyError('Unknown lease')
            db.execute("UPDATE capability_leases SET state='REVOKED', revoked_at=?, reason=? "
                       'WHERE lease_id=?', (time.time(), reason or 'revoked', lease_id))
            self._event(db, lease_id, 'revoked', {'reason': reason})
        return {'lease_id': lease_id, 'state': 'REVOKED'}

    def leases(self, job_id=None):
        with contextlib.closing(self.store.connect()) as db:
            rows = (db.execute('SELECT * FROM capability_leases WHERE job_id=? ORDER BY issued_at',
                               (job_id,)).fetchall() if job_id
                    else db.execute('SELECT * FROM capability_leases ORDER BY issued_at').fetchall())
            out = []
            for row in rows:
                item = dict(row)
                item['expired'] = item['expires_at'] <= time.time()
                item['scope'] = [dict(scope) for scope in db.execute(
                    'SELECT kind, value, uses_remaining FROM lease_scope WHERE lease_id=? '
                    'ORDER BY kind, value', (item['lease_id'],))]
                out.append(item)
            return out

    # ---- enforcement ---------------------------------------------------------
    def check(self, lease_id, kind, target='', tool='', destructive_snapshot=''):
        """Fails closed. Returns {'allowed': bool, 'rule': str, 'reason': str}."""
        self.assert_intact()
        with self.store.transaction() as db:
            lease = self._lease(db, lease_id)
            if not lease:
                self._event(db, lease_id, 'denied', {'kind': kind, 'reason': 'unknown lease'})
                return {'allowed': False, 'rule': 'lease-unknown', 'reason': 'Unknown lease'}
            if lease['state'] != 'ACTIVE':
                self._event(db, lease_id, 'denied', {'kind': kind, 'reason': lease['state']})
                return {'allowed': False, 'rule': 'lease-' + lease['state'].lower(),
                        'reason': 'Lease is %s' % lease['state']}
            if lease['expires_at'] <= time.time():
                self._event(db, lease_id, 'denied', {'kind': kind, 'reason': 'expired'})
                return {'allowed': False, 'rule': 'lease-expired',
                        'reason': 'Lease expired at %s' % lease['expires_at']}
            if kind in BLOCKED_KINDS:
                rule = BLOCKED_KINDS[kind]
                self._event(db, lease_id, 'denied', {'kind': kind, 'rule': rule, 'target': target})
                return {'allowed': False, 'rule': rule, 'reason': 'Locked guardrail: %s' % rule}
            if kind not in KINDS:
                self._event(db, lease_id, 'denied', {'kind': kind, 'reason': 'unknown kind'})
                return {'allowed': False, 'rule': 'kind-unknown', 'reason': 'Unknown action kind'}
            if kind in ('write', 'repo') and _frozen(target):
                self._event(db, lease_id, 'denied', {'kind': kind, 'target': target,
                                                     'rule': 'frozen-immutable'})
                return {'allowed': False, 'rule': 'frozen-immutable',
                        'reason': 'Frozen releases and their manifests are read-only'}
            if kind == 'destructive' and not str(destructive_snapshot).strip():
                self._event(db, lease_id, 'denied', {'kind': kind, 'rule': 'destructive-snapshot'})
                return {'allowed': False, 'rule': 'destructive-snapshot',
                        'reason': 'A snapshot or backup reference is required before a destructive action'}
            rows = [dict(row) for row in db.execute(
                'SELECT * FROM lease_scope WHERE lease_id=? AND kind=?', (lease_id,
                 'root' if kind in ('read', 'write', 'destructive') else ('repo' if kind == 'repo' else ('domain' if kind == 'browser' else ('tool' if kind == 'tool' else 'external')))))]
            match = None
            if kind in ('read', 'write', 'repo', 'destructive'):
                probe = Path(str(target)).resolve() if str(target).strip() else None
                for row in rows:
                    try:
                        if probe is not None and probe.is_relative_to(Path(row['value'])):
                            match = row
                            break
                    except (OSError, ValueError):
                        continue
                if match is None and _system(target):
                    self._event(db, lease_id, 'denied', {'kind': kind, 'target': target,
                                                         'rule': 'system-path'})
                    return {'allowed': False, 'rule': 'system-path',
                            'reason': 'System locations are outside every lease'}
            elif kind == 'browser':
                for row in rows:
                    if str(target).lower() == str(row['value']).lower() or str(target).lower(
                    ).endswith('.' + str(row['value']).lower()):
                        match = row
                        break
            else:
                needle = str(tool or target).strip().lower()
                for row in rows:
                    if needle and needle == str(row['value']).lower():
                        match = row
                        break
            if match is None:
                self._event(db, lease_id, 'denied', {'kind': kind, 'target': target,
                                                     'reason': 'outside the lease'})
                return {'allowed': False, 'rule': 'lease-scope',
                        'reason': 'Target is outside the leased scope'}
            if match['uses_remaining'] == 0:
                self._event(db, lease_id, 'denied', {'kind': kind, 'target': target,
                                                     'reason': 'grant used'})
                return {'allowed': False, 'rule': 'grant-used',
                        'reason': 'This one-time grant was already used'}
            if match['uses_remaining'] > 0:
                db.execute('UPDATE lease_scope SET uses_remaining=uses_remaining-1 '
                           'WHERE lease_id=? AND kind=? AND value=?',
                           (lease_id, match['kind'], match['value']))
            self._event(db, lease_id, 'allowed', {'kind': kind, 'target': target,
                                                  'value': match['value']})
            return {'allowed': True, 'rule': 'lease-scope', 'reason': 'Inside the leased scope',
                    'scope': match['value']}

    # ---- boundary expansion ---------------------------------------------------
    def request_expansion(self, lease_id, scope, target, what='', why='', benefit='', fallback='',
                          risk=''):
        scope = _text(scope, 'scope')
        target = _text(target, 'target')
        request_id = uid()
        with self.store.transaction() as db:
            if not self._lease(db, lease_id):
                raise PolicyError('Unknown lease')
            db.execute('INSERT INTO boundary_expansion_requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (request_id, lease_id, scope, target, what, why, benefit, fallback, risk,
                        'PENDING', None, time.time(), None, None))
            self._event(db, lease_id, 'expansion.requested', {'request_id': request_id,
                                                              'scope': scope, 'target': target})
        return {'request_id': request_id, 'status': 'PENDING'}

    def resolve_expansion(self, request_id, allow, actor='user', grant_kind='once', seconds=86400):
        if actor != 'user':
            raise PolicyError('Only user input can resolve a boundary request')
        with self.store.transaction() as db:
            row = db.execute('SELECT * FROM boundary_expansion_requests WHERE request_id=?',
                             (request_id,)).fetchone()
            if not row:
                raise PolicyError('Unknown boundary request')
            if row['status'] != 'PENDING':
                raise PolicyError('Boundary request already resolved')
            now = time.time()
            if not allow:
                db.execute("UPDATE boundary_expansion_requests SET status='DENIED', actor=?, "
                           'resolved_at=? WHERE request_id=?', (actor, now, request_id))
                self._event(db, row['lease_id'], 'expansion.denied', {'request_id': request_id})
                return {'request_id': request_id, 'status': 'DENIED'}
            if grant_kind not in ('once', 'project'):
                raise PolicyError('grant_kind must be once or project')
            uses = 1 if grant_kind == 'once' else -1
            db.execute('INSERT OR REPLACE INTO lease_scope VALUES(?,?,?,?,?)',
                       (row['lease_id'], row['scope'], row['target'], uses,
                        now + float(seconds) if grant_kind == 'once' else 0))
            db.execute("UPDATE boundary_expansion_requests SET status='GRANTED', grant_kind=?, "
                       'actor=?, resolved_at=? WHERE request_id=?',
                       (grant_kind, actor, now, request_id))
            self._event(db, row['lease_id'], 'expansion.granted',
                        {'request_id': request_id, 'scope': row['scope'], 'target': row['target'],
                         'grant_kind': grant_kind})
        return {'request_id': request_id, 'status': 'GRANTED', 'grant_kind': grant_kind,
                'scope': row['scope'], 'target': row['target']}

    def requests(self, lease_id=None):
        with contextlib.closing(self.store.connect()) as db:
            rows = (db.execute('SELECT * FROM boundary_expansion_requests WHERE lease_id=? '
                               'ORDER BY created DESC', (lease_id,)).fetchall() if lease_id
                    else db.execute('SELECT * FROM boundary_expansion_requests '
                                    'ORDER BY created DESC').fetchall())
            return [dict(row) for row in rows]

    def emergency_stop(self, actor='user'):
        if actor != 'user':
            raise PolicyError('Only the user can trigger an emergency stop')
        stopped = []
        with self.store.transaction() as db:
            rows = db.execute("SELECT lease_id FROM capability_leases WHERE state='ACTIVE'").fetchall()
            for row in rows:
                db.execute("UPDATE capability_leases SET state='REVOKED', revoked_at=?, "
                           "reason='emergency stop' WHERE lease_id=?", (time.time(), row['lease_id']))
                self._event(db, row['lease_id'], 'emergency_stop', {'actor': actor})
                stopped.append(row['lease_id'])
        return {'stopped': stopped, 'count': len(stopped)}

    # ---- service envelope -----------------------------------------------------
    def apply(self, data):
        action = data.get('action')
        if action == 'issue':
            return self.issue(data['job_id'], data.get('project_id', 'default'),
                              data.get('profile', 'broad'), data.get('review_ref', ''),
                              data.get('roots', ()), data.get('repositories', ()),
                              data.get('domains', ()), data.get('tools', ()),
                              data.get('external_actions', ()), float(data.get('seconds', 86400)))
        if action == 'check':
            return self.check(data['lease_id'], data['kind'], data.get('target', ''),
                              data.get('tool', ''), data.get('destructive_snapshot', ''))
        if action == 'revoke':
            return self.revoke(data['lease_id'], data.get('reason', ''))
        if action == 'leases':
            return {'leases': self.leases(data.get('job_id'))}
        if action == 'request':
            return self.request_expansion(data['lease_id'], data['scope'], data['target'],
                                          data.get('what', ''), data.get('why', ''),
                                          data.get('benefit', ''), data.get('fallback', ''),
                                          data.get('risk', ''))
        if action == 'resolve':
            return self.resolve_expansion(data['request_id'], bool(data.get('allow')),
                                          data.get('actor', 'user'), data.get('grant_kind', 'once'))
        if action == 'requests':
            return {'requests': self.requests(data.get('lease_id'))}
        if action == 'guardrails':
            return {'rules': self.guardrails(), 'digest': GUARDRAIL_DIGEST}
        if action == 'emergency_stop':
            return self.emergency_stop(data.get('actor', 'user'))
        raise PolicyError('Unknown autonomy action: %s' % action)
