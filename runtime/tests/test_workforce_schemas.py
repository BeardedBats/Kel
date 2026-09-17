"""Phase 5.0 workforce schemas and registries - engine verification.

Migration 16 (v16-workforce-schemas) is additive: it creates task_contracts,
workforce_messages, findings, evidence_records and skill_packs with append-only triggers on
the three ledgers. The pure validators refuse malformed contracts, completion packets,
messages and findings; stored records are sampled for hidden reasoning and secret material;
and the lens and staffing registries match the design catalogs (workforce-os docs 03-08).
"""
import contextlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kel import workforce
from kel.assurance import (LENSES, LENS_NAMES, NEVER_GATE, ORACLE_LENS, quality_score,
                           validate_finding)
from kel.contracts import validate_completion_packet, validate_task_contract
from kel.core import PolicyError, Store
from kel.evidence import content_bound, freshness, validate_evidence, write_evidence
from kel.messages import PAIR_MESSAGE_BUDGET, TASK_MESSAGE_BUDGET, validate_message
from kel.service import Service
from kel.staffing import CAPS, FEATURES, RULES, TIERS, rule
from kel.workforce import (ID_PREFIXES, MIGRATION_VERSION, TABLES, find_unsafe, new_id,
                           register_skill_pack, validate_skill_pack)


from workforce_fixtures import EVIDENCE_ITEM, contract, packet


def message(**overrides):
    body = {
        'id': 'msg_' + 'd' * 12, 'schema_version': 1, 'mission_id': 'mis_' + 'a' * 12,
        'task_id': 'tsk_' + 'b' * 12, 'from': 'cmd', 'to': 'asn_' + 'e' * 12,
        'type': 'REQUEST', 'summary': 'Draft the export endpoint per ARCH-4.',
        'refs': ['tsk_' + 'b' * 12, 'art_arch4'], 'required_action': 'Deliver the endpoint.',
    }
    body.update(overrides)
    return body


