"""Round 2.5 R6 — LIVENESS-SEPARATION / COMPLETION-TRUTH / RECOVERY-CLASSIFICATION.

The inventory is recorded in `docs/v1.6/pre-audit/increments/R6-TRUTHFUL-STATE.md`. Process
liveness, execution liveness and mission progress are separate facts: none of them establishes
completion, and a dead process never becomes an automatic retry or a completed mission.
"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_fixtures import job_contract  # noqa: E402

from kel.core import Store  # noqa: E402
from kel.diagnostics import Diagnostics, ensure_schema as ensure_diagnostics  # noqa: E402


class LivenessTruthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        ensure_diagnostics(self.store)
        self.job_id = self.store.create(job_contract(), conversation='main')
        claim = self.store.claim(self.job_id, 'm1', provider='fixture', model='fixture')
        self.run_id, self.epoch = claim['id'], claim['epoch']

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _run(self):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM runs WHERE id=?', (self.run_id,)).fetchone())

    def _fence_expired(self):
        with self.store.transaction() as db:
            db.execute('UPDATE runs SET expires=? WHERE id=?', (time.time() - 1, self.run_id))

    def test_an_expired_run_is_orphaned_reconcile_first_never_auto_retried(self):
        self._fence_expired()
        self.store.recover_expired()
        job = self.store.get(self.job_id)
        self.assertEqual(job['state'], 'WAITING_RESOURCE')
        self.assertEqual(job['verdict'], 'UNCERTAIN')
        milestone = job['milestones']['m1']
        self.assertEqual(milestone['state'], 'UNCERTAIN')
        self.assertIn('reconciliation', milestone['error'])
        run = self._run()
        self.assertEqual(run['state'], 'ORPHANED')
        self.assertNotEqual(run['epoch'], self.epoch)  # a fresh fence epoch for late deliveries

    def test_a_late_result_from_the_orphaned_epoch_is_discarded(self):
        self._fence_expired()
        self.store.recover_expired()
        self.store.enqueue_result('ev_late', self.run_id, self.epoch, {'outcome': 'completed'})
        self.store.consume()
        job = self.store.get(self.job_id)
        self.assertEqual(job['milestones']['m1']['state'], 'UNCERTAIN')
        self.assertEqual(job['state'], 'WAITING_RESOURCE')

    def test_no_new_events_alone_never_orphans_a_live_run(self):
        self.store.recover_expired(now=time.time() - 3600)
        job = self.store.get(self.job_id)
        self.assertEqual(job['milestones']['m1']['state'], 'RUNNING')
        self.assertEqual(self._run()['state'], 'RUNNING')

    def test_a_dead_observed_process_is_reported_never_completed(self):
        # The liveness surface for native children is `native_processes` (created by the runner).
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS native_processes(run_id TEXT PRIMARY KEY,pid INTEGER,'
                       'identity TEXT,stdout_path TEXT,deadline REAL)')
            db.execute('INSERT INTO native_processes VALUES(?,?,?,?,?)',
                       (self.run_id, 999999999, 'simulated', None, None))
        snapshot = Diagnostics(self.store).snapshot()
        row = [entry for entry in snapshot['processes'] if entry['pid'] == 999999999]
        self.assertEqual(len(row), 1)
        self.assertFalse(row[0]['alive'])
        self.assertTrue(any('no longer alive' in problem
                            for problem in snapshot['database']['problems']))
        job = self.store.get(self.job_id)
        self.assertEqual(job['milestones']['m1']['state'], 'RUNNING')  # liveness never completes work

    def test_waiting_is_not_completion_and_not_failure(self):
        self.store.request_approval(self.job_id, self.run_id,
                                    {'method': 'command', 'command': 'echo hi'}, seconds=300)
        job = self.store.get(self.job_id)
        self.assertEqual(job['state'], 'AWAITING_USER')
        self.assertNotEqual(job['milestones']['m1']['state'], 'COMPLETE')
        self.assertIn(job.get('verdict', '') or '', ('', 'UNCERTAIN'))
