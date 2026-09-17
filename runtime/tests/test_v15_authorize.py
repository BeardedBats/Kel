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

    def test_approval_from_another_job_is_not_this_jobs_approval(self):
        action = {'kind': 'delete-backup', 'target': 'old.db'}
        with self.store.transaction() as db:
            db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?)',
                       ('other-approval', 'some-other-job', None, digest(action), 'APPROVED',
                        time.time() + 300, 'user'))
        decision = self.authz.decide(self.intent(
            action_kind='destructive', target=str(self.project / 'old.db'),
            snapshot_ref='backup:old.db', approval_id='other-approval',
            metadata={'action': action}))
        self.assertEqual(decision['outcome'], 'REQUIRES_USER_APPROVAL')

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
        # Phase 3 (in-chat approvals): the pause notice is plain language - no 'authorization',
        # no raw ids - and it is linked to the request so chat shows the decision card in place.
        self.assertIn('permission', (job['milestones']['code']['error'] or '').lower())
        with contextlib.closing(self.store.connect()) as db:
            messages = db.execute("SELECT COUNT(*) FROM messages WHERE job_id=? AND role='assistant'",
                                  (self.job,)).fetchone()[0]
            announcement = db.execute(
                "SELECT message_seq FROM approval_announcements WHERE kind='access' AND ref_id=?",
                (request_id,)).fetchone()
        self.assertGreaterEqual(messages, 1)  # the permission notice is linked to the job
        self.assertTrue(announcement)  # ... and to the request the decision card resolves
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
            # Plain copy: the user reads why the work stopped, not the internal rule id.
            self.assertIn('no longer active', (job['milestones']['code']['error'] or '').lower())
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

    def test_lease_issuance_is_not_available_through_the_shell(self):
        with self.assertRaises(PolicyError):
            self.service.action('/api/autonomy', {'action': 'issue', 'job_id': 'x',
                                                  'review_ref': 'attacker', 'roots': [str(self.root)]})

    def test_greenfield_project_creation_crosses_the_boundary(self):
        home = self.root / 'home'
        (home / 'Documents' / 'Kel Projects').mkdir(parents=True)
        packet = {'project': {'root': None, 'id': None}, 'files': []}
        with mock.patch.object(Path, 'home', return_value=home):
            self.service._plan('sid-allow', 'main', 'create a tiny app', dict(packet),
                               kind='coding', greenfield_flag=True)
        with contextlib.closing(self.service.store.connect()) as db:
            projects = [dict(r) for r in db.execute('SELECT * FROM projects')]
        self.assertTrue(any('Kel Projects' in (r['root'] or '') for r in projects),
                        'an authorized request creates the project folder')
        self.assertTrue(any(j.get('contract', {}).get('greenfield')
                            for j in self.service.store.list_jobs()))
        # A target outside the Kel Projects root is refused and nothing is created.
        before = len(projects)
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
                       ('sid-deny', 'main', 'create another tiny app', 'PLANNING', None, None,
                        time.time()))
        with mock.patch.object(Path, 'home', return_value=home), \
                mock.patch('kel.authorize.project_creation_root',
                           return_value=(home / 'elsewhere').resolve()):
            self.service._plan('sid-deny', 'main', 'create another tiny app', dict(packet),
                               kind='coding', greenfield_flag=True)
        with contextlib.closing(self.service.store.connect()) as db:
            row = db.execute('SELECT * FROM submissions WHERE id=?', ('sid-deny',)).fetchone()
            after = db.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
        self.assertEqual(row['state'], 'FAILED')
        self.assertIn('project folder', (row['error'] or '').lower())
        self.assertEqual(after, before, 'a denied creation leaves no project behind')


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


