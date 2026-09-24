"""V1.3 Gate 4: service-level continuation wiring (chat flow, state surface, probes-in-process)."""
import contextlib
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from kel.service import Service


def contract(request='Do the work'):
    return {'request': request,
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}]}]}


class ContinuationServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            self.service = Service(self.tmp.name)
        self.service.engine.adapters.clear()  # no worker may claim seeded test jobs

    def tearDown(self):
        self.service.shutdown()
        self.tmp.cleanup()

    def wait_submission(self, sid, terminal=('DISPATCHED', 'SETTLED', 'FAILED', 'INTERRUPTED')):
        deadline = time.time() + 15
        while time.time() < deadline:
            with contextlib.closing(self.service.store.connect()) as db:
                row = db.execute('SELECT state FROM submissions WHERE id=?', (sid,)).fetchone()
            if row and row['state'] in terminal:
                return row['state']
            time.sleep(.05)
        raise TimeoutError('submission did not settle')

    def assistant_messages(self, cid):
        return [m['text'] for m in self.service.state(cid)['messages']
                if m['role'] == 'assistant']

    def seed_job(self, conversation, **changes):
        job_id = self.service.store.create(contract(), conversation=conversation)
        with self.service.store.transaction() as db:
            job = self.service.store._get(db, job_id)
            if changes.get('state'):
                job['state'] = changes['state']
            if changes.get('verdict'):
                job['verdict'] = changes['verdict']
            for mid, patch_ in (changes.get('milestones') or {}).items():
                job['milestones'][mid].update(patch_)
            self.service.store._save(db, job, 'test.fixture')
        return job_id

    def test_continue_single_resumes_and_links(self):
        cid = self.service.context.conversation('default', title='Continuation chat')
        job = self.seed_job(cid, state='PAUSED')
        sid = self.service.submit({'text': 'continue', 'conversation': cid})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        self.assertIn(self.service.store.get(job)['state'], ('READY', 'WAITING_RESOURCE'))
        text = '\n'.join(self.assistant_messages(cid))
        self.assertIn('Continuing', text)
        with contextlib.closing(self.service.store.connect()) as db:
            rows = db.execute('SELECT kind FROM job_links WHERE job_id=?', (job,)).fetchall()
        self.assertEqual([r['kind'] for r in rows], ['continuation'])

    def test_continue_choice_lists_candidates(self):
        cid = self.service.context.conversation('default', title='Choice chat')
        other = self.service.context.conversation('default', title='Other chat')
        first = self.seed_job(other, state='PAUSED')
        second = self.seed_job(other, state='PAUSED')
        sid = self.service.submit({'text': 'continue', 'conversation': cid})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        text = '\n'.join(self.assistant_messages(cid))
        self.assertIn('Which one should I continue', text)
        self.assertIn(first, text)
        self.assertIn(second, text)
        self.assertEqual(self.service.store.get(first)['state'], 'PAUSED')
        self.assertEqual(self.service.store.get(second)['state'], 'PAUSED')

    def test_continue_explicit_job_id_resumes_closed_job(self):
        cid = self.service.context.conversation('default', title='Explicit chat')
        other = self.service.context.conversation('default', title='Work chat')
        job = self.seed_job(other, state='CLOSED', verdict='FAILED',
                            milestones={'m1': {'state': 'NEEDS_REPAIR'}})
        sid = self.service.submit({'text': 'continue this please', 'conversation': cid,
                                   'job_id': job})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        self.assertIn(self.service.store.get(job)['state'], ('READY', 'WAITING_RESOURCE'))
        with contextlib.closing(self.service.store.connect()) as db:
            row = db.execute('SELECT kind FROM job_links WHERE job_id=? AND conversation_id=?',
                             (job, cid)).fetchone()
        self.assertIsNotNone(row)

    def test_continue_wrong_project_refused(self):
        other_project = self.service.context.project('Other', project_id='p2')
        cid2 = self.service.context.conversation(project_id=other_project, title='P2 chat')
        job = self.seed_job(cid2, state='PAUSED')
        cid = self.service.context.conversation('default', title='P1 chat')
        sid = self.service.submit({'text': 'continue this', 'conversation': cid, 'job_id': job})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        self.assertEqual(self.service.store.get(job)['state'], 'PAUSED')
        text = '\n'.join(self.assistant_messages(cid))
        self.assertIn('another project', text)
    def test_continue_none_message(self):
        cid = self.service.context.conversation('default', title='Empty chat')
        sid = self.service.submit({'text': 'continue', 'conversation': cid})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        text = '\n'.join(self.assistant_messages(cid)).lower()
        self.assertIn('no unfinished work', text)

    def test_state_exposes_candidates(self):
        cid = self.service.context.conversation('default', title='State chat')
        job = self.seed_job(cid, state='PAUSED')
        state = self.service.state(cid)
        ids = [c['job_id'] for c in state['continuation']]
        self.assertIn(job, ids)
        entry = next(c for c in state['continuation'] if c['job_id'] == job)
        self.assertEqual(entry['state'], 'PAUSED')
        self.assertEqual(entry['total'], 1)

    def test_verified_job_refused_explicitly(self):
        cid = self.service.context.conversation('default', title='Verified chat')
        job = self.seed_job(cid, state='CLOSED', verdict='VERIFIED',
                            milestones={'m1': {'state': 'ACCEPTED'}})
        sid = self.service.submit({'text': 'continue again', 'conversation': cid, 'job_id': job})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        text = '\n'.join(self.assistant_messages(cid))
        self.assertIn('already verified', text)
        self.assertEqual(self.service.store.get(job)['state'], 'CLOSED')

    def test_continue_preserves_awaiting_user_and_pending_approval(self):
        cid = self.service.context.conversation('default', title='Approval chat')
        job = self.seed_job(cid, state='AWAITING_USER',
                            milestones={'m1': {'state': 'NEEDS_REPAIR'}})
        with self.service.store.transaction() as db:
            db.execute("INSERT INTO approvals VALUES('ap1',?,NULL,'digest','PENDING',?,NULL)",
                       (job, time.time() + 3600))
            db.execute("INSERT INTO approval_actions VALUES('ap1',"
                       "'{\"kind\":\"command\",\"command\":\"echo hi\"}')")
        sid = self.service.submit({'text': 'continue this work', 'conversation': cid,
                                   'job_id': job})
        self.assertEqual(self.wait_submission(sid), 'SETTLED')
        self.assertEqual(self.service.store.get(job)['state'], 'AWAITING_USER')
        state = self.service.state(cid)
        self.assertEqual(len(state['approvals']), 1)
        with contextlib.closing(self.service.store.connect()) as db:
            row = db.execute("SELECT status FROM approvals WHERE id='ap1'").fetchone()
        self.assertEqual(row['status'], 'PENDING')

    def test_origin_link_helper(self):
        cid = self.service.context.conversation('default', title='Origin chat')
        job = self.seed_job(cid, state='READY')
        self.service._link_origin(job, cid, 'sub12345')
        with contextlib.closing(self.service.store.connect()) as db:
            rows = db.execute('SELECT kind, reason FROM job_links WHERE job_id=?',
                              (job,)).fetchall()
        self.assertEqual(rows[0]['kind'], 'origin')
        self.assertIn('sub12345', rows[0]['reason'])


if __name__ == '__main__':
    unittest.main()
