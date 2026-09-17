"""Phase 5.4: assurance army — deterministic gating, dispatched lenses, the gate, Sentinel
rules, the Oracle harness and lens statistics.

Verification for the Phase 5.4 additions in `kel/assurance.py` (workforce-os docs 08, 09, 15
§5.4): every skipped lens carries a reason; dispatch is anti-anchored (payload = artifact +
lens + requirement only) and coverage-stated; findings dedupe/confirm through the standard
pipeline; the gate is deterministic; never-gate findings can only be waived by the user;
Sentinel (security) is mandatory for security boundaries; the Oracle must differ in family
and state coverage; lens stats track FP rates.
"""
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from kel import messages as messages_module
from kel import pods as pods_module
from kel.assurance import (GATING_FLOORS, GATE_TRIGGERS, LENSES, NEVER_GATE, ORACLE_LENS,
                           dispatch_assurance, gate, lens_stats, lenses_for, oracle_check,
                           record_finding, resolve_finding, waive_gate)
from kel.core import PolicyError, Store
from kel.evidence import write_evidence
from kel.workforce import ensure_schema as ensure_workforce_schema


def finding(lens='functional-testing', **overrides):
    body = {'schema_version': 1, 'mission_id': 'mis_' + 'a' * 8, 'task_id': 'tsk_' + 'b' * 8,
            'lens': lens, 'severity': 'blocker', 'confidence': 8, 'artifact': 'art_x',
            'location': 'loc', 'summary': 'Review found a blocking defect.',
            'evidence': 'fixture', 'fix': '', 'fingerprint': 'fp-%s' % lens, 'status': 'open',
            'by': {'lens': lens, 'model_family': 'fixture', 'assignment': 'asn_' + 'c' * 8}}
    body.update(overrides)
    return body

TASK = 'tsk_' + 'b' * 8
MISSION = 'mis_' + 'a' * 8


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)


class GatingTests(Base):
    def test_floors_and_triggers(self):
        plan = lenses_for('D2', ('security_boundary', 'user_facing'))
        for name in ('functional-testing', 'maintainability', 'security', 'adversarial', 'ux',
                     'accessibility', 'visual-design'):
            self.assertIn(name, plan['lenses'])
        self.assertEqual(plan['reasons']['security'], 'triggered by security_boundary')
        self.assertEqual(plan['reasons']['functional-testing'], 'tier floor (D2)')

    def test_d4_runs_the_never_gate_class(self):
        plan = lenses_for('D4')
        for name in NEVER_GATE:
            self.assertIn(name, plan['lenses'])

    def test_every_skipped_lens_carries_a_reason(self):
        plan = lenses_for('D1')
        self.assertEqual(len(plan['skipped']), len(LENSES) - len(plan['lenses']))
        self.assertTrue(all(plan['skipped'].values()))
        self.assertNotIn('functional-testing', plan['skipped'])

    def test_unknown_tier_and_flag_refused(self):
        with self.assertRaises(PolicyError):
            lenses_for('D9')
        with self.assertRaises(PolicyError):
            lenses_for('D2', ('mystery',))

    def test_never_gate_membership(self):
        self.assertEqual(sorted(NEVER_GATE),
                         ['adversarial', 'data-integrity', 'privacy', 'release-integrity',
                          'security'])


