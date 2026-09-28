"""Routing 2 §5.3 — outcome-aware routing per (task class, model), inside doc 10's limits.

Promotion as well as demotion, only with at least three outcomes and the decayed weight floor;
never past Nick's Fixed/Preferred choice; never a weaker model for an assurance binding; every
change carries its plain reason. MoFlo's idea, without MoFlo's gaps (failures count, evidence
decays, small samples say nothing). No provider is called.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

from kel import role_models, routing_evidence, staff, task_routing
from kel.core import Store
from kel.routing_evidence import DAY, class_score, record

ALL = {'codex', 'codex-code', 'claude', 'claude-code', 'internal', 'research'}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        self.n = 0

    def outcome(self, provider, model, verdict, task_class, attempts=1, age_days=0.0, job_kind=None):
        self.n += 1
        record(self.store, 'run-%d' % self.n, provider, verdict, model=model, attempts=attempts,
               task_class=task_class, job_kind=job_kind, at=time.time() - age_days * DAY)


class ScoreTests(Base):
    def test_three_first_try_verified_outcomes_promote(self):
        for _ in range(3):
            self.outcome('codex', 'gpt-6-luna', 'VERIFIED', 'utility')
        scored = class_score(self.store, 'utility', 'gpt-6-luna')
        self.assertEqual((scored['samples'], scored['rate'], scored['verdict']), (3, 1.0, 'promote'))
        self.assertIsNone(class_score(self.store, 'coding', 'gpt-6-luna')['rate'], 'classes do not mix')

    def test_two_outcomes_say_nothing(self):
        for _ in range(2):
            self.outcome('codex', 'gpt-6-luna', 'FAILED', 'utility')
        scored = class_score(self.store, 'utility', 'gpt-6-luna')
        self.assertEqual((scored['samples'], scored['rate'], scored['verdict']), (2, None, None))
        self.assertIn('not enough to judge', routing_evidence.class_sentence(scored))

    def test_rework_counts_half_and_failures_demote(self):
        for _ in range(3):
            self.outcome('claude', 'claude-sonnet', 'VERIFIED', 'writing', attempts=2)
        scored = class_score(self.store, 'writing', 'claude-sonnet')
        self.assertEqual((scored['rate'], scored['verdict']), (0.5, None))
        self.outcome('claude', 'claude-sonnet', 'FAILED', 'writing')
        self.assertEqual(class_score(self.store, 'writing', 'claude-sonnet')['verdict'], 'demote')

    def test_old_outcomes_decay_below_the_floor(self):
        for _ in range(4):
            self.outcome('codex', 'gpt-6-luna', 'FAILED', 'utility', age_days=25)
        self.assertIsNone(class_score(self.store, 'utility', 'gpt-6-luna')['rate'])

    def test_older_rows_count_by_their_job_kind_and_raw_model_ids_map_to_the_catalog(self):
        for _ in range(3):
            self.outcome('claude-code', 'claude-opus-5-5[1m]', 'VERIFIED', None, job_kind='coding')
        self.assertEqual(class_score(self.store, 'coding', 'claude-opus-5-5')['verdict'], 'promote')
        for _ in range(3):
            self.outcome('codex-code', None, 'FAILED', None, job_kind='coding')
        self.assertEqual(class_score(self.store, 'coding', 'codex')['verdict'], 'demote',
                         "a Codex run with no model named ran Codex's default")


class RankingTests(Base):
    def test_promotion_moves_a_model_up_one_band_and_says_why(self):
        role_models.set_role(self.store, 'utility', 'automatic')
        before = [e['model'] for e in task_routing.ranking(self.store, 'utility', adapters=ALL, tier='standard')
                  if e['runnable']]
        weaker = next(m for m in before if role_models.STRENGTH[m] == 1)
        for _ in range(3):
            self.outcome('codex', weaker, 'VERIFIED', 'utility')
        ranked = task_routing.ranking(self.store, 'utility', adapters=ALL, tier='standard')
        entry = next(e for e in ranked if e['model'] == weaker)
        self.assertTrue(entry.get('promoted'))
        self.assertIn('moved up: Verified in about 100% of its recent utility work runs', entry['why'])
        self.assertLess([e['model'] for e in ranked].index(weaker), before.index(weaker) + 1)

    def test_demotion_steps_aside_but_never_removes(self):
        role_models.set_role(self.store, 'discovery', 'automatic')
        first = task_routing.top(self.store, 'research', adapters=ALL)['model']
        for _ in range(3):
            self.outcome('claude', first, 'FAILED', 'research')
        ranked = [e for e in task_routing.ranking(self.store, 'research', adapters=ALL) if e['runnable']]
        self.assertNotEqual(ranked[0]['model'], first)
        self.assertEqual(ranked[-1]['model'], first, 'still in the list, last')
        self.assertIn('moved down', ranked[-1]['why'])

    def test_evidence_never_moves_a_preferred_choice(self):
        for _ in range(4):
            self.outcome('claude-code', 'claude-opus-5-5', 'FAILED', 'coding')
        ranked = task_routing.ranking(self.store, 'coding', adapters=ALL)
        self.assertEqual(ranked[0]['model'], 'claude-opus-5-5')
        self.assertIn('your preferred choice', ranked[0]['why'])
        out = role_models.resolve(self.store, 'builder', adapters=ALL, purpose='code', task_class='coding')
        self.assertEqual(out['model'], 'claude-opus-5-5', 'D-69: the role model always runs when it can')

    def test_an_assurance_binding_is_never_moved_to_a_weaker_model(self):
        role_models.set_role(self.store, 'verifier', 'automatic')
        for _ in range(5):
            self.outcome('claude', 'claude-sonnet', 'VERIFIED', 'review')
        ranked = [e for e in task_routing.ranking(self.store, 'review', adapters=ALL, tier='assurance')
                  if e['runnable']]
        self.assertEqual(role_models.STRENGTH[ranked[0]['model']], 3)
        sonnet = next(e for e in ranked if e['model'] == 'claude-sonnet')
        self.assertFalse(sonnet.get('promoted'))

    def test_the_resolved_call_records_the_ranking_it_used(self):
        role_models.set_role(self.store, 'utility', 'automatic')
        out = role_models.resolve(self.store, 'utility', adapters=ALL, task_class='utility', tier='fast')
        self.assertTrue(out['asked']['ranking'])
        self.assertEqual(out['asked']['ranking'][0]['model'], out['model'])


class RecordTests(Base):
    def test_a_reviewed_verdict_carries_its_task_class(self):
        contract = {'request': 'Write a haiku', 'milestones': [{'id': 'd', 'objective': 'Write a haiku',
                    'filename': 'd.md', 'depends_on': [], 'checks': [
                        {'kind': 'min_chars', 'value': 3}, {'kind': 'manual_review', 'rubric': 'Good.'}]}]}
        contract['staffing'] = staff.plan_job(self.store, contract)
        job = self.store.create(contract)
        run = self.store.claim(job, 'd', provider='codex', model='gpt-6-luna')
        self.store.enqueue_result('r', run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': 'Leaves fall.',
                                                                  'model_used': 'gpt-6-luna'})
        self.store.consume()
        self.store.verify(job, 'd')
        subject = self.store.get(job)['milestones']['d']['artifact']['sha256']
        self.store.record_review(job, 'd', subject, 'rev', 'VERIFIED', ['Good.'])
        import contextlib
        with contextlib.closing(self.store.connect()) as db:
            row = dict(db.execute('SELECT * FROM routing_outcomes WHERE run_id=?', (run['id'],)).fetchone())
        self.assertEqual((row['task_class'], row['model'], row['verdict']),
                         (staff.step_routing(self.store.get(job), 'd')[0], 'gpt-6-luna', 'VERIFIED'))


class WhyTests(unittest.TestCase):
    def test_why_this_model_reads_the_staffed_steps_own_record(self):
        from kel.service import Service
        with tempfile.TemporaryDirectory() as tmp:
            saved = dict(os.environ)
            try:
                os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none',
                                  CODEX_HOME=str(Path(tmp) / 'codex-home'))
                os.environ.pop('ANTHROPIC_API_KEY', None)
                service = Service(Path(tmp) / 'data')
                try:
                    store = service.store
                    contract = {'request': 'Tidy this list', 'milestones': [{'id': 'd', 'objective': 'x',
                                'filename': 'd.md', 'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 3}]}]}
                    contract['staffing'] = staff.plan_job(store, contract)
                    job = store.create(contract, conversation='chat-1')
                    route = {'selected': 'codex', 'why': 'your preferred model', 'chain': ['codex']}
                    store.claim(job, 'd', provider='codex', route=route, model='gpt-6-luna', staff={
                        'role': 'utility',
                        'asked': {'role': 'utility', 'mode': 'AUTOMATIC', 'task_class': 'utility', 'dispatch': 'fast',
                                  'ranking': [{'model': 'gpt-6-luna', 'why': 'a close fit for fast work'}]},
                        'why': 'Automatic: a close fit for fast work; covered by your subscription',
                        'ran': {'adapter': 'codex', 'model': 'gpt-6-luna', 'model_confirmed': True}})
                    answer = service.action('/api/model', {'action': 'why', 'conversation': 'chat-1'})
                    self.assertEqual(answer['task_class'], 'utility')
                    self.assertEqual(answer['answer'],
                                     'Kel used ChatGPT Luna as the Utility (utility work, fast tier): '
                                     'Automatic: a close fit for fast work; covered by your subscription.')
                finally:
                    service.shutdown()
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
