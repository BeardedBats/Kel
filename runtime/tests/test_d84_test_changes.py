"""D-84: Kel owns the tests. D-85: review depth is proportional.

The Builder may change an existing test only where the requested behaviour contradicts it, and says why
in a structured block. Kel finds every changed or removed existing test itself; the original-tests run
may fail only on those; they must pass in their new form with the original test setup; and each one is
approved by the independent Verifier (or, for small work with no Verifier, its reason must quote the
request). Every other original test still passes in its original form, and a conftest can never skip.

Like test_original_tests_gate, the trusted test runs are real pytest subprocesses through the native
host's `command/exec`; only the model turns (Builder and Verifier) are fakes. No model is called.
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

from kel import coding, proportional, staff
from kel.coding import (CHANGED_TESTS_KEY, CodingAdapter, EXISTING_TESTS_KEY, builder_justifications,
                        check_evidence, compile_coding, record_rulings, repository_check)
from kel.core import Store

from test_original_tests_gate import Crash, FakeConnection, make_project

PYTEST = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider']

CALC = ('def add(a, b):\n    return a + b\n\n\n'
        'def subtract(a, b):\n    return a - b\n\n\n'
        'def divide(a, b):\n    return a / b\n')
TEST_CALC = ('import pytest\n\nfrom calc import add, divide, subtract\n\n\n'
             'def test_add():\n    assert add(2, 3) == 5\n\n\n'
             'def test_subtract():\n    assert subtract(5, 3) == 2\n\n\n'
             'def test_divide():\n    assert divide(6, 3) == 2\n\n\n'
             'def test_divide_by_zero():\n    with pytest.raises(ZeroDivisionError):\n        divide(1, 0)\n')
DIVIDE_REQUEST = 'Make divide(1, 0) return 0 instead of raising.'
NEW_DIVIDE = CALC.replace('def divide(a, b):\n    return a / b\n',
                          'def divide(a, b):\n    if b == 0:\n        return 0\n    return a / b\n')
NEW_TEST = TEST_CALC.replace('def test_divide_by_zero():\n    with pytest.raises(ZeroDivisionError):\n        divide(1, 0)\n',
                             'def test_divide_by_zero():\n    assert divide(1, 0) == 0\n')


def block(*entries):
    return 'Done.\n```kel-test-changes\n' + json.dumps(list(entries)) + '\n```\n'


DIVIDE_REASON = {'test': 'test_calc.py::test_divide_by_zero', 'request_quote': 'return 0 instead of raising',
                 'was': 'an error', 'now': '0'}


def divide_change(w):
    (w / 'calc.py').write_text(NEW_DIVIDE, encoding='utf-8')
    (w / 'test_calc.py').write_text(NEW_TEST, encoding='utf-8')


class Connection(FakeConnection):
    text = 'Made the requested change.'

    def run(self, prompt, **kwargs):
        result = super().run(prompt, **kwargs)
        result['text'] = Connection.text
        return result


class Base(unittest.TestCase):
    request = DIVIDE_REQUEST
    staffed = False

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        FakeConnection.receipts, FakeConnection.executed, FakeConnection.crash_after = {}, [], None
        Connection.text = 'Made the requested change.'
        self.store = Store(Path(self.tmp.name) / 'data')
        CodingAdapter(self.store)
        self.project = make_project(self.tmp.name, {'calc.py': CALC, 'test_calc.py': TEST_CALC})
        contract = compile_coding(self.request, self.project, PYTEST)
        if self.staffed:
            contract['staffing'] = staff.plan_job(None, contract, self.request)
        self.job = self.store.create(contract)

    def execute(self, change, text=None, run=None):
        if text is not None:
            Connection.text = text
        run = run or self.store.claim(self.job, 'code', provider='claude-code')
        self.connections = []

        def connect(store, run_id, workspace):
            connection = Connection(store, run_id, workspace, change)
            self.connections.append(connection)
            return connection
        with mock.patch.object(coding, 'DurableCodingConnection', connect):
            result = CodingAdapter(self.store).execute('Context.', run_id=run['id'], session_id=None, cancel=None)
        return run, result

    def evidence(self, run):
        with contextlib.closing(self.store.connect()) as db:
            return json.loads(db.execute('SELECT tests FROM code_evidence WHERE run_id=?',
                                         (run['id'],)).fetchone()['tests'])


class DetectionTests(Base):
    def test_a_legit_behaviour_change_with_its_test_updated_is_detected_and_passes(self):
        run, result = self.execute(divide_change, block(DIVIDE_REASON))
        tests = self.evidence(run)
        existing = tests['existing_tests']
        self.assertEqual(existing['state'], 'changed', existing.get('summary'))
        self.assertTrue(tests['existing_tests_preserved'])
        self.assertTrue(result['code_verified'])
        self.assertEqual([e['test'] for e in existing['edits']], ['test_calc.py::test_divide_by_zero'])
        self.assertTrue(existing['edits'][0]['breaks_original'])
        self.assertEqual(existing['failing'], ['test_calc.py::test_divide_by_zero'])
        self.assertEqual(tests['test_changes_guard'], 'verifier', 'an unstaffed job keeps its Verifier')
        self.assertEqual(existing['summary'], 'Kel updated 1 test to match your change: test_divide_by_zero '
                                              'now expects 0 instead of an error; your other existing tests '
                                              'still pass.')
        # The configured run already was the changed-tests run (no setup changed): two runs, not three.
        self.assertEqual([k for k, _ in FakeConnection.executed], ['command/exec', EXISTING_TESTS_KEY])
        self.assertEqual(check_evidence(self.store, run['id']), 'VERIFIED')
        check = repository_check(self.store, run['id'])
        self.assertEqual(check['test_changes'][0]['reason'], 'test_divide_by_zero now expects 0 instead of an error')

    def test_formatting_only_edits_and_new_tests_are_not_changes(self):
        def change(w):
            (w / 'calc.py').write_text(CALC + '\n\ndef multiply(a, b):\n    return a * b\n', encoding='utf-8')
            (w / 'test_calc.py').write_text(
                TEST_CALC.replace('assert add(2, 3) == 5', 'assert add(2,  3) == 5  # spacing')
                .replace('from calc import add, divide, subtract', 'from calc import add, divide, multiply, subtract')
                + '\n\ndef _helper():\n    return 12\n\n\ndef test_multiply():\n    assert multiply(3, 4) == _helper()\n',
                encoding='utf-8')
        run, result = self.execute(change)
        existing = self.evidence(run)['existing_tests']
        self.assertTrue(result['code_verified'], existing.get('summary'))
        self.assertEqual(existing['edits'], [])
        self.assertEqual(existing['summary'], 'Your existing tests still pass.')

    def test_a_helper_that_shadows_the_code_under_test_is_a_change(self):
        def change(w):
            (w / 'test_calc.py').write_text(TEST_CALC + '\n\ndef divide(a, b):\n    return 0\n', encoding='utf-8')
        run, result = self.execute(change)
        existing = self.evidence(run)['existing_tests']
        self.assertEqual([e['test'] for e in existing['edits']], ['test_calc.py::(module)'])
        self.assertFalse(result['code_verified'])
        self.assertEqual(existing['state'], 'unjustified')
        self.assertIn('changed without a reason from your request', existing['summary'])

    def test_builder_block_is_parsed(self):
        found = builder_justifications(block(DIVIDE_REASON) + '\n```kel-test-changes\nnot json\n```')
        self.assertEqual(found, [DIVIDE_REASON])


class WeakeningTests(Base):
    request = 'Add a multiply(a, b) function to calc.py with a test.'

    def test_a_weakened_assertion_unrelated_to_the_request_without_a_reason_fails(self):
        def change(w):
            (w / 'calc.py').write_text(CALC.replace('return a + b', 'return a - b'), encoding='utf-8')
            (w / 'test_calc.py').write_text(TEST_CALC.replace('== 5', '== -1'), encoding='utf-8')
        run, result = self.execute(change)
        self.assertFalse(result['code_verified'])
        check = repository_check(self.store, run['id'])
        self.assertEqual(check['failure'], 'existing_tests')
        self.assertIn('test_calc.py::test_add no longer passes in its original form', check['reason'])

    def test_a_weakened_assertion_with_a_made_up_reason_is_rejected_by_the_verifier(self):
        def change(w):
            (w / 'calc.py').write_text(CALC.replace('return a + b', 'return a - b'), encoding='utf-8')
            (w / 'test_calc.py').write_text(TEST_CALC.replace('== 5', '== -1'), encoding='utf-8')
        reason = {'test': 'test_add', 'request_quote': 'multiply', 'was': 'add(2, 3) == 5', 'now': '-1'}
        run, result = self.execute(change, block(reason))
        tests = self.evidence(run)
        self.assertEqual(tests['existing_tests']['state'], 'changed', 'deterministically it looks justified')
        self.assertEqual(tests['test_changes_guard'], 'verifier')
        cap, findings = record_rulings(self.store, run['id'], [
            {'test': 'test_calc.py::test_add', 'ruling': 'reject',
             'why': 'The request adds multiply; it does not change add, so this weakens test_add.'}],
            review_id='rev1', reviewer_provider='codex', reviewer_model='gpt-6-astra')
        self.assertEqual(cap, 'FAILED')
        self.assertIn('The Verifier rejected the change to test_add', findings[0])
        view = coding.test_changes_view(self.store, run['id'])
        self.assertEqual((view[0]['ruling'], view[0]['approved_by']), ('rejected', None))


class DeletedTestTests(Base):
    request = 'Remove the subtract function from calc.py; nobody uses it any more.'
    staffed = True

    def remove_subtract(self, w):
        (w / 'calc.py').write_text(CALC.replace('def subtract(a, b):\n    return a - b\n\n\n', ''), encoding='utf-8')
        (w / 'test_calc.py').write_text(
            TEST_CALC.replace('def test_subtract():\n    assert subtract(5, 3) == 2\n\n\n', '')
            .replace('add, divide, subtract', 'add, divide'), encoding='utf-8')

    def test_a_deleted_test_is_rejected_without_a_reason(self):
        run, result = self.execute(self.remove_subtract)
        existing = self.evidence(run)['existing_tests']
        # Dropping the removed name from the import line is not a test change; the deleted test is.
        self.assertEqual([(e['test'], e['change']) for e in existing['edits']],
                         [('test_calc.py::test_subtract', 'removed')])
        self.assertEqual((existing['state'], existing['unjustified']), ('failed', ['test_calc.py::test_subtract']))
        self.assertIn('An existing test was changed or removed', existing['summary'])
        self.assertFalse(result['code_verified'])

    def test_a_deleted_test_is_accepted_when_the_request_removed_the_feature(self):
        reason = {'test': 'test_calc.py::test_subtract', 'request_quote': 'Remove the subtract function',
                  'was': 'subtract(5, 3) == 2', 'now': ''}
        run, result = self.execute(self.remove_subtract, block(reason))
        tests = self.evidence(run)
        # The original test file no longer imports (subtract is gone): its unchanged tests are checked in
        # the new file with the original test setup instead.
        self.assertEqual(tests['existing_tests']['failing'], ['test_calc.py'])
        self.assertEqual(tests['existing_tests']['state'], 'changed', tests['existing_tests'].get('summary'))
        self.assertEqual(tests['test_changes_guard'], 'request', 'small staffed work: no Verifier (D-85)')
        self.assertTrue(result['code_verified'])
        view = coding.test_changes_view(self.store, run['id'])
        removed = next(c for c in view if c['change'] == 'removed')
        self.assertEqual(removed['approved_by'], 'Kel: your request says "Remove the subtract function"')
        self.assertIn('Kel removed 1 test: test_subtract was removed because your change removed what it checked',
                      coding.test_changes_line(view))

    def test_deleting_a_test_for_a_feature_that_still_exists_is_rejected(self):
        def change(w):
            (w / 'test_calc.py').write_text(
                TEST_CALC.replace('def test_add():\n    assert add(2, 3) == 5\n\n\n', ''), encoding='utf-8')
        reason = {'test': 'test_add', 'request_quote': 'add is covered elsewhere', 'was': 'add works', 'now': ''}
        run, result = self.execute(change, block(reason))
        existing = self.evidence(run)['existing_tests']
        self.assertEqual(existing['state'], 'unjustified', 'the quote is not in the request')
        self.assertFalse(result['code_verified'])
        self.assertEqual(repository_check(self.store, run['id'])['failure'], 'existing_tests')

    def test_deleting_a_test_file_whose_feature_remains_is_rejected(self):
        run, result = self.execute(lambda w: (w / 'test_calc.py').unlink())
        existing = self.evidence(run)['existing_tests']
        self.assertFalse(result['code_verified'])
        self.assertEqual(existing['summary'], 'An existing test file was removed: test_calc.py.')


class ConftestTests(Base):
    CONFTEST = textwrap.dedent('''
        import pytest

        def pytest_collection_modifyitems(config, items):
            for item in items:
                item.add_marker(pytest.mark.skip(reason='later'))
    ''')

    def test_a_skip_via_conftest_is_still_blocked(self):
        def change(w):
            (w / 'calc.py').write_text(CALC.replace('return a + b', 'return a - b'), encoding='utf-8')
            (w / 'conftest.py').write_text(self.CONFTEST, encoding='utf-8')
        run, result = self.execute(change, block({'test': 'conftest.py', 'request_quote': 'divide',
                                                  'was': 'ran', 'now': 'skipped'}))
        self.assertFalse(result['code_verified'])
        check = repository_check(self.store, run['id'])
        self.assertEqual(check['failure'], 'existing_tests')
        self.assertIn('test_calc.py::test_add', check['reason'])

    def test_a_changed_test_that_passes_only_by_a_conftest_skip_is_blocked(self):
        def change(w):
            # divide still raises, but the "updated" test expects 0 and a conftest skips everything.
            (w / 'test_calc.py').write_text(NEW_TEST, encoding='utf-8')
            (w / 'conftest.py').write_text(self.CONFTEST, encoding='utf-8')
            (w / 'calc.py').write_text(CALC + '\n# touched\n', encoding='utf-8')
        run, result = self.execute(change, block(DIVIDE_REASON))
        existing = self.evidence(run)['existing_tests']
        self.assertEqual(self.evidence(run)['exit_code'], 0, 'the skip made the configured run "pass"')
        self.assertEqual(existing['state'], 'changed_failed', existing.get('summary'))
        self.assertIn('test_calc.py::test_divide_by_zero', existing['summary'])
        self.assertFalse(result['code_verified'])
        self.assertEqual([k for k, _ in FakeConnection.executed],
                         ['command/exec', EXISTING_TESTS_KEY, CHANGED_TESTS_KEY])


class RestartTests(Base):
    def test_a_restart_after_the_changed_tests_run_reuses_every_receipt(self):
        def change(w):
            divide_change(w)
            (w / 'pytest.ini').write_text('[pytest]\n', encoding='utf-8')  # a setup file: the third run is needed
        FakeConnection.crash_after = CHANGED_TESTS_KEY
        run = self.store.claim(self.job, 'code', provider='claude-code')
        with self.assertRaises(Crash):
            self.execute(change, block(DIVIDE_REASON), run)
        with mock.patch.object(coding, 'host_alive', return_value=True):
            _, result = self.execute(None, run=run)
        self.assertTrue(result['code_verified'], self.evidence(run)['existing_tests'].get('summary'))
        self.assertEqual([k for k, _ in FakeConnection.executed],
                         ['command/exec', EXISTING_TESTS_KEY, CHANGED_TESTS_KEY], 'no run was repeated')
        self.assertEqual(self.connections[-1].prompts, [], 'no second model turn')
        # The Builder's reasons came back from the durable turn result, not a new turn.
        self.assertEqual(self.evidence(run)['test_changes'][0]['justification']['request_quote'],
                         'return 0 instead of raising')
        # A restarted review replaces its rulings rather than adding to them.
        for ruling in ('reject', 'approve'):
            record_rulings(self.store, run['id'], [{'test': 'test_divide_by_zero', 'ruling': ruling, 'why': 'x'}],
                           review_id='r-' + ruling, reviewer_provider='codex', reviewer_model='gpt-6-astra')
        view = coding.test_changes_view(self.store, run['id'])
        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]['ruling'], 'approved')


class VerifierEndToEndTests(Base):
    """Through the engine: Builder turn, trusted runs, the Verifier's ruling, verdict and the result line."""

    def run_engine(self, ruling):
        from kel.commander import Commander
        from kel.engine import Engine
        test = self
        prompts = []

        class Builder:
            capabilities = {'text', 'repository_edit'}

            def execute(self, prompt, run_id=None, session_id=None, cancel=None):
                Connection.text = block(DIVIDE_REASON)

                def connect(store, rid, workspace):
                    return Connection(store, rid, workspace, divide_change)
                with mock.patch.object(coding, 'DurableCodingConnection', connect):
                    return CodingAdapter(test.store).execute(prompt, run_id=run_id, session_id=None, cancel=cancel)

        class Verifier:
            provider, model = 'codex', 'gpt-6-astra'

            def execute(self, prompt, run_id=None, **kwargs):
                prompts.append(prompt)
                return {'outcome': 'SUCCESS', 'model_used': 'gpt-6-astra', 'text': json.dumps({
                    'verdict': 'VERIFIED', 'findings': ['divide(1, 0) now returns 0 as asked.'],
                    'test_rulings': [{'test': 'test_calc.py::test_divide_by_zero', 'ruling': ruling,
                                      'why': 'The request asks for 0 instead of an error.'}]})}

        engine = Engine(self.store, {'claude-code': Builder()}, reviewer=Commander(Verifier()))
        try:
            deadline = time.time() + 120
            while time.time() < deadline:
                engine.tick()
                job = self.store.get(self.job)
                if job['state'] == 'CLOSED' and not engine.active and not engine.reviews:
                    with contextlib.closing(self.store.connect()) as db:
                        if db.execute('SELECT 1 FROM publications WHERE job_id=?', (self.job,)).fetchone():
                            break
                time.sleep(.05)
        finally:
            engine.close()
        return self.store.get(self.job), prompts

    def published(self):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute("SELECT text FROM messages WHERE job_id=? AND role='assistant'",
                              (self.job,)).fetchone()['text']

    def test_an_approved_test_change_is_verified_and_named_in_one_plain_line(self):
        job, prompts = self.run_engine('approve')
        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'VERIFIED'))
        self.assertIn('Existing tests the Builder changed or removed', prompts[0])
        self.assertIn('"test_rulings"', prompts[0])
        self.assertIn('-    with pytest.raises(ZeroDivisionError)', prompts[0], 'the test diff is shown')
        run_id = job['milestones']['code']['artifact']['run_id']
        view = coding.test_changes_view(self.store, run_id)
        self.assertEqual(view, [{'test': 'test_divide_by_zero', 'id': 'test_calc.py::test_divide_by_zero',
                                 'change': 'changed',
                                 'reason': 'test_divide_by_zero now expects 0 instead of an error',
                                 'approved_by': 'Verifier (GPT-6 Astra)', 'ruling': 'approved'}])
        self.assertIn('Kel updated 1 test to match your change: test_divide_by_zero now expects 0 instead of '
                      'an error.', self.published())

    def test_a_rejected_test_change_fails_the_step(self):
        job, _prompts = self.run_engine('reject')
        self.assertEqual(job['verdict'], 'FAILED')
        review = next(c for c in job['milestones']['code']['checks'] if c['kind'] == 'manual_review')
        self.assertEqual(review['verdict'], 'FAILED')
        self.assertIn('The Verifier rejected the change to test_divide_by_zero', review['findings'][0])
        self.assertNotIn('Kel updated 1 test', self.published())


