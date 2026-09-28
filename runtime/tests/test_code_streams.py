"""D3 for code: parallel Builders on independent, disjoint-write parts, then one integration step.

Fake runtimes only: the model turn is a fake that writes exactly what each case describes; the trusted
test runs are real (the native host's own `command/exec` runs pytest in each copy), so each part's
tests, the D-71 original-tests check, the combined run and the evidence are the real ones. No model is
called. Cases: independent parts run at once and combine cleanly; a conflict falls back to a
sequential Builder; a failed part is retried alone (and a part that writes outside its files fails);
a restart mid-part and mid-merge never applies anything twice; the caps; a sequential plan stays one
step.
"""
import contextlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from test_original_tests_gate import PYTEST, Crash, FakeConnection, make_project  # noqa: E402

from kel import code_streams, coding, office, parallel, staff  # noqa: E402
from kel.coding import CodingAdapter, compile_coding, git, repository_check  # noqa: E402
from kel.core import PolicyError, Store  # noqa: E402
from kel.engine import Engine  # noqa: E402

REQUEST = ('Add three independent helpers, each with a test: a slugify helper in text_tools.py, '
           'a clamp helper in num_tools.py, and a chunk helper in list_tools.py.')
QUOTES = ('a slugify helper in text_tools.py', 'a clamp helper in num_tools.py', 'a chunk helper in list_tools.py')
MODULES = ('text_tools', 'num_tools', 'list_tools')
CODE = {
    'text_tools': ('def slugify(text):\n    return "-".join(text.lower().split())\n',
                   'from text_tools import slugify\n\n\ndef test_slugify():\n    assert slugify("A B") == "a-b"\n'),
    'num_tools': ('def clamp(x, lo, hi):\n    return max(lo, min(hi, x))\n',
                  'from num_tools import clamp\n\n\ndef test_clamp():\n    assert clamp(5, 0, 3) == 3\n'),
    'list_tools': ('def chunk(items, n):\n    return [items[i:i + n] for i in range(0, len(items), n)]\n',
                   'from list_tools import chunk\n\n\ndef test_chunk():\n    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]\n'),
}


def proposal(count=3, quotes=QUOTES, modules=MODULES):
    return {'independent': True, 'parts': [
        {'objective': 'Add %s with its test' % quotes[i], 'source_quote': quotes[i],
         'write_paths': ['%s.py' % modules[i], 'test_%s.py' % modules[i]]} for i in range(count)]}


def helper(module):
    def change(workspace):
        source, test = CODE[module]
        (workspace / ('%s.py' % module)).write_text(source, encoding='utf-8')
        (workspace / ('test_%s.py' % module)).write_text(test, encoding='utf-8')
    return change


