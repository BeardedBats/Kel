"""Round 2.5 R2 — EVENT-IDEMPOTENCY / EFFECT-REPLAY.

The matrix (recorded in `docs/v1.6/pre-audit/increments/R2-IDEMPOTENCY-MATRIX.md`) showed every
authoritative event family is already idempotent except one: an already-observed external effect
could have its recorded receipt silently overwritten. These tests pin the repaired contract and the
duplicate behavior of the families the directive names first.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workforce_fixtures import job_contract  # noqa: E402

from kel.core import PolicyError, Store, digest  # noqa: E402
from kel.service import Service  # noqa: E402


class _StoreBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.conversation = 'main'
        self.job_id = self.store.create(job_contract(), conversation=self.conversation)

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass


class EffectObservationTests(_StoreBase):
    """EFFECT-REPLAY: an observation is evidence; it is never silently rewritten."""

    def setUp(self):
        super().setUp()
        self.operation = 'op_deploy_1'
        self.action = {'kind': 'deploy', 'target': 'staging'}
        self.store.prepare_effect(self.job_id, self.operation, self.action)

    def _row(self):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM effects WHERE id=?', (self.operation,)).fetchone())

    def test_preparing_the_same_operation_twice_keeps_one_row_and_state(self):
        self.assertEqual(self.store.prepare_effect(self.job_id, self.operation, self.action),
                         'PREPARED')
        with self.store.connect() as db:
            count = db.execute('SELECT count(*) FROM effects WHERE id=?',
                               (self.operation,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_reusing_an_operation_identity_for_a_different_effect_is_refused(self):
        with self.assertRaises(PolicyError) as caught:
            self.store.prepare_effect(self.job_id, self.operation, {'kind': 'deploy',
                                                                   'target': 'production'})
        self.assertIn('Operation identity reused', str(caught.exception))

    def test_re_observing_the_identical_receipt_is_a_noop(self):
        receipt = {'outcome': 'ok', 'exit_code': 0}
        self.store.observe_effect(self.operation, receipt)
        before = self._row()
        self.store.observe_effect(self.operation, receipt)
        after = self._row()
        self.assertEqual(after['state'], 'OBSERVED')
        self.assertEqual(json.loads(after['receipt']), receipt)
        self.assertEqual(before['receipt'], after['receipt'])

    def test_a_contradictory_receipt_is_refused_and_the_evidence_is_kept(self):
        first = {'outcome': 'ok', 'exit_code': 0}
        self.store.observe_effect(self.operation, first)
        with self.assertRaises(PolicyError) as caught:
            self.store.observe_effect(self.operation, {'outcome': 'failed', 'exit_code': 1})
        self.assertIn('different receipt', str(caught.exception))
        self.assertEqual(json.loads(self._row()['receipt']), first)


class DuplicateDeliveryTests(_StoreBase):
    """Same logical event twice: no more than one authoritative execution."""

    def test_a_duplicate_result_delivery_lands_once(self):
        run = self.store.claim(self.job_id, 'm1')
        payload = {'outcome': 'completed', 'summary': 'done'}
        self.store.enqueue_result('ev_dup_1', run['id'], run['epoch'], payload)
        self.store.enqueue_result('ev_dup_1', run['id'], run['epoch'], payload)
        with self.store.connect() as db:
            rows = db.execute('SELECT * FROM inbox WHERE id=?', ('ev_dup_1',)).fetchall()
        self.assertEqual(len(rows), 1)

    def test_a_stale_run_epoch_delivery_is_consumed_but_never_applied(self):
        run = self.store.claim(self.job_id, 'm1')
        stale_epoch = 'epoch_from_a_previous_run'
        self.store.enqueue_result('ev_stale_1', run['id'], stale_epoch, {'outcome': 'completed'})
        self.store.consume()
        with self.store.connect() as db:
            inbox = db.execute('SELECT handled FROM inbox WHERE id=?', ('ev_stale_1',)).fetchone()
            current = db.execute('SELECT state,epoch FROM runs WHERE id=?', (run['id'],)).fetchone()
        self.assertEqual(inbox['handled'], 1)          # never left to spin
        self.assertEqual(current['epoch'], run['epoch'])  # the live epoch is untouched
        self.assertNotEqual(current['state'], 'COMPLETED')

    def test_an_event_revision_cannot_be_written_twice(self):
        with self.store.transaction() as db:
            db.execute("INSERT INTO events(id,aggregate_id,revision,type,at,payload)"
                       " VALUES(?,?,?,?,?,?)", ('ev_a', self.job_id, 900, 't', 1.0, '{}'))
        with self.assertRaises(Exception) as caught:
            with self.store.transaction() as db:
                db.execute("INSERT INTO events(id,aggregate_id,revision,type,at,payload)"
                           " VALUES(?,?,?,?,?,?)", ('ev_b', self.job_id, 900, 't', 1.0, '{}'))
        self.assertIn('UNIQUE', str(caught.exception).upper())

    def test_an_approval_resolves_once(self):
        # Handcrafted pending approval on a run that awaits it (the smallest real shape).
        action = {'kind': 'apply_changes', 'target': 'repo'}
        with self.store.transaction() as db:
            db.execute("INSERT INTO runs(id,job_id,milestone_id,epoch,state,reservation,expires,"
                       "result,provider,model) VALUES(?,?,?,?,?,?,?,?,?,?)",
                       ('run_apr_r2', self.job_id, 'm1', 'ep_1', 'WAITING_APPROVAL', 1,
                        __import__('time').time() + 600, None, 'fixture', 'fixture'))
            db.execute("INSERT INTO approvals(id,job_id,run_id,action_digest,status,expires,actor)"
                       " VALUES(?,?,?,?,?,?,?)",
                       ('apr_r2', self.job_id, 'run_apr_r2', digest(action), 'PENDING',
                        __import__('time').time() + 600, None))
        self.assertEqual(self.store.resolve_approval('apr_r2', action, True, actor='user'), 'APPROVED')
        with self.assertRaises(PolicyError) as caught:
            self.store.resolve_approval('apr_r2', action, True, actor='user')
        self.assertIn('does not match this action', str(caught.exception))


class SubmissionDuplicateTests(unittest.TestCase):
    """A repeated submission id is one piece of logical work, not two."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.service = Service(str(Path(self.tmp.name) / 'kel.sqlite3'))
        self.addCleanup(self.service.shutdown)
        self.plan_calls = []

        def record(*args, **kwargs):
            self.plan_calls.append(args)

        self.service.requests.submit = record  # the planner never runs in this test

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_the_same_submission_plans_once(self):
        payload = {'id': 'req_dup_1', 'conversation': 'main', 'text': 'write a haiku'}
        first = self.service.submit(dict(payload))
        self.assertEqual(first, 'req_dup_1')
        second = self.service.submit(dict(payload))
        self.assertEqual(second, 'req_dup_1')
        self.assertEqual(len(self.plan_calls), 1)  # the duplicate never reaches the planner
        with self.service.store.connect() as db:
            count = db.execute('SELECT count(*) FROM submissions WHERE id=?',
                               ('req_dup_1',)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_the_same_id_with_different_content_is_refused(self):
        self.service.submit({'id': 'req_dup_2', 'conversation': 'main', 'text': 'first'})
        with self.assertRaises(PolicyError) as caught:
            self.service.submit({'id': 'req_dup_2', 'conversation': 'main', 'text': 'second'})
        self.assertIn('different content', str(caught.exception))
        self.assertEqual(len(self.plan_calls), 1)


if __name__ == '__main__':
    unittest.main()
