"""D-71: "existing tests preserved" means the original tests still pass against the new code.

Found in a live test: a Builder that added `multiply` to calc.py and a `test_multiply` to the existing
test_calc.py (the usual way to add a test) was failed because test_calc.py was no longer byte-identical,
then retried the same deterministic failure four times across models, and the result said
"failed check repository_evidence: expected None".

Here the coding adapter runs for real against a scratch git project: the trusted test runs go through the
native host's own `command/exec` (a real subprocess running pytest); only the model turn is a fake that
makes exactly the change each case describes. No model is called.
"""
import contextlib
import json
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

from kel import coding
from kel.coding import (CodingAdapter, EXISTING_TESTS_KEY, build_original_tests_copy, check_evidence,
                        compile_coding, file_manifest, git, original_tests_plan, protected_files,
                        repository_check, snapshot, suite_role)
from kel.coding_transport import init as transport_init
from kel.core import Store, digest, encode, explain_failure, verification_summary
from kel.host_runtime import HostConnection

PYTEST = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider']

CALC = 'def add(a, b):\n    return a + b\n'
TEST_CALC = 'from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n'


def make_project(base, files=None):
    root = Path(base) / 'proj'
    root.mkdir()
    git(root, 'init')
    for name, text in (files or {'calc.py': CALC, 'test_calc.py': TEST_CALC}).items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding='utf-8')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class Crash(Exception):
    """The engine process dying after a test run was dispatched (its receipt is already durable)."""


