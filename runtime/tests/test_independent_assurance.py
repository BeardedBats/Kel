"""Phase 3 independent assurance: Sentinel as a real staff member, the Red Team mode of Independent
Assurance, and the resume brief's `wait` on /api/work and the continuation list.

Fake runtimes only (no provider is ever called): the Builder is `FakeCoder` (a real isolated copy
and diff), every reviewer is `FakeModel`, which answers by what it is asked.
"""
import contextlib
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel import office, oracle, scoping, staff
from kel.auto_apply import decision as apply_decision
from kel.coding import CodingAdapter, compile_coding
from kel.commander import Commander
from kel.core import STUCK_WAIT, BUDGET_WAIT, Store
from kel.engine import Engine

sys.path.insert(0, str(Path(__file__).parent))
from test_role_models_live import FakeCoder, make_project  # noqa: E402
from test_workforce_e2e import FakeModel, ServiceBase, StaffStub  # noqa: E402


def writing(request):
    return {'request': request, 'milestones': [{'id': 'document', 'objective': request, 'filename': 'd.md',
                                                'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 3}]}]}


class TriggerTests(unittest.TestCase):
    """Who is staffed is decided once, at intake, from staff.py's flags (frozen in the contract)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        self.project = make_project(self.tmp.name)

    def code(self, text):
        return staff.plan_job(self.store, compile_coding(text, self.project, ['python', '-c', 'pass']), text)

    def test_a_security_code_change_brings_sentinel_with_the_security_lens(self):
        record = self.code('Fix the password check in app.txt')
        self.assertEqual(record['sentinel'], {'required': True, 'why': ['a code change touching security'],
                                              'lenses': ['security']})
        # D-85: the Red Team is for high-assurance (D4) work only; security alone never brings it.
        self.assertEqual(record['red_team'], {'required': False, 'why': [], 'size_trigger': None})
        self.assertFalse(record['oracle']['required'], 'security is for Sentinel; the Oracle is for hard-to-undo work')

    def test_migration_and_privacy_work_bring_their_own_lenses(self):
        self.assertEqual(self.code('Migrate the users table to the new schema')['sentinel']['lenses'],
                         ['data-integrity'])
        # D-85: a privacy word alone is not security work; the Verifier covers it.
        record = self.code('Stop sending personal data in the crash telemetry')
        self.assertEqual((record['sentinel']['required'], record['sentinel']['lenses']), (False, ['privacy']))
        self.assertEqual(record['review']['verifier']['when'], 'always')
        record = self.code('Encrypt the personal data in the crash telemetry')
        self.assertEqual((record['sentinel']['required'], record['sentinel']['lenses']), (True, ['privacy', 'security']))

    def test_an_ordinary_change_has_no_sentinel(self):
        record = self.code('Fix the typo in app.txt')
        self.assertFalse(record['sentinel']['required'])
        self.assertIsNone(record['sentinel']['not_needed'])

    def test_a_security_word_in_writing_is_a_mention_not_a_sentinel_review(self):
        # FN-07: the word alone neither asks Nick first nor brings Sentinel.
        text = 'Write a short note explaining what an API token is'
        record = staff.plan_job(self.store, writing(text), text)
        self.assertFalse(record['sentinel']['required'])
        self.assertIn('changes no code', record['sentinel']['not_needed'])
        self.assertIsNone(scoping.consider(self.store, text, 'writing', {}))
        self.assertIsNone(scoping.consider(self.store, 'Write a note about privacy at work', 'writing', {}))

    def test_high_assurance_work_gets_sentinel_and_the_red_team(self):
        self.assertTrue(staff.sentinel_decision('writing', 'D4', ['security_boundary'])['required'])
        self.assertFalse(staff.sentinel_decision('writing', 'D4', [])['required'])
        red = staff.red_team_decision('writing', 'D4', [])
        self.assertEqual((red['required'], red['why']), (True, ['high-assurance work is attacked once it is accepted']))
        self.assertFalse(staff.red_team_decision('code', 'D2', ['security_boundary'])['required'])

    def test_work_staffed_before_sentinel_existed_is_never_re_decided(self):
        record = self.code('Fix the password check in app.txt')
        record.pop('sentinel')
        record.pop('red_team')
        job = {'id': 'j', 'contract': {'kind': 'coding', 'staffing': record}, 'verdict': 'VERIFIED'}
        self.assertEqual(oracle.trigger(self.store, job, 'sentinel'), (False, []))
        self.assertEqual(oracle.trigger(self.store, job, 'red_team'), (False, []))


class EngineBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        CodingAdapter(self.store)
        self.project = make_project(self.tmp.name)

    def job(self, text, legacy=False):
        contract = compile_coding(text, self.project, ['python', '-c', 'pass'])
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        if legacy:
            # A job staffed before D-85: its frozen record brings the Oracle and the Red Team's size
            # trigger for security work, and is never re-decided.
            contract['staffing']['oracle'] = {'required': True, 'why': ['consequential work (security boundary)']}
            contract['staffing']['red_team']['size_trigger'] = {'files': 5, 'lines': 150}
            contract['staffing']['review'].pop('verifier', None)
        return self.store.create(contract)

    def engine(self, reviews, adapters=('codex', 'claude'), files=1):
        self.coder = FakeCoder(self.store, reports='claude-opus-5-5', files=files)
        commander = Commander(FakeModel('claude'))
        commander.staff = StaffStub(set(adapters), reviews)
        return Engine(self.store, {'claude-code': self.coder}, reviewer=commander)

    def drive(self, engine, job, until, timeout=40):
        deadline = time.time() + timeout
        while time.time() < deadline:
            engine.tick()
            current = self.store.get(job)
            if until(current):
                return current
            time.sleep(.03)
        raise TimeoutError(self.store.get(job)['state'])

    def settled(self, engine, job):
        return self.drive(engine, job, lambda j: bool(apply_decision(self.store, j['id'])))

    def kinds(self, job):
        return [(c['role'], c['kind'], c['state']) for c in staff.calls(self.store, job)
                if c['kind'] not in ('work', 'check')]


class SentinelTests(EngineBase):
    def test_sentinel_runs_read_only_on_its_role_model_and_a_clean_result_applies(self):
        reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}
        job = self.job('Fix the password check in app.txt')
        engine = self.engine(reviews)
        try:
            self.drive(engine, job, lambda j: (self.project / 'app.txt').read_text() == 'new')
        finally:
            engine.close()
        self.assertEqual(self.kinds(job), [('sentinel', 'sentinel', 'done')], 'D-85: no Oracle for routine security work')
        call = next(c for c in staff.calls(self.store, job) if c['kind'] == 'sentinel')
        # Automatic role, resolved on the assurance tier (never lowered), another family than the Builder.
        self.assertEqual((call['asked']['role'], call['asked']['mode'], call['asked'].get('dispatch')),
                         ('sentinel', 'AUTOMATIC', 'assurance'))
        self.assertEqual((call['ran']['adapter'], call['ran']['independence']), ('codex', 'different'))
        prompt = next(p for p in reviews['codex'].prompts if p.startswith('You are Sentinel'))
        self.assertIn('diff', prompt)
        self.assertNotIn('Changed app.txt to the new text', prompt, "never the Builder's own report")
        self.assertNotIn('Earlier findings', prompt, 'fresh context: Sentinel does not see earlier findings')
        with contextlib.closing(self.store.connect()) as db:
            labels = [r[0] for r in db.execute("SELECT label FROM evidence_records WHERE task_id=?",
                                               ('sentinel:' + job,))]
        self.assertEqual(labels, ['lens coverage: security (sentinel)'])
        text = self.store.get(job)
        self.assertIn('Sentinel also checked it', oracle.result_note(self.store, text))

    def test_a_sentinel_blocker_stops_auto_apply_and_becomes_needs_you(self):
        blocker = {'verdict': 'block', 'findings': [{
            'severity': 'blocker', 'area': 'security', 'summary': 'The password is compared in plain text.',
            'where': 'app.txt:1', 'proof': 'static', 'clears_when': 'It compares a salted hash.'}]}
        reviews = {'codex': FakeModel('codex', sentinel=blocker), 'claude': FakeModel('claude', sentinel=blocker)}
        job = self.job('Fix the password check in app.txt')
        engine = self.engine(reviews, files=8)
        try:
            final = self.settled(engine, job)
        finally:
            engine.close()
        self.assertEqual((self.project / 'app.txt').read_text(), 'old', 'nothing applied on its own')
        self.assertEqual(apply_decision(self.store, job)['decision'], 'waiting')
        needed = oracle.attention(self.store, final)
        self.assertEqual(needed['source'], 'sentinel')
        self.assertEqual(needed['why'], "Sentinel's security check found a problem: The password is compared "
                                        'in plain text..')
        rows = oracle.findings_for(self.store, final, live_only=True, kind='sentinel')
        self.assertEqual([(r['lens'], r['severity'], r['location']) for r in rows],
                         [('security', 'blocker', 'app.txt:1')])
        self.assertIn('clears when: It compares a salted hash.', rows[0]['evidence'])
        # The card: Needs you, with Sentinel's own words, and the staff row in plain words.
        state, line, needs_you, _why, _next = office.state_of(self.store, final)
        self.assertEqual((state, needs_you), ('needs_you', True))
        self.assertIn('Sentinel', line)
        view = office.detail(self.store, job)
        self.assertEqual(view['question']['text'], "Sentinel's security check raised a problem. Apply the change anyway?")
        member = next(m for m in view['staff'] if m['role'] == 'sentinel')
        self.assertEqual(member['doing'], 'Security check: raised 1 serious finding')
        self.assertEqual(view['sentinel']['findings'][0]['area'], 'Security')
        self.assertTrue(view['sentinel']['conclusion'].startswith('It found a serious problem'))
        # D-85: no Red Team below D4.
        self.assertEqual(view['red_team']['state'], 'not_needed')
        self.assertNotIn('red_team', [c['kind'] for c in staff.calls(self.store, job)])
        team = office.items(self.store)['items'][0]['team']
        self.assertIn({'role': 'sentinel', 'role_label': 'Sentinel', 'state': 'done'}, team)

    def test_sentinel_that_could_not_assess_is_never_clean(self):
        unassessed = {'verdict': 'not_assessed', 'findings': []}
        reviews = {'codex': FakeModel('codex', sentinel=unassessed)}
        job = self.job('Fix the password check in app.txt')
        engine = self.engine(reviews, adapters=('codex',))
        try:
            final = self.settled(engine, job)
        finally:
            engine.close()
        self.assertEqual(oracle.status(self.store, final, 'sentinel')['state'], 'could_not_run')
        self.assertEqual(apply_decision(self.store, job)['decision'], 'waiting')
        self.assertIn('could not assess', oracle.attention(self.store, final)['why'])


class RedTeamTests(EngineBase):
    def test_a_sizeable_security_change_is_attacked_with_every_earlier_finding(self):
        note = [{'severity': 'info', 'summary': 'The error message names the user.', 'claim': 'c'}]
        attack = [{'severity': 'blocker', 'surface': 'empty password', 'summary': 'An empty password is accepted.',
                   'outcome': 'confirmed', 'procedure': 'Submit an empty password.'},
                  {'severity': 'info', 'surface': 'long input', 'summary': 'Long input is handled.',
                   'outcome': 'clean'}]
        reviews = {'codex': FakeModel('codex', challenges=note, attacks=attack), 'claude': FakeModel('claude')}
        job = self.job('Fix the password check in app.txt', legacy=True)
        engine = self.engine(reviews, files=7)
        try:
            final = self.settled(engine, job)
        finally:
            engine.close()
        self.assertEqual([k for _r, k, _s in self.kinds(job)], ['sentinel', 'oracle', 'red_team'])
        status = oracle.status(self.store, final, 'red_team')
        self.assertEqual((status['state'], status['independence']), ('done', 'different'))
        self.assertIn('a sizeable security change (7 files', status['reasons'][0])
        call = next(c for c in staff.calls(self.store, job) if c['kind'] == 'red_team')
        self.assertEqual((call['role'], call['asked']['role'], call['ran']['adapter']), ('red_team', 'oracle', 'codex'))
        prompt = next(p for p in reviews['codex'].prompts if p.startswith('You are the Red Team'))
        self.assertIn('The error message names the user.', prompt, 'earlier findings are its coverage map')
        # Its findings behave like the Oracle's: a blocker holds the change for Nick.
        rows = oracle.findings_for(self.store, final, kind='red_team')
        self.assertEqual([(r['lens'], r['severity'], r['location']) for r in rows],
                         [('adversarial', 'blocker', 'empty password')], 'clean outcomes are coverage, not findings')
        self.assertEqual(apply_decision(self.store, job)['decision'], 'waiting')
        self.assertEqual((self.project / 'app.txt').read_text(), 'old')
        needed = oracle.attention(self.store, final)
        self.assertEqual((needed['source'], needed['why']),
                         ('red_team', 'The Red Team found a problem: An empty password is accepted..'))
        view = office.detail(self.store, job)
        member = next(m for m in view['staff'] if m['role'] == 'red_team')
        self.assertEqual((member['role_label'], member['doing']), ('Red Team', 'Tried to break it: raised 1 serious finding'))
        self.assertEqual(view['red_team']['independence_label'],
                         'A different model family from the one that did the work')
        with contextlib.closing(self.store.connect()) as db:
            labels = [r[0] for r in db.execute('SELECT label FROM evidence_records WHERE task_id=?',
                                               ('redteam:' + job,))]
        self.assertEqual(labels, ['lens coverage: adversarial (red team)'])

    def test_a_small_security_change_is_not_attacked(self):
        reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}
        job = self.job('Fix the password check in app.txt', legacy=True)
        engine = self.engine(reviews, files=2)
        try:
            self.drive(engine, job, lambda j: (self.project / 'app.txt').read_text() == 'new')
        finally:
            engine.close()
        self.assertEqual(oracle.status(self.store, self.store.get(job), 'red_team')['state'], 'not_needed')

    def test_same_family_red_team_records_reduced_independence(self):
        reviews = {'claude': FakeModel('claude')}
        job = self.job('Fix the password check in app.txt', legacy=True)
        engine = self.engine(reviews, adapters=('claude',), files=7)
        try:
            self.drive(engine, job, lambda j: (self.project / 'app.txt').read_text() == 'new')
        finally:
            engine.close()
        status = oracle.status(self.store, self.store.get(job), 'red_team')
        self.assertEqual((status['state'], status['independence']), ('done', 'reduced'))


class RestartTests(EngineBase):
    def test_a_sentinel_pass_killed_mid_review_is_rerun_once_then_recorded_as_a_gap(self):
        reviews = {'codex': FakeModel('codex'), 'claude': FakeModel('claude')}
        job = self.job('Fix the password check in app.txt')
        engine = self.engine(reviews)
        try:
            self.drive(engine, job, lambda j: j['state'] == 'CLOSED')
        finally:
            engine.close()
        final = self.store.get(job)
        _mid, subject = oracle.subject_of(final)
        key = 'sentinel:' + subject
        # A killed engine left Sentinel RUNNING with an open staff call (as a crash would).
        with self.store.transaction() as db:
            db.execute('DELETE FROM oracle_reviews')
            db.execute("DELETE FROM staff_calls WHERE kind IN ('sentinel','oracle')")
        oracle._start(self.store, job, key, ['test'])
        staff.start_call(self.store, call_id='snt_dead', job_id=job, milestone_id='code', role='sentinel',
                         kind='sentinel', subject=subject)
        engine = self.engine(reviews)
        try:
            self.assertEqual(oracle._row(self.store, job, key)['status'], oracle.INTERRUPTED)
            self.assertEqual(next(c for c in staff.calls(self.store, job) if c['id'] == 'snt_dead')['state'],
                             'stopped')
            self.drive(engine, job, lambda j: (self.project / 'app.txt').read_text() == 'new')
        finally:
            engine.close()
        row = oracle._row(self.store, job, key)
        self.assertEqual((row['status'], row['attempts']), (oracle.DONE, 2))
        self.assertEqual(self.store.get(job)['contract']['staffing']['decided_at'],
                         final['contract']['staffing']['decided_at'], 'the decision is never re-made')
        self.assertEqual(len(self.coder.calls), 0, 'the built change was never rebuilt')

    def test_interrupted_twice_is_a_recorded_gap_that_waits_for_nick(self):
        reviews = {'codex': FakeModel('codex')}
        job = self.job('Fix the password check in app.txt')
        engine = self.engine(reviews, adapters=('codex',))
        try:
            self.drive(engine, job, lambda j: j['state'] == 'CLOSED' and oracle.subject_of(j)[1] is not None)
        finally:
            engine.close()
        _mid, subject = oracle.subject_of(self.store.get(job))
        key = 'sentinel:' + subject
        with self.store.transaction() as db:
            db.execute('DELETE FROM oracle_reviews')
            db.execute('INSERT INTO oracle_reviews VALUES(?,?,?,?,?,?)', (job, key, 2, oracle.INTERRUPTED, '{}', 0))
        self.assertIsNone(oracle._pending_one(self.store, self.store.get(job), 'sentinel'))
        status = oracle.status(self.store, self.store.get(job), 'sentinel')
        self.assertEqual((status['state'], status['why']), ('could_not_run', 'the security check was interrupted twice'))
        self.assertIn("Sentinel's security check could not run", oracle.gate(self.store, self.store.get(job)))


class WaitFieldTests(ServiceBase):
    def test_work_entries_and_continuation_candidates_carry_the_wait(self):
        from kel.continuation import Continuation
        cid = self.service.context.conversation('default')
        stuck = self.store.create(writing('Write a haiku about autumn'), conversation=cid)
        self.store.wait_for_route(stuck, STUCK_WAIT + 'it ran out of tries.')
        budget = self.store.create(writing('Write a limerick'), conversation=cid)
        self.store.wait_for_route(budget, BUDGET_WAIT + 'the standard budget is used up.')
        fenced = self.store.create(writing('Write a sonnet'), conversation=cid)
        self.store.claim(fenced, 'document', provider='fixture', model='fixture')
        self.store.recover_abandoned(now=time.time() + 600)
        running = self.store.create(writing('Write a riddle'), conversation=cid)
        waits = {entry['job_id']: entry['wait'] for entry in self.service._work(cid)['work']['jobs']}
        self.assertEqual(waits, {stuck: 'stuck', budget: 'budget', fenced: 'interrupted', running: None})
        candidates = {c['job_id']: c['wait'] for c in
                      Continuation(self.store).candidates(self.service._project_of(cid))}
        self.assertEqual((candidates[stuck], candidates[budget], candidates[fenced]), ('stuck', 'budget', 'interrupted'))
        self.assertEqual(Continuation(self.store).resume_brief(stuck)['wait'], 'stuck')


if __name__ == '__main__':
    unittest.main()
