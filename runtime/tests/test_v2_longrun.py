"""V2-11 — long-running work: runtime fencing, the Work brief, and the resume brief.

The liveness truths (R6) already rule the floor: an expired run is fenced and never auto-replayed,
waiting is neither completion nor failure, and a dead process is reported rather than completed.
V2-11 adds the runtime half (the engine fences runs nothing durable can carry) and the person's half
(a Work-surface brief that says what shipped, what is open, why it stopped and what only they can do).
"""
import contextlib
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from kel.continuation import Continuation
from kel.context import Context
from kel.core import Store
from kel.engine import Engine
from kel.runner import init as runner_init


def contract(request='Long run probe'):
    return {'request': request, 'milestones': [
        {'id': 'm1', 'objective': 'Work', 'filename': 'out.md', 'depends_on': [],
         'checks': [{'kind': 'min_chars', 'value': 10}]}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        runner_init(self.store)  # the brokers table exists exactly as it does in a real engine
        self.context = Context(self.store)  # projects + the 'main' conversation, as the service has

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def job(self, conversation='main'):
        return self.store.create(contract(), conversation=conversation)

    def claim(self, job_id, timeout=5):
        return self.store.claim(job_id, 'm1', provider='fixture', model='fixture', timeout=timeout)

    def rows(self, sql, args=()):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]

    def run_row(self, run_id):
        return self.rows('SELECT * FROM runs WHERE id=?', (run_id,))[0]

    def brief(self, job_id):
        return Continuation(self.store).resume_brief(job_id)


class FenceTests(Base):
    def test_an_expired_run_with_no_broker_is_fenced_and_never_replayed(self):
        job_id = self.job()
        run_id = self.claim(job_id)['id']
        fenced = self.store.recover_abandoned(now=time.time() + 60)
        self.assertEqual(fenced, [run_id])
        self.assertEqual(self.run_row(run_id)['state'], 'ORPHANED')
        job = self.store.get(job_id)
        self.assertEqual(job['state'], 'WAITING_RESOURCE')
        self.assertEqual(job['verdict'], 'UNCERTAIN')
        milestone = job['milestones']['m1']
        self.assertEqual(milestone['state'], 'UNCERTAIN')
        self.assertIn('requires reconciliation', milestone['error'])
        self.assertNotEqual(milestone['state'], 'READY', 'fencing never re-arms on its own')
        self.assertEqual(self.store.recover_abandoned(now=time.time() + 60), [],
                         'fencing is idempotent')

    def test_a_broker_backed_run_is_left_for_the_engine_to_adopt(self):
        job_id = self.job()
        claim = self.claim(job_id)
        with self.store.transaction() as db:
            db.execute('INSERT INTO brokers(run_id,epoch,provider,state) VALUES(?,?,?,?)',
                       (claim['id'], claim['epoch'], 'fixture', 'RUNNING'))
        self.assertEqual(self.store.recover_abandoned(now=time.time() + 60), [])
        self.assertEqual(self.run_row(claim['id'])['state'], 'RUNNING')

    def test_a_fresh_lease_and_an_active_run_are_never_fenced(self):
        job_id = self.job()
        run_id = self.claim(job_id, timeout=300)['id']
        self.assertEqual(self.store.recover_abandoned(now=time.time()), [],
                         'a live lease is not fenced')
        self.assertEqual(self.run_row(run_id)['state'], 'RUNNING')
        self.assertEqual(self.store.recover_abandoned(now=time.time() + 1000,
                                                      exclude=(run_id,)), [],
                         'an active run in this process is excluded even when its lease lapsed')
        self.assertEqual(self.run_row(run_id)['state'], 'RUNNING')

    def test_the_engine_fences_abandoned_runs_on_a_tick(self):
        job_id = self.job()
        run_id = self.claim(job_id)['id']
        engine = Engine(self.store, {}, concurrency=1)
        try:
            with self.store.transaction() as db:
                db.execute('UPDATE runs SET expires=0 WHERE id=?', (run_id,))
            engine.tick()
        finally:
            engine.close()
        self.assertEqual(self.run_row(run_id)['state'], 'ORPHANED')
        self.assertEqual(self.store.get(job_id)['state'], 'WAITING_RESOURCE')

    def test_continuing_a_fenced_job_re_arms_it_as_the_persons_decision(self):
        job_id = self.job()
        run_id = self.claim(job_id)['id']
        self.store.recover_abandoned(now=time.time() + 60)
        out = Continuation(self.store).execute_resume(job_id, 'main', reason='test continuation')
        self.assertEqual(out['state'], 'READY')
        job = self.store.get(job_id)
        self.assertIn(job['milestones']['m1']['state'], ('READY', 'NEEDS_REPAIR'))
        again = self.store.claim(job_id, 'm1', provider='fixture', model='fixture')
        self.assertNotEqual(again['id'], run_id, 'continuation starts a fresh attempt')

    def test_recover_expired_still_fences_any_expired_lease(self):
        # The deliberate difference: the person's own `recover` command fences everything expired,
        # including a broker-backed run; only the runtime path is narrower.
        job_id = self.job()
        claim = self.claim(job_id)
        with self.store.transaction() as db:
            db.execute('INSERT INTO brokers(run_id,epoch,provider,state) VALUES(?,?,?,?)',
                       (claim['id'], claim['epoch'], 'fixture', 'RUNNING'))
        self.assertEqual(self.store.recover_expired(now=time.time() + 60), [claim['id']])


class BriefTests(Base):
    def test_the_brief_of_a_fenced_job_says_so_and_what_next(self):
        job_id = self.job()
        self.claim(job_id)
        self.store.recover_abandoned(now=time.time() + 60)
        brief = self.brief(job_id)
        self.assertTrue(brief['fenced'])
        self.assertTrue(brief['needs_you'])
        self.assertIn('not replay', brief['why'])
        self.assertTrue(brief['next'].startswith('Say "continue"'))
        self.assertEqual([item['id'] for item in brief['open']], ['m1'])
        self.assertEqual(brief['shipped'], [])

    def test_a_route_blocked_job_is_automatic_and_not_the_person(self):
        job_id = self.job()
        self.store.wait_for_route(job_id, 'No eligible route: provider quota exhausted')
        brief = self.brief(job_id)
        self.assertFalse(brief['needs_you'], 'a routing block clears itself')
        self.assertIn('No model was free', brief['why'])
        self.assertIn('automatically', brief['next'])

    def test_a_running_job_and_a_queued_job_need_nothing(self):
        running = self.job('running')
        self.claim(running, timeout=300)
        brief = self.brief(running)
        self.assertIn('working on it now', brief['why'])
        self.assertFalse(brief['needs_you'])
        queued = self.job('queued')
        brief = self.brief(queued)
        self.assertIn('Queued', brief['why'])
        self.assertFalse(brief['needs_you'])

    def test_a_verified_closed_job_reads_done(self):
        job_id = self.job()
        with self.store.transaction() as db:
            job = self.store._get(db, job_id)
            job.update(state='CLOSED', verdict='VERIFIED')
            self.store._save(db, job, 'test.close')
        brief = self.brief(job_id)
        self.assertEqual(brief['why'], 'Done and verified.')
        self.assertFalse(brief['needs_you'])
        self.assertIn('new change', brief['next'])


class SurfaceTests(Base):
    def setUp(self):
        super().setUp()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('ANTHROPIC_API_KEY', None)
            os.environ.pop('KEL_INTERNAL_MODEL', None)
            os.environ['KEL_SKIP_TELEMETRY'] = '1'
            os.environ['KEL_REVIEWER'] = 'none'
            from kel.service import Service
            self.service = Service(Path(self.tmp.name) / 'svc')
        self.addCleanup(self._shutdown)

    def _shutdown(self):
        self.service.shutdown()

    def test_the_work_surface_reports_needs_you_and_the_next_step(self):
        job_id = self.service.store.create(contract(), conversation='main')
        self.service.store.claim(job_id, 'm1', provider='fixture', model='fixture', timeout=5)
        self.service.store.recover_abandoned(now=time.time() + 600)
        second = self.service.store.create(contract('Second probe'), conversation='main')
        self.service.store.wait_for_route(second, 'No eligible route: provider quota exhausted')
        work = self.service._work('main')['work']
        by_id = {entry['job_id']: entry for entry in work['jobs']}
        self.assertIn(job_id, by_id)
        self.assertIn(second, by_id)
        self.assertTrue(by_id[job_id]['needs_you'])
        self.assertTrue(by_id[job_id]['fenced'])
        self.assertTrue(by_id[job_id]['next'].startswith('Say "continue"'))
        self.assertFalse(by_id[second]['needs_you'])
        self.assertEqual(work['needs_you'], 1, 'only the person-action job counts')
        self.assertEqual(work['jobs'][0]['job_id'], job_id, 'needs-you jobs sort first')


if __name__ == '__main__':
    unittest.main()
