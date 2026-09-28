"""Default Kel model + per-conversation override tests (docs/basic-ux-sweep/04_MODEL_UX.md).

The choice is a soft routing preference: Auto keeps the deterministic order, a preferred provider
is tried first, and every existing fallback remains. These tests are provider-independent.
"""
import sys
import tempfile
import unittest
from pathlib import Path

from kel.core import PolicyError, Store
from kel.model_prefs import ModelPrefs, MODEL_LABELS, PROVIDER_LABELS, model_label, provider_label
from kel.providers import DEFINITIONS
from kel.router import Candidate, select


class ModelPrefsBase(unittest.TestCase):
    def setUp(self):
        sys.stdout.reconfigure(errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.prefs = ModelPrefs(self.store)

    def tearDown(self):
        self.tmp.cleanup()


class MigrationTests(ModelPrefsBase):
    def test_migration_is_recorded_once(self):
        import contextlib
        ModelPrefs(self.store)
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT version, name FROM schema_migrations WHERE version=13').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'v15-model-prefs')


class DefaultChoiceTests(ModelPrefsBase):
    def test_default_roundtrip_and_clear(self):
        self.assertIsNone(self.prefs.default())
        self.prefs.set_default('deepseek', 'deepseek-flash')
        self.assertEqual(self.prefs.default()['provider'], 'deepseek')
        self.prefs.clear('default')
        self.assertIsNone(self.prefs.default())

    def test_conversation_override_wins(self):
        self.prefs.set_default('deepseek', 'deepseek-flash')
        self.prefs.set_conversation('c1', 'claude-code', 'claude-native')
        snap = self.prefs.snapshot('c1')
        self.assertEqual(snap['conversation']['provider'], 'claude-code')
        self.assertEqual(snap['default']['provider'], 'deepseek')
        self.prefs.clear_conversation('c1')
        self.assertIsNone(self.prefs.snapshot('c1')['conversation'])

    def test_unknown_choices_are_refused_plainly(self):
        with self.assertRaises(PolicyError):
            self.prefs.set_default('not-a-provider', None)
        with self.assertRaises(PolicyError):
            self.prefs.set_default('deepseek', 'not-a-model')


class ResolutionTests(ModelPrefsBase):
    def test_resolve_falls_back_to_default_without_submissions_table(self):
        self.prefs.set_default('codex', 'codex-native')
        resolved = ModelPrefs.resolve_for_job(self.store, 'job-missing')
        self.assertEqual(resolved['provider'], 'codex')

    def test_resolve_prefers_conversation_override(self):
        import contextlib
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS submissions('
                       'id TEXT PRIMARY KEY, conversation_id TEXT, text TEXT, state TEXT, error TEXT, '
                       'job_id TEXT, created REAL)')
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
                       ('s1', 'c9', 'hello', 'DISPATCHED', None, 'job-9', 1.0))
        self.prefs.set_default('deepseek', 'deepseek-flash')
        self.prefs.set_conversation('c9', 'internal', 'claude-sonnet-4-6')
        resolved = ModelPrefs.resolve_for_job(self.store, 'job-9')
        self.assertEqual(resolved['provider'], 'internal')
        self.assertEqual(resolved['model'], 'claude-sonnet-4-6')


class RouterPreferenceTests(unittest.TestCase):
    def test_prefer_moves_provider_first(self):
        candidates = [Candidate(name='alpha', cost=1), Candidate(name='beta', cost=2)]
        route = select(candidates, prefer='beta')
        self.assertEqual(route['selected'], 'beta')

    def test_prefer_keeps_fallbacks_when_unusable(self):
        candidates = [Candidate(name='alpha', cost=1), Candidate(name='beta', cost=2, quota=0)]
        route = select(candidates, prefer='beta')
        self.assertEqual(route['selected'], 'alpha')
        self.assertIn('beta', route['excluded'])

    def test_auto_without_preference_keeps_cost_order(self):
        candidates = [Candidate(name='alpha', cost=1), Candidate(name='beta', cost=2)]
        self.assertEqual(select(candidates)['selected'], 'alpha')


class LabelTests(unittest.TestCase):
    def test_plain_labels_cover_every_definition(self):
        for item in DEFINITIONS:
            self.assertTrue(provider_label(item['id']))
            for model in item.get('models', ()):
                self.assertTrue(model_label(model['id']))

    def test_labels_never_leak_raw_ids(self):
        self.assertEqual(provider_label('claude-code'), 'Claude')
        self.assertEqual(model_label('deepseek-v4-pro'), 'DeepSeek V4 Pro')
        self.assertEqual(provider_label('unknown-id'), 'unknown-id')


