"""OAuth foundation for Connections (V2.0 / V2-04b).

One framework for account-authorization services — no per-service auth app, no second credential
store, no token anywhere a model, a log, a message, an approval, an access-history row or a renderer
could read it. A provider is a row of data (where to authorize, where to trade the code, where to
revoke, whether PKCE applies, which permissions Kel asks for); flow state lives in the engine's own
store under `oauth_flows` (single-use, short-lived, never a token); tokens land in the same
in-memory custody the rest of the Connection framework uses, and reach their durable home through
the shell's existing credential custody — the shell claims a finished authorization exactly once
(`claim`), keeps it in the OS-backed store, and pushes it back into engine memory the same way it
pushes every other connection value.

Lifecycle: disconnected -> connect (browser) -> callback (state + PKCE checked) -> connected ->
test -> authorized action -> refresh when the access token ages -> revoke -> disconnected.

Design: docs/v2/DECISIONS.md (V2-04b). The provider addresses below are the documented ones; a live
run against the real provider only happens when Nick completes a real sign-in.
"""
import base64
import contextlib
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode

from .core import PolicyError
from .connections import (clear_credentials, custody_for, perform_request, supply_credentials)

FLOW_TTL = 10 * 60
TOKEN_TIMEOUT = 20
TOKEN_ATTEMPTS = 2
CLOCK_SKEW = 60
AUTH_STATES = ('disconnected', 'pending', 'connected', 'needs_reconnect')

# The providers Kel knows, as data. `pkce` says whether the authorization request carries a code
# challenge; `client_secret` says whether the trade may also carry a stored secret (a public client
# needs only the client ID). `scopes` maps each permission to the plain words a person reads.
PROVIDERS = (
    {
        'id': 'google',
        'label': 'Google',
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'revoke_url': 'https://oauth2.googleapis.com/revoke',
        'pkce': True,
        'client_secret': True,
        'extra_authorize': {'access_type': 'offline', 'prompt': 'consent'},
        'scopes': {
            'https://www.googleapis.com/auth/drive.metadata.readonly':
                'See the names, types and sizes of your Drive files (never their contents)',
        },
        'default_scopes': ('https://www.googleapis.com/auth/drive.metadata.readonly',),
    },
)
BY_ID = {entry['id']: entry for entry in PROVIDERS}


def provider(provider_id):
    entry = BY_ID.get(str(provider_id or '').strip().lower())
    if not entry:
        raise PolicyError('Kel does not know that account-authorization provider.')
    return dict(entry)


def provider_for_connection(connection):
    """The provider an oauth connection signs in with: its own row first, then the catalogue's."""
    declared = str(connection.get('oauth_provider') or '').strip().lower()
    if declared:
        return provider(declared)
    try:
        from .connection_services import entry as service_entry
        service = service_entry(connection.get('id'))
    except Exception:
        service = None
    candidate = str((service or {}).get('oauth_provider') or '')
    if candidate:
        return provider(candidate)
    raise PolicyError('Kel does not know which account provider this connection signs in with yet.')


def scope_labels(scopes):
    """The same permissions in plain words, for whatever surface is showing them."""
    labels = {}
    for entry in PROVIDERS:
        labels.update(entry['scopes'])
    return [labels.get(str(scope), str(scope)) for scope in (scopes or ())]


def _pkce_pair():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')
    return verifier, challenge


def _auth_state(store, connection_id, state, scopes=None, expires=None, provider_id=None):
    with store.transaction() as db:
        sets = ['auth_state=?', 'updated=?']
        args = [state, time.time()]
        if scopes is not None:
            sets.append('auth_scopes=?')
            args.append(json.dumps(list(scopes)))
        if expires is not None:
            sets.append('auth_expires=?')
            args.append(float(expires))
        if provider_id:
            sets.append('oauth_provider=?')
            args.append(str(provider_id))
        args.append(str(connection_id))
        db.execute('UPDATE connections SET %s WHERE id=?' % ', '.join(sets), args)


