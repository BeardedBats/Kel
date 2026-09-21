"""Network permissions (V2-14): the rules behind the single choke point.

Directive §19, kept practical: three modes (**none** — NO INTERNET, **approved** — APPROVED
DOMAINS, **full** — FULL INTERNET), a per-Project scope, per-tool overrides, "ask before a new
domain", and an access history. Everything answers the ONE hook `kel.connections.NETWORK_RULES`
already exposes (asked before anything leaves the computer and again for a redirect's host, fail
closed if the rule source errors) — this module is the rule source, never a second path.

With no policy rows the default is `full`: behaviour is exactly as before until a person chooses a
mode. An `approved` host is matched exactly or as a parent domain (`api.github.com` matches an
approved `github.com`; approving `api.github.com` also covers its own subdomains). A new host in
`approved` is not sent: it is recorded as a pending request and refused with one plain sentence
naming the one action that fixes it (approve it in Connections, or change the scope's mode).

This module is bound per engine store around the one call that leaves the computer
(`Connections.test` / `Connections.run`), so nothing global leaks between stores and a process
that never uses Connections keeps the seam open exactly as before.
"""
import contextlib
import json
import time

from .core import PolicyError

MODES = ('none', 'approved', 'full')
DEFAULT_MODE = 'full'
DEFAULT_SCOPE = 'default'

DDL = """
CREATE TABLE IF NOT EXISTS network_policy(
    scope TEXT PRIMARY KEY, mode TEXT NOT NULL, domains TEXT NOT NULL DEFAULT '[]',
    updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS network_tool_rules(
    tool TEXT PRIMARY KEY, mode TEXT NOT NULL, domains TEXT NOT NULL DEFAULT '[]',
    updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS network_events(
    seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, host TEXT, tool TEXT, project TEXT,
    scope TEXT, decision TEXT NOT NULL, reason TEXT);
CREATE TABLE IF NOT EXISTS network_requests(
    id TEXT PRIMARY KEY, host TEXT NOT NULL, tool TEXT, project TEXT, scope TEXT NOT NULL,
    state TEXT NOT NULL, created REAL NOT NULL, decided REAL);
"""


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)


def _uid():
    from .core import uid
    return uid()


def _mode(value):
    if value not in MODES:
        raise PolicyError('Network mode is one of %s.' % ', '.join(MODES))
    return value


def _domains(value):
    if value in (None, ''):
        return []
    if not isinstance(value, (list, tuple)):
        raise PolicyError('Approved domains are a list of names.')
    cleaned = []
    for item in value:
        name = str(item or '').strip().lower().lstrip('.')
        if not name or '/' in name or ' ' in name:
            raise PolicyError('"%s" is not a domain name.' % item)
        if name not in cleaned:
            cleaned.append(name)
    return cleaned


def _row(store, sql, args=()):
    with contextlib.closing(store.connect()) as db:
        return db.execute(sql, args).fetchone()


def get_policy(store):
    """Everything the surface needs to show: the default, every project scope, every tool rule."""
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM network_policy ORDER BY scope')]
        tools = [dict(r) for r in db.execute('SELECT * FROM network_tool_rules ORDER BY tool')]
    out = {'default': {'scope': DEFAULT_SCOPE, 'mode': DEFAULT_MODE, 'domains': []},
           'projects': [], 'tools': []}
    for row in rows:
        item = {'scope': row['scope'], 'mode': row['mode'],
                'domains': json.loads(row['domains'] or '[]'), 'updated': row['updated']}
        if row['scope'] == DEFAULT_SCOPE:
            out['default'] = item
        else:
            out['projects'].append(item)
    for row in tools:
        out['tools'].append({'tool': row['tool'], 'mode': row['mode'],
                             'domains': json.loads(row['domains'] or '[]'),
                             'updated': row['updated']})
    return out


