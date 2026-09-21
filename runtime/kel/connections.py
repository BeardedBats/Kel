"""Connections (V2.0): Kel has credentials for a service and can use its API.

One product term, one store, one place to manage them. A Connection is deliberately thin — the
service's name, where its API lives, how the credential is presented, where its docs are, and whether
the OS-backed store actually holds a credential for it. There is no per-service app, database, worker
or workflow here: every service is a row, and what Kel can *do* with a service belongs to tools
(V2-04), never to this table.

Credential values never reach the engine. The shell keeps them in the OS-backed store under the
`connection:<id>` namespace; this store keeps only the metadata — which field names exist and a
pointer (`credential_ref`) into that store. A connection therefore always reports its state honestly:
`ready` when the shell has reported a credential for it, `needs_credentials` when it has not.

Design: docs/v2/DECISIONS.md (V2-01).
"""
import contextlib
import json
import re
import time
from urllib.parse import urlparse

from .core import PolicyError

MIGRATION_VERSION = 23
MIGRATION_NAME = 'v20-connections'

# The three framework templates (directive §8). A row's kind only says how its credential is shaped —
# the framework that authenticates a request with it is V2-04's job.
KINDS = ('api_key', 'oauth', 'bot')
KIND_LABELS = {'api_key': 'API key', 'oauth': 'Account authorization',
               'bot': 'Bot or webhook'}
