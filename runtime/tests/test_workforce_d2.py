"""Phase 5.3: D2 small pods — protocol v1 conformance, findings, Builder→Verifier flow,
stall detection, and the evaluation-harness pilot gates.

Verification for `kel/messages.py` (dispatch), `kel/assurance.py` (findings pipeline +
arbitration v1), `kel/pods.py` (run_d2, stalls, interruptions) and `kel/evaluation.py`
(A-vs-C pilot on classes 2/6/8), per workforce-os docs 07/08/13/15 §5.3.
"""
import contextlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from kel.assurance import findings, record_finding, resolve_finding
from kel.assignment import ensure_archetypes
from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.context import Context
from kel.core import PolicyError, Store, uid
from kel.delegation import delegate
from kel.delegation import ensure_schema as ensure_delegation_schema
from kel.delegation import task_ledger
from kel.evaluation import INTERRUPTION_BUDGET, run_pilot
from kel.evidence import write_evidence
from kel.messages import (PAIR_MESSAGE_BUDGET, TASK_MESSAGE_BUDGET, messages, send_message)
from kel.pods import VERIFICATION_LENSES, check_stall, family_of, interruptions, run_d2
from kel.team import Team
from kel.workforce import ensure_schema as ensure_workforce_schema
from workforce_fixtures import candidates, packet


def d2_features(**overrides):
    features = {'complexity': 2, 'decomposability': 1, 'sequentiality': 1, 'uncertainty': 1,
                'novelty': 1, 'risk': 0, 'domain_breadth': 0, 'tool_requirements': 1,
                'consequence_of_failure': 0, 'user_facing': 0, 'release_proximity': 0,
                'budget_class': 'standard'}
    features.update(overrides)
    return features


def d1_features():
    return d2_features(complexity=1, uncertainty=1, novelty=0, tool_requirements=0)


def high_features():
    return d2_features(complexity=3, decomposability=2, sequentiality=0, uncertainty=3,
                       novelty=2, risk=2, domain_breadth=1, tool_requirements=2,
                       consequence_of_failure=1)


def msg(**overrides):
    body = {'schema_version': 1, 'mission_id': 'mis_' + 'a' * 8, 'task_id': 'tsk_' + 'b' * 8,
            'from': 'cmd', 'to': 'asn_' + 'c' * 8, 'type': 'REQUEST',
            'summary': 'Do the bounded thing.', 'refs': ['tsk_' + 'b' * 8],
            'required_action': 'Deliver the thing.'}
    body.update(overrides)
    return body


def finding(**overrides):
    body = {'schema_version': 1, 'mission_id': 'mis_' + 'a' * 8, 'task_id': 'tsk_' + 'b' * 8,
            'lens': 'functional-testing', 'severity': 'blocker', 'confidence': 8,
            'artifact': 'art_x', 'location': 'src/app.py:10',
            'summary': 'The delivered behavior misses the acceptance requirement.',
            'evidence': 'fixture reproduction', 'fix': '',
            'fingerprint': 'art_x:src/app.py:10:behavior',
            'status': 'open',
            'by': {'lens': 'functional-testing', 'model_family': 'fixture',
                   'assignment': 'asn_' + 'c' * 8}}
    body.update(overrides)
    return body


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
        self.conv = self.ctx.conversation('default', title='D2 tests')
        self.job_id = self.store.create(
            {'request': 'D2 fixture job',
             'milestones': [{'id': 'm1', 'objective': 'Draft the deliverable',
                             'filename': 'out.md', 'depends_on': [],
                             'checks': [{'kind': 'min_chars', 'value': 40}]}]},
            conversation=self.conv)
        self.team = Team(self.store)

    def message_count(self, task_id):
        return len(messages(self.store, task_id=task_id))

    def contract_rows(self):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(row) for row in db.execute('SELECT * FROM task_contracts')]

    def assignments(self):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(row) for row in db.execute('SELECT * FROM team_assignments')]


