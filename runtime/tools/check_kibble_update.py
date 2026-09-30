"""Run the existing engine tests tied to the actual update's changed modules.

The package/install gate still owns the full suite. This worker check is bounded
to the change, with Kibble's intake regression suite as a baseline.
"""
from pathlib import Path
import ast
import runpy
import subprocess
import sys
import unittest


def load_suite_guards(runtime):
    """Use the suite's canonical defaults before unittest imports its test modules."""
    runpy.run_path(str(Path(runtime) / 'tests/conftest.py'))


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'runtime'))
    load_suite_guards(root / 'runtime')
    changed = subprocess.run(['git', '-C', str(root), 'diff', '--name-only', 'HEAD'],
                             capture_output=True, text=True, encoding='utf-8', check=True).stdout.splitlines()
    untracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--others', '--exclude-standard'],
                               capture_output=True, text=True, encoding='utf-8', check=True).stdout.splitlines()
    changed += untracked
    modules = {Path(path).stem for path in changed if path.startswith('runtime/kel/') and path.endswith('.py')}
    # Importing Service alone is common to most journey tests. Select its changed
    # methods instead of running every journey for a small endpoint change.
    service_methods = set()
    if 'service' in modules:
        old = subprocess.run(['git', '-C', str(root), 'show', 'HEAD:runtime/kel/service.py'],
                             capture_output=True, text=True, encoding='utf-8', check=True).stdout
        new = (root / 'runtime/kel/service.py').read_text(encoding='utf-8')
        def methods(source):
            return {node.name: ast.dump(node) for node in ast.walk(ast.parse(source))
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        before, after = methods(old), methods(new)
        service_methods = {name for name, body in after.items() if before.get(name) != body}
        modules.remove('service')
    tests = root / 'runtime/tests'
    selected = {tests / 'test_dogfood.py', tests / 'test_kibble_work.py'}
    selected.update(root / path for path in changed if path.startswith('runtime/tests/test_') and path.endswith('.py'))
    selected.update(tests / ('test_' + module + '.py') for module in modules)
    for test in tests.glob('test_*.py'):
        text = test.read_text(encoding='utf-8')
        if any(name in text for name in service_methods):
            selected.add(test)
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for test in sorted(selected):
        if test.is_file():
            print('Checking ' + test.name, flush=True)
            suite.addTests(loader.discover(str(tests), pattern=test.name))
    if not suite.countTestCases():
        print('No engine tests were available.', file=sys.stderr)
        return 1
    print('Affected engine checks only; desktop checks run when building the update.', flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
