"""V2-06 — Needs Your Attention 2.0: what a Work row says, and the one action it offers.

Every field is derived from authoritative state (jobs, runs, approvals, events). The surface may
group, filter and sort; it never resolves, snoozes or re-runs anything itself — the direct action
points at the existing route that does.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.core import Store
from kel.engine import compile_document


def contract(request='Write the attention note with enough text to pass.'):
    return compile_document(request, required=[])


class SurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            from kel.service import Service
            self.service = Service(Path(self.tmp.name) / 'svc')
        self.addCleanup(self._shutdown)
        self.store = self.service.store

    def _shutdown(self):
        self.service.shutdown()

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def _fenced_job(self):
        job_id = self.store.create(contract(), conversation='main')
        milestone_id = next(iter(self.store.get(job_id)['milestones']))
        self.store.claim(job_id, milestone_id, provider='fixture', model='fixture', timeout=5)
        self.store.recover_abandoned(now=time.time() + 600)
        return job_id

    def _rows(self):
        work = self.service._work('main')['work']
        return work, {entry['job_id']: entry for entry in work['jobs']}

    def test_a_needs_you_row_says_why_it_is_here_and_offers_one_action(self):
        job_id = self._fenced_job()
        work, rows = self._rows()
        entry = rows[job_id]
        self.assertTrue(entry['needs_you'])
        self.assertEqual(entry['priority'], 'now')
        self.assertEqual(entry['reason'], entry['why'])
        self.assertTrue(entry['reason'])
        self.assertGreaterEqual(entry['age_seconds'], 0)
        self.assertTrue(entry['next'])
        self.assertIsNotNone(entry['direct'])
        self.assertEqual(entry['direct']['action'], 'resume')
        self.assertEqual(entry['direct']['route'], '/api/send',
                         'a fenced run resumes as a conversation continuation')
        self.assertEqual(entry['related']['conversation'], 'main')
        self.assertEqual(entry['related']['milestones'], 1)
        self.assertEqual(work['needs_you'], 1, 'only the person-action job counts')
        self.assertEqual(work['jobs'][0]['job_id'], job_id, 'the needs-you row sorts first')

    def test_a_pending_approval_offers_answer_and_is_grouped_by_project(self):
        job_id = self.store.create(contract(), conversation='main')
        milestone_id = next(iter(self.store.get(job_id)['milestones']))
        run = self.store.claim(job_id, milestone_id, provider='fixture', model='fixture',
                               timeout=30)
        self.store.request_approval(job_id, run['id'], {'tool': 'repository_edit'})
        work, rows = self._rows()
        entry = rows[job_id]
        self.assertTrue(entry['needs_you'])
        self.assertEqual(entry['direct']['action'], 'answer')
        self.assertEqual(entry['direct']['route'], '/api/approval')
        self.assertEqual(entry['related']['approvals'], 1)
        self.assertEqual(entry['priority'], 'now')
        self.assertEqual(work['grouping'], 'project')
        self.assertTrue(work['groups'])
        self.assertEqual(work['filters']['needs_you'], work['needs_you'])
        self.assertIn('priority', work['sorting'])

    def test_a_settled_bad_result_is_soon_and_offers_a_retry(self):
        job_id = self.store.create(contract(), conversation='main')
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            job.update(state='CLOSED', verdict='FAILED')
            self.store._save(db, job, 'test.settle')
        work, rows = self._rows()
        entry = rows[job_id]
        self.assertEqual(entry['priority'], 'soon')
        self.assertFalse(entry['needs_you'])
        self.assertEqual(entry['direct']['action'], 'retry')
        self.assertEqual(entry['direct']['route'], '/api/retry')
        self.assertEqual(work['filters']['failed'], 1)

    def test_a_settled_verified_result_is_later_and_asks_for_nothing(self):
        job_id = self.store.create(contract(), conversation='main')
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            job.update(state='CLOSED', verdict='VERIFIED')
            self.store._save(db, job, 'test.settle')
        work, rows = self._rows()
        entry = rows[job_id]
        self.assertEqual(entry['priority'], 'later')
        self.assertIsNone(entry['direct'])
        self.assertFalse(entry['needs_you'])
        self.assertEqual(work['filters']['settled'], 1)

    def test_a_cancelled_job_offers_no_action_it_cannot_honour(self):
        # Measured mismatch this pins: the row used to offer retry -> /api/retry for a cancelled job,
        # and the endpoint refused it ("This request is not ready for retry") because retry accepts a
        # submission whose own state is FAILED/INTERRUPTED. The row must say what is true instead.
        job_id = self.store.create(contract(), conversation='main')
        self.store.control(job_id, 'cancel')
        work, rows = self._rows()
        entry = rows[job_id]
        self.assertEqual(entry['state'], 'CANCELLED')
        self.assertIsNone(entry['direct'], 'a stopped job must not promise an action it cannot honour')
        self.assertIn('stopped', entry['why'].lower())
        self.assertIn('kept', entry['next'].lower())
        self.assertFalse(entry['needs_you'])

    def test_the_surface_offers_no_snooze_that_state_cannot_keep(self):
        self._fenced_job()
        work, _rows = self._rows()
        self.assertEqual(work['grouping'], 'project')
        self.assertEqual(sorted(work['filters']), ['failed', 'needs_you', 'running', 'settled'])
        self.assertEqual(sorted(work['sorting']), ['age', 'priority'])
        self.assertNotIn('snooze', str(work).lower(),
                         'nothing offers a snooze the authoritative state cannot honour')


if __name__ == '__main__':
    unittest.main()
