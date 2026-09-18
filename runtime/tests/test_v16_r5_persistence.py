"""Round 2.5 R5 — PERSIST-CANONICAL: only validated, serializable, reconstructable state is durably
committed.

The inventory is recorded in `docs/v1.6/pre-audit/increments/R5-PERSISTENCE-INTEGRITY.md`. These
tests attack the ingress points that external processes and callers can reach, and check that every
refusal leaves the database healthy with no half-written authoritative row.
"""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_fixtures import job_contract  # noqa: E402

from kel.core import PolicyError, Store, encode  # noqa: E402
from kel.service import Service  # noqa: E402


class CanonicalEncodingTests(unittest.TestCase):
    def test_non_finite_values_are_refused_before_they_reach_the_store(self):
        for bad in (float('nan'), float('inf'), float('-inf'), {'x': [float('nan')]},
                    {'nested': {'deep': float('inf')}}):
            with self.assertRaises(PolicyError) as caught:
                encode(bad)
            self.assertIn('canonical JSON', str(caught.exception))

    def test_ordinary_values_stay_canonical(self):
        self.assertEqual(encode({'b': 1, 'a': 2}), '{"a":2,"b":1}')
        self.assertEqual(encode({'text': 'unicode ✓'}), '{"text":"unicode ✓"}')


class IngressIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.path = Path(self.tmp.name) / 'kel.sqlite3'
        self.store = Store(self.path)
        self.job_id = self.store.create(job_contract(), conversation='main')
        claim = self.store.claim(self.job_id, 'm1', provider='fixture', model='fixture')
        self.run_id, self.epoch = claim['id'], claim['epoch']

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _inbox_count(self):
        with self.store.connect() as db:
            return db.execute('SELECT count(*) FROM inbox').fetchone()[0]

    def test_a_malformed_worker_result_is_refused_and_leaves_no_row(self):
        with self.assertRaises(PolicyError):
            self.store.enqueue_result('ev_r5', self.run_id, self.epoch,
                                      {'tokens': float('nan')})
        self.assertEqual(self._inbox_count(), 0)
        # The same connection keeps working: a well-formed result lands normally.
        self.assertTrue(self.store.enqueue_result('ev_r5', self.run_id, self.epoch,
                                                  {'outcome': 'completed'}))
        self.assertEqual(self._inbox_count(), 1)

    def test_a_non_object_worker_result_is_refused(self):
        with self.assertRaises(PolicyError) as caught:
            self.store.enqueue_result('ev_r5b', self.run_id, self.epoch, ['not', 'an', 'object'])
        self.assertIn('must be an object', str(caught.exception))
        self.assertEqual(self._inbox_count(), 0)

    def test_the_provider_state_stays_finite_when_a_provider_reports_nonsense(self):
        self.store.provider_outcome('claude-code', {'outcome': 'FAILED', 'error': 'boom',
                                                    'duration': float('nan'),
                                                    'cost_usd': float('inf')})
        with self.store.connect() as db:
            row = db.execute("SELECT data FROM providers WHERE id='claude-code'").fetchone()
        state = json.loads(row['data'])
        self.assertEqual(state['failures'], 1)
        if 'latency' in state:
            self.assertTrue(math.isfinite(state['latency']))
        if 'cost' in state:
            self.assertTrue(math.isfinite(state['cost']))

    def test_an_oversized_artifact_is_refused_before_anything_is_written(self):
        with self.assertRaises(PolicyError) as caught:
            self.store._artifact(self.job_id, 'm1', self.run_id, 'x' * 1_000_001)
        self.assertIn('under one megabyte', str(caught.exception))
        self.assertFalse((self.store.root / 'artifacts' / self.job_id / self.run_id).exists())

    def test_a_malformed_request_type_answers_in_a_plain_sentence(self):
        service = Service(self.path)
        self.addCleanup(service.shutdown)
        with self.store.connect() as db:
            before = (db.execute('SELECT count(*) FROM submissions').fetchone()[0],
                      db.execute('SELECT count(*) FROM messages').fetchone()[0])
        with self.assertRaises(PolicyError) as caught:
            service.submit({'text': 123})
        self.assertIn('Request must be', str(caught.exception))
        with self.assertRaises(PolicyError):
            service.submit({'text': 'y' * 20001})
        # Nothing was durably half-written by the refused requests.
        with self.store.connect() as db:
            after = (db.execute('SELECT count(*) FROM submissions').fetchone()[0],
                     db.execute('SELECT count(*) FROM messages').fetchone()[0])
        self.assertEqual(after, before)
