"""V1.4 Gate 6: capability leases, boundary expansion, guardrail enforcement (AUTO-*).

These tests are the enforcement proof for docs/v1.4/KEL_V1.4_AUTONOMY_POLICY.md §8.
"""
import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kel.autonomy import Autonomy, BLOCKED_KINDS, KINDS
from kel.core import PolicyError, Store


class AutonomyBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root)
        self.autonomy = Autonomy(self.store)
        self.workspace = self.root / 'fixture-project'
        self.workspace.mkdir()
        self.other = self.root / 'other-project'
        self.other.mkdir()
        self.lease = self.autonomy.issue(
            'job-1', review_ref='brief:approved',
            roots=[str(self.workspace)], repositories=[str(self.workspace)],
            domains=['docs.python.org'], tools=['read', 'write', 'run_tests'])
        self.lease_id = self.lease['lease_id']

    def tearDown(self):
        self.tmp.cleanup()


class BoundaryScopeTests(AutonomyBase):
    def test_unknown_boundary_scope_is_refused(self):
        # D16: a scope literal that can never match a check (e.g. the plural 'roots') would create a
        # grant that quietly never applies — refuse it instead of filing a dead request.
        with self.assertRaises(PolicyError):
            self.autonomy.request_expansion(self.lease_id, 'roots', str(self.other))
        self.assertEqual(len(self.autonomy.requests(self.lease_id)), 0)

    def test_the_kinds_that_can_match_are_accepted(self):
        before = len(self.autonomy.requests(self.lease_id))
        for scope in ('root', 'repo', 'domain', 'tool', 'external'):
            self.autonomy.request_expansion(self.lease_id, scope, str(self.other))
        self.assertEqual(len(self.autonomy.requests(self.lease_id)), before + 5)


class LeaseIssueTests(AutonomyBase):
    def test_a_reviewed_plan_is_required(self):
        with self.assertRaises(PolicyError):
            self.autonomy.issue('job-2', review_ref='', roots=[str(self.workspace)])

    def test_at_least_one_root_is_required(self):
        with self.assertRaises(PolicyError):
            self.autonomy.issue('job-2', review_ref='brief:approved', roots=[])

    def test_a_root_that_does_not_exist_is_refused(self):
        with self.assertRaises(PolicyError):
            self.autonomy.issue('job-2', review_ref='brief:approved',
                                roots=[str(self.root / 'not-here')])

    def test_frozen_releases_cannot_be_leased(self):
        frozen = self.root / 'Kel Releases'
        frozen.mkdir()
        with self.assertRaises(PolicyError):
            self.autonomy.issue('job-2', review_ref='brief:approved', roots=[str(frozen)])

    def test_system_locations_cannot_be_leased(self):
        with self.assertRaises(PolicyError):
            self.autonomy.issue('job-2', review_ref='brief:approved', roots=['C:\\Windows'])

    def test_roles_are_narrow_until_asked(self):
        lease = self.autonomy.leases('job-1')
        self.assertEqual(len(lease), 1)
        self.assertEqual(lease[0]['state'], 'ACTIVE')
        self.assertFalse(lease[0]['expired'])
        pairs = sorted((item['kind'], item['value']) for item in lease[0]['scope'])
        self.assertEqual(sorted({kind for kind, _value in pairs}),
                         ['domain', 'repo', 'root', 'tool'])
        self.assertIn(('tool', 'run_tests'), pairs)
        self.assertIn(('tool', 'read'), pairs)
        self.assertIn(('domain', 'docs.python.org'), pairs)
        self.assertIn(('root', str(self.workspace.resolve())), pairs)