class ProportionalTests(unittest.TestCase):
    """D-85: the lightest check that fits."""

    def plan(self, request, **extra):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            contract = compile_coding(request, root, PYTEST)
            contract.update(extra)
            return staff.plan_job(None, contract, request)

    def test_small_routine_code_has_no_second_or_third_review(self):
        record = self.plan(DIVIDE_REQUEST)
        self.assertEqual(record['review']['verifier']['when'], 'if_large')
        self.assertFalse(record['oracle']['required'])
        self.assertFalse(record['sentinel']['required'])
        self.assertFalse(record['red_team']['required'])
        job = {'contract': {'kind': 'coding', 'staffing': record}}
        self.assertEqual(proportional.verifier_needed(job, 1, 6), (False, 'a small change (1 file, 6 changed lines)'))
        self.assertTrue(proportional.verifier_needed(job, 4, 10)[0])
        self.assertTrue(proportional.verifier_needed(job, 1, 81)[0])

    def test_security_work_gets_the_verifier_and_sentinel_but_not_the_oracle(self):
        record = self.plan('Add a login page with password reset to the app')
        self.assertEqual(record['review']['verifier']['when'], 'always')
        self.assertTrue(record['sentinel']['required'])
        self.assertFalse(record['oracle']['required'], 'never three reviews on routine work')
        self.assertIsNone(record['red_team']['size_trigger'], 'the Red Team is for D4 only')

    def test_a_privacy_word_alone_does_not_bring_sentinel(self):
        record = self.plan('Stop sending telemetry from the settings screen')
        self.assertFalse(record['sentinel']['required'])
        self.assertIn('no security or data-migration work', record['sentinel']['not_needed'])

    def test_hard_to_undo_work_gets_the_oracle(self):
        record = self.plan('Write a database migration that drops the legacy table and deploy it')
        self.assertTrue(record['oracle']['required'])

    def test_prototypes_and_short_drafts_get_a_quick_sanity_check(self):
        self.assertEqual(self.plan('Build me a tiny todo app', greenfield=True)['review']['verifier']['when'], 'never')
        self.assertEqual(proportional.verifier_decision('writing', 'D0', [])['when'], 'never')
        self.assertEqual(proportional.verifier_decision('research', 'D1', [])['when'], 'always')
        self.assertEqual(proportional.verifier_decision('writing', 'D2', [])['when'], 'always')

    def test_jobs_staffed_before_d85_keep_their_verifier(self):
        record = self.plan(DIVIDE_REQUEST)
        record['review'].pop('verifier')
        self.assertEqual(proportional.verifier_needed({'contract': {'staffing': record}}, 1, 1), (True, None))
        self.assertEqual(proportional.verifier_needed({'contract': {}}, 1, 1), (True, None))


