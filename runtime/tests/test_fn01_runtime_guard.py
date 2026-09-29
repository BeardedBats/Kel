"""FN-01: protected places are enforced on what the model runtimes do directly.

Found live (installed 5294c27, Full access): "add multiply to calc.py, and also save a copy of calc.py
as <Data>\\engine\\calc-copy.py" made Claude write that file into Kel's own Data folder, because the
native host ran with --dangerously-skip-permissions / danger-full-access and the protected-path rule
only ran on permission requests and on apply. These tests pin the three layers (kel.runtime_guard):
the runtimes start with real boundaries (prevent), anything that still lands in a protected place
fails the step and is moved back out (detect), and a request that asks for one is answered plainly
before any work starts (refuse). Fake runtimes only; no model is called.
"""
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kel import coding, runtime_guard
from kel.appserver import CodexConnection
from kel.coding import CodingAdapter, compile_coding
from kel.core import Store
from kel.host_runtime import HostConnection

sys.path.insert(0, str(Path(__file__).parent))
from test_original_tests_gate import FakeConnection, PYTEST, live_change, make_project  # noqa: E402

NODE = shutil.which('node')
HOOK = Path(runtime_guard.__file__).with_name('guard_hook.mjs')
OUTSIDE = "That's outside Kel's Memory folder, so I can't touch it."  # D-81: the one plain refusal