class EnforcementTests(AutonomyBase):
    def test_write_inside_the_lease_is_allowed_without_prompting(self):
        inside = self.workspace / 'src' / 'main.py'
        result = self.autonomy.check(self.lease_id, 'write', target=str(inside))
        self.assertTrue(result['allowed'])
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT COUNT(*) AS n FROM approvals').fetchone()
        self.assertEqual(rows['n'], 0)

    def test_write_outside_the_lease_is_denied(self):
        outside = self.other / 'src' / 'main.py'
        result = self.autonomy.check(self.lease_id, 'write', target=str(outside))
        self.assertFalse(result['allowed'])
        self.assertEqual(result['rule'], 'lease-scope')

    def test_repository_scope_matches_the_leased_repository_only(self):
        allowed = self.autonomy.check(self.lease_id, 'repo', target=str(self.workspace))
        denied = self.autonomy.check(self.lease_id, 'repo', target=str(self.other))
        self.assertTrue(allowed['allowed'])
        self.assertFalse(denied['allowed'])

    def test_browser_domains_are_limited_to_the_lease(self):
        allowed = self.autonomy.check(self.lease_id, 'browser', target='docs.python.org')
        subdomain = self.autonomy.check(self.lease_id, 'browser', target='www.docs.python.org')
        denied = self.autonomy.check(self.lease_id, 'browser', target='evil.example.com')
        self.assertTrue(allowed['allowed'])
        self.assertTrue(subdomain['allowed'])
        self.assertFalse(denied['allowed'])

    def test_tools_fail_closed(self):
        allowed = self.autonomy.check(self.lease_id, 'tool', tool='run_tests')
        denied = self.autonomy.check(self.lease_id, 'tool', tool='shell')
        self.assertTrue(allowed['allowed'])
        self.assertFalse(denied['allowed'])
        self.assertEqual(denied['rule'], 'lease-scope')

    def test_locked_guardrail_kinds_are_never_allowed(self):
        for kind, rule in BLOCKED_KINDS.items():
            result = self.autonomy.check(self.lease_id, kind, target='anything')
            self.assertFalse(result['allowed'], kind)
            self.assertEqual(result['rule'], rule)

    def test_unknown_action_kinds_are_denied(self):
        result = self.autonomy.check(self.lease_id, 'teleport', target='anything')
        self.assertFalse(result['allowed'])
        self.assertEqual(result['rule'], 'kind-unknown')

    def test_frozen_paths_are_denied_even_inside_a_leased_root(self):
        frozen = self.workspace / 'Kel Releases' / 'Kel-V1.3-Frozen'
        result = self.autonomy.check(self.lease_id, 'write', target=str(frozen / 'Kel.exe'))
        self.assertFalse(result['allowed'])
        self.assertEqual(result['rule'], 'frozen-immutable')

    def test_destructive_actions_need_a_snapshot_reference(self):
        without = self.autonomy.check(self.lease_id, 'destructive',
                                      target=str(self.workspace / 'old.db'))
        with_snapshot = self.autonomy.check(self.lease_id, 'destructive',
                                           target=str(self.workspace / 'old.db'),
                                           destructive_snapshot='backup:old.db.20260915')
        self.assertFalse(without['allowed'])
        self.assertEqual(without['rule'], 'destructive-snapshot')
        self.assertTrue(with_snapshot['allowed'])

    def test_expired_leases_deny_everything(self):
        short = self.autonomy.issue('job-3', review_ref='brief:approved',
                                    roots=[str(self.workspace)], seconds=0.01)
        import time
        time.sleep(0.05)
        result = self.autonomy.check(short['lease_id'], 'write',
                                     target=str(self.workspace / 'late.txt'))
        self.assertFalse(result['allowed'])
        self.assertEqual(result['rule'], 'lease-expired')

    def test_revoked_and_unknown_leases_deny(self):
        self.autonomy.revoke(self.lease_id, 'task finished')
        revoked = self.autonomy.check(self.lease_id, 'write', target=str(self.workspace / 'a.txt'))
        unknown = self.autonomy.check('no-such-lease', 'write', target=str(self.workspace / 'a.txt'))
        self.assertFalse(revoked['allowed'])
        self.assertEqual(revoked['rule'], 'lease-revoked')
        self.assertFalse(unknown['allowed'])
        self.assertEqual(unknown['rule'], 'lease-unknown')

    def test_every_action_kind_is_covered_by_the_policy(self):
        self.assertIn('write', KINDS)
        self.assertIn('destructive', KINDS)
        for kind in BLOCKED_KINDS:
            self.assertNotIn(kind, KINDS)


