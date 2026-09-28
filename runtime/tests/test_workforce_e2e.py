"""D-66/D-67/D-69 end to end, one test per staffing level, plus the Oracle and a restart mid-mission.

Submit → staffed → built → independently reviewed → (Oracle) → result / D-65 auto-apply, with fake
runtimes only (no provider is ever called). The D0/D1/D2 paths go through the real Service intake;
D3 goes through the engine with a planner-shaped contract (a real planner is a model call).
"""
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel import oracle, role_models, staff
from kel.auto_apply import decision as apply_decision
from kel.coding import CodingAdapter, compile_coding
from kel.commander import Commander
from kel.core import Store
from kel.engine import Engine

sys.path.insert(0, str(Path(__file__).parent))
from test_role_models_live import FakeCoder, make_project  # noqa: E402


class FakeModel:
    """A text/review/Oracle model. It answers by what it is asked to do, and reports its model."""

    def __init__(self, provider, model=None, verdict='VERIFIED', findings=None, challenges=None,
                 reports=True, sentinel=None, attacks=None):
        self.provider, self.model = provider, model
        self.verdict, self.findings = verdict, findings
        self.challenges = challenges or []
        self.reports = reports
        self.sentinel = sentinel if sentinel is not None else {'verdict': 'clear', 'findings': []}
        self.attacks = attacks or []
        self.prompts = []

    def execute(self, prompt, run_id=None, **kwargs):
        self.prompts.append(prompt)
        out = {'outcome': 'SUCCESS'}
        if self.reports and self.model:
            out['model_used'] = self.model
        if prompt.startswith('Plan a bounded Markdown document job'):
            return {'outcome': 'FAILED', 'error': 'the fake planner does not plan'}
        if prompt.startswith('You are Sentinel'):
            out['text'] = json.dumps(dict(self.sentinel, coverage='Read the diff for secrets and access.'))
            return out
        if prompt.startswith('You are the Red Team'):
            out['text'] = json.dumps({'attacks': self.attacks, 'coverage': 'Attacked the inputs and the recovery path.'})
            return out
        if 'You are the Oracle' in prompt:
            out['text'] = json.dumps({'challenges': self.challenges,
                                      'coverage': 'Read the diff, the claims and the checks.'})
            return out
        if prompt.startswith('Independently review'):
            findings = self.findings if self.findings is not None else ['Meets the request.']
            out['text'] = json.dumps({'verdict': self.verdict, 'findings': findings})
            return out
        out['text'] = 'A finished piece of writing that answers the request in full.'
        return out


class FakeText:
    """An engine text worker (Kel's own model or a specialist) that reports the model it ran."""
    capabilities = {'text'}

    def __init__(self, model):
        self.model = model
        self.calls = 0

    def execute(self, prompt, run_id=None, session_id=None, cancel=None):
        self.calls += 1
        time.sleep(.15)
        return {'outcome': 'SUCCESS', 'model_used': self.model,
                'text': 'A finished piece of writing that answers the request in full.'}


class StaffStub:
    """What the service gives the Commander and the Oracle: the runtimes present and fake models."""

    def __init__(self, adapters, models):
        self.adapters, self.models = set(adapters), models
        self.built = []

    def staff_adapters(self):
        return set(self.adapters)

    def staff_model(self, binding, timeout=100, turn=False):
        name = (binding or {}).get('adapter')
        if name not in self.adapters:
            return None
        self.built.append(binding)
        model = self.models.get(name)
        if model is None:
            return None
        clone = FakeModel(name, binding.get('model_arg'), model.verdict, model.findings, model.challenges,
                          model.reports, model.sentinel, model.attacks)
        clone.prompts = model.prompts
        return clone


class ServiceBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for name in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL', 'KEL_WORKFORCE'):
            os.environ.pop(name, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none')
        from kel.service import Service
        self.service = Service(Path(self.tmp.name) / 'data')
        self.store = self.service.store
        self.reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        with contextlib.suppress(Exception):
            self.tmp.cleanup()

    def wire(self, adapters, reviews=None):
        """Fake runtimes into the real service: engine adapters, the reviewer and the staff models."""
        reviews = reviews or self.reviews
        self.service.engine.adapters = adapters
        commander = Commander(FakeModel('claude'))
        stub = StaffStub({name for name in adapters if name in ('codex', 'claude')}, reviews)
        commander.staff = stub
        self.service.commander = commander
        self.service.engine.reviewer = commander
        self.service.staff_model = stub.staff_model
        self.stub = stub

    def submit(self, text, cid):
        sid = self.service.submit({'text': text, 'conversation': cid})
        self.last_sid = sid
        deadline = time.time() + 30
        while time.time() < deadline:
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute('SELECT state, job_id FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['job_id']:
                return row['job_id']
            if row and row['state'] in ('FAILED', 'SETTLED'):
                self.fail('no job: %s' % row['state'])
            time.sleep(.05)
        self.fail('intake timed out')

    def wait_published(self, job, timeout=40):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute('SELECT text FROM publications WHERE job_id=?', (job,)).fetchone()
            if row:
                return row['text']
            time.sleep(.05)
        current = self.store.get(job)
        self.fail('not published: %s %s' % (current['state'], {k: (m['state'], m.get('error'))
                                                               for k, m in current['milestones'].items()}))

    def roles(self, job):
        return [(call['role'], call['kind'], call['state']) for call in staff.calls(self.store, job)]


class ServiceLevelTests(ServiceBase):
    def test_d0_kel_alone_writes_and_a_verifier_checks(self):
        self.wire({'codex': FakeText('gpt-6-luna'), 'claude': FakeText('claude-sonnet-4-6')})
        cid = self.service.context.conversation('default')
        job = self.submit('Write a haiku about autumn', cid)
        record = self.store.get(job)['contract']['staffing']
        self.assertEqual((record['tier'], record['steps']['document']['role']), ('D0', 'kel'))
        text = self.wait_published(job)
        self.assertIn('passed its checks', text)
        calls = staff.calls(self.store, job)
        work = next(c for c in calls if c['kind'] == 'work')
        check = next(c for c in calls if c['kind'] == 'check')
        self.assertEqual((work['role'], work['ran']['adapter'], work['ran']['model']), ('kel', 'codex', 'gpt-6-luna'))
        self.assertEqual(work['asked']['model'], 'gpt-6-luna')
        # Kel's own model is openai, so the Verifier moves to another family (D-69 independence).
        self.assertEqual((check['role'], check['ran']['adapter'], check['ran']['independence']),
                         ('verifier', 'claude', 'different'))
        self.assertEqual(self.store.get(job)['verdict'], 'VERIFIED')

    def code_setup(self, text):
        project = make_project(self.tmp.name)
        CodingAdapter(self.store)
        created = self.service.projects.create('proj', root=str(project), test_command=['python', '-c', 'pass'])
        cid = self.service.context.conversation(created['id'])
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        self.wire({'claude-code': claude, 'codex-code': FakeCoder(self.store), 'codex': FakeText('gpt-6-astra'),
                   'claude': FakeText('claude-opus-5-5')})
        return project, cid, self.submit(text, cid), claude

    def test_d1_one_builder_then_review_then_auto_apply(self):
        project, _cid, job, claude = self.code_setup('Fix the typo in app.txt')
        record = self.store.get(job)['contract']['staffing']
        self.assertEqual((record['tier'], record['review']['mode']), ('D1', 'check'))
        text = self.wait_published(job)
        self.assertEqual((project / 'app.txt').read_text(), 'new', 'D-65 applied the verified change')
        self.assertIn('Applied to', text)
        self.assertEqual(self.roles(job), [('builder', 'work', 'done'), ('verifier', 'check', 'done')])
        builder = staff.calls(self.store, job)[0]
        self.assertEqual((builder['ran']['model'], builder['ran']['model_confirmed']), ('claude-opus-5-5', True))
        check = staff.calls(self.store, job)[1]
        self.assertEqual((check['ran']['adapter'], check['ran']['model']), ('codex', 'gpt-6-astra'))
        self.assertEqual(oracle.status(self.store, self.store.get(job))['state'], 'not_needed')

    def test_d2_pod_with_lens_review_and_the_oracle_before_apply(self):
        project, cid, job, _claude = self.code_setup('Fix the password check in app.txt')
        record = self.store.get(job)['contract']['staffing']
        self.assertEqual((record['tier'], record['review']['mode']), ('D2', 'pod'))
        self.assertIn('security', record['review']['lenses'])
        self.wait_published(job)
        self.assertEqual((project / 'app.txt').read_text(), 'new')
        # A code change touching security gets Sentinel (its own read-only review) before the Oracle.
        self.assertEqual([r for r, k, s in self.roles(job)], ['builder', 'verifier', 'sentinel', 'oracle'])
        self.assertEqual(oracle.status(self.store, self.store.get(job), 'sentinel')['state'], 'done')
        status = oracle.status(self.store, self.store.get(job))
        self.assertEqual((status['state'], status['independence']), ('done', 'different'))
        oracle_call = next(c for c in staff.calls(self.store, job) if c['kind'] == 'oracle')
        self.assertEqual((oracle_call['ran']['adapter'], oracle_call['ran']['model']), ('codex', 'gpt-6-astra'))
        review_prompt = self.reviews['codex'].prompts[0]
        self.assertIn('This is a pod review', review_prompt)
        oracle_prompt = next(p for p in self.reviews['codex'].prompts if 'You are the Oracle' in p)
        self.assertIn('diff', oracle_prompt)
        self.assertNotIn('Changed app.txt to the new text', oracle_prompt, "never the Builder's own report")
        work = self.service._work(cid)['work']['jobs'][0]
        self.assertFalse(work['needs_you'])

    def test_an_oracle_blocker_stops_auto_apply_and_needs_nick(self):
        self.reviews['codex'].challenges = [{'severity': 'blocker', 'summary': 'The check accepts any password.',
                                             'claim': 'repository.evidence', 'settle': 'Try a wrong password.'}]
        project, cid, job, _claude = self.code_setup('Fix the password check in app.txt')
        text = self.wait_published(job)
        self.assertEqual((project / 'app.txt').read_text(), 'old', 'nothing applied on its own')
        self.assertEqual(apply_decision(self.store, job)['decision'], 'waiting')
        self.assertIn('second opinion found a problem', text)
        work = self.service._work(cid)['work']['jobs'][0]
        self.assertTrue(work['needs_you'])
        self.assertIn('The check accepts any password', work['why'])
        self.assertEqual(work['priority'], 'now')
        card = self.service.handoff_view(cid, self.last_sid)
        self.assertEqual(card['phase'], 'needs_you')
        self.assertIn('The check accepts any password', card['why'])
        rows = oracle.findings_for(self.store, self.store.get(job), live_only=True)
        self.assertEqual([(r['lens'], r['severity']) for r in rows], [('adversarial', 'blocker')])

    def test_a_pod_blocker_sends_the_step_back_to_the_builder(self):
        codex = FakeModel('codex', findings=[{'lens': 'security', 'severity': 'blocker',
                                              'summary': 'The password is logged in plain text.'}])
        reviews = {'codex': codex, 'claude': FakeModel('claude')}
        project = make_project(self.tmp.name)
        CodingAdapter(self.store)
        created = self.service.projects.create('proj', root=str(project), test_command=['python', '-c', 'pass'])
        cid = self.service.context.conversation(created['id'])
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        self.wire({'claude-code': claude, 'codex-code': FakeCoder(self.store), 'codex': FakeText('x')}, reviews)
        job = self.submit('Fix the password check in app.txt', cid)
        deadline = time.time() + 30
        while time.time() < deadline and len(claude.calls) < 2:
            time.sleep(.05)
        self.assertGreaterEqual(len(claude.calls), 2, 'a blocker held the step and the Builder repaired it')
        from kel import assurance
        rows = assurance.findings(self.store, mission_id=job)
        self.assertTrue(any(r['lens'] == 'security' and r['severity'] == 'blocker' for r in rows))
        # The first version's review was recorded as FAILED over the blocker (never a clean pass).
        failed = [e for e in self.store.events() if e.get('aggregate_id') == job and e['type'] == 'review.recorded'
                  and json.loads(e['payload'])['detail']['verdict'] == 'FAILED']
        self.assertTrue(failed)
        self.service.stop.set()


class EngineLevelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        CodingAdapter(self.store)

    def run_engine(self, engine, job, until, timeout=40):
        peak = 0
        deadline = time.time() + timeout
        while time.time() < deadline:
            engine.tick()
            current = self.store.get(job)
            peak = max(peak, sum(1 for m in current['milestones'].values() if m['state'] == 'RUNNING'))
            if until(current):
                return current, peak
            time.sleep(.03)
        raise TimeoutError(self.store.get(job)['state'])

    def test_d3_parallel_parts_are_reviewed_and_combined_by_kel(self):
        checks = [{'kind': 'min_chars', 'value': 20}, {'kind': 'manual_review', 'rubric': 'Covers the part.'}]
        milestones = [{'id': 'p%d' % i, 'objective': 'Part %d' % i, 'filename': 'p%d.md' % i, 'depends_on': [],
                       'checks': list(checks)} for i in (1, 2, 3)]
        milestones.append({'id': 'combined', 'objective': 'Combine', 'filename': 'combined.md',
                           'depends_on': ['p1', 'p2', 'p3'], 'checks': list(checks)})
        contract = {'request': 'Write three short guides for onboarding, billing and support, then '
                               'combine them into one handbook', 'milestones': milestones,
                    'final_milestone': 'combined', 'compiler': 'commander-proposal-v1'}
        contract['staffing'] = staff.plan_job(self.store, contract)
        self.assertEqual(contract['staffing']['tier'], 'D3')
        reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}
        commander = Commander(FakeModel('claude'))
        commander.staff = StaffStub({'codex', 'claude'}, reviews)
        engine = Engine(self.store, {'claude': FakeText('claude-opus-5-5'), 'codex': FakeText('gpt-6-luna')},
                        reviewer=commander)
        job = engine.submit(contract)
        try:
            final, peak = self.run_engine(engine, job, lambda j: j['state'] == 'CLOSED')
        finally:
            engine.close()
        self.assertEqual(final['verdict'], 'VERIFIED')
        self.assertEqual(peak, 3, 'independent parts ran together (up to three at once for D3)')
        calls = staff.calls(self.store, job)
        builders = [c for c in calls if c['kind'] == 'work' and c['role'] == 'builder']
        self.assertEqual(len(builders), 3)
        self.assertEqual(sorted(c['instance'] for c in builders), [1, 2, 3])
        self.assertEqual([c['role'] for c in calls if c['milestone_id'] == 'combined' and c['kind'] == 'work'], ['kel'])
        self.assertEqual(len([c for c in calls if c['kind'] == 'check']), 4)
        self.assertTrue(all('This is a pod review' in p for p in reviews['codex'].prompts + reviews['claude'].prompts
                            if p.startswith('Independently review')))

    def test_restart_mid_mission_resumes_review_and_oracle_without_replaying_work(self):
        project = make_project(self.tmp.name)
        text = 'Fix the password check in app.txt'
        contract = compile_coding(text, project, ['python', '-c', 'pass'])
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        decided = contract['staffing']['decided_at']
        job = self.store.create(contract)
        # One process builds the change, then dies inside the Verifier's review (a real crash).
        script = '\n'.join([
            'import os, sys, time',
            'sys.path.insert(0, sys.argv[2])',
            'from kel.core import Store',
            'from kel.engine import Engine',
            'from kel.commander import Commander',
            'from test_role_models_live import FakeCoder',
            'class Dies:',
            '    provider = "codex"; model = "gpt-6-astra"',
            '    def execute(self, *a, **k): os._exit(23)',
            'class Staff:',
            '    def staff_adapters(self): return {"codex"}',
            '    def staff_model(self, binding, timeout=100, turn=False): return Dies()',
            'store = Store(sys.argv[1])',
            'c = Commander(Dies()); c.staff = Staff()',
            'e = Engine(store, {"claude-code": FakeCoder(store, reports="claude-opus-5-5")}, reviewer=c)',
            'for _ in range(400):',
            '    e.tick(); time.sleep(.05)'])
        done = subprocess.run([sys.executable, '-c', script, str(self.store.root), str(Path(__file__).parent)],
                              cwd=Path(__file__).resolve().parents[1], timeout=60, capture_output=True)
        self.assertEqual(done.returncode, 23, done.stderr)
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        check = next(c for c in staff.calls(self.store, job) if c['kind'] == 'check')
        self.assertEqual(check['state'], 'running', 'the killed review left its call open')
        # Engine B: the frozen staffing is reused, the review resumes, the Oracle runs, D-65 applies.
        reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}
        commander = Commander(FakeModel('claude'))
        commander.staff = StaffStub({'codex'}, reviews)
        engine = Engine(self.store, {'claude-code': claude}, reviewer=commander)
        try:
            with contextlib.closing(self.store.connect()) as db:
                self.assertEqual(db.execute("SELECT state FROM staff_calls WHERE kind='check'").fetchone()[0],
                                 'stopped')
            self.run_engine(engine, job, lambda j: bool(apply_decision(self.store, j['id'])))
            self.run_engine(engine, job, lambda j: (project / 'app.txt').read_text() == 'new')
        finally:
            engine.close()
        self.assertEqual(claude.calls, [], 'the built change was never rebuilt after the restart')
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 1)
        final = self.store.get(job)
        self.assertEqual(final['contract']['staffing']['decided_at'], decided)
        self.assertEqual(oracle.status(self.store, final)['state'], 'done')
        with contextlib.closing(self.store.connect()) as db:
            attempts = db.execute('SELECT attempts FROM review_runs').fetchone()[0]
        self.assertEqual(attempts, 2)
        self.assertEqual([c['state'] for c in staff.calls(self.store, job) if c['kind'] == 'check'],
                         ['stopped', 'done'])

    def test_an_interrupted_oracle_is_retried_then_recorded_as_a_gap(self):
        project = make_project(self.tmp.name)
        text = 'Fix the password check in app.txt'
        contract = compile_coding(text, project, ['python', '-c', 'pass'])
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        job = self.store.create(contract)
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}
        commander = Commander(FakeModel('claude'))
        commander.staff = StaffStub(set(), reviews)  # no model can run the second opinion here
        engine = Engine(self.store, {'claude-code': claude}, reviewer=commander)
        try:
            self.run_engine(engine, job, lambda j: bool(apply_decision(self.store, j['id'])))
        finally:
            engine.close()
        final = self.store.get(job)
        status = oracle.status(self.store, final)
        self.assertEqual(status['state'], 'could_not_run')
        self.assertEqual(apply_decision(self.store, job)['decision'], 'waiting')
        self.assertEqual((project / 'app.txt').read_text(), 'old')
        self.assertIn('could not run', oracle.attention(self.store, final)['why'])

    def test_a_large_change_applied_on_its_own_gets_the_oracle_even_below_a_pod(self):
        project = make_project(self.tmp.name)
        text = 'Fix the typo in app.txt'
        contract = compile_coding(text, project, ['python', '-c', 'pass'])
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        self.assertEqual((contract['staffing']['tier'], contract['staffing']['oracle']['required']), ('D1', False))
        job = self.store.create(contract)
        claude = FakeCoder(self.store, reports='claude-opus-5-5', files=12)
        reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}
        commander = Commander(FakeModel('claude'))
        commander.staff = StaffStub({'codex'}, reviews)
        engine = Engine(self.store, {'claude-code': claude}, reviewer=commander)
        try:
            self.run_engine(engine, job, lambda j: (project / 'app.txt').read_text() == 'new')
        finally:
            engine.close()
        status = oracle.status(self.store, self.store.get(job))
        self.assertEqual(status['state'], 'done')
        self.assertIn('a large change applied on its own (12 files)', status['reasons'])

    def test_findings_on_an_older_version_are_retired_by_the_re_review(self):
        from kel import assurance, pod_review
        contract = {'request': 'Write the security policy', 'milestones': [{'id': 'd', 'objective': 'Write it',
                    'filename': 'd.md', 'depends_on': [], 'checks': [
                        {'kind': 'min_chars', 'value': 3}, {'kind': 'manual_review', 'rubric': 'Good.'}]}]}
        contract['staffing'] = staff.plan_job(self.store, contract, 'Fix the password rules in the security policy')
        job = self.store.create(contract)
        run = self.store.claim(job, 'd', provider='claude')
        self.store.enqueue_result('r1', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'Version one.'})
        self.store.consume()
        first = self.store.get(job)
        lenses = pod_review.lenses_for(first) or ['requirements-coverage']
        verdict, sentences = pod_review.record(
            self.store, first, 'd', 'rev1', 'codex', lenses, 'VERIFIED',
            [{'lens': lenses[0], 'severity': 'blocker', 'summary': 'It allows reused passwords.'}])
        self.assertEqual(verdict, 'FAILED')
        self.assertTrue(any('held this back' in line for line in sentences))
        self.assertEqual(len(pod_review.live_serious(self.store, first)), 1)
        with self.store.transaction() as db:
            record = self.store._get(db, job)
            record['milestones']['d'].update(state='NEEDS_REPAIR')
            record['state'] = 'READY'
            self.store._save(db, record, 'test.repair')
        run = self.store.claim(job, 'd', provider='claude')
        self.store.enqueue_result('r2', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'Version two.'})
        self.store.consume()
        second = self.store.get(job)
        verdict, _sentences = pod_review.record(self.store, second, 'd', 'rev2', 'codex', lenses, 'VERIFIED', [])
        self.assertEqual(verdict, 'VERIFIED')
        self.assertEqual(pod_review.live_serious(self.store, second), [])
        rows = assurance.findings(self.store, mission_id=job)
        self.assertEqual([(r['status'], r['resolution_kind']) for r in rows], [('fixed', 'fixed')])

    def test_the_oracle_goes_to_another_model_when_astra_cannot_run(self):
        project = make_project(self.tmp.name)
        text = 'Fix the password check in app.txt'
        contract = compile_coding(text, project, ['python', '-c', 'pass'])
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        job = self.store.create(contract)
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        reviews = {'claude': FakeModel('claude')}
        commander = Commander(FakeModel('claude'))
        commander.staff = StaffStub({'claude'}, reviews)  # only the Builder's own family is here
        engine = Engine(self.store, {'claude-code': claude}, reviewer=commander)
        try:
            self.run_engine(engine, job, lambda j: (project / 'app.txt').read_text() == 'new')
        finally:
            engine.close()
        status = oracle.status(self.store, self.store.get(job))
        self.assertEqual((status['state'], status['independence']), ('done', 'reduced'))
        call = next(c for c in staff.calls(self.store, job) if c['kind'] == 'oracle')
        self.assertEqual(call['ran']['adapter'], 'claude')
        self.assertIn('GPT-6 Astra', call['why'])


if __name__ == '__main__':
    unittest.main()
