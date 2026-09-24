"""V1.4 Gate 8: diagnostics, retention, compaction, sanitized export (DIAG-*)."""
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel.core import PolicyError, Store, encode, uid
from kel.diagnostics import Diagnostics, EXPORT_ALLOWLIST, _pid_alive


def contract(filler='x'):
    return {'request': 'Do the work', 'project_id': 'default',
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 4}]},
                           {'id': 'm2', 'objective': 'Second step', 'filename': 'two.md',
                            'depends_on': ['m1'], 'checks': [{'kind': 'min_chars', 'value': 4}]}]}


class DiagnosticsBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name))
        self.diagnostics = Diagnostics(self.store, engine_version='1.4.0-test')

    def tearDown(self):
        self.tmp.cleanup()

    def plant_secret(self):
        """Put a secret-shaped string where a naive exporter would leak it."""
        marker = 'sk-live-LEAK123456'
        job = self.store.create(contract(), conversation='main')
        with self.store.transaction() as db:
            # native_processes is created lazily by the runner; mirror its DDL for the fixture.
            db.execute('CREATE TABLE IF NOT EXISTS native_processes('
                       'run_id TEXT PRIMARY KEY,pid INTEGER,identity TEXT,stdout_path TEXT,deadline REAL)')
            db.execute('UPDATE jobs SET data=? WHERE id=?',
                       (encode(dict(self.store.get(job), request='Use %s to call the API' % marker)), job))
            db.execute("INSERT INTO native_processes VALUES(?,?,?,?,?)",
                       ('run-planted', os.getpid(), 'token=%s' % marker, 'x.log', time.time() + 60))
        return marker, job


class SchemaTests(DiagnosticsBase):
    def test_migration_recorded_and_idempotent(self):
        with contextlib.closing(self.store.connect()) as db:
            versions = [row['version'] for row in db.execute(
                'SELECT version FROM schema_migrations ORDER BY version')]
        self.assertIn(9, versions)
        Diagnostics(self.store)  # second instantiation must be a no-op
        with contextlib.closing(self.store.connect()) as db:
            again = [row['version'] for row in db.execute('SELECT version FROM schema_migrations')]
        self.assertEqual(sorted(again), sorted(versions))


