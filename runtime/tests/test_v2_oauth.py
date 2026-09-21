"""V2-04b — the OAuth foundation: one reusable sign-in flow for account-authorization services.

The lifecycle this file proves: disconnected -> connect -> provider authorization -> callback
(state + PKCE checked) -> connected -> Test Connection -> authorized read action -> refresh when the
access token ages -> revoke -> disconnected. Not a per-service auth app: a provider is data, the
flow lives in `oauth_flows` (single-use state, never a token), and tokens flow through the same
in-memory custody the rest of the Connection framework uses. A local stand-in provider mounts the
documented addresses, so the WHOLE framework is exercised without Nick or a real Google account —
and nothing here claims real Google OAuth: that needs Nick's own client ID and a real browser
sign-in (recorded in KNOWN_LIMITATIONS.md).
"""
import base64
import contextlib
import hashlib
import http.server
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from kel import connection_oauth
from kel import service as kel_service
from kel.connection_oauth import begin, claim, complete, missing_scopes, revoke
from kel.connections import Connections, custody_for, supply_credentials
from kel.core import PolicyError, Store

FIXTURE_SCOPE = 'https://www.googleapis.com/auth/drive.metadata.readonly'


class LocalProvider:
    """A local stand-in for a provider's OAuth endpoints. Records everything it is asked."""

    def __init__(self):
        self.authorize_params = []
        self.token_calls = []
        self.revoke_calls = []
        self.api_calls = []
        self.fail_token = False
        self.granted_scope = FIXTURE_SCOPE
        self.access_tokens = 0

        class Handler(http.server.BaseHTTPRequestHandler):
            def _read_form(self):
                length = int(self.headers.get('Content-Length', '0') or 0)
                raw = self.rfile.read(length).decode('utf-8') if length else ''
                return {key: value[0] for key, value in urllib.parse.parse_qs(raw).items()}

            def _send(self, status, payload):
                raw = json.dumps(payload).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except ConnectionError:
                    pass

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                owner = self.server.owner
                query = {key: value[0] for key, value in urllib.parse.parse_qs(parsed.query).items()}
                authorization = self.headers.get('Authorization')
                if parsed.path == '/authorize':
                    owner.authorize_params.append(query)
                    self._send(200, {'authorize': 'standing by'})
                elif parsed.path in ('/files', '/about'):
                    owner.api_calls.append({'path': self.path, 'authorization': authorization})
                    if str(authorization or '').startswith('Bearer '):
                        if parsed.path == '/files':
                            self._send(200, {'files': [{'id': 'f1', 'name': 'report.txt',
                                                        'mimeType': 'text/plain'}],
                                             'served_with': authorization})
                        else:
                            self._send(200, {'user': 'nick@example'})
                    else:
                        self._send(401, {'error': 'no token'})
                else:
                    self._send(404, {'error': 'no'})

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                owner = self.server.owner
                form = self._read_form()
                if parsed.path == '/token':
                    owner.token_calls.append(form)
                    if owner.fail_token:
                        self._send(400, {'error': 'invalid_grant',
                                         'error_description': 'the grant is not valid'})
                        return
                    if form.get('grant_type') == 'authorization_code':
                        if form.get('code') != 'good-code':
                            self._send(400, {'error': 'invalid_grant'})
                            return
                        # Real PKCE: the verifier must hash back to the recorded challenge.
                        last = owner.authorize_params[-1] if owner.authorize_params else {}
                        challenge = str(last.get('code_challenge') or '')
                        verifier = str(form.get('code_verifier') or '')
                        digest = hashlib.sha256(verifier.encode('ascii')).digest() if verifier else b''
                        computed = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
                        if not challenge or challenge != computed:
                            self._send(400, {'error': 'invalid_grant',
                                             'error_description': 'code verifier mismatch'})
                            return
                        owner.access_tokens += 1
                        self._send(200, {'access_token': 'at-%d' % owner.access_tokens,
                                         'refresh_token': 'rt-%d' % owner.access_tokens,
                                         'expires_in': 3600, 'scope': owner.granted_scope or '',
                                         'token_type': 'Bearer'})
                    elif form.get('grant_type') == 'refresh_token':
                        if not str(form.get('refresh_token') or '').startswith('rt-'):
                            self._send(400, {'error': 'invalid_grant'})
                            return
                        owner.access_tokens += 1
                        self._send(200, {'access_token': 'at-%d' % owner.access_tokens,
                                         'expires_in': 3600, 'scope': owner.granted_scope or '',
                                         'token_type': 'Bearer'})
                    else:
                        self._send(400, {'error': 'unsupported_grant_type'})
                elif parsed.path == '/revoke':
                    owner.revoke_calls.append(form)
                    self._send(200, {})
                else:
                    self._send(404, {'error': 'no'})

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.owner = self
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base(self):
        return 'http://127.0.0.1:%d' % self.server.server_address[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def fixture_provider(base):
    return {'id': 'fixture', 'label': 'Fixture', 'authorize_url': base + '/authorize',
            'token_url': base + '/token', 'revoke_url': base + '/revoke', 'pkce': True,
            'client_secret': True, 'extra_authorize': {},
            'scopes': {FIXTURE_SCOPE: 'See the names, types and sizes of your Drive files '
                                      '(never their contents)'},
            'default_scopes': (FIXTURE_SCOPE,)}


class OAuthCase(unittest.TestCase):
    """One connection, one stand-in provider, real engine code — no network beyond loopback."""

    ID = 'google-drive'
    REDIRECT = 'http://127.0.0.1:41999'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(self.tmp.name)
        self.provider = LocalProvider()
        self.addCleanup(self.provider.stop)
        patched = (fixture_provider(self.provider.base),)
        for attribute, value in (('PROVIDERS', patched), ('BY_ID', {'fixture': patched[0]})):
            patcher = mock.patch.object(connection_oauth, attribute, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.connections = Connections(self.store)
        self.connections.save('Google Drive', kind='oauth', base_url=self.provider.base,
                              auth_method='bearer', test_endpoint=self.provider.base + '/about',
                              oauth_provider='fixture')
        self.connections.set_credential(self.ID, ['client_id'], 'kel:connection:' + self.ID)
        supply_credentials(self.ID, {'client_id': 'client-abc', 'client_secret': 'secret-xyz'})

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def connection(self):
        return self.connections.get(self.ID)

    def visit(self, started):
        """The browser step: the provider page is really opened, recording the challenge."""
        urllib.request.urlopen(started['authorize_url'], timeout=10).read()

    def sign_in(self):
        started = begin(self.store, self.connection(), self.REDIRECT)
        self.visit(started)
        finished = complete(self.store, started['state'], code='good-code')
        self.assertTrue(finished['ok'], finished)
        return started, finished

    # -- the whole lifecycle, engine level --------------------------------------------------------
    def test_full_lifecycle_engine_level(self):
        started = begin(self.store, self.connection(), self.REDIRECT)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(started['authorize_url']).query)
        self.assertEqual(query['client_id'][0], 'client-abc')
        self.assertEqual(query['redirect_uri'][0], self.REDIRECT + '/oauth/callback')
        self.assertEqual(query['scope'][0], FIXTURE_SCOPE)
        self.assertEqual(query['code_challenge_method'][0], 'S256')
        self.assertEqual(self.connection()['auth_state'], 'pending')
        self.visit(started)

        finished = complete(self.store, started['state'], code='good-code')
        self.assertTrue(finished['ok'], finished)
        self.assertEqual(finished['state'], 'connected')
        row = self.connection()
        self.assertEqual(row['auth_state'], 'connected')
        self.assertEqual(row['auth_scopes'], [FIXTURE_SCOPE])
        self.assertGreater(row['auth_expires'], time.time())
        held = custody_for(self.ID)
        self.assertEqual(held['access_token'], 'at-1')
        self.assertEqual(held['refresh_token'], 'rt-1')
        self.assertEqual(held['client_id'], 'client-abc')          # the app's own fields survive

        checked = self.connections.test(self.ID)
        self.assertEqual(checked['last_test_state'], 'ok')
        self.assertEqual(self.provider.api_calls[-1]['authorization'], 'Bearer at-1')

        done = self.connections.run(self.ID, 'gdrive-files')
        self.assertEqual(done['state'], 'ok')
        # The request carried the sign-in token (the plain words echo is scrubbed by design);
        # the provider's own record shows exactly which token it accepted.
        self.assertEqual(self.provider.api_calls[-1]['authorization'], 'Bearer at-1')
        self.assertEqual(done['result']['served_with'], 'Bearer [redacted]')
        self.assertEqual(done['result']['files'][0]['name'], 'report.txt')

    def test_state_mismatch_replay_and_malformed_answers(self):
        unknown = complete(self.store, 'not-a-state', code='good-code')
        self.assertFalse(unknown['ok'])
        self.assertIn('does not match', unknown['note'])
        empty = complete(self.store, '')
        self.assertFalse(empty['ok'])
        missing_code = begin(self.store, self.connection(), self.REDIRECT)
        incomplete = complete(self.store, missing_code['state'])
        self.assertFalse(incomplete['ok'])
        self.assertIn('incomplete', incomplete['note'])

        started = begin(self.store, self.connection(), self.REDIRECT)
        self.visit(started)
        first = complete(self.store, started['state'], code='good-code')
        self.assertTrue(first['ok'])
        replay = complete(self.store, started['state'], code='good-code')
        self.assertFalse(replay['ok'])
        self.assertIn('already used', replay['note'])

        expired = begin(self.store, self.connection(), self.REDIRECT)
        self.visit(expired)
        with self.store.transaction() as db:
            db.execute('UPDATE oauth_flows SET expires=? WHERE state=?',
                       (time.time() - 5, expired['state']))
        too_late = complete(self.store, expired['state'], code='good-code')
        self.assertFalse(too_late['ok'])
        self.assertIn('too long', too_late['note'])
        self.assertEqual(len(self.provider.token_calls), 1,
                         'a refused or replayed answer never trades a second time')

    def test_pkce_verifier_mismatch_is_refused(self):
        started = begin(self.store, self.connection(), self.REDIRECT)
        self.visit(started)
        with self.store.transaction() as db:
            db.execute("UPDATE oauth_flows SET verifier='wrong-verifier' WHERE state=?",
                       (started['state'],))
        refused = complete(self.store, started['state'], code='good-code')
        self.assertFalse(refused['ok'])
        self.assertIn('did not accept', refused['note'])
        self.assertEqual(self.connection()['auth_state'], 'disconnected')
        self.assertNotIn('access_token', custody_for(self.ID))

    def test_refresh_when_expired_then_revoked_fails_honestly(self):
        self.sign_in()
        with self.store.transaction() as db:
            db.execute('UPDATE connections SET auth_expires=? WHERE id=?',
                       (time.time() - 5, self.ID))
        done = self.connections.run(self.ID, 'gdrive-files')
        self.assertEqual(done['state'], 'ok')
        self.assertEqual(self.provider.api_calls[-1]['authorization'], 'Bearer at-2',
                         'the refreshed access token served the call')
        refreshes = [call for call in self.provider.token_calls
                     if call.get('grant_type') == 'refresh_token']
        self.assertEqual(len(refreshes), 1)
        self.assertEqual(refreshes[0]['client_id'], 'client-abc')
        row = self.connection()
        self.assertEqual(row['auth_state'], 'connected')
        self.assertGreater(row['auth_expires'], time.time())

        self.provider.fail_token = True
        with self.store.transaction() as db:
            db.execute('UPDATE connections SET auth_expires=? WHERE id=?',
                       (time.time() - 5, self.ID))
        with self.assertRaises(PolicyError) as caught:
            self.connections.run(self.ID, 'gdrive-files')
        self.assertIn('reconnect', str(caught.exception))
        self.assertEqual(self.connection()['auth_state'], 'needs_reconnect')
        self.provider.fail_token = False
        with self.assertRaises(PolicyError) as again:
            self.connections.test(self.ID)
        self.assertIn('reconnect', str(again.exception))

    def test_revoke_returns_to_disconnected(self):
        self.sign_in()
        outcome = revoke(self.store, self.connection())
        self.assertEqual(outcome['state'], 'disconnected')
        self.assertTrue(self.provider.revoke_calls, 'the provider was told')
        self.assertEqual(self.provider.revoke_calls[0]['token'], 'rt-1')
        self.assertEqual(custody_for(self.ID), {})
        self.assertEqual(self.connection()['auth_state'], 'disconnected')
        after = self.connections.run(self.ID, 'gdrive-files')
        self.assertEqual(after['state'], 'refused',
                         'with no sign-in the service answers, and Kel reports it honestly')
        self.assertIsNone(self.provider.api_calls[-1]['authorization'])

    def test_wrong_connection_cannot_use_anothers_credential(self):
        self.sign_in()
        self.connections.save('Drive Other', kind='oauth', base_url=self.provider.base,
                              auth_method='bearer', oauth_provider='fixture',
                              test_endpoint=self.provider.base + '/about')
        self.connections.set_credential('drive-other', ['client_id'], 'kel:connection:drive-other')
        supply_credentials('drive-other', {'client_id': 'client-other'})
        other = self.connections.test('drive-other')
        self.assertEqual(other['last_test_state'], 'refused')
        self.assertIsNone(self.provider.api_calls[-1]['authorization'],
                          "one connection's token never rides another's request")
        self.assertEqual(custody_for(self.ID)['access_token'], 'at-1')

    def test_missing_scopes_surfaced_honestly(self):
        self.provider.granted_scope = ''  # the provider grants nothing
        started = begin(self.store, self.connection(), self.REDIRECT)
        self.visit(started)
        finished = complete(self.store, started['state'], code='good-code')
        self.assertTrue(finished['ok'])
        self.assertEqual(self.connection()['auth_scopes'], [])
        self.assertIn('did not grant', finished['note'])
        with self.assertRaises(PolicyError) as caught:
            self.connections.run(self.ID, 'gdrive-files')
        self.assertIn('not granted', str(caught.exception))
        self.assertIn('Drive files', str(caught.exception), 'the permission is named in plain words')

    def test_tokens_never_reach_durable_stories(self):
        self.sign_in()
        self.connections.run(self.ID, 'gdrive-files')
        revoke(self.store, self.connection())
        with contextlib.closing(self.store.connect()) as db:
            stories = []
            for table in ('messages', 'approvals', 'approval_actions', 'connection_events',
                          'guardrail_decisions', 'oauth_flows', 'jobs', 'submissions'):
                try:
                    rows = db.execute('SELECT * FROM %s' % table).fetchall()
                except Exception:
                    continue
                stories.append(json.dumps([dict(row) for row in rows]))
        joined = ' '.join(stories)
        for secret in ('at-1', 'rt-1', 'secret-xyz'):
            self.assertNotIn(secret, joined, '%s must never land in durable state' % secret)


class OAuthHttpJourney(unittest.TestCase):
    """The shell's real path: engine HTTP, the browser callback, one-time claim, bridge call."""

    ID = 'google-drive'
    SECRET_FIELDS = {'client_id': 'client-abc', 'client_secret': 'secret-xyz'}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.root = Path(self.tmp.name) / 'engine'
        self.root.mkdir(parents=True)
        self.provider = LocalProvider()
        self.addCleanup(self.provider.stop)
        patched = (fixture_provider(self.provider.base),)
        for attribute, value in (('PROVIDERS', patched), ('BY_ID', {'fixture': patched[0]})):
            patcher = mock.patch.object(connection_oauth, attribute, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.engine = threading.Thread(target=kel_service.serve,
                                       args=(str(self.root), 0), daemon=True)
        self.engine.start()
        self.descriptor = self._wait_for_engine()

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _wait_for_engine(self):
        path = self.root / 'desktop-session.json'
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                data = json.loads(path.read_text(encoding='utf-8-sig'))
                if data.get('url') and data.get('token'):
                    return data
            except Exception:
                pass
            time.sleep(0.1)
        self.fail('the engine did not come up')

    def post(self, body):
        request = urllib.request.Request(
            self.descriptor['url'].rstrip('/') + '/api/connections',
            data=json.dumps(body).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + self.descriptor['token'],
                     'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            payload = error.read().decode('utf-8', 'replace')
            raise AssertionError('engine answered %d: %s' % (error.code, payload)) from None

    def get_public(self, path):
        request = urllib.request.Request(self.descriptor['url'].rstrip('/') + path, method='GET')
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode('utf-8', 'replace')

    def seed(self):
        self.post({'action': 'save', 'name': 'Google Drive', 'kind': 'oauth',
                   'base_url': self.provider.base, 'auth_method': 'bearer',
                   'test_endpoint': self.provider.base + '/about', 'oauth_provider': 'fixture'})
        self.post({'action': 'set_credential', 'id': self.ID,
                   'fields': ['client_id', 'client_secret'],
                   'credential_ref': 'kel:connection:' + self.ID})
        self.post({'action': 'supply', 'id': self.ID, 'credentials': dict(self.SECRET_FIELDS)})

    def test_http_lifecycle_with_browser_callback_claim_and_bridge_call(self):
        self.seed()
        started = self.post({'action': 'oauth-initiate', 'id': self.ID})
        self.assertIn('/authorize?', started['authorize_url'])
        self.assertIn('code_challenge=', started['authorize_url'])
        self.assertEqual(started['redirect_uri'],
                         self.descriptor['url'].rstrip('/') + '/oauth/callback')
        state = urllib.parse.parse_qs(
            urllib.parse.urlparse(started['authorize_url']).query)['state'][0]
        # The browser really opens the provider page (the fixture records the PKCE challenge).
        urllib.request.urlopen(started['authorize_url'], timeout=10).read()

        # The browser comes back with no bearer at all — the single-use state is the proof.
        status, html = self.get_public('/oauth/callback?state=%s&code=good-code' % state)
        self.assertEqual(status, 200)
        self.assertIn('sign-in finished', html)
        self.assertNotIn('at-1', html, 'no token ever reaches the sign-in page')

        row = self.post({'action': 'get', 'id': self.ID})
        self.assertEqual(row['auth_state'], 'connected')
        self.assertEqual(row['auth_scopes'], [FIXTURE_SCOPE])

        claimed = self.post({'action': 'oauth-claim', 'id': self.ID})
        self.assertTrue(claimed['claimed'])
        self.assertEqual(claimed['credentials']['access_token'], 'at-1')
        again = self.post({'action': 'oauth-claim', 'id': self.ID})
        self.assertFalse(again['claimed'])
        self.assertEqual(again['fields'], [])

        catalog = self.post({'action': 'catalog'})
        usable = [item for item in catalog['actions'] if item['id'] == 'gdrive-files']
        self.assertTrue(usable and usable[0]['usable'])
        called = self.post({'action': 'call', 'action_id': 'gdrive-files'})
        self.assertEqual(called['state'], 'ok')
        self.assertEqual(self.provider.api_calls[-1]['authorization'], 'Bearer at-1')
        self.assertEqual(called['result']['served_with'], 'Bearer [redacted]')

        revoked = self.post({'action': 'oauth-revoke', 'id': self.ID})
        self.assertEqual(revoked['state'], 'disconnected')
        self.assertEqual(self.provider.revoke_calls[0]['token'], 'rt-1')
        self.assertEqual(custody_for(self.ID), {})

    def test_browser_callbacks_that_cannot_be_trusted_are_refused_plainly(self):
        self.seed()
        status, html = self.get_public('/oauth/callback')
        self.assertEqual(status, 200)
        self.assertIn('not finished', html)
        status, html = self.get_public('/oauth/callback?state=nope&code=good-code')
        self.assertIn('not finished', html)
        started = self.post({'action': 'oauth-initiate', 'id': self.ID})
        state = urllib.parse.parse_qs(
            urllib.parse.urlparse(started['authorize_url']).query)['state'][0]
        # The person said no on the provider's page: the flow closes honestly, nothing trades.
        status, html = self.get_public('/oauth/callback?state=%s&error=access_denied' % state)
        self.assertIn('not finished', html)
        self.assertEqual(self.provider.token_calls, [])
        self.assertEqual(self.post({'action': 'get', 'id': self.ID})['auth_state'], 'disconnected')