def finding(**overrides):
    body = {
        'id': 'find_' + 'f' * 12, 'schema_version': 1, 'mission_id': 'mis_' + 'a' * 12,
        'task_id': 'tsk_' + 'b' * 12, 'lens': 'security', 'severity': 'blocker',
        'confidence': 8, 'artifact': 'art_e51', 'location': 'src/api/export.py:42',
        'summary': 'The export route can be hit without an authenticated session.',
        'evidence': 'Reproduced with a direct request against the dev server.',
        'fix': 'Require the existing session check.',
        'fingerprint': 'art_e51:src/api/export.py:42:authz',
        'status': 'open', 'by': {'lens': 'security', 'model_family': 'anthropic',
                                 'assignment': 'asn_' + 'e' * 12},
        'confirmations': [],
    }
    body.update(overrides)
    return body


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        workforce.ensure_schema(self.store)

    def table_names(self):
        with contextlib.closing(self.store.connect()) as db:
            return {row[0] for row in
                    db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def trigger_names(self):
        with contextlib.closing(self.store.connect()) as db:
            return {row[0] for row in
                    db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}


class MigrationTests(Base):
    def test_fresh_store_gets_tables_triggers_and_bookkeeping(self):
        names = self.table_names()
        for table in TABLES:
            self.assertIn(table, names)
        triggers = self.trigger_names()
        for trigger in ('task_contracts_append_only_update', 'task_contracts_append_only_delete',
                        'workforce_messages_append_only_update',
                        'workforce_messages_append_only_delete',
                        'evidence_records_append_only_update',
                        'evidence_records_append_only_delete'):
            self.assertIn(trigger, triggers)
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT name FROM schema_migrations WHERE version=?',
                             (MIGRATION_VERSION,)).fetchone()
        self.assertEqual(row['name'], 'v16-workforce-schemas')

    def test_ensure_is_idempotent_across_reopens(self):
        workforce.ensure_schema(self.store)
        workforce.ensure_schema(self.store)
        with contextlib.closing(self.store.connect()) as db:
            count = db.execute('SELECT count(*) FROM schema_migrations WHERE version=?',
                               (MIGRATION_VERSION,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_existing_store_upgrades_additively_without_losing_data(self):
        self.store.add_message('pre-existing conversation turn', role='user')
        # Simulate a database created before migration 16.
        with self.store.transaction() as db:
            for table in TABLES:
                db.execute('DROP TABLE IF EXISTS %s' % table)
            db.execute('DELETE FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,))
        self.assertNotIn('task_contracts', self.table_names())
        self.assertTrue(workforce.ensure_schema(self.store))
        self.assertIn('task_contracts', self.table_names())
        with contextlib.closing(self.store.connect()) as db:
            turns = db.execute('SELECT count(*) FROM messages').fetchone()[0]
        self.assertEqual(turns, 1)

    def test_service_startup_applies_the_migration(self):
        root = Path(self.tmp.name) / 'service-data'
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            service = Service(root)
        try:
            with contextlib.closing(service.store.connect()) as db:
                count = db.execute('SELECT count(*) FROM schema_migrations WHERE version=?',
                                   (MIGRATION_VERSION,)).fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            service.shutdown()


class ContractSchemaTests(Base):
    def test_valid_contract_passes(self):
        self.assertEqual(validate_task_contract(contract())['task_id'], 'tsk_' + 'b' * 12)

    def test_executable_oracle_is_refused(self):
        bad = contract()
        bad['acceptance_criteria'][0]['verification_method'] = 'executable_oracle'
        with self.assertRaises(PolicyError):
            validate_task_contract(bad)

    def test_authority_may_only_narrow_the_role_ceiling(self):
        widened = contract(role='verifier', authority={'class': 'leased-write',
                          'write_scope': ['src/api/export.py'], 'external_effects': 'none'})
        with self.assertRaises(PolicyError):
            validate_task_contract(widened)
        narrowed = contract(authority={'class': 'read-only', 'write_scope': [],
                                       'external_effects': 'none'})
        validate_task_contract(narrowed)

    def test_write_authority_needs_a_scope_and_read_only_must_not_have_one(self):
        with self.assertRaises(PolicyError):
            validate_task_contract(contract(authority={'class': 'leased-write',
                                                       'write_scope': [],
                                                       'external_effects': 'none'}))
        with self.assertRaises(PolicyError):
            validate_task_contract(contract(authority={'class': 'read-only',
                                                       'write_scope': ['src/x.py'],
                                                       'external_effects': 'none'}))

    def test_budget_attempts_are_capped_at_four(self):
        bad = contract()
        bad['budget']['attempts_max'] = 5
        with self.assertRaises(PolicyError):
            validate_task_contract(bad)

    def test_objective_is_capped_at_500_characters(self):
        with self.assertRaises(PolicyError):
            validate_task_contract(contract(objective='x' * 501))

    def test_unknown_role_and_unknown_field_are_refused(self):
        with self.assertRaises(PolicyError):
            validate_task_contract(contract(role='utility'))
        bad = contract()
        bad['mood'] = 'sparkling'
        with self.assertRaises(PolicyError):
            validate_task_contract(bad)

    def test_self_parent_is_refused(self):
        bad = contract()
        bad['parent_task'] = bad['task_id']
        with self.assertRaises(PolicyError):
            validate_task_contract(bad)

    def test_hidden_reasoning_and_secrets_never_validate(self):
        bad = contract()
        bad['escalation_policy'] = [{'on_blocker': 'commander', 'chain_of_thought': 'because'}]
        with self.assertRaises(PolicyError):
            validate_task_contract(bad)
        with self.assertRaises(PolicyError):
            validate_task_contract(contract(why='Use the key AKIAIOSFODNN7EXAMPLE for the bucket'))


class PacketSchemaTests(Base):
    def test_valid_packet_passes(self):
        self.assertEqual(validate_completion_packet(packet())['outcome'], 'completed')

    def test_completed_packet_with_unverified_claim_is_refused(self):
        bad = packet()
        bad['completion_claims'] = [{'claim_id': 'c1', 'status': 'uncertain',
                                     'evidence_refs': ['ev_101']}]
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)

    def test_verified_claim_needs_evidence(self):
        bad = packet()
        bad['completion_claims'] = [{'claim_id': 'c1', 'status': 'verified', 'evidence_refs': []}]
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)

    def test_claim_evidence_must_exist_in_the_packet(self):
        bad = packet()
        bad['completion_claims'] = [{'claim_id': 'c1', 'status': 'verified',
                                     'evidence_refs': ['ev_nope']}]
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)

    def test_non_completed_outcome_requires_uncertainty(self):
        with self.assertRaises(PolicyError):
            validate_completion_packet(packet(outcome='failed'))
        ok = packet(outcome='failed', unresolved_uncertainty=['The runner never started.'])
        validate_completion_packet(ok)

    def test_command_bound_evidence_needs_the_exact_command(self):
        bad = packet()
        item = dict(EVIDENCE_ITEM)
        item.pop('command')
        bad['evidence'] = [item]
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)

    def test_missing_reviewer_coverage_is_never_clean(self):
        bad = packet()
        bad['reviewer_requirements_met']['coverage_complete'] = False
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)

    def test_required_oracle_must_run(self):
        bad = packet()
        bad['required_reviewer'] = {'lenses': ['adversarial'],
                                    'independence': 'any_but_executor', 'oracle': True}
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)

    def test_completed_packet_missing_a_required_lens_is_refused(self):
        bad = packet()
        bad['reviewer_requirements_met']['lenses_run'] = []
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)
        # Partial coverage (2 required, 1 run) is refused too: the set difference, not
        # just the empty case (audit increment 8 follow-up).
        partial = packet()
        partial['required_reviewer'] = {'lenses': ['security', 'functional-testing'],
                                        'independence': 'any_but_executor', 'oracle': False}
        with self.assertRaises(PolicyError):
            validate_completion_packet(partial)
        ok = packet()
        ok['required_reviewer'] = {'lenses': ['security', 'functional-testing'],
                                   'independence': 'any_but_executor', 'oracle': False}
        ok['reviewer_requirements_met']['lenses_run'].append(
            {'lens': 'security', 'verdict': 'pass', 'coverage_statement': 'route auth checked'})
        validate_completion_packet(ok)

    def test_evidence_binds_to_at_least_one_digest(self):
        bad = packet()
        item = dict(EVIDENCE_ITEM)
        item.pop('command')
        item['class'] = 'research_source'
        item['output_digest'] = None
        item['artifact_digest'] = None
        bad['evidence'] = [item]
        with self.assertRaises(PolicyError):
            validate_completion_packet(bad)
        good = packet()
        good['evidence'] = [dict(item, output_digest='sha256:aa11')]
        validate_completion_packet(good)


