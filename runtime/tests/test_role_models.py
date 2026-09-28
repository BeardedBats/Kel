"""D-67: the starting model per staff role, Fixed/Preferred/Automatic, and a real reasoning level.

No provider is called: availability is decided from the adapters a test hands in, and Codex's model
catalog is a fixture file.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from kel import role_models, staff
from kel.core import PolicyError, Store

ALL = {'codex', 'codex-code', 'claude', 'claude-code', 'internal', 'research'}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)
        home = Path(self.tmp.name) / 'codex'
        home.mkdir()
        (home / 'models_cache.json').write_text(json.dumps({'models': [
            {'slug': 'gpt-6-astra', 'default_reasoning_level': 'medium',
             'supported_reasoning_levels': [{'effort': e} for e in
                                            ('low', 'medium', 'high', 'xhigh', 'max', 'ultra')]},
            {'slug': 'gpt-6-luna', 'default_reasoning_level': 'medium',
             'supported_reasoning_levels': [{'effort': e} for e in ('low', 'medium', 'high')]}]}))
        saved = os.environ.get('CODEX_HOME')
        os.environ['CODEX_HOME'] = str(home)
        self.addCleanup(lambda: os.environ.__setitem__('CODEX_HOME', saved) if saved
                        else os.environ.pop('CODEX_HOME', None))


class DefaultsTests(Base):
    def test_d67_starting_models(self):
        expected = {'kel': 'gpt-6-luna', 'discovery': 'claude-sonnet', 'designer': 'claude-fable-5-1',
                    'builder': 'claude-opus-5-5', 'verifier': 'gpt-6-astra', 'oracle': 'gpt-6-astra',
                    'utility': 'deepseek-flash'}
        for role, model in expected.items():
            current = role_models.setting(self.store, role)
            self.assertEqual((current['mode'], current['model'], current['reasoning']),
                             ('PREFERRED', model, 'auto'), role)
        for role in ('architect', 'sentinel', 'release'):
            self.assertEqual(role_models.setting(self.store, role)['mode'], 'AUTOMATIC')

    def test_reviewers_start_in_a_different_family_than_the_builder(self):
        builder = role_models.MODELS[role_models.setting(self.store, 'builder')['model']]['family']
        for role in ('verifier', 'oracle'):
            model = role_models.setting(self.store, role)['model']
            self.assertNotEqual(role_models.MODELS[model]['family'], builder)


class SettingsTests(Base):
    def test_set_and_reset_a_role(self):
        row = role_models.set_role(self.store, 'verifier', 'fixed', 'claude-opus-5-5', 'high')
        self.assertEqual((row['mode'], row['model'], row['reasoning'], row['is_default']),
                         ('FIXED', 'claude-opus-5-5', 'high', False))
        self.assertTrue(role_models.reset_role(self.store, 'verifier')['is_default'])

    def test_refusals_are_plain(self):
        with self.assertRaisesRegex(PolicyError, 'Fixed, Preferred or Automatic'):
            role_models.set_role(self.store, 'builder', 'sometimes', 'codex')
        with self.assertRaisesRegex(PolicyError, 'not one Kel can run'):
            role_models.set_role(self.store, 'builder', 'fixed', 'gpt-9')
        with self.assertRaisesRegex(PolicyError, 'does not offer'):
            role_models.set_role(self.store, 'kel', 'preferred', 'gpt-6-luna', 'max')
        with self.assertRaises(PolicyError):
            role_models.set_role(self.store, 'commander-two', 'fixed', 'codex')

    def test_reasoning_options_come_from_the_runtime(self):
        self.assertEqual(role_models.reasoning_options('claude-opus-5-5'),
                         ('auto', 'low', 'medium', 'high', 'xhigh', 'max'))
        self.assertEqual(role_models.reasoning_options('gpt-6-luna'), ('auto', 'low', 'medium', 'high'))
        self.assertIn('ultra', role_models.reasoning_options('gpt-6-astra'))
        self.assertEqual(role_models.reasoning_options('deepseek-flash'), ('auto',))
        self.assertEqual(role_models.default_reasoning('gpt-6-astra'), 'medium')

    def test_listing_says_what_can_run_here(self):
        out = role_models.listing(self.store, {'codex', 'codex-code'})
        rows = {row['role']: row for row in out['roles']}
        self.assertTrue(rows['verifier']['available'])
        self.assertFalse(rows['builder']['available'])
        self.assertIn('Claude Code', rows['builder']['note'])
        self.assertEqual(rows['builder']['fallbacks'], ['Codex'])
        self.assertFalse(next(m for m in out['models'] if m['id'] == 'deepseek-flash')['available'])


class ResolveTests(Base):
    def test_preferred_model_runs_on_its_runtime_with_real_flags(self):
        role_models.set_role(self.store, 'builder', 'preferred', 'claude-opus-5-5', 'high')
        out = role_models.resolve(self.store, 'builder', adapters=ALL, purpose='code')
        self.assertEqual((out['adapter'], out['model_arg'], out['fallback_arg'], out['effort_arg']),
                         ('claude-code', 'claude-opus-5-5', 'opus', 'high'))
        self.assertIsNone(out['why'])

    def test_auto_reasoning_sends_no_override(self):
        out = role_models.resolve(self.store, 'verifier', adapters=ALL, purpose='text')
        self.assertEqual((out['adapter'], out['model_arg'], out['effort_arg']), ('codex', 'gpt-6-astra', None))

    def test_builder_falls_back_to_codex_and_says_why(self):
        out = role_models.resolve(self.store, 'builder', adapters={'codex', 'codex-code'}, purpose='code')
        self.assertEqual((out['adapter'], out['model']), ('codex-code', 'codex'))
        self.assertIn('Claude Opus 5.5', out['why'])
        self.assertEqual(out['asked']['model'], 'claude-opus-5-5')

    def test_verifier_moves_to_another_family_when_the_builder_shares_it(self):
        out = role_models.resolve(self.store, 'verifier', adapters=ALL, purpose='text',
                                  avoid_family='openai')
        self.assertEqual(out['family'], 'anthropic')
        self.assertEqual(out['independence'], 'different')
        self.assertIn('GPT-6 Astra', role_models.MODELS[out['asked']['model']]['label'])

    def test_reduced_independence_is_recorded_not_hidden(self):
        out = role_models.resolve(self.store, 'verifier', adapters={'codex'}, purpose='text',
                                  avoid_family='openai')
        self.assertEqual(out['independence'], 'reduced')
        self.assertTrue(out['why'])

    def test_the_oracle_always_gets_a_model_when_any_can_run(self):
        # D-69: GPT-6 Astra missing -> the next available model, another family first.
        out = role_models.resolve(self.store, 'oracle', adapters={'claude', 'claude-code'},
                                  purpose='text', avoid_family='openai')
        self.assertEqual((out['adapter'], out['family'], out['independence']), ('claude', 'anthropic', 'different'))
        self.assertIn('GPT-6 Astra', out['why'])
        # Only the Builder's own family can run: it still runs, and the record says so.
        out = role_models.resolve(self.store, 'oracle', adapters={'claude'}, purpose='text',
                                  avoid_family='anthropic')
        self.assertEqual((out['adapter'], out['independence']), ('claude', 'reduced'))
        # Nothing at all can run: no adapter (the caller waits for Nick).
        out = role_models.resolve(self.store, 'oracle', adapters=set(), purpose='text', avoid_family='anthropic')
        self.assertIsNone(out['adapter'])

    def test_fixed_model_that_cannot_run_waits(self):
        role_models.set_role(self.store, 'designer', 'fixed', 'claude-fable-5-1')
        out = role_models.resolve(self.store, 'designer', adapters={'codex'}, purpose='text')
        self.assertTrue(out['waiting'])
        self.assertIn('Claude Fable 5.1', out['why'])

    def test_utility_falls_back_because_deepseek_has_no_connection(self):
        out = role_models.resolve(self.store, 'utility', adapters=ALL, purpose='text')
        self.assertIsNone(out['adapter'])
        self.assertFalse(out['waiting'])
        self.assertIn('DeepSeek', out['why'])

    def test_automatic_leaves_routing_to_kel(self):
        out = role_models.resolve(self.store, 'sentinel', adapters=ALL)
        self.assertEqual((out['adapter'], out['mode']), (None, 'AUTOMATIC'))

    def test_a_refused_model_is_skipped_for_a_day(self):
        with self.store.transaction() as db:
            db.execute("INSERT INTO staff_model_status VALUES('claude-opus-5-5','rejected','model not found',?)",
                       (__import__('time').time(),))
        out = role_models.resolve(self.store, 'builder', adapters=ALL, purpose='code')
        self.assertEqual(out['model'], 'codex')
        self.assertIn('refused', out['why'])

    def test_web_research_runs_sonnet_on_the_api_worker(self):
        out = role_models.resolve(self.store, 'discovery', adapters=ALL, purpose='web')
        self.assertEqual((out['adapter'], out['model_arg']), ('research', 'claude-sonnet-4-6'))

    def test_describe_models_that_ran(self):
        self.assertEqual(role_models.describe_model(raw='claude-opus-5-5'), ('Claude Opus 5.5', 'Opus 5.5'))
        self.assertEqual(role_models.describe_model(raw='claude-fable-5'), ('Claude Fable 5', 'Fable 5'))
        self.assertEqual(role_models.describe_model(raw='claude-sonnet-4-6'), ('Claude Sonnet', 'Sonnet'))
        self.assertEqual(role_models.describe_model(raw='gpt-6-astra'), ('GPT-6 Astra', 'GPT-6 Astra'))
        self.assertEqual(role_models.describe_model(), (None, None))


if __name__ == '__main__':
    unittest.main()