class DispatchTests(Base):
    def _runner(self, findings_by_lens=None, coverage='covered'):
        calls = []
        findings_by_lens = findings_by_lens or {}

        def runner(lens_name, payload):
            calls.append((lens_name, payload))
            items = [finding(lens=lens_name, fingerprint='fp-%s' % lens_name)
                     for _ in range(findings_by_lens.get(lens_name, 0))]
            return {'coverage_statement': coverage, 'findings': items}
        return runner, calls

    def test_dispatch_records_findings_and_coverage(self):
        runner, _ = self._runner({'security': 1}, coverage='threat surface enumerated')
        result = dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                                    tier='D2', flags=('security_boundary',), now=1000.0)
        self.assertIn('security', result['dispatched'])
        self.assertEqual(result['results']['security']['coverage_statement'],
                         'threat surface enumerated')
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['lens'], 'security')
        self.assertIn('quality_score', result)

    def test_dispatch_defaults_to_the_plan(self):
        runner, calls = self._runner()
        result = dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                                    tier='D2', now=1000.0)
        self.assertEqual(result['dispatched'], ['functional-testing', 'maintainability'])
        self.assertEqual([name for name, _ in calls], result['dispatched'])

    def test_payload_is_anti_anchored(self):
        runner, calls = self._runner()
        dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                           tier='D2', lenses=['functional-testing', 'maintainability',
                                             'licensing'], now=1000.0)
        _, payload = calls[0]
        self.assertEqual(set(payload), {'lens', 'artifact', 'requirement'})
        text = json.dumps(payload)
        for banned in ('packet', 'claims', 'summary', 'confidence', 'packet_outcome'):
            self.assertNotIn(banned, text)

    def test_missing_coverage_is_refused(self):
        def runner(lens_name, payload):
            return {'findings': []}

        with self.assertRaises(PolicyError):
            dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                               tier='D2', lenses=['functional-testing', 'maintainability'])

    def test_sentinel_security_lens_is_mandatory(self):
        runner, _ = self._runner()
        with self.assertRaises(PolicyError):
            dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                               tier='D2', flags=('security_boundary',),
                               lenses=['functional-testing'])
        # With the security lens present the same dispatch passes.
        dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                           tier='D2', flags=('security_boundary',),
                           lenses=['functional-testing', 'maintainability', 'security',
                                   'adversarial'],
                           now=1000.0)

    def test_unknown_lens_is_refused(self):
        runner, _ = self._runner()
        with self.assertRaises(PolicyError):
            dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                               tier='D2', lenses=['wizardry'])

    def test_multi_lens_confirmation_through_dispatch(self):
        def runner(lens_name, payload):
            if lens_name in ('security', 'maintainability'):
                return {'coverage_statement': 'ok',
                        'findings': [finding(lens=lens_name, fingerprint='fp-shared',
                                             severity='critical')]}
            return {'coverage_statement': 'ok', 'findings': []}

        result = dispatch_assurance(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                                    tier='D2', lenses=['functional-testing', 'maintainability',
                                                       'security'],
                                    now=1000.0)
        self.assertEqual(len(result['findings']), 1)
        self.assertIn('security', result['findings'][0]['confirmations'])


class GateTests(Base):
    def _rec(self, **overrides):
        return record_finding(self.store, finding(**overrides), now=1000.0)

    def test_clean_gate(self):
        result = gate(self.store, task_id=TASK)
        self.assertFalse(result['blocked'])
        self.assertFalse(result['waivable'])
        self.assertEqual(result['reasons'], [])

    def test_blocker_blocks_and_is_waivable_by_kel(self):
        self._rec(fingerprint='fp-b1')
        result = gate(self.store, task_id=TASK)
        self.assertTrue(result['blocked'])
        self.assertTrue(result['waivable'])
        self.assertTrue(result['reasons'])
        waived = waive_gate(self.store, task_id=TASK, authority='kel', rationale='triaged')
        self.assertTrue(waived['waived'])
        self.assertFalse(gate(self.store, task_id=TASK)['blocked'])

    def test_never_gate_finding_is_user_only(self):
        self._rec(lens='security', fingerprint='fp-s1')
        result = gate(self.store, task_id=TASK)
        self.assertTrue(result['blocked'])
        self.assertFalse(result['waivable'])
        self.assertEqual(len(result['never_gate_hits']), 1)
        with self.assertRaises(PolicyError):
            waive_gate(self.store, task_id=TASK, authority='kel', rationale='ship it')
        waived = waive_gate(self.store, task_id=TASK, authority='user',
                            rationale='accepted risk explicitly')
        self.assertTrue(waived['waived'])
        self.assertFalse(gate(self.store, task_id=TASK)['blocked'])

    def test_dismissed_findings_do_not_block(self):
        record = self._rec(fingerprint='fp-d1', severity='critical')
        resolve_finding(self.store, record['id'], resolution='dismissed',
                        rationale='false positive')
        self.assertFalse(gate(self.store, task_id=TASK)['blocked'])

    def test_waive_requires_a_blocked_gate_and_rationale(self):
        with self.assertRaises(PolicyError):
            waive_gate(self.store, task_id=TASK, authority='user', rationale='x')
        self._rec(fingerprint='fp-w1')
        with self.assertRaises(PolicyError):
            waive_gate(self.store, task_id=TASK, authority='user', rationale=' ')

    def test_gate_determinism(self):
        self._rec(fingerprint='fp-g1')
        self.assertEqual(gate(self.store, task_id=TASK), gate(self.store, task_id=TASK))


