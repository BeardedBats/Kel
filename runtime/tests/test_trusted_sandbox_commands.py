import os
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from kel.appserver import CodexConnection
from kel.core import PolicyError
from kel.host_runtime import HostConnection,normalize_installed_npm


class TrustedSandboxCommandTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root=Path(self.folder.name)
        self.connection=object.__new__(HostConnection)
        c=self.connection
        c.workspace=str(root/'work');Path(c.workspace).mkdir()
        c.logs=root/'engine'/'native-logs'/'test';c.logs.mkdir(parents=True)
        c.engine_root=c.logs.parent.parent;c.temp=root/'temp';c.temp.mkdir()
        c.provider='codex';c.network=False

    def test_scope_refusal_precedes_sandbox_launch(self):
        with patch.object(self.connection,'_trusted_test_argv') as argv,patch('kel.host_runtime.subprocess.Popen') as launch:
            with self.assertRaises(PolicyError):self.connection.call('command/exec',{'cwd':str(self.connection.logs),'command':['python','-V']})
        argv.assert_not_called();launch.assert_not_called()

    def test_reparse_ancestor_cannot_widen_the_write_profile(self):
        original=Path.lstat
        parent=Path(self.connection.workspace).parent
        def inspect(path,*args,**kwargs):
            if path==parent:return SimpleNamespace(st_file_attributes=0x400,st_mode=0o40755)
            return original(path,*args,**kwargs)
        with patch.object(Path,'lstat',inspect),patch.object(self.connection,'_trusted_test_argv') as profile:
            with self.assertRaisesRegex(PolicyError,'linked folder'):
                self.connection.call('command/exec',{'command':['python','-V']})
        profile.assert_not_called()

    def test_replaced_workspace_identity_cannot_widen_profile(self):
        self.connection._trusted_workspace_identity=(-1,-1)
        with patch.object(self.connection,'_trusted_test_argv') as profile:
            with self.assertRaisesRegex(PolicyError,'folder changed'):
                self.connection.call('command/exec',{'command':['python','-V']})
        profile.assert_not_called()

    def test_profile_preserves_network_and_mode_for_both_providers(self):
        for provider in ('codex','claude'):
            self.connection.provider=provider
            with self.subTest(provider=provider),patch('kel.host_runtime.executable',return_value=['codex.exe']),\
                 patch('kel.memory_folder.codex_elevated',return_value=False),\
                 patch('kel.runtime_guard.codex_config',return_value=['-c','same-profile']) as config:
                argv,mode=self.connection._trusted_test_argv(Path(self.connection.workspace),['python.exe','-B','tests.py'])
            self.assertFalse(mode);self.assertEqual(argv[:4],['codex.exe','sandbox','--permission-profile','kel'])
            self.assertEqual(argv[-4:],['--','python.exe','-B','tests.py'])
            self.assertEqual(config.call_args.args[0],False);self.assertEqual(config.call_args.args[-1],False)

    def test_elevated_unready_refuses_before_command(self):
        with patch('kel.host_runtime.executable',return_value=['codex.exe']),\
             patch('kel.memory_folder.codex_elevated',return_value=True),\
             patch.object(CodexConnection,'call',return_value={'status':'updateRequired'}),\
             patch('kel.memory_folder.codex_not_ready') as unavailable,patch('kel.host_runtime.subprocess.Popen') as launch:
            with self.assertRaises(PolicyError):self.connection.call('command/exec',{'command':['python','-V']})
        unavailable.assert_called_once_with(self.connection.engine_root,'updateRequired');launch.assert_not_called()

    def test_claude_checks_close_readiness_transport(self):
        self.connection.provider='claude'
        probe=Mock();probe.call.return_value={'status':'ready'}
        with patch('kel.host_runtime.executable',return_value=['codex.exe']),\
             patch('kel.memory_folder.codex_elevated',return_value=True),\
             patch('kel.runtime_guard.codex_config',return_value=[]),\
             patch('kel.host_runtime.CodexConnection',return_value=probe):
            _,mode=self.connection._trusted_test_argv(Path(self.connection.workspace),['python','-V'])
        self.assertTrue(mode);probe.close.assert_called_once();probe.call.assert_called_once_with('windowsSandbox/readiness',{},timeout=10)

    def test_missing_codex_has_no_unsandboxed_fallback(self):
        with patch('kel.host_runtime.executable',side_effect=PolicyError('missing')),patch('kel.host_runtime.subprocess.Popen') as launch:
            with self.assertRaisesRegex(PolicyError,'installed Codex sandbox'):
                self.connection.call('command/exec',{'command':['python','-V']})
        launch.assert_not_called()

    def test_receipt_keeps_read_and_network_limits(self):
        process=Mock();process.poll.return_value=0;process.returncode=0
        with patch.object(self.connection,'_trusted_test_argv',return_value=(['codex.exe','sandbox'],False)),\
             patch('kel.host_runtime.launch_trusted_command',return_value=process) as launch:
            result=self.connection.call('command/exec',{'command':['python','-V']})
        self.assertEqual(launch.call_args.args[0],['codex.exe','sandbox'])
        fact=result['_kel_execution'];self.assertTrue(fact['sandbox']);self.assertFalse(fact['complete_read_confinement'])
        self.assertEqual(fact['read_coverage'],'unconfined');self.assertEqual(fact['external_network'],'unverified')
        self.assertEqual(fact['loopback_network'],'allowed-in-synthetic-probe')

    def test_original_suite_excludes_the_assigned_workspace_from_tool_resolution(self):
        original=self.connection.logs/'original-tests';original.mkdir()
        process=Mock();process.poll.return_value=0;process.returncode=0
        with patch('kel.host_runtime.normalize_installed_npm',return_value=None) as normalize,\
             patch.object(self.connection,'_trusted_test_argv',return_value=(['codex.exe','sandbox'],False)),\
             patch('kel.host_runtime.launch_trusted_command',return_value=process):
            self.connection.call('command/exec',{'cwd':str(original),'command':['python','-V']})
        self.assertIn(Path(self.connection.workspace),normalize.call_args.args[1])

    def test_output_budget_stops_sandbox_without_retry(self):
        process=Mock();process.poll.return_value=None
        def launch(*args,**kwargs):
            kwargs['stdout'].write(b'x'*2_000_001);kwargs['stdout'].flush();return process
        with patch.object(self.connection,'_trusted_test_argv',return_value=(['codex.exe','sandbox'],False)),\
             patch('kel.host_runtime.launch_trusted_command',side_effect=launch) as spawned,\
             patch.object(self.connection,'_stop_test_process') as stop:
            with self.assertRaisesRegex(PolicyError,'output budget'):
                self.connection.call('command/exec',{'command':['python','-V']})
        stop.assert_called_once_with(process);self.assertEqual(spawned.call_count,1)

    def test_cancel_after_launch_suppresses_passing_receipt(self):
        process=Mock();process.poll.return_value=None
        def launch(*args,**kwargs):self.connection._tests_closed=True;return process
        with patch.object(self.connection,'_trusted_test_argv',return_value=(['codex.exe','sandbox'],False)),\
             patch('kel.host_runtime.launch_trusted_command',side_effect=launch),\
             patch.object(self.connection,'_stop_test_process') as stop:
            with self.assertRaisesRegex(PolicyError,'stopped during execution'):
                self.connection.call('command/exec',{'command':['python','-V']})
        stop.assert_called_once_with(process);self.assertIsNone(self.connection._test_process)


class InstalledNpmNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.install=self.root/'installed';self.install.mkdir()
        self.shim=self.install/'npm.cmd';self.shim.write_bytes(b'known fixture shim')
        self.node=self.install/'node.exe';self.node.write_bytes(b'fixture only')
        package=self.install/'node_modules'/'npm';(package/'bin').mkdir(parents=True)
        self.package=package/'package.json';self.package.write_text('{"name":"npm","version":"11.16.0"}')
        self.entry=package/'bin'/'npm-cli.js';self.entry.write_text('// fixture only')
        self.owned=self.root/'work';self.owned.mkdir()
        self.addCleanup(patch.stopall)
        self.which=patch('kel.host_runtime.shutil.which',side_effect=lambda name: str(self.node if name=='node' else self.shim)).start()
        patch('kel.host_runtime.NPM_SHIM_HASHES',{'npm':hashlib.sha256(self.shim.read_bytes()).hexdigest()}).start()

    def test_recognized_shim_preserves_literal_arguments_and_reports_version(self):
        args,fact=normalize_installed_npm(['npm','test','two words','x&y'],[self.owned])
        self.assertEqual(args,[str(self.node),str(self.entry),'test','two words','x&y'])
        self.assertEqual(fact,{'kind':'adjacent-installed-npm','tool':'npm','package_version':'11.16.0'})

    def test_unknown_shim_refuses(self):
        self.shim.write_text('unknown shim')
        with self.assertRaises(PolicyError):normalize_installed_npm(['npm','test'],[self.owned])

    def test_owned_install_cannot_supply_normalized_tool(self):
        with self.assertRaises(PolicyError):normalize_installed_npm(['npm','test'],[self.install])

    def test_different_selected_node_refuses(self):
        self.which.side_effect=lambda name:str(self.root/'different-node.exe' if name=='node' else self.shim)
        with self.assertRaises(PolicyError):normalize_installed_npm(['npm','test'],[self.owned])

    def test_duplicate_or_malformed_metadata_refuses(self):
        for body in ('{"name":"other","name":"npm","version":"11.16.0"}', '{"name":"npm","version":null}'):
            with self.subTest(body=body):
                self.package.write_text(body)
                with self.assertRaises(PolicyError):normalize_installed_npm(['npm','test'],[self.owned])


if __name__=='__main__':unittest.main()