class MessageSchemaTests(Base):
    def test_valid_message_passes(self):
        self.assertEqual(validate_message(message())['type'], 'REQUEST')

    def test_status_is_not_a_message_type(self):
        with self.assertRaises(PolicyError):
            validate_message(message(type='STATUS'))

    def test_messages_need_refs_and_required_action(self):
        with self.assertRaises(PolicyError):
            validate_message(message(refs=[]))
        bad = message()
        del bad['required_action']
        with self.assertRaises(PolicyError):
            validate_message(bad)

    def test_staffing_request_states_its_budget_impact(self):
        with self.assertRaises(PolicyError):
            validate_message(message(type='STAFFING_REQUEST'))
        validate_message(message(type='STAFFING_REQUEST',
                                 budget_impact={'tokens': 40000, 'wallclock_s': 900}))

    def test_caps_and_unknown_fields(self):
        with self.assertRaises(PolicyError):
            validate_message(message(summary='x' * 401))
        with self.assertRaises(PolicyError):
            validate_message(message(details='y' * 2001))
        bad = message()
        bad['priority'] = 'urgent'
        with self.assertRaises(PolicyError):
            validate_message(bad)

    def test_budget_constants_match_the_design(self):
        self.assertEqual(PAIR_MESSAGE_BUDGET, 6)
        self.assertEqual(TASK_MESSAGE_BUDGET, 12)


class FindingSchemaTests(Base):
    def test_valid_finding_passes(self):
        self.assertEqual(validate_finding(finding())['lens'], 'security')

    def test_unknown_lens_and_severity_are_refused(self):
        with self.assertRaises(PolicyError):
            validate_finding(finding(lens='wizardry'))
        with self.assertRaises(PolicyError):
            validate_finding(finding(severity='warn'))

    def test_confidence_is_bounded_and_dismissal_needs_a_reason(self):
        with self.assertRaises(PolicyError):
            validate_finding(finding(confidence=11))
        with self.assertRaises(PolicyError):
            validate_finding(finding(status='dismissed'))
        validate_finding(finding(status='dismissed',
                                 dismissal_reason='Not reachable from the shipped route.'))

    def test_advisory_findings_are_info_only(self):
        validate_finding(finding(lens='simplification', severity='info', advisory=True))
        with self.assertRaises(PolicyError):
            validate_finding(finding(lens='simplification', severity='blocker', advisory=True))