class MessageDispatchTests(Base):
    def test_valid_dispatch_and_reader(self):
        record = send_message(self.store, msg(id='msg_1'))
        self.assertEqual(record['id'], 'msg_1')
        rows = messages(self.store, task_id='tsk_' + 'b' * 8)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['refs'], ['tsk_' + 'b' * 8])
        self.assertEqual(rows[0]['recipient'], 'asn_' + 'c' * 8)

    def test_uuid_parties_are_the_engine_convention(self):
        sender = uid()
        record = send_message(self.store, msg(id='msg_u', **{'from': sender, 'to': 'cmd'}))
        self.assertEqual(record['from'], sender)

    def test_status_is_not_a_message_type(self):
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(type='STATUS'))

    def test_duplicate_fingerprint_is_rejected(self):
        send_message(self.store, msg(id='msg_d1'))
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_d2'))
        send_message(self.store, msg(id='msg_d3',
                                     required_action='Deliver the other thing.'))
        self.assertEqual(self.message_count('tsk_' + 'b' * 8), 2)

    def test_worker_pair_budget_with_cmd_escalation_exempt(self):
        for index in range(PAIR_MESSAGE_BUDGET):
            send_message(self.store, msg(id='msg_p%d' % index,
                                         **{'from': 'asn_' + 'c' * 8, 'to': 'asn_' + 'd' * 8},
                                         required_action='Step %d.' % index))
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_px',
                                         **{'from': 'asn_' + 'c' * 8, 'to': 'asn_' + 'd' * 8},
                                         required_action='One more.'))
        send_message(self.store, msg(id='msg_pb', **{'from': 'asn_' + 'c' * 8, 'to': 'cmd'},
                                     type='BLOCKER', required_action='Unblock step 3.'))

    def test_task_budget(self):
        # F14-2: non-escalation traffic counts toward the pair cap, so span two pairs to
        # reach the task-wide cap of 12.
        for index in range(PAIR_MESSAGE_BUDGET):
            send_message(self.store, msg(id='msg_t%d' % index, to='asn_' + 'c' * 8,
                                         required_action='Task step %d.' % index))
        for index in range(PAIR_MESSAGE_BUDGET, TASK_MESSAGE_BUDGET):
            send_message(self.store, msg(id='msg_t%d' % index, to='asn_' + 'e' * 8,
                                         required_action='Task step %d.' % index))
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_tx', to='asn_' + 'f' * 8,
                                         required_action='One too many.'))

    def test_cmd_escalation_boundary(self):
        # Non-escalation traffic to cmd counts toward the pair; escalation types stay exempt.
        for index in range(PAIR_MESSAGE_BUDGET):
            send_message(self.store, msg(id='msg_c%d' % index, to='asn_' + 'c' * 8,
                                         required_action='Chatter %d.' % index))
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_cx', to='asn_' + 'c' * 8,
                                         required_action='More chatter.'))
        for index, kind in enumerate(('BLOCKER', 'DECISION_PROPOSAL', 'REPLAN_REQUEST')):
            send_message(self.store, msg(id='msg_cb%d' % index,
                                         **{'from': 'asn_' + 'c' * 8, 'to': 'cmd'},
                                         type=kind, required_action='Escalate %s.' % kind))
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_ch', **{'from': 'asn_' + 'c' * 8, 'to': 'cmd'},
                                         required_action='Hand it over.'))

    def test_cancelled_receiver_is_refused(self):
        prepared = delegate(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                            features=d1_features(), enabled=True, candidates=candidates())
        assignment_id = prepared['assignment_id']
        with self.store.transaction() as db:
            db.execute("UPDATE team_assignments SET state='CANCELLED' WHERE assignment_id=?",
                       (assignment_id,))
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_c', to=assignment_id))

    def test_refs_required_and_secrets_refused(self):
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_r', refs=[]))
        with self.assertRaises(PolicyError):
            send_message(self.store, msg(id='msg_s',
                                         summary='token AKIAIOSFODNN7EXAMPLE leaked'))

    def test_supersedes_round_trip(self):
        send_message(self.store, msg(id='msg_a1'))
        send_message(self.store, msg(id='msg_a2', supersedes='msg_a1',
                                     required_action='Deliver the revised thing.'))
        rows = messages(self.store, task_id='tsk_' + 'b' * 8)
        self.assertEqual(rows[-1]['supersedes'], 'msg_a1')


