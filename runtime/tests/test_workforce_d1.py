"""Phase 5.2: D1 single-specialist delegation — staffing decisions, contract issuance,
evidence-bound completion, and ledger projections.

Verification for `kel/delegation.py` (workforce-os doc 15 §5.2; docs 05/06/13): D0 missions
delegate nothing; flag-off performs no writes at all (B-config parity by construction); D1
issues a frozen contract linked to the milestone plus exactly one assignment; closes refuse
stale or unbound evidence and missing criterion coverage; uncertain outcomes close as
UNCERTAIN; worker tools are enforced against the frozen grants; the task/progress ledgers
project the full trail read-only.
"""
import contextlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from kel.assignment import ensure_archetypes
from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.context import Context
from kel.core import PolicyError, Store
from kel.delegation import (D1_BUDGET_DEFAULTS, close_d1, delegate, progress_ledger, run_d1,
                            task_ledger)
from kel.delegation import ensure_schema as ensure_delegation_schema
from kel.evidence import write_evidence
from kel.staffing import decide, score
from kel.team import Team
from kel.workforce import ensure_schema as ensure_workforce_schema
from workforce_fixtures import candidates, packet


def small_features(**overrides):
    features = {'complexity': 1, 'decomposability': 1, 'sequentiality': 1, 'uncertainty': 1,
                'novelty': 1, 'risk': 0, 'domain_breadth': 0, 'tool_requirements': 1,
                'consequence_of_failure': 0, 'user_facing': 0, 'release_proximity': 0,
                'budget_class': 'standard'}
    features.update(overrides)
    return features


def tiny_features(**overrides):
    features = {name: 0 for name in ('complexity', 'decomposability', 'sequentiality',
                                     'uncertainty', 'novelty', 'risk', 'domain_breadth',
                                     'tool_requirements', 'consequence_of_failure',
                                     'user_facing', 'release_proximity')}
    features['budget_class'] = 'tiny'
    features.update(overrides)
    return features


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')
        ensure_workforce_schema(self.store)
        ensure_assignment_schema(self.store)
        ensure_delegation_schema(self.store)
        ensure_archetypes(self.store)
        self.ctx = Context(self.store)
        self.conv = self.ctx.conversation('default', title='D1 tests')
        self.job_id = self.store.create(
            {'request': 'D1 fixture job',
             'milestones': [{'id': 'm1', 'objective': 'Draft the deliverable',
                             'filename': 'out.md', 'depends_on': [],
                             'checks': [{'kind': 'min_chars', 'value': 40}]}]},
            conversation=self.conv)
        self.team = Team(self.store)

    def event_count(self, kind):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute('SELECT count(*) FROM team_events WHERE kind=?',
                              (kind,)).fetchone()[0]

    def contract_rows(self):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(row) for row in db.execute('SELECT * FROM task_contracts')]

    def assignments(self):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(row) for row in db.execute('SELECT * FROM team_assignments')]


class StaffingDecideTests(unittest.TestCase):
    def test_score_is_deterministic_and_weighted(self):
        self.assertEqual(score(tiny_features()), 0.0)
        self.assertAlmostEqual(score(small_features()), 4.2, places=1)

    def test_bands_map_scores_to_tiers(self):
        self.assertEqual(decide(tiny_features())['tier'], 'D0')
        self.assertEqual(decide(small_features())['tier'], 'D1')
        self.assertEqual(decide(tiny_features())['workers'], 0)
        self.assertEqual(decide(small_features())['workers'], 1)

    def test_undecomposable_work_is_capped_to_a_pod(self):
        features = small_features(complexity=3, decomposability=1, sequentiality=2,
                                  uncertainty=3, novelty=2, risk=2, domain_breadth=1,
                                  tool_requirements=2, consequence_of_failure=1)
        result = decide(features)
        self.assertEqual(result['tier'], 'D2')
        self.assertIn('R1', [item['id'] for item in result['rules_fired']])

    def test_flags_raise_the_floor(self):
        raised = decide(small_features(), flags=('security_boundary',))
        self.assertEqual(raised['tier'], 'D2')
        self.assertIn('R3', [item['id'] for item in raised['rules_fired']])
        noted = decide(small_features(), flags=('new_dependency',))
        self.assertEqual(noted['tier'], 'D1')
        self.assertIn('R7', [item['id'] for item in noted['rules_fired']])

    def test_tier_max_caps_the_decision(self):
        result = decide(small_features(), flags=('release',), tier_max='D1')
        self.assertEqual(result['tier'], 'D1')

    def test_feature_validation(self):
        with self.assertRaises(PolicyError):
            score(small_features(complexity=4))
        with self.assertRaises(PolicyError):
            score(small_features(mystery=1))
        with self.assertRaises(PolicyError):
            decide(small_features(), flags=('telepathy',))
        with self.assertRaises(PolicyError):
            decide(small_features(budget_class='enormous'))


