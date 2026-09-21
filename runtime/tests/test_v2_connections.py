"""Connections (V2.0 / V2-01 / V2-02): one product term, one store, one place to manage them.

The pins here are about product shape, not plumbing. A Connection is what Nick adds when he wants Kel
to be able to use a service: a name he recognises, where its API lives, how the credential is
presented, and whether a credential is actually stored. It is deliberately NOT a plugin, not a
per-service app/database/worker/workflow, and never a place a secret value can land — the engine keeps
metadata and a pointer, and the OS-backed store keeps the value.

V2-02 adds Test Connection: one request to the service through the single choke point, and an honest
result. The tests below keep that honest — a refusal is a result, an unreachable address is not a
failed credential, and the value never appears in the store, the note or the answer.
"""
import ast
import base64
import contextlib
import http.server
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from kel.connection_actions import action, actions, actions_for
from kel.connection_framework import request_policy, template, templates
from kel.connection_services import catalogue, entry
from kel.connections import (AUTH_METHODS, CREDENTIAL_REF_PREFIX, KINDS, MAX_ANSWER_BYTES,
                             MAX_REDIRECTS, REQUEST_ATTEMPTS, RETRY_AFTER_CAP, RETRY_STATUSES,
                             STATES, TEST_TIMEOUT, Connections, ensure_schema, perform_request,
                             scrub, slug)
from kel.core import PolicyError, Store

EXPECTED_COLUMNS = {
    'id', 'name', 'kind', 'base_url', 'auth_method', 'auth_header', 'docs_url', 'test_endpoint',
    'notes', 'credential_ref', 'credential_fields', 'created', 'updated',
    # V2-02: what the last check of the service found. Still no column a value could live in.
    'last_test_at', 'last_test_state', 'last_test_status', 'last_test_ms', 'last_test_note',
    # V2-03: the word a service wants in front of its credential.
    'auth_prefix',
    # V2-04b: the account sign-in state — plain words, granted scopes, expiry, provider. No value.
    'auth_state', 'auth_scopes', 'auth_expires', 'oauth_provider',
}

MODULE = Path(__file__).resolve().parents[1] / 'kel' / 'connections.py'
# The part of a catalogue row that is a Connection field; the rest is what Nick is asked to go and get.
CATALOGUE_FIELDS = ('name', 'kind', 'base_url', 'auth_method', 'auth_header', 'auth_prefix',
                    'docs_url', 'test_endpoint')


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

    def test_a_check_travels_through_the_api_without_the_value(self):
        # V2-02: the shell sends the credential for this one request; the answer is all that comes back.
        service = LocalService()
        self.addCleanup(service.stop)
        service.status = 401
        self.action({'action': 'save', 'name': 'Stripe', 'base_url': service.base})
        result = self.action({'action': 'test', 'id': 'stripe',
                              'credentials': {'api_key': 'sk_live_secret_value'}})
        self.assertEqual(result['last_test_state'], 'refused')
        self.assertEqual(result['last_test_status'], 401)
        self.assertNotIn('sk_live_secret_value', json.dumps(result))
        with self.assertRaises(PolicyError):
            self.action({'action': 'test', 'id': 'nope', 'credentials': {}})

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


