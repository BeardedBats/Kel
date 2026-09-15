"""V1.5 Gate 1/2: the central authorization boundary on the real execution path.

Adversarial cases from the V1.5 security matrix: no lease, expired lease, revoked lease, spoofed
actors through the service, a worker outside its leased repository or filesystem root, unauthorized
tools, locked kinds, frozen and system paths, destructive actions without a snapshot or approval,
allow-once reuse, denied boundary requests, guardrail tampering, stale worker context, the engine
claim gate (blocked and allowed), resume-after-grant, and the durable decision record.
"""
import contextlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from kel import guardrails
from kel.authorize import (Authorizer, authorize, block_job, decisions, ensure_job_lease,
                           resume_after_grant)
from kel.autonomy import Autonomy, BLOCKED_KINDS
from kel.coding import compile_coding, git
from kel.core import PolicyError, Store, digest
from kel.engine import Engine
from kel.native import FixtureAdapter
from kel.service import Service
from kel.team import Team


def make_project(base, name):
    root = base / name
    root.mkdir(parents=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class AuthorizeBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.store = Store(self.base / 'data')
        self.project = make_project(self.base, 'proj')
        self.other = make_project(self.base, 'other')
        self.job = self.store.create(compile_coding('Change app.txt.', self.project,
                                                     ['python', '-m', 'unittest']))
        latest = Autonomy(self.store).latest_lease(self.job)
        self.assertIsNotNone(latest, 'a coding job must carry an execution lease from creation')
        self.lease_id = latest['lease_id']
        self.authz = Authorizer(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def intent(self, **overrides):
        base = {'actor': 'kel', 'job': self.job, 'milestone': 'code',
                'action_kind': 'write', 'target': str(self.project / 'app.txt')}
        base.update(overrides)
        return base

    def claim_run(self):
        return self.store.claim(self.job, 'code', provider='codex-code')


class LeaseIssuanceTests(AuthorizeBase):
    def test_execution_lease_binds_scope_to_the_compiled_contract(self):
        with contextlib.closing(self.store.connect()) as db:
            lease = db.execute('SELECT * FROM capability_leases WHERE lease_id=?',
                               (self.lease_id,)).fetchone()
            scope = [dict(r) for r in db.execute(
                'SELECT kind, value FROM lease_scope WHERE lease_id=? ORDER BY kind',
                (self.lease_id,))]
        self.assertEqual(lease['state'], 'ACTIVE')
        self.assertTrue(lease['review_ref'].startswith('kel-contract:'))
        self.assertEqual({row['kind'] for row in scope}, {'root', 'repo', 'tool'})
        self.assertIn(('tool', 'git'), {(r['kind'], r['value']) for r in scope})
        self.assertIn(('tool', 'run_tests'), {(r['kind'], r['value']) for r in scope})

    def test_ineligible_root_stays_unleased_and_fails_closed(self):
        frozen = make_project(self.base / 'Kel Releases' / 'Kel-V1.9-Frozen', 'proj')
        job = self.store.create(compile_coding('Change x.', frozen, ['python', '-m', 'unittest']))
        self.assertIsNone(Autonomy(self.store).latest_lease(job))


class DecisionTests(AuthorizeBase):
    def test_allow_inside_the_leased_scope_and_record_shape(self):
        decision = self.authz.decide(self.intent())
        self.assertEqual(decision['outcome'], 'ALLOW')
        rows = decisions(self.store, job_id=self.job)
        self.assertTrue(rows)
        row = rows[0]
        for field in ('decision_id', 'at', 'actor', 'action_kind', 'decision', 'policy_version',
                      'guardrail_digest'):
            self.assertTrue(row.get(field), field)
        self.assertEqual(row['guardrail_digest'], guardrails.DIGEST)

    def test_identical_decisions_collapse_to_one_record(self):
        first = self.authz.decide(self.intent(target=str(self.other / 'x.txt')))
        second = self.authz.decide(self.intent(target=str(self.other / 'x.txt')))
        self.assertEqual(first['decision_id'], second['decision_id'])

    def test_no_lease_is_denied(self):
        with self.store.transaction() as db:
            db.execute('DELETE FROM capability_leases')
            db.execute('DELETE FROM lease_scope')
        decision = self.authz.decide(self.intent())
        self.assertEqual(decision['outcome'], 'DENY')
        self.assertEqual(decision['rule'], 'lease-required')

    def test_expired_lease_is_reported_as_expired(self):
        with self.store.transaction() as db:
            db.execute('UPDATE capability_leases SET expires_at=0 WHERE lease_id=?', (self.lease_id,))
        self.assertEqual(self.authz.decide(self.intent())['outcome'], 'EXPIRED_LEASE')

    def test_revoked_lease_is_reported_as_revoked(self):
        Autonomy(self.store).revoke(self.lease_id, 'task finished')
        self.assertEqual(self.authz.decide(self.intent())['outcome'], 'REVOKED_LEASE')

    def test_locked_kinds_are_denied_with_their_guardrail_rule(self):
        for kind, rule in BLOCKED_KINDS.items():
            decision = self.authz.decide(self.intent(action_kind=kind, target='anything'))
            self.assertEqual(decision['outcome'], 'DENY', kind)
            self.assertEqual(decision['rule'], rule, kind)

    def test_frozen_and_system_paths_are_denied(self):
        frozen = self.authz.decide(self.intent(target=str(
            self.base / 'Kel Releases' / 'Kel-V1.3-Frozen' / 'x.txt')))
        system = self.authz.decide(self.intent(target='C:\\Windows\\System32\\drivers\\x.sys'))
        self.assertEqual((frozen['outcome'], frozen['rule']), ('DENY', 'frozen-immutable'))
        self.assertEqual((system['outcome'], system['rule']), ('DENY', 'system-path'))

    def test_destructive_needs_snapshot_and_approval(self):
        action = {'kind': 'delete-backup', 'target': 'old.db'}
        base_intent = self.intent(action_kind='destructive', target=str(self.project / 'old.db'))
        without = self.authz.decide(base_intent)
        self.assertEqual((without['outcome'], without['rule']), ('DENY', 'destructive-snapshot'))
        with_snapshot = self.authz.decide(dict(base_intent, snapshot_ref='backup:old.db'))
        self.assertEqual(with_snapshot['outcome'], 'REQUIRES_USER_APPROVAL')
        approval_id = 'approval-1'
        with self.store.transaction() as db:
            db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?)',
                       (approval_id, self.job, None, digest(action), 'APPROVED',
                        time.time() + 300, 'user'))
        approved = self.authz.decide(dict(base_intent, snapshot_ref='backup:old.db',
                                          approval_id=approval_id,
                                          metadata={'action': action}))
        self.assertEqual(approved['outcome'], 'ALLOW', approved)

    def test_guardrail_tampering_refuses_every_decision(self):
        weakened = (('weakened', 'Rule removed.', 'AUTO-X'),)
        with mock.patch('kel.guardrails.RULES', weakened):
            decision = self.authz.decide(self.intent())
        self.assertEqual(decision['outcome'], 'GUARDRAIL_TAMPERED')
        self.assertTrue(any(row['decision'] == 'GUARDRAIL_TAMPERED'
                            for row in decisions(self.store, job_id=self.job)))