class RecordingTests(DiagnosticsBase):
    def test_startup_spans_and_measurements(self):
        self.diagnostics.record_startup('store-open', 11.5)
        self.diagnostics.measure('claim', 3.25, detail={'job': 'fixture'})
        dump = json.dumps(self.diagnostics.performance(), default=str)
        self.assertIn('store-open', dump)
        self.assertIn('claim', dump)

    def test_observe_records_health_and_reports_integrity(self):
        result = self.diagnostics.observe()
        self.assertEqual(result['state'], 'ok')
        self.assertEqual(result['snapshot']['database']['integrity'], 'ok')
        with contextlib.closing(self.store.connect()) as db:
            rows = list(db.execute('SELECT subject, state FROM health_observations'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['subject'], 'overall')

    def test_expired_runs_are_reported_as_a_problem(self):
        job = self.store.create(contract(), conversation='main')
        run = self.store.claim(job, 'm1')
        with self.store.transaction() as db:
            db.execute('UPDATE runs SET expires=? WHERE id=?', (time.time() - 5, run['id']))
        snapshot = self.diagnostics.snapshot()
        self.assertEqual(snapshot['runs']['expired_unfenced'], 1)
        self.assertTrue(any('past their fence' in problem for problem in snapshot['database']['problems']))

    def test_process_liveness_is_reported(self):
        _, _ = self.plant_secret()
        snapshot = self.diagnostics.snapshot()
        planted = [row for row in snapshot['processes'] if row['run_id'] == 'run-planted']
        self.assertEqual(len(planted), 1)
        self.assertTrue(planted[0]['alive'])
        self.assertFalse(planted[0]['past_deadline'])

    def test_pid_liveness_helper(self):
        self.assertTrue(_pid_alive(os.getpid()))
        self.assertFalse(_pid_alive(999999))
        self.assertFalse(_pid_alive(None))

    def test_pid_liveness_does_not_stop_child(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            self.assertTrue(_pid_alive(child.pid))
            self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait(timeout=10)
        self.assertFalse(_pid_alive(child.pid))

    def test_pid_liveness_rejects_invalid_ids(self):
        for pid in (0, -1, 'invalid'):
            self.assertFalse(_pid_alive(pid))
        if os.name == 'nt':
            self.assertFalse(_pid_alive(2 ** 40))


class ExportTests(DiagnosticsBase):
    def test_export_is_allowlisted_and_never_carries_the_planted_secret(self):
        marker, _job = self.plant_secret()
        payload = self.diagnostics.export()
        dump = json.dumps(payload, default=str)
        self.assertNotIn(marker, dump)
        self.assertNotIn('sk-', dump)
        self.assertTrue(set(payload.keys()) <= set(EXPORT_ALLOWLIST))
        self.assertIn('receipt', payload)
        self.assertIn('credentials, tokens and API keys', payload['receipt']['excluded'])
        self.assertTrue(payload['receipt']['included'])

    def test_issue_report_is_a_local_draft_without_secrets(self):
        marker, _job = self.plant_secret()
        report = self.diagnostics.issue_report(note='Reproduce with %s' % marker)
        path = Path(report['path'])
        self.assertTrue(path.exists())
        self.assertGreater(report['bytes'], 0)
        self.assertTrue(report['redacted'])
        content = path.read_text(encoding='utf-8')
        self.assertNotIn(marker, content)
        self.assertIn('[redacted]', content)
        self.assertIn('redacted before writing this file', content)
        self.assertEqual(path.parent.name, 'diagnostics')


class MaintenanceTests(DiagnosticsBase):
    def test_retention_purge_removes_old_observations_only(self):
        job = self.store.create(contract(), conversation='main')
        self.diagnostics.observe()
        with self.store.transaction() as db:
            db.execute('INSERT INTO health_observations VALUES(?,?,?,?,?)',
                       (uid(), time.time() - 100000, 'old', 'ok', encode({'old': True})))
        self.diagnostics.set_retention('health_observations', 1.0)
        result = self.diagnostics.purge()
        self.assertEqual(result['removed']['health_observations'], 1)
        with contextlib.closing(self.store.connect()) as db:
            remaining = [row['subject'] for row in db.execute('SELECT subject FROM health_observations')]
            jobs = db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        self.assertNotIn('old', remaining)
        self.assertEqual(jobs, 1)  # jobs are never purged
        self.assertTrue(self.store.get(job))

    def test_retention_keys_are_validated(self):
        with self.assertRaises(PolicyError):
            self.diagnostics.set_retention('jobs', 1.0)

    def test_compact_returns_a_summary(self):
        self.diagnostics.measure('boot', 5)
        summary = self.diagnostics.compact()
        self.assertTrue(summary)
        self.assertIn('bytes', json.dumps(summary, default=str))


class EnvelopeTests(DiagnosticsBase):
    def test_apply_covers_the_service_actions(self):
        observed = self.diagnostics.apply({'action': 'observe'})
        self.assertEqual(observed['state'], 'ok')
        exported = self.diagnostics.apply({'action': 'export'})
        self.assertIn('receipt', exported)
        self.assertTrue(self.diagnostics.apply({'action': 'performance'}))
        self.assertTrue(self.diagnostics.apply({'action': 'retention'}))
        self.assertIn('integrity', self.diagnostics.apply({'action': 'snapshot'})['database'])
        self.assertTrue(self.diagnostics.apply({'action': 'measure', 'name': 'boot', 'value': 4}))
        self.assertTrue(self.diagnostics.apply({'action': 'startup', 'phase': 'service',
                                                'duration_ms': 9}))
        self.assertTrue(self.diagnostics.apply({'action': 'compact'}))
        with self.assertRaises(PolicyError):
            self.diagnostics.apply({'action': 'not-an-action'})