class FindingPipelineTests(Base):
    def test_record_and_read(self):
        record = record_finding(self.store, finding(), now=1000.0)
        rows = findings(self.store, task_id='tsk_' + 'b' * 8)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], record['id'])
        self.assertEqual(rows[0]['by']['model_family'], 'fixture')
        self.assertEqual(rows[0]['confirmations'], [])

    def test_same_lens_duplicate_is_refused(self):
        record_finding(self.store, finding(), now=1000.0)
        with self.assertRaises(PolicyError):
            record_finding(self.store, finding(confidence=9), now=1001.0)

    def test_multi_lens_confirmation_upgrades(self):
        record_finding(self.store, finding(), now=1000.0)
        upgraded = record_finding(self.store, finding(
            lens='maintainability', confidence=7,
            by={'lens': 'maintainability', 'model_family': 'fixture',
                'assignment': 'asn_' + 'e' * 8}), now=1001.0)
        self.assertEqual(upgraded['confidence'], 9)  # max(8, 7) + 1
        self.assertIn('maintainability', upgraded['confirmations'])
        self.assertEqual(upgraded['status'], 'open')  # corroboration never retires a finding
        self.assertTrue(upgraded.get('confirmed_by_multi'))

    def test_confidence_is_capped_at_ten(self):
        record_finding(self.store, finding(confidence=10), now=1000.0)
        upgraded = record_finding(self.store, finding(
            lens='maintainability', confidence=10,
            by={'lens': 'maintainability', 'model_family': 'fixture',
                'assignment': 'asn_' + 'e' * 8}), now=1001.0)
        self.assertEqual(upgraded['confidence'], 10)

    def _evidence(self):
        return write_evidence(self.store, mission_id='mis_' + 'a' * 8,
                              task_id='tsk_' + 'b' * 8, evidence_class='check_result',
                              label='fix verified', command='kel check fix', exit_code=0,
                              output='ok', produced_by='run_fix', ran_at=1002.0)

    def test_fixed_requires_recorded_evidence(self):
        record = record_finding(self.store, finding(), now=1000.0)
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='fixed')
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='fixed',
                            evidence_ref='ev_missing')
        evidence = self._evidence()
        updated = resolve_finding(self.store, record['id'], resolution='fixed',
                                  evidence_ref=evidence['id'], now=1002.0)
        self.assertEqual(updated['status'], 'fixed')

    def test_accepted_needs_rationale_and_blockers_need_evidence(self):
        record = record_finding(self.store, finding(), now=1000.0)
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='accepted')
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='accepted',
                            rationale='ship it')
        evidence = self._evidence()
        updated = resolve_finding(self.store, record['id'], resolution='accepted',
                                  rationale='ship it after review',
                                  evidence_ref=evidence['id'])
        self.assertEqual(updated['status'], 'dismissed')
        self.assertTrue(updated['dismissal_reason'].startswith('risk-accepted:'))

    def test_dismissed_requires_rationale_and_closed_is_refused(self):
        record = record_finding(self.store, finding(severity='info', fingerprint='fp-i'),
                                now=1000.0)
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='dismissed')
        updated = resolve_finding(self.store, record['id'], resolution='dismissed',
                                  rationale='not reproducible')
        self.assertEqual(updated['status'], 'dismissed')
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='fixed')

    def test_unknown_finding_and_bad_resolution(self):
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, 'find_missing', resolution='fixed')
        record = record_finding(self.store, finding(), now=1000.0)
        with self.assertRaises(PolicyError):
            resolve_finding(self.store, record['id'], resolution='maybe')

    def test_reader_filters(self):
        record_finding(self.store, finding(fingerprint='fp-1'), now=1000.0)
        record_finding(self.store, finding(severity='info', fingerprint='fp-2'), now=1001.0)
        self.assertEqual(len(findings(self.store, mission_id='mis_' + 'a' * 8)), 2)
        self.assertEqual(len(findings(self.store, status='open')), 2)
        self.assertEqual(len(findings(self.store, status='fixed')), 0)