class KnownServiceTests(unittest.TestCase):
    """V2-03 — the services Kel already knows about are data, and nothing else."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(self.tmp.name)
        self.connections = Connections(self.store)
        self.service = LocalService()
        self.addCleanup(self.service.stop)

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_the_catalogue_is_data_with_no_per_service_behaviour(self):
        source = (Path(__file__).resolve().parents[1] / 'kel'
                  / 'connection_services.py').read_text(encoding='utf-8')
        # Two functions: hand out the list, hand out one row. Anything else here would be a per-service
        # code path, which is exactly what this program forbids.
        self.assertEqual(source.count('\ndef '), 2)
        self.assertNotIn('if service_id', source)
        self.assertNotIn('import', source.split('"""')[2])

    def test_every_known_service_is_a_usable_connection_row(self):
        rows = catalogue()
        self.assertEqual([row['id'] for row in rows],
                         ['github', 'stripe', 'figma', 'clickup', 'discord', 'google-drive',
                          'pitcher-list', 'raptive'])
        self.assertEqual([row['name'] for row in rows],
                         ['GitHub', 'Stripe', 'Figma', 'ClickUp', 'Discord', 'Google Drive',
                          'Pitcher List', 'Raptive'])
        for row in rows:
            self.assertIn(row['kind'], KINDS)
            self.assertIn(row['auth_method'], AUTH_METHODS)
            self.assertIn(row['source'], ('documented', 'assumed', 'to-confirm'))
            self.assertTrue(row['credential'], row['id'])
            for key in ('base_url', 'docs_url', 'test_endpoint'):
                value = row[key]
                if value:
                    self.assertTrue(value.startswith('http://') or value.startswith('https://'),
                                    '%s.%s' % (row['id'], key))

    def test_a_known_service_can_be_added_as_a_connection_unchanged(self):
        row = entry('github')
        saved = self.connections.save(**{key: row[key] for key in CATALOGUE_FIELDS if key in row})
        self.assertEqual(saved['id'], 'github')
        self.assertEqual(saved['auth_prefix'], 'Bearer ')
        self.assertEqual(saved['test_endpoint'], 'https://api.github.com/user')
        self.assertIsNone(entry('nope'))

    def test_a_known_service_added_by_name_gets_the_id_the_catalogue_uses(self):
        # Nothing has to carry the id around: adding "Pitcher List" by name already produces
        # `pitcher-list`, so the catalogue and the store cannot disagree about which connection it is.
        for row in catalogue():
            connection = self.connections.save(row['name'])
            self.assertEqual(connection['id'], row['id'], row['name'])
            self.connections.remove(connection['id'])

    def test_the_declared_prefix_is_what_the_service_gets(self):
        # GitHub and Discord want a scheme in front of the value; ClickUp and Figma want it untouched.
        for service, prefix in (('github', 'Bearer '), ('discord', 'Bot '), ('clickup', ''),
                                ('figma', '')):
            row = entry(service)
            connection = self.connections.save(row['name'], kind=row['kind'],
                                               auth_method=row['auth_method'],
                                               auth_header=row['auth_header'],
                                               auth_prefix=row['auth_prefix'],
                                               base_url=self.service.base)
            self.service.seen.clear()
            self.connections.test(connection['id'], {'api_key': 'the-credential'})
            header = (self.service.seen[0]['headers'].get('authorization')
                      or self.service.seen[0]['headers'].get('x-figma-token'))
            self.assertEqual(header, prefix + 'the-credential', service)
            self.connections.remove(connection['id'])

    def test_a_prefix_is_not_added_twice(self):
        self.connections.save('Discord', kind='bot', auth_method='header',
                              auth_header='Authorization', auth_prefix='Bot ',
                              base_url=self.service.base)
        self.connections.test('discord', {'api_key': 'Bot the-credential'})
        self.assertEqual(self.service.seen[0]['headers'].get('authorization'), 'Bot the-credential')

    def test_a_connection_without_a_declared_prefix_still_works_out_its_own(self):
        # The old behaviour, kept: a bare value in Authorization gets a scheme, a custom header does not.
        self.connections.save('Anything', auth_method='header', auth_header='X-Api-Key',
                              base_url=self.service.base)
        self.assertEqual(self.connections.get('anything')['auth_prefix'], None)
        self.connections.test('anything', {'api_key': 'the-credential'})
        self.assertEqual(self.service.seen[0]['headers'].get('x-api-key'), 'the-credential')

    def test_an_absurd_prefix_is_refused(self):
        with self.assertRaises(PolicyError) as caught:
            self.connections.save('Anything', auth_prefix='x' * 41)
        self.assertIn('prefix is too long', str(caught.exception))

    def test_the_separator_after_a_prefix_survives_being_saved(self):
        # 'Bearer ' is a word and a separator: trimming it away would send 'Bearerthe-credential'.
        self.assertEqual(self.connections.save('Anything', auth_prefix='  Bearer   ')['auth_prefix'],
                         'Bearer ')
        self.assertEqual(self.connections.save('Other', auth_prefix='   ')['auth_prefix'], '')


