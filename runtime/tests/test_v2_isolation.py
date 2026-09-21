"""V2-13 — local execution isolation: sensitive folders, disposable sessions, a scrubbed env.

§18's list, done on the paths Kel already has — no VM, no container platform, no rewritten sandbox.
The pins: sensitive roots are refused with a plain reason (system folders, credential folders,
environment-protected app folders, and Kel's own data root); a normal temp project is allowed; the
child environment keeps its provider credential and loses every secret-shaped name; TMP/TEMP/TMPDIR
point at the run's disposable session and it is removed on cleanup; the coding snapshot stands behind
the same guard so no caller can start from a sensitive source; and the tool-disabled native leaf
(the read-only CLI argv) cannot regress silently.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kel.coding import snapshot  # noqa: E402
from kel.containment import (assert_usable_root, cleanup_session, scrub_secrets,  # noqa: E402
                             sensitive_reason, session_dir)
from kel.core import PolicyError, Store  # noqa: E402
from kel.native import NativeAdapter, child_env  # noqa: E402


def windows_root():
    return os.environ.get('WINDIR') or os.environ.get('SystemRoot')


class SensitiveRootTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_system_folders_are_refused(self):
        root = windows_root()
        self.assertTrue(root, 'this probe needs a Windows root')
        self.assertEqual(sensitive_reason(root), 'a Windows system folder')
        with self.assertRaises(PolicyError) as raised:
            assert_usable_root(root, purpose='a snapshot')
        self.assertIn('Kel will not use', str(raised.exception))
        self.assertIn('Windows system folder', str(raised.exception))

    def test_credential_folders_are_refused(self):
        home = Path(os.environ.get('USERPROFILE') or Path.home())
        self.assertEqual(sensitive_reason(home / '.ssh'), 'your credentials folder')
        self.assertEqual(sensitive_reason(home / '.aws' / 'credentials'),
                         'your credentials folder')

    def test_an_environment_protected_app_folder_is_refused(self):
        protected = Path(self.tmp.name) / 'protected-app'
        protected.mkdir()
        with patch.dict(os.environ, {'KEL_PROTECTED_PATHS': str(protected)}, clear=False):
            self.assertEqual(sensitive_reason(protected), 'a protected app folder')
            self.assertEqual(sensitive_reason(protected / 'inner'), 'a protected app folder')

    def test_kels_own_data_folder_is_refused(self):
        self.assertEqual(sensitive_reason(self.store.root, store=self.store),
                         "Kel's own data folder")
        with self.assertRaises(PolicyError):
            assert_usable_root(self.store.root / 'repositories', purpose='a snapshot',
                               store=self.store)

    def test_a_plain_project_folder_is_allowed(self):
        project = Path(self.tmp.name) / 'project'
        project.mkdir()
        self.assertIsNone(sensitive_reason(project, store=self.store))
        self.assertEqual(assert_usable_root(project, store=self.store), project)

    def test_the_coding_snapshot_refuses_a_sensitive_source(self):
        with self.assertRaises(PolicyError) as raised:
            snapshot(windows_root(), Path(self.tmp.name) / 'copy')
        self.assertIn('Windows system folder', str(raised.exception))


class EnvironmentTests(unittest.TestCase):
    def test_scrub_drops_every_secret_shape_and_keeps_the_named_credential(self):
        env = {'PATH': 'x', 'KEL_DATA_DIR': 'y', 'MY_API_TOKEN': 't1',
               'AWS_SECRET_ACCESS_KEY': 's', 'DB_PASSWORD': 'p', 'OPENAI_API_KEY': 'k',
               'SOME_AUTH_HEADER': 'h', 'LANG': 'en'}
        kept = scrub_secrets(env, keep=('OPENAI_API_KEY',))
        self.assertEqual(sorted(kept),
                         sorted(['PATH', 'KEL_DATA_DIR', 'OPENAI_API_KEY', 'LANG']))

    def test_child_env_keeps_only_its_own_provider_credential(self):
        base = {'PATH': 'x', 'ANTHROPIC_API_KEY': 'a', 'OPENAI_API_KEY': 'o',
                'DEEPSEEK_API_KEY': 'd', 'MY_TOKEN': 'm'}
        codex = child_env('codex', base=base)
        self.assertEqual(codex['OPENAI_API_KEY'], 'o')
        self.assertNotIn('ANTHROPIC_API_KEY', codex)
        self.assertNotIn('DEEPSEEK_API_KEY', codex)
        self.assertNotIn('MY_TOKEN', codex)
        self.assertEqual(codex['PATH'], 'x')

    def test_the_session_becomes_the_child_temp_and_is_removed_on_cleanup(self):
        session = session_dir(Path(self._dir()), 'run-1')
        env = child_env('codex', base={'PATH': 'x'}, session=session)
        for name in ('TMP', 'TEMP', 'TMPDIR'):
            self.assertEqual(env[name], str(session))
        self.assertTrue(session.is_dir())
        self.assertTrue(cleanup_session(session))
        self.assertFalse(session.exists())

    def _dir(self):
        if not hasattr(self, '_tmpdir'):
            self._tmpdir = tempfile.TemporaryDirectory()
            self.addCleanup(self._tmpdir.cleanup)
        return self._tmpdir.name


class ReadOnlyLeafTests(unittest.TestCase):
    def test_the_native_leaf_argv_is_read_only_and_tool_disabled(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        adapter = NativeAdapter('codex', Path(tmp.name) / 'ws', Path(tmp.name) / 'logs')
        argv = adapter.argv()
        self.assertIn('-s', argv)
        self.assertIn('read-only', argv)
        self.assertIn('sandbox_mode="read-only"', argv)
        self.assertIn('--disable', argv)


if __name__ == '__main__':
    unittest.main()
