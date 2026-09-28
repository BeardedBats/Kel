"""D-72 — the six routing defaults, adopted 2026-09-28, each pinned here.

1. "Auto" reasoning follows the dispatch tier (fast → low, standard → the model's default, deep and
   assurance → high); an explicit level in Settings wins.
2. Budget classes keep their starting values.
3. Strength ranks start from the list-price estimate; outcome evidence moves a model in the ranking.
4. OpenRouter carries only DeepSeek Flash.
5. Codex and Claude Code subscription calls cost nothing extra when ranking; the plan's quota counts.
6. Kel's own turn, reply and plan calls are recorded in usage.

Fake models only; no provider is ever called.
"""
import contextlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel import api_models, budget, role_models, staff, task_routing, usage
from kel.commander import Commander
from kel.core import Store, encode
from kel.providers import DEFINITIONS

sys.path.insert(0, str(Path(__file__).parent))
from test_turn_handoff import FakeTurn  # noqa: E402

ALL = {'codex', 'codex-code', 'claude', 'claude-code', 'internal', 'research'}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)


class ReasoningFollowsTheTier(Base):  # item 1
    def test_auto_reasoning_per_tier_and_an_explicit_level_wins(self):
        self.assertEqual(task_routing.TIER_REASONING,
                         {'fast': 'low', 'standard': None, 'deep': 'high', 'assurance': 'high'})
        for tier, effort in (('fast', 'low'), ('standard', None), ('deep', 'high'), ('assurance', 'high')):
            out = role_models.resolve(self.store, 'builder', adapters=ALL, purpose='code', task_class='coding',
                                      tier=tier)
            self.assertEqual(out['effort_arg'], effort, tier)
        role_models.set_role(self.store, 'builder', 'preferred', 'claude-opus-5-5', 'medium')
        out = role_models.resolve(self.store, 'builder', adapters=ALL, purpose='code', task_class='coding',
                                  tier='deep')
        self.assertEqual(out['effort_arg'], 'medium')

    def test_reviews_run_at_high_by_default(self):
        out = role_models.resolve(self.store, 'verifier', adapters=ALL, task_class='review',
                                  tier='assurance', avoid_family='anthropic')
        self.assertEqual(out['effort_arg'], 'high')


class BudgetsKeepTheirStartingValues(unittest.TestCase):  # item 2
    def test_the_ceilings_are_the_starting_values(self):
        self.assertEqual(budget.CEILINGS, {
            'tiny': {'tokens': 300_000, 'minutes': 20, 'cost': 2.0},
            'standard': {'tokens': 3_000_000, 'minutes': 90, 'cost': 10.0},
            'deep': {'tokens': 8_000_000, 'minutes': 240, 'cost': 30.0},
            'high-assurance': {'tokens': 15_000_000, 'minutes': 480, 'cost': 60.0}})
        self.assertEqual(budget.class_for('D1'), 'standard')


class StrengthStartsFromPrice(Base):  # item 3
    def test_ranks_come_from_the_list_price(self):
        for model_id in role_models.MODELS:
            self.assertEqual(role_models.STRENGTH[model_id], role_models.strength_from_price(model_id), model_id)
        self.assertEqual(role_models.STRENGTH, {'gpt-6-luna': 1, 'gpt-6-astra': 3, 'codex': 2,
                                                'claude-opus-5-5': 3, 'claude-fable-5-1': 3,
                                                'claude-sonnet': 2, 'deepseek-flash': 1})
        # An unpriced model is balanced (never "cheap and weak" because its price is unknown).
        self.assertEqual(role_models.strength_from_price('claude-sonnet'), role_models.UNPRICED_STRENGTH)

    def test_outcome_evidence_moves_a_model_without_rewriting_its_rank(self):
        from kel.routing_evidence import record as record_outcome
        # Luna fails its recent writing work three times: it moves down; its starting rank stays.
        for index in range(4):
            record_outcome(self.store, 'r%d' % index, 'codex', 'FAILED', job_kind='document', model='gpt-6-luna',
                           source='review', task_class='utility')
        ranked = task_routing.ranking(self.store, 'utility', adapters=ALL, protect=False)
        luna = next(e for e in ranked if e['model'] == 'gpt-6-luna')
        self.assertTrue(luna.get('demoted'))
        self.assertEqual(luna['strength'], 1)
        runnable = [e['model'] for e in ranked if e['runnable']]
        self.assertEqual(runnable[-1], 'gpt-6-luna')


class OpenRouterCarriesOnlyDeepSeekFlash(unittest.TestCase):  # item 4
    def test_one_catalog_model_and_one_listed_model(self):
        routed = [m for m, info in role_models.MODELS.items() if info.get('openrouter_arg')]
        self.assertEqual(routed, ['deepseek-flash'])
        listed = next(d for d in DEFINITIONS if d['id'] == 'openrouter')['models']
        self.assertEqual([m['id'] for m in listed], ['deepseek/deepseek-v4.1-flash'])

    def test_the_worker_refuses_any_other_model_without_calling_out(self):
        called = []
        adapter = api_models.OpenAICompatAdapter('openrouter', model='openai/gpt-9',
                                                 transport=lambda body, timeout: called.append(body))
        out = adapter.execute('hello')
        self.assertEqual(out['outcome'], 'FAILED')
        self.assertIn('only DeepSeek Flash', out['error'])
        self.assertEqual(called, [])


