"""Repository work in isolated snapshots; deterministic test and patch evidence."""
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import stat
import time
from .appserver import CodexConnection
from .core import PolicyError, digest, encode, uid, validate_contract
from .context import Context
from .coding_transport import DurableCodingConnection,host_alive


def git(root,*args,input=None):
    p=subprocess.run(['git','-c','core.hooksPath=NUL','-c','core.longpaths=true',*args],cwd=root,input=input,
                     capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode:raise PolicyError(p.stderr.decode('utf-8','replace')[:1000])
    return p.stdout


def compile_coding(request,root,tests,project_id='default',greenfield=False):
    root=Path(root).resolve(strict=True)
    if not isinstance(tests,list) or not tests or not all(isinstance(s,str) and s for s in tests):
        raise PolicyError('Coding needs an explicit test command as an argument list')
    if len(tests)>40:raise PolicyError('Test command is too long')
    git(root,'rev-parse','--show-toplevel')
    rubric=('The code diff satisfies the source request. Existing tests remain intact and pass. Review the actual diff and trusted test output.'
            if not greenfield else
            'The new project implements the source request and its smoke test passes. The project runs with only standard tooling unless the request requires otherwise.')
    contract={'request':request,'kind':'coding','root':str(root),'test_command':tests,
        'project_id':project_id,'compiler':'coding-contract-v2','runtime':'native-host',
        'non_goals':['unrequested source checkout changes','unrequested external publication'],
        'milestones':[{'id':'code','objective':request,'filename':'changes.md','depends_on':[],
            'checks':[{'kind':'min_chars','value':40},{'kind':'manual_review','rubric':rubric}]}]}
    if greenfield:contract['greenfield']=True
    return validate_contract(contract)


# D-71: "existing tests preserved" means the project's own tests, in their original form, still pass
# against the new code. Two kinds of file define the existing test suite:
# - test files (by folder or name, in any language), and
# - test setup files: anything that changes what the test command collects or how it starts
#   (conftest.py, sitecustomize.py, pytest/tox/setup.cfg/pyproject settings, package.json scripts,
#   jest/vitest/mocha/karma configs, Makefiles, a file the command names, a module that would shadow
#   the `-m` runner). D-49 was a new sitecustomize.py that made a failing command exit 0.
# The second test run puts every one of these back to its original bytes and leaves new ones out.
TEST_DIRS = {'tests', 'test', '__tests__', 'spec', 'specs', 'testing'}
SETUP_NAMES = {'conftest.py', 'sitecustomize.py', 'usercustomize.py', 'pytest.ini', '.pytest.ini', 'tox.ini',
               'tox.toml', 'setup.cfg', 'pyproject.toml', 'noxfile.py', 'package.json', '.babelrc',
               'deno.json', 'deno.jsonc', 'makefile', 'gnumakefile', 'justfile', '.coveragerc'}
SETUP_PREFIXES = ('jest.config.', 'jest.setup.', 'vitest.config.', 'vitest.workspace.', 'vitest.setup.',
                  'karma.conf.', 'playwright.config.', 'babel.config.', '.mocharc', 'ava.config.')
EXISTING_TESTS_KEY = 'command/exec#existing-tests'  # the second trusted test run's durable RPC identity
OUTPUT_LIMIT = 50000


def _command_refs(command):
    """Repository paths the test command names, and the modules a `-m` runner would import first."""
    paths, modules = set(), set()
    args = list(command or [])
    for index, arg in enumerate(args[1:], 1):
        if args[index - 1] == '-m':
            modules.add(arg.split('.')[0])
            continue
        if arg.startswith('-') or '://' in arg:
            continue
        ref = arg.replace('\\', '/').split('::')[0]
        while ref.startswith('./'):
            ref = ref[2:]
        if ref and not Path(ref).is_absolute() and '..' not in Path(ref).parts:
            paths.add(ref.rstrip('/'))
    return paths, modules


def suite_role(path, command=()):
    """'test', 'setup' or None for one repository path (POSIX form)."""
    parts = Path(path).parts
    if not parts:
        return None
    name = parts[-1]
    lower = name.lower()
    stem = name.split('.')[0]
    paths, modules = _command_refs(command)
    if (lower in SETUP_NAMES or lower.startswith(SETUP_PREFIXES) or lower.endswith('.pth')
            or (len(parts) == 1 and stem in modules and lower.endswith('.py'))
            or (len(parts) > 1 and parts[0] in modules)):
        return 'setup'
    # A file the command names (`python smoke_test.py`, `pytest checks/`) is part of the test suite.
    if (any(part.lower() in TEST_DIRS for part in parts[:-1]) or lower.startswith('test')
            or stem.lower().endswith(('_test', '_spec', '_tests')) or stem.endswith(('Test', 'Tests'))
            or '.test.' in lower or '.spec.' in lower
            or path in paths or any(path.startswith(ref + '/') for ref in paths)):
        return 'test'
    return None


def protected_files(manifest, command):
    """The baseline test and test setup files, path -> digest."""
    return {p: h for p, h in manifest.items() if suite_role(p, command)}


def _tail(text, limit=OUTPUT_LIMIT):
    text = str(text or '')
    return text if len(text) <= limit else '…' + text[-limit:]


def _last_line(*outputs):
    for output in outputs:
        lines = [line.strip().strip('=').strip() for line in str(output or '').splitlines()]
        lines = [line for line in lines if line]
        if lines:
            return lines[-1][:160]
    return ''


def failing_tests(*outputs):
    """Test ids a runner named as failing (pytest `FAILED x::y`, unittest `FAIL: y (x)`), at most five."""
    found = []
    for output in outputs:
        for line in str(output or '').splitlines():
            text = line.strip()
            for prefix in ('FAILED ', 'ERROR ', 'FAIL: ', 'ERROR: '):
                if text.startswith(prefix):
                    ident = text[len(prefix):].split(' - ')[0].strip()
                    if ident and ident not in found:
                        found.append(ident)
    return found[:5]


def all_failing(*outputs):
    """Every test id a runner named as failing (no limit)."""
    found = []
    for output in outputs:
        for line in str(output or '').splitlines():
            text = line.strip()
            for prefix in ('FAILED ', 'ERROR ', 'FAIL: ', 'ERROR: '):
                if text.startswith(prefix):
                    ident = text[len(prefix):].split(' - ')[0].strip()
                    if ident and ident not in found:
                        found.append(ident)
    return found


# ---- D-84: Kel owns the tests ---------------------------------------------------------------------
# The Builder may change an existing test only where the requested behaviour contradicts it, and says
# so in a structured block. Kel finds every changed or removed existing test itself (per test, from the
# code), and the original-tests run may fail only on those. Every other original test still has to
# pass in its original form, and test setup files are still put back (never a way to skip tests).
CHANGED_TESTS_KEY = 'command/exec#changed-tests'  # the changed-tests run's durable RPC identity
TEST_RULES = (
    'Existing tests: Kel runs the original versions of the existing test files and test settings against your '
    'code, so add new tests freely (new test functions or files) but keep every existing test as it is, except a '
    'test whose expectation the requested behaviour directly contradicts. You may change or remove such a test, '
    'and only such a test; never change test settings (conftest.py, pytest.ini, pyproject.toml, setup.cfg, '
    'package.json and similar) to skip or relax tests. For every existing test you change or remove, end your '
    'report with this block (JSON, one entry per test):\n```kel-test-changes\n[{"test": "test_file.py::test_name", '
    '"request_quote": "<the exact words of the request that contradict it>", "was": "<what the test expected '
    'before>", "now": "<what it expects now, or empty if removed>"}]\n```\nKel checks each change against the '
    'request; a change the request does not require fails the step.')
JUSTIFY_FENCE = 'kel-test-changes'
MODULE = '(module)'


def _py_units(source):
    """{unit id: normalised code} for one Python test file, or None when it does not parse.

    Units: each test function (`test_x`), each test method (`TestX::test_y`), a class's other code
    (`TestX`), and the module's own code (`(module)`: imports, helpers, fixtures, assignments).
    Formatting and comments never count as a change (the code is compared as a syntax tree).
    """
    import ast
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    units, module = {}, []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test'):
            units[node.name] = ast.dump(node)
        elif isinstance(node, ast.ClassDef) and (node.name.startswith('Test') or any(
                isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test') for n in node.body)):
            rest = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith('test'):
                    units[node.name + '::' + item.name] = ast.dump(item)
                else:
                    rest.append(ast.dump(item))
            units[node.name] = json.dumps([[ast.dump(d) for d in node.decorator_list],
                                           [ast.dump(b) for b in node.bases], rest])
        else:
            module.append(node)
    units[MODULE] = module
    return units


def _module_changed(before, after):
    """True when a test file's own code changed in a way that can change what its tests check.

    Removing or changing an existing statement counts; adding imports or new helper functions/classes
    does not, unless the new definition shadows a name the file already had (an import or a helper) —
    `def divide(...)` added to a test file would silently replace the code under test.
    """
    import ast

    def bindings(nodes):
        """Import bindings: bound name -> where it comes from."""
        found = {}
        for node in nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found[alias.asname or alias.name.split('.')[0]] = (alias.name if alias.asname else
                                                                       alias.name.split('.')[0], None)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    found[alias.asname or alias.name] = ('.' * node.level + (node.module or ''), alias.name)
        return found
    imports = (ast.Import, ast.ImportFrom)
    old = [ast.dump(n) for n in before if not isinstance(n, imports)]
    new = [ast.dump(n) for n in after if not isinstance(n, imports)]
    if any(item not in new for item in old):
        return True
    # Imports: adding names or dropping them is fine (a test that needs a dropped name fails on its
    # own); binding a name the file already had to something else is not (`from fake import add`).
    was, now = bindings(before), bindings(after)
    known = {n.name for n in before if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    if any(name in was and was[name] != source or name in known for name, source in now.items()):
        return True
    for node in after:
        if isinstance(node, imports) or ast.dump(node) in old:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and \
                node.name not in known and node.name not in was:
            continue
        return True
    return False


def test_edits(workspace, base, baseline, after, command):
    """Every changed or removed existing test, per test where the language allows (D-84).

    [{'test': id, 'file': path, 'change': 'changed'|'removed'}] — ids are pytest-style
    (`test_calc.py::test_divide`, `tests/test_a.py::TestA::test_b`); a file's own code is
    `path::(module)`; a non-Python test file is one entry, its path. New tests are not edits.
    """
    edits = []
    for path, expected in sorted(protected_files(baseline, command).items()):
        if suite_role(path, command) != 'test' or after.get(path) == expected:
            continue
        original = _baseline_bytes(workspace, base, path, expected)
        current = (Path(workspace) / path).read_bytes() if path in after else None
        old = _py_units(original.decode('utf-8', 'replace')) if path.endswith('.py') else None
        new = _py_units(current.decode('utf-8', 'replace')) if (old is not None and current is not None) else None
        if old is None or (current is not None and new is None):
            edits.append({'test': path, 'file': path, 'change': 'removed' if current is None else 'changed'})
            continue
        new = new or {}
        for unit in sorted(old):
            if unit == MODULE:
                if current is not None and _module_changed(old[MODULE], new.get(MODULE) or []):
                    edits.append({'test': path + '::' + MODULE, 'file': path, 'change': 'changed'})
                continue
            if unit not in new:
                edits.append({'test': path + '::' + unit, 'file': path, 'change': 'removed'})
            elif new[unit] != old[unit]:
                edits.append({'test': path + '::' + unit, 'file': path, 'change': 'changed'})
    return edits


def _failing_ref(ident):
    """(file, [names]) for one failing test id (pytest or unittest form), or None."""
    ident = ident.strip()
    if '(' in ident and ident.endswith(')'):  # unittest: "test_b (pkg.test_a.TestA.test_b)"
        method = ident.split('(')[0].strip()
        dotted = ident[ident.index('(') + 1:-1].split('.')
        if dotted and dotted[-1] == method:
            dotted = dotted[:-1]
        if len(dotted) < 2:
            return None
        return '/'.join(dotted[:-1]) + '.py', [dotted[-1], method]
    parts = ident.replace('\\', '/').split('::')
    names = [part.split('[')[0] for part in parts[1:]]
    return parts[0], names


def _covers(entry_id, ref):
    """True when a changed/removed test (entry id) accounts for one failing test (ref)."""
    file, names = ref
    if entry_id in (file, file + '::' + MODULE):
        return True
    if not names:
        # The whole file failed in its original form (it no longer imports: the request removed a name
        # it used). Its unchanged tests are the same code in the new file, which the changed-tests run
        # checks with the original setup; only its changed/removed tests need a reason.
        return entry_id.startswith(file + '::')
    for depth in range(1, len(names) + 1):
        if entry_id == file + '::' + '::'.join(names[:depth]):
            return True
    return False


def builder_justifications(text):
    """The Builder's structured reasons for its test changes (the fenced `kel-test-changes` block)."""
    import re
    found = []
    for block in re.findall(r'```\s*' + JUSTIFY_FENCE + r'\s*\n(.*?)```', str(text or ''), re.S):
        try:
            value = json.loads(block)
        except (TypeError, ValueError):
            continue
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, dict) and str(item.get('test') or '').strip():
                found.append({k: ' '.join(str(item.get(k) or '').split())[:400]
                              for k in ('test', 'request_quote', 'was', 'now')})
    return found


def _match(entry, reasons):
    test = entry['test']
    short = test.split('::')[-1]
    for reason in reasons:
        given = reason['test'].replace('\\', '/').strip()
        if given == test or test.endswith('::' + given) or given.endswith('::' + short) or given == short:
            return reason
    return None


def _norm(text):
    import re
    return re.sub(r'[^a-z0-9]+', ' ', str(text or '').lower()).strip()


def quote_in_request(request, quote):
    """The lighter guard (D-85, no Verifier): the reason quotes the words of the request it relies on."""
    quote = _norm(quote)
    return len(quote) >= 3 and quote in _norm(request)


def _justified(entry, request, guard):
    reason = entry.get('justification') or {}
    if not reason.get('request_quote') or not reason.get('was'):
        return False
    if entry['change'] == 'changed' and not reason.get('now'):
        return False
    if guard == 'request' and not quote_in_request(request, reason['request_quote']):
        return False
    return True


def _short_test(test):
    parts = test.split('::')
    return parts[-1] if parts[-1] != MODULE else parts[0] + ' (shared test code)'


def change_reason(entry):
    """'test_divide_by_zero now expects 0 instead of an error' for one justified change."""
    reason = entry.get('justification') or {}
    name = _short_test(entry['test'])
    if entry['change'] == 'removed':
        return '%s was removed because your change removed what it checked (%s)' % (
            name, reason.get('was') or 'its old behaviour')
    return '%s now expects %s instead of %s' % (name, (reason.get('now') or 'the new behaviour').rstrip('.'),
                                                (reason.get('was') or 'the old behaviour').rstrip('.'))


def test_changes_line(changes):
    """One plain line for Nick: which tests Kel changed and why (D-84), or None."""
    changes = [c for c in changes or [] if c.get('reason')]
    if not changes:
        return None
    updated = [c for c in changes if c.get('change') != 'removed']
    removed = [c for c in changes if c.get('change') == 'removed']
    parts = []
    if updated:
        parts.append('Kel updated %s to match your change: %s' % (
            '1 test' if len(updated) == 1 else '%d tests' % len(updated), '; '.join(c['reason'] for c in updated)))
    if removed:
        parts.append('Kel removed %s: %s' % ('1 test' if len(removed) == 1 else '%d tests' % len(removed),
                                             '; '.join(c['reason'] for c in removed)))
    return '. '.join(parts) + '.'


def _names(paths, limit=4):
    paths = sorted(paths)
    shown = ', '.join(paths[:limit])
    return shown + (' and %d more' % (len(paths) - limit) if len(paths) > limit else '')


def tests_summary(exit_code, stdout, stderr):
    """The configured test run in plain words."""
    line = _last_line(stdout, stderr)
    if exit_code == 0:
        return 'Your tests passed' + (' (%s).' % line if line else '.')
    failed = failing_tests(stdout, stderr)
    if failed:
        return 'Your tests failed: %s.' % _names(failed)
    return 'Your tests failed (exit code %s%s).' % (exit_code, ': ' + line if line else '')


def _existing_summary(check):
    """One plain sentence for the existing-tests check."""
    state = check['state']
    if state == 'none':
        return 'There were no existing tests to keep.'
    edits = check.get('edits')
    unjustified = check.get('unjustified') or []
    missing = check['missing'] if edits is None else sorted(
        {e['file'] for e in edits if e['file'] in check['missing'] and e['test'] in unjustified})
    if state == 'changed':
        line = test_changes_line([{'change': e['change'], 'reason': change_reason(e)} for e in edits])
        return line[:-1] + '; your other existing tests still pass.'
    if state == 'changed_failed':
        failed = check.get('changed_failing') or []
        return ('A test Kel changed does not pass in its new form with your original test settings: %s.'
                % _names(failed) if failed else
                'The changed tests do not pass in their new form with your original test settings (exit code %s).'
                % check.get('changed_exit_code'))
    if state == 'unjustified' and not missing:
        return ('An existing test was changed without a reason from your request: %s. Kel changes an existing '
                'test only where the request contradicts it.' % _names(_short_test(t) for t in unjustified))
    if missing:
        check = dict(check, missing=missing)
        which = _names(check['missing'])
        return ('An existing test file was removed: %s.' if len(check['missing']) == 1
                else 'Existing test files were removed: %s.') % which
    setup = sorted(p for p in check['changed'] + check['added_setup'] if suite_role(p, check['command']) == 'setup')
    note = (' The change also added or changed test settings (%s); Kel ran the tests without them.'
            % _names(setup)) if setup else ''
    if state == 'error':
        return 'Kel could not finish running your existing tests in their original form: %s' % check.get('error')
    if state == 'legacy':
        return ('Existing test files or test settings were changed (%s); this older project copy cannot check '
                'the original tests another way.' % _names(check['changed'] + check['added_setup'] + check['added_tests']))
    if not check['files']:
        # No test files before the change: only new test settings were checked.
        if state == 'passed':
            return 'There were no existing tests to keep, and the tests also pass without the new test settings.'
        if setup:
            return 'The tests pass only with the new test settings (%s); without them they fail.' % _names(setup)
        return 'Your tests do not pass with the new code (exit code %s).' % check.get('exit_code')
    if state == 'passed':
        return 'Your existing tests still pass.'
    failed = check.get('failing') or []
    changed_tests = {p for p in check['changed'] if suite_role(p, check['command']) == 'test'}
    if failed and any(f.split('::')[0].replace('\\', '/') in changed_tests for f in failed):
        return ('An existing test was changed or removed: %s no longer passes in its original form.'
                % _names(failed)) + note
    if failed:
        return 'An existing test fails with the new code: %s.' % _names(failed) + note
    if changed_tests:
        return ('An existing test was changed or removed: %s no longer passes in its original form.'
                % _names(changed_tests)) + note
    return ('Your existing tests do not pass with the new code (exit code %s).' % check.get('exit_code')) + note


def settle_existing(check, request, reasons, guard):
    """Finish the existing-tests check (D-71, D-84): (preserved, check) with its plain summary.

    With no changed or removed existing test this is D-71 unchanged. Otherwise every such test needs
    the Builder's reason (`reasons`, from its `kel-test-changes` block); the original-tests run may fail
    only on those tests; and they must pass in their new form with the original test setup. `guard` is
    who judges the reasons: 'verifier' (the independent Verifier rules on each one after this) or
    'request' (D-85 small work, no Verifier: each reason must quote the words of the request it relies on).
    """
    state = check['state']
    edits = check.get('edits') or []
    if edits and state in ('passed', 'failed'):
        for entry in edits:
            entry['justification'] = _match(entry, reasons or [])
            entry['justified'] = _justified(entry, request, guard)
        check['unjustified'] = [e['test'] for e in edits if not e['justified']]
        check['guard'] = guard
        if check.get('covered'):
            if check['unjustified']:
                state = 'failed' if state == 'failed' else 'unjustified'
            elif check.get('changed_exit_code') not in (0, None):
                state = 'changed_failed'
            else:
                state = 'changed'
        check['state'] = state
        preserved = state == 'changed'
    else:
        preserved = state in ('passed', 'none') and not check['missing']
    check['summary'] = _existing_summary(check)
    return preserved, check


def test_changes_of(tests):
    """The justified test changes recorded in one run's evidence: [{test, change, reason}]."""
    existing = (tests or {}).get('existing_tests') or {}
    if existing.get('state') != 'changed':
        return []
    return [{'test': e['test'], 'change': e['change'], 'reason': change_reason(e),
             'justification': e.get('justification'), 'breaks_original': bool(e.get('breaks_original'))}
            for e in existing.get('edits') or []]


def _baseline_bytes(workspace, base, path, expected):
    """The original bytes of one protected file, from the snapshot commit, checked against its digest."""
    for args in (('cat-file', 'blob'), ('cat-file', '--filters')):
        try:
            raw = git(workspace, *args, base + ':' + path)
        except PolicyError:
            continue
        if digest(raw) == expected:
            return raw
    raise PolicyError('Kel could not rebuild the original version of ' + path)


def _remove_tree(path):
    def writable(function, target, _error):
        try:
            os.chmod(target, stat.S_IWRITE)
            function(target)
        except OSError:
            pass
    if Path(path).exists():
        try:
            shutil.rmtree(path, onexc=writable)
        except TypeError:  # Python before 3.12
            shutil.rmtree(path, onerror=writable)


def build_original_tests_copy(workspace, target, base, baseline, after, command):
    """A throwaway copy of the changed workspace with the original test suite put back.

    Every baseline test and setup file gets its original bytes (a removed one comes back); new setup
    files are left out; new test files are left out too when the project already had tests, because a
    new test module can patch the code under test when it is imported. Everything else is the new code.
    """
    target = Path(target)
    _remove_tree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Git metadata stays behind: it can be large, and the test command runs on files, not history.
    shutil.copytree(workspace, target, symlinks=True,
                    ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache'))
    protected = protected_files(baseline, command)
    had_tests = any(suite_role(p, command) == 'test' for p in protected)
    for path, expected in protected.items():
        if after.get(path) != expected:
            dest = target / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(_baseline_bytes(workspace, base, path, expected))
    for path in after:
        if path in baseline:
            continue
        role = suite_role(path, command)
        if role == 'setup' or (role == 'test' and had_tests):
            (target / path).unlink(missing_ok=True)
    return target


def build_changed_tests_copy(workspace, target, base, baseline, after, command):
    """D-84: a throwaway copy with the Builder's changed tests in their new form but every original
    test setup file put back (and new setup files left out), so a changed test has to pass on its own
    merits — never because a conftest or config change skipped it. New test files stay out when the
    project already had tests, as in the original-tests copy."""
    target = Path(target)
    _remove_tree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(workspace, target, symlinks=True,
                    ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache'))
    protected = protected_files(baseline, command)
    had_tests = any(suite_role(p, command) == 'test' for p in protected)
    for path, expected in protected.items():
        if suite_role(path, command) == 'setup' and after.get(path) != expected:
            dest = target / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(_baseline_bytes(workspace, base, path, expected))
    for path in after:
        if path in baseline:
            continue
        role = suite_role(path, command)
        if role == 'setup' or (role == 'test' and had_tests):
            (target / path).unlink(missing_ok=True)
    return target


def original_tests_plan(baseline, after, command):
    """What the original-tests check has to do for this change (no side effects)."""
    protected = protected_files(baseline, command)
    tests = sorted(p for p in protected if suite_role(p, command) == 'test')
    added = [p for p in after if p not in baseline and suite_role(p, command)]
    plan = {'command': list(command), 'files': tests,
            'missing': sorted(p for p in tests if p not in after),
            'changed': sorted(p for p, h in protected.items() if p in after and after[p] != h),
            'added_setup': sorted(p for p in added if suite_role(p, command) == 'setup'),
            'added_tests': sorted(p for p in added if suite_role(p, command) == 'test')}
    # Nothing to preserve and nothing that could change how the command starts.
    plan['needed'] = bool(plan['missing'] or plan['changed'] or plan['added_setup']
                          or (tests and plan['added_tests']))
    plan['state'] = 'none' if not tests and not plan['needed'] else None
    return plan


def run_params(command, cwd):
    """One trusted test run: same sandbox request, scrubbed provider keys and time budget every time."""
    return {'command': command, 'cwd': str(cwd), 'timeoutMs': 90000,
            'sandboxPolicy': {'type': 'workspaceWrite', 'writableRoots': [str(cwd)], 'networkAccess': False},
            'env': {'ANTHROPIC_API_KEY':None,'OPENAI_API_KEY':None,'DEEPSEEK_API_KEY':None,'OPENROUTER_API_KEY':None}}


def _rpc_recorded(store, run_id, key):
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='coding_calls'").fetchone():
            return False
        return bool(db.execute('SELECT 1 FROM coding_calls WHERE run_id=? AND key=?', (run_id, key)).fetchone())


def retry_brief(store, run_id):
    """What the Builder is told before its next try after a repository check failed (D-71)."""
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='code_evidence'").fetchone():
            return None
        row = db.execute('SELECT tests FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()
    if not row:
        return None
    tests = json.loads(row['tests'])
    existing = tests.get('existing_tests') or {}
    failed = []
    if existing and not tests.get('existing_tests_preserved', True):
        failed.append(existing.get('summary') or 'Your existing tests did not pass in their original form.')
        output = (existing.get('stdout') or '') + (existing.get('stderr') or '')
    elif tests.get('exit_code') != 0:
        failed.append(tests.get('summary') or tests_summary(tests.get('exit_code'), tests.get('stdout'), tests.get('stderr')))
        output = (tests.get('stdout') or '') + (tests.get('stderr') or '')
    elif not tests.get('source_stable_during_tests', True):
        failed.append('Running the tests changed files in the project copy; tests must not write into the source.')
        output = ''
    elif (tests.get('ownership') or {}).get('outside'):
        from .code_streams import ownership_words
        failed.append(ownership_words(tests['ownership']['outside']) + ' Kel put those files back as they were before this try; leave them alone.')
        output = ''
    else:
        return None
    text = ('What failed on the last try (Kel\'s own test runs, not a guess): ' + ' '.join(failed) + '\n'
            'How Kel checks a change: it runs the test command on your change, and again on a copy where every '
            'existing test file and test setup file (conftest.py, sitecustomize.py, pytest.ini, pyproject.toml, '
            'setup.cfg, tox.ini, package.json, test configs and similar) is put back exactly as it was before your '
            'change, with new test setup files and new test files left out. Both runs must pass, except that an '
            'existing test the request directly contradicts may be changed or removed: then list it in the '
            '`kel-test-changes` block with the words of the request that contradict it, and it must pass in its new '
            'form with the original test settings. Never weaken, skip or remove any other existing test; add new '
            'tests as new test functions or new files (adding to an existing test file is fine); do not add or '
            'change test setup to change what runs.')
    if output.strip():
        text += '\nEnd of the failing output:\n' + _tail(output, 3000)
    return text


def file_manifest(root):
    root=Path(root)
    files={}
    def check(path):
        info=path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0):
            raise PolicyError('Linked paths are not allowed in coding evidence')
        if stat.S_ISREG(info.st_mode) and info.st_nlink>1:
            raise PolicyError('Hard-linked files are not allowed in coding evidence')
        return info
    if not stat.S_ISDIR(check(root).st_mode):raise PolicyError('Coding workspace must be a directory')
    def unreadable(error):
        raise PolicyError('Cannot inspect every coding workspace path') from error
    for directory,dirs,names in os.walk(root,followlinks=False,onerror=unreadable):
        parent=Path(directory)
        for name in dirs:check(parent/name)
        # Git owns its metadata. Other excluded trees still need link checks:
        # native commands can enter them even though they are not source evidence.
        dirs[:]=[name for name in dirs if name!='.git']
        for name in names:
            path=parent/name;info=check(path);relative=path.relative_to(root)
            if any(p in ('.git','__pycache__','.pytest_cache','node_modules','.venv') for p in relative.parts):continue
            if not stat.S_ISREG(info.st_mode):raise PolicyError('Special files are not allowed in coding evidence')
            if info.st_size>10_000_000:raise PolicyError('A source file exceeds the 10 MB evidence limit')
            files[relative.as_posix()]=digest(path.read_bytes())
    return files


def snapshot(source,target):
    """Copy the actual tracked and untracked source state, never alter its checkout."""
    from .containment import assert_usable_root
    assert_usable_root(source,purpose='a coding snapshot')
    source=Path(source).resolve(strict=True);target=Path(target).resolve()
    if target.exists():raise PolicyError('Snapshot target already exists')
    file_manifest(source)
    # Git may materialize symlinks as ordinary files on Windows. Check index mode
    # before cloning so that behavior cannot silently hide a linked source path.
    if any(entry.startswith(b'120000 ') for entry in git(source,'ls-files','--stage','-z').split(b'\0')):
        raise PolicyError('Tracked symbolic links are not supported in coding snapshots')
    git(source,'clone','--no-local','--no-hardlinks',str(source),str(target))
    git(target,'remote','remove','origin')
    patch=git(source,'diff','--binary','HEAD')
    if patch:git(target,'apply','--binary','-',input=patch)
    git(target,'config','core.autocrlf','false')
    # Preserve actual source bytes across Windows and Linux Git defaults.
    for raw in git(source,'ls-files','-z').split(b'\0'):
        if not raw:continue
        relative=Path(os.fsdecode(raw));candidate=source/relative
        if candidate.is_file():
            dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(candidate,dest)
    for raw in git(source,'ls-files','--others','--exclude-standard','-z').split(b'\0'):
        if not raw:continue
        relative=Path(os.fsdecode(raw));candidate=source/relative
        if candidate.is_symlink() or candidate.is_junction():raise PolicyError('Untracked path is linked')
        src=candidate.resolve(strict=True)
        if not src.is_relative_to(source):raise PolicyError('Untracked path escaped source')
        if any(part.startswith('.env') for part in relative.parts):continue
        if src.stat().st_size>10_000_000:raise PolicyError('Untracked file exceeds 10 MB')
        dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    file_manifest(target)
    git(target,'add','-A')
    git(target,'-c','user.name=Kel','-c','user.email=kel@localhost','commit','--allow-empty','-m','Kel source snapshot')
    return git(target,'rev-parse','HEAD').decode().strip()


class CodingAdapter:
    provider='codex-code'
    capabilities={'text','repository_edit','native_session','approval_stream'}
    def __init__(self,store):
        self.store=store
        self.context=Context(store)
        with contextlib.closing(store.connect()) as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS code_workspaces(job_id TEXT PRIMARY KEY,path TEXT,base TEXT,manifest TEXT);
            CREATE TABLE IF NOT EXISTS native_progress(seq INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,method TEXT,data TEXT,at REAL);
            CREATE TABLE IF NOT EXISTS approval_actions(approval_id TEXT PRIMARY KEY,action TEXT);
            CREATE TABLE IF NOT EXISTS code_evidence(run_id TEXT PRIMARY KEY,workspace TEXT,manifest TEXT,patch TEXT,patch_digest TEXT,tests TEXT,baseline_tests TEXT,at REAL);
            CREATE TABLE IF NOT EXISTS coding_phases(run_id TEXT PRIMARY KEY,phase TEXT,result TEXT,at REAL);
            ''')

    def approval(self,run,method,params,cancel):
        job=self.store.get(run['job_id'])
        # Stable action identity excludes delivery IDs and timestamps, retaining the exact command and scope.
        action={'method':method,'workspace':params.get('cwd'),'command':params.get('command'),
                'permissions':params.get('permissions'),'grantRoot':params.get('grantRoot'),
                'network':params.get('networkApprovalContext')}
        if method=='item/fileChange/requestApproval':
            with contextlib.closing(self.store.connect()) as db:
                events=db.execute("SELECT data FROM native_progress WHERE run_id=? AND method='item/started' ORDER BY seq DESC",(run['id'],)).fetchall()
            item=next((json.loads(e['data']).get('item',{}) for e in events if json.loads(e['data']).get('item',{}).get('id')==params.get('itemId')),None)
            action['changes']=item.get('changes') if item else None
            # Missing patch details cannot create a reusable wildcard grant.
            if not action['changes']:action['unrepeatable_request']=params.get('itemId')
        pid=job['contract'].get('project_id','default')
        if self.context.allowed(pid,action):return True
        from . import authority
        if authority.is_full(self.store):
            # D-64 Full access: go ahead without a prompt; the approval is still recorded
            # (actor full-access) and the job gets an Activity line saying what Kel did. Kel's own
            # app/data and credential folders stay out of reach (refused and recorded).
            from .code_streams import workspace_row
            ws=workspace_row(self.store,job['id'],run['milestone_id'])  # a parallel part's own copy, else the job's
            reason=authority.protected_hit(self.store,action,ws['path'] if ws else None)
            if reason:
                authority.refuse(self.store,job['id'],run['id'],action,reason,source='coding')
                return False
            authority.auto_approve(self.store,job['id'],run['id'],action,source='coding')
            return True
        with contextlib.closing(self.store.connect()) as db:
            prior=db.execute('SELECT a.id FROM approvals a JOIN approval_actions x ON x.approval_id=a.id WHERE a.run_id=? AND x.action=? ORDER BY a.rowid DESC LIMIT 1',(run['id'],encode(action))).fetchone()
        if prior:aid=prior['id']
        else:
            aid=self.store.request_approval(job['id'],run['id'],action,seconds=300)
            with self.store.transaction() as db:db.execute('INSERT INTO approval_actions VALUES(?,?)',(aid,encode(action)))
            # The conversation shows a decision card for this ask (in-chat approvals, V1.6).
            from .chat_approvals import announce_approval
            announce_approval(self.store, aid, job, action)
        while not (cancel and cancel.is_set()):
            with contextlib.closing(self.store.connect()) as db:
                row=db.execute('SELECT * FROM approvals WHERE id=?',(aid,)).fetchone()
            if row['status']!='PENDING':return row['status']=='APPROVED'
            if row['expires']<time.time():
                self.store.resolve_approval(aid,action,False)
                return False
            time.sleep(.2)
        return False

    def _original_tests(self,connection,run_id,contract,workspace,base,baseline,after,tests,resumed=False):
        """D-71: do the project's own tests, as they were before the change, pass against the new code?

        The configured run above covers new tests. This second run covers the old ones: a throwaway
        copy of the changed workspace with every original test and test setup file put back (see
        `build_original_tests_copy`), run with the same command, sandbox request, scrubbed keys and time
        budget. It is skipped when that copy would equal the workspace (then the first run already was
        the original suite). Its RPC has its own durable identity, so a restart reuses its receipt.

        D-84: it also finds every changed or removed existing test (`test_edits`). When the original run
        fails only on those, a third run (`build_changed_tests_copy`, its own durable identity) checks
        they pass in their new form with the original test setup. `settle_existing` then applies the
        Builder's reasons and who judges them.
        """
        command=contract['test_command']
        test_timeout=600 if (contract.get('context') or {}).get('kibble') else 100
        plan=original_tests_plan(baseline,after,command)
        check={k:v for k,v in plan.items() if k!='needed'}
        def done(state,**extra):
            check.update(state=state,**extra)
            return check
        if plan['state']=='none':
            return done('none',ran=False)
        if not plan['needed']:
            return done('passed' if tests['exitCode']==0 else 'failed',ran=False,exit_code=tests['exitCode'],
                        failing=failing_tests(tests['stdout'],tests['stderr']))
        if contract.get('runtime')!='native-host':
            # Older isolated runtimes cannot run a second copy; they keep the byte-for-byte rule.
            return done('legacy',ran=False,exit_code=None,failing=[])
        from .host_runtime import ORIGINAL_TESTS_DIR
        target=self.store.root/'native-logs'/run_id/ORIGINAL_TESTS_DIR
        try:
            # D-84: every changed or removed existing test, found from the code (never from the Builder).
            check['edits']=test_edits(workspace,base,baseline,after,command)
            if not (resumed and _rpc_recorded(self.store,run_id,EXISTING_TESTS_KEY)):
                build_original_tests_copy(workspace,target,base,baseline,after,command)
            receipt=connection.call('command/exec',run_params(command,target),timeout=test_timeout,key=EXISTING_TESTS_KEY)
        except (PolicyError,RuntimeError,TimeoutError,OSError) as exc:
            return done('error',ran=True,exit_code=None,failing=[],error=str(exc)[:300])
        finally:
            _remove_tree(target)
        failing=all_failing(receipt.get('stdout'),receipt.get('stderr'))
        done('passed' if receipt['exitCode']==0 else 'failed',ran=True,exit_code=receipt['exitCode'],
             failing=failing[:5],stdout=_tail(receipt.get('stdout')),stderr=_tail(receipt.get('stderr')),
             execution=receipt.get('_kel_execution'))
        edits=check['edits']
        if not edits:
            return check
        # Which original tests failed, and does a changed/removed test account for each one?
        refs=[_failing_ref(f) for f in failing]
        for entry in edits:
            entry['breaks_original']=any(ref and _covers(entry['test'],ref) for ref in refs)
        uncovered=[f for f,ref in zip(failing,refs) if not ref or not any(_covers(e['test'],ref) for e in edits)]
        check['uncovered']=uncovered[:5]
        check['covered']=receipt['exitCode']==0 or bool(failing and not uncovered)
        if not check['covered']:
            return check
        # D-84: the changed tests must pass in their new form on their own merits: original test setup
        # put back, new setup left out. When that copy equals the workspace the first run already was it.
        protected=protected_files(baseline,command)
        had_tests=any(suite_role(p,command)=='test' for p in protected)
        same=not (plan['added_setup'] or (had_tests and plan['added_tests'])
                  or any(suite_role(p,command)=='setup' for p in plan['changed']))
        if same:
            changed={'exitCode':tests['exitCode'],'stdout':tests['stdout'],'stderr':tests['stderr'],'ran':False}
        else:
            try:
                if not (resumed and _rpc_recorded(self.store,run_id,CHANGED_TESTS_KEY)):
                    build_changed_tests_copy(workspace,target,base,baseline,after,command)
                changed=dict(connection.call('command/exec',run_params(command,target),timeout=test_timeout,key=CHANGED_TESTS_KEY),ran=True)
            except (PolicyError,RuntimeError,TimeoutError,OSError) as exc:
                return done('error',error=str(exc)[:300])
            finally:
                _remove_tree(target)
        check.update(changed_ran=changed['ran'],changed_exit_code=changed['exitCode'],
                     changed_failing=failing_tests(changed.get('stdout'),changed.get('stderr')))
        if changed['ran']:
            check.update(changed_stdout=_tail(changed.get('stdout')),changed_stderr=_tail(changed.get('stderr')))
        return check

    def execute(self,prompt,run_id=None,session_id=None,cancel=None):
        with contextlib.closing(self.store.connect()) as db:
            run=dict(db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone())
            row=db.execute('SELECT * FROM code_workspaces WHERE job_id=?',(run['job_id'],)).fetchone()
            phase=db.execute('SELECT * FROM coding_phases WHERE run_id=?',(run_id,)).fetchone()
        if phase and phase['phase'] not in ('TURN_COMPLETED','TURN_DISPATCHED','TESTS_DISPATCHED'):
            raise PolicyError('Coding execution already dispatched; reconcile its durable phase')
        job=self.store.get(run['job_id']);contract=job['contract']
        # V1.5: the real effect point. A worker cannot start repository work or run the configured
        # test command without a valid lease and role policy; a revoked lease stops it here.
        from .authorize import authorize,role_for
        from .capabilities import capability_for_tool, recommendation
        role_info=role_for(self.store,run['job_id'],run['milestone_id'])
        for tool in ('git','run_tests','write'):
            decision=authorize(self.store,{'actor':'worker','worker':run_id,'job':run['job_id'],
                'milestone':run['milestone_id'],'role':(role_info or {}).get('template_id'),
                'role_tool_policy':(role_info or {}).get('tool_policy'),
                'capability':capability_for_tool(tool),
                'action_kind':'repo','tool':tool,'target':str(contract.get('root') or ''),
                'metadata':{'what':'make the planned changes in a safe copy of the project',
                            'why':'the task needs repository changes',
                            'fallback':'stop before any change and report'}})
            if decision['outcome']!='ALLOW':
                tool_capability=capability_for_tool(tool)
                return {'outcome':'BLOCKED','error':'Kel paused this work before any change: '+
                        str(decision.get('reason') or decision.get('rule') or 'authorization required'),
                        'authorization':decision.get('outcome'),
                        'capability':tool_capability,
                        'recommendation':recommendation(tool_capability,{'allowed':False,
                            'rule':decision.get('rule'),'reason':decision.get('reason')})}
        # V2-13: never snapshot a sensitive source — system folders, credential folders, Kel's own
        # data folder or an environment-protected app folder. Checked on every execute, not just
        # the first, so a project root that moves under one later is refused too.
        from .containment import assert_usable_root
        assert_usable_root(contract['root'],purpose='a coding snapshot',store=self.store)
        # D3 for code (code_streams): a part works in its own project copy under its own write lease;
        # the integration step combines the checked parts into the job's one copy before it runs.
        from . import code_streams
        stream=code_streams.stream_of(contract,run['milestone_id'])
        integrating=code_streams.is_integration(contract,run['milestone_id'])
        lease=None
        if stream:
            row=code_streams.stream_workspace(self.store,job,run['milestone_id'])
            lease=code_streams.take_lease(self.store,job['id'],run['milestone_id'],run_id)
        elif integrating and not row:
            code_streams.integrate(self.store,job)
            row=code_streams.workspace_row(self.store,job['id'],run['milestone_id'])
        if row:
            workspace=Path(row['path']);base=row['base'];baseline=json.loads(row['manifest'])
        else:
            workspace=self.store.root/'repositories'/job['id'];workspace.parent.mkdir(exist_ok=True)
            base=snapshot(contract['root'],workspace);baseline=file_manifest(workspace)
            with self.store.transaction() as db:db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',
                (job['id'],str(workspace),base,encode(baseline)))
        if phase and phase['phase']=='TURN_COMPLETED' and file_manifest(workspace)!=json.loads(phase['result']).get('_checkpoint_manifest'):
            raise PolicyError('Workspace changed before pending checks resumed')
        if phase and phase['phase'] in ('TURN_DISPATCHED','TESTS_DISPATCHED') and not host_alive(self.store,run_id):
            raise PolicyError('Native transport lost; unresolved effects cannot be replayed')
        from .kibble_work import stage_images
        input_images=stage_images(self.store,contract,run_id)
        if input_images:
            prompt+='\nRecorded screenshots copied into this run\'s temporary input folder. Inspect them: '+encode(input_images)
        connection=DurableCodingConnection(self.store,run_id,workspace)
        # D-67: a staffed step runs on its role's model and reasoning level. Codex takes both per
        # turn; Kel's Claude Code host takes them once per thread (--model/--fallback-model/--effort).
        from .staff import binding_for_run,update_call
        binding=binding_for_run(self.store,run_id)
        if run['provider']=='claude-code':
            run_options={'model':binding.get('model_arg'),'fallback_model':binding.get('fallback_arg'),
                         'thread_effort':binding.get('effort_arg')}
        else:
            run_options={'model':binding.get('model_arg'),
                         'effort':binding.get('effort_arg') if binding else 'low'}
        observed={}
        from .usage import TurnTokens
        tokens=TurnTokens()  # Routing 2 §5.2: the runtime's own token counts for this turn
        def progress(event):
            method=event.get('method','');params=event.get('params',{})
            tokens.observe(method,params)
            if method in ('kel/runtime','kel/thread') and (params.get('model') or params.get('reasoningEffort') or params.get('effort')):
                # What the runtime itself reports running — the only source for "ran".
                observed.update({k:v for k,v in {'model_used':params.get('model'),
                    'reasoning_used':observed.get('turn_reasoning') or params.get('reasoningEffort') or params.get('effort')}.items() if v})
                try:update_call(self.store,run_id,ran={'model':params.get('model'),
                    'reasoning':observed.get('reasoning_used'),
                    'model_confirmed':True if params.get('model') else None})
                except Exception:pass
            if method=='kel/turn' and params.get('reasoningEffort'):
                # LIVE-9: the level this turn really ran at (Codex takes it per turn), recorded over
                # the thread's default.
                observed['turn_reasoning']=params['reasoningEffort']
                observed['reasoning_used']=params['reasoningEffort']
                try:update_call(self.store,run_id,ran={'reasoning':params['reasoningEffort']})
                except Exception:pass
            # Persist bounded user-visible native events, not token-by-token reasoning.
            if method in ('kel/session','item/started','item/completed','turn/completed'):
                with self.store.transaction() as db:
                    data=encode(params)
                    if not db.execute('SELECT 1 FROM native_progress WHERE run_id=? AND method=? AND data=?',(run_id,method,data)).fetchone():
                        db.execute('INSERT INTO native_progress(run_id,method,data,at) VALUES(?,?,?,?)',
                            (run_id,method,data,time.time()))
                    if method=='kel/session':db.execute('UPDATE runs SET native_session=? WHERE id=?',(params['threadId'],run_id))
        from . import runtime_guard
        watch=None  # FN-01: the protected places, watched around the runtime's own turn
        try:
            if phase and phase['phase']!='TURN_DISPATCHED':
                result=json.loads(phase['result'])
            else:
                if not phase:
                    if stream:
                        # A part never carries an earlier try's change outside its own files.
                        code_streams.restore_outside(workspace,base,baseline,stream['write_paths'])
                    with self.store.transaction() as db:
                        db.execute('INSERT INTO coding_phases VALUES(?,?,?,?)',(run_id,'TURN_DISPATCHED','{}',time.time()))
                note=code_streams.integration_turn(self.store,job,run_id) if integrating else ''
                if integrating and note is None:
                    # Every part fitted: the combined copy goes straight to the full tests (no model turn).
                    result=code_streams.merged_result(self.store,job)
                    try:
                        from .staff import update_call
                        update_call(self.store,run_id,why='No model was needed: every part fitted together without a conflict.')
                    except Exception:
                        pass
                else:
                    watch=runtime_guard.Watch(self.store.root,workspace,run_id)
                    head='Source request: '+contract['request']+'\nWork in this isolated repository. Implement the requested change.'
                    if stream:
                        head=('Source request (for context; the other parts are built at the same time by other Builders in '
                              'separate copies): '+contract['request']+'\nWork in this isolated repository. Implement only your part: '
                              +stream['quote']+'\nYou own only these files: '+', '.join(stream['write_paths'])+'. Create or change '
                              'only these files; do not create, change or delete any other file (Kel refuses a change outside them).')
                    elif integrating:
                        head+='\n'+note
                    result=connection.run(head+' '+TEST_RULES+' '
                    'Do not change the source checkout. '
                    'Do not delete caches or clean the workspace. Kel runs tests after your turn. Avoid generating bytecode. '
                    'Test command: '+encode(contract['test_command'])
                    +('\nThis is a brand-new empty project: create the complete application source AND a smoke test file that the configured test command runs and passes. '
                      'Keep everything inside the project root. Prefer the Python standard library; only add dependencies the project can install and document them.' if contract.get('greenfield') else '')
                    +'\nContext:\n'+prompt,
                    session_id=session_id,cancel=cancel,on_event=progress,
                    on_approval=lambda m,p:self.approval(run,m,p,cancel),**run_options)
            result.update(observed)
            tokens.apply(result)
            breach=runtime_guard.settle(self.store,job['id'],run_id,watch,self.store.root/'native-logs'/run_id,result)
            if breach:return breach
            if result['outcome']!='SUCCESS':return result
            if not phase or phase['phase']=='TURN_DISPATCHED':
                result['_checkpoint_manifest']=file_manifest(workspace)
                with self.store.transaction() as db:
                    db.execute("UPDATE coding_phases SET phase='TURN_COMPLETED',result=?,at=? WHERE run_id=?",(encode(result),time.time(),run_id))
            before=result['_tests_before'] if phase and phase['phase']=='TESTS_DISPATCHED' else file_manifest(workspace)
            protected=protected_files(baseline,contract['test_command'])
            if cancel and cancel.is_set() and not (phase and phase['phase']=='TESTS_DISPATCHED'):
                return {'outcome':'CANCELLED','session_id':result.get('session_id')}
            if not phase or phase['phase']!='TESTS_DISPATCHED':
                result['_tests_before']=before
                with self.store.transaction() as db:
                    changed=db.execute("UPDATE coding_phases SET phase='TESTS_DISPATCHED',result=?,at=? WHERE run_id=? AND phase='TURN_COMPLETED'",(encode(result),time.time(),run_id)).rowcount
                    if changed!=1:raise PolicyError('Tests already dispatched; refusing duplicate execution')
            watch=runtime_guard.Watch(self.store.root,workspace,run_id)  # the project's own test code too
            test_timeout=600 if (contract.get('context') or {}).get('kibble') else 100
            tests=connection.call('command/exec',run_params(contract['test_command'],workspace),timeout=test_timeout)
            after=file_manifest(workspace)
            existing=self._original_tests(connection,run_id,contract,workspace,base,baseline,after,tests,
                                          resumed=bool(phase and phase['phase']=='TESTS_DISPATCHED'))
            breach=runtime_guard.settle(self.store,job['id'],run_id,watch,self.store.root/'native-logs'/run_id,result,
                                  actor="The project's tests")
            if breach:return breach
            after=file_manifest(workspace)  # the second run works on a copy; the workspace must not move
            stable=before==after
            git(workspace,'add','-A')
            patch=git(workspace,'diff','--cached','--binary',base).decode('utf-8','replace')
            # D-84/D-85: who judges the Builder's test changes — the independent Verifier when one
            # reviews this change, else the request itself (each reason must quote it).
            from .proportional import verifier_needed
            files=sum(1 for line in patch.splitlines() if line.startswith('diff --git '))
            lines=sum(1 for line in patch.splitlines() if line[:1] in '+-' and not line.startswith(('+++','---')))
            guard='verifier' if verifier_needed(job,files,lines)[0] else 'request'
            preserved,existing_check=settle_existing(existing,contract['request'],
                                                     builder_justifications(result.get('text')),guard)
            evidence={'exit_code':tests['exitCode'],'stdout':tests['stdout'],'stderr':tests['stderr'],
                      'summary':tests_summary(tests['exitCode'],tests['stdout'],tests['stderr']),
                      'existing_tests_preserved':preserved,'existing_tests':existing_check,
                      'source_stable_during_tests':stable,
                      'command':contract['test_command']}
            changes=test_changes_of(evidence)
            if changes:
                evidence.update(test_changes=changes,test_changes_guard=guard)
            if tests.get('_kel_execution'):evidence['execution']=tests['_kel_execution']
            if stream:
                evidence['ownership']=code_streams.ownership(self.store,lease,baseline,after,stream['write_paths'])
            if integrating:
                evidence['integration']=code_streams.summary(self.store,job['id'])
            with self.store.transaction() as db:
                db.execute('INSERT OR REPLACE INTO code_evidence VALUES(?,?,?,?,?,?,?,?)',
                    (run_id,str(workspace),encode(after),patch,digest(patch.encode()),encode(evidence),encode(protected),time.time()))
                db.execute("UPDATE coding_phases SET phase='EVIDENCE_CAPTURED',at=? WHERE run_id=?",(time.time(),run_id))
            # Trusted evidence stays outside the writable worker folder.
            verdict=(tests['exitCode']==0 and preserved and stable and bool(patch.strip())
                     and not (evidence.get('ownership') or {}).get('outside'))
            report='# Repository change\n\n'+result.get('text','')+'\n\n## Trusted checks\n'+json.dumps(evidence,indent=2)+'\n\n## Diff\n```diff\n'+patch+'\n```\n'
            result.update(text=report,code_verified=verdict)
            return result
        finally:
            connection.close()
            code_streams.release(self.store,lease)


# ---- D-84: the Verifier rules on each changed test ------------------------------------------------
RULINGS_SQL = ('CREATE TABLE IF NOT EXISTS test_change_rulings(run_id TEXT, test TEXT, ruling TEXT, why TEXT, '
               'reviewer_provider TEXT, reviewer_model TEXT, review_id TEXT, at REAL, PRIMARY KEY(run_id, test))')


def _evidence_row(store, run_id):
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='code_evidence'").fetchone():
            return None
        return db.execute('SELECT patch, tests FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()


def recorded_test_changes(store, run_id):
    """(changes, guard) recorded for one coding run: the justified changed/removed existing tests."""
    row = _evidence_row(store, run_id) if run_id else None
    if not row:
        return [], None
    try:
        tests = json.loads(row['tests'])
    except (TypeError, ValueError):
        return [], None
    return list(tests.get('test_changes') or []), tests.get('test_changes_guard')


def _file_diffs(patch, files):
    """The parts of a unified diff that touch the given files."""
    out, keep = [], False
    for line in str(patch or '').splitlines():
        if line.startswith('diff --git '):
            keep = any(line.endswith(' b/' + f) or (' a/' + f + ' ') in line for f in files)
        if keep:
            out.append(line)
    return '\n'.join(out)


def test_changes_section(store, run_id, *, for_verifier=False):
    """What a reviewer sees about the Builder's test changes (D-84), or '' when there were none."""
    changes, _guard = recorded_test_changes(store, run_id)
    if not changes:
        return ''
    row = _evidence_row(store, run_id)
    files = sorted({c['test'].split('::')[0] for c in changes})
    listed = [{'test': c['test'], 'change': c['change'], 'breaks_original_test': c.get('breaks_original'),
               'builder_reason': c.get('justification')} for c in changes]
    rulings = rulings_for(store, run_id)
    if rulings and not for_verifier:
        for item in listed:
            ruling = rulings.get(item['test'])
            if ruling:
                item['verifier_ruling'] = {'ruling': ruling['ruling'], 'why': ruling['why']}
    text = ('\nExisting tests the Builder changed or removed (D-84: allowed only where the request directly '
            "contradicts the test; untrusted evidence, the Builder's own reasons):\n" + json.dumps(listed)[:8000]
            + '\nThe test-file diff:\n' + _file_diffs(row['patch'] if row else '', files)[:20000])
    if for_verifier:
        text += ('\nRule on EACH listed test in "test_rulings": approve only when the change is necessary for the '
                 "request (the request's own words contradict the old expectation) and faithful to it (the new "
                 'expectation is exactly what the request asks, no weaker); reject a weakened, loosened, skipped '
                 'or deleted check the request does not require, an unrelated change, or anything that makes the '
                 'test pass without testing the requested behaviour. Add to your JSON: "test_rulings":[{"test":'
                 '"<id as listed>","ruling":"approve|reject","why":"<one sentence>"}].')
    return text


def rulings_for(store, run_id):
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='test_change_rulings'").fetchone():
            return {}
        return {row['test']: dict(row) for row in
                db.execute('SELECT * FROM test_change_rulings WHERE run_id=?', (run_id,))}


def record_rulings(store, run_id, rulings, *, review_id, reviewer_provider=None, reviewer_model=None):
    """Store the Verifier's ruling on each changed test; (verdict cap, findings) for its review.

    The cap is 'FAILED' when any change was rejected (an unjustified test change fails the step) and
    'UNCERTAIN' when a change got no ruling; None when every change was approved. Rulings are keyed by
    run and test, so a restarted review replaces them rather than adding to them.
    """
    changes, guard = recorded_test_changes(store, run_id)
    if not changes or guard != 'verifier':
        return None, []
    given = [r for r in (rulings if isinstance(rulings, list) else []) if isinstance(r, dict)]
    reasons = [{'test': str(r.get('test') or ''), 'ruling': str(r.get('ruling') or '').strip().lower(),
                'why': ' '.join(str(r.get('why') or '').split())[:400]} for r in given]
    cap, findings, now = None, [], time.time()
    with store.transaction() as db:
        db.execute(RULINGS_SQL)
        for change in changes:
            ruling = _match(change, [r for r in reasons if r['test']])
            verdict = (ruling or {}).get('ruling')
            verdict = ('approve' if verdict in ('approve', 'approved')
                       else 'reject' if verdict in ('reject', 'rejected') else None)
            name = _short_test(change['test'])
            if verdict == 'reject':
                cap = 'FAILED'
                findings.append('The Verifier rejected the change to %s: %s'
                                % (name, ruling.get('why') or 'the request does not require it'))
            elif verdict is None:
                cap = cap or 'UNCERTAIN'
                findings.append('The Verifier did not rule on the change to %s.' % name)
            db.execute('INSERT OR REPLACE INTO test_change_rulings VALUES(?,?,?,?,?,?,?,?)',
                       (run_id, change['test'], verdict or 'none', (ruling or {}).get('why'), reviewer_provider,
                        reviewer_model, review_id, now))
    return cap, findings


def test_changes_view(store, run_id):
    """`test_changes` for Nick's surfaces: [{test, reason, approved_by, ruling, change, id}] (D-84)."""
    changes, guard = recorded_test_changes(store, run_id)
    if not changes:
        return []
    rulings = rulings_for(store, run_id) if guard == 'verifier' else {}
    out = []
    for change in changes:
        item = {'test': _short_test(change['test']), 'id': change['test'], 'change': change['change'],
                'reason': change.get('reason'), 'approved_by': None, 'ruling': None}
        if guard == 'request':
            quote = (change.get('justification') or {}).get('request_quote')
            item.update(ruling='approved', approved_by='Kel: your request says "%s"' % quote)
        else:
            ruling = rulings.get(change['test'])
            if ruling and ruling['ruling'] == 'approve':
                label = None
                try:
                    from .role_models import describe_model
                    label = describe_model(raw=ruling.get('reviewer_model'))[0]
                except Exception:
                    label = None
                item.update(ruling='approved', approved_by='Verifier' + (' (%s)' % label if label else ''))
            elif ruling and ruling['ruling'] == 'reject':
                item.update(ruling='rejected', why=ruling.get('why'))
        out.append(item)
    return out


def test_changes_result_line(store, job):
    """The one plain line for the result (D-84), from the approved changes of the code step, or None."""
    run_id = (((job.get('milestones') or {}).get('code') or {}).get('artifact') or {}).get('run_id')
    view = [c for c in test_changes_view(store, run_id) if c['ruling'] == 'approved'] if run_id else []
    return test_changes_line(view)


def check_evidence(store,run_id):
    with contextlib.closing(store.connect()) as db:
        row=db.execute('SELECT * FROM code_evidence WHERE run_id=?',(run_id,)).fetchone()
    if not row:return 'UNCERTAIN'
    tests=json.loads(row['tests'])
    if tests['exit_code']!=0 or not tests['existing_tests_preserved'] or not tests['source_stable_during_tests']:return 'FAILED'
    if (tests.get('ownership') or {}).get('outside'):return 'FAILED'  # a parallel part wrote outside its files
    if not row['patch'].strip():return 'UNCERTAIN'
    if digest(row['patch'].encode())!=row['patch_digest']:return 'UNCERTAIN'
    if file_manifest(Path(row['workspace']))!=json.loads(row['manifest']):return 'UNCERTAIN'
    return 'VERIFIED'


def repository_check(store, run_id):
    """The repository_evidence check for one run, with what it found in plain words (D-71).

    `failure` names the kind of failure: 'existing_tests' (an original test does not pass, or a test
    file was removed — the same change will fail the same way, so Kel allows one informed retry),
    'tests' (the configured run failed), 'unstable' (the tests changed the source) or None.
    """
    verdict = check_evidence(store, run_id)
    check = {'kind': 'repository_evidence', 'verdict': verdict}
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT tests, patch FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()
    if not row:
        check['reason'] = 'Kel has no record of its own test run for this change.'
        return check
    tests = json.loads(row['tests'])
    summary = tests.get('summary') or tests_summary(tests.get('exit_code'), tests.get('stdout'), tests.get('stderr'))
    existing = (tests.get('existing_tests') or {}).get('summary')
    if not existing and 'existing_tests' not in tests:
        # Evidence recorded before D-71: only the old byte-for-byte rule was checked.
        existing = ('Your existing test files are unchanged.' if tests.get('existing_tests_preserved')
                    else 'An existing test file was changed or removed.')
    check.update(tests=summary, existing=existing)
    if tests.get('test_changes'):
        # D-84: which existing tests Kel changed and why (the Verifier's rulings are read live).
        check['test_changes'] = [{'test': c['test'], 'change': c['change'], 'reason': c['reason']}
                                 for c in tests['test_changes']]
    if verdict == 'FAILED':
        if not tests.get('existing_tests_preserved', True):
            check.update(failure='existing_tests', reason=existing)
        elif tests.get('exit_code') != 0:
            check.update(failure='tests', reason=summary)
        elif (tests.get('ownership') or {}).get('outside'):
            from .code_streams import ownership_words
            check.update(failure='ownership', reason=ownership_words(tests['ownership']['outside']))
        else:
            check.update(failure='unstable',
                         reason='Running the tests changed files in the project copy, so the result cannot be trusted.')
    elif verdict == 'UNCERTAIN':
        check['reason'] = ('The change was empty: nothing in the project copy changed.' if not row['patch'].strip()
                           else 'The project copy changed after Kel ran its tests, so the recorded result no longer matches it.')
    return check


def recover_checked_code(store,run,row):
    """Recover already-captured tests and diff; never start another coding turn."""
    from .runner import process_identity,terminate_known_process
    with contextlib.closing(store.connect()) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'code_evidence','native_processes','native_progress'}.issubset(tables):return None
        evidence=db.execute('SELECT * FROM code_evidence WHERE run_id=?',(run['id'],)).fetchone()
        child=db.execute('SELECT * FROM native_processes WHERE run_id=?',(run['id'],)).fetchone()
        events=db.execute("SELECT data FROM native_progress WHERE run_id=? AND method='turn/completed' ORDER BY seq DESC LIMIT 1",(run['id'],)).fetchone()
    if not evidence or not child or not child['identity'] or not events:return None
    try:
        turn=json.loads(events['data']).get('turn',{})
        if turn.get('status')!='completed':return None
        # Test receipt is captured after command/exec returned. With its broker gone,
        # this app-server has no remaining authorized work; stop only its exact handle.
        if process_identity(child['pid'])==child['identity']:
            if not terminate_known_process(child['pid'],child['identity']):return None
            return 'LIVE'
        if check_evidence(store,run['id'])!='VERIFIED':return None
        tests=json.loads(evidence['tests'])
        text='# Recovered repository change\n\nThe native coding turn and configured tests completed before the broker exited.\n\n## Trusted checks\n'+json.dumps(tests,indent=2)+'\n\n## Diff\n```diff\n'+evidence['patch']+'\n```\n'
        return {'outcome':'SUCCESS','text':text,'session_id':run['native_session'],'turn_id':turn.get('id'),'code_verified':True,'recovered_from_code_evidence':True}
    except (ValueError,TypeError,KeyError,OSError,PolicyError):return None


def recover_pending_checks(store,run):
    """Identify the narrow window where tests provably have not been dispatched."""
    from .runner import process_identity,terminate_known_process
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='coding_phases'").fetchone():return None
        phase=db.execute('SELECT * FROM coding_phases WHERE run_id=?',(run['id'],)).fetchone()
        child=db.execute('SELECT * FROM native_processes WHERE run_id=?',(run['id'],)).fetchone()
    from .code_streams import workspace_row
    workspace=workspace_row(store,run['job_id'],run['milestone_id'])
    if not phase or phase['phase']!='TURN_COMPLETED' or not child or not workspace:return None
    if run['state']!='RUNNING':return None
    try:
        result=json.loads(phase['result'])
        if result.get('outcome')!='SUCCESS' or not result.get('turn_id'):return None
        if not child['identity']:return None
        if process_identity(child['pid'])==child['identity']:
            return 'LIVE' if terminate_known_process(child['pid'],child['identity']) else None
        if file_manifest(Path(workspace['path']))!=result.get('_checkpoint_manifest'):return None
        return 'RESUME_CHECKS'
    except (ValueError,TypeError,OSError,PolicyError):return None