class Turns:
    """The fake model turns, per step and attempt, with the peak number running at once."""

    def __init__(self, changes, delay=0.4, together=None):
        self.changes, self.delay = changes, delay
        # `together`: that many turns wait for each other, so "they ran at once" never depends on timing.
        self.barrier = threading.Barrier(together, timeout=60) if together else None
        self.lock = threading.Lock()
        self.live = self.peak = 0
        self.prompts = {}

    def change_for(self, store, run_id):
        with contextlib.closing(store.connect()) as db:
            run = db.execute('SELECT job_id, milestone_id, rowid FROM runs WHERE id=?', (run_id,)).fetchone()
            attempt = db.execute('SELECT COUNT(*) FROM runs WHERE job_id=? AND milestone_id=? AND rowid<=?',
                                 (run['job_id'], run['milestone_id'], run['rowid'])).fetchone()[0]
        mid = run['milestone_id']
        change = self.changes.get((mid, attempt), self.changes.get(mid))
        turns = self

        def wrapped(workspace):
            with turns.lock:
                turns.live += 1
                turns.peak = max(turns.peak, turns.live)
            try:
                if turns.barrier is not None:
                    turns.barrier.wait()
                time.sleep(turns.delay)
                if change:
                    change(workspace)
            finally:
                with turns.lock:
                    turns.live -= 1
        return mid, wrapped

    def count(self, mid):
        return len(self.prompts.get(mid, []))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        FakeConnection.receipts, FakeConnection.executed, FakeConnection.crash_after = {}, [], None
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        CodingAdapter(self.store)
        self.project = make_project(self.tmp.name)
        self.turns = Turns({})
        test = self

        def connect(store, run_id, workspace):
            mid, change = test.turns.change_for(store, run_id)
            connection = FakeConnection(store, run_id, workspace, change)
            original = connection.run

            def run(prompt, **kwargs):
                test.turns.prompts.setdefault(mid, []).append(prompt)
                return original(prompt, **kwargs)
            connection.run = run
            return connection
        patcher = mock.patch.object(coding, 'DurableCodingConnection', connect)
        patcher.start()
        self.addCleanup(patcher.stop)

    def contract(self, parts=None, request=REQUEST):
        single = compile_coding(request, self.project, PYTEST)
        planned = code_streams.parallel_contract(
            single, code_streams.validate_parts(request, parts or proposal(), PYTEST))
        planned['staffing'] = staff.plan_job(self.store, planned, request)
        return planned

    def run_job(self, contract, timeout=180):
        test = self

        class Builder:
            capabilities = {'text', 'repository_edit'}

            def execute(self, prompt, run_id=None, session_id=None, cancel=None):
                return CodingAdapter(test.store).execute(prompt, run_id=run_id, session_id=None, cancel=cancel)

        class Reviewer:
            def review(self, store, job_id, mid):
                job = store.get(job_id)
                m = job['milestones'][mid]
                store.record_review(job_id, mid, m['artifact']['sha256'], 'reviewer', 'VERIFIED',
                                    ['The combined diff adds the three helpers with their tests.'],
                                    job['contract_version'], reviewer_provider='codex', reviewer_model='gpt-6-astra')

        engine = Engine(self.store, {'claude-code': Builder()}, reviewer=Reviewer())
        job = engine.submit(contract, budget=24)
        try:
            deadline = time.time() + timeout
            while time.time() < deadline:
                engine.tick()
                with contextlib.closing(self.store.connect()) as db:
                    done = db.execute('SELECT 1 FROM publications WHERE job_id=?', (job,)).fetchone()
                if done and not engine.active and not engine.reviews:
                    break
                time.sleep(.05)
            else:
                current = self.store.get(job)
                self.fail('not published: %s %s' % (current['state'], {k: (m['state'], m.get('attempts'))
                                                                       for k, m in current['milestones'].items()}))
        finally:
            engine.close()
        return self.store.get(job)

    def evidence(self, job, mid):
        run_id = job['milestones'][mid]['artifact']['run_id']
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT workspace, tests FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()
        return row['workspace'], json.loads(row['tests'])