class FakeConnection:
    """The durable coding connection with a fake model turn and the real native-host test runner.

    Receipts are kept per (run, key) across instances, like `coding_calls`, so a resumed execute gets
    the receipt of a run that already happened instead of running it again.
    """
    receipts = {}
    executed = []
    crash_after = None

    def __init__(self, store, run_id, workspace, change=None):
        self.store, self.run_id, self.workspace, self.change = store, run_id, Path(workspace), change
        transport_init(store)
        logs = store.root / 'native-logs' / run_id
        logs.mkdir(parents=True, exist_ok=True)
        host = object.__new__(HostConnection)
        host.workspace, host.logs, host.provider = str(self.workspace), logs, 'claude'
        self.host = host
        self.prompts = []

    def run(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if self.change:
            self.change(self.workspace)
        return {'outcome': 'SUCCESS', 'text': 'Made the requested change.', 'session_id': 's', 'turn_id': 't'}

    def call(self, method, params, timeout=25, key=None):
        key = key or method
        slot = (self.run_id, key)
        if slot in FakeConnection.receipts:
            return FakeConnection.receipts[slot]
        with self.store.transaction() as db:
            db.execute("INSERT OR IGNORE INTO coding_calls VALUES(?,?,?,'DISPATCHED',NULL)",
                       (self.run_id, key, encode(params)))
        result = self.host.call(method, params, timeout)
        FakeConnection.executed.append((key, params['cwd']))
        FakeConnection.receipts[slot] = result
        if FakeConnection.crash_after == key:
            FakeConnection.crash_after = None
            raise Crash(key)
        return result

    def close(self):
        pass


class GateBase(unittest.TestCase):
    command = PYTEST
    files = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        FakeConnection.receipts, FakeConnection.executed, FakeConnection.crash_after = {}, [], None
        self.store = Store(Path(self.tmp.name) / 'data')
        CodingAdapter(self.store)
        self.project = make_project(self.tmp.name, self.files)
        self.job = self.store.create(compile_coding('Add a multiply(a, b) function to calc.py and a pytest '
                                                    'test for it in test_calc.py.', self.project, self.command))

    def execute(self, change, run=None):
        run = run or self.store.claim(self.job, 'code', provider='claude-code')
        self.connections = []

        def connect(store, run_id, workspace):
            connection = FakeConnection(store, run_id, workspace, change)
            self.connections.append(connection)
            return connection
        with mock.patch.object(coding, 'DurableCodingConnection', connect):
            result = CodingAdapter(self.store).execute('Context.', run_id=run['id'], session_id=None, cancel=None)
        return run, result

    def evidence(self, run):
        with contextlib.closing(self.store.connect()) as db:
            return json.loads(db.execute('SELECT tests FROM code_evidence WHERE run_id=?',
                                         (run['id'],)).fetchone()['tests'])


def live_change(workspace):
    """Exactly what Claude Opus 5.5 did in the live test."""
    (workspace / 'calc.py').write_text(CALC + '\n\ndef multiply(a, b):\n    return a * b\n', encoding='utf-8')
    (workspace / 'test_calc.py').write_text(
        TEST_CALC.replace('from calc import add', 'from calc import add, multiply')
        + '\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n', encoding='utf-8')


def broken_add(workspace):
    (workspace / 'calc.py').write_text('def add(a, b):\n    return a - b\n', encoding='utf-8')


class LiveScenarioTests(GateBase):
    def test_adding_a_test_to_the_existing_test_file_passes_and_verifies(self):
        run, result = self.execute(live_change)
        self.assertTrue(result['code_verified'], result['text'][-2000:])
        self.assertEqual(check_evidence(self.store, run['id']), 'VERIFIED')
        tests = self.evidence(run)
        self.assertEqual(tests['exit_code'], 0)
        self.assertTrue(tests['existing_tests_preserved'])
        existing = tests['existing_tests']
        self.assertEqual((existing['state'], existing['ran'], existing['changed']), ('passed', True, ['test_calc.py']))
        self.assertEqual(existing['summary'], 'Your existing tests still pass.')
        self.assertIn('Your tests passed (2 passed', tests['summary'])
        # Both trusted runs happened: one on the workspace, one on the original-tests copy.
        self.assertEqual([k for k, _ in FakeConnection.executed], ['command/exec', EXISTING_TESTS_KEY])
        self.assertTrue(FakeConnection.executed[1][1].endswith('original-tests'))
        self.assertIn('1 passed', existing['stdout'])  # the original suite: test_add only
        self.assertFalse((self.store.root / 'native-logs' / run['id'] / 'original-tests').exists(),
                         'the throwaway copy is removed')
        check = repository_check(self.store, run['id'])
        self.assertEqual(check['verdict'], 'VERIFIED')
        self.assertEqual(check['existing'], 'Your existing tests still pass.')

    def test_a_source_only_change_needs_one_run(self):
        run, result = self.execute(lambda w: (w / 'calc.py').write_text(CALC + '\n# tidy\n', encoding='utf-8'))
        self.assertTrue(result['code_verified'])
        existing = self.evidence(run)['existing_tests']
        self.assertEqual((existing['state'], existing['ran']), ('passed', False))
        self.assertEqual(len(FakeConnection.executed), 1)

    def test_a_new_test_file_is_left_out_of_the_original_run(self):
        def change(w):
            (w / 'calc.py').write_text(CALC + '\n\ndef multiply(a, b):\n    return a * b\n', encoding='utf-8')
            (w / 'test_multiply.py').write_text('from calc import multiply\n\n\ndef test_multiply():\n'
                                                '    assert multiply(3, 4) == 12\n', encoding='utf-8')
        run, result = self.execute(change)
        self.assertTrue(result['code_verified'])
        existing = self.evidence(run)['existing_tests']
        self.assertEqual((existing['state'], existing['added_tests']), ('passed', ['test_multiply.py']))
        self.assertIn('1 passed', existing['stdout'])


class WeakenedTestsTests(GateBase):
    def assert_existing_failure(self, run, result, *phrases):
        self.assertFalse(result['code_verified'])
        self.assertEqual(check_evidence(self.store, run['id']), 'FAILED')
        check = repository_check(self.store, run['id'])
        self.assertEqual(check['failure'], 'existing_tests')
        for phrase in phrases:
            self.assertIn(phrase, check['reason'])
        return check

    def test_deleting_an_existing_test_file_fails(self):
        def change(w):
            (w / 'test_calc.py').unlink()
            (w / 'test_other.py').write_text('def test_other():\n    assert True\n', encoding='utf-8')
        run, result = self.execute(change)
        self.assert_existing_failure(run, result, 'An existing test file was removed: test_calc.py.')

    def test_deleting_an_existing_test_to_hide_broken_code_fails(self):
        def change(w):
            broken_add(w)
            (w / 'test_calc.py').write_text('from calc import add\n', encoding='utf-8')
        run, result = self.execute(change)
        self.assertEqual(self.evidence(run)['exit_code'], 5, 'the changed suite collects no tests')
        self.assert_existing_failure(run, result, 'test_calc.py::test_add no longer passes in its original form')

    def test_editing_an_existing_assertion_to_make_it_pass_fails(self):
        def change(w):
            broken_add(w)
            (w / 'test_calc.py').write_text(TEST_CALC.replace('== 5', '== -1'), encoding='utf-8')
        run, result = self.execute(change)
        self.assertEqual(self.evidence(run)['exit_code'], 0, 'the edited test passes on its own')
        check = self.assert_existing_failure(
            run, result, 'An existing test was changed or removed: test_calc.py::test_add no longer passes '
                         'in its original form.')
        self.assertIn('Your tests passed', check['tests'])

    def test_a_conftest_that_skips_tests_fails(self):
        def change(w):
            broken_add(w)
            (w / 'conftest.py').write_text(textwrap.dedent('''
                import pytest

                def pytest_collection_modifyitems(config, items):
                    for item in items:
                        item.add_marker(pytest.mark.skip(reason='later'))
            '''), encoding='utf-8')
        run, result = self.execute(change)
        self.assertEqual(self.evidence(run)['exit_code'], 0, 'every test was skipped, so the run "passed"')
        self.assert_existing_failure(run, result, 'test_calc.py::test_add', 'test settings (conftest.py)')

    def test_a_module_that_shadows_the_test_runner_fails(self):
        # The D-49 class: a new file that changes how the test command starts (here a `pytest.py` that
        # `python -m pytest` would import instead of pytest, exiting 0).
        def change(w):
            broken_add(w)
            (w / 'pytest.py').write_text('raise SystemExit(0)\n', encoding='utf-8')
        run, result = self.execute(change)
        self.assertEqual(self.evidence(run)['exit_code'], 0)
        self.assert_existing_failure(run, result, 'test_calc.py::test_add', 'pytest.py')

    def test_breaking_existing_code_without_touching_tests_fails_as_an_existing_test(self):
        run, result = self.execute(broken_add)
        check = self.assert_existing_failure(run, result, 'An existing test fails with the new code: '
                                                          'test_calc.py::test_add.')
        self.assertIn('Your tests failed: test_calc.py::test_add', check['tests'])


class SitecustomizeTests(unittest.TestCase):
    """D-49's own bypass was a new sitecustomize.py: it is test setup, and the original run leaves it out."""

    def test_setup_files_are_classified_and_left_out_of_the_original_copy(self):
        command = ['python', '-m', 'pytest', '-q']
        for path in ('sitecustomize.py', 'conftest.py', 'tests/conftest.py', 'pytest.ini', 'pyproject.toml',
                     'setup.cfg', 'tox.ini', 'package.json', 'jest.config.js', 'vitest.config.ts', 'pytest.py',
                     'Makefile', '.mocharc.yml'):
            self.assertEqual(suite_role(path, command), 'setup', path)
        for path in ('test_calc.py', 'tests/helpers.py', 'src/calc_test.go', 'web/app.test.ts',
                     'spec/calc_spec.rb', 'src/CalcTest.java', '__tests__/a.js'):
            self.assertEqual(suite_role(path, command), 'test', path)
        for path in ('calc.py', 'src/app.ts', 'README.md', 'contest.py'):
            self.assertIsNone(suite_role(path, command), path)
        self.assertEqual(suite_role('smoke_test.py', ['python', 'smoke_test.py']), 'test')
        self.assertEqual(suite_role('checks/a.py', ['python', '-m', 'pytest', 'checks/']), 'test')

        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            workspace = Path(tmp) / 'ws'
            base = snapshot(root, workspace)
            baseline = file_manifest(workspace)
            (workspace / 'sitecustomize.py').write_text('import sys\nsys.exit = lambda *a: None\n')
            (workspace / 'test_calc.py').write_text(TEST_CALC + '\n\ndef test_more():\n    pass\n')
            (workspace / 'test_new.py').write_text('def test_new():\n    pass\n')
            after = file_manifest(workspace)
            plan = original_tests_plan(baseline, after, command)
            self.assertEqual((plan['added_setup'], plan['changed'], plan['added_tests']),
                             (['sitecustomize.py'], ['test_calc.py'], ['test_new.py']))
            copy = build_original_tests_copy(workspace, Path(tmp) / 'copy', base, baseline, after, command)
            self.assertFalse((copy / 'sitecustomize.py').exists())
            self.assertFalse((copy / 'test_new.py').exists())
            self.assertEqual(digest((copy / 'test_calc.py').read_bytes()), baseline['test_calc.py'])
            self.assertEqual(file_manifest(workspace), after, 'building the copy never touches the workspace')
            self.assertEqual(set(protected_files(baseline, command)), {'test_calc.py'})

    def test_a_brand_new_project_keeps_its_new_smoke_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'new'
            root.mkdir()
            git(root, 'init')
            git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '--allow-empty', '-m', 'e')
            workspace = Path(tmp) / 'ws'
            base = snapshot(root, workspace)
            baseline = file_manifest(workspace)
            (workspace / 'app.py').write_text('print(1)\n')
            (workspace / 'smoke_test.py').write_text('import app\n')
            plan = original_tests_plan(baseline, file_manifest(workspace), ['python', 'smoke_test.py'])
            self.assertEqual((plan['state'], plan['needed']), ('none', False))
            (workspace / 'pyproject.toml').write_text('[project]\nname="x"\n')
            after = file_manifest(workspace)
            plan = original_tests_plan(baseline, after, ['python', 'smoke_test.py'])
            self.assertTrue(plan['needed'])
            copy = build_original_tests_copy(workspace, Path(tmp) / 'copy', base, baseline, after,
                                             ['python', 'smoke_test.py'])
            self.assertTrue((copy / 'smoke_test.py').exists(), 'no old tests: the new ones are the suite')
            self.assertFalse((copy / 'pyproject.toml').exists())


