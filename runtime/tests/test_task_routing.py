"""Routing 2 §5.1 — task classes, dispatch tiers and the per-class ranked model list.

Nick's Settings row (Fixed / Preferred) always heads the list and is never moved; Automatic finally
picks a model (not just a runtime); a tier sets the reasoning of a role left on Auto; review is
always assurance. No provider is called.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path

from kel import role_models, staff, task_routing
from kel.core import Store

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


class TierTests(unittest.TestCase):
    def test_review_is_always_assurance(self):
        self.assertEqual(task_routing.tier_for_step('review', {}, 'fast')[0], 'assurance')

    def test_a_hint_sets_the_tier_and_rules_only_raise_it(self):
        self.assertEqual(task_routing.tier_for_step('writing', {}, 'fast')[0], 'fast')
        tier, reasons = task_routing.tier_for_step('writing', {'flags': ['security_boundary']}, 'fast')
        self.assertEqual(tier, 'deep', 'a security flag is never lowered by the classifier')
        self.assertTrue(any('consequential' in r for r in reasons))
        self.assertEqual(task_routing.tier_for_step('coding', {'features': {'complexity': 2}})[0], 'deep')
        self.assertEqual(task_routing.tier_for_step('coding', {'features': {'complexity': 1}})[0], 'standard')
        self.assertEqual(task_routing.tier_for_step('writing', {}, 'assurance')[0], 'deep')

    def test_tier_reasoning_is_clamped_to_what_the_runtime_offers(self):
        self.assertEqual(task_routing.reasoning_for('deep', 'claude-opus-5-5'), 'high')
        self.assertEqual(task_routing.reasoning_for('fast', 'claude-opus-5-5'), 'low')
        self.assertIsNone(task_routing.reasoning_for('standard', 'claude-opus-5-5'))
        self.assertIsNone(task_routing.reasoning_for('deep', 'deepseek-flash'), 'no reasoning setting there')


class StaffingTests(Base):
    def test_every_staffed_step_carries_its_class_and_tier(self):
        contract = {'request': 'Fix the login bug in the authentication module', 'kind': 'coding',
                    'milestones': [{'id': 'code', 'objective': 'x', 'filename': 'r.md', 'depends_on': [],
                                    'checks': []}]}
        record = staff.plan_job(self.store, contract)
        step = record['steps']['code']
        self.assertEqual((step['role'], step['task_class']), ('builder', 'coding'))
        self.assertEqual(step['dispatch'], 'deep', 'an authentication change is consequential')
        self.assertTrue(step['dispatch_why'])
        writing = staff.plan_job(self.store, {'request': 'Draft a short thank-you note', 'milestones': [
            {'id': 'd', 'objective': 'x', 'filename': 'd.md', 'depends_on': [], 'checks': []}],
            'classification': {'task_class': 'writing', 'tier': 'fast'}})
        self.assertEqual(writing['steps']['d']['dispatch'], 'fast')

    def test_older_decisions_still_route(self):
        job = {'contract': {'staffing': {'schema': 1, 'kind': 'code', 'steps': {'code': {'role': 'builder'}},
                                         'features': {}, 'flags': []}}}
        self.assertEqual(staff.step_routing(job, 'code'), ('coding', 'standard'))
        self.assertEqual(staff.step_routing({'contract': {}}, 'code'), (None, None))


class RankingTests(Base):
    def test_a_preferred_choice_heads_the_list_and_is_protected(self):
        ranked = task_routing.ranking(self.store, 'coding', adapters=ALL)
        self.assertEqual([e['model'] for e in ranked[:2]], ['claude-opus-5-5', 'codex'])
        self.assertTrue(ranked[0]['protected'] and ranked[1]['protected'])
        self.assertIn('your preferred choice for Builder', ranked[0]['why'])
        self.assertIn('fallback you set', ranked[1]['why'])

    def test_models_that_cannot_run_come_last_with_the_reason(self):
        ranked = task_routing.ranking(self.store, 'writing', adapters={'codex'})
        deepseek = next(e for e in ranked if e['model'] == 'deepseek-flash')
        self.assertFalse(deepseek['runnable'])
        self.assertIn('DeepSeek', deepseek['why'])
        opus = next(e for e in ranked if e['model'] == 'claude-opus-5-5')
        self.assertIn('Claude Code, which is not set up', opus['why'])
        # every runnable, unprotected entry precedes every non-runnable, unprotected entry
        rest = [e for e in ranked if not e['protected']]
        seen_blocked = False
        for entry in rest:
            if not entry['runnable']:
                seen_blocked = True
            else:
                self.assertFalse(seen_blocked, 'a runnable model is never ranked below one that cannot run')

    def test_the_tier_decides_which_strength_leads(self):
        role_models.set_role(self.store, 'utility', 'automatic')
        fast = [e['model'] for e in task_routing.ranking(self.store, 'utility', adapters=ALL, tier='fast')
                if e['runnable']]
        deep = [e['model'] for e in task_routing.ranking(self.store, 'utility', adapters=ALL, tier='deep')
                if e['runnable']]
        self.assertEqual(role_models.STRENGTH[fast[0]], 1)
        self.assertEqual(role_models.STRENGTH[deep[0]], 3)

    def test_a_refused_model_is_not_runnable_and_says_why(self):
        role_models.note_refusal(self.store, 'gpt-6-luna',
                                 "The 'gpt-6-luna' model is not supported when using Codex with a ChatGPT account.")
        entry = next(e for e in task_routing.ranking(self.store, 'planning', adapters=ALL)
                     if e['model'] == 'gpt-6-luna')
        self.assertFalse(entry['runnable'])
        self.assertIn("doesn't offer it in Codex", entry['why'])


class ResolveTests(Base):
    def test_automatic_now_picks_a_model_from_the_ranking(self):
        role_models.set_role(self.store, 'utility', 'automatic')
        out = role_models.resolve(self.store, 'utility', adapters=ALL, task_class='utility', tier='fast')
        self.assertIsNotNone(out['adapter'])
        self.assertEqual(role_models.STRENGTH[out['model']], 1)
        self.assertTrue(out['why'].startswith('Automatic: '))
        self.assertEqual((out['asked']['task_class'], out['asked']['dispatch']), ('utility', 'fast'))
        self.assertEqual(out['effort_arg'], role_models.effort_arg(out['model'], 'low'))
        # Without a task class Automatic keeps today's routing (unstaffed callers).
        self.assertIsNone(role_models.resolve(self.store, 'utility', adapters=ALL)['adapter'])

    def test_a_preferred_model_that_cannot_run_falls_to_the_next_ranked_model(self):
        out = role_models.resolve(self.store, 'designer', adapters={'codex'}, task_class='design')
        self.assertEqual(out['adapter'], 'codex')
        self.assertIn('Claude Fable 5.1 needs Claude Code', out['why'])
        self.assertIn('Kel picked', out['why'])
        self.assertNotIn('usual routing', out['why'])

    def test_the_tier_sets_reasoning_only_when_the_role_is_on_auto(self):
        out = role_models.resolve(self.store, 'builder', adapters=ALL, purpose='code', task_class='coding',
                                  tier='deep')
        self.assertEqual((out['model'], out['effort_arg']), ('claude-opus-5-5', 'high'))
        self.assertEqual(out['asked']['reasoning_source'], 'tier')
        role_models.set_role(self.store, 'builder', 'preferred', 'claude-opus-5-5', 'low')
        out = role_models.resolve(self.store, 'builder', adapters=ALL, purpose='code', task_class='coding',
                                  tier='deep')
        self.assertEqual(out['effort_arg'], 'low', "Nick's explicit level always wins")

    def test_a_fixed_model_still_waits_rather_than_using_the_ranking(self):
        role_models.set_role(self.store, 'builder', 'fixed', 'claude-opus-5-5')
        out = role_models.resolve(self.store, 'builder', adapters={'codex-code'}, purpose='code',
                                  task_class='coding')
        self.assertTrue(out['waiting'])


class EngineTests(Base):
    def test_a_deep_step_runs_its_role_model_at_high_reasoning_and_says_so(self):
        from kel.coding import CodingAdapter, compile_coding
        from kel.engine import Engine
        from test_role_models_live import FakeCoder, make_project
        CodingAdapter(self.store)
        project = make_project(self.tmp.name)
        text = 'Fix the password reset flow in the authentication module'
        contract = compile_coding(text, project, ['python', '-c', 'pass'])
        contract['staffing'] = staff.plan_job(self.store, contract, text)
        job = self.store.create(contract)
        claude = FakeCoder(self.store, reports='claude-opus-5-5')
        engine = Engine(self.store, {'claude-code': claude})
        try:
            deadline = time.time() + 20
            while time.time() < deadline and not claude.calls:
                engine.tick()
                time.sleep(.02)
        finally:
            engine.close()
        self.assertEqual((claude.calls[0]['model_arg'], claude.calls[0]['effort_arg']), ('claude-opus-5-5', 'high'))
        call = staff.calls(self.store, job)[0]
        self.assertEqual((call['asked']['task_class'], call['asked']['dispatch']), ('coding', 'deep'))
        self.assertEqual(call['asked']['reasoning_source'], 'tier')


class ApiTests(unittest.TestCase):
    def test_the_ranking_is_readable_through_the_engine_api(self):
        from kel.service import Service
        with tempfile.TemporaryDirectory() as tmp:
            saved = dict(os.environ)
            try:
                os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none',
                                  CODEX_HOME=str(Path(tmp) / 'codex-home'))
                os.environ.pop('ANTHROPIC_API_KEY', None)
                service = Service(Path(tmp) / 'data')
                try:
                    service.engine.adapters = {'codex': object(), 'codex-code': object()}
                    view = service.action('/api/model', {'action': 'ranking'})
                    classes = {c['task_class']: c for c in view['classes']}
                    self.assertEqual(set(classes), set(task_routing.TASK_CLASSES))
                    coding = classes['coding']
                    self.assertEqual((coding['role'], coding['mode'], coding['tier']), ('builder', 'PREFERRED', 'standard'))
                    self.assertEqual(coding['models'][0]['id'], 'claude-opus-5-5')
                    self.assertFalse(coding['models'][0]['runnable'])
                    self.assertTrue(all(m['why'] for m in coding['models']))
                    self.assertEqual(classes['review']['tier'], 'assurance')
                    self.assertEqual([t['id'] for t in view['tiers']], list(task_routing.TIERS))
                finally:
                    service.shutdown()
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
