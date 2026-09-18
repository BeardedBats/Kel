"""Round 2.5 R4 — APPROVAL-EXACT: an approval authorizes one exact runtime action, under its
preconditions, inside its window.

The inventory is recorded in `docs/v1.6/pre-audit/increments/R4-APPROVAL-EXACT.md`. The producers
(`Store.request_approval`, `coding.CodingAdapter.approval`, `Authorizer._expansion`) already bind a
digest of a canonical action; these tests pin the consumer side — the checks a hostile caller hits
immediately before an effect runs.
"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_fixtures import job_contract  # noqa: E402

from kel.authorize import Authorizer  # noqa: E402
from kel.context import Context  # noqa: E402
from kel.core import Store  # noqa: E402


class ApprovalExactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.job_id = self.store.create(job_contract(), conversation='main')
        claim = self.store.claim(self.job_id, 'm1', provider='fixture', model='fixture')
        self.run_id = claim['id']
        self.action = {'method': 'command', 'workspace': 'proj', 'command': 'python -m pytest -q',
                       'permissions': None, 'grantRoot': None, 'network': None}
        self.approval_id = self.store.request_approval(self.job_id, self.run_id, self.action,
                                                       seconds=300)
        self.authorizer = Authorizer(self.store)

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _intent(self, action=None, job=None):
        return {'metadata': {'action': action or self.action},
                'job': job or self.job_id}

    def _row(self):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM approvals WHERE id=?',
                                   (self.approval_id,)).fetchone())

    def test_an_approval_authorizes_only_its_exact_action(self):
        self.store.resolve_approval(self.approval_id, self.action, True)
        self.assertTrue(self.authorizer._approval_ok(self.approval_id, self._intent()))
        changed = dict(self.action, command='rm -rf /')
        self.assertFalse(self.authorizer._approval_ok(self.approval_id, self._intent(changed)))
        # Equivalent-looking but materially different arguments are refused too.
        self.assertFalse(self.authorizer._approval_ok(
            self.approval_id, self._intent(dict(self.action, workspace='other'))))

    def test_an_approval_copied_to_another_job_is_refused(self):
        self.store.resolve_approval(self.approval_id, self.action, True)
        other_job = self.store.create(job_contract(), conversation='main')
        self.assertFalse(self.authorizer._approval_ok(self.approval_id,
                                                      self._intent(job=other_job)))

    def test_a_pending_approval_never_authorizes_execution(self):
        self.assertFalse(self.authorizer._approval_ok(self.approval_id, self._intent()))

    def test_an_approval_outside_its_window_is_refused(self):
        self.store.resolve_approval(self.approval_id, self.action, True)
        with self.store.transaction() as db:
            db.execute('UPDATE approvals SET expires=? WHERE id=?',
                       (time.time() - 1, self.approval_id))
        self.assertFalse(self.authorizer._approval_ok(self.approval_id, self._intent()))

    def test_resolving_after_the_window_records_expired_not_approved(self):
        with self.store.transaction() as db:
            db.execute('UPDATE approvals SET expires=? WHERE id=?',
                       (time.time() - 1, self.approval_id))
        status = self.store.resolve_approval(self.approval_id, self.action, True)
        self.assertEqual(status, 'EXPIRED')
        self.assertEqual(self._row()['status'], 'EXPIRED')
        self.assertFalse(self.authorizer._approval_ok(self.approval_id, self._intent()))

    def test_a_second_resolution_is_refused(self):
        self.store.resolve_approval(self.approval_id, self.action, True)
        with self.assertRaises(Exception):
            self.store.resolve_approval(self.approval_id, self.action, True)

    def test_a_remembered_grant_is_scoped_expiring_and_revocable(self):
        context = Context(self.store)
        project = context.project('r4-project')
        context.grant(project, self.action, seconds=300)
        self.assertTrue(context.allowed(project, self.action))
        self.assertFalse(context.allowed(project, dict(self.action, command='other')))
        context.revoke(project)
        self.assertFalse(context.allowed(project, self.action))