class PayloadContractTests(unittest.TestCase):
    """The renderer reads the stored choice and the provider listing from one payload.

    `action='get'` used to answer without `providers`; the Kel model control then crashed on
    `state.providers.map(...)` and React unmounted the whole page (settings · Model and any
    chat header went blank). The contract is: both actions always carry the listing.
    """

    def setUp(self):
        import os
        sys.stdout.reconfigure(errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
        for key in ('ANTHROPIC_API_KEY', 'KEL_INTERNAL_MODEL'):
            os.environ.pop(key, None)
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        os.environ['KEL_REVIEWER'] = 'none'
        self.tmp = tempfile.TemporaryDirectory()
        from kel.service import Service
        self.service = Service(self.tmp.name)

    def tearDown(self):
        self.service.shutdown()
        self.tmp.cleanup()

    def test_get_carries_the_provider_listing(self):
        state = self.service._model_action({'action': 'get'})
        self.assertIn('providers', state)
        self.assertIsInstance(state['providers'], list)
        self.assertTrue(state['providers'])
        for row in state['providers']:
            self.assertIn('id', row)
            self.assertTrue(row['label'])
            self.assertIn('available', row)
            for option in row['options']:
                self.assertTrue(option['label'])

    def test_get_and_list_answer_the_same_shape(self):
        got = self.service._model_action({'action': 'get'})
        listed = self.service._model_action({'action': 'list'})
        self.assertEqual(sorted(got), sorted(listed))
        self.assertEqual([row['id'] for row in got['providers']],
                         [row['id'] for row in listed['providers']])

    def test_the_older_default_is_retired_for_kels_model(self):
        # D-73.3 / FN-06: Kel's model is the Kel role. A catalog choice sent as the old default is
        # written to the Kel role; a provider-only choice is refused plainly; a clear still works.
        from kel.core import PolicyError
        from kel.role_models import setting
        self.service._model_action({'action': 'set_default', 'choice': {'model': 'deepseek-flash'}})
        self.assertEqual(setting(self.service.store, 'kel')['model'], 'deepseek-flash')
        self.assertIsNone(self.service._model_action({'action': 'get'})['default'])
        with self.assertRaises(PolicyError):
            self.service._model_action({'action': 'set_default', 'choice': {'provider': 'codex', 'model': None}})
        self.service._model_action({'action': 'set_default', 'choice': None})
        self.assertIsNone(self.service._model_action({'action': 'get'})['default'])


class SavedChoiceRoutingTests(unittest.TestCase):
    """CH-2: a saved catalog choice ('claude-code', 'codex') reaches the engine adapter it names."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from kel.core import Store
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_catalog_ids_map_to_engine_adapters(self):
        from kel.model_prefs import adapter_names, runtime_model
        self.assertEqual(adapter_names('claude-code'), ('claude-code', 'claude'))
        self.assertEqual(adapter_names('codex'), ('codex-code', 'codex'))
        self.assertEqual(adapter_names(None), ())
        self.assertIsNone(runtime_model('claude-native'))
        self.assertEqual(runtime_model('claude-sonnet-4-6'), 'claude-sonnet-4-6')

    def test_a_saved_claude_choice_routes_a_document_job_to_claude(self):
        from kel.engine import Engine, compile_document
        from kel.native import FixtureAdapter
        import json
        with self.store.transaction() as db:  # Auto alone would pick the cheaper Codex
            for name, cost in (('codex', 0.01), ('claude', 1.0)):
                db.execute('INSERT INTO providers VALUES(?,?)',
                           (name, json.dumps({'failures': 0, 'circuit_until': 0, 'quota': None, 'cost': cost})))
        ModelPrefs(self.store).set_default('claude-code', 'claude-native')
        engine = Engine(self.store, {'codex': FixtureAdapter(delay=5), 'claude': FixtureAdapter(delay=5)})
        try:
            job = engine.submit(compile_document('Write a short plain note about soil.'))
            engine.tick()
            milestone = self.store.get(job)['milestones']['document']
            self.assertEqual(milestone['provider'], 'claude')
            self.assertIsNone(milestone['model'], 'a catalog-only model id is not a runtime model')
        finally:
            engine.control(job, 'cancel')
            engine.close()


if __name__ == '__main__':
    unittest.main()
