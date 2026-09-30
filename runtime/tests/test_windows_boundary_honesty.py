"""Mocked native readiness and isolated status checks; no setup, ACLs or providers."""
import contextlib
import json
import os
import queue
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from kel import memory_folder
from kel.appserver import CodexConnection
from kel.core import PolicyError
from kel.host_runtime import HostConnection


class WindowsBoundaryHonestyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.engine = self.root / 'engine'
        self.workspace = self.engine / 'repositories' / 'job'
        self.logs = self.engine / 'native-logs' / 'run'
        self.workspace.mkdir(parents=True)
        self.logs.mkdir(parents=True)
        self.env = mock.patch.dict(os.environ, {
            'KEL_MEMORY_ROOT': str(self.root / 'Memory'), 'KEL_DATA_DIR': str(self.engine),
            'KEL_MEMORY_MIRROR': '0', 'TEMP': str(self.root / 'temp'), 'TMP': str(self.root / 'temp')})
        self.env.start()
        self.addCleanup(self.env.stop)

    @contextlib.contextmanager
    def host(self, readiness):
        started = []
        def fake_init(conn, workspace, logs, process_argv=None):
            started.append(process_argv)
            conn.workspace, conn.logs = str(workspace), Path(logs)
        with mock.patch.object(CodexConnection, '__init__', fake_init), \
             mock.patch.object(CodexConnection, 'close') as closed, \
             mock.patch.object(CodexConnection, 'call', side_effect=readiness) as rpc, \
             mock.patch('kel.host_runtime.executable', return_value=['C:/bin/codex.exe']), \
             mock.patch('kel.runtime_guard.codex_mcp_servers', return_value=[]), \
             mock.patch('kel.memory_folder.codex_elevated', return_value=True):
            memory_folder._save_codex_state(self.engine, mode='elevated', setup='done')
            yield started, closed, rpc

    def test_unready_choice_stops_without_second_launch_or_execution(self):
        with self.host(lambda *args: {'status': 'updateRequired'}) as (started, closed, rpc):
            with self.assertRaisesRegex(PolicyError, 'without using a weaker sandbox'):
                HostConnection(self.workspace, self.logs)
            self.assertEqual(len(started), 1)
            closed.assert_called_once()
            self.assertEqual([call.args[0] for call in rpc.call_args_list], ['windowsSandbox/readiness'])
        state = memory_folder.codex_state(self.engine)
        self.assertEqual(state['mode'], 'elevated')
        self.assertEqual(state['readiness'], 'not_ready')
        fact = json.loads((self.logs / 'boundary.json').read_text())
        self.assertEqual(fact['effective_mode'], 'blocked')
        self.assertFalse(fact['complete_read_confinement'])

    def test_readiness_exception_is_unknown_without_raw_private_error(self):
        private = 'secret C:/Users/Private/token.txt'
        with self.host(RuntimeError(private)) as (started, closed, rpc):
            with self.assertRaises(PolicyError) as error:
                HostConnection(self.workspace, self.logs)
            self.assertNotIn(private, str(error.exception))
            self.assertEqual(len(started), 1)
            closed.assert_called_once()
        state = memory_folder.codex_state(self.engine)
        self.assertEqual(state['readiness'], 'unknown')
        self.assertNotIn(private, json.dumps(state))
        self.assertNotIn(private, (self.logs / 'boundary.json').read_text())

    def test_ready_observation_is_partial_and_never_complete_read_confinement(self):
        with self.host(lambda *args: {'status': 'ready'}) as (started, closed, rpc):
            conn = HostConnection(self.workspace, self.logs)
            self.assertTrue(conn.elevated)
            self.assertEqual(len(started), 1)
            closed.assert_not_called()
            status = memory_folder.status(self.engine)
            self.assertEqual(status['codex_configured_mode'], 'elevated')
            self.assertEqual(status['codex_readiness'], 'ready')
            self.assertEqual(status['codex_read_coverage'], 'partial-deny-list')
            self.assertFalse(status['codex_reads_blocked'])
            self.assertFalse(status['codex_complete_read_confinement'])
            self.assertIsInstance(status['codex_readiness_at'], float)
        fact = json.loads((self.logs / 'boundary.json').read_text())
        self.assertEqual(fact['effective_mode'], 'elevated')
        self.assertNotIn(str(self.root), json.dumps(fact))

    def test_missing_readiness_is_not_inferred_from_configured_choice(self):
        memory_folder._save_codex_state(self.engine, mode='elevated', setup='done')
        with mock.patch('kel.memory_folder.codex_elevated', return_value=True):
            status = memory_folder.status(self.engine)
        self.assertEqual(status['codex_readiness'], 'not_checked')
        self.assertFalse(status['codex_reads_blocked'])
        if os.name == 'nt':
            self.assertTrue(status['codex_setup_available'])

    def test_boundary_logging_failure_closes_without_downgrade(self):
        with self.host(lambda *args: {'status': 'ready'}) as (started, closed, rpc), \
             mock.patch.object(HostConnection, '_record_boundary', side_effect=OSError('owned log unavailable')):
            with self.assertRaises(OSError):
                HostConnection(self.workspace, self.logs)
            self.assertEqual(len(started), 1)
            closed.assert_called_once()
        self.assertEqual(memory_folder.codex_state(self.engine)['mode'], 'elevated')

    def test_linked_boundary_target_or_log_ancestor_cannot_be_written(self):
        target = self.logs / 'boundary.json'
        target.write_text('existing boundary receipt')
        real_lstat = Path.lstat
        for linked in (target, self.logs):
            with self.subTest(linked=linked.name):
                def lstat(path):
                    if path == linked:
                        return SimpleNamespace(st_file_attributes=0x400, st_nlink=1, st_mode=real_lstat(path).st_mode)
                    return real_lstat(path)
                with self.host(lambda *args: {'status': 'ready'}) as (started, closed, rpc), \
                     mock.patch.object(Path, 'lstat', lstat):
                    with self.assertRaisesRegex(PolicyError, 'linked path'):
                        HostConnection(self.workspace, self.logs)
                    self.assertEqual(len(started), 1)
                    closed.assert_called_once()
                self.assertEqual(target.read_text(), 'existing boundary receipt')

    def test_status_describes_tool_guard_and_open_read_limits(self):
        status = memory_folder.status(self.engine)
        self.assertEqual(status['codex_read_coverage'], 'unconfined')
        self.assertIn('tool-level protection', status['claude'])
        self.assertFalse(status['codex_complete_read_confinement'])

    def test_verified_ready_clears_previous_setup_failure(self):
        memory_folder._save_codex_state(self.engine, mode='elevated', setup='failed',
                                       readiness='not_ready', error='Earlier failure', note='Earlier note')
        memory_folder.codex_ready(self.engine)
        state = memory_folder.codex_state(self.engine)
        self.assertEqual(state['setup'], 'done')
        self.assertEqual(state['readiness'], 'ready')
        self.assertIsNone(state['error'])
        self.assertIsNone(state['note'])
        self.assertIsInstance(state['readiness_at'], float)

    @unittest.skipUnless(os.name == 'nt', 'Windows sandbox setup')
    def test_setup_completion_normalizes_actual_followup_readiness(self):
        for value, expected in (('ready', 'ready'), ('updateRequired', 'not_ready'), (None, 'unknown')):
            with self.subTest(observation=expected):
                def fake_init(conn, *args, **kwargs):
                    conn.events = queue.Queue()
                    conn.events.put({'method':'windowsSandbox/setupCompleted', 'params':{'success':True}})
                with mock.patch('kel.native.executable', return_value=['C:/bin/codex.exe']), \
                     mock.patch.object(CodexConnection, '__init__', fake_init), \
                     mock.patch.object(CodexConnection, 'call', side_effect=[{'status':'updateRequired'},
                         {'started':True}, {'status':value}]), \
                     mock.patch.object(CodexConnection, 'close') as closed:
                    state = memory_folder.codex_sandbox_setup(self.engine)
                self.assertEqual(state['readiness'], expected)
                self.assertEqual(state['before'], 'not_ready')
                self.assertIsInstance(state['readiness_at'], float)
                self.assertEqual(state['setup'], 'done' if expected == 'ready' else 'failed')
                status = memory_folder.status(self.engine)
                self.assertEqual(status['codex_readiness'], expected)
                self.assertFalse(status['codex_reads_blocked'])
                closed.assert_called_once()

    @unittest.skipUnless(os.name == 'nt', 'Windows sandbox setup')
    def test_setup_exception_preserves_selected_stronger_mode_and_hides_raw_error(self):
        memory_folder._save_codex_state(self.engine, mode='elevated', setup='done')
        with mock.patch('kel.native.executable', return_value=['C:/bin/codex.exe']), \
             mock.patch.object(CodexConnection, '__init__', return_value=None), \
             mock.patch.object(CodexConnection, 'call', side_effect=RuntimeError('secret private path')), \
             mock.patch.object(CodexConnection, 'close') as closed:
            result = memory_folder.codex_sandbox_setup(self.engine)
        self.assertEqual(result['mode'], 'elevated')
        self.assertEqual(result['setup'], 'failed')
        self.assertNotIn('secret private path', result['error'])
        closed.assert_called_once()


if __name__ == '__main__':
    unittest.main()
