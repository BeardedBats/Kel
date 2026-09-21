"""Connections (V2.0 / V2-01): one product term, one store, one place to manage them.

The pins here are about product shape, not plumbing. A Connection is what Nick adds when he wants Kel
to be able to use a service: a name he recognises, where its API lives, how the credential is
presented, and whether a credential is actually stored. It is deliberately NOT a plugin, not a
per-service app/database/worker/workflow, and never a place a secret value can land — the engine keeps
metadata and a pointer, and the OS-backed store keeps the value.
"""
import ast
import contextlib
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.connections import (AUTH_METHODS, CREDENTIAL_REF_PREFIX, KINDS, STATES, Connections,
                            ensure_schema, slug)
from kel.core import PolicyError, Store

EXPECTED_COLUMNS = {
    'id', 'name', 'kind', 'base_url', 'auth_method', 'auth_header', 'docs_url', 'test_endpoint',
    'notes', 'credential_ref', 'credential_fields', 'created', 'updated',
}

MODULE = Path(__file__).resolve().parents[1] / 'kel' / 'connections.py'


class ConnectionCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.connections = Connections(self.store)

    def add(self, name='Stripe', **extra):
        return self.connections.save(name, **extra)

    # -- schema / shape ---------------------------------------------------------------------------
    def test_schema_keeps_metadata_only(self):
        with contextlib.closing(self.store.connect()) as db:
            columns = {row[1] for row in db.execute('PRAGMA table_info(connections)')}
        self.assertEqual(columns, EXPECTED_COLUMNS)
        # Nothing here can hold a credential value: no secret/value/token/password column exists.
        for banned in ('value', 'secret', 'token', 'password', 'api_key', 'key', 'payload'):
            self.assertNotIn(banned, columns)

    def test_ensure_schema_is_idempotent(self):
        self.assertFalse(ensure_schema(self.store))
        self.assertEqual(self.connections.list()['connections'], [])

    def test_no_service_is_built_in(self):
        # V2-03 adds the personal services; the model itself must stay service-agnostic — the same
        # reason there is no per-service app, database, worker or workflow. Docstrings and comments
        # may name an example; nothing in the code may branch on a service.
        tree = ast.parse(MODULE.read_text(encoding='utf-8'))
        code = MODULE.read_text(encoding='utf-8')
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                text = ast.get_docstring(node, clean=False)
                if text:
                    code = code.replace(text, '')
        code = '\n'.join(line for line in code.splitlines() if not line.strip().startswith('#'))
        for service in ('stripe', 'github', 'figma', 'discord', 'clickup', 'raptive', 'pitcher',
                        'wordpress', 'drive'):
            self.assertNotIn(service, code.lower())
        for seeding in ('builtin', 'install_', 'seed'):
            self.assertNotIn(seeding, code.lower())
        self.assertEqual(self.connections.list()['counts'],
                         {'ready': 0, 'needs_credentials': 0})

    def test_kinds_are_the_three_framework_templates(self):
        self.assertEqual(KINDS, ('api_key', 'oauth', 'bot'))
        self.assertEqual(AUTH_METHODS, ('header', 'bearer', 'query', 'basic'))
        self.assertEqual(STATES, ('ready', 'needs_credentials'))

    def test_slug_is_readable_and_stable(self):
        self.assertEqual(slug('Pitcher List'), 'pitcher-list')
        self.assertEqual(slug('  GitHub  '), 'github')
        self.assertEqual(slug('!!!'), 'service')

    # -- save -------------------------------------------------------------------------------------
    def test_save_derives_a_readable_id_and_reports_state_honestly(self):
        item = self.add()
        self.assertEqual(item['id'], 'stripe')
        self.assertEqual(item['name'], 'Stripe')
        self.assertEqual(item['state'], 'needs_credentials')
        self.assertFalse(item['has_credentials'])
        self.assertEqual(item['kind'], 'api_key')
        self.assertEqual(item['auth_method'], 'header')
        self.assertEqual(item['auth_header'], 'Authorization')

    def test_save_requires_a_service_name(self):
        with self.assertRaises(PolicyError) as caught:
            self.connections.save('   ')
        self.assertIn('service name', str(caught.exception))

    def test_oauth_defaults_to_a_bearer_credential(self):
        item = self.add('Google Drive', kind='oauth')
        self.assertEqual(item['auth_method'], 'bearer')
        self.assertEqual(item['auth_header'], '')

    def test_addresses_must_be_real_http_addresses(self):
        for bad in ('api.stripe.com', 'javascript:alert(1)', 'ftp://api.stripe.com',
                    'data:text/plain,hello'):
            with self.subTest(bad=bad):
                with self.assertRaises(PolicyError):
                    self.add('Stripe', base_url=bad)
        item = self.add('Stripe', base_url='https://api.stripe.com/v1')
        self.assertEqual(item['base_url'], 'https://api.stripe.com/v1')

    def test_unknown_kind_and_method_are_refused(self):
        with self.assertRaises(PolicyError):
            self.add('Stripe', kind='plugin')
        with self.assertRaises(PolicyError):
            self.add('Stripe', auth_method='magic')

    def test_two_services_with_the_same_name_stay_distinct(self):
        first = self.add('Stripe')
        second = self.add('stripe')
        self.assertEqual([first['id'], second['id']], ['stripe', 'stripe-2'])

    def test_editing_keeps_the_id_and_never_drops_the_credential_pointer(self):
        created = self.add('Stripe', base_url='https://api.stripe.com/v1')
        ready = self.connections.set_credential(
            created['id'], ['api_key'], CREDENTIAL_REF_PREFIX + 'stripe:api_key')
        self.assertEqual(ready['state'], 'ready')
        edited = self.connections.save('Stripe Payments', connection_id=created['id'],
                                       kind='api_key', base_url='https://api.stripe.com/v2',
                                       notes='used by the payouts recipe')
        self.assertEqual(edited['id'], created['id'])
        self.assertEqual(edited['name'], 'Stripe Payments')
        self.assertEqual(edited['base_url'], 'https://api.stripe.com/v2')
        self.assertTrue(edited['has_credentials'])
        self.assertEqual(edited['credential_fields'], ['api_key'])

    def test_editing_an_unknown_connection_is_refused(self):
        with self.assertRaises(PolicyError):
            self.connections.save('Stripe', connection_id='nope')

    def test_notes_are_capped_rather_than_silently_truncated(self):
        with self.assertRaises(PolicyError):
            self.add('Stripe', notes='x' * 2001)
        self.assertEqual(self.add('Stripe', notes='  payouts only  ')['notes'], 'payouts only')

    # -- credential metadata (never values) --------------------------------------------------------
    def test_a_credential_is_recorded_as_a_pointer_and_field_names_only(self):
        item = self.add('Stripe')
        recorded = self.connections.set_credential(
            item['id'], ['api_key'], CREDENTIAL_REF_PREFIX + 'stripe:api_key')
        self.assertEqual(recorded['credential_ref'], 'kel:connection:stripe:api_key')
        self.assertEqual(recorded['credential_fields'], ['api_key'])
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM connections WHERE id=?', (item['id'],)).fetchone()
        # The stored pointer is a pointer: the value Nick pasted appears nowhere in the engine.
        self.assertNotIn('sk_live', str(dict(row)))

    def test_a_value_offered_as_the_pointer_is_refused(self):
        item = self.add('Stripe')
        with self.assertRaises(PolicyError) as caught:
            self.connections.set_credential(item['id'], ['api_key'], 'sk_live_1234567890')
        self.assertIn('never the credential itself', str(caught.exception))

    def test_credential_metadata_needs_a_field_name_and_a_known_connection(self):
        item = self.add('Stripe')
        with self.assertRaises(PolicyError):
            self.connections.set_credential(item['id'], [], CREDENTIAL_REF_PREFIX + 'stripe:api_key')
        with self.assertRaises(PolicyError):
            self.connections.set_credential('nope', ['api_key'], CREDENTIAL_REF_PREFIX + 'nope:api_key')

    def test_removing_a_credential_returns_the_connection_to_needs_credentials(self):
        item = self.add('Stripe')
        self.connections.set_credential(item['id'], ['api_key'],
                                        CREDENTIAL_REF_PREFIX + 'stripe:api_key')
        cleared = self.connections.delete_credential(item['id'])
        self.assertFalse(cleared['has_credentials'])
        self.assertEqual(cleared['state'], 'needs_credentials')
        self.assertEqual(cleared['credential_fields'], [])
        # The row itself survives: losing a credential is not losing the service.
        self.assertEqual(self.connections.get('stripe')['name'], 'Stripe')

    # -- list / get / remove -----------------------------------------------------------------------
    def test_list_is_readable_and_counts_states(self):
        self.add('Stripe')
        drive = self.add('Google Drive', kind='oauth')
        self.connections.set_credential(drive['id'], ['client_id', 'client_secret'],
                                        CREDENTIAL_REF_PREFIX + 'google-drive:client_id')
        listed = self.connections.list()
        self.assertEqual([item['name'] for item in listed['connections']],
                         ['Google Drive', 'Stripe'])
        self.assertEqual(listed['counts'], {'ready': 1, 'needs_credentials': 1})
        self.assertEqual(listed['kinds'], list(KINDS))
        self.assertEqual(listed['connections'][0]['kind_label'], 'Account authorization')

    def test_remove_forgets_the_service_and_its_metadata(self):
        item = self.add('Stripe')
        self.connections.set_credential(item['id'], ['api_key'],
                                        CREDENTIAL_REF_PREFIX + 'stripe:api_key')
        self.assertEqual(self.connections.remove('stripe'), {'id': 'stripe', 'removed': True})
        self.assertEqual(self.connections.list()['connections'], [])
        with self.assertRaises(PolicyError):
            self.connections.get('stripe')
        with self.assertRaises(PolicyError):
            self.connections.remove('stripe')

    def test_unknown_connection_reads_one_plain_sentence(self):
        with self.assertRaises(PolicyError) as caught:
            self.connections.get('ghost')
        self.assertEqual(str(caught.exception), 'That connection was not found.')


