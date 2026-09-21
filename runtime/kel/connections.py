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

V2-02 adds the one thing that talks to a service: `test()`. The shell passes the credential for that
single request, the request goes out through `perform_request` (the single choke point every future
network rule can live in), and what is recorded afterwards is the *result* — never the value, which is
used in memory and dropped.

Design: docs/v2/DECISIONS.md (V2-01, V2-02).
"""
import base64
import contextlib
import json
import re
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .core import PolicyError

MIGRATIONS = (
    (23, 'v20-connections', 'Connections: credentials for a service'),
    (24, 'v20-connection-tests', 'Connections: what the last check found'),
)
MIGRATION_VERSION = MIGRATIONS[-1][0]
MIGRATION_NAME = MIGRATIONS[-1][1]

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
# What one check of a service can honestly find (V2-02). `ok` is the only state that means the
# credential was accepted; everything else says exactly which part of the request did not work.
TEST_STATES = ('ok', 'refused', 'not_found', 'busy', 'error', 'unreachable', 'timeout')
TEST_TIMEOUT = 10
REDACTED = '[redacted]'

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

# Migration 24 (V2-02): what the last check of the service found. Additive and nullable — an older
# database keeps working, and a connection that has never been checked simply has no result.
TEST_COLUMNS = ('last_test_at REAL', 'last_test_state TEXT', 'last_test_status INTEGER',
                'last_test_ms INTEGER', 'last_test_note TEXT')


def _exec(db, ddl):
    for statement in filter(None, (part.strip() for part in ddl.split(';'))):
        db.execute(statement)


def _create_connections(db):
    _exec(db, DDL)


def _add_test_columns(db):
    """Additive and safe to re-run: a database that already has a column keeps it as it is."""
    existing = {row[1] for row in db.execute('PRAGMA table_info(connections)').fetchall()}
    for column in TEST_COLUMNS:
        if column.split()[0] not in existing:
            db.execute('ALTER TABLE connections ADD COLUMN ' + column)


# Every step must be safe to run again on a database that already has it: a resumed upgrade may
# re-apply the newest step when its marker was lost.
STEP_BY_VERSION = {23: _create_connections, 24: _add_test_columns}


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                      (name,)).fetchone() is not None


def ensure_schema(store):
    """Create or extend the store once. Returns True when this call applied anything."""
    applied = False
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'schema_migrations'):
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        for version, name, note in MIGRATIONS:
            if db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (version,)).fetchone():
                continue
            STEP_BY_VERSION[version](db)
            db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) '
                       'VALUES(?,?,?,?)', (version, name, time.time(), note))
            applied = True
    return applied


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


def scrub(text, credentials):
    """Replace any credential value that somehow reached a sentence. Nothing durable may carry one."""
    cleaned = str(text or '')
    for value in (credentials or {}).values():
        if isinstance(value, str) and len(value) >= 4:
            cleaned = cleaned.replace(value, REDACTED)
    return cleaned


def perform_request(url, headers, timeout=TEST_TIMEOUT):
    """The one place a Connection's request leaves this computer.

    Every future network rule (V2-14: no internet / approved domains / ask before a new domain) has a
    single place to live because of this function. Kel reads the status and nothing else — the body is
    never kept, so a service's data cannot end up in Kel's records by accident.

    Returns (status, final_url, elapsed_ms). A refusal is a result: 401 is an answer, not an error.
    """
    request = urllib.request.Request(url, method='GET', headers=dict(headers or {}))
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, 'status', None) or 200)
            final = response.geturl()
    except urllib.error.HTTPError as error:
        status = int(error.code)
        final = getattr(error, 'url', url)
        error.close()
    return status, final, int((time.monotonic() - started) * 1000)


def auth_for(connection, credentials):
    """Headers and query additions for one request, from the method the connection declares.

    Returns (headers, query, problem). A missing credential is not a problem: the request still goes
    out, so the answer comes from the service instead of from Kel's guesswork.
    """
    values = {str(key): value for key, value in (credentials or {}).items()
              if isinstance(value, str) and value}
    method = connection['auth_method']
    if method == 'basic':
        user, password = values.get('username'), values.get('password')
        if not user or not password:
            return None, None, 'Kel needs both the username and the password for this connection.'
        token = base64.b64encode(('%s:%s' % (user, password)).encode('utf-8')).decode('ascii')
        return {'Authorization': 'Basic ' + token}, None, None
    value = values.get('api_key') or next(iter(values.values()), '')
    if not value:
        return {}, None, None
    if method == 'bearer':
        return {'Authorization': 'Bearer ' + value}, None, None
    if method == 'query':
        return {}, {connection['auth_header'] or 'api_key': value}, None
    name = connection['auth_header'] or 'Authorization'
    # A token in `Authorization` is nearly always a scheme plus the value; a service that wants a bare
    # value in a custom header (X-Api-Key) gets exactly that. A value that already carries a scheme is
    # sent as it is.
    if name.lower() == 'authorization' and not re.match(r'^[A-Za-z]+\s+\S', value):
        return {name: 'Bearer ' + value}, None, None
    return {name: value}, None, None


def classify(status, connection, final_url):
    """The honest meaning of a status code, in one sentence, with no service data in it."""
    host = urlparse(final_url or '').netloc
    asked = urlparse(connection['test_endpoint'] or connection['base_url'] or '').netloc
    redirect = ' It answered from %s instead.' % host if host and host != asked else ''
    if 200 <= status < 300:
        return 'ok', 'The service answered %d.%s' % (status, redirect)
    if status in (401, 403):
        return 'refused', 'The service refused the credential (%d).%s' % (status, redirect)
    if status == 404:
        return 'not_found', ('The service answered, but there is nothing at that address (404).%s'
                             % redirect)
    if status == 429:
        return 'busy', 'The service is limiting requests right now (%d).%s' % (status, redirect)
    if status >= 500:
        return 'error', 'The service answered with its own error (%d).%s' % (status, redirect)
    return 'error', 'The service answered %d.%s' % (status, redirect)


class Connections:
    """The connection store. Rows carry metadata only; values live in the OS-backed store."""

    def __init__(self, store, timeout=TEST_TIMEOUT):
        self.store = store
        self.timeout = timeout
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
            'can_test': bool(row['test_endpoint'] or row['base_url']),
            'last_test_at': row['last_test_at'],
            'last_test_state': row['last_test_state'],
            'last_test_status': row['last_test_status'],
            'last_test_ms': row['last_test_ms'],
            'last_test_note': row['last_test_note'],
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

    # -- talking to the service (V2-02) ------------------------------------------------------------
    def test(self, connection_id, credentials=None):
        """Ask the service whether this works, and record only what happened.

        `credentials` is the shell's own map of field name to value for this one request: it is used
        in memory, never written, and scrubbed out of anything that could become durable. Nothing is
        read from the answer except its status.
        """
        connection = self.get(connection_id)
        target = connection['test_endpoint'] or connection['base_url']
        if not target:
            raise PolicyError('Kel needs a test address or an API address before it can check this '
                              'connection.')
        headers, query, problem = auth_for(connection, credentials)
        if problem:
            raise PolicyError(problem)
        url = target
        if query:
            parsed = urlparse(url)
            pairs = parse_qsl(parsed.query, keep_blank_values=True) + list(query.items())
            url = urlunparse(parsed._replace(query=urlencode(pairs)))
        state, status, elapsed, note = 'error', None, 0, 'The check did not finish.'
        try:
            status, final, elapsed = perform_request(url, headers, timeout=self.timeout)
            state, note = classify(status, connection, final)
        except (TimeoutError, socket.timeout):
            state = 'timeout'
            seconds = int(self.timeout) if float(self.timeout).is_integer() else self.timeout
            note = 'The service did not answer within %s seconds.' % seconds
        except urllib.error.URLError:
            state = 'unreachable'
            note = 'Kel could not reach that address.'
        except Exception:
            state = 'error'
            note = 'The check did not finish.'
        note = scrub(note, credentials)
        with self.store.transaction() as db:
            db.execute('UPDATE connections SET last_test_at=?, last_test_state=?, last_test_status=?,'
                       ' last_test_ms=?, last_test_note=? WHERE id=?',
                       (time.time(), state, status, elapsed, note, connection['id']))
        return self.get(connection['id'])