class ExpansionTests(AutonomyBase):
    def test_a_denied_request_leaves_the_target_blocked(self):
        request = self.autonomy.request_expansion(self.lease_id, 'root', str(self.other),
                                                  what='another repository',
                                                  why='the fix lives there',
                                                  benefit='complete the task',
                                                  fallback='stop and report',
                                                  risk='writes outside the reviewed project')
        self.assertEqual(self.autonomy.resolve_expansion(request['request_id'],
                                                        allow=False)['status'], 'DENIED')
        result = self.autonomy.check(self.lease_id, 'write', target=str(self.other / 'x.py'))
        self.assertFalse(result['allowed'])

    def test_a_one_time_grant_is_used_exactly_once(self):
        request = self.autonomy.request_expansion(self.lease_id, 'root', str(self.other))
        self.autonomy.resolve_expansion(request['request_id'], allow=True, grant_kind='once')
        first = self.autonomy.check(self.lease_id, 'write', target=str(self.other / 'x.py'))
        second = self.autonomy.check(self.lease_id, 'write', target=str(self.other / 'y.py'))
        self.assertTrue(first['allowed'])
        self.assertFalse(second['allowed'])
        self.assertEqual(second['rule'], 'grant-used')

    def test_a_project_grant_covers_repeated_use(self):
        request = self.autonomy.request_expansion(self.lease_id, 'root', str(self.other))
        self.autonomy.resolve_expansion(request['request_id'], allow=True, grant_kind='project')
        for name in ('a.py', 'b.py', 'c.py'):
            result = self.autonomy.check(self.lease_id, 'write', target=str(self.other / name))
            self.assertTrue(result['allowed'])

    def test_only_the_user_can_resolve_a_boundary_request(self):
        request = self.autonomy.request_expansion(self.lease_id, 'root', str(self.other))
        with self.assertRaises(PolicyError):
            self.autonomy.resolve_expansion(request['request_id'], allow=True, actor='kel')

    def test_a_request_can_only_be_resolved_once(self):
        request = self.autonomy.request_expansion(self.lease_id, 'root', str(self.other))
        self.autonomy.resolve_expansion(request['request_id'], allow=True)
        with self.assertRaises(PolicyError):
            self.autonomy.resolve_expansion(request['request_id'], allow=False)

    def test_requests_are_recorded_for_the_receipt(self):
        self.autonomy.request_expansion(self.lease_id, 'domain', 'github.com',
                                        why='open the pull request')
        rows = self.autonomy.requests(self.lease_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['target'], 'github.com')
        self.assertEqual(rows[0]['why'], 'open the pull request')
        self.assertEqual(rows[0]['status'], 'PENDING')


class GuardrailTests(AutonomyBase):
    def test_the_locked_block_is_presented_read_only(self):
        rules = self.autonomy.guardrails()
        self.assertGreaterEqual(len(rules), 14)
        self.assertTrue(all('rule' in row and 'text' in row and 'test' in row for row in rules))

    def test_weakened_rules_are_detected(self):
        weakened = (('no-registry-write', 'Registry writes allowed.', 'AUTO-BLOCK-REG'),)
        with mock.patch('kel.autonomy.RULES', weakened):
            with self.assertRaises(PolicyError):
                self.autonomy.assert_intact()
            with self.assertRaises(PolicyError):
                self.autonomy.check(self.lease_id, 'write', target=str(self.workspace / 'x'))

    def test_emergency_stop_revokes_every_active_lease(self):
        second = self.autonomy.issue('job-9', review_ref='brief:approved',
                                     roots=[str(self.other)])
        stopped = self.autonomy.emergency_stop()
        self.assertEqual(stopped['count'], 2)
        self.assertIn(self.lease_id, stopped['stopped'])
        self.assertIn(second['lease_id'], stopped['stopped'])
        after = self.autonomy.check(self.lease_id, 'write', target=str(self.workspace / 'x'))
        self.assertFalse(after['allowed'])

    def test_only_the_user_can_trigger_an_emergency_stop(self):
        with self.assertRaises(PolicyError):
            self.autonomy.emergency_stop(actor='kel')

    def test_apply_envelope_covers_the_service_actions(self):
        listed = self.autonomy.apply({'action': 'leases'})
        self.assertEqual(len(listed['leases']), 1)
        checked = self.autonomy.apply({'action': 'check', 'lease_id': self.lease_id,
                                       'kind': 'write',
                                       'target': str(self.workspace / 'main.py')})
        self.assertTrue(checked['allowed'])
        rules = self.autonomy.apply({'action': 'guardrails'})
        self.assertTrue(rules['digest'])
        with self.assertRaises(PolicyError):
            self.autonomy.apply({'action': 'not-an-action'})

    def test_lease_events_record_allow_and_deny(self):
        self.autonomy.check(self.lease_id, 'write', target=str(self.workspace / 'ok.txt'))
        self.autonomy.check(self.lease_id, 'write', target=str(self.other / 'no.txt'))
        with contextlib.closing(self.store.connect()) as db:
            rows = list(db.execute('SELECT kind FROM lease_events WHERE lease_id=? ORDER BY seq',
                                   (self.lease_id,)))
        kinds = [row['kind'] for row in rows]
        self.assertIn('issued', kinds)
        self.assertIn('allowed', kinds)
        self.assertIn('denied', kinds)