class FrameworkPolicyTests(unittest.TestCase):
    """V2-04 — the framework's standard parts: the retry policy and the three templates."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(self.tmp.name)
        # No real waiting in a test: the pauses are counted instead.
        self.pauses = []
        self.connections = Connections(self.store, attempts=3, sleep=self.pauses.append)
        self.service = LocalService()
        self.addCleanup(self.service.stop)

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_a_busy_service_is_asked_again(self):
        self.connections.save('Stripe', base_url=self.service.base)
        self.service.statuses = [503, 200]
        result = self.connections.test('stripe', {'api_key': 'the-credential'})
        self.assertEqual(result['last_test_state'], 'ok')
        self.assertEqual(result['last_test_status'], 200)
        self.assertIn('Kel tried 2 times.', result['last_test_note'])
        self.assertEqual(len(self.service.seen), 2)
        self.assertEqual(len(self.pauses), 1)

    def test_saying_no_is_an_answer_and_is_never_retried(self):
        # A 401 and a 404 are information. Asking again would just be rude, and would raise the chance of
        # a service locking the credential out.
        for status in (401, 403, 404):
            self.connections.save('Service %d' % status, base_url=self.service.base)
            self.service.seen.clear()
            self.service.statuses = []
            self.service.status = status
            result = self.connections.test('service-%d' % status, {'api_key': 'the-credential'})
            self.assertEqual(len(self.service.seen), 1, status)
            self.assertNotIn('tried', result['last_test_note'], status)
        self.assertEqual(self.pauses, [])

    def test_kel_stops_after_the_policy_allows(self):
        self.connections.save('Stripe', base_url=self.service.base)
        self.service.statuses = [500, 500, 500, 200]
        result = self.connections.test('stripe', {'api_key': 'the-credential'})
        self.assertEqual(result['last_test_state'], 'error')
        self.assertIn('Kel tried 3 times.', result['last_test_note'])
        self.assertEqual(len(self.service.seen), 3)
        # The fourth answer was never collected: Kel gave up where the policy says it gives up.
        self.assertEqual(self.service.statuses, [200])

    def test_a_dropped_connection_is_tried_again(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            closed = 'http://127.0.0.1:%d' % probe.getsockname()[1]
        with self.assertRaises(urllib.error.URLError):
            perform_request(closed, {}, timeout=1, attempts=3, sleep=self.pauses.append)
        self.assertEqual(len(self.pauses), 2)

    def test_the_policy_is_the_same_one_for_every_service(self):
        policy = request_policy()
        self.assertEqual(policy['attempts'], REQUEST_ATTEMPTS)
        self.assertEqual(policy['timeout'], TEST_TIMEOUT)
        self.assertEqual(policy['retry_statuses'], list(RETRY_STATUSES))
        self.assertIn('never keeps the body', policy['note'])

    def test_the_three_templates_are_the_three_kinds_of_credential(self):
        rows = templates()
        self.assertEqual([row['id'] for row in rows], list(KINDS))
        for row in rows:
            self.assertTrue(row['label'] and row['hint'] and row['credential_field'])
            self.assertTrue(row['check'].endswith('.'))
        self.assertEqual(template('oauth')['credential_field'], 'access_token')
        self.assertIsNone(template('nope'))

    def test_the_framework_knows_no_service(self):
        source = (Path(__file__).resolve().parents[1] / 'kel'
                  / 'connection_framework.py').read_text(encoding='utf-8')
        for service in ('stripe', 'github', 'figma', 'discord', 'clickup', 'raptive', 'pitcher',
                        'wordpress', 'drive'):
            self.assertNotIn(service, source.lower())


class ActionTests(unittest.TestCase):
    """V2-04 — what Kel can do with a service: rows of data, one request, an honest answer."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(self.tmp.name)
        self.pauses = []
        self.connections = Connections(self.store, attempts=2, sleep=self.pauses.append)
        self.service = LocalService()
        self.addCleanup(self.service.stop)
        self.connections.save('Local Service', base_url=self.service.base)

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _one_action(self, **over):
        """A single action row, as if the catalogue had it — used to exercise the machinery honestly."""
        row = {'id': 'local-read', 'service': '', 'name': 'Read something', 'description': 'd',
               'method': 'GET', 'path': '/something', 'params': (), 'returns': 'r',
               'mutating': False, 'source': 'documented'}
        row.update(over)
        return patch('kel.connection_actions.ACTIONS', (row,))

    def test_the_action_catalogue_is_data_belonging_to_known_services(self):
        rows = actions()
        self.assertEqual(len({row['id'] for row in rows}), len(rows))
        services = {row['id'] for row in catalogue()}
        for row in rows:
            self.assertIn(row['service'], services, row['id'])
            self.assertEqual(row['method'], 'GET', row['id'])
            self.assertTrue(row['path'].startswith('/'), row['id'])
            self.assertIn(row['source'], ('documented', 'assumed'), row['id'])
            # Nothing Kel can do today changes anything in Nick's account.
            self.assertFalse(row['mutating'], row['id'])
        self.assertEqual([row['id'] for row in actions_for('github')],
                         ['github-whoami', 'github-notifications'])
        self.assertIsNone(action('nope'))

    def test_a_read_action_hands_back_the_answer_and_records_no_payload(self):
        self.service.answer_text = '{"login": "nick", "plan": "pro"}'
        with self._one_action():
            result = self.connections.run('local-service', 'local-read')
        self.assertEqual(result['state'], 'ok')
        self.assertEqual(result['status'], 200)
        self.assertEqual(result['result'], {'login': 'nick', 'plan': 'pro'})
        self.assertEqual(self.service.seen[0]['path'], '/something')
        # What is written down is the fact of the call: a domain, a status, a duration — no path, no query,
        # no answer.
        history = self.connections.events('local-service')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['action'], 'local-read')
        self.assertEqual(history[0]['domain'], '127.0.0.1:%d' % int(self.service.base.rsplit(':', 1)[1]))
        self.assertNotIn('/something', json.dumps(history))
        self.assertNotIn('nick', json.dumps(history))

    def test_a_text_answer_comes_back_as_text(self):
        self.service.answer_text = 'not json at all'
        with self._one_action():
            result = self.connections.run('local-service', 'local-read')
        self.assertEqual(result['result'], 'not json at all')

    def test_an_answer_can_never_carry_a_credential_back_into_the_records(self):
        self.service.answer_text = '{"echo": "the-credential"}'
        with self._one_action():
            result = self.connections.run('local-service', 'local-read',
                                         {'api_key': 'the-credential'})
        self.assertNotIn('the-credential', json.dumps(result))
        self.assertEqual(result['result'], {'echo': '[redacted]'})
        self.assertEqual(self.service.seen[0]['headers'].get('authorization'),
                         'Bearer the-credential')

    def test_an_action_for_another_service_is_refused(self):
        self.connections.save('Stripe')
        with self.assertRaises(PolicyError) as caught:
            self.connections.run('stripe', 'github-whoami')
        self.assertIn('not for Stripe', str(caught.exception))
        with self.assertRaises(PolicyError):
            self.connections.run('local-service', 'nope')

    def test_something_that_changes_anything_waits_for_nick(self):
        # No catalogue row is mutating today, so this proves the gate with one that is.
        with self._one_action(method='POST', mutating=True, name='Change something'):
            with self.assertRaises(PolicyError) as caught:
                self.connections.run('local-service', 'local-read')
            self.assertIn('Kel asks first', str(caught.exception))
            self.assertEqual(self.service.seen, [])
            done = self.connections.run('local-service', 'local-read', confirmed=True)
        self.assertEqual(done['state'], 'ok')
        self.assertEqual(self.service.seen[0]['method'], 'POST')

    def test_an_action_needs_an_address_to_go_to(self):
        self.connections.save('Nowhere')
        with self._one_action(service='nowhere'):
            with self.assertRaises(PolicyError) as caught:
                self.connections.run('nowhere', 'local-read')
        self.assertIn('API address', str(caught.exception))

    def test_a_busy_service_is_asked_again_by_an_action_too(self):
        self.service.statuses = [503, 200]
        with self._one_action():
            result = self.connections.run('local-service', 'local-read')
        self.assertEqual(result['state'], 'ok')
        self.assertEqual(result['attempts'], 2)
        self.assertIn('Kel tried 2 times.', result['note'])

    def test_the_history_is_the_access_trail(self):
        with self._one_action():
            self.connections.run('local-service', 'local-read')
            self.connections.run('local-service', 'local-read')
        history = self.connections.events(limit=1)
        self.assertEqual(len(history), 1)
        self.assertEqual(len(self.connections.events()), 2)
        self.assertEqual(self.connections.events('other'), [])