class OracleTests(Base):
    def _runner(self, findings_count=1, coverage='attacked'):
        calls = []

        def runner(lens_name, payload):
            calls.append((lens_name, payload))
            items = [finding(lens=ORACLE_LENS, fingerprint='fp-oracle-%d' % index,
                             severity='critical') for index in range(findings_count)]
            return {'coverage_statement': coverage, 'findings': items}
        return runner, calls

    def test_requires_a_different_family(self):
        runner, _ = self._runner()
        with self.assertRaises(PolicyError):
            oracle_check(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                         producer_provider='claude-code', oracle_provider='internal')
        ok = oracle_check(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                          producer_provider='codex', oracle_provider='claude-code', now=1000.0)
        self.assertEqual(ok['family_diversity'], 'different')
        self.assertEqual(ok['lens'], ORACLE_LENS)
        self.assertEqual(len(ok['findings']), 1)
        self.assertEqual(ok['coverage_statement'], 'attacked')

    def test_same_family_fallback_must_be_recorded(self):
        runner, _ = self._runner()
        fallback = oracle_check(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                                producer_provider='claude-code', oracle_provider='internal',
                                allow_same_family=True, now=1000.0)
        self.assertIn('unavailable', fallback['family_diversity'])

    def test_coverage_statement_required(self):
        def runner(lens_name, payload):
            return {'findings': []}

        with self.assertRaises(PolicyError):
            oracle_check(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                         producer_provider='codex', oracle_provider='claude-code')

    def test_oracle_payload_is_anti_anchored(self):
        runner, calls = self._runner()
        oracle_check(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                     producer_provider='codex', oracle_provider='claude-code', now=1000.0)
        _, payload = calls[0]
        self.assertEqual(set(payload), {'lens', 'artifact', 'requirement'})


class StatsTests(Base):
    def test_lens_stats_fp_rates(self):
        # An ordinary lens's false positive is a real false positive and is learnable.
        record = record_finding(self.store, finding(lens='maintainability', fingerprint='fp-1',
                                                   severity='critical'), now=1000.0)
        resolve_finding(self.store, record['id'], resolution='dismissed',
                        rationale='false positive')
        # An accepted risk is not a reviewer false positive, and a never-gate lens never earns
        # gating credit (doc 08 §3/§7).
        accepted = record_finding(self.store, finding(lens='security', fingerprint='fp-2',
                                                     severity='critical'), now=1001.0)
        resolve_finding(self.store, accepted['id'], resolution='accepted',
                        rationale='accepted for the pilot', authority='user')
        record_finding(self.store, finding(lens='privacy', fingerprint='fp-3',
                                           severity='critical'), now=1002.0)
        stats = lens_stats(self.store)
        self.assertEqual(stats['maintainability']['dismissed'], 1)
        self.assertEqual(stats['maintainability']['false_positive'], 1)
        self.assertEqual(stats['maintainability']['fp_rate'], 1.0)
        self.assertTrue(stats['maintainability']['learnable'])
        self.assertEqual(stats['security']['accepted'], 1)
        self.assertEqual(stats['security']['false_positive'], 0)
        self.assertIsNone(stats['security']['fp_rate'])
        self.assertFalse(stats['security']['learnable'])
        self.assertEqual(stats['privacy']['open'], 1)
        self.assertIsNone(stats['privacy']['fp_rate'])