class ConnectionServiceCase(unittest.TestCase):
    """The shell's door: /api/connections, with the same one-sentence error contract."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            from kel.service import Service
            self.service = Service(self.tmp.name)
        self.addCleanup(self.service.shutdown)

    def action(self, payload):
        return self.service.action('/api/connections', payload)

    def test_a_service_can_be_added_read_and_removed_through_the_api(self):
        added = self.action({'action': 'save', 'name': 'Pitcher List', 'kind': 'api_key',
                             'base_url': 'https://pitcherlist.com/wp-json', 'auth_method': 'header',
                             'auth_header': 'X-Api-Key', 'docs_url': 'https://pitcherlist.com/docs'})
        self.assertEqual(added['id'], 'pitcher-list')
        self.assertEqual(added['auth_header'], 'X-Api-Key')
        self.assertEqual(self.action({'action': 'get', 'id': 'pitcher-list'})['name'], 'Pitcher List')
        self.assertEqual(self.action({'action': 'list'})['counts'],
                         {'ready': 0, 'needs_credentials': 1})
        self.assertTrue(self.action({'action': 'remove', 'id': 'pitcher-list'})['removed'])

    def test_credential_metadata_travels_through_the_api_without_the_value(self):
        self.action({'action': 'save', 'name': 'Stripe'})
        recorded = self.action({'action': 'set_credential', 'id': 'stripe', 'fields': ['api_key'],
                                'credential_ref': 'kel:connection:stripe:api_key'})
        self.assertEqual(recorded['state'], 'ready')
        self.assertNotIn('value', recorded)
        cleared = self.action({'action': 'delete_credential', 'id': 'stripe'})
        self.assertEqual(cleared['state'], 'needs_credentials')

    def test_refusals_stay_plain_sentences_and_unknown_actions_are_closed(self):
        with self.assertRaises(PolicyError) as caught:
            self.action({'action': 'save', 'name': ''})
        self.assertIn('service name', str(caught.exception))
        with self.assertRaises(PolicyError):
            self.action({'action': 'get'})
        with self.assertRaises(PolicyError):
            self.action({'action': 'run'})

    def test_the_engine_has_no_value_getter_for_a_connection(self):
        """No engine route returns a credential value — values are the shell's custody alone."""
        source = (Path(__file__).resolve().parents[1] / 'kel' / 'service.py').read_text(encoding='utf-8')
        block = source.split('# -- Connections (V2.0)')[1].split('def _vetting_all_answered')[0]
        self.assertNotIn('get_credential', block)
        self.assertNotIn('decrypt', block)
        self.assertNotRegex(block, re.compile(r"'value'"))


if __name__ == '__main__':
    unittest.main()
