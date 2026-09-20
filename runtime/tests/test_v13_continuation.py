"""V1.3 Gate 4: first-class continuation (docs/v1.3/KEL_V1.3_CONTINUATION_SPEC.md; CONT-*)."""
import contextlib
import tempfile
import time
import unittest

from kel.core import PolicyError, Store
from kel.context import Context
from kel.continuation import Continuation
from kel.engine import Engine
from kel.native import FixtureAdapter


def contract(request='Do the work'):
    return {'request': request,
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 40}]}]}


class ContinuationCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.context = Context(self.store)
        self.p1 = self.context.project('One', project_id='p1')
        self.p2 = self.context.project('Two', project_id='p2')
        self.c1 = self.context.conversation('p1', title='First')
        self.cont = Continuation(self.store)

    def tweak(self, job_id, **changes):
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            for key in ('state', 'verdict'):
                if key in changes:
                    job[key] = changes[key]
            if 'conversation' in changes:
                job['conversation'] = changes['conversation']
            if 'route_block' in changes:
                job['route_block'] = changes['route_block']
            for mid, patch in (changes.get('milestones') or {}).items():
                job['milestones'][mid].update(patch)
            if changes.get('contract'):
                job['contract'].update(changes['contract'])
            self.store._save(db, job, 'test.fixture')
        return job_id

    def make_job(self, request='Do the work', conversation=None, **changes):
        job_id = self.store.create(contract(request), conversation=conversation or self.c1)
        if changes:
            self.tweak(job_id, **changes)
        return job_id

    def test_candidates_project_scoped(self):
        mine = self.make_job('Task A')
        other_conv = self.context.conversation('p2', title='Other')
        theirs = self.make_job('Task B', conversation=other_conv)
        ids = [c['job_id'] for c in self.cont.candidates(self.p1)]
        self.assertEqual(ids, [mine])
        self.assertNotIn(theirs, ids)

    def test_candidates_states_and_verified_excluded(self):
        ready = self.make_job('Ready task')
        paused = self.make_job('Paused task', state='PAUSED')
        closed = self.make_job('Closed task', state='CLOSED', verdict='UNCERTAIN',
                               milestones={'m1': {'state': 'UNCERTAIN', 'attempts': 1}})
        verified = self.make_job('Verified task', state='CLOSED', verdict='VERIFIED',
                                 milestones={'m1': {'state': 'ACCEPTED'}})
        cancelled = self.make_job('Cancelled task', state='CANCELLED',
                                  milestones={'m1': {'state': 'READY', 'attempts': 0}})
        ids = {c['job_id'] for c in self.cont.candidates(self.p1)}
        for job in (ready, paused, closed, cancelled):
            self.assertIn(job, ids)
        self.assertNotIn(verified, ids)

    def test_resolve_single(self):
        job = self.make_job('Only one')
        result = self.cont.resolve(self.p1, self.c1)
        self.assertEqual(result['kind'], 'single')
        self.assertEqual(result['candidate']['job_id'], job)

    def test_resolve_single_via_conversation_link(self):
        elsewhere = self.context.conversation('p1', title='Elsewhere')
        self.make_job('Alpha work', conversation=elsewhere)
        mine = self.make_job('Beta work', conversation=self.c1)
        result = self.cont.resolve(self.p1, self.c1)
        self.assertEqual(result['kind'], 'single')
        self.assertEqual(result['candidate']['job_id'], mine)

    def test_resolve_choice_when_ambiguous(self):
        elsewhere = self.context.conversation('p1', title='Elsewhere')
        another = self.context.conversation('p1', title='Another')
        self.make_job('X work', conversation=elsewhere)
        self.make_job('Y work', conversation=another)
        result = self.cont.resolve(self.p1, self.c1)
        self.assertEqual(result['kind'], 'choice')
        self.assertEqual(len(result['candidates']), 2)

    def test_resolve_text_ranks_and_selects(self):
        elsewhere = self.context.conversation('p1', title='Elsewhere')
        another = self.context.conversation('p1', title='Another')
        self.make_job('Write the release notes', conversation=elsewhere)
        self.make_job('Fix the parser bug', conversation=another)
        result = self.cont.resolve(self.p1, self.c1,
                                   text='please continue the release notes work')
        self.assertEqual(result['kind'], 'single')
        self.assertEqual(result['candidate']['title'], 'Write the release notes')

    def test_resolve_none_and_wrong_project(self):
        other_conv = self.context.conversation('p2', title='Other')
        self.make_job('Task only in project two', conversation=other_conv)
        result = self.cont.resolve(self.p1, self.c1)
        self.assertEqual(result['kind'], 'none')
        self.assertEqual(result['candidates'], [])
    def test_verified_job_cannot_resume(self):
        job = self.make_job('Done work', state='CLOSED', verdict='VERIFIED',
                            milestones={'m1': {'state': 'ACCEPTED'}})
        self.assertEqual(self.cont.resolve(self.p1, self.c1)['kind'], 'none')
        with self.assertRaises(PolicyError):
            self.cont.execute_resume(job, self.c1)

    def test_attach_idempotent_and_survives_restart(self):
        job = self.make_job('Attach me')
        self.assertTrue(self.cont.attach(job, self.c1, reason='first talk'))
        self.assertFalse(self.cont.attach(job, self.c1))
        reopened = Continuation(Store(self.temp.name))
        links = reopened.links(job)
        self.assertEqual([link['job_id'] for link in links], [job])
        self.assertEqual(links[0]['kind'], 'continuation')

    def test_execute_resume_paused_and_waiting_resource(self):
        paused = self.make_job('Paused task', state='PAUSED')
        out = self.cont.execute_resume(paused, self.c1)
        self.assertEqual(out['state'], 'READY')
        waiting = self.make_job('Waiting task', state='WAITING_RESOURCE',
                                route_block='No eligible route')
        out2 = self.cont.execute_resume(waiting, self.c1)
        self.assertEqual(out2['state'], 'READY')

    def test_execute_resume_after_an_interrupted_run_rearms_the_fenced_work(self):
        # An expired/orphaned run leaves its milestone fenced as UNCERTAIN so the engine never
        # replays an unconfirmed writer by itself (D7). The person saying "continue" is the
        # authority that lifts the fence; before D19 this call attached the link and did nothing
        # else, so the promise the Work page makes (reply "continue") was silently empty.
        job = self.make_job('Interrupted task', state='WAITING_RESOURCE', verdict='UNCERTAIN',
                            milestones={'m1': {'state': 'UNCERTAIN', 'attempts': 1,
                                               'error': 'Expired run; native state requires '
                                                        'reconciliation'}})
        out = self.cont.execute_resume(job, self.c1, reason='user: continue')
        self.assertEqual(out['state'], 'READY')
        row = self.store.get(job)
        self.assertEqual(row['state'], 'READY')
        self.assertEqual(row['milestones']['m1']['state'], 'NEEDS_REPAIR')
        self.assertIsNone(row['milestones']['m1']['artifact'])
        self.assertEqual(row['milestones']['m1']['attempts'], 1, 'the fresh attempt is not pre-spent')
        with contextlib.closing(self.store.connect()) as db:
            kinds = [r['type'] for r in db.execute(
                'SELECT type FROM events WHERE aggregate_id=?', (job,))]
        self.assertIn('job.reopened', kinds)

    def test_execute_resume_keeps_an_automatic_route_wait_separate(self):
        # A route-blocked job resumes by itself once a worker appears, so a person asking early
        # clears the block and must never take the fence-lifting path.
        job = self.make_job('Waiting on a worker', state='WAITING_RESOURCE', verdict='UNCERTAIN',
                            route_block='No eligible route',
                            milestones={'m1': {'state': 'READY', 'attempts': 0}})
        out = self.cont.execute_resume(job, self.c1)
        self.assertEqual(out['state'], 'READY')
        row = self.store.get(job)
        self.assertEqual(row['milestones']['m1']['state'], 'READY')
        self.assertIsNone(row.get('route_block'))
        with contextlib.closing(self.store.connect()) as db:
            kinds = [r['type'] for r in db.execute(
                'SELECT type FROM events WHERE aggregate_id=?', (job,))]
        self.assertIn('route.retry', kinds)
        self.assertNotIn('job.reopened', kinds)

    def test_execute_resume_closed_reopens_with_event(self):
        job = self.make_job('Closed task', state='CLOSED', verdict='FAILED',
                            milestones={'m1': {'state': 'NEEDS_REPAIR'}})
        out = self.cont.execute_resume(job, self.c1)
        self.assertEqual(out['state'], 'READY')
        with contextlib.closing(self.store.connect()) as db:
            kinds = [r['type'] for r in db.execute(
                'SELECT type FROM events WHERE aggregate_id=?', (job,))]
        self.assertIn('job.reopened', kinds)

    def test_revalidation_invalidates_source_changed_milestones(self):
        root = self.temp.name + '/repo'
        import pathlib
        pathlib.Path(root).mkdir()
        pathlib.Path(root + '/main.py').write_text('x = 1', encoding='utf-8')
        two = {'request': 'Coding task',
               'milestones': [
                   {'id': 'm1', 'objective': 'One', 'filename': 'a.md', 'depends_on': [],
                    'checks': [{'kind': 'min_chars', 'value': 40}]},
                   {'id': 'm2', 'objective': 'Two', 'filename': 'b.md', 'depends_on': [],
                    'checks': [{'kind': 'min_chars', 'value': 40}]}]}
        job = self.store.create(two, conversation=self.c1)
        self.tweak(job, state='CLOSED', verdict='UNCERTAIN',
                   contract={'kind': 'coding', 'root': root,
                             'source_digest': 'git:deadbeef'},
                   milestones={'m1': {'state': 'ACCEPTED'},
                               'm2': {'state': 'UNCERTAIN', 'attempts': 1}})
        plan = self.cont.plan_resume(job)
        self.assertEqual([item['id'] for item in plan['revalidate']], ['m1'])
        self.assertIn('m2', plan['reopen'])
        self.assertEqual(plan['preserve'], [])
        out = self.cont.execute_resume(job, self.c1)
        self.assertEqual(out['state'], 'READY')
        job_row = self.store.get(job)
        self.assertEqual(job_row['milestones']['m1']['state'], 'INVALIDATED')
        self.assertIn('source changed', job_row['milestones']['m1']['error'])

    def test_revalidation_preserves_matching_digest(self):
        import pathlib
        from kel.projectmap import fingerprint
        root = pathlib.Path(self.temp.name) / 'repo2'
        root.mkdir()
        (root / 'main.py').write_text('y = 2', encoding='utf-8')
        digest = fingerprint(root)
        job = self.make_job('Coding task', contract={'kind': 'coding', 'root': str(root),
                                                     'source_digest': digest},
                            milestones={'m1': {'state': 'ACCEPTED'}})
        plan = self.cont.plan_resume(job)
        self.assertEqual(plan['preserve'], ['m1'])
        self.assertEqual(plan['revalidate'], [])

    def test_legacy_coding_milestone_uses_evidence_check(self):
        from unittest import mock
        import kel.coding as coding
        job = self.make_job('Legacy coding', contract={'kind': 'coding'},
                            milestones={'m1': {'state': 'ACCEPTED',
                                               'artifact': {'run_id': 'run1'}}})
        with mock.patch.object(coding, 'check_evidence', return_value='VERIFIED'):
            plan = self.cont.plan_resume(job)
        self.assertEqual(plan['preserve'], ['m1'])
        with mock.patch.object(coding, 'check_evidence', return_value='UNCERTAIN'):
            plan2 = self.cont.plan_resume(job)
        self.assertEqual([item['id'] for item in plan2['revalidate']], ['m1'])

    def test_native_session_validation(self):
        from kel.continuation import valid_session_id
        job = self.make_job('Session task')
        with self.store.transaction() as db:
            db.execute("INSERT INTO runs(id,job_id,milestone_id,epoch,state,reservation,"
                       "expires,result) VALUES('run1',?,?,1,'RESULT_RECORDED',0,0,NULL)",
                       (job, 'm1'))
            db.execute("UPDATE runs SET native_session='8a5c2f1e-42bd-4c7e-9d10-abcdef012345',"
                       " provider='claude', model='sonnet' WHERE id='run1'")
        plan = self.cont.plan_resume(job)
        self.assertTrue(plan['session']['valid'])
        self.assertEqual(plan['session']['provider'], 'claude')
        self.assertTrue(valid_session_id('abc-123_XY.z'))
        self.assertFalse(valid_session_id('has spaces'))
        self.assertFalse(valid_session_id(''))

    def test_approval_state_survives_attach_only(self):
        job = self.make_job('Waiting approval', state='AWAITING_USER',
                            milestones={'m1': {'state': 'NEEDS_REPAIR'}})
        out = self.cont.execute_resume(job, self.c1)
        self.assertEqual(out['state'], 'AWAITING_USER')
        self.assertTrue(self.cont.links(job))

    def test_idempotent_execute_resume(self):
        job = self.make_job('Repeatable', state='PAUSED')
        first = self.cont.execute_resume(job, self.c1)
        second = self.cont.execute_resume(job, self.c1)
        self.assertEqual(first['state'], 'READY')
        self.assertEqual(second['state'], 'READY')
        self.assertFalse(second['link_created'])
        self.assertEqual(len(self.cont.links(job)), 1)