class PodFlowTests(Base):
    def _builder(self, *, digest='sha256:77bb'):
        def worker(prepared):
            now = time.time()
            record = write_evidence(self.store, mission_id=prepared['job_id'],
                                    task_id=prepared['task_id'], evidence_class='check_result',
                                    label='builder checks', command='kel check m1',
                                    exit_code=0, output='ok', artifact_digest=digest,
                                    ran_at=now, produced_by=prepared['assignment_id'])
            return packet(task_id=prepared['task_id'],
                          artifacts=[{'id': 'art_delivered', 'digest': digest, 'kind': 'code'}],
                          evidence=[{'id': record['id'], 'class': 'check_result',
                                     'command': 'kel check m1', 'exit_code': 0,
                                     'output_digest': record['output_digest'],
                                     'artifact_digest': digest, 'ran_at': now,
                                     'freshness_ok': True,
                                     'produced_by': prepared['assignment_id']}],
                          completion_claims=[
                              {'claim_id': 'c1', 'status': 'verified',
                               'evidence_refs': [record['id']]},
                              {'claim_id': 'artifact', 'status': 'verified',
                               'evidence_refs': [record['id']]}])
        return worker

    def _verifier(self, *, seeds=(), verdict='VERIFIED', digest='sha256:77bb'):
        def worker(prepared):
            now = time.time()
            record = write_evidence(self.store, mission_id=prepared['job_id'],
                                    task_id=prepared['task_id'], evidence_class='review_record',
                                    label='lenses run', command='kel verify',
                                    produced_by=prepared['assignment_id'],
                                    output='verdict %s' % verdict, artifact_digest=digest,
                                    ran_at=now)
            items = []
            for index, seed in enumerate(seeds):
                items.append({'schema_version': 1, 'mission_id': prepared['job_id'],
                              'task_id': prepared['task_id'],
                              'lens': seed.get('lens', 'functional-testing'),
                              'severity': seed.get('severity', 'blocker'), 'confidence': 8,
                              'artifact': 'art_delivered',
                              'location': seed.get('location', 'seed-%d' % index),
                              'summary': seed.get('summary', 'defect %d' % index),
                              'evidence': 'fixture reproduction',
                              'fingerprint': 'fp-%d' % index, 'status': 'open',
                              'by': {'lens': seed.get('lens', 'functional-testing'),
                                     'model_family': 'fixture',
                                     'assignment': prepared['assignment_id']}})
            completed = verdict == 'VERIFIED'
            body = packet(task_id=prepared['task_id'],
                          outcome='completed' if completed else 'failed',
                          artifacts=[{'id': 'art_verified', 'digest': digest, 'kind': 'code'}],
                          evidence=[{'id': record['id'], 'class': 'review_record',
                                     'command': 'kel verify', 'exit_code': None,
                                     'output_digest': record['output_digest'],
                                     'artifact_digest': digest, 'ran_at': now,
                                     'freshness_ok': True,
                                     'produced_by': prepared['assignment_id']}],
                          completion_claims=[
                              {'claim_id': claim_id,
                               'status': 'verified' if completed else 'failed',
                               'evidence_refs': [record['id']]}
                              for claim_id in ('c1', 'artifact')],
                          required_reviewer={'lenses': list(VERIFICATION_LENSES),
                                             'independence': 'any_but_executor',
                                             'oracle': False},
                          reviewer_requirements_met={
                              'lenses_run': [{'lens': name, 'verdict': verdict.lower(),
                                              'coverage_statement': 'fixture lens pass'}
                                             for name in VERIFICATION_LENSES],
                              'coverage_complete': True, 'oracle': {'ran': False}})
            if not completed:
                body['unresolved_uncertainty'] = ['verification found defects']
            return {'findings': items, 'verdict': verdict, 'packet': body}
        return worker

    def test_flag_off_performs_zero_writes(self):
        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'}, None, None,
                        enabled=False, features=d2_features())
        self.assertFalse(result['delegated'])
        self.assertEqual(self.contract_rows(), [])
        self.assertEqual(self.assignments(), [])
        self.assertEqual(len(messages(self.store, mission_id=self.job_id)), 0)
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM findings').fetchone()[0], 0)

    def test_requires_a_d2_decision(self):
        d1 = d2_features(complexity=1, uncertainty=1, novelty=0, tool_requirements=0)
        with self.assertRaises(PolicyError):
            run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'}, None, None,
                   enabled=True, features=d1)
        with self.assertRaises(PolicyError):
            run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'}, None, None,
                   enabled=True, features=high_features(), candidates=candidates())

    def test_happy_verified_flow(self):
        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                        self._builder(), self._verifier(), enabled=True,
                        features=d2_features(), candidates=candidates())
        self.assertTrue(result['closed'])
        self.assertEqual(result['verdict'], 'VERIFIED')
        self.assertEqual(result['builder']['assignment_state'], 'DONE')
        self.assertEqual(result['verifier']['assignment_state'], 'DONE')
        self.assertEqual(result['family_diversity'], 'different')
        pod = result['pod']
        self.assertNotEqual(pod['assignment_ids']['builder'], pod['assignment_ids']['verifier'])
        rows = self.contract_rows()
        self.assertEqual(len(rows), 2)
        data_by_task = {row['task_id']: json.loads(row['data']) for row in rows}
        verifier_contract = data_by_task[pod['task_ids']['verifier']]
        self.assertEqual(verifier_contract['dependencies']['tasks'],
                         [pod['task_ids']['builder']])
        self.assertEqual(verifier_contract['required_reviewer']['lenses'],
                         list(VERIFICATION_LENSES))
        sent = messages(self.store, task_id=pod['task_ids']['verifier'])
        self.assertEqual([row['type'] for row in sent], ['HANDOFF', 'HANDOFF'])
        self.assertEqual(result['interruptions'], 0)
        self.assertEqual(len(task_ledger(self.store, job_id=self.job_id)), 2)
        assignments = {row['assignment_id']: row for row in self.assignments()}
        builder_row = assignments[pod['assignment_ids']['builder']]
        verifier_row = assignments[pod['assignment_ids']['verifier']]
        self.assertEqual(builder_row['provider'], 'codex')
        self.assertEqual(verifier_row['provider'], 'claude-code')
        self.assertNotEqual(family_of(builder_row['provider']),
                            family_of(verifier_row['provider']))

    def test_failed_verdict_records_findings(self):
        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                        self._builder(),
                        self._verifier(seeds=({'lens': 'functional-testing'},),
                                       verdict='FAILED'),
                        enabled=True, features=d2_features(), candidates=candidates())
        self.assertEqual(result['verdict'], 'FAILED')
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['status'], 'open')
        self.assertEqual(result['verifier']['assignment_state'], 'FAILED')

    def test_verdict_contradicts_open_findings_is_refused(self):
        with self.assertRaises(PolicyError):
            run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                   self._builder(),
                   self._verifier(seeds=({'lens': 'functional-testing'},),
                                  verdict='VERIFIED'),
                   enabled=True, features=d2_features(), candidates=candidates())

    def test_builder_worker_error_closes_failed(self):
        def broken(prepared):
            raise RuntimeError('boom')

        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'}, broken,
                        self._verifier(), enabled=True, features=d2_features(),
                        candidates=candidates())
        self.assertEqual(result['verdict'], 'FAILED')
        self.assertEqual(result['stage'], 'builder')
        self.assertEqual(result['error'], 'RuntimeError')

    def test_verifier_worker_error_closes_uncertain(self):
        def broken(prepared):
            raise RuntimeError('boom')

        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                        self._builder(), broken, enabled=True, features=d2_features(),
                        candidates=candidates())
        self.assertEqual(result['verdict'], 'UNCERTAIN')
        self.assertEqual(result['stage'], 'verifier')
        self.assertEqual(len(result['messages']), 1)

    def test_worker_tools_are_enforced_before_the_run(self):
        called = {'count': 0}

        def worker(prepared):
            called['count'] += 1
            return packet(task_id=prepared['task_id'])

        with self.assertRaises(PolicyError):
            run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'}, worker,
                   self._verifier(), builder_tools=('shell',), enabled=True,
                   features=d2_features(), candidates=candidates())
        self.assertEqual(called['count'], 0)

    def test_family_diversity_falls_back_when_unavailable(self):
        single = [item for item in candidates() if item.name == 'codex']
        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                        self._builder(), self._verifier(), enabled=True,
                        features=d2_features(), candidates=single)
        self.assertEqual(result['family_diversity'], 'unavailable')
        self.assertEqual(result['verdict'], 'VERIFIED')

    def test_reservation_links_to_the_builder_assignment(self):
        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                        self._builder(), self._verifier(), enabled=True,
                        features=d2_features(), candidates=candidates(),
                        budget_estimate={'tokens': 40000, 'wallclock': 900, 'cost': 1.5})
        self.assertIsNotNone(result['reservation'])
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM budget_reservations').fetchone()
        self.assertEqual(row['assignment_id'], result['pod']['assignment_ids']['builder'])
        self.assertEqual(row['milestone_id'], 'm1')


