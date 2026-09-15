"""V1.4 Gate 6: provider registry, state model, readiness preflight, credential metadata (PROV-*)."""
import contextlib
import json
import os
import tempfile
import unittest
from unittest import mock

from kel.core import PolicyError, Store, encode
from kel.providers import DEFINITIONS, Providers, capabilities, definition, models


class ProviderBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.providers = Providers(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def authenticate_api(self, provider='deepseek'):
        self.providers.set_credential_metadata(
            provider, ['api_key'], 'kel:provider:%s:api_key' % provider)

    def seed_state(self, provider, **fields):
        """Write the engine's provider state row the way provider_outcome/telemetry would."""
        with self.store.transaction() as db:
            row = db.execute('SELECT data FROM providers WHERE id=?', (provider,)).fetchone()
            data = json.loads(row['data']) if row else {}
            data.update(fields)
            db.execute(
                'INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                (provider, encode(data)))

    def status(self, provider):
        return self.providers.status(provider)


class RegistryTests(ProviderBase):
    def test_definitions_cover_the_required_providers(self):
        self.assertEqual([item['id'] for item in DEFINITIONS],
                         ['claude-code', 'codex', 'internal', 'deepseek'])
        self.assertEqual(definition('codex')['class'], 'native-cli')
        self.assertEqual(definition('codex')['auth_mode'], 'subscription')
        self.assertEqual(definition('deepseek')['base_url'], 'https://api.deepseek.com/v1')
        self.assertEqual(definition('deepseek')['auth_mode'], 'api_key')
        with self.assertRaises(PolicyError):
            definition('nope')

    def test_capability_matrix(self):
        self.assertEqual([m['id'] for m in models('deepseek', 'text')],
                         ['deepseek-chat', 'deepseek-reasoner'])
        self.assertEqual(models('internal', 'vision')[0]['id'], 'claude-sonnet-4-6')
        self.assertEqual(models('deepseek', 'vision'), [])
        self.assertIn('tools', capabilities('claude-code'))

    def test_status_reports_registry_fields(self):
        entry = self.status('deepseek')
        self.assertEqual(entry['label'], 'DeepSeek API')
        self.assertEqual(entry['auth_mode'], 'api_key')
        self.assertEqual([m['id'] for m in entry['models']],
                         ['deepseek-chat', 'deepseek-reasoner'])
        self.assertIn(entry['status'],
                      ('installed_not_authenticated', 'healthy', 'quota_not_reported'))


class StateModelTests(ProviderBase):
    def test_cli_missing_is_not_installed(self):
        with mock.patch('kel.providers.shutil.which', return_value=None):
            entry = self.status('codex')
        self.assertEqual(entry['status'], 'not_installed')
        self.assertFalse(entry['installed'])
        self.assertEqual(entry['note'], 'not on PATH')

    def test_cli_present_without_session_needs_sign_in(self):
        with mock.patch('kel.providers.shutil.which', return_value='C:/bin/codex.exe'), \
                mock.patch.dict(os.environ, {'CODEX_HOME': os.path.join(self.tmp.name, 'nope')}):
            entry = self.status('codex')
        self.assertEqual(entry['status'], 'installed_not_authenticated')
        self.assertEqual(entry['note'], 'sign-in needed')

    def test_cli_session_present_is_usable(self):
        home = os.path.join(self.tmp.name, 'codex-home')
        os.makedirs(home, exist_ok=True)
        with open(os.path.join(home, 'auth.json'), 'w', encoding='utf-8') as handle:
            handle.write('{}')
        with mock.patch('kel.providers.shutil.which', return_value='C:/bin/codex.exe'), \
                mock.patch.dict(os.environ, {'CODEX_HOME': home}):
            entry = self.status('codex')
        self.assertTrue(entry['authenticated'])
        self.assertEqual(entry['note'], 'CLI session present')
        self.assertIn(entry['status'], ('healthy', 'quota_not_reported'))

    def test_api_key_states(self):
        self.assertEqual(self.status('deepseek')['status'], 'installed_not_authenticated')
        self.authenticate_api('deepseek')
        self.assertEqual(self.status('deepseek')['note'], 'stored credential metadata present')
        self.assertIn(self.status('deepseek')['status'], ('healthy', 'quota_not_reported'))

    def test_circuit_makes_provider_degraded(self):
        self.authenticate_api('deepseek')
        self.seed_state('deepseek', failures=3, circuit_until=9999999999.0)
        entry = self.status('deepseek')
        self.assertEqual(entry['status'], 'degraded')
        self.assertEqual(entry['failures'], 3)

    def test_quota_present_and_exhausted_and_not_reported(self):
        self.authenticate_api('deepseek')
        self.seed_state('deepseek', quota=42, quota_unit='percent_remaining',
                        quota_source='account/rateLimits/read')
        entry = self.status('deepseek')
        self.assertEqual(entry['quota'], 42)
        self.assertIn(entry['status'], ('healthy', 'quota'))

        self.seed_state('deepseek', quota=0)
        self.assertEqual(self.status('deepseek')['status'], 'unavailable')

        self.seed_state('deepseek', quota=None)
        self.assertEqual(self.status('deepseek')['status'], 'quota_not_reported')

    def test_all_status_covers_the_registry(self):
        rows = self.providers.all_status()
        self.assertEqual([row['provider'] for row in rows],
                         [item['id'] for item in DEFINITIONS])


class ReadinessTests(ProviderBase):
    def test_no_usable_provider_records_every_reason(self):
        with mock.patch('kel.providers.shutil.which', return_value=None), mock.patch.dict(
                os.environ, {'ANTHROPIC_API_KEY': '', 'DEEPSEEK_API_KEY': ''}, clear=False):
            result = self.providers.readiness('text', prefer='')
        self.assertIsNone(result['chosen'])
        self.assertTrue(result['reasons'])
        self.assertIn('No usable provider', result['reason'])

    def test_preferred_provider_is_selected(self):
        self.authenticate_api('deepseek')
        result = self.providers.readiness('text', prefer='deepseek')
        self.assertEqual(result['chosen']['provider'], 'deepseek')
        self.assertEqual(result['chosen']['model'], 'deepseek-chat')
        self.assertIn('Preferred provider selected', result['reason'])

    def test_fallback_is_explained(self):
        with mock.patch('kel.providers.shutil.which', return_value=None):
            self.authenticate_api('deepseek')
            self.authenticate_api('internal')
            self.seed_state('internal', failures=2, circuit_until=9999999999.0)
            result = self.providers.readiness('text', prefer='internal')
        self.assertEqual(result['chosen']['provider'], 'deepseek')
        self.assertIn('Fell back to deepseek', result['reason'])
        self.assertTrue([reason for reason in result['reasons'] if 'unusable' in reason])

    def test_capability_without_any_provider(self):
        result = self.providers.readiness('vision', prefer='')
        chosen = result['chosen']['provider'] if result['chosen'] else None
        self.assertIn(chosen, (None, 'internal'))


class CredentialMetadataTests(ProviderBase):
    def test_metadata_round_trip_never_stores_values(self):
        saved = self.providers.set_credential_metadata(
            'deepseek', ['api_key'], 'kel:provider:deepseek:api_key')
        self.assertEqual(saved['fields'], ['api_key'])
        rows = self.providers.credential_metadata('deepseek')
        self.assertEqual(len(rows), 1)
        self.assertEqual(sorted(rows[0].keys()),
                         ['created', 'credential_ref', 'fields', 'provider', 'updated'])
        self.assertNotIn('value', json.dumps(rows))
        self.assertNotIn('sk-', json.dumps(rows))

    def test_empty_reference_is_refused(self):
        with self.assertRaises(PolicyError):
            self.providers.set_credential_metadata('deepseek', ['api_key'], '')
        with self.assertRaises(PolicyError):
            self.providers.set_credential_metadata('deepseek', ['  '], 'ref')

    def test_delete_removes_metadata_only(self):
        self.authenticate_api('deepseek')
        self.assertEqual(self.providers.delete_credential_metadata('deepseek')['deleted'], True)
        self.assertEqual(self.providers.credential_metadata('deepseek'), [])
        self.assertEqual(self.status('deepseek')['status'], 'installed_not_authenticated')

    def test_usage_observations_are_ordered(self):
        self.providers.observe('deepseek', {'event': 'one'})
        self.providers.observe('deepseek', {'event': 'two'})
        rows = self.providers.usage('deepseek', limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['data']['event'], 'two')


class EnvelopeAndMigrationTests(ProviderBase):
    def test_apply_envelope(self):
        listed = self.providers.apply({'action': 'list'})
        self.assertEqual(len(listed['providers']), len(DEFINITIONS))
        self.assertEqual(self.providers.apply({'action': 'status', 'provider': 'codex'})['provider'],
                         'codex')
        self.assertIn('chosen', self.providers.apply({'action': 'readiness'}))
        self.assertIn('credentials', self.providers.apply({'action': 'credentials'}))
        with self.assertRaises(PolicyError):
            self.providers.apply({'action': 'nope'})

    def test_migration_recorded_and_idempotent(self):
        Providers(self.store)
        with contextlib.closing(self.store.connect()) as db:
            versions = [row['version'] for row in db.execute(
                'SELECT version FROM schema_migrations ORDER BY version')]
        self.assertIn(7, versions)
        Providers(self.store)
        with contextlib.closing(self.store.connect()) as db:
            tables = [row['name'] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertIn('provider_credentials', tables)
        self.assertIn('provider_usage', tables)


if __name__ == '__main__':
    unittest.main()