class FailClosedTests(AuthorizeBase):
    def test_malformed_contexts_fail_closed(self):
        cases = [
            ({'actor': 'robot', 'action_kind': 'write', 'target': str(self.project)},
             'INVALID_CONTEXT', 'actor-unknown'),
            ({'actor': 'kel', 'action_kind': 'teleport', 'target': 'x'},
             'INVALID_CONTEXT', 'kind-unknown'),
            ({'actor': 'kel', 'job': 'no-such-job', 'action_kind': 'write',
              'target': str(self.project)}, 'INVALID_CONTEXT', 'job-unknown'),
            ({'actor': 'kel', 'job': self.job, 'milestone': 'ghost', 'action_kind': 'write',
              'target': str(self.project)}, 'INVALID_CONTEXT', 'milestone-unknown'),
            ({'actor': 'kel', 'job': self.job, 'action_kind': 'write', 'target': '  '},
             'DENY', 'target-required'),
            ({'actor': 'worker', 'worker': 'no-such-run', 'job': self.job,
              'action_kind': 'repo', 'tool': 'git', 'target': str(self.project)},
             'INVALID_CONTEXT', 'worker-not-active'),
        ]
        for intent, outcome, rule in cases:
            decision = self.authz.decide(intent)
            self.assertEqual((decision['outcome'], decision['rule']), (outcome, rule), intent)

    def test_worker_and_lease_identity_forgery_is_invalid(self):
        run = self.claim_run()
        wrong_milestone = self.authz.decide({'actor': 'worker', 'worker': run['id'],
                                             'job': self.job, 'milestone': 'other',
                                             'action_kind': 'repo', 'tool': 'git',
                                             'target': str(self.project)})
        self.assertEqual(wrong_milestone['rule'], 'worker-milestone-mismatch')
        other_job = self.store.create(compile_coding('Other work.', self.other,
                                                     ['python', '-m', 'unittest']))
        other_lease = Autonomy(self.store).latest_lease(other_job)['lease_id']
        borrowed = self.authz.decide({'actor': 'kel', 'job': self.job, 'action_kind': 'write',
                                      'target': str(self.project / 'x.txt'),
                                      'lease_id': other_lease})
        self.assertEqual((borrowed['outcome'], borrowed['rule']),
                         ('INVALID_CONTEXT', 'lease-mismatch'))

    def test_unknown_role_is_denied(self):
        decision = self.authz.decide(self.intent(action_kind='repo', tool='git',
                                                 target=str(self.project), role='ghost-role'))
        self.assertEqual((decision['outcome'], decision['rule']), ('DENY', 'role-unknown'))