class RestartTests(GateBase):
    def test_a_restart_after_the_original_run_reuses_both_receipts(self):
        FakeConnection.crash_after = EXISTING_TESTS_KEY
        run = self.store.claim(self.job, 'code', provider='claude-code')
        with self.assertRaises(Crash):
            self.execute(live_change, run)
        with contextlib.closing(self.store.connect()) as db:
            phase = db.execute('SELECT phase FROM coding_phases WHERE run_id=?', (run['id'],)).fetchone()['phase']
        self.assertEqual(phase, 'TESTS_DISPATCHED')
        with mock.patch.object(coding, 'host_alive', return_value=True):
            _, result = self.execute(None, run)
        self.assertTrue(result['code_verified'])
        self.assertEqual([k for k, _ in FakeConnection.executed], ['command/exec', EXISTING_TESTS_KEY],
                         'neither test run was repeated')
        self.assertEqual(self.connections[-1].prompts, [], 'no second model turn')
        with contextlib.closing(self.store.connect()) as db:
            phase = db.execute('SELECT phase FROM coding_phases WHERE run_id=?', (run['id'],)).fetchone()['phase']
        self.assertEqual(phase, 'EVIDENCE_CAPTURED')

    def test_the_transport_keeps_a_separate_identity_for_the_original_run(self):
        from kel.coding_transport import DurableCodingConnection
        transport_init(self.store)
        run = self.store.claim(self.job, 'code', provider='claude-code')
        with self.store.transaction() as db:
            db.execute("INSERT INTO coding_hosts VALUES(?,?,NULL,NULL,'RUNNING',?)",
                       (run['id'], str(Path(self.tmp.name).resolve()), time.time() + 60))
            for key, code in (('command/exec', 0), (EXISTING_TESTS_KEY, 1)):
                db.execute("INSERT INTO coding_calls VALUES(?,?,?,'FINISHED',?)",
                           (run['id'], key, encode({'cwd': key}), encode({'result': {'exitCode': code}})))
        with mock.patch('kel.coding_transport.host_alive', return_value=True):
            connection = DurableCodingConnection(self.store, run['id'], self.tmp.name)
            self.assertEqual(connection.call('command/exec', {'cwd': 'command/exec'}), {'exitCode': 0})
            self.assertEqual(connection.call('command/exec', {'cwd': EXISTING_TESTS_KEY}, key=EXISTING_TESTS_KEY),
                             {'exitCode': 1})
            from kel.core import PolicyError
            with self.assertRaises(PolicyError):
                connection.call('command/exec', {}, key='turn/start#x')