class IndependentPartsTests(Base):
    def test_three_parts_run_at_once_in_their_own_copies_then_combine_and_verify(self):
        self.turns = Turns({'stream-%d' % (i + 1): helper(m) for i, m in enumerate(MODULES)}, delay=0.1, together=3)
        contract = self.contract()
        record = contract['staffing']
        self.assertEqual((record['tier'], record['serial']), ('D3', False))
        self.assertEqual(record['parallel']['stream_count'], 3)
        self.assertEqual(record['parallel']['order'], ['stream-1', 'stream-2', 'stream-3'])
        self.assertLessEqual(record['parallel']['caps']['concurrent_workers'], parallel.WORKER_LIMIT)
        self.assertEqual({s['role'] for s in record['steps'].values()}, {'builder'})
        job = self.run_job(contract)

        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'VERIFIED'))
        self.assertEqual(self.turns.peak, 3, 'the three Builders worked at the same time')
        # Each part worked in its own copy, owned only its files, and passed its own tests and D-71 check.
        copies = set()
        for index, module in enumerate(MODULES, 1):
            workspace, tests = self.evidence(job, 'stream-%d' % index)
            copies.add(workspace)
            self.assertEqual(tests['exit_code'], 0)
            self.assertTrue(tests['existing_tests_preserved'])
            self.assertEqual(tests['ownership']['outside'], [])
            self.assertEqual(tests['ownership']['changed'], sorted(['%s.py' % module, 'test_%s.py' % module]))
            self.assertIn('Implement only your part: ' + QUOTES[index - 1], self.turns.prompts['stream-%d' % index][0])
        self.assertEqual(len(copies), 3)
        # The integration applied the parts in plan order, needed no model turn, and ran the full suite
        # and the original-tests check on the combined copy.
        self.assertEqual(self.turns.count('code'), 0)
        merged = code_streams.integration(self.store, job['id'])
        self.assertEqual(merged['state'], 'CLEAN')
        self.assertEqual([a['stream'] for a in merged['applied']], ['stream-1', 'stream-2', 'stream-3'])
        workspace, tests = self.evidence(job, 'code')
        self.assertNotIn(workspace, copies)
        self.assertEqual(tests['exit_code'], 0)
        self.assertIn('4 passed', tests['summary'])
        self.assertEqual(tests['existing_tests']['state'], 'passed')
        self.assertEqual(tests['integration']['state'], 'clean')
        # D-65 applied the verified combined change to the project.
        for module in MODULES:
            self.assertEqual((self.project / ('%s.py' % module)).read_text(encoding='utf-8'), CODE[module][0])
        # The staffing record: one Builder per part plus the one that combined them, then the review.
        calls = staff.calls(self.store, job['id'])
        work = [c for c in calls if c['kind'] == 'work']
        self.assertEqual([c['role'] for c in work], ['builder'] * 4)
        self.assertEqual(sorted(c['instance'] for c in work), [1, 2, 3, 4])
        combine = next(c for c in work if c['milestone_id'] == 'code')
        self.assertIn('No model was needed', combine['why'])
        # The work card: each part's Builder is its own staff row, with its step.
        detail = office.detail(self.store, job['id'])
        rows = {r['step']: r for r in detail['staff'] if r['role'] == 'builder'}
        self.assertEqual(rows['stream-2']['step_label'], 'Part 2 of 3: Add a clamp helper in num_tools.py with its test')
        self.assertEqual(rows['code']['step_label'], 'Combining the parts')
        self.assertTrue(rows['stream-1']['doing'].startswith('Finished part 1 of 3'))
        self.assertEqual([s['id'] for s in detail['steps']], ['stream-1', 'stream-2', 'stream-3', 'code'])
        team = [t for t in office.items(self.store)['items'][0]['team'] if t['role'] == 'builder']
        self.assertEqual(len(team), 4)
        self.assertTrue(all(t['step_label'] for t in team))
        # The parts' leases were released and their streams closed once combined.
        self.assertEqual(parallel.leases(self.store, mission_id=job['id'], state='ACTIVE'), [])
        self.assertEqual({s['state'] for s in parallel.streams(self.store, mission_id=job['id'])}, {'DONE'})


class ConflictTests(Base):
    def test_a_part_that_no_longer_fits_is_done_by_a_builder_on_top_of_the_combined_code(self):
        project = self.project

        def second(workspace):
            (workspace / 'calc.py').write_text('def add(a, b):\n    return a + b\n\n\ndef twice(x):\n    return 2 * x\n',
                                               encoding='utf-8')
            (workspace / 'test_twice.py').write_text('from calc import twice\n\n\ndef test_twice():\n'
                                                     '    assert twice(2) == 4\n', encoding='utf-8')
            # Meanwhile the project's own calc.py changes (Nick edits it): part 2's copy is now stale.
            (project / 'calc.py').write_text('def add(a, b):\n    """Add two numbers."""\n    return a + b\n',
                                             encoding='utf-8')

        def sequential(workspace):
            text = (workspace / 'calc.py').read_text(encoding='utf-8')
            (workspace / 'calc.py').write_text(text + '\n\ndef twice(x):\n    return 2 * x\n', encoding='utf-8')
            (workspace / 'test_twice.py').write_text('from calc import twice\n\n\ndef test_twice():\n'
                                                     '    assert twice(2) == 4\n', encoding='utf-8')

        request = 'Add two helpers: a slugify helper in text_tools.py, and a twice helper in calc.py.'
        parts = {'independent': True, 'parts': [
            {'objective': 'slugify', 'source_quote': 'a slugify helper in text_tools.py',
             'write_paths': ['text_tools.py', 'test_text_tools.py']},
            {'objective': 'twice', 'source_quote': 'a twice helper in calc.py',
             'write_paths': ['calc.py', 'test_twice.py']}]}
        self.turns = Turns({'stream-1': helper('text_tools'), 'stream-2': second, 'code': sequential}, delay=0.1)
        contract = self.contract(parts, request)
        self.assertEqual(contract['staffing']['tier'], 'D3')
        job = self.run_job(contract)

        merged = code_streams.integration(self.store, job['id'])
        self.assertEqual(merged['state'], 'CONFLICT')
        self.assertEqual([(c['stream'], c['kind']) for c in merged['conflicts']], [('stream-2', 'project-changed')])
        self.assertEqual([a['stream'] for a in merged['applied']], ['stream-1'])
        # Fallback: one Builder did the part that did not fit, on top of the combined code, told why.
        self.assertEqual(self.turns.count('code'), 1)
        self.assertIn('could not be combined automatically', self.turns.prompts['code'][0])
        self.assertIn('a twice helper in calc.py', self.turns.prompts['code'][0])
        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'VERIFIED'))
        _, tests = self.evidence(job, 'code')
        self.assertEqual(tests['integration']['state'], 'conflict')
        self.assertEqual(tests['exit_code'], 0)
        final = (self.project / 'calc.py').read_text(encoding='utf-8')
        self.assertIn('Add two numbers', final, "Nick's edit is kept")
        self.assertEqual(final.count('def twice'), 1)