def _trade(chosen, form):
    """One token trade through the framework's single request choke point. Returns (payload, problem)."""
    body = urlencode(form).encode('utf-8')
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
    try:
        status, final, tried, elapsed, raw = perform_request(
            chosen['token_url'], headers, timeout=TOKEN_TIMEOUT, attempts=TOKEN_ATTEMPTS,
            budget=TOKEN_TIMEOUT * TOKEN_ATTEMPTS, method='POST', read_body=True, payload=body)
    except Exception:
        return None, 'Kel could not reach %s to finish the sign-in.' % chosen['label']
    try:
        payload = json.loads(raw.decode('utf-8', 'replace') or '{}')
    except ValueError:
        payload = {}
    if status != 200 or not payload.get('access_token'):
        reason = str(payload.get('error_description') or payload.get('error') or '').strip()
        return None, ('%s did not accept the sign-in%s.'
                      % (chosen['label'], (' — ' + reason[:200]) if reason else ''))
    return payload, None


def begin(store, connection, redirect_base, provider_id=None, scopes=None):
    """Start one authorization: a single-use state, an optional PKCE pair, a recorded short-lived flow."""
    if connection.get('kind') != 'oauth':
        raise PolicyError('Only an account-authorization connection is connected this way.')
    base = str(redirect_base or '').strip().rstrip('/')
    if not base.startswith('http://127.0.0.1:'):
        raise PolicyError('Kel can only finish a sign-in on its own local address.')
    chosen = provider(provider_id) if provider_id else provider_for_connection(connection)
    credentials = custody_for(connection['id'])
    client_id = str(credentials.get('client_id') or '')
    if not client_id:
        raise PolicyError('Kel needs the app\'s client ID stored for %s first — create one with %s as '
                          'a desktop app, then store it like a credential.' % (connection['name'],
                                                                               chosen['label']))
    wanted = tuple(str(scope) for scope in (scopes or chosen['default_scopes']))
    unknown = [scope for scope in wanted if scope not in chosen['scopes']]
    if unknown:
        raise PolicyError('Kel does not know what that permission would allow.')
    state = secrets.token_urlsafe(32)
    verifier = ''
    params = {'response_type': 'code', 'client_id': client_id,
              'redirect_uri': base + '/oauth/callback',
              'scope': ' '.join(wanted), 'state': state}
    if chosen['pkce']:
        verifier, challenge = _pkce_pair()
        params['code_challenge'] = challenge
        params['code_challenge_method'] = 'S256'
    params.update(chosen.get('extra_authorize') or {})
    authorize_url = chosen['authorize_url'] + '?' + urlencode(params)
    now = time.time()
    with store.transaction() as db:
        db.execute('INSERT OR REPLACE INTO oauth_flows(state, connection_id, provider, verifier,'
                   ' redirect_uri, scopes, created, expires, status, claimed)'
                   ' VALUES(?,?,?,?,?,?,?,?,?,0)',
                   (state, connection['id'], chosen['id'], verifier, params['redirect_uri'],
                    json.dumps(list(wanted)), now, now + FLOW_TTL, 'PENDING'))
        db.execute("UPDATE connections SET auth_state='pending', updated=? WHERE id=?",
                   (now, connection['id']))
    return {'connection': connection['id'], 'state': state, 'provider': chosen['id'],
            'provider_label': chosen['label'], 'authorize_url': authorize_url,
            'redirect_uri': params['redirect_uri'], 'scopes': list(wanted),
            'scope_labels': scope_labels(wanted), 'expires': now + FLOW_TTL}