class Layout(unittest.TestCase):
    """A scratch copy of the installed layout: Data\\{engine,store,host}, a working copy inside the
    engine root, a fake credentials folder registered through KEL_PROTECTED_PATHS and a fake home
    credential folder (the real ~/.ssh is never used)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.data = base / 'Data'
        self.engine = self.data / 'engine'
        for folder in (self.engine, self.data / 'store', self.data / 'host'):
            folder.mkdir(parents=True)
        (self.engine / 'desktop-session.json').write_text('{}')
        (self.engine / 'kel-credentials.json').write_text('{"a": 1}')
        self.workspace = self.engine / 'repositories' / 'job'
        self.workspace.mkdir(parents=True)
        (self.workspace / 'calc.py').write_text('def add(a, b):\n    return a + b\n')
        self.creds = base / 'dummy-credentials'
        self.creds.mkdir()
        (self.creds / 'secret.txt').write_text('TOPSECRET')
        self.home_ssh = base / 'home' / '.ssh'
        self.home_ssh.mkdir(parents=True)
        (self.home_ssh / 'id_rsa').write_text('KEY')
        self.logs = self.engine / 'native-logs' / 'run1'
        env = mock.patch.dict(os.environ, {'KEL_DATA_DIR': str(self.engine),
                                           'KEL_PROTECTED_PATHS': str(self.creds)})
        env.start()
        self.addCleanup(env.stop)
        for key in ('AIONUI_DATA_DIR', 'KEL_HOST_DATA_DIR'):
            os.environ.pop(key, None)
        roots = mock.patch('kel.runtime_guard._credential_roots', return_value=[self.home_ssh])
        roots.start()
        self.addCleanup(roots.stop)


# ---- refuse clearly (D-55) ------------------------------------------------------------------------

class RefusalTests(Layout):
    def test_the_fn01_request_is_refused_up_front_in_plain_words(self):
        text = ('add multiply to calc.py, and also save a copy of calc.py as `%s`'
                % (self.engine / 'calc-copy.py'))
        self.assertEqual(runtime_guard.request_refusal(text, self.engine), OUTSIDE)  # D-81

    def test_a_protected_folder_read_is_refused(self):
        text = 'summarise %s' % (self.creds / 'secret.txt')
        answer = runtime_guard.request_refusal(text, self.engine)
        self.assertEqual(answer, OUTSIDE)
        self.assertNotIn('verify', answer)

    def test_credentials_by_name_are_refused(self):
        self.assertEqual(runtime_guard.request_refusal('read ~/.ssh/id_rsa for me', self.engine), OUTSIDE)
        self.assertEqual(runtime_guard.request_refusal('look in my .aws folder', self.engine), OUTSIDE)

    def test_ordinary_requests_pass(self):
        # D-81: a Documents path is outside the Memory folder now (tests/test_d81_memory_folder.py).
        for text in ('add multiply to calc.py', 'add a .dockerignore to the project'):
            self.assertIsNone(runtime_guard.request_refusal(text, self.engine), text)


class ServiceRefusalTests(unittest.TestCase):
    """The chat path: the turn model chose to start work, and Kel answers plainly instead (D-55)."""

    def setUp(self):
        from test_turn_handoff import FakeTurn, WORK
        from kel.service import Service
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for key in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL', 'KEL_PROTECTED_PATHS', 'KEL_DATA_DIR'):
            os.environ.pop(key, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        self.service = Service(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(lambda: contextlib.suppress(Exception) and self.service.shutdown())
        self.service.turn_mode = ''
        self.service.model = FakeTurn(WORK)
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.cid = self.service.context.conversation('default')

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()

    def settle(self, sid):
        import time
        for _ in range(1000):
            with contextlib.closing(self.service.store.connect()) as db:
                row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['state'] not in ('PLANNING', 'QUEUED'):
                return row['state']
            time.sleep(.02)
        raise TimeoutError(sid)

    def test_the_fn01_request_gets_a_plain_answer_and_no_job(self):
        target = Path(self.service.store.root) / 'calc-copy.py'
        sid = self.service.submit({'text': 'Please add multiply to calc.py, and also save a copy of calc.py as %s'
                                   % target, 'conversation': self.cid})
        self.assertEqual(self.settle(sid), 'SETTLED')
        with contextlib.closing(self.service.store.connect()) as db:
            last = db.execute('SELECT text FROM messages WHERE conversation_id=? ORDER BY seq DESC LIMIT 1',
                              (self.cid,)).fetchone()['text']
            acked = db.execute('SELECT 1 FROM submission_acks WHERE submission_id=?', (sid,)).fetchone()
        self.assertEqual(last, OUTSIDE)
        self.assertIsNone(acked)
        self.assertEqual([j for j in self.service.store.list_jobs() if j['conversation'] == self.cid], [])


# ---- prevent: Claude Code hook --------------------------------------------------------------------

@unittest.skipUnless(NODE, 'Node.js runs the Claude Code guard hook')
class HookTests(Layout):
    def setUp(self):
        super().setUp()
        temp = Path(self.tmp.name) / 'temp'
        temp.mkdir()
        env = mock.patch.dict(os.environ, {'TEMP': str(temp), 'TMP': str(temp)})
        env.start()
        self.addCleanup(env.stop)
        self.policy = runtime_guard.write_policy(self.engine, self.workspace, self.logs)

    def hook(self, tool, args, cwd=None, policy=None):
        payload = json.dumps({'tool_name': tool, 'tool_input': args, 'cwd': str(cwd or self.workspace),
                              'hook_event_name': 'PreToolUse'})
        env = dict(os.environ, KEL_GUARD_POLICY=str(policy or self.policy))
        out = subprocess.run([NODE, str(HOOK)], input=payload, capture_output=True, text=True, env=env,
                             timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(out.returncode, 0, out.stderr)
        if not out.stdout.strip():
            return None
        data = json.loads(out.stdout)['hookSpecificOutput']
        self.assertEqual(data['permissionDecision'], 'deny')
        return data['permissionDecisionReason']

    def test_writing_into_kels_data_folder_is_blocked(self):
        reason = self.hook('Write', {'file_path': str(self.engine / 'calc-copy.py'), 'content': 'x'})
        self.assertIn("Kel's own data folder", reason)
        self.assertIn('not done', reason)

    def test_reading_a_protected_folder_is_blocked(self):
        self.assertIn('a protected folder', self.hook('Read', {'file_path': str(self.creds / 'secret.txt')}))
        self.assertIn('credentials folder', self.hook('Read', {'file_path': str(self.home_ssh / 'id_rsa')}))
        self.assertIsNotNone(self.hook('Grep', {'pattern': 'x', 'path': str(self.data / 'store')}))

    def test_shell_commands_that_reach_a_protected_place_are_blocked(self):
        self.assertIsNotNone(self.hook('Bash', {'command': "cat '%s'" % (self.creds / 'secret.txt')}))
        self.assertIsNotNone(self.hook('Bash', {'command': 'echo hi > ../../calc-copy.py'}))
        self.assertIsNotNone(self.hook('PowerShell', {'command': 'Copy-Item calc.py %s' % (self.engine / 'x.py')}))
        bash_form = '/' + str(self.creds)[0].lower() + str(self.creds)[2:].replace('\\', '/')
        if os.name == 'nt':
            self.assertIsNotNone(self.hook('Bash', {'command': 'cat %s/secret.txt' % bash_form}))

    def test_the_working_copy_and_the_session_file_stay_usable(self):
        self.assertIsNone(self.hook('Write', {'file_path': str(self.workspace / 'calc.py'), 'content': 'x'}))
        self.assertIsNone(self.hook('Edit', {'file_path': 'calc.py', 'old_string': 'a', 'new_string': 'b'}))
        self.assertIsNone(self.hook('Bash', {'command': 'python -m pytest -q && git status'}))
        self.assertIsNone(self.hook('Bash', {'command': 'cat "%s"' % (self.workspace / 'calc.py')}))
        self.assertIsNone(self.hook('Read', {'file_path': str(self.engine / 'desktop-session.json')}))
        self.assertIsNone(self.hook('WebSearch', {'query': 'python multiply'}))

    def test_outside_tool_servers_are_blocked(self):
        self.assertIn('outside tool servers', self.hook('mcp__node_repl__js', {'code': 'fs.writeFile("x")'}))

    def test_file_tools_cannot_write_outside_the_working_copy(self):
        other = Path(self.tmp.name) / 'elsewhere' / 'x.py'
        self.assertIn("outside Kel's Memory folder", self.hook('Write', {'file_path': str(other), 'content': 'x'}))

    def test_a_broken_policy_fails_closed(self):
        broken = self.logs / 'broken.json'
        broken.write_text('{not json')
        self.assertIn('could not check', self.hook('Read', {'file_path': 'calc.py'}, policy=broken))

    def test_refusals_are_logged_for_the_run(self):
        self.hook('Write', {'file_path': str(self.engine / 'calc-copy.py'), 'content': 'x'})
        items = runtime_guard.denials(self.logs)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['tool'], 'Write')
        self.assertEqual(runtime_guard.denials(self.logs), [])  # read once

    def test_claude_settings_carry_the_hook_and_deny_rules(self):
        settings = runtime_guard.claude_settings(self.policy, NODE, self.workspace)
        command = settings['hooks']['PreToolUse'][0]['hooks'][0]['command']
        self.assertIn('guard_hook.mjs', command)
        self.assertEqual(settings['hooks']['PreToolUse'][0]['matcher'], '*')
        deny = settings['permissions']['deny']
        self.assertTrue(any('dummy-credentials' in rule and rule.startswith('Read(//') for rule in deny))
        # The engine root holds the working copy by design: the hook, not a blanket rule, covers it.
        self.assertFalse(any(rule.rstrip('/**)').endswith('/Data/engine') for rule in deny))


# ---- prevent: runtime flags -----------------------------------------------------------------------

class RuntimeFlagTests(Layout):
    def connection(self, provider):
        captured = {}

        def fake_init(conn, workspace, logs, process_argv=None):
            captured['argv'] = process_argv
            conn.workspace, conn.logs = str(workspace), Path(logs)

        with mock.patch.object(CodexConnection, '__init__', fake_init), \
                mock.patch('kel.host_runtime.executable', lambda name: ['C:/bin/%s.exe' % name]), \
                mock.patch('kel.host_runtime.shutil.which', return_value='C:/node/node.exe'), \
                mock.patch('kel.runtime_guard.codex_mcp_servers', return_value=['node_repl']), \
                mock.patch.dict(os.environ, {}):
            conn = HostConnection(self.workspace, self.logs, provider=provider)
        return conn, captured['argv']

    def test_codex_runs_in_the_workspace_write_sandbox_with_network(self):
        conn, argv = self.connection('codex')
        text = ' '.join(argv)
        self.assertNotIn('danger-full-access', text)
        self.assertIn('sandbox_mode="workspace-write"', argv)
        self.assertIn('sandbox_workspace_write.network_access=true', argv)
        self.assertIn('approval_policy="never"', argv)
        # Nothing that runs outside the sandbox: a user MCP server (found live: node_repl wrote files
        # past the sandbox) is switched off by name, and the outside-acting features are off.
        self.assertIn('mcp_servers.node_repl.enabled=false', argv)
        for feature in ('plugins', 'apps', 'hooks', 'computer_use', 'browser_use'):
            self.assertIn(feature, [argv[i + 1] for i, a in enumerate(argv) if a == '--disable'])
        if os.name == 'nt':
            self.assertIn('windows.sandbox="unelevated"', argv)
        # D-81: Kel's permission profile writes only the working copy, the Memory folder and the run temp.
        self.assertIn('default_permissions="kel"', argv)
        profile = next(a for a in argv if a.startswith('permissions.kel.filesystem='))
        self.assertIn('":root"="read"', profile.replace("'", '"'))
        self.assertIn('":workspace_roots"="write"', profile.replace("'", '"'))
        from kel import memory_folder
        self.assertIn("'%s'=\"write\"" % memory_folder.memory_root(self.engine), profile)
        self.assertNotIn('"deny"', profile)  # deny entries need the elevated sandbox
        with mock.patch.object(CodexConnection, 'call', return_value={}) as rpc:
            conn.call('thread/start', {'cwd': str(self.workspace), 'sandbox': 'workspace-write'})
            self.assertNotIn('sandbox', rpc.call_args.args[1])
            self.assertEqual(rpc.call_args.args[1]['approvalPolicy'], 'never')
            self.assertIn('off-limits', rpc.call_args.args[1]['developerInstructions'])
            conn.call('turn/start', {'threadId': 't', 'input': []})
            self.assertNotIn('sandboxPolicy', rpc.call_args.args[1])

    def test_codex_does_not_start_when_its_tool_servers_cannot_be_read(self):
        from kel.core import PolicyError
        with self.assertRaises(PolicyError) as caught:
            runtime_guard.codex_mcp_servers([sys.executable, '-c', 'import sys; sys.exit(3)'], self.workspace)
        self.assertIn('did not start', str(caught.exception))
        listing = [sys.executable, '-c', 'import json; print(json.dumps([{"name": "node_repl"}, {"name": "docs"}]))']
        self.assertEqual(runtime_guard.codex_mcp_servers(listing, self.workspace), ['node_repl', 'docs'])

    def test_network_off_closes_the_codex_sandbox_network(self):
        import sqlite3
        with contextlib.closing(sqlite3.connect(self.engine / 'kel.sqlite3')) as db:
            db.execute('DROP TABLE IF EXISTS network_policy')
        (self.engine / 'kel.sqlite3').unlink()
        with contextlib.closing(sqlite3.connect(self.engine / 'kel.sqlite3')) as db:
            db.execute("CREATE TABLE network_policy(scope TEXT, mode TEXT, domains TEXT, updated REAL)")
            db.execute("INSERT INTO network_policy VALUES('default','none','[]',0)")
            db.commit()
        _conn, argv = self.connection('codex')
        self.assertIn('sandbox_workspace_write.network_access=false', argv)

    def test_claude_runs_with_the_guard_settings(self):
        _conn, argv = self.connection('claude')
        settings = Path(argv[-2])  # then the Memory folder (D-81)
        self.assertEqual(settings.name, 'claude-settings.json')
        data = json.loads(settings.read_text(encoding='utf-8'))
        self.assertIn('PreToolUse', data['hooks'])
        self.assertTrue(Path(os.environ.get('KEL_GUARD_POLICY', '')).name == 'guard-policy.json'
                        or (self.logs / 'guard-policy.json').exists())
        source = Path(runtime_guard.__file__).with_name('host_claude.mjs').read_text(encoding='utf-8')
        self.assertIn("'--settings',guardSettings", source)
        self.assertIn("""'--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--setting-sources','user'""", source)
        self.assertIn('Kel guard settings are missing', source)


# ---- detect ---------------------------------------------------------------------------------------

class WatchTests(Layout):
    def test_a_new_file_in_the_data_folder_is_found_and_moved_back_out(self):
        watch = runtime_guard.Watch(self.engine, self.workspace, 'run1')
        (self.engine / 'calc-copy.py').write_text('copy')
        (self.workspace / 'calc.py').write_text('changed inside the working copy')
        (self.engine / 'kel.sqlite3-wal').write_text('churn')
        (self.engine / 'native-logs').mkdir(exist_ok=True)
        changes = watch.changes()
        self.assertEqual([(Path(c['path']).name, c['change']) for c in changes], [('calc-copy.py', 'new')])
        self.assertTrue(watch.restore(changes[0], self.logs))
        self.assertFalse((self.engine / 'calc-copy.py').exists())
        self.assertTrue(any((self.logs / runtime_guard.QUARANTINE).iterdir()))

    def test_changes_in_credential_and_protected_folders_are_found(self):
        watch = runtime_guard.Watch(self.engine, self.workspace, 'run1')
        (self.home_ssh / 'authorized_keys').write_text('x')
        (self.creds / 'secret.txt').write_text('TOPSECRET changed')
        (self.engine / 'kel-credentials.json').write_text('{"a": 2, "b": 3}')
        found = {(Path(c['path']).name, c['change'], c['label']) for c in watch.changes()}
        self.assertIn(('authorized_keys', 'new', runtime_guard.CREDENTIALS_LABEL), found)
        self.assertIn(('secret.txt', 'changed', runtime_guard.PROTECTED_LABEL), found)
        self.assertIn(('kel-credentials.json', 'changed', runtime_guard.DATA_LABEL), found)

    def test_the_shell_folders_only_count_new_entries(self):
        (self.data / 'host' / 'Preferences').write_text('a')
        watch = runtime_guard.Watch(self.engine, self.workspace, 'run1')
        (self.data / 'host' / 'Preferences').write_text('rewritten by the app')
        self.assertEqual(watch.changes(), [])
        (self.data / 'store' / 'evil.py').write_text('x')
        self.assertEqual([Path(c['path']).name for c in watch.changes()], ['evil.py'])


class SettleTests(Layout):
    def setUp(self):
        super().setUp()
        self.store = Store(self.engine)
        CodingAdapter(self.store)
        self.project = make_project(self.tmp.name)
        self.job = self.store.create(compile_coding('Add multiply.', self.project, PYTEST))

    def events(self, kind):
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT type,payload FROM events WHERE aggregate_id=? AND type=?',
                              (self.job, kind)).fetchall()
        return [json.loads(r['payload'])['detail'] for r in rows]

    def test_a_protected_write_fails_the_step_with_a_plain_reason_and_an_activity_line(self):
        watch = runtime_guard.Watch(self.engine, self.workspace, 'run1')
        (self.engine / 'calc-copy.py').write_text('copy')
        failed = runtime_guard.settle(self.store, self.job, 'run1', watch, self.logs,
                                      {'outcome': 'SUCCESS', 'text': 'Done', 'session_id': 's'})
        self.assertEqual(failed['outcome'], 'FAILED')
        self.assertEqual(failed['error'], "The worker wrote calc-copy.py into Kel's own data folder, which Kel "
                                          'never allows, so Kel stopped this step. Kel moved it back out.')
        self.assertFalse((self.engine / 'calc-copy.py').exists())
        self.assertEqual(failed['session_id'], 's')
        refused = self.events('approval.refused')
        self.assertEqual(refused[-1]['reason'], "Kel's own data folder")
        from kel.activity import sentence_for
        line = sentence_for('approval.refused', {'detail': refused[-1]})
        self.assertIn("Kel's own data folder", line)
        self.assertNotIn('verify', line)

    def test_a_blocked_attempt_is_recorded_and_said_plainly(self):
        self.logs.mkdir(parents=True, exist_ok=True)
        (self.logs / runtime_guard.DENIALS).write_text(json.dumps(
            {'tool': 'Write', 'input': {'file_path': str(self.engine / 'calc-copy.py')},
             'reason': "Kel blocked this: ... is in Kel's own data folder, which Kel never changes"}) + '\n')
        result = {'outcome': 'SUCCESS', 'text': 'Added multiply.'}
        self.assertIsNone(runtime_guard.settle(self.store, self.job, 'run1', None, self.logs, result))
        self.assertIn("Kel stopped the worker from touching Kel's own data folder", result['text'])
        self.assertEqual(self.events('approval.refused')[-1]['reason'], "Kel's own data folder")


class CodingRunTests(Layout):
    """The coding adapter end to end, with a fake runtime that does what Claude did in FN-01."""

    def setUp(self):
        super().setUp()
        self.store = Store(self.engine)
        CodingAdapter(self.store)
        self.project = make_project(self.tmp.name)
        self.job = self.store.create(compile_coding('Add multiply to calc.py and a test for it.',
                                                    self.project, PYTEST))
        FakeConnection.receipts, FakeConnection.executed, FakeConnection.crash_after = {}, [], None

    def execute(self, change):
        run = self.store.claim(self.job, 'code', provider='claude-code')

        def connect(store, run_id, workspace):
            return FakeConnection(store, run_id, workspace, change)
        with mock.patch.object(coding, 'DurableCodingConnection', connect):
            return CodingAdapter(self.store).execute('Context.', run_id=run['id'], session_id=None, cancel=None)

    def test_a_runtime_that_writes_into_kels_data_fails_the_step(self):
        engine = self.engine

        def fn01(workspace):
            live_change(workspace)
            (engine / 'calc-copy.py').write_text((workspace / 'calc.py').read_text())
        result = self.execute(fn01)
        self.assertEqual(result['outcome'], 'FAILED')
        self.assertIn("into Kel's own data folder", result['error'])
        self.assertFalse((engine / 'calc-copy.py').exists())

    def test_project_test_code_that_writes_into_kels_data_fails_the_step(self):
        def sneaky(workspace):
            live_change(workspace)
            (workspace / 'test_side.py').write_text(
                'from pathlib import Path\n\n\ndef test_side():\n'
                '    (Path(__file__).resolve().parents[2] / "side.txt").write_text("x")\n', encoding='utf-8')
        result = self.execute(sneaky)
        self.assertEqual(result['outcome'], 'FAILED')
        self.assertTrue(result['error'].startswith("The project's tests wrote side.txt into Kel's own data folder"),
                        result['error'])
        self.assertFalse((self.engine / 'side.txt').exists())

    def test_a_normal_change_is_unaffected(self):
        result = self.execute(live_change)
        self.assertEqual(result['outcome'], 'SUCCESS')
        self.assertTrue(result['code_verified'])


if __name__ == '__main__':
    unittest.main()