class DelegateTests(Base):
    def test_flag_off_performs_no_writes(self):
        result = delegate(self.store, self.job_id, 'm1', {}, features=small_features(),
                          enabled=False)
        self.assertFalse(result['delegated'])
        self.assertEqual(self.contract_rows(), [])
        self.assertEqual(self.assignments(), [])
        self.assertEqual(self.event_count('staffing.decided'), 0)
        self.assertEqual(self.event_count('contract.issued'), 0)

    def test_d0_delegates_nothing(self):
        result = delegate(self.store, self.job_id, 'm1', {}, features=tiny_features(),
                          enabled=True)
        self.assertFalse(result['delegated'])
        self.assertIn('D0', result['reason'])
        self.assertEqual(self.contract_rows(), [])

    def test_d2_is_refused_explicitly(self):
        with self.assertRaises(PolicyError):
            delegate(self.store, self.job_id, 'm1', {}, features=small_features(),
                     enabled=True, mission_flags=('security_boundary',))
        self.assertEqual(self.contract_rows(), [])

    def test_d1_issues_contract_and_exactly_one_assignment(self):
        result = delegate(self.store, self.job_id, 'm1', {'objective': 'Draft v1'},
                          features=small_features(), enabled=True, candidates=candidates())
        self.assertTrue(result['delegated'])
        rows = self.contract_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['milestone_id'], 'm1')
        self.assertEqual(rows[0]['mission_id'], self.job_id)
        self.assertEqual(rows[0]['task_id'], result['task_id'])
        data = json.loads(rows[0]['data'])
        self.assertEqual(data['state'], 'approved')
        self.assertEqual(data['tier'], 'D1')
        self.assertEqual(data['staffing_ref'], result['staffing_id'])
        self.assertEqual(data['budget'], D1_BUDGET_DEFAULTS)
        self.assertEqual(len(self.assignments()), 1)
        self.assertEqual(self.event_count('staffing.decided'), 1)
        self.assertEqual(self.event_count('contract.issued'), 1)
        with contextlib.closing(self.store.connect()) as db:
            detail = db.execute("SELECT detail FROM team_events WHERE kind='staffing.decided'"
                                ).fetchone()['detail']
        recorded = json.loads(detail)
        self.assertEqual(recorded['tier'], 'D1')
        self.assertTrue(recorded['reasons'])

    def test_contract_rows_are_frozen(self):
        import sqlite3
        delegate(self.store, self.job_id, 'm1', {}, features=small_features(), enabled=True,
                 candidates=candidates())
        with contextlib.closing(self.store.connect()) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE task_contracts SET data='{}'")

    def test_missing_features_are_refused(self):
        with self.assertRaises(PolicyError):
            delegate(self.store, self.job_id, 'm1', {}, enabled=True)

    def test_reservation_is_linked_before_completion(self):
        result = delegate(self.store, self.job_id, 'm1', {}, features=small_features(),
                          enabled=True, candidates=candidates(),
                          budget_estimate={'tokens': 40000, 'wallclock': 900, 'cost': 1.5})
        self.assertIsNotNone(result['reservation'])
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM budget_reservations').fetchone()
        self.assertEqual(row['assignment_id'], result['assignment_id'])
        self.assertEqual(row['milestone_id'], 'm1')