def complete(store, state, code=None, refused=None):
    """Finish an authorization: the state is single-use, the exact flow is bound, tokens stay memory."""
    wanted = str(state or '').strip()
    if not wanted:
        return {'ok': False, 'state': 'disconnected',
                'note': 'That sign-in answer did not include which request it was for.'}
    with store.transaction() as db:
        flow = db.execute('SELECT * FROM oauth_flows WHERE state=?', (wanted,)).fetchone()
        if not flow:
            return {'ok': False, 'state': 'disconnected',
                    'note': 'That sign-in answer does not match any request Kel started.'}
        if flow['status'] != 'PENDING':
            return {'ok': False, 'state': 'disconnected',
                    'note': 'That sign-in answer was already used.'}
        db.execute("UPDATE oauth_flows SET status='USED' WHERE state=?", (wanted,))
    connection_id = str(flow['connection_id'])
    chosen = provider(flow['provider'])
    if float(flow['expires'] or 0) < time.time():
        _auth_state(store, connection_id, 'disconnected')
        return {'ok': False, 'state': 'disconnected',
                'note': 'That sign-in took too long; start it again.'}
    if refused:
        _auth_state(store, connection_id, 'disconnected')
        return {'ok': False, 'state': 'disconnected',
                'note': '%s sign-in was not finished on the sign-in page.' % chosen['label']}
    code_text = str(code or '').strip()
    if not code_text:
        _auth_state(store, connection_id, 'disconnected')
        return {'ok': False, 'state': 'disconnected',
                'note': 'That sign-in answer was incomplete.'}
    credentials = custody_for(connection_id)
    form = {'grant_type': 'authorization_code', 'code': code_text,
            'redirect_uri': str(flow['redirect_uri'] or ''),
            'client_id': str(credentials.get('client_id') or '')}
    if flow['verifier']:
        form['code_verifier'] = str(flow['verifier'])
    if chosen.get('client_secret') and credentials.get('client_secret'):
        form['client_secret'] = credentials['client_secret']
    traded, problem = _trade(chosen, form)
    if problem:
        _auth_state(store, connection_id, 'disconnected')
        return {'ok': False, 'state': 'disconnected', 'note': problem}
    granted = [scope for scope in str(traded.get('scope') or '').split() if scope]
    missing = [scope for scope in json.loads(flow['scopes'] or '[]') if scope not in granted]
    merged = dict(credentials)
    merged['access_token'] = str(traded['access_token'])
    if traded.get('refresh_token'):
        merged['refresh_token'] = str(traded['refresh_token'])
    supply_credentials(connection_id, merged)
    expires = time.time() + max(60, int(traded.get('expires_in') or 3600) - CLOCK_SKEW)
    _auth_state(store, connection_id, 'connected', scopes=granted, expires=expires,
                provider_id=chosen['id'])
    with store.transaction() as db:
        db.execute("UPDATE oauth_flows SET status='COMPLETED' WHERE state=?", (wanted,))
    if missing:
        note = ('%s is connected, but it did not grant: %s.'
                % (chosen['label'], '; '.join(scope_labels(missing))))
    else:
        note = '%s is connected.' % chosen['label']
    return {'ok': True, 'state': 'connected', 'connection': connection_id,
            'scopes': granted, 'scope_labels': scope_labels(granted), 'note': note}


def claim(store, connection_id):
    """Hand a finished authorization to the shell's custody exactly once (the engine keeps memory)."""
    wanted = str(connection_id or '')
    with store.transaction() as db:
        flow = db.execute("SELECT * FROM oauth_flows WHERE connection_id=? AND status='COMPLETED'"
                          " ORDER BY created DESC LIMIT 1", (wanted,)).fetchone()
        if not flow or flow['claimed']:
            return {'connection': wanted, 'claimed': False, 'fields': [],
                    'note': 'There is no new sign-in waiting to be stored.'}
        db.execute('UPDATE oauth_flows SET claimed=1 WHERE state=?', (flow['state'],))
    values = custody_for(wanted)
    return {'connection': wanted, 'claimed': True, 'fields': sorted(values.keys()),
            'credentials': values, 'note': 'Handed over once; the engine keeps only its working copy.'}