class RetryTests(GateBase):
    """A deterministic failure gets one informed retry, then Kel stops and says so in plain words."""

    def test_one_informed_retry_then_stop(self):
        from kel.engine import Engine
        prompts = []
        test = self

        class Builder:
            capabilities = {'text', 'repository_edit'}

            def execute(self, prompt, run_id=None, session_id=None, cancel=None):
                prompts.append(prompt)

                def change(w):
                    broken_add(w)
                    (w / 'test_calc.py').write_text(TEST_CALC.replace('== 5', '== -1'), encoding='utf-8')

                def connect(store, rid, workspace):
                    return FakeConnection(store, rid, workspace, change)
                with mock.patch.object(coding, 'DurableCodingConnection', connect):
                    return CodingAdapter(test.store).execute(prompt, run_id=run_id, session_id=None, cancel=cancel)

        engine = Engine(self.store, {'claude-code': Builder()})
        try:
            deadline = time.time() + 120
            while time.time() < deadline:
                engine.tick()
                job = self.store.get(self.job)
                if job['state'] == 'CLOSED' and job.get('assessment') and not engine.active:
                    with contextlib.closing(self.store.connect()) as db:
                        if db.execute('SELECT 1 FROM publications WHERE job_id=?', (self.job,)).fetchone():
                            break
                time.sleep(.05)
        finally:
            engine.close()
        job = self.store.get(self.job)
        milestone = job['milestones']['code']
        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'FAILED'))
        self.assertEqual((milestone['state'], milestone['attempts']), ('EXHAUSTED', 2), 'not four identical tries')
        self.assertEqual(len(prompts), 2)
        self.assertNotIn('What failed on the last try', prompts[0])
        self.assertIn('What failed on the last try', prompts[1])
        self.assertIn('test_calc.py::test_add no longer passes in its original form', prompts[1])
        self.assertIn('put back exactly as it was', prompts[1])
        text = explain_failure(job)
        self.assertIn("The change didn't pass Kel's checks, so nothing was applied to your project.", text)
        self.assertIn('Why: An existing test was changed or removed: test_calc.py::test_add no longer passes', text)
        self.assertIn('it failed the same way, so Kel stopped rather than repeat it', text)
        self.assertIn('Kel updates a test only where your request contradicts it', text)  # D-84
        summary = verification_summary(job)
        self.assertIn('• Your tests passed', summary)
        self.assertIn('• An existing test was changed or removed', summary)
        with contextlib.closing(self.store.connect()) as db:
            published = db.execute("SELECT text FROM messages WHERE job_id=? AND role='assistant'",
                                   (self.job,)).fetchone()['text']
        for jargon in ('repository_evidence', 'expected None', 'failed check'):
            self.assertNotIn(jargon, published + summary)