class RegistryTests(Base):
    def test_lens_catalog_matches_the_design(self):
        self.assertEqual(len(LENSES), 15)
        self.assertEqual(len(set(LENS_NAMES)), 15)
        for name in NEVER_GATE:
            self.assertIn(name, LENS_NAMES)
        self.assertIn(ORACLE_LENS, NEVER_GATE)
        self.assertEqual(quality_score(criticals=2, infos=4), 4.0)

    def test_staffing_rules_table_is_complete(self):
        self.assertEqual([item['id'] for item in RULES],
                         ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10'])
        self.assertEqual(rule('R8')['kind'], 'hard')
        self.assertEqual(CAPS['workers_max'], 6)
        self.assertEqual(len(FEATURES), 12)
        self.assertEqual(len(TIERS), 5)
        with self.assertRaises(PolicyError):
            rule('R99')

    def test_id_vocabulary(self):
        self.assertTrue(new_id('ev_').startswith('ev_'))
        self.assertIn('asn_', ID_PREFIXES)
        with self.assertRaises(PolicyError):
            new_id('bad')

    def test_skill_pack_registry_validates_and_freezes_versions(self):
        pack = {'name': 'python-fastapi', 'description': 'FastAPI patterns for Kel missions',
                'version': '2.1.0', 'owner': 'kel-core', 'triggers': ['fastapi', 'api'],
                'authority_hint': 'leased-write'}
        validate_skill_pack(pack)
        first = register_skill_pack(self.store, pack)
        self.assertEqual(first['state'], 'registered')
        again = register_skill_pack(self.store, pack)
        self.assertEqual(again['state'], 'existing')
        with self.assertRaises(PolicyError):
            register_skill_pack(self.store, dict(pack, description='Changed without a version bump'))
        with self.assertRaises(PolicyError):
            validate_skill_pack(dict(pack, owner=None))
        with self.assertRaises(PolicyError):
            validate_skill_pack(dict(pack, description='x' * 501))


class EvidenceWriterTests(Base):
    def test_write_evidence_computes_digests_and_persists(self):
        record = write_evidence(self.store, mission_id='mis_' + 'a' * 12,
                                task_id='tsk_' + 'b' * 12, evidence_class='test_run',
                                label='export tests', produced_by='run_8841',
                                command='python -m pytest tests/test_export.py -q',
                                exit_code=0, output='12 passed',
                                artifact_digest='sha256:77bb')
        self.assertTrue(record['output_digest'].startswith('sha256:'))
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM evidence_records WHERE id=?',
                             (record['id'],)).fetchone()
        self.assertEqual(row['label'], 'export tests')
        self.assertEqual(row['exit_code'], 0)

    def test_command_bound_classes_demand_the_exact_command(self):
        with self.assertRaises(PolicyError):
            write_evidence(self.store, mission_id='mis_' + 'a' * 12, task_id='tsk_' + 'b' * 12,
                           evidence_class='test_run', label='x', produced_by='run_1')
        review = write_evidence(self.store, mission_id='mis_' + 'a' * 12,
                                task_id='tsk_' + 'b' * 12, evidence_class='review_record',
                                label='review', produced_by='run_2', output='reviewed')
        self.assertIsNone(review['command'])
        self.assertTrue(review['output_digest'].startswith('sha256:'))

    def test_freshness_and_content_binding(self):
        record = write_evidence(self.store, mission_id='mis_' + 'a' * 12,
                                task_id='tsk_' + 'b' * 12, evidence_class='review_record',
                                label='review', produced_by='run_2', ran_at=1000.0,
                                freshness_window=10, artifact_digest='sha256:77bb')
        self.assertTrue(freshness(record, now=1000.0 + 599))
        self.assertFalse(freshness(record, now=1000.0 + 601))
        self.assertTrue(content_bound(record, 'sha256:77bb'))
        self.assertFalse(content_bound(record, 'sha256:other'))
        # The real read path returns sqlite3.Row (no .get); the helpers must accept it.
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM evidence_records WHERE id=?',
                             (record['id'],)).fetchone()
        self.assertFalse(hasattr(row, 'get'))
        self.assertTrue(freshness(row, now=1000.0 + 599))
        self.assertFalse(freshness(row, now=1000.0 + 601))
        self.assertTrue(content_bound(row, 'sha256:77bb'))

    def test_malformed_records_are_refused(self):
        with self.assertRaises(PolicyError):
            validate_evidence({'schema_version': 1})
        with self.assertRaises(PolicyError):
            write_evidence(self.store, mission_id='mis_' + 'a' * 12, task_id='tsk_' + 'b' * 12,
                           evidence_class='review_record', label='no binding', produced_by='run_3')