class FailureTests(Base):
    def test_a_failed_part_is_retried_alone_and_a_part_writing_outside_its_files_fails(self):
        def broken(workspace):
            helper('num_tools')(workspace)
            (workspace / 'num_tools.py').write_text('def clamp(x, lo, hi):\n    return x\n', encoding='utf-8')

        def strays(workspace):
            helper('list_tools')(workspace)
            (workspace / 'notes.txt').write_text('not mine', encoding='utf-8')

        self.turns = Turns({'stream-1': helper('text_tools'),
                            ('stream-2', 1): broken, 'stream-2': helper('num_tools'),
                            ('stream-3', 1): strays, 'stream-3': helper('list_tools')}, delay=0.1)
        job = self.run_job(self.contract())
        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'VERIFIED'))
        self.assertEqual({mid: self.turns.count(mid) for mid in ('stream-1', 'stream-2', 'stream-3', 'code')},
                         {'stream-1': 1, 'stream-2': 2, 'stream-3': 2, 'code': 0},
                         'only the failed parts ran again; nothing else was repeated')
        self.assertIn('What failed on the last try', self.turns.prompts['stream-2'][1])
        self.assertIn('This part changed a file it does not own: notes.txt', self.turns.prompts['stream-3'][1])
        with contextlib.closing(self.store.connect()) as db:
            first = db.execute("SELECT id FROM runs WHERE job_id=? AND milestone_id='stream-3' ORDER BY rowid LIMIT 1",
                               (job['id'],)).fetchone()['id']
        check = repository_check(self.store, first)
        self.assertEqual((check['verdict'], check['failure']), ('FAILED', 'ownership'))
        self.assertFalse((self.project / 'notes.txt').exists())
        copy, _tests = self.evidence(job, 'stream-3')
        self.assertFalse((Path(copy) / 'notes.txt').exists(), "Kel put the stray file back before the retry")