class WorkerIdentityTests(AuthorizeBase):
    def worker_intent(self, run, **overrides):
        base = {'actor': 'worker', 'worker': run['id'], 'job': self.job, 'milestone': 'code',
                'action_kind': 'repo', 'tool': 'git', 'target': str(self.project)}
        base.update(overrides)
        return base

    def test_live_worker_is_allowed_inside_its_leased_repository(self):
        run = self.claim_run()
        decision = self.authz.decide(self.worker_intent(run))
        self.assertEqual(decision['outcome'], 'ALLOW', decision)

    def test_stopped_worker_context_is_invalid(self):
        run = self.claim_run()
        with self.store.transaction() as db:
            db.execute("UPDATE runs SET state='CANCEL_REQUESTED' WHERE id=?", (run['id'],))
        decision = self.authz.decide(self.worker_intent(run))
        self.assertEqual((decision['outcome'], decision['rule']),
                         ('INVALID_CONTEXT', 'worker-not-active'))
        unknown = self.authz.decide(self.worker_intent({'id': 'no-such-run'}))
        self.assertEqual(unknown['outcome'], 'INVALID_CONTEXT')

    def test_worker_outside_the_repository_asks_once_then_grant_resumes(self):
        run = self.claim_run()
        outside = self.authz.decide(self.worker_intent(run, target=str(self.other)))
        self.assertEqual(outside['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        request_id = outside['boundary_request_id']
        self.assertTrue(request_id)
        requests = Autonomy(self.store).requests(self.lease_id)
        self.assertEqual([r['status'] for r in requests], ['PENDING'])
        # Real sequence: the worker returns BLOCKED and its run settles before the job is blocked.
        with self.store.transaction() as db:
            db.execute("UPDATE runs SET state='RESULT_RECORDED' WHERE id=?", (run['id'],))
            job_row = self.store._get(db, self.job)
            job_row['milestones']['code'].update(state='NEEDS_REPAIR')
            self.store._save(db, job_row, 'test.worker-blocked')
        blocked = block_job(self.store, self.job, 'code', outside)
        self.assertTrue(blocked)
        job = self.store.get(self.job)
        self.assertEqual(job['state'], 'AWAITING_USER')
        self.assertIn('authorization', (job['milestones']['code']['error'] or '').lower())
        with contextlib.closing(self.store.connect()) as db:
            messages = db.execute("SELECT COUNT(*) FROM messages WHERE job_id=? AND role='assistant'",
                                  (self.job,)).fetchone()[0]
        self.assertGreaterEqual(messages, 1)  # the authorization notice is linked to the job
        Autonomy(self.store).resolve_expansion(request_id, allow=True, grant_kind='project')
        self.assertTrue(resume_after_grant(self.store, request_id))
        job = self.store.get(self.job)
        self.assertEqual(job['state'], 'READY')
        self.assertIsNone(job['authz'])
        self.assertIsNone(job['milestones']['code']['error'])
        reused = self.authz.decide(self.intent(action_kind='repo', tool='git',
                                               target=str(self.other / 'src')))
        self.assertEqual(reused['outcome'], 'ALLOW')

    def test_denied_boundary_request_is_not_reasked(self):
        run = self.claim_run()
        first = self.authz.decide(self.worker_intent(run, target=str(self.other / 'sub')))
        self.assertEqual(first['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        Autonomy(self.store).resolve_expansion(first['boundary_request_id'], allow=False)
        again = self.authz.decide(self.worker_intent(run, target=str(self.other / 'sub')))
        self.assertEqual((again['outcome'], again['rule']), ('DENY', 'boundary-denied'))
        # A different target is a new, legitimate question (asked once per target).
        fresh = self.authz.decide(self.worker_intent(run, target=str(self.other / 'sub2')))
        self.assertEqual(fresh['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')

    def test_allow_once_grant_is_consumed_exactly_once(self):
        run = self.claim_run()
        third = self.base / 'third'
        third.mkdir()
        first = self.authz.decide(self.worker_intent(run, target=str(third)))
        Autonomy(self.store).resolve_expansion(first['boundary_request_id'], allow=True,
                                               grant_kind='once')
        consumed = self.authz.decide(self.worker_intent(run, target=str(third)))
        self.assertEqual(consumed['outcome'], 'ALLOW')
        reused = self.authz.decide(self.worker_intent(run, target=str(third / 'b.txt')))
        self.assertEqual((reused['outcome'], reused['rule']), ('DENY', 'grant-used'))


class RolePolicyTests(AuthorizeBase):
    def test_role_policy_narrows_the_lease(self):
        team = Team(self.store)
        team.define_role('strict-role', 'Strict Role', 'Engineering',
                         {'goal': 'Inspect only.', 'outputs': 'notes', 'quality_bar': 'exact',
                          'tool_policy': {'allow': ['read'], 'deny': ['git', 'run_tests']},
                          'budget': 5})
        denied = self.authz.decide(self.intent(action_kind='repo', tool='git',
                                               target=str(self.project), role='strict-role'))
        self.assertEqual((denied['outcome'], denied['rule']), ('DENY', 'role-policy'))
        team.define_role('wide-role', 'Wide Role', 'Engineering',
                         {'goal': 'Implement.', 'outputs': 'code', 'quality_bar': 'tests pass',
                          'tool_policy': {'allow': ['read', 'write', 'git', 'run_tests'],
                                          'deny': []}, 'budget': 12})
        allowed = self.authz.decide(self.intent(action_kind='repo', tool='git',
                                                target=str(self.project), role='wide-role'))
        self.assertEqual(allowed['outcome'], 'ALLOW', allowed)


class EngineGateTests(AuthorizeBase):
    def test_claim_gate_blocks_after_a_targeted_revoke(self):
        engine = Engine(self.store, {'fixture': FixtureAdapter()})
        try:
            Autonomy(self.store).revoke(self.lease_id, 'task finished')
            engine.tick()
            job = self.store.get(self.job)
            self.assertEqual(job['state'], 'AWAITING_USER')
            self.assertIn('revoked', (job['milestones']['code']['error'] or '').lower())
            with contextlib.closing(self.store.connect()) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 0)
        finally:
            engine.close()

    def test_claim_gate_allows_leased_coding_work(self):
        class CodingProbe:
            capabilities = {'text', 'repository_edit'}

            def execute(self, prompt, run_id=None, session_id=None, cancel=None):
                return {'outcome': 'FAILED', 'error': 'probe'}

        engine = Engine(self.store, {'codex-code': CodingProbe()})
        try:
            engine.tick()
            with contextlib.closing(self.store.connect()) as db:
                runs = db.execute('SELECT COUNT(*) FROM runs WHERE job_id=?',
                                  (self.job,)).fetchone()[0]
            self.assertGreaterEqual(runs, 1, 'a leased coding job must be allowed to claim')
        finally:
            engine.close()

    def test_resumed_work_after_an_emergency_stop_is_reissued_a_lease(self):
        autonomy = Autonomy(self.store)
        autonomy.emergency_stop()
        self.assertEqual(self.store.get(self.job)['state'], 'PAUSED')
        self.store.control(self.job, 'resume')
        job = self.store.get(self.job)
        lease_id, failure = ensure_job_lease(self.store, job)
        self.assertIsNone(failure)
        self.assertNotEqual(lease_id, self.lease_id)
        self.assertEqual(autonomy.latest_lease(self.job)['state'], 'ACTIVE')


class ApplicationGateTests(AuthorizeBase):
    def test_apply_refuses_without_authorization(self):
        from kel.apply_changes import apply_checked
        Autonomy(self.store).revoke(self.lease_id, 'task finished')
        with self.assertRaises(PolicyError) as caught:
            apply_checked(self.store, self.job)
        self.assertIn('not authorized', str(caught.exception))
        self.assertEqual((self.project / 'app.txt').read_text(), 'old')


class ServiceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            self.service = Service(self.root / 'data')
        self.service.stop.set()

    def tearDown(self):
        self.service.shutdown()
        self.tmp.cleanup()

    def test_payload_actor_identity_is_rejected_on_every_route(self):
        payloads = [
            ('/api/send', {'text': 'hello', 'actor': 'user'}),
            ('/api/control', {'job': 'x', 'action': 'pause', 'actor': 'kel'}),
            ('/api/team', {'action': 'roster', 'actor': 'kel'}),
            ('/api/apply', {'job': 'x', 'actor': 'user'}),
            ('/api/approval', {'id': 'x', 'allow': True, 'actor': 'user'}),
            ('/api/autonomy', {'action': 'emergency_stop', 'actor': 'worker'}),
        ]
        for path, payload in payloads:
            with self.assertRaises(PolicyError, msg=path):
                self.service.action(path, payload)

    def test_actor_free_payloads_still_work(self):
        result = self.service.action('/api/autonomy', {'action': 'guardrails'})
        self.assertTrue(result['rules'])


class AdapterEffectPointTests(unittest.TestCase):
    """The coding adapter is the real effect point; a revoked lease stops it before any change."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.store = Store(base / 'data')
        self.project = make_project(base, 'proj')
        self.job = self.store.create(compile_coding('Change app.txt.', self.project,
                                                    ['python', '-m', 'unittest']))

    def tearDown(self):
        self.tmp.cleanup()

    def test_coding_dispatch_is_blocked_after_the_lease_is_revoked(self):
        run = self.store.claim(self.job, 'code', provider='codex-code')
        lease_id = Autonomy(self.store).latest_lease(self.job)['lease_id']
        Autonomy(self.store).revoke(lease_id, 'task finished')
        from kel.coding import CodingAdapter
        result = CodingAdapter(self.store).execute('Change app.txt.', run_id=run['id'],
                                                   session_id=None, cancel=None)
        self.assertEqual(result['outcome'], 'BLOCKED')
        self.assertIn('revoked', result['error'].lower())
        self.assertEqual(result['authorization'], 'REVOKED_LEASE')
        with contextlib.closing(self.store.connect()) as db:
            workspaces = db.execute('SELECT COUNT(*) FROM code_workspaces').fetchone()[0]
        self.assertEqual(workspaces, 0)  # nothing was copied, cloned, or changed


if __name__ == '__main__':
    unittest.main()