class ImmutabilityTests(Base):
    def insert_contract(self):
        with contextlib.closing(self.store.connect()) as db:
            db.execute('INSERT INTO task_contracts(contract_id,task_id,version,mission_id,'
                       'parent_task,digest,data,created) VALUES(?,?,?,?,?,?,?,?)',
                       ('ctr_1', 'tsk_1', 1, 'mis_1', None, 'sha256:aa', '{}', 1000.0))

    def test_task_contracts_are_append_only(self):
        self.insert_contract()
        with contextlib.closing(self.store.connect()) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE task_contracts SET data='{}' WHERE contract_id='ctr_1'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM task_contracts WHERE contract_id='ctr_1'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO task_contracts(contract_id,task_id,version,mission_id,'
                           'parent_task,digest,data,created) VALUES(?,?,?,?,?,?,?,?)',
                           ('ctr_2', 'tsk_1', 1, 'mis_1', None, 'sha256:bb', '{}', 1001.0))

    def test_messages_and_evidence_are_append_only(self):
        with contextlib.closing(self.store.connect()) as db:
            db.execute('INSERT INTO workforce_messages(id,schema_version,mission_id,task_id,'
                       'sender,recipient,type,summary,refs,required_action,at) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       ('msg_1', 1, 'mis_1', 'tsk_1', 'cmd', 'asn_1', 'REQUEST', 's',
                        '["tsk_1"]', 'a', 1000.0))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE workforce_messages SET summary='t' WHERE id='msg_1'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM workforce_messages WHERE id='msg_1'")
        record = write_evidence(self.store, mission_id='mis_1', task_id='tsk_1',
                                evidence_class='review_record', label='r', produced_by='run_1',
                                output='ok')
        with contextlib.closing(self.store.connect()) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('DELETE FROM evidence_records WHERE id=?', (record['id'],))

    def test_findings_keep_workflow_state(self):
        with contextlib.closing(self.store.connect()) as db:
            db.execute('INSERT INTO findings(id,schema_version,mission_id,task_id,lens,severity,'
                       'confidence,summary,fingerprint,status,reporter,created,updated) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       ('find_1', 1, 'mis_1', 'tsk_1', 'security', 'blocker', 8, 's',
                        'fp', 'open', '{}', 1000.0, 1000.0))
            db.execute("UPDATE findings SET status='confirmed' WHERE id='find_1'")
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT status FROM findings WHERE id='find_1'").fetchone()
        self.assertEqual(row['status'], 'confirmed')


class SafetySamplingTests(Base):
    def test_stored_records_never_carry_hidden_reasoning_or_secrets(self):
        register_skill_pack(self.store, {'name': 'demo', 'description': 'demo pack',
                                         'version': '1.0.0', 'owner': 'kel-core'})
        write_evidence(self.store, mission_id='mis_1', task_id='tsk_1',
                       evidence_class='review_record', label='review', produced_by='run_1',
                       output='all green')
        with contextlib.closing(self.store.connect()) as db:
            db.execute('INSERT INTO workforce_messages(id,schema_version,mission_id,task_id,'
                       'sender,recipient,type,summary,refs,required_action,at) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       ('msg_s', 1, 'mis_1', 'tsk_1', 'cmd', 'asn_1', 'EVIDENCE', 'green',
                        '["ev_1"]', 'none', 1000.0))
            db.execute('INSERT INTO findings(id,schema_version,mission_id,task_id,lens,severity,'
                       'confidence,summary,fingerprint,status,reporter,created,updated) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       ('find_s', 1, 'mis_1', 'tsk_1', 'security', 'info', 5, 'clean sweep',
                        'fp', 'open', '{}', 1000.0, 1000.0))
            db.execute('INSERT INTO task_contracts(contract_id,task_id,version,mission_id,'
                       'parent_task,digest,data,created) VALUES(?,?,?,?,?,?,?,?)',
                       ('ctr_s', 'tsk_s', 1, 'mis_1', None, 'sha256:aa', '{}', 1000.0))
        with contextlib.closing(self.store.connect()) as db:
            for table in TABLES:
                for row in db.execute('SELECT * FROM %s' % table):
                    for key in row.keys():
                        value = row[key]
                        if isinstance(value, str) and value[:1] in ('{', '['):
                            try:
                                value = json.loads(value)
                            except ValueError:
                                pass
                        self.assertEqual(find_unsafe(value, path='%s.%s' % (table, key)), [])
        # The scanner itself must catch a planted violation.
        self.assertTrue(find_unsafe({'chain_of_thought': 'x'}))
        self.assertTrue(find_unsafe('AKIAIOSFODNN7EXAMPLE'))


if __name__ == '__main__':
    unittest.main()
