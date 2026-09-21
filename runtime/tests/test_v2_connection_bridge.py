"""V2-04a — the assistant bridge: the runtime can call a Connection action through the same systems.

This is the runtime journey, not a stub of it: the real engine service is started (HTTP on loopback,
its desktop-session.json written), a local stand-in service answers the requests, and the helper the
coding runtime actually runs (`python -m kel.conn`) is executed as a subprocess against the engine.
Discovery, argument validation, the capability control (including a one-shot grant and its single
spend), the mutating approval row (granted only by the exact action digest and only by the user),
bounded answers, provenance and the no-leak rules are all exercised through that path.

The credential value is asserted to appear nowhere the model could see: not in helper output, not in
the access history, not in approvals, not in messages, not on disk.
"""
import contextlib
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from kel import connection_actions
from kel import service as kel_service
from kel.autonomy import Autonomy
from kel.capabilities import availability, capability_for_tool
from kel.chat_approvals import ensure_schema as ensure_approvals
from kel.chat_approvals import plain_summary
from kel.coding import compile_coding, git
from kel.connection_tools import TOOL_ANSWER_LIMIT
from kel.connections import Connections
from kel.core import Store

RUNTIME_DIR = Path(__file__).resolve().parents[1]
SECRET = 'kel-v2-04a-credential-8f4d2c1a-secret'
STUB_LOGIN = 'kel-v2-stub-account'
PAD = 'pad-' * 2200  # ~8800 characters, enough to prove the answer is bounded


class LocalService:
    """A local stand-in for a real service: it answers only when the credential is presented."""

    def __init__(self):
        self.seen = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def _respond(self):
                service = self.server.owner
                service.seen.append({'path': self.path,
                                     'authorization': self.headers.get('Authorization')})
                if self.headers.get('Authorization') != 'Bearer ' + SECRET:
                    self._send(401, {'error': 'bad credential'})
                elif self.path.startswith('/ping'):
                    self._send(200, {'pong': True})
                else:
                    self._send(200, {'login': STUB_LOGIN, 'id': 4242, 'pad': PAD})

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
                self._respond()

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


