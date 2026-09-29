"""D-66/D-67: the workforce on the everyday path.

Every real-work job carries one recorded staffing decision (frozen in its contract), each step runs
under its role with the model call recorded, review and the Oracle stay independent, and the live
state is exposed read-only. No real model provider is called: every runtime here is a fake.
"""
import contextlib
import json
import os
import tempfile
import time
import unittest

from kel import staff, staffing
from kel.authorize import role_for
from kel.core import Store
from kel.engine import Engine
from kel.native import FixtureAdapter
from kel.team import Team


def writing(request, parts=0):
    """A writing contract like the planner's: one step, or N independent parts plus a combine."""
    checks = [{'kind': 'min_chars', 'value': 5},
              {'kind': 'manual_review', 'rubric': 'Satisfies the request.'}]
    if not parts:
        return {'request': request, 'compiler': 'test',
                'milestones': [{'id': 'document', 'objective': request, 'filename': 'result.md',
                                'depends_on': [], 'checks': list(checks)}]}
    milestones = [{'id': 'p%d' % i, 'objective': 'Part %d of %s' % (i, request),
                   'filename': 'p%d.md' % i, 'depends_on': [], 'checks': list(checks)}
                  for i in range(1, parts + 1)]
    milestones.append({'id': 'combined', 'objective': 'Combine', 'filename': 'combined.md',
                       'depends_on': [m['id'] for m in milestones], 'checks': list(checks)})
    return {'request': request, 'compiler': 'test', 'milestones': milestones,
            'final_milestone': 'combined'}


def research(request, parts=0):
    contract = writing(request, parts)
    contract['kind'] = 'research'
    contract['required_capabilities'] = ['web_research']
    return contract


