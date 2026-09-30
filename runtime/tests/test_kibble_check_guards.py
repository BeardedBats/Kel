"""The focused worker checker uses the same isolated guard defaults as pytest."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('kibble_checker', Path(__file__).resolve().parents[1] / 'tools/check_kibble_update.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class KibbleCheckGuardsTests(unittest.TestCase):
    def test_guard_defaults_preserve_explicit_scratch_roots(self):
        with tempfile.TemporaryDirectory() as scratch:
            roots = {'KEL_MEMORY_ROOT': str(Path(scratch) / 'Memory'),
                     'KEL_PROJECTS_ROOT': str(Path(scratch) / 'Projects')}
            with patch.dict(os.environ, roots, clear=True):
                checker.load_suite_guards(Path(__file__).resolve().parents[1])
                for key, value in roots.items():
                    self.assertEqual(os.environ[key], value)
                self.assertEqual(os.environ['KEL_GENERAL_ROOT'], 'none')
                self.assertEqual(os.environ['KEL_TURN_MODEL'], 'none')
                for key in ('KEL_MEMORY_MIRROR', 'KEL_CLI_WEB', 'KEL_TASTE'):
                    self.assertEqual(os.environ[key], '0')

    def test_missing_roots_are_created_under_temporary_test_space(self):
        with tempfile.TemporaryDirectory() as scratch:
            def temporary_root(prefix):
                path = Path(scratch) / prefix
                path.mkdir(exist_ok=True)
                return str(path)
            with patch.dict(os.environ, {}, clear=True), patch('tempfile.mkdtemp', side_effect=temporary_root):
                checker.load_suite_guards(Path(__file__).resolve().parents[1])
                self.assertTrue(Path(os.environ['KEL_MEMORY_ROOT']).is_relative_to(Path(scratch)))
                self.assertTrue(Path(os.environ['KEL_PROJECTS_ROOT']).is_relative_to(Path(scratch)))


if __name__ == '__main__':
    unittest.main()