class RestartTests(Base):
    def test_a_crash_mid_part_resumes_without_repeating_its_turn_or_tests(self):
        self.turns = Turns({'stream-1': helper('text_tools')}, delay=0)
        job = self.store.create(self.contract(), budget=24)
        run = self.store.claim(job, 'stream-1', provider='claude-code')
        FakeConnection.crash_after = 'command/exec'
        with self.assertRaises(Crash):
            CodingAdapter(self.store).execute('Context.', run_id=run['id'], session_id=None, cancel=None)
        with mock.patch.object(coding, 'host_alive', return_value=True):
            result = CodingAdapter(self.store).execute('Context.', run_id=run['id'], session_id=None, cancel=None)
        self.assertTrue(result['code_verified'], result['text'][-1500:])
        self.assertEqual(self.turns.count('stream-1'), 1, 'no second model turn')
        self.assertEqual([k for k, _ in FakeConnection.executed].count('command/exec'), 1)
        with contextlib.closing(self.store.connect()) as db:
            copies = db.execute("SELECT COUNT(*) FROM code_stream_workspaces WHERE job_id=? AND milestone_id='stream-1'",
                                (job,)).fetchone()[0]
        self.assertEqual(copies, 1)
        self.assertEqual(len(parallel.streams(self.store, mission_id=job)), 1, 'one copy for the part, never two')

    def test_a_copy_made_before_a_crash_is_rebuilt_once(self):
        job = self.store.create(self.contract(), budget=24)
        original = parallel.open_stream

        def dies(store, **kwargs):
            def record(db, opened):
                raise Crash('after the snapshot, before the row')
            return original(store, **dict(kwargs, record=record))
        with mock.patch.object(parallel, 'open_stream', dies), self.assertRaises(Crash):
            code_streams.stream_workspace(self.store, self.store.get(job), 'stream-1')
        leftover = self.store.root / 'missions' / job / 'streams' / 'stream-1'
        self.assertTrue(leftover.exists(), 'the copy exists without its row')
        self.assertIsNone(code_streams.workspace_row(self.store, job, 'stream-1'))
        row = code_streams.stream_workspace(self.store, self.store.get(job), 'stream-1')
        self.assertEqual(Path(row['path']).resolve(), leftover.resolve())
        self.assertEqual(len(parallel.streams(self.store, mission_id=job)), 1)

    def test_a_crash_mid_merge_rebuilds_the_combined_copy_and_applies_each_part_once(self):
        self.turns = Turns({'stream-%d' % (i + 1): helper(m) for i, m in enumerate(MODULES)}, delay=0.05)
        original = code_streams._apply_change
        state = {'crashed': False}

        def once(source, target, changed, after, mid):
            original(source, target, changed, after, mid)
            if mid == 'stream-2' and not state['crashed']:
                state['crashed'] = True
                raise Crash('the engine died mid-merge')
        with mock.patch.object(code_streams, '_apply_change', once):
            job = self.run_job(self.contract())
        self.assertTrue(state['crashed'])
        self.assertEqual((job['state'], job['verdict']), ('CLOSED', 'VERIFIED'))
        merged = code_streams.integration(self.store, job['id'])
        self.assertEqual([a['stream'] for a in merged['applied']], ['stream-1', 'stream-2', 'stream-3'])
        self.assertFalse((self.store.root / 'repositories' / (job['id'] + '.merging')).exists())
        for module in MODULES:
            self.assertEqual((self.project / ('%s.py' % module)).read_text(encoding='utf-8'), CODE[module][0],
                             'each part applied exactly once')
        self.assertEqual({mid: self.turns.count(mid) for mid in ('stream-1', 'stream-2', 'stream-3')},
                         {'stream-1': 1, 'stream-2': 1, 'stream-3': 1}, 'no part was built again')
        self.assertEqual(job['milestones']['code']['attempts'], 2)


class CapTests(Base):
    def test_at_most_three_parts_and_three_live_workers(self):
        four = proposal(3)
        four['parts'].append({'objective': 'x', 'source_quote': 'helpers', 'write_paths': ['x.py']})
        with self.assertRaises(PolicyError):
            code_streams.validate_parts(REQUEST, four, PYTEST)
        contract = self.contract()
        self.assertLessEqual(contract['staffing']['parallel']['stream_count'], parallel.STREAM_LIMIT)
        caps = contract['staffing']['parallel']['caps']
        self.assertEqual((caps['streams_max'], caps['workers_max']), (3, 6))
        job = self.store.create(contract, budget=24)
        other = self.store.create(compile_coding('Tidy calc.py', self.project, PYTEST), budget=8)
        for mid in ('stream-1', 'stream-2'):
            self.store.claim(job, mid, provider='claude-code')
        with self.assertRaisesRegex(PolicyError, 'concurrency limit'):
            self.store.claim(other, 'code', provider='claude-code')  # other work keeps the cap of two
        self.store.claim(job, 'stream-3', provider='claude-code')  # a D3 part may be the third
        with self.assertRaisesRegex(PolicyError, 'concurrency limit'):
            self.store.claim(other, 'code', provider='claude-code')