class StallTests(Base):
    def _active_assignment(self):
        created = self.team.create_assignment(self.job_id, 'm1', 'builder')
        self.team.set_state(created['assignment_id'], 'ACTIVE')
        return created['assignment_id']

    def test_unknown_assignment_is_refused(self):
        with self.assertRaises(PolicyError):
            check_stall(self.store, 'missing_assignment')

    def test_stall_fires_beyond_threshold(self):
        aid = self._active_assignment()
        probe = check_stall(self.store, aid, now=time.time() + 3600, threshold_minutes=30)
        self.assertTrue(probe['stalled'])
        self.assertIn('threshold 30', probe['reason'])

    def test_fresh_activity_is_not_stalled(self):
        aid = self._active_assignment()
        probe = check_stall(self.store, aid, now=time.time() + 60, threshold_minutes=30)
        self.assertFalse(probe['stalled'])

    def test_done_assignment_is_not_stalled(self):
        aid = self._active_assignment()
        self.team.set_state(aid, 'DONE')
        probe = check_stall(self.store, aid, now=time.time() + 3600)
        self.assertFalse(probe['stalled'])
        self.assertIn('not active', probe['reason'])

    def test_pod_records_stall_probes(self):
        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                        PodFlowTests._builder(self), PodFlowTests._verifier(self),
                        enabled=True, features=d2_features(), candidates=candidates())
        self.assertFalse(result['builder']['stall']['stalled'])
        self.assertFalse(result['verifier']['stall']['stalled'])


