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
        result = dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                                    tier='D2', flags=('security_boundary',), now=1000.0)
        self.assertIn('security', result['dispatched'])
        self.assertEqual(result['results']['security']['coverage_statement'],
                         'threat surface enumerated')
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['lens'], 'security')
        self.assertIn('quality_score', result)

    def test_dispatch_defaults_to_the_plan(self):
        runner, calls = self._runner()
        result = dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                                    tier='D2', now=1000.0)
        self.assertEqual(result['dispatched'], ['functional-testing', 'maintainability'])
        self.assertEqual([name for name, _ in calls], result['dispatched'])

    def test_payload_is_anti_anchored(self):
        runner, calls = self._runner()
        dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                           tier='D2', lenses=['functional-testing'], now=1000.0)
        _, payload = calls[0]
        self.assertEqual(set(payload), {'lens', 'artifact', 'requirement'})
        text = json.dumps(payload)
        for banned in ('packet', 'claims', 'summary', 'confidence', 'packet_outcome'):
            self.assertNotIn(banned, text)

    def test_missing_coverage_is_refused(self):
        def runner(lens_name, payload):
            return {'findings': []}

        with self.assertRaises(PolicyError):
            dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                               tier='D2', lenses=['functional-testing'])

    def test_sentinel_security_lens_is_mandatory(self):
        runner, _ = self._runner()
        with self.assertRaises(PolicyError):
            dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                               tier='D2', flags=('security_boundary',),
                               lenses=['functional-testing'])
        # With the security lens present the same dispatch passes.
        dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                           tier='D2', flags=('security_boundary',),
                           lenses=['functional-testing', 'security'], now=1000.0)

    def test_unknown_lens_is_refused(self):
        runner, _ = self._runner()
        with self.assertRaises(PolicyError):
            dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                               tier='D2', lenses=['wizardry'])

    def test_multi_lens_confirmation_through_dispatch(self):
        def runner(lens_name, payload):
            if lens_name in ('security', 'maintainability'):
                return {'coverage_statement': 'ok',
                        'findings': [finding(lens=lens_name, fingerprint='fp-shared',
                                             severity='critical')]}
            return {'coverage_statement': 'ok', 'findings': []}

        result = dispatch_assurance(self.store, task_id=TASK, artifact='art_x', runner=runner,
                                    tier='D2', lenses=['maintainability', 'security'],
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
            oracle_check(self.store, task_id=TASK, artifact='art_x', runner=runner,
                         producer_provider='claude-code', oracle_provider='internal')
        ok = oracle_check(self.store, task_id=TASK, artifact='art_x', runner=runner,
                          producer_provider='codex', oracle_provider='claude-code', now=1000.0)
        self.assertEqual(ok['family_diversity'], 'different')
        self.assertEqual(ok['lens'], ORACLE_LENS)
        self.assertEqual(len(ok['findings']), 1)
        self.assertEqual(ok['coverage_statement'], 'attacked')

    def test_same_family_fallback_must_be_recorded(self):
        runner, _ = self._runner()
        fallback = oracle_check(self.store, task_id=TASK, artifact='art_x', runner=runner,
                                producer_provider='claude-code', oracle_provider='internal',
                                allow_same_family=True, now=1000.0)
        self.assertIn('unavailable', fallback['family_diversity'])

    def test_coverage_statement_required(self):
        def runner(lens_name, payload):
            return {'findings': []}

        with self.assertRaises(PolicyError):
            oracle_check(self.store, task_id=TASK, artifact='art_x', runner=runner,
                         producer_provider='codex', oracle_provider='claude-code')

    def test_oracle_payload_is_anti_anchored(self):
        runner, calls = self._runner()
        oracle_check(self.store, task_id=TASK, artifact='art_x', runner=runner,
                     producer_provider='codex', oracle_provider='claude-code', now=1000.0)
        _, payload = calls[0]
        self.assertEqual(set(payload), {'lens', 'artifact', 'requirement'})


class StatsTests(Base):
    def test_lens_stats_fp_rates(self):
        record = record_finding(self.store, finding(lens='security', fingerprint='fp-1',
                                                   severity='critical'),
                                now=1000.0)
        record_finding(self.store, finding(lens='maintainability', fingerprint='fp-2',
                                           severity='critical'), now=1001.0)
        resolve_finding(self.store, record['id'], resolution='dismissed',
                        rationale='false positive')
        stats = lens_stats(self.store)
        self.assertEqual(stats['security']['total'], 1)
        self.assertEqual(stats['security']['dismissed'], 1)
        self.assertEqual(stats['security']['fp_rate'], 1.0)
        self.assertIsNone(stats['maintainability']['fp_rate'])
        self.assertEqual(stats['maintainability']['open'], 1)


class CarryTests(unittest.TestCase):
    def test_escalation_types_are_single_sourced(self):
        self.assertIs(messages_module.ESCALATION_TYPES, pods_module.INTERRUPTION_TYPES)
        self.assertEqual(messages_module.ESCALATION_TYPES,
                         ('BLOCKER', 'DECISION_PROPOSAL', 'REPLAN_REQUEST'))


if __name__ == '__main__':
    unittest.main()