class LiveScenarioEngineTests(GateBase):
    """The live request end to end through the engine: tests, review, verdict, publication."""

    def test_the_live_change_is_verified_and_published(self):
        from kel.engine import Engine
        test = self

        class Builder:
            capabilities = {'text', 'repository_edit'}

            def execute(self, prompt, run_id=None, session_id=None, cancel=None):
                def connect(store, rid, workspace):
                    return FakeConnection(store, rid, workspace, live_change)
                with mock.patch.object(coding, 'DurableCodingConnection', connect):
                    return CodingAdapter(test.store).execute(prompt, run_id=run_id, session_id=None, cancel=cancel)

        class Reviewer:
            def review(self, store, job_id, mid):
                job = store.get(job_id)
                m = job['milestones'][mid]
                store.record_review(job_id, mid, m['artifact']['sha256'], 'reviewer', 'VERIFIED',
                                    ['The diff adds multiply and its test; test_add is intact.'],
                                    job['contract_version'], reviewer_provider='codex', reviewer_model='gpt-6-astra')

        engine = Engine(self.store, {'claude-code': Builder()}, reviewer=Reviewer())
        try:
            deadline = time.time() + 120
            while time.time() < deadline:
                engine.tick()
                with contextlib.closing(self.store.connect()) as db:
                    done = db.execute('SELECT 1 FROM publications WHERE job_id=?', (self.job,)).fetchone()
                if done and not engine.active and not engine.reviews:
                    break
                time.sleep(.05)
        finally:
            engine.close()
        job = self.store.get(self.job)
        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'VERIFIED'))
        self.assertEqual(job['milestones']['code']['attempts'], 1)
        summary = verification_summary(job)
        self.assertIn('• Your tests passed (2 passed', summary)
        self.assertIn('• Your existing tests still pass.', summary)


class PlanNoteTests(unittest.TestCase):
    def test_the_standard_plan_is_named_plainly(self):
        from kel.office import _kel_member
        coding_job = {'contract': {'kind': 'coding', 'planner': {'provider': None, 'model': None,
                                                                  'compiler': 'coding-contract-v2'}}}
        self.assertEqual(_kel_member(coding_job)['note'], 'Kel used its standard coding plan.')
        research = {'contract': {'planner': {'compiler': 'research-v1'}}}
        self.assertEqual(_kel_member(research)['note'], 'Kel used its standard research plan.')
        planned = {'contract': {'planner': {'provider': 'codex', 'model': 'gpt-6-luna'}}}
        self.assertIsNone(_kel_member(planned)['note'])


if __name__ == '__main__':
    unittest.main()