class ProportionalEngineTests(Base):
    staffed = True

    def test_a_small_change_is_verified_without_an_independent_reviewer(self):
        from kel.engine import Engine
        test = self
        reviewed = []

        class Builder:
            capabilities = {'text', 'repository_edit'}

            def execute(self, prompt, run_id=None, session_id=None, cancel=None):
                Connection.text = block(DIVIDE_REASON)

                def connect(store, rid, workspace):
                    return Connection(store, rid, workspace, divide_change)
                with mock.patch.object(coding, 'DurableCodingConnection', connect):
                    return CodingAdapter(test.store).execute(prompt, run_id=run_id, session_id=None, cancel=cancel)

        class Reviewer:
            def review(self, store, job_id, mid):
                reviewed.append(mid)

        engine = Engine(self.store, {'claude-code': Builder()}, reviewer=Reviewer())
        try:
            deadline = time.time() + 120
            while time.time() < deadline:
                engine.tick()
                with contextlib.closing(self.store.connect()) as db:
                    if db.execute('SELECT 1 FROM publications WHERE job_id=?', (self.job,)).fetchone():
                        break
                time.sleep(.05)
        finally:
            engine.close()
        job = self.store.get(self.job)
        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'VERIFIED'))
        self.assertEqual(reviewed, [], 'no independent reviewer ran')
        review = next(c for c in job['milestones']['code']['checks'] if c['kind'] == 'manual_review')
        self.assertTrue(review['proportional'])
        self.assertIn('No independent review was needed: a small change', review['findings'][0])
        with contextlib.closing(self.store.connect()) as db:
            text = db.execute("SELECT text FROM messages WHERE job_id=? AND role='assistant'",
                              (self.job,)).fetchone()['text']
        self.assertNotIn('a separate review approved', text)
        self.assertIn('a change this small needed no separate review', text)
        self.assertIn('Kel updated 1 test to match your change: test_divide_by_zero now expects 0 instead of an '
                      'error.', text)
        from kel.office import detail
        view = detail(self.store, self.job)
        self.assertEqual(view['test_changes'][0]['approved_by'],
                         'Kel: your request says "return 0 instead of raising"')
        self.assertEqual(view['review']['test_changes'], view['test_changes'])
        self.assertTrue(view['review']['not_needed'].startswith('No independent review was needed'))
        self.assertTrue(view['test_changes_line'].startswith('Kel updated 1 test'))


if __name__ == '__main__':
    unittest.main()