class InterruptedRunCase(unittest.TestCase):
    """The interrupted-run journey end to end: a lost run, then the person's continuation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.context = Context(self.store)
        self.p1 = self.context.project('One', project_id='p1')
        self.c1 = self.context.conversation('p1', title='First')

    def test_continue_after_a_lost_run_finishes_the_same_job(self):
        job = self.store.create(contract('Write the interrupted report'), conversation=self.c1)
        lost = self.store.claim(job, 'm1')
        self.store.recover_expired(now=time.time() + 100000)  # what startup recovery does
        fenced = self.store.get(job)
        self.assertEqual(fenced['state'], 'WAITING_RESOURCE')
        self.assertEqual(fenced['milestones']['m1']['state'], 'UNCERTAIN')

        engine = Engine(self.store, {'fixture': FixtureAdapter(output='x' * 80)})
        self.addCleanup(engine.close)
        out = Continuation(self.store).execute_resume(job, self.c1, reason='user: continue')
        self.assertEqual(out['state'], 'READY')
        result = engine.wait(job, 60)
        for _ in range(5):
            if result.get('state') == 'CLOSED':
                break
            result = engine.wait(job, 60)
        row = self.store.get(job)
        self.assertEqual(row['state'], 'CLOSED')
        self.assertEqual(row['verdict'], 'VERIFIED')
        self.assertEqual(row['milestones']['m1']['state'], 'ACCEPTED')
        self.assertEqual(row['milestones']['m1']['attempts'], 2, 'a fresh attempt ran')
        # The accepted artifact comes from the new run, never from a replayed fenced run.
        self.assertNotEqual(row['milestones']['m1']['artifact']['run_id'], lost['id'])
        self.assertIsNone(row['milestones']['m1']['error'])

    def test_continue_still_refuses_verified_work(self):
        job = self.store.create(contract('Already finished'), conversation=self.c1)
        with self.store.transaction() as db:
            row = self.store._get(db, job)
            row.update(state='CLOSED', verdict='VERIFIED')
            row['milestones']['m1'].update(state='ACCEPTED', artifact={'hi': 'there'})
            self.store._save(db, row, 'test.fixture')
        with self.assertRaises(PolicyError):
            Continuation(self.store).execute_resume(job, self.c1)


if __name__ == '__main__':
    unittest.main()