class InterruptionTests(Base):
    def test_clean_pod_records_no_interruptions(self):
        result = run_d2(self.store, self.job_id, 'm1', {'objective': 'Draft'},
                        PodFlowTests._builder(self), PodFlowTests._verifier(self),
                        enabled=True, features=d2_features(), candidates=candidates())
        self.assertEqual(interruptions(self.store, job_id=self.job_id)['count'], 0)
        self.assertEqual(result['interruptions'], 0)

    def test_blocker_to_cmd_is_counted(self):
        send_message(self.store, msg(id='msg_b1', **{'from': 'asn_' + 'c' * 8, 'to': 'cmd'},
                                     type='BLOCKER', required_action='Unblock step 3.'))
        counted = interruptions(self.store, job_id='mis_' + 'a' * 8)
        self.assertEqual(counted['count'], 1)
        self.assertEqual(counted['messages'], ['msg_b1'])

    def test_handoff_to_cmd_is_not_an_interruption(self):
        send_message(self.store, msg(id='msg_h1', **{'from': 'asn_' + 'c' * 8, 'to': 'cmd'}))
        self.assertEqual(interruptions(self.store, job_id='mis_' + 'a' * 8)['count'], 0)


class PilotHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.results = run_pilot(workdir=cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_gates_pass(self):
        self.assertTrue(self.results['gates_ok'])
        for class_id, info in self.results['per_class'].items():
            self.assertTrue(info['escaped_below_A'], 'class %s' % class_id)
            self.assertTrue(info['interruptions_ok'], 'class %s' % class_id)

    def test_escaped_defects_strictly_below_a(self):
        for class_id in ('2', '6', '8'):
            info = self.results['per_class'][class_id]
            self.assertLess(info['escaped_C'], info['escaped_A'])

    def test_run_shape(self):
        self.assertEqual(len(self.results['runs']), 6)
        configs = {(run['class'], run['config']) for run in self.results['runs']}
        self.assertEqual(configs, {('2', 'A'), ('2', 'C'), ('6', 'A'), ('6', 'C'),
                                   ('8', 'A'), ('8', 'C')})

    def test_interruptions_within_budget(self):
        for run in self.results['runs']:
            if run['config'] == 'C':
                self.assertLessEqual(run['interruptions'], INTERRUPTION_BUDGET)

    def test_determinism_on_a_single_class(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        rerun = run_pilot(classes=('8',), workdir=tmp.name)
        first = self.results['per_class']['8']
        second = rerun['per_class']['8']
        self.assertEqual(first['escaped_C'], second['escaped_C'])
        self.assertEqual(first['escaped_A'], second['escaped_A'])


class StallClampTests(Base):
    def test_negative_idle_is_clamped(self):
        created = self.team.create_assignment(self.job_id, 'm1', 'builder')
        self.team.set_state(created['assignment_id'], 'ACTIVE')
        probe = check_stall(self.store, created['assignment_id'],
                            now=time.time() - 3600, threshold_minutes=30)
        self.assertFalse(probe['stalled'])
        self.assertEqual(probe['idle_minutes'], 0.0)