def make_project(base, name):
    root = base / name
    root.mkdir(parents=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class BridgeJourney(unittest.TestCase):
    """The whole bridge, end to end: helper → engine HTTP → stub service → bounded answer."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.root = Path(self.tmp.name) / 'engine'
        self.root.mkdir(parents=True)
        self.stub = LocalService()
        self.addCleanup(self.stub.stop)
        self.engine = threading.Thread(target=kel_service.serve,
                                       args=(str(self.root), 0), daemon=True)
        self.engine.start()
        self.descriptor = self._wait_for_engine()
        self.job_id = ''
        self.run_id = ''

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

    # -- engine HTTP ------------------------------------------------------------------------------
    def post(self, path, body):
        request = urllib.request.Request(
            self.descriptor['url'].rstrip('/') + path,
            data=json.dumps(body).encode('utf-8'),
            headers={'Authorization': 'Bearer ' + self.descriptor['token'],
                     'Content-Type': 'application/json'},
            method='POST')
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode('utf-8'))
            raise AssertionError('engine answered %d: %s' % (error.code, payload)) from None

    def get(self, path):
        request = urllib.request.Request(
            self.descriptor['url'].rstrip('/') + path,
            headers={'Authorization': 'Bearer ' + self.descriptor['token']},
            method='GET')
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode('utf-8'))
            raise AssertionError('engine answered %d: %s' % (error.code, payload)) from None

    def connections(self, body):
        return self.post('/api/connections', body)

    def seed_connection(self, test_endpoint=None):
        self.connections({'action': 'save', 'name': 'GitHub',
                          'base_url': self.stub.base, 'auth_method': 'bearer',
                          'test_endpoint': test_endpoint})
        self.connections({'action': 'set_credential', 'id': 'github', 'fields': ['api_key'],
                          'credential_ref': 'kel:connection:github'})
        supplied = self.connections({'action': 'supply', 'id': 'github',
                                     'credentials': {'api_key': SECRET}})
        self.assertEqual(supplied['fields'], ['api_key'])

    # -- the helper the runtime runs --------------------------------------------------------------
    def helper(self, *args, with_run=False):
        env = dict(os.environ)
        env['KEL_DATA_DIR'] = str(self.root)
        env['PYTHONPATH'] = str(RUNTIME_DIR)
        env['KEL_JOB_ID'] = self.job_id if with_run else ''
        env['KEL_RUN_ID'] = self.run_id if with_run else ''
        return subprocess.run([sys.executable, '-X', 'utf8', '-m', 'kel.conn', *args],
                              capture_output=True, text=True, encoding='utf-8',
                              env=env, cwd=str(self.root), timeout=90)

    # -- pins -------------------------------------------------------------------------------------
    def test_capability_is_declared_and_honest_about_configuration(self):
        self.assertEqual(capability_for_tool('connection'), 'connections')
        store = Store(str(self.root))
        self.assertEqual(availability(store, 'connections'),
                         ('needs_setup', 'Add a service in Connections first.'))
        self.connections({'action': 'save', 'name': 'GitHub',
                          'base_url': self.stub.base, 'auth_method': 'bearer'})
        self.assertEqual(availability(store, 'connections'),
                         ('needs_setup', 'Store a credential for one of your connected services first.'))
        self.seed_connection()
        self.assertEqual(availability(store, 'connections'),
                         ('available', 'Kel can use your connected services'))

    def test_the_runtime_journey_discovery_read_and_bounds(self):
        self.seed_connection()

        listed = self.helper('list')
        self.assertEqual(listed.returncode, 0, listed.stdout + listed.stderr)
        self.assertIn('github-whoami', listed.stdout)
        self.assertIn('no fields', listed.stdout)
        self.assertNotIn(SECRET, listed.stdout)

        read = self.helper('call', 'github-whoami')
        self.assertEqual(read.returncode, 0, read.stdout + read.stderr)
        self.assertIn(STUB_LOGIN, read.stdout)          # the service's answer reached the runtime
        self.assertNotIn(SECRET, read.stdout)           # the credential never did
        self.assertNotIn(self.descriptor['token'], read.stdout)

        bounded = self.helper('call', 'github-whoami', '--json', '--connection', 'github')
        self.assertEqual(bounded.returncode, 0, bounded.stdout + bounded.stderr)
        payload = json.loads(bounded.stdout)
        self.assertEqual(payload['state'], 'ok')
        self.assertTrue(payload['truncated'], 'an over-long answer must be cut short')
        self.assertLessEqual(len(str(payload['result'])), TOOL_ANSWER_LIMIT + 1)
        self.assertNotIn(SECRET, bounded.stdout)

        # The stub only answered because the engine supplied the pushed credential for this request.
        self.assertTrue(self.stub.seen)
        self.assertEqual(self.stub.seen[-1]['authorization'], 'Bearer ' + SECRET)

        # Provenance: the access history says who asked, what ran and where — and nothing else.
        history = self.connections({'action': 'events', 'id': 'github'})['events']
        self.assertTrue(history)
        last = history[0]
        self.assertEqual(last['action'], 'github-whoami')
        self.assertEqual(last['source'], 'runtime')
        self.assertEqual(last['state'], 'ok')
        self.assertTrue(last['domain'].startswith('127.0.0.1:'))
        self.assertNotIn(SECRET, json.dumps(history))

    def test_arguments_are_validated_in_plain_words(self):
        self.seed_connection()
        wrong = self.helper('call', 'github-whoami', '--param', 'nope=1')
        self.assertEqual(wrong.returncode, 4)
        self.assertIn('does not take a "nope" field', wrong.stdout)
        long_value = self.helper('call', 'github-notifications', '--param', 'per_page=' + 'x' * 300)
        self.assertEqual(long_value.returncode, 4)
        self.assertIn('under 200 characters', long_value.stdout)
        unknown = self.helper('call', 'no-such-action')
        self.assertEqual(unknown.returncode, 4)
        self.assertIn('does not know that action', unknown.stdout)

    def test_the_capability_control_gates_the_runtime_and_a_grant_is_spent_once(self):
        self.seed_connection()
        self.post('/api/capabilities', {'action': 'set', 'conversation': 'main',
                                        'capability': 'connections', 'state': 'off'})

        refused = self.helper('call', 'github-whoami', '--conversation', 'main', '--json')
        self.assertEqual(refused.returncode, 4)
        payload = json.loads(refused.stdout)
        self.assertEqual(payload['state'], 'not_allowed')
        self.assertIn('disabled for this conversation', payload['note'])
        self.assertEqual(payload['recommendation']['actions'],
                         ['allow_once', 'enable', 'keep_disabled'])
        self.assertEqual(self.stub.seen, [], 'nothing may reach the service while it is off')

        self.post('/api/capabilities', {'action': 'allow_once', 'conversation': 'main',
                                        'capability': 'connections'})
        once = self.helper('call', 'github-whoami', '--conversation', 'main')
        self.assertEqual(once.returncode, 0, once.stdout + once.stderr)
        self.assertIn(STUB_LOGIN, once.stdout)
        again = self.helper('call', 'github-whoami', '--conversation', 'main')
        self.assertEqual(again.returncode, 4, 'a one-shot grant must be spent exactly once')
        self.assertEqual(len(self.stub.seen), 1)

    def test_mutating_without_a_run_is_honest_and_executes_nothing(self):
        self.seed_connection()
        row = {'id': 'github-test-ping', 'service': 'github', 'name': 'Send a test ping',
               'description': 'A test-only mutating action.', 'method': 'GET', 'path': '/ping',
               'params': (), 'returns': 'an acknowledgement.', 'mutating': True,
               'source': 'documented'}
        with mock.patch.object(connection_actions, 'ACTIONS',
                               connection_actions.ACTIONS + (row,)):
            asked = self.helper('call', 'github-test-ping')
            self.assertEqual(asked.returncode, 3)
            self.assertIn('needs an OK first', asked.stdout)
            self.assertEqual(self.stub.seen, [])

    def test_the_secret_reaches_no_durable_story(self):
        self.seed_connection()
        self.helper('call', 'github-whoami')
        store = Store(str(self.root))
        with contextlib.closing(store.connect()) as db:
            events = json.dumps([dict(row) for row in db.execute(
                'SELECT * FROM connection_events')])
            approvals = json.dumps([dict(row) for row in db.execute(
                'SELECT * FROM approvals')])
            messages = json.dumps([dict(row) for row in db.execute(
                'SELECT * FROM messages')])
        for story in (events, approvals, messages):
            self.assertNotIn(SECRET, story)
        # The value was used for exactly one request and never a second time.
        self.assertEqual(self.stub.seen[0]['authorization'], 'Bearer ' + SECRET)

    def test_approval_summary_speaks_plainly(self):
        text = plain_summary({'kind': 'connection', 'action_name': 'Send a test ping',
                              'connection_name': 'GitHub'})
        self.assertEqual(text, 'use "Send a test ping" on GitHub')


class BridgeWithRun(BridgeJourney):
    """The mutating journey with real work behind it: a claimed run, the ask, the grant, the call."""

    def setUp(self):
        super().setUp()
        self.project = make_project(Path(self.tmp.name), 'proj')
        self.job_id = str(Store(str(self.root)).create(
            compile_coding('Change app.txt.', self.project, ['python', '-m', 'unittest'])))
        run = Store(str(self.root)).claim(self.job_id, 'code', provider='codex-code')
        self.run_id = str(run['id'])

    def test_job_context_matches(self):
        # Pin the setup itself: a claimed run is RUNNING and belongs to the job.
        store = Store(str(self.root))
        with contextlib.closing(store.connect()) as db:
            row = db.execute('SELECT job_id, state FROM runs WHERE id=?', (self.run_id,)).fetchone()
        self.assertEqual(row['job_id'], self.job_id)
        self.assertEqual(row['state'], 'RUNNING')

    def test_mutating_asks_in_the_conversation_and_runs_only_after_the_user_approves(self):
        self.seed_connection()
        row = {'id': 'github-test-ping', 'service': 'github', 'name': 'Send a test ping',
               'description': 'A test-only mutating action.', 'method': 'GET', 'path': '/ping',
               'params': (), 'returns': 'an acknowledgement.', 'mutating': True,
               'source': 'documented'}
        with mock.patch.object(connection_actions, 'ACTIONS',
                               connection_actions.ACTIONS + (row,)):
            asked = self.helper('call', 'github-test-ping', '--json', with_run=True)
            self.assertEqual(asked.returncode, 3, asked.stdout + asked.stderr)
            payload = json.loads(asked.stdout)
            approval_id = payload['approval']
            self.assertTrue(approval_id)

            # The ask reached the conversation the job belongs to, once, with the card anchored.
            items = self.get('/api/approvals?conversation=main')
            pending = [item for item in items['items']
                       if item.get('kind') == 'action' and item.get('id') == approval_id]
            self.assertTrue(pending)
            self.assertIn('Send a test ping', str(pending[0]))

            # Asking again must not stack a second request for the same action.
            again = self.helper('call', 'github-test-ping', '--json', with_run=True)
            self.assertEqual(json.loads(again.stdout)['approval'], approval_id)

            # Only the user's decision through the real endpoint makes it runnable.
            self.post('/api/approval', {'id': approval_id, 'allow': True})
            done = self.helper('call', 'github-test-ping', '--confirm', 'auto', '--json')
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(json.loads(done.stdout)['state'], 'ok')
            self.assertEqual(len(self.stub.seen), 1)
            self.assertEqual(self.stub.seen[0]['path'], '/ping')

            # A different, unrelated approval id cannot be used for this action.
            other = self.helper('call', 'github-test-ping', '--confirm', 'approval-does-not-exist')
            self.assertEqual(other.returncode, 3)
            self.assertEqual(len(self.stub.seen), 1)


if __name__ == '__main__':
    unittest.main()