class LocalService:
    """A stand-in for a service on this computer only.

    Everything these tests do stays on the loopback interface: the suite never needs the internet, and
    a real service is never contacted.
    """

    def __init__(self):
        self.status = 200
        # A scripted run of answers: the next request takes the next status, so a busy service can be
        # stood up honestly (503 then 200) instead of mocked.
        self.statuses = []
        self.delay = 0.0
        # What the service says back. Answer bodies are only read by actions. 
        self.answer_text = ''
        # V2-04 hardening knobs: a redirect target, and a Retry-After header on 429/503 answers.
        self.location = ''
        self.retry_after = ''
        self.seen = []
        probe = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def _respond(self, method):
                probe.seen.append({'method': method,
                                   'path': self.path,
                                   'headers': {k.lower(): v for k, v in self.headers.items()}})
                if probe.delay:
                    time.sleep(probe.delay)
                payload = probe.answer_text.encode('utf-8')
                code = probe.statuses.pop(0) if probe.statuses else probe.status
                self.send_response(code)
                if probe.retry_after and code in (429, 503):
                    self.send_header('Retry-After', str(probe.retry_after))
                if probe.location and 300 <= code < 400:
                    self.send_header('Location', probe.location)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except ConnectionError:
                    # The client gave up (the timeout test) before the answer was written. Nothing to do.
                    pass

            def do_GET(self):
                self._respond('GET')

            def do_POST(self):
                self._respond('POST')

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base(self):
        return 'http://127.0.0.1:%d' % self.server.server_address[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def closed_port():
    """An address nothing is listening on — the honest 'could not reach it' case."""
    with contextlib.closing(socket.socket()) as probe:
        probe.bind(('127.0.0.1', 0))
        return 'http://127.0.0.1:%d' % probe.getsockname()[1]


class ConnectionTestRequestTests(unittest.TestCase):
    """V2-02 — Test Connection: one request, an honest result, and never a stored value."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(self.tmp.name)
        self.connections = Connections(self.store)
        self.service = LocalService()
        self.addCleanup(self.service.stop)
        self.value = 'sk_live_CONNECTION_test_value'

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def add(self, **extra):
        fields = {'name': 'Stripe', 'base_url': self.service.base, 'auth_method': 'header',
                  'auth_header': 'X-Api-Key'}
        fields.update(extra)
        return self.connections.save(**fields)

    def test_the_engine_has_exactly_one_place_that_calls_a_service(self):
        source = (Path(__file__).resolve().parents[1] / 'kel' / 'connections.py').read_text(encoding='utf-8')
        # One opener, built once (V2-04 hardening put the redirect bound inside it): every request
        # still goes through perform_request, and nothing else opens a URL.
        self.assertEqual(source.count('build_opener('), 1)
        self.assertEqual(source.count('.open('), 1)
        self.assertIn('def perform_request(', source)

    def test_a_service_that_answers_is_recorded_as_ok_with_its_status(self):
        self.add(test_endpoint=self.service.base + '/v1/account')
        result = self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(result['last_test_state'], 'ok')
        self.assertEqual(result['last_test_status'], 200)
        self.assertGreaterEqual(result['last_test_ms'], 0)
        self.assertEqual(result['last_test_note'], 'The service answered 200.')
        self.assertIsNotNone(result['last_test_at'])
        self.assertEqual(self.service.seen[0]['path'], '/v1/account')

    def test_the_credential_reaches_the_service_and_is_written_nowhere(self):
        self.add(test_endpoint=self.service.base + '/v1/account', auth_header='X-Api-Key')
        result = self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(self.service.seen[0]['headers'].get('x-api-key'), self.value)
        self.assertNotIn(self.value, json.dumps(result))
        with contextlib.closing(self.store.connect()) as db:
            row = dict(db.execute('SELECT * FROM connections').fetchone())
        self.assertNotIn(self.value, json.dumps(row))
        self.assertNotIn(self.value, row['last_test_note'] or '')

    def test_a_bearer_connection_sends_a_bearer_token(self):
        self.add(auth_method='bearer', auth_header='', test_endpoint=self.service.base + '/me')
        self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(self.service.seen[0]['headers'].get('authorization'),
                         'Bearer ' + self.value)

    def test_a_plain_authorization_header_gets_the_scheme_but_a_custom_header_does_not(self):
        self.add(auth_method='header', auth_header='Authorization', test_endpoint=self.service.base)
        self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(self.service.seen[0]['headers'].get('authorization'),
                         'Bearer ' + self.value)
        self.connections.save('Stripe', connection_id='stripe', auth_method='header',
                              auth_header='Authorization', base_url=self.service.base)
        self.connections.test('stripe', {'api_key': 'Bearer ' + self.value})
        self.assertEqual(self.service.seen[1]['headers'].get('authorization'),
                         'Bearer ' + self.value)

    def test_a_query_connection_puts_the_credential_in_the_address(self):
        self.add(auth_method='query', auth_header='key', test_endpoint=self.service.base + '/v1/posts')
        self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(self.service.seen[0]['path'], '/v1/posts?key=' + self.value)
        self.assertEqual(self.service.seen[0]['headers'].get('authorization'), None)

    def test_a_basic_connection_needs_both_halves_and_says_so(self):
        self.add(auth_method='basic', auth_header='', test_endpoint=self.service.base)
        with self.assertRaises(PolicyError) as caught:
            self.connections.test('stripe', {'api_key': self.value})
        self.assertIn('username and the password', str(caught.exception))
        self.assertEqual(self.service.seen, [])
        self.assertIsNone(self.connections.get('stripe')['last_test_at'])
        result = self.connections.test('stripe', {'username': 'nick', 'password': self.value})
        self.assertEqual(result['last_test_state'], 'ok')
        self.assertEqual(self.service.seen[0]['headers'].get('authorization'),
                         'Basic ' + base64.b64encode(('nick:' + self.value).encode()).decode())

    def test_a_refusal_is_a_result_not_an_error(self):
        self.add(test_endpoint=self.service.base)
        self.connections.set_credential('stripe', ['api_key'], 'kel:connection:stripe')
        self.service.status = 401
        result = self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(result['last_test_state'], 'refused')
        self.assertEqual(result['last_test_status'], 401)
        self.assertIn('refused the credential', result['last_test_note'])
        # A refused check does not quietly change what the connection claims to hold.
        self.assertTrue(result['has_credentials'])
        self.assertEqual(result['state'], 'ready')

    def test_the_other_answers_are_named_honestly(self):
        self.add(test_endpoint=self.service.base)
        for status, state in ((404, 'not_found'), (429, 'busy'), (500, 'error'), (418, 'error')):
            self.service.status = status
            result = self.connections.test('stripe', {'api_key': self.value})
            self.assertEqual((result['last_test_state'], result['last_test_status']), (state, status))
            self.assertIn(str(status), result['last_test_note'])

    def test_a_closed_port_is_unreachable_not_a_failed_credential(self):
        self.add(test_endpoint=closed_port())
        result = self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(result['last_test_state'], 'unreachable')
        self.assertIsNone(result['last_test_status'])
        self.assertEqual(result['last_test_note'], 'Kel could not reach that address.')

    def test_a_slow_service_times_out(self):
        self.connections = Connections(self.store, timeout=0.5)
        self.add(test_endpoint=self.service.base)
        self.service.delay = 1.5
        result = self.connections.test('stripe', {'api_key': self.value})
        self.assertEqual(result['last_test_state'], 'timeout')
        self.assertEqual(result['last_test_note'],
                         'The service did not answer within 0.5 seconds.')

    def test_a_connection_with_no_address_is_refused_before_anything_is_sent(self):
        self.connections.save('Stripe')
        with self.assertRaises(PolicyError) as caught:
            self.connections.test('stripe', {'api_key': self.value})
        self.assertIn('test address or an API address', str(caught.exception))
        self.assertFalse(self.connections.get('stripe')['can_test'])
        self.assertEqual(self.service.seen, [])

    def test_a_connection_without_a_credential_still_asks_the_service(self):
        self.add(test_endpoint=self.service.base)
        self.service.status = 401
        result = self.connections.test('stripe', {})
        self.assertEqual(self.service.seen[0]['headers'].get('x-api-key'), None)
        self.assertEqual(result['last_test_state'], 'refused')
        self.assertEqual(self.connections.get('stripe')['state'], 'needs_credentials')

    def test_a_value_that_somehow_reached_a_sentence_is_scrubbed(self):
        sentence = 'The service refused %s for key %s.' % (self.value, self.value)
        cleaned = scrub(sentence, {'api_key': self.value})
        self.assertNotIn(self.value, cleaned)
        self.assertEqual(cleaned, 'The service refused [redacted] for key [redacted].')
        self.assertEqual(scrub('nothing to hide', {}), 'nothing to hide')

    def test_testing_a_connection_that_does_not_exist_is_a_plain_refusal(self):
        with self.assertRaises(PolicyError) as caught:
            self.connections.test('nope', {})
        self.assertIn('not found', str(caught.exception))


class ExecutionHardeningTests(unittest.TestCase):
    """V2-04 priority 2 — the choke point's own rules: redirects, Retry-After, network authority,
    honest truncation. Everything runs against a loopback stand-in; nothing here leaves the computer."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(self.tmp.name)
        self.pauses = []
        self.connections = Connections(self.store, attempts=3, sleep=self.pauses.append)
        self.service = LocalService()
        self.addCleanup(self.service.stop)

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_a_redirect_chain_is_bounded(self):
        # A service that redirects to itself forever: the opener stops a few hops in (urllib's own
        # default would allow ten) and the answer is reported honestly — a 302, not a hang.
        self.service.status = 302
        self.service.location = self.service.base + '/again'
        status, final, tried, elapsed, _body = perform_request(self.service.base + '/start', {},
                                                               timeout=5, attempts=1,
                                                               sleep=self.pauses.append)
        self.assertEqual(status, 302)
        self.assertGreaterEqual(len(self.service.seen), 2)
        self.assertLess(len(self.service.seen), 10, 'the bound must be far below urllib’s default')

    def test_a_service_may_ask_for_a_short_pause_and_get_it(self):
        self.connections.save('Stripe', base_url=self.service.base)
        self.service.statuses = [503, 200]
        self.service.retry_after = '1'
        result = self.connections.test('stripe', {'api_key': 'the-credential'})
        self.assertEqual(result['last_test_state'], 'ok')
        self.assertEqual(self.pauses, [1.0])          # the service's own number, honoured

    def test_an_absurd_pause_is_capped(self):
        self.connections.save('Stripe', base_url=self.service.base)
        self.service.statuses = [429, 200]
        self.service.retry_after = '600'
        result = self.connections.test('stripe', {'api_key': 'the-credential'})
        self.assertEqual(result['last_test_state'], 'ok')
        self.assertEqual(self.pauses, [RETRY_AFTER_CAP])   # bounded, never a ten-minute wait

    def test_a_network_rule_stops_a_request_before_it_leaves(self):
        self.connections.save('Stripe', base_url=self.service.base)
        refusal = 'Kel is not allowed to reach that address right now.'
        with patch.object(sys.modules['kel.connections'], 'NETWORK_RULES',
                          lambda host: (False, refusal)):
            with self.assertRaises(PolicyError) as caught:
                self.connections.test('stripe', {'api_key': 'the-credential'})
        self.assertEqual(str(caught.exception), refusal)
        self.assertEqual(self.service.seen, [], 'a refused host must never be contacted')

    def test_a_rule_source_that_cannot_answer_fails_closed(self):
        self.connections.save('Stripe', base_url=self.service.base)
        with patch.object(sys.modules['kel.connections'], 'NETWORK_RULES',
                          lambda host: (_ for _ in ()).throw(RuntimeError('no rules'))):
            with self.assertRaises(PolicyError) as caught:
                self.connections.test('stripe', {'api_key': 'the-credential'})
        self.assertIn('could not check its network rules', str(caught.exception))
        self.assertEqual(self.service.seen, [])

    def test_an_answer_beyond_the_reading_cap_says_it_was_cut_short(self):
        self.connections.save('GitHub', base_url=self.service.base, auth_method='bearer')
        self.service.answer_text = 'x' * (MAX_ANSWER_BYTES + 5000)
        done = self.connections.run('github', 'github-whoami', credentials={'api_key': 'the-credential'})
        self.assertEqual(done['state'], 'ok')
        self.assertIn('cut short', done['note'])
        self.assertLessEqual(len(done['result'] or ''), MAX_ANSWER_BYTES)


if __name__ == '__main__':
    unittest.main()