def set_mode(store, mode, *, scope=DEFAULT_SCOPE, domains=None):
    """Set one scope's mode (and its approved list). The person's own choice, never inferred."""
    ensure_schema(store)
    mode = _mode(mode)
    scope = str(scope or DEFAULT_SCOPE)
    if scope != DEFAULT_SCOPE and not scope.startswith('project:'):
        raise PolicyError('A network scope is "default" or "project:<id>".')
    with store.transaction() as db:
        db.execute('INSERT INTO network_policy(scope,mode,domains,updated) VALUES(?,?,?,?)'
                   ' ON CONFLICT(scope) DO UPDATE SET mode=excluded.mode,'
                   ' domains=excluded.domains, updated=excluded.updated',
                   (scope, mode, json.dumps(_domains(domains)), time.time()))
    return get_policy(store)


def set_tool_rule(store, tool, mode, *, domains=None):
    ensure_schema(store)
    mode = _mode(mode)
    if not isinstance(tool, str) or not tool.strip():
        raise PolicyError('A tool rule names the tool it applies to.')
    with store.transaction() as db:
        db.execute('INSERT INTO network_tool_rules(tool,mode,domains,updated) VALUES(?,?,?,?)'
                   ' ON CONFLICT(tool) DO UPDATE SET mode=excluded.mode,'
                   ' domains=excluded.domains, updated=excluded.updated',
                   (tool.strip(), mode, json.dumps(_domains(domains)), time.time()))
    return get_policy(store)


def clear_tool_rule(store, tool):
    ensure_schema(store)
    with store.transaction() as db:
        db.execute('DELETE FROM network_tool_rules WHERE tool=?', (str(tool or ''),))
    return get_policy(store)


def host_matches(host, domains):
    """Exact host or a parent domain on the list (an approved `github.com` covers its subdomains)."""
    host = str(host or '').strip().lower().rstrip('.')
    if not host:
        return None
    for domain in domains or ():
        if host == domain or host.endswith('.' + domain):
            return domain
    return None


def _effective(store, tool, project):
    """Which scope decides this call: an exact tool rule beats the project, the project beats default."""
    if tool:
        row = _row(store, 'SELECT * FROM network_tool_rules WHERE tool=?', (tool,))
        if row:
            return {'scope': 'tool:%s' % tool, 'mode': row['mode'],
                    'domains': json.loads(row['domains'] or '[]')}
    if project:
        row = _row(store, 'SELECT * FROM network_policy WHERE scope=?', ('project:%s' % project,))
        if row:
            return {'scope': 'project:%s' % project, 'mode': row['mode'],
                    'domains': json.loads(row['domains'] or '[]')}
    row = _row(store, 'SELECT * FROM network_policy WHERE scope=?', (DEFAULT_SCOPE,))
    if row:
        return {'scope': DEFAULT_SCOPE, 'mode': row['mode'],
                'domains': json.loads(row['domains'] or '[]')}
    return {'scope': DEFAULT_SCOPE, 'mode': DEFAULT_MODE, 'domains': []}


def _record(store, host, tool, project, scope, decision, reason):
    with store.transaction() as db:
        db.execute('INSERT INTO network_events(at,host,tool,project,scope,decision,reason)'
                   ' VALUES(?,?,?,?,?,?,?)',
                   (time.time(), host, tool, project, scope, decision, str(reason or '')[:400]))