def coding(request):
    return {'request': request, 'kind': 'coding', 'root': 'C:/nowhere', 'test_command': ['x'],
            'greenfield': False,
            'milestones': [{'id': 'code', 'objective': request, 'filename': 'changes.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}]}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        staff.ensure_schema(self.store)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)


class StaffingDecisionTests(Base):
    def test_small_writing_is_kel_alone(self):
        record = staff.plan_job(self.store, writing('Write a haiku about autumn'))
        self.assertEqual(record['tier'], 'D0')
        self.assertEqual(record['steps']['document']['role'], 'kel')
        self.assertEqual(record['review']['mode'], 'check')
        self.assertTrue(record['serial'])
        self.assertFalse(record['oracle']['required'])
        self.assertTrue(any('score' in reason for reason in record['reasons']))

    def test_a_small_code_fix_gets_one_builder(self):
        record = staff.plan_job(self.store, coding('Fix the typo in the README heading'))
        self.assertEqual(record['tier'], 'D1')
        self.assertEqual(record['steps']['code']['role'], 'builder')
        self.assertEqual(record['kind'], 'code')

    def test_code_is_never_below_one_builder(self):
        record = staff.plan_job(self.store, coding('Fix it'), tier_max='D0')
        self.assertEqual(record['tier'], 'D1')
        self.assertIn('code is always written by a Builder (at least one specialist)', record['reasons'])

    def test_security_work_is_a_pod_with_the_security_lens_and_sentinel(self):
        record = staff.plan_job(self.store, coding('Fix the password check on the login page'))
        self.assertEqual(record['tier'], 'D2')
        self.assertIn('R3', record['rules'])
        self.assertEqual(record['review']['mode'], 'pod')
        self.assertIn('security', record['review']['lenses'])
        self.assertIn('functional-testing', record['review']['lenses'])
        # D-85: Verifier and Sentinel; the Oracle is for large or hard-to-undo work, not every security fix.
        self.assertEqual(record['review']['verifier']['when'], 'always')
        self.assertTrue(record['sentinel']['required'])
        self.assertFalse(record['oracle']['required'])
        hard = staff.plan_job(self.store, coding('Fix the password check on the login page and deploy it'))
        self.assertTrue(hard['oracle']['required'])

    def test_independent_research_parts_run_as_parallel_streams(self):
        record = staff.plan_job(self.store, research('Research three CRM options and compare them', 3))
        self.assertEqual(record['tier'], 'D3')
        self.assertFalse(record['serial'])
        self.assertEqual(record['parallel']['stream_count'], 3)
        self.assertEqual(sorted(s['write_paths'][0] for s in record['parallel']['streams']),
                         ['p1.md', 'p2.md', 'p3.md'])
        self.assertIn('combined', record['parallel']['merge_strategy'])
        self.assertEqual({record['steps']['p%d' % i]['role'] for i in (1, 2, 3)}, {'discovery'})
        self.assertEqual(record['steps']['combined']['role'], 'kel')

    def test_small_multi_part_writing_is_not_parallelised(self):
        record = staff.plan_job(self.store, writing('Write two short notes', 2))
        self.assertIn(record['tier'], ('D0', 'D1'))
        self.assertIsNone(record['parallel'])
        self.assertTrue(record['serial'])

    def test_sequential_parts_never_run_in_parallel(self):
        contract = writing('Research the market, then write a plan based on it', 2)
        contract['milestones'][1]['depends_on'] = ['p1']
        contract['kind'] = 'research'
        record = staff.plan_job(self.store, contract)
        self.assertIsNone(record['parallel'])
        self.assertTrue(record['serial'])

    def test_code_is_never_parallel_streams(self):
        record = staff.plan_job(self.store, coding(
            'Refactor the entire architecture across every module and deploy it to production'))
        self.assertIsNone(record['parallel'])
        self.assertTrue(record['serial'])
        self.assertLessEqual(staff.TIER_RANK[record['tier']], 4)

    def test_positive_scope_signals_are_flags(self):
        self.assertIn('security_boundary', staff.flags_for('rotate the API key'))
        self.assertIn('data_migration', staff.flags_for('write a schema migration'))
        self.assertIn('irreversible', staff.flags_for('send the invoice to the client'))
        self.assertEqual(staff.flags_for('write a garden plan'), [])

    def test_off_switch(self):
        for off in ('0', 'false', 'off', 'no'):
            self.assertFalse(staff.enabled({'KEL_WORKFORCE': off}))
        self.assertTrue(staff.enabled({}))


class HistoryTests(Base):
    def test_everyday_decisions_feed_the_one_step_history(self):
        features, _flags = staff.features_for(writing('Write a haiku about autumn'))
        for _ in range(3):
            contract = writing('Write a haiku about autumn')
            contract['staffing'] = staff.plan_job(self.store, contract)
            job = self.store.create(contract)
            staff.record_decision(self.store, job, contract['staffing'])
            staff.record_decision(self.store, job, contract['staffing'])  # idempotent
            with self.store.transaction() as db:
                record = self.store._get(db, job)
                record['state'] = 'CLOSED'
                self.store._save(db, record, 'test.closed')
        advice = staffing.outcome_advice(self.store, features)
        self.assertEqual(advice['history']['settled'], 3)
        with contextlib.closing(self.store.connect()) as db:
            count = db.execute("SELECT COUNT(*) FROM team_events WHERE kind='staffing.decided'"
                               ' AND assignment_id IS NULL').fetchone()[0]
        self.assertEqual(count, 3)


class EngineStaffingTests(Base):
    def run_engine(self, adapters, job, until, timeout=20, reviewer=None):
        engine = Engine(self.store, adapters, reviewer=reviewer)
        peak = 0
        try:
            deadline = time.time() + timeout
            while time.time() < deadline:
                engine.tick()
                current = self.store.get(job)
                peak = max(peak, sum(1 for m in current['milestones'].values()
                                     if m['state'] == 'RUNNING'))
                if until(current):
                    return current, peak
                time.sleep(.02)
            raise TimeoutError(self.store.get(job)['state'])
        finally:
            engine.close()

    def staffed(self, contract, tier_max=None):
        contract['staffing'] = staff.plan_job(self.store, contract, tier_max=tier_max)
        job = self.store.create(contract)
        staff.record_decision(self.store, job, contract['staffing'])
        return job

    def test_each_step_records_its_role_and_the_run_it_rode(self):
        job = self.staffed(coding_free_writing('Write a haiku about autumn leaves falling'))
        final, _peak = self.run_engine({'fixture': FixtureAdapter(delay=0.05)}, job,
                                       lambda j: j['milestones']['document']['state'] != 'RUNNING'
                                       and j['milestones']['document']['attempts'] >= 1)
        calls = staff.calls(self.store, job)
        self.assertEqual(len(calls), 1)
        call = calls[0]
        with contextlib.closing(self.store.connect()) as db:
            run = db.execute('SELECT id FROM runs WHERE job_id=?', (job,)).fetchone()
        self.assertEqual(call['id'], run['id'], 'the binding rides the run (same id, one transaction)')
        self.assertEqual(call['role'], 'kel')
        self.assertEqual(call['kind'], 'work')
        self.assertEqual(call['ran']['adapter'], 'fixture')
        self.assertIn(call['state'], ('done', 'running'))

    def test_serial_staffing_runs_one_step_at_a_time(self):
        job = self.staffed(writing('Write two short notes', 2))
        self.assertTrue(self.store.get(job)['contract']['staffing']['serial'])
        final, peak = self.run_engine({'fixture': FixtureAdapter(delay=0.2)}, job,
                                      lambda j: all(j['milestones'][m]['attempts'] >= 1
                                                    and j['milestones'][m]['state'] != 'RUNNING'
                                                    for m in ('p1', 'p2')))
        self.assertEqual(peak, 1, 'below D3 a staffed job never runs two steps at once')

    def test_parallel_staffing_runs_independent_parts_together(self):
        job = self.staffed(research('Research three CRM options and compare them', 3))
        record = self.store.get(job)['contract']['staffing']
        self.assertFalse(record['serial'])
        adapters = {'research': FixtureAdapter(delay=0.3)}
        adapters['research'].capabilities = {'text', 'web_research'}
        final, peak = self.run_engine(adapters, job,
                                      lambda j: sum(1 for m in ('p1', 'p2', 'p3')
                                                    if j['milestones'][m]['attempts'] >= 1) >= 2)
        self.assertEqual(peak, 3, 'independent parts overlap (a D3 job runs up to three parts at once)')
        roles = {call['role'] for call in staff.calls(self.store, job)}
        self.assertEqual(roles, {'discovery'})
        self.assertGreaterEqual(max(call['instance'] for call in staff.calls(self.store, job)), 2,
                                'the same role runs as several instances')

    def test_unstaffed_jobs_keep_the_legacy_role(self):
        job = self.store.create(writing('Write a haiku'))
        self.run_engine({'fixture': FixtureAdapter()}, job,
                        lambda j: j['milestones']['document']['attempts'] >= 1)
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT template_id FROM team_assignments WHERE job_id=?', (job,)).fetchone()
        self.assertEqual(row['template_id'], 'documentation-specialist')
        self.assertEqual(staff.calls(self.store, job), [])

    def test_a_staffed_writer_runs_under_its_own_archetype(self):
        # D-88: writing that was the Builder's is the Writer's (supersedes D-69.4).
        job = self.staffed(writing('Draft a detailed onboarding guide for new engineers covering '
                                   'accounts, tooling, the review process, deployment and on-call '
                                   'expectations, with a checklist for the first two weeks and '
                                   'pointers to every internal system they will touch'))
        record = self.store.get(job)['contract']['staffing']
        self.assertIn(record['steps']['document']['role'], ('writer', 'designer', 'utility'))
        self.run_engine({'fixture': FixtureAdapter()}, job,
                        lambda j: j['milestones']['document']['attempts'] >= 1)
        info = role_for(self.store, job, 'document')
        self.assertEqual(info['template_id'], staff.EXECUTOR_TEMPLATES[record['steps']['document']['role']])

    def test_a_review_assignment_never_becomes_the_executor_policy(self):
        job = self.staffed(coding_free_writing('Write a long detailed plan for a product launch '
                                               'with risks and dependencies and owners'))
        self.run_engine({'fixture': FixtureAdapter()}, job,
                        lambda j: j['milestones']['document']['attempts'] >= 1)
        from kel.assignment import ensure_archetypes
        ensure_archetypes(self.store)
        before = role_for(self.store, job, 'document')
        Team(self.store).create_assignment(job, 'document', 'verifier')
        self.assertEqual(role_for(self.store, job, 'document'), before)


def coding_free_writing(request):
    return writing(request)


class ServiceIntakeTests(unittest.TestCase):
    """Every D-53 hand-off gets a recorded staffing decision; the off-switch restores the old path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for name in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL', 'KEL_WORKFORCE'):
            os.environ.pop(name, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        self.services = []

    def tearDown(self):
        for service in self.services:
            with contextlib.suppress(Exception):
                service.shutdown()
        self.tmp.cleanup()

    def start(self):
        from kel.service import Service
        service = Service(self.tmp.name)
        self.services.append(service)
        service.engine.adapters = {}
        service.stop.set()  # no supervision: the job stays where intake put it
        return service

    def hand_off(self, service, text):
        cid = service.context.conversation('default')
        sid = service.submit({'text': text, 'conversation': cid})
        deadline = time.time() + 20
        while time.time() < deadline:
            with contextlib.closing(service.store.connect()) as db:
                row = db.execute('SELECT state, job_id FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['job_id']:
                return service.store.get(row['job_id'])
            if row and row['state'] in ('FAILED', 'SETTLED'):
                self.fail('no job was created: %s' % row['state'])
            time.sleep(.02)
        self.fail('intake timed out')

    def test_every_handoff_carries_a_recorded_decision(self):
        service = self.start()
        job = self.hand_off(service, 'Write a short plan for the weekend')
        record = job['contract']['staffing']
        self.assertEqual(record['schema'], 1)
        self.assertIn(record['tier'], staffing.TIER_ORDER)
        self.assertEqual(set(record['steps']), set(job['milestones']))
        with contextlib.closing(service.store.connect()) as db:
            event = db.execute("SELECT detail FROM team_events WHERE kind='staffing.decided' AND job_id=?",
                               (job['id'],)).fetchone()
        self.assertEqual(json.loads(event['detail'])['tier'], record['tier'])

    def test_the_off_switch_keeps_todays_path(self):
        os.environ['KEL_WORKFORCE'] = '0'
        service = self.start()
        job = self.hand_off(service, 'Write a short plan for the weekend')
        self.assertNotIn('staffing', job['contract'])


if __name__ == '__main__':
    unittest.main()
