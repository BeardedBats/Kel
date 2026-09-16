"""V1.5 G9 / WS31: reliability probes for ground the V1.4 suites do not exercise.

The full case-by-case map lives in docs/v1.5/10_RELIABILITY_REVIEW.md. These probes cover the
fresh ground on purpose: write contention against a competing SQLite writer, the bounded
lock-failure path (10 s busy timeout, then a clean error — never corruption and never a masked
error message), and the version identity every stale-package check builds on.
"""
import contextlib
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path

from kel.core import Store
from kel.diagnostics import Diagnostics
from kel.service import ENGINE_VERSION, Service

JOBS_INSERT = 'INSERT INTO jobs(id, revision, data) VALUES(?, 1, ?)'


class ReliabilitySweepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'data')

    def hold_write_lock(self, seconds):
        """Hold BEGIN IMMEDIATE plus a write on a second connection for `seconds`."""
        held = threading.Event()

        def holder():
            with contextlib.closing(self.store.connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute(JOBS_INSERT, ('lock-holder', '{}'))
                held.set()
                time.sleep(seconds)
                db.execute('ROLLBACK')

        thread = threading.Thread(target=holder)
        thread.start()
        self.addCleanup(thread.join)
        self.assertTrue(held.wait(5), 'lock holder never started')
        return thread

    def integrity(self):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute('PRAGMA integrity_check').fetchone()[0]

    def test_write_waits_for_a_competing_writer_then_succeeds(self):
        thread = self.hold_write_lock(0.6)
        started = time.perf_counter()
        with self.store.transaction() as db:
            db.execute(JOBS_INSERT, ('contended-writer', '{}'))
        elapsed = time.perf_counter() - started
        thread.join()
        self.assertGreaterEqual(elapsed, 0.4, 'the write must wait, not race the lock')
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT id FROM jobs WHERE id='contended-writer'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(self.integrity(), 'ok')

    def test_a_held_lock_surfaces_a_clean_bounded_error_then_recovers(self):
        # Bounded on purpose: the store's busy timeout is 10 s, so the failure path costs ~10 s
        # of wall time once per suite run. That is the recorded price of proving it at all.
        thread = self.hold_write_lock(12.0)
        started = time.perf_counter()
        with self.assertRaises(sqlite3.OperationalError) as caught:
            with self.store.transaction() as db:
                db.execute(JOBS_INSERT, ('blocked-writer', '{}'))
        elapsed = time.perf_counter() - started
        thread.join()
        # The surfaced error must be the real one: a failed BEGIN must not be masked by a
        # rollback of a transaction that never started.
        self.assertIn('lock', str(caught.exception).lower())
        self.assertGreaterEqual(elapsed, 9.0, 'the busy timeout must be spent before failing')
        with self.store.transaction() as db:
            db.execute(JOBS_INSERT, ('recovered-writer', '{}'))
        self.assertEqual(self.integrity(), 'ok')

    def test_engine_version_identity_is_reported_everywhere(self):
        service = Service(Path(self.tmp.name) / 'service-data')
        self.addCleanup(service.shutdown)
        state = service.state('main')
        self.assertEqual(state['engine_version'], ENGINE_VERSION)
        self.assertTrue(ENGINE_VERSION, 'a stale-package check needs a non-empty identity')
        snapshot = Diagnostics(service.store, ENGINE_VERSION).snapshot()
        self.assertEqual(snapshot['engine_version'], ENGINE_VERSION)


if __name__ == '__main__':
    unittest.main()