def decide(store, host, *, tool=None, project=None):
    """The decision for one host: allowed, blocked, or ask (recorded, never silently sent)."""
    ensure_schema(store)
    host = str(host or '').strip().lower()
    effective = _effective(store, tool, project)
    mode, scope = effective['mode'], effective['scope']
    if mode == 'full':
        if not host:
            return {'allowed': True, 'mode': mode, 'scope': scope, 'host': host, 'reason': ''}
        _record(store, host, tool, project, scope, 'allowed', 'full internet')
        return {'allowed': True, 'mode': mode, 'scope': scope, 'host': host, 'reason': ''}
    if mode == 'none':
        reason = 'You set Kel to no internet for %s, so nothing is sent.' % scope
        _record(store, host, tool, project, scope, 'blocked', reason)
        return {'allowed': False, 'mode': mode, 'scope': scope, 'host': host, 'reason': reason}
    matched = host_matches(host, effective['domains'])
    if matched:
        _record(store, host, tool, project, scope, 'allowed', 'on the approved list (%s)' % matched)
        return {'allowed': True, 'mode': mode, 'scope': scope, 'host': host,
                'reason': '', 'matched': matched}
    existing = _row(store, "SELECT * FROM network_requests WHERE host=? AND state='pending'"
                           " AND scope=? AND IFNULL(tool,'')=IFNULL(?,'')"
                           " ORDER BY created DESC LIMIT 1",
                    (host, scope, tool))
    if existing:
        request_id = existing['id']
    else:
        request_id = _uid()
        with store.transaction() as db:
            db.execute('INSERT INTO network_requests(id,host,tool,project,scope,state,created)'
                       ' VALUES(?,?,?,?,?,?,?)',
                       (request_id, host, tool, project, scope, 'pending', time.time()))
    reason = ('%s is not on the approved list for %s. Approve it in Connections, or change that '
              'scope to full internet, then ask again.' % (host or 'that address', scope))
    _record(store, host, tool, project, scope, 'ask', reason)
    return {'allowed': False, 'mode': mode, 'scope': scope, 'host': host, 'reason': reason,
            'request': request_id}


def requests(store, *, state='pending'):
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        rows = [dict(r) for r in db.execute(
            'SELECT * FROM network_requests WHERE state=? ORDER BY created DESC LIMIT 100',
            (state,))]
    return {'requests': rows}


def resolve_request(store, request_id, allow):
    """Approve or deny one pending request; approval adds the host to that scope's approved list."""
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM network_requests WHERE id=?', (str(request_id),)).fetchone()
    if row is None:
        raise PolicyError('Kel has no request with that id.')
    if row['state'] != 'pending':
        raise PolicyError('That request was already answered.')
    scope = row['scope']
    if allow:
        if scope.startswith('tool:'):
            tool = scope.split(':', 1)[1]
            current = _row(store, 'SELECT * FROM network_tool_rules WHERE tool=?', (tool,))
            domains = json.loads(current['domains'] or '[]') if current else []
            if row['host'] not in domains:
                domains.append(row['host'])
            set_tool_rule(store, tool, current['mode'] if current else 'approved', domains=domains)
        else:
            current = _row(store, 'SELECT * FROM network_policy WHERE scope=?', (scope,))
            domains = json.loads(current['domains'] or '[]') if current else []
            if row['host'] not in domains:
                domains.append(row['host'])
            set_mode(store, current['mode'] if current else 'approved', scope=scope,
                     domains=domains)
    now = time.time()
    with store.transaction() as db:
        db.execute("UPDATE network_requests SET state=?, decided=? WHERE id=?",
                   ('approved' if allow else 'denied', now, row['id']))
    return {'id': row['id'], 'host': row['host'], 'state': 'approved' if allow else 'denied'}


def history(store, limit=50):
    ensure_schema(store)
    limit = max(1, min(int(limit or 50), 200))
    with contextlib.closing(store.connect()) as db:
        rows = [dict(r) for r in db.execute(
            'SELECT * FROM network_events ORDER BY seq DESC LIMIT ?', (limit,))]
    return {'events': rows}


# ---- the seam's rule source, bound per store around the one outbound call ----------------------

_STORE = {'value': None}


def _hook(host, context=None):
    store = _STORE['value']
    if store is None:
        return True, ''
    context = context or {}
    decision = decide(store, host, tool=context.get('tool'), project=context.get('project'))
    return decision['allowed'], decision['reason']


def bind(store):
    """Point the choke point's rule source at this store; returns a token for `unbind`.

    An explicitly configured rule source wins: the policy module is the **default** source for the
    seam, never an override of one that was set deliberately (tests and embeddings install their own
    hooks and must keep working).
    """
    from . import connections
    previous = (connections.NETWORK_RULES, _STORE['value'])
    if connections.NETWORK_RULES is not None and connections.NETWORK_RULES is not _hook:
        return previous
    _STORE['value'] = store
    connections.NETWORK_RULES = _hook
    return previous


def unbind(token):
    from . import connections
    connections.NETWORK_RULES, _STORE['value'] = token