class SubscriptionsCostNothingExtra(Base):  # item 5
    def test_codex_and_claude_code_rank_at_zero_marginal_cost(self):
        for adapter in ('codex', 'codex-code', 'claude', 'claude-code'):
            self.assertTrue(role_models.is_subscription(adapter))
        for adapter in ('internal', 'research', 'deepseek', 'openrouter'):
            self.assertFalse(role_models.is_subscription(adapter))
        usage.record(self.store, 'c1', adapter='codex', model='gpt-6-astra', task_class='review',
                     result={'usage': {'input_tokens': 1000, 'cached_input_tokens': 0, 'output_tokens': 100}})
        ranked = task_routing.ranking(self.store, 'review', adapters=ALL)
        astra = next(e for e in ranked if e['model'] == 'gpt-6-astra')
        self.assertEqual(astra['measured']['marginal_cost'], 0.0)
        self.assertTrue(astra['measured']['subscription'])
        self.assertGreater(astra['measured']['avg_cost'], 0, 'the API-equivalent figure stays visible')

    def test_a_used_up_plan_quota_still_counts(self):
        with self.store.transaction() as db:
            db.execute('INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                       ('codex', encode({'failures': 0, 'circuit_until': 0, 'quota': 0})))
        ranked = task_routing.ranking(self.store, 'review', adapters={'codex', 'claude'})
        astra = next(e for e in ranked if e['model'] == 'gpt-6-astra')
        self.assertFalse(astra['runnable'])
        self.assertIn("usage limit is reached", astra['why'])
        self.assertTrue(next(e for e in ranked if e['model'] == 'claude-opus-5-5')['runnable'])


class UsageTurn(FakeTurn):
    provider = 'codex'
    model = 'gpt-6-luna'

    def execute(self, prompt, system=None, images=None, **kwargs):
        out = super().execute(prompt, system=system, images=images, **kwargs)
        out.update(model_used='gpt-6-luna', usage={'input_tokens': 900, 'cached_input_tokens': 100,
                                                   'output_tokens': 60})
        return out


class ServiceCase(unittest.TestCase):
    def setUp(self):
        from kel.service import Service
        self.tmp = tempfile.TemporaryDirectory()
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        for name in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL', 'KEL_WORKFORCE'):
            os.environ.pop(name, None)
        os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none',
                          CODEX_HOME=str(Path(self.tmp.name) / 'codex-home'))
        self.service = Service(self.tmp.name)
        self.service.turn_mode = ''
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.cid = self.service.context.conversation('default')

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.service.shutdown()
        self.tmp.cleanup()

    def wait(self, sid, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with contextlib.closing(self.service.store.connect()) as db:
                row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['state'] in ('DISPATCHED', 'SETTLED', 'FAILED'):
                return row['state']
            time.sleep(.02)
        raise TimeoutError(sid)


class KelsOwnCallsAreRecorded(ServiceCase):  # item 6

    def test_a_turn_decision_is_recorded_with_its_conversation_and_message(self):
        self.service.model = UsageTurn({'action': 'reply', 'text': 'Six to eight hours of sun.'})
        sid = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        items = usage.rows(self.service.store, submission_id=sid)
        self.assertEqual([i['kind'] for i in items], ['turn'])
        item = items[0]
        self.assertEqual((item['conversation_id'], item['role'], item['task_class']), (self.cid, 'kel', 'quick_answer'))
        self.assertEqual((item['model'], item['processed'], item['subscription']), ('gpt-6-luna', 860, True))

    def test_a_direct_reply_is_recorded(self):
        self.service.turn_mode = 'none'  # no turn model: the keyword gate, then Kel's reply model
        self.service.model = UsageTurn('Six to eight hours of sun.')
        sid = self.service.submit({'text': 'How much sun do tomatoes need?', 'conversation': self.cid})
        self.assertEqual(self.wait(sid), 'SETTLED')
        self.assertEqual([i['kind'] for i in usage.rows(self.service.store, submission_id=sid)], ['reply'])

    def test_a_plan_call_is_recorded(self):
        planner = UsageTurn(json.dumps({'milestones': [{'id': 'm', 'objective': 'x', 'filename': 'a.md',
                                                        'depends_on': [], 'checks': []}]}))
        seen = []
        contract, meta = Commander(planner).plan('Write a short note about tomatoes',
                                                 on_result=lambda model, result, wall: seen.append((model, result, wall)))
        self.assertTrue(contract['milestones'])  # a proposal or the template: the call is recorded either way
        self.assertEqual(len(seen), 1)
        self.assertIs(seen[0][0], planner)
        self.service._kel_usage('plan', 'sub-1', self.cid, planner, seen[0][1], seen[0][2])
        self.assertEqual([(i['kind'], i['task_class']) for i in usage.rows(self.service.store, submission_id='sub-1')],
                         [('plan', 'planning')])


if __name__ == '__main__':
    unittest.main()