# How the credential is presented on a request. `auth_header` names the header (method `header`) or
# the query parameter (method `query`); bearer and basic need no name.
AUTH_METHODS = ('header', 'bearer', 'query', 'basic')
STATES = ('ready', 'needs_credentials')
CREDENTIAL_REF_PREFIX = 'kel:connection:'

ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,59}$')
MAX_NAME = 80
MAX_URL = 500
MAX_NOTES = 2000
LIST_LIMIT = 200

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
    version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS connections(
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'api_key',
    base_url TEXT,
    auth_method TEXT NOT NULL DEFAULT 'header',
    auth_header TEXT,
    docs_url TEXT,
    test_endpoint TEXT,
    notes TEXT,
    credential_ref TEXT,
    credential_fields TEXT,
    created REAL NOT NULL,
    updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS connections_by_name ON connections(name);
"""


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                      (name,)).fetchone() is not None


def ensure_schema(store):
    """Create the store once. Returns True when this call applied it."""
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'schema_migrations'):
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                      (MIGRATION_VERSION,)).fetchone():
            return False
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) '
                   'VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'Connections: credentials for a service'))
        return True


def _text(value, limit, field):
    """One line of plain text, or nothing. Control characters are never stored."""
    if value in (None, ''):
        return None
    cleaned = ' '.join(str(value).split())
    cleaned = ''.join(ch for ch in cleaned if ch.isprintable())
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise PolicyError('That %s is too long — keep it under %d characters.' % (field, limit))
    return cleaned


def _url(value, field):
    """An http(s) address, or nothing. Anything else (a path, javascript:, data:) is refused."""
    cleaned = _text(value, MAX_URL, field)
    if not cleaned:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise PolicyError('That %s needs to be a full http:// or https:// address.' % field)
    return cleaned


def _kind(value):
    cleaned = str(value or '').strip().lower() or 'api_key'
    if cleaned not in KINDS:
        raise PolicyError('That is not a kind of connection Kel knows.')
    return cleaned


def _auth_method(value, fallback='header'):
    cleaned = str(value or '').strip().lower() or fallback
    if cleaned not in AUTH_METHODS:
        raise PolicyError('That is not an authentication method Kel knows.')
    return cleaned


def slug(name):
    """A stable, readable id from a service name — 'Pitcher List' becomes 'pitcher-list'."""
    base = re.sub(r'[^a-z0-9]+', '-', str(name or '').strip().lower()).strip('-')[:48]
    return base or 'service'


class Connections:
    """The connection store. Rows carry metadata only; values live in the OS-backed store."""

    def __init__(self, store):
        self.store = store
        ensure_schema(store)

    # -- reads ------------------------------------------------------------------------------------
    def _row(self, row):
        fields = json.loads(row['credential_fields']) if row['credential_fields'] else []
        item = {
            'id': row['id'],
            'name': row['name'],
            'kind': row['kind'],
            'kind_label': KIND_LABELS.get(row['kind'], row['kind']),
            'base_url': row['base_url'] or '',
            'auth_method': row['auth_method'],
            'auth_header': row['auth_header'] or '',
            'docs_url': row['docs_url'] or '',
            'test_endpoint': row['test_endpoint'] or '',
            'notes': row['notes'] or '',
            'credential_ref': row['credential_ref'],
            'credential_fields': fields,
            'has_credentials': bool(row['credential_ref']),
            'created': row['created'],
            'updated': row['updated'],
        }
        item['state'] = 'ready' if item['has_credentials'] else 'needs_credentials'
        return item

    def list(self):
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT * FROM connections ORDER BY name COLLATE NOCASE, id '
                              'LIMIT ?', (LIST_LIMIT,)).fetchall()
        items = [self._row(row) for row in rows]
        counts = {state: 0 for state in STATES}
        for item in items:
            counts[item['state']] += 1
        return {'connections': items, 'counts': counts, 'states': list(STATES), 'kinds': list(KINDS)}

    def get(self, connection_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM connections WHERE id=?',
                             (str(connection_id or ''),)).fetchone()
        if not row:
            raise PolicyError('That connection was not found.')
        return self._row(row)

    # -- writes -----------------------------------------------------------------------------------
    def _available_id(self, db, name, wanted=None):
        if wanted:
            candidate = str(wanted).strip().lower()
            if not ID_RE.match(candidate):
                raise PolicyError('That connection id is not usable.')
            return candidate
        base = slug(name)
        candidate, suffix = base, 2
        while db.execute('SELECT 1 FROM connections WHERE id=?', (candidate,)).fetchone():
            candidate = '%s-%d' % (base, suffix)
            suffix += 1
        return candidate

    def save(self, name, *, connection_id=None, kind='api_key', base_url=None, auth_method=None,
             auth_header=None, docs_url=None, test_endpoint=None, notes=None):
        """Create a connection, or update the one with this id. Never stores a credential value."""
        clean_name = _text(name, MAX_NAME, 'name')
        if not clean_name:
            raise PolicyError('Give this connection the service name you know it by.')
        clean_kind = _kind(kind)
        method = _auth_method(auth_method, 'bearer' if clean_kind == 'oauth' else 'header')
        header = _text(auth_header, 120, 'header name')
        if method == 'header' and not header:
            header = 'Authorization'
        if method in ('bearer', 'basic'):
            header = None
        now = time.time()
        with self.store.transaction() as db:
            existing = None
            if connection_id:
                existing = db.execute('SELECT * FROM connections WHERE id=?',
                                      (str(connection_id),)).fetchone()
                if not existing:
                    raise PolicyError('That connection was not found.')
            target = self._available_id(db, clean_name, existing['id'] if existing else None)
            fields = dict(
                name=clean_name, kind=clean_kind,
                base_url=_url(base_url, 'address'),
                auth_method=method, auth_header=header,
                docs_url=_url(docs_url, 'documentation address'),
                test_endpoint=_url(test_endpoint, 'test address'),
                notes=_text(notes, MAX_NOTES, 'note'),
            )
            if existing:
                # Credential metadata is custody state, not a form field: editing a connection never
                # silently drops the pointer to a stored credential.
                db.execute('UPDATE connections SET name=?, kind=?, base_url=?, auth_method=?,'
                           ' auth_header=?, docs_url=?, test_endpoint=?, notes=?, updated=?'
                           ' WHERE id=?',
                           (fields['name'], fields['kind'], fields['base_url'],
                            fields['auth_method'], fields['auth_header'], fields['docs_url'],
                            fields['test_endpoint'], fields['notes'], now, target))
            else:
                db.execute('INSERT INTO connections(id, name, kind, base_url, auth_method,'
                           ' auth_header, docs_url, test_endpoint, notes, credential_ref,'
                           ' credential_fields, created, updated)'
                           ' VALUES(?,?,?,?,?,?,?,?,?,NULL,NULL,?,?)',
                           (target, fields['name'], fields['kind'], fields['base_url'],
                            fields['auth_method'], fields['auth_header'], fields['docs_url'],
                            fields['test_endpoint'], fields['notes'], now, now))
        return self.get(target)

    def remove(self, connection_id):
        """Forget the connection and the metadata pointing at its credential.

        The stored value itself belongs to the shell's OS-backed custody — the shell removes it at the
        same moment (it is the only side that can reach the value).
        """
        with self.store.transaction() as db:
            row = db.execute('SELECT id FROM connections WHERE id=?',
                             (str(connection_id or ''),)).fetchone()
            if not row:
                raise PolicyError('That connection was not found.')
            db.execute('DELETE FROM connections WHERE id=?', (row['id'],))
        return {'id': row['id'], 'removed': True}

    # -- credential metadata (never values) -------------------------------------------------------
    def set_credential(self, connection_id, fields, credential_ref):
        """Record that the shell holds a credential for this connection.

        The engine stores field *names* and a pointer, exactly like the model-provider registry: a
        value has no column to live in, and the pointer may not be a value.
        """
        item = self.get(connection_id)
        names = [str(field).strip() for field in (fields or [])]
        if not names or any(not name for name in names):
            raise PolicyError('Kel needs the credential field names before it can record one.')
        ref = str(credential_ref or '')
        if not ref.startswith(CREDENTIAL_REF_PREFIX):
            raise PolicyError('Kel records a pointer to the credential, never the credential itself.')
        now = time.time()
        with self.store.transaction() as db:
            db.execute('UPDATE connections SET credential_ref=?, credential_fields=?, updated=?'
                       ' WHERE id=?', (ref, json.dumps(names), now, item['id']))
        return self.get(item['id'])

    def delete_credential(self, connection_id):
        item = self.get(connection_id)
        with self.store.transaction() as db:
            db.execute('UPDATE connections SET credential_ref=NULL, credential_fields=NULL,'
                       ' updated=? WHERE id=?', (time.time(), item['id']))
        return self.get(item['id'])