class ExpansionScopeTests(AuthorizeBase):
    def test_unauthorized_domain_asks_once(self):
        lease = Autonomy(self.store).issue(self.job, review_ref='kel-contract:test',
                                           roots=[str(self.project)], domains=['docs.python.org'])
        allowed = self.authz.decide({'actor': 'kel', 'job': self.job, 'action_kind': 'browser',
                                     'target': 'docs.python.org', 'lease_id': lease['lease_id']})
        self.assertEqual(allowed['outcome'], 'ALLOW')
        denied = self.authz.decide({'actor': 'kel', 'job': self.job, 'action_kind': 'browser',
                                    'target': 'evil.example.com', 'lease_id': lease['lease_id']})
        self.assertEqual(denied['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        requests = Autonomy(self.store).requests(lease['lease_id'])
        self.assertEqual((requests[0]['scope'], requests[0]['target']),
                         ('domain', 'evil.example.com'))

    def test_unauthorized_tool_asks_once(self):
        decision = self.authz.decide(self.intent(action_kind='tool', tool='shell', target=''))
        self.assertEqual(decision['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        requests = Autonomy(self.store).requests(self.lease_id)
        self.assertEqual((requests[0]['scope'], requests[0]['target']), ('tool', 'shell'))

    def test_revoked_project_grant_is_asked_again_not_silently_allowed(self):
        run = self.claim_run()
        third = self.base / 'third'
        third.mkdir()
        base = {'actor': 'worker', 'worker': run['id'], 'job': self.job, 'milestone': 'code',
                'action_kind': 'repo', 'tool': 'git', 'target': str(third)}
        first = self.authz.decide(base)
        Autonomy(self.store).resolve_expansion(first['boundary_request_id'], allow=True,
                                               grant_kind='project')
        self.assertEqual(self.authz.decide(base)['outcome'], 'ALLOW')
        with self.store.transaction() as db:
            db.execute('DELETE FROM lease_scope WHERE lease_id=? AND kind=? AND value=?',
                       (self.lease_id, 'repo', str(third)))
        after = self.authz.decide(base)
        self.assertEqual(after['outcome'], 'REQUIRES_BOUNDARY_EXPANSION',
                         'a revoked grant returns to asking, never to a silent allow')


class RestartResumeTests(AuthorizeBase):
    def test_restarted_engine_reevaluates_against_durable_state(self):
        Autonomy(self.store).revoke(self.lease_id, 'revoked while offline')
        restarted = Store(self.store.root)
        decision = Authorizer(restarted).decide({'actor': 'kel', 'job': self.job,
                                                 'action_kind': 'write',
                                                 'target': str(self.project / 'x.txt')})
        self.assertEqual(decision['outcome'], 'REVOKED_LEASE',
                         'stale in-memory authorization must not survive a restart')

    def test_resumed_after_emergency_stop_requires_current_durable_rules(self):
        Autonomy(self.store).emergency_stop()
        restarted = Store(self.store.root)
        self.assertEqual(restarted.get(self.job)['state'], 'PAUSED')
        decision = Authorizer(restarted).decide({'actor': 'kel', 'job': self.job,
                                                 'action_kind': 'repo',
                                                 'target': str(self.project)})
        self.assertEqual(decision['outcome'], 'REVOKED_LEASE')
        restarted.control(self.job, 'resume')
        lease_id, failure = ensure_job_lease(restarted, restarted.get(self.job))
        self.assertIsNone(failure)
        self.assertNotEqual(lease_id, self.lease_id)

    def test_expired_lease_stops_a_resumed_worker_at_the_effect_point(self):
        run = self.claim_run()
        with self.store.transaction() as db:
            db.execute('UPDATE capability_leases SET expires_at=0 WHERE lease_id=?',
                       (self.lease_id,))
        from kel.coding import CodingAdapter
        result = CodingAdapter(self.store).execute('Change app.txt.', run_id=run['id'],
                                                   session_id=None, cancel=None)
        self.assertEqual(result['outcome'], 'BLOCKED')
        self.assertEqual(result['authorization'], 'EXPIRED_LEASE')
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM code_workspaces').fetchone()[0], 0)

    def test_emergency_stop_stops_the_worker_effect_point(self):
        run = self.claim_run()
        Autonomy(self.store).emergency_stop()
        from kel.coding import CodingAdapter
        result = CodingAdapter(self.store).execute('Change app.txt.', run_id=run['id'],
                                                   session_id=None, cancel=None)
        self.assertEqual(result['outcome'], 'BLOCKED')
        # The stop marks the run CANCEL_REQUESTED (worker no longer live) before the lease check;
        # either way no effect may occur.
        self.assertIn(result['authorization'], ('INVALID_CONTEXT', 'REVOKED_LEASE'))

    def test_role_changes_apply_immediately_without_restart_caches(self):
        team = Team(self.store)
        team.define_role('fresh-role', 'Fresh Role', 'Engineering',
                         {'goal': 'Work.', 'outputs': 'code', 'quality_bar': 'tests pass',
                          'tool_policy': {'allow': ['read', 'git'], 'deny': []}, 'budget': 8})
        before = self.authz.decide(self.intent(action_kind='repo', tool='git',
                                               target=str(self.project), role='fresh-role'))
        self.assertEqual(before['outcome'], 'ALLOW')
        team.edit_role('fresh-role', {'tool_policy': {'allow': ['read'], 'deny': ['git']}})
        restarted = Store(self.store.root)
        after = Authorizer(restarted).decide(self.intent(action_kind='repo', tool='git',
                                                         target=str(self.project),
                                                         role='fresh-role'))
        self.assertEqual((after['outcome'], after['rule']), ('DENY', 'role-policy'))


class ParallelIsolationTests(AuthorizeBase):
    def test_unauthorized_worker_does_not_disturb_an_authorized_one(self):
        run_a = self.claim_run()
        job_b = self.store.create(compile_coding('Change other.txt.', self.other,
                                                 ['python', '-m', 'unittest']))
        run_b = self.store.claim(job_b, 'code', provider='codex-code')
        lease_b = Autonomy(self.store).latest_lease(job_b)['lease_id']
        intent_a = {'actor': 'worker', 'worker': run_a['id'], 'job': self.job,
                    'milestone': 'code', 'action_kind': 'repo', 'tool': 'git',
                    'target': str(self.project)}
        intent_b = {'actor': 'worker', 'worker': run_b['id'], 'job': job_b,
                    'milestone': 'code', 'action_kind': 'repo', 'tool': 'git',
                    'target': str(self.project)}
        self.assertEqual(self.authz.decide(intent_a)['outcome'], 'ALLOW')
        intrude = self.authz.decide(intent_b)
        self.assertEqual(intrude['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        self.assertEqual(self.authz.decide(intent_a)['outcome'], 'ALLOW',
                         'worker A keeps its authority while worker B is denied')
        self.assertEqual(Autonomy(self.store).requests(self.lease_id), [])
        self.assertEqual(len(Autonomy(self.store).requests(lease_b)), 1)
        own = dict(intent_b, target=str(self.other))
        self.assertEqual(self.authz.decide(own)['outcome'], 'ALLOW',
                         'worker B keeps its own scope')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT state FROM capability_leases WHERE lease_id=?',
                             (self.lease_id,)).fetchone()
        self.assertEqual(row['state'], 'ACTIVE')


class ProjectCreationPolicyTests(AuthorizeBase):
    def test_user_project_creation_is_confined_and_actor_bound(self):
        allowed_root = self.base / 'home' / 'Documents' / 'Kel Projects'
        allowed_root.mkdir(parents=True)
        with mock.patch('kel.authorize.project_creation_root',
                        return_value=allowed_root.resolve()):
            allowed = self.authz.decide({'actor': 'user', 'action_kind': 'write',
                                         'target': str(allowed_root / 'app-1'),
                                         'metadata': {'operation': 'create-project'}})
            outside = self.authz.decide({'actor': 'user', 'action_kind': 'write',
                                         'target': str(self.base / 'elsewhere'),
                                         'metadata': {'operation': 'create-project'}})
            forged = self.authz.decide({'actor': 'kel', 'action_kind': 'write',
                                        'target': str(allowed_root / 'app-2'),
                                        'metadata': {'operation': 'create-project'}})
            frozen = self.authz.decide({'actor': 'user', 'action_kind': 'write',
                                        'target': str(allowed_root / 'Kel-V1.3-Frozen' / 'app'),
                                        'metadata': {'operation': 'create-project'}})
        self.assertEqual((allowed['outcome'], allowed['rule']),
                         ('ALLOW', 'user-project-create'))
        self.assertEqual((outside['outcome'], outside['rule']),
                         ('DENY', 'project-create-scope'))
        self.assertEqual((forged['outcome'], forged['rule']), ('DENY', 'lease-required'),
                         'only the user actor carries creation authority')
        self.assertEqual((frozen['outcome'], frozen['rule']), ('DENY', 'frozen-immutable'))


class NativeTrustBoundaryTests(unittest.TestCase):
    def test_readonly_codex_agent_flags_are_pinned(self):
        from kel.native import NativeAdapter
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        adapter = NativeAdapter('codex', Path(tmp.name) / 'ws', Path(tmp.name) / 'logs')
        joined = ' '.join(adapter.argv())
        self.assertIn('sandbox_mode="read-only"', joined)
        self.assertIn('approval_policy="never"', joined)
        self.assertIn('--disable', joined)
        self.assertIn('-s read-only', joined)


class InternalWorkerBoundaryTests(unittest.TestCase):
    """G2 case 22: the internal worker cannot spawn agents; its allowlist refuses everything else."""

    def test_internal_worker_cannot_spawn_agents(self):
        from kel.internal import InternalAdapter

        def transport(body, timeout):
            return {'content': [{'type': 'tool_use', 'id': 't1', 'name': 'spawn_agent',
                                 'input': {}}],
                    'usage': {'output_tokens': 1}}

        adapter = InternalAdapter(transport=transport, timeout=30)
        result = adapter.execute('Do the task.')
        self.assertEqual(result['outcome'], 'FAILED')
        self.assertIn('Tool denied: spawn_agent', result['error'])


class ActiveWorkDenialTests(AuthorizeBase):
    """G2 case 25: a denial during active work is announced once and never touches the live run."""

    def test_denial_during_active_work_is_announced_once_and_never_touches_the_run(self):
        run = self.claim_run()
        third = self.base / 'third'
        third.mkdir()
        decision = self.authz.decide({'actor': 'worker', 'worker': run['id'], 'job': self.job,
                                      'milestone': 'code', 'action_kind': 'repo', 'tool': 'git',
                                      'target': str(third)})
        self.assertEqual(decision['outcome'], 'REQUIRES_BOUNDARY_EXPANSION')
        self.assertTrue(block_job(self.store, self.job, 'code', decision))
        with contextlib.closing(self.store.connect()) as db:
            first = db.execute("SELECT COUNT(*) FROM messages WHERE job_id=? AND role='assistant'",
                               (self.job,)).fetchone()[0]
            run_state = db.execute('SELECT state FROM runs WHERE id=?', (run['id'],)).fetchone()[0]
        self.assertEqual(run_state, 'RUNNING', 'a denial never cancels a live run')
        self.assertEqual(self.store.get(self.job)['state'], 'RUNNING',
                         'the job stays live while its run is')
        self.assertFalse(block_job(self.store, self.job, 'code', decision))
        with contextlib.closing(self.store.connect()) as db:
            second = db.execute("SELECT COUNT(*) FROM messages WHERE job_id=? AND role='assistant'",
                                (self.job,)).fetchone()[0]
        self.assertEqual(first, second, 'no repeated announcement for the same block')


if __name__ == '__main__':
    unittest.main()