def refresh(store, connection, credentials):
    """Trade the refresh token for a fresh access token. Returns (credentials, problem)."""
    chosen = provider_for_connection(connection)
    refresh_token = str((credentials or {}).get('refresh_token') or '')
    if not refresh_token:
        return None, 'Kel has no saved refresh for %s.' % connection['name']
    form = {'grant_type': 'refresh_token', 'refresh_token': refresh_token,
            'client_id': str((credentials or {}).get('client_id') or '')}
    if chosen.get('client_secret') and (credentials or {}).get('client_secret'):
        form['client_secret'] = credentials['client_secret']
    traded, problem = _trade(chosen, form)
    if problem:
        return None, problem
    merged = dict(credentials or {})
    merged['access_token'] = str(traded['access_token'])
    if traded.get('refresh_token'):
        merged['refresh_token'] = str(traded['refresh_token'])
    supply_credentials(connection['id'], merged)
    expires = time.time() + max(60, int(traded.get('expires_in') or 3600) - CLOCK_SKEW)
    _auth_state(store, connection['id'], 'connected', expires=expires)
    return merged, None


def ensure_fresh(store, connection, credentials):
    """The gate every oauth call passes: reconnect honesty first, refresh when the clock says so."""
    if connection.get('kind') != 'oauth':
        return credentials
    auth = str(connection.get('auth_state') or '')
    values = dict(credentials or {})
    if not values:
        # No caller supplied values: the sign-in Kel keeps for this connection is the source.
        values = custody_for(connection['id'])
    if auth == 'needs_reconnect':
        raise PolicyError('Kel needs you to reconnect %s before it can use it.' % connection['name'])
    if auth != 'connected':
        return credentials  # a pasted token still works exactly as it did before
    if not values.get('access_token'):
        raise PolicyError('Kel does not have %s\'s sign-in on this computer right now; reconnect it '
                          'first.' % connection['name'])
    expires = connection.get('auth_expires')
    if expires and float(expires) - 1 <= time.time():
        merged, problem = refresh(store, connection, values)
        if problem or not merged:
            _auth_state(store, connection['id'], 'needs_reconnect')
            raise PolicyError('Kel needs you to reconnect %s: the saved sign-in no longer works.'
                              % connection['name'])
        return merged
    return values


def revoke(store, connection):
    """Sign out: the provider's revoke endpoint when it has one, then local custody, plainly."""
    chosen = provider_for_connection(connection)
    credentials = custody_for(connection['id'])
    token = str(credentials.get('refresh_token') or credentials.get('access_token') or '')
    note = '%s is signed out on this computer.' % connection['name']
    if token and chosen.get('revoke_url'):
        body = urlencode({'token': token}).encode('utf-8')
        try:
            status, final, tried, elapsed, raw = perform_request(
                chosen['revoke_url'],
                {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'},
                timeout=TOKEN_TIMEOUT, attempts=1, budget=TOKEN_TIMEOUT, method='POST',
                read_body=True, payload=body)
            if status not in (200, 400, 401):
                note = ('%s is signed out here, but %s did not confirm it (answered %d).'
                        % (connection['name'], chosen['label'], status))
        except Exception:
            note = ('%s is signed out here, but %s could not be reached to confirm it.'
                    % (connection['name'], chosen['label']))
    clear_credentials(connection['id'])
    _auth_state(store, connection['id'], 'disconnected', scopes=[])
    return {'connection': connection['id'], 'state': 'disconnected', 'note': note}


def missing_scopes(connection, wanted):
    """Which of an action's permissions the provider did not grant (empty when all is well)."""
    if connection.get('kind') != 'oauth' or str(connection.get('auth_state') or '') != 'connected':
        return []
    granted = set(connection.get('auth_scopes') or ())
    return [scope for scope in (wanted or ()) if scope not in granted]