class RemediationTests(Base):
    """Increment-16 review findings F16-1 … F16-8 — regressions that fail on `932db33`."""

    def _runner(self, findings_by_lens=None, coverage='covered'):
        calls = []
        findings_by_lens = findings_by_lens or {}

        def runner(lens_name, payload):
            calls.append((lens_name, payload))
            items = [finding(lens=lens_name, fingerprint='fp-%s' % lens_name)
                     for _ in range(findings_by_lens.get(lens_name, 0))]
            return {'coverage_statement': coverage, 'findings': items}
        return runner, calls

    def _dispatch(self, **overrides):
        runner, calls = self._runner()
        params = dict(task_id=TASK, mission_id=MISSION, artifact='art_x', runner=runner,
                      tier='D2', now=1000.0)
        params.update(overrides)
        return dispatch_assurance(self.store, **params), runner, calls

    def _evidence(self, label_contains=None):
        with contextlib.closing(self.store.connect()) as db:
            records = [dict(row) for row in db.execute('SELECT * FROM evidence_records')]
        if label_contains is not None:
            records = [item for item in records if label_contains in item['label']]
        return records

    def test_lenses_override_cannot_drop_a_mandated_lens(self):
        # F16-4: the gating plan (tier floor + flag triggers + Sentinel) is not replaceable.
        for overrides in ({'lenses': ['functional-testing']},
                          {'flags': ('security_boundary',),
                           'lenses': ['functional-testing', 'maintainability']},
                          {'tier': 'D4',
                           'lenses': ['functional-testing', 'maintainability']}):
            with self.assertRaises(PolicyError):
                self._dispatch(**overrides)

    def test_lenses_override_may_still_add_a_domain_lens(self):
        result, _, _ = self._dispatch(flags=('security_boundary',),
                                      lenses=['functional-testing', 'maintainability',
                                              'security', 'adversarial', 'licensing'])
        self.assertIn('licensing', result['dispatched'])
        self.assertIn('security', result['dispatched'])

    def test_never_gate_acceptance_requires_user_authority(self):
        # F16-1: the constitutional constant must hold on every door out of `open`.
        record = record_finding(self.store, finding(lens='security', fingerprint='fp-ng',
                                                    severity='critical'), now=1000.0)
        for authority in (None, 'kel'):
            with self.assertRaises(PolicyError):
                resolve_finding(self.store, record['id'], resolution='accepted',
                                rationale='kel would move on', authority=authority)
            with self.assertRaises(PolicyError):
                resolve_finding(self.store, record['id'], resolution='dismissed',
                                rationale='kel calls it a false positive',
                                authority=authority)
        self.assertTrue(gate(self.store, task_id=TASK)['blocked'])
        resolve_finding(self.store, record['id'], resolution='accepted',
                        rationale='the user accepts the risk', authority='user')
        self.assertFalse(gate(self.store, task_id=TASK)['blocked'])

    def test_never_gate_fix_remains_available_with_recorded_evidence(self):
        # F16-1 boundary: remediation is not acceptance, so `fixed` stays open to Kel.
        evidence = write_evidence(self.store, mission_id=MISSION, task_id=TASK,
                                  evidence_class='test_run', label='security regression',
                                  produced_by='builder', command='pytest -k security',
                                  exit_code=0, output='1 passed')
        record = record_finding(self.store, finding(lens='security', fingerprint='fp-fix',
                                                    severity='blocker'), now=1000.0)
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='fixed')
        updated = resolve_finding(self.store, record['id'], resolution='fixed',
                                  evidence_ref=evidence['id'], authority='kel')
        self.assertEqual(updated['status'], 'fixed')

    def test_coverage_statements_are_recorded_in_the_ledger(self):
        # F16-5: coverage honesty must survive the call, not only the returned dict.
        result, _, _ = self._dispatch()
        recorded = self._evidence('lens coverage:')
        self.assertEqual(sorted(item['label'] for item in recorded),
                         ['lens coverage: %s' % name for name in sorted(result['dispatched'])])
        self.assertEqual({item['evidence_class'] for item in recorded}, {'review_record'})
        self.assertTrue(all(item['output_digest'] for item in recorded))
        self.assertEqual(sorted(result['results'][name]['coverage_evidence']
                                for name in result['dispatched']),
                         sorted(item['id'] for item in recorded))

    def test_oracle_same_family_fallback_is_recorded_durably(self):
        # F16-2: the fallback must be auditable after the call returns.
        runner, _ = self._runner()
        fallback = oracle_check(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x',
                                runner=runner, producer_provider='claude-code',
                                oracle_provider='internal', allow_same_family=True, now=1000.0)
        rows = self._evidence('oracle same-family fallback')
        self.assertEqual(len(rows), 1)
        self.assertEqual(fallback['fallback_evidence'], rows[0]['id'])
        self.assertIn('unavailable', fallback['family_diversity'])
        self.assertTrue(fallback['coverage_evidence'])
        different = oracle_check(self.store, task_id=TASK, mission_id=MISSION, artifact='art_x',
                                 runner=runner, producer_provider='codex',
                                 oracle_provider='claude-code', now=1001.0)
        self.assertIsNone(different['fallback_evidence'])
        self.assertEqual(len(self._evidence('oracle same-family fallback')), 1)

    def test_mission_context_is_required_for_durable_records(self):
        runner, _ = self._runner()
        with self.assertRaises(PolicyError):
            dispatch_assurance(self.store, task_id=TASK, mission_id=None, artifact='art_x',
                               runner=runner, tier='D2')
        with self.assertRaises(PolicyError):
            oracle_check(self.store, task_id=TASK, mission_id='', artifact='art_x',
                         runner=runner, producer_provider='codex',
                         oracle_provider='claude-code')

    def test_irreversible_signal_dispatches_the_data_integrity_lens(self):
        # F16-7: a positive signal may never dispatch nothing (doc 08 §2 fail-safe).
        plan = lenses_for('D2', ('irreversible',))
        self.assertIn('data-integrity', plan['lenses'])
        self.assertEqual(plan['reasons']['data-integrity'], 'triggered by irreversible')

    def test_skip_reasons_name_the_triggering_flag(self):
        # F16-8: a skip reason must say which signal would have run the lens.
        skipped = lenses_for('D2')['skipped']
        self.assertEqual(skipped['security'],
                         'not triggered at D2 (would run for: security_boundary, '
                         'new_dependency)')
        self.assertEqual(skipped['data-integrity'],
                         'not triggered at D2 (would run for: data_migration, irreversible)')
        self.assertEqual(skipped['simplification'],
                         'not triggered at D2 (would run for: tier floor only)')

    def test_unknown_authority_is_refused(self):
        record = record_finding(self.store, finding(lens='maintainability',
                                                    fingerprint='fp-auth'), now=1000.0)
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='dismissed',
                            rationale='nope', authority='nobody')


class CarryTests(unittest.TestCase):
    def test_escalation_types_are_single_sourced(self):
        self.assertIs(messages_module.ESCALATION_TYPES, pods_module.INTERRUPTION_TYPES)
        self.assertEqual(messages_module.ESCALATION_TYPES,
                         ('BLOCKER', 'DECISION_PROPOSAL', 'REPLAN_REQUEST'))


if __name__ == '__main__':
    unittest.main()
