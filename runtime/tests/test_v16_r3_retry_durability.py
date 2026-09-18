"""Round 2.5 R3 — RETRY-DURABLE: restarting Kel must not restore spent automatic retry budget.

The inventory is recorded in `docs/v1.6/pre-audit/increments/R3-RETRY-DURABILITY.md`. These tests
pin the durability of the two counters that gate *automatic* retries: the per-milestone attempt
budget on the job row, and the provider failure/circuit state in the providers row.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_fixtures import job_contract  # noqa: E402

from kel.core import PolicyError, Store  # noqa: E402
from kel.providers import Providers  # noqa: E402


class RetryBudgetDurabilityTests(unittest.TestCase):
    """A new Store over the same file is exactly what a process restart does."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.path = Path(self.tmp.name) / 'kel.sqlite3'
        self.store = Store(self.path)
        self.job_id = self.store.create(job_contract(), conversation='main')

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _reopen(self):
        return Store(self.path)

    def test_the_milestone_attempt_budget_survives_a_restart(self):
        claimed = self.store.claim(self.job_id, 'm1', provider='fixture', model='fixture')
        self.assertEqual(claimed['attempt'], 1)
        # Spend the rest of the budget the way history would: the counter lives on the job row.
        with self.store.transaction() as db:
            job = self.store._get(db, self.job_id)
            job['milestones']['m1'].update(attempts=4, state='NEEDS_REPAIR')
            self.store._save(db, job, 'attempts.spent')
        reopened = self._reopen()
        with self.assertRaises(PolicyError) as caught:
            reopened.claim(self.job_id, 'm1', provider='fixture', model='fixture')
        self.assertIn('Milestone cannot run', str(caught.exception))
        self.assertEqual(reopened.get(self.job_id)['milestones']['m1']['attempts'], 4)

    def test_a_spent_budget_is_not_restored_by_a_second_restart(self):
        with self.store.transaction() as db:
            job = self.store._get(db, self.job_id)
            job['milestones']['m1'].update(attempts=4, state='NEEDS_REPAIR')
            self.store._save(db, job, 'attempts.spent')
        for _ in range(2):
            reopened = self._reopen()
            with self.assertRaises(PolicyError):
                reopened.claim(self.job_id, 'm1', provider='fixture', model='fixture')
        self.assertEqual(self._reopen().get(self.job_id)['milestones']['m1']['attempts'], 4)

    def test_an_automatic_resume_refuses_once_every_milestone_is_exhausted(self):
        with self.store.transaction() as db:
            job = self.store._get(db, self.job_id)
            job['milestones']['m1'].update(attempts=4, state='EXHAUSTED')
            self.store._save(db, job, 'attempts.exhausted')
        with self.assertRaises(PolicyError) as caught:
            self._reopen().reopen(self.job_id)
        self.assertIn('No retryable milestones', str(caught.exception))

    def test_the_provider_failure_counter_survives_a_restart(self):
        for _ in range(3):
            self.store.provider_outcome('claude-code', {'outcome': 'FAILED', 'error': 'boom'})
        status = Providers(self._reopen()).status('claude-code')
        self.assertEqual(status['failures'], 3)
        self.assertEqual(status['status'], 'degraded')
        self.assertIsNotNone(status['circuit_until'])

    def test_only_a_success_clears_the_provider_circuit(self):
        for _ in range(3):
            self.store.provider_outcome('claude-code', {'outcome': 'FAILED', 'error': 'boom'})
        reopened = self._reopen()
        self.assertEqual(Providers(reopened).status('claude-code')['failures'], 3)
        reopened.provider_outcome('claude-code', {'outcome': 'SUCCESS', 'duration': 1.0})
        self.assertEqual(Providers(reopened).status('claude-code')['failures'], 0)