class SequentialTests(Base):
    def test_a_sequential_plan_stays_one_step(self):
        ordered = 'Add a slugify helper in text_tools.py, then use it in a clamp helper in num_tools.py.'
        self.assertFalse(code_streams.worth_planning(ordered))
        with self.assertRaisesRegex(PolicyError, 'orders its parts'):
            code_streams.validate_parts(ordered, proposal(2, ('a slugify helper in text_tools.py',
                                                              'a clamp helper in num_tools.py')), PYTEST)
        self.assertFalse(code_streams.worth_planning('Fix the rounding bug in calc.py'))
        # The planner itself said the parts depend on each other.
        with self.assertRaises(PolicyError):
            code_streams.validate_parts(REQUEST, dict(proposal(), independent=False), PYTEST)
        # Two parts writing one file, or one changing shared test setup, are not independent.
        shared = proposal(2)
        shared['parts'][1]['write_paths'] = ['text_tools.py']
        with self.assertRaisesRegex(PolicyError, 'disjoint'):
            code_streams.validate_parts(REQUEST, shared, PYTEST)
        setup = proposal(2)
        setup['parts'][1]['write_paths'].append('conftest.py')
        with self.assertRaisesRegex(PolicyError, 'shared test setup'):
            code_streams.validate_parts(REQUEST, setup, PYTEST)
        invented = proposal(2)
        invented['parts'][0]['source_quote'] = 'words the request never said'
        with self.assertRaises(PolicyError):
            code_streams.validate_parts(REQUEST, invented, PYTEST)

    def test_parts_that_do_not_qualify_run_as_one_builder_step(self):
        from kel.service import Service
        contract = self.contract(request=REQUEST.replace('helpers', 'database migration helpers'))
        self.assertIsNone(contract['staffing']['parallel'], 'R6: migrations run one step at a time')
        contract.pop('staffing')
        Service._staff_contract(SimpleNamespace(store=self.store), contract, contract['request'])
        self.assertEqual([m['id'] for m in contract['milestones']], ['code'])
        self.assertNotIn('code_streams', contract)
        self.assertNotIn('final_milestone', contract)
        self.assertEqual(contract['code_plan']['ran_as'], 'one step')
        self.assertIn('R6', contract['code_plan']['why'])
        self.assertTrue(contract['staffing']['serial'])
        # With the workforce off the parts never run unstaffed.
        os.environ['KEL_WORKFORCE'] = 'off'
        off = self.contract()
        off.pop('staffing')
        Service._staff_contract(SimpleNamespace(store=self.store), off, off['request'])
        self.assertEqual([m['id'] for m in off['milestones']], ['code'])

    def test_the_planner_decides_only_through_the_deterministic_check(self):
        from kel.service import Service

        class Commander:
            def __init__(self, value):
                self.value, self.asked = value, []

            def plan_code(self, request, files=(), model=None, on_result=None):
                self.asked.append((request, list(files)))
                return self.value
        fake = SimpleNamespace(commander=Commander({'independent': False, 'parts': []}),
                               _kel_model=lambda *a, **k: None, _kel_usage=lambda *a, **k: None)
        single = compile_coding(REQUEST, self.project, PYTEST)
        out = Service._plan_code_parts(fake, 's', 'c', REQUEST, dict(single))
        self.assertEqual([m['id'] for m in out['milestones']], ['code'])
        self.assertEqual(out['code_plan']['ran_as'], 'one step')
        self.assertIn('calc.py', fake.commander.asked[0][1], 'the planner sees the project files')
        fake.commander = Commander(proposal())
        out = Service._plan_code_parts(fake, 's', 'c', REQUEST, dict(single))
        self.assertEqual([m['id'] for m in out['milestones']], ['stream-1', 'stream-2', 'stream-3', 'code'])
        self.assertEqual(out['final_milestone'], 'code')
        # A one-change request never asks the planner.
        fake.commander = Commander(proposal())
        Service._plan_code_parts(fake, 's', 'c', 'Fix the rounding bug in calc.py', dict(single))
        self.assertEqual(fake.commander.asked, [])


class PlannerTests(unittest.TestCase):
    def test_the_plan_is_read_even_after_a_sentence_from_the_runtime(self):
        from kel.commander import Commander
        answer = ("I'll inspect the project files first, then return the plan.\n" + json.dumps(proposal()))

        class Model:
            provider, model = 'codex', 'gpt-6-luna'

            def execute(self, prompt):
                self.prompt = prompt
                return {'outcome': 'SUCCESS', 'text': answer, 'model_used': 'gpt-6-luna'}
        model = Model()
        value = Commander(model).plan_code(REQUEST, files=['calc.py'])
        self.assertTrue(value['independent'])
        self.assertEqual(len(code_streams.validate_parts(REQUEST, value, PYTEST)), 3)
        self.assertEqual(value['planner'], {'provider': 'codex', 'model': 'gpt-6-luna'})
        self.assertIn('calc.py', model.prompt)
        answer = 'Not a plan at all.'
        self.assertEqual(Commander(model).plan_code(REQUEST)['independent'], False)


if __name__ == '__main__':
    unittest.main()