class CloseTests(Base):
    def _run(self, build, **kwargs):
        holder = {}

        def worker(prepared):
            holder['prepared'] = prepared
            return build(prepared)

        result = run_d1(self.store, self.job_id, 'm1', {'objective': 'Draft'}, worker,
                        enabled=True, features=small_features(),
                        candidates=candidates(), **kwargs)
        return result, holder

    def _evidence_and_packet(self, prepared, *, ran_at, artifact_digest='sha256:77bb',
                             outcome='completed'):
        record = write_evidence(self.store, mission_id=prepared['job_id'],
                                task_id=prepared['task_id'], evidence_class='check_result',
                                label='milestone checks green', command='kel check m1',
                                exit_code=0, output='ok', artifact_digest=artifact_digest,
                                ran_at=ran_at, produced_by=prepared['assignment_id'])
        body = packet(
            task_id=prepared['task_id'],
            evidence=[{'id': record['id'], 'class': 'check_result', 'command': 'kel check m1',
                       'exit_code': 0, 'output_digest': record['output_digest'],
                       'artifact_digest': artifact_digest, 'ran_at': ran_at,
                       'freshness_ok': True, 'produced_by': prepared['assignment_id']}],
            completion_claims=[
                {'claim_id': 'c1', 'status': 'verified', 'evidence_refs': [record['id']]},
                {'claim_id': 'artifact', 'status': 'verified',
                 'evidence_refs': [record['id']]}],
            outcome=outcome)
        if outcome != 'completed':
            body['unresolved_uncertainty'] = ['fixture uncertainty']
        return body


    def test_happy_path_closes_done(self):
        now = time.time()

        def build(prepared):
            return self._evidence_and_packet(prepared, ran_at=now)

        result, _ = self._run(build, now=now)
        self.assertTrue(result['closed'])
        self.assertEqual(result['packet_outcome'], 'completed')
        self.assertEqual(result['assignment_state'], 'DONE')
        self.assertEqual(result['violations'], [])
        self.assertEqual(len(self.assignments()), 1)

    def test_stale_evidence_cannot_close_completed(self):
        now = time.time()
        old = now - (24 * 60 + 30) * 60  # 24.5 hours old; the contract window is 24 hours

        def build(prepared):
            return self._evidence_and_packet(prepared, ran_at=old)

        with self.assertRaises(PolicyError):
            self._run(build, now=now)

    def test_content_unbound_evidence_is_refused(self):
        now = time.time()

        def build(prepared):
            body = self._evidence_and_packet(prepared, ran_at=now)
            body['artifacts'] = [{'id': 'art_x', 'digest': 'sha256:other', 'kind': 'code'}]
            return body

        with self.assertRaises(PolicyError):
            self._run(build, now=now)

    def test_missing_criterion_coverage_is_refused(self):
        now = time.time()

        def build(prepared):
            body = self._evidence_and_packet(prepared, ran_at=now)
            body['completion_claims'] = [body['completion_claims'][0]]
            return body

        with self.assertRaises(PolicyError):
            self._run(build, now=now)

    def test_uncertain_outcome_closes_as_uncertain(self):
        now = time.time()

        def build(prepared):
            return self._evidence_and_packet(prepared, ran_at=now, outcome='uncertain')

        result, _ = self._run(build, now=now)
        self.assertEqual(result['packet_outcome'], 'uncertain')
        self.assertEqual(result['assignment_state'], 'UNCERTAIN')

    def test_failed_outcome_closes_as_failed(self):
        now = time.time()

        def build(prepared):
            return self._evidence_and_packet(prepared, ran_at=now, outcome='failed')

        result, _ = self._run(build, now=now)
        self.assertEqual(result['packet_outcome'], 'failed')
        self.assertEqual(result['assignment_state'], 'FAILED')

    def test_worker_error_closes_failed_honestly(self):
        def worker(prepared):
            raise RuntimeError('boom')

        result = run_d1(self.store, self.job_id, 'm1', {'objective': 'Draft'}, worker,
                        enabled=True, features=small_features(), candidates=candidates())
        self.assertTrue(result['closed'])
        self.assertEqual(result['outcome'], 'failed')
        self.assertEqual(result['error'], 'RuntimeError')

    def test_worker_tools_are_enforced_against_grants(self):
        called = {'count': 0}

        def worker(prepared):
            called['count'] += 1
            return packet(task_id=prepared['task_id'])

        with self.assertRaises(PolicyError):
            run_d1(self.store, self.job_id, 'm1', {'objective': 'Draft'}, worker,
                   worker_tools=('shell',), enabled=True, features=small_features(),
                   candidates=candidates())
        self.assertEqual(called['count'], 0)

    def test_double_close_is_refused(self):
        now = time.time()
        holder = {}

        def build(prepared):
            body = self._evidence_and_packet(prepared, ran_at=now)
            holder['task_id'] = prepared['task_id']
            holder['body'] = body
            return body

        self._run(build, now=now)
        with self.assertRaises(PolicyError):
            close_d1(self.store, holder['task_id'], holder['body'], now=now)


class LedgerTests(Base):
    def _closed_task(self):
        now = time.time()

        def build(prepared):
            return CloseTests._evidence_and_packet(self, prepared, ran_at=now)

        return run_d1(self.store, self.job_id, 'm1', {'objective': 'Draft'}, build,
                      enabled=True, features=small_features(), candidates=candidates(),
                      now=now)

    def test_task_ledger_projects_the_trail(self):
        result = self._closed_task()
        rows = task_ledger(self.store, job_id=self.job_id)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['milestone_id'], 'm1')
        self.assertEqual(row['role'], 'builder')
        self.assertEqual(row['tier'], 'D1')
        self.assertEqual(row['assignment']['assignment_id'], result['assignment_id'])
        self.assertEqual(row['closed']['outcome'], 'completed')

    def test_progress_ledger_is_read_only_and_complete(self):
        result = self._closed_task()
        before = (len(self.contract_rows()), len(self.assignments()))
        ledger = progress_ledger(self.store, job_id=self.job_id)
        self.assertEqual(len(ledger['milestones']), 1)
        self.assertEqual(ledger['milestones'][0]['id'], 'm1')
        self.assertEqual(ledger['milestones'][0]['state'], 'READY')
        self.assertEqual(len(ledger['tasks']), 1)
        self.assertEqual(len(ledger['assignments']), 1)
        self.assertEqual(ledger['assignments'][0]['assignment_id'], result['assignment_id'])
        self.assertEqual(ledger['evidence'][0]['label'], 'milestone checks green')
        self.assertEqual(ledger['closed'], {'count': 1, 'outcomes': ['completed']})
        self.assertEqual((len(self.contract_rows()), len(self.assignments())), before)
        with self.assertRaises(PolicyError):
            progress_ledger(self.store, job_id='job_missing')


if __name__ == '__main__':
    unittest.main()
