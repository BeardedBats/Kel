"""Routing 2 §5.4 — the budget governor: classes with ceilings, reserve before spawn, a plain stop.

Exhaustion stops the job before its next step and waits for Nick (never auto-retried, never moved to
a cheaper model); a review of finished work still runs; Nick raising the budget lets it continue.
No provider is called — the adapters are fixtures.
"""
import concurrent.futures
import contextlib
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from kel import budget, staff, usage
from kel.core import Store
from kel.engine import Engine
from kel.native import FixtureAdapter


def writing(text='Tidy up this shopping list into sections'):
    return {'request': text, 'milestones': [{'id': 'd', 'objective': text, 'filename': 'd.md',
                                             'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 5}]}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        os.environ.pop('KEL_WORKFORCE', None)
        os.environ['CODEX_HOME'] = str(Path(self.tmp.name) / 'codex-home')
        self.store = Store(Path(self.tmp.name) / 'data')
        staff.ensure_schema(self.store)

    def staffed(self, contract):
        contract = dict(contract)
        contract['staffing'] = staff.plan_job(self.store, contract)
        return self.store.create(contract)

    def spend(self, job, tokens, call='old-1'):
        usage.record(self.store, call, job_id=job, adapter='codex', model='gpt-6-luna', task_class='writing',
                     result={'usage': {'input_tokens': tokens, 'cached_input_tokens': 0, 'output_tokens': 0},
                             'wall_ms': 1000})


class ClassTests(unittest.TestCase):
    def test_the_class_follows_the_staffing_tier_and_risk(self):
        self.assertEqual(budget.class_for('D0'), 'tiny')
        self.assertEqual(budget.class_for('D1'), 'standard')
        self.assertEqual(budget.class_for('D2', features={'complexity': 2}), 'deep')
        self.assertEqual(budget.class_for('D3'), 'deep')
        self.assertEqual(budget.class_for('D1', flags=['security_boundary']), 'high-assurance')
        self.assertEqual(budget.class_for('D4'), 'high-assurance')


class GovernorTests(Base):
    def test_the_class_is_frozen_with_the_staffing_decision(self):
        record = staff.plan_job(self.store, writing())
        self.assertEqual(record['budget']['class'], record['budget_class'])
        self.assertEqual(record['budget']['ceilings'], budget.CEILINGS[record['budget_class']])

    def test_a_step_that_would_pass_the_ceiling_is_refused_in_plain_words(self):
        job = self.staffed(writing())
        cls = budget.job_class(self.store, self.store.get(job))
        step = budget.estimate(self.store, 'writing', 'gpt-6-luna')
        self.assertIsNone(budget.check(self.store, self.store.get(job), step))
        self.spend(job, budget.CEILINGS[cls]['tokens'])
        reason = budget.check(self.store, self.store.get(job), step)
        self.assertIn('tokens', reason)
        self.assertIn('rather than continue on a cheaper model', reason)
        self.assertNotIn('D1', reason)

    def test_the_engine_reserves_before_spawn_and_settles_with_the_measurement(self):
        job = self.staffed(writing())
        fixture = FixtureAdapter(output='## Shopping\n- apples\n- bread')
        engine = Engine(self.store, {'fixture': fixture})
        try:
            deadline = time.time() + 20
            while time.time() < deadline and self.store.get(job)['state'] != 'CLOSED':
                engine.tick()
                time.sleep(.02)
        finally:
            engine.close()
        with contextlib.closing(self.store.connect()) as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM budget_reservations WHERE job_id=?', (job,))]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['state'], 'consumed')
        self.assertEqual(rows[0]['budget_class'], budget.job_class(self.store, self.store.get(job)))

    def test_exhaustion_waits_for_nick_and_raising_the_budget_continues(self):
        job = self.staffed(writing())
        cls = budget.job_class(self.store, self.store.get(job))
        self.spend(job, budget.CEILINGS[cls]['tokens'])
        fixture = FixtureAdapter(output='## Shopping\n- apples\n- bread')
        engine = Engine(self.store, {'fixture': fixture})
        try:
            for _ in range(30):
                engine.tick()
                time.sleep(.01)
            waiting = self.store.get(job)
            self.assertEqual(waiting['state'], 'WAITING_RESOURCE')
            self.assertTrue(waiting['route_block'].startswith(budget.BUDGET_WAIT))
            self.assertEqual(fixture.calls, 0, 'nothing ran, and nothing ran on a cheaper model')
            from kel.continuation import Continuation
            brief = Continuation(self.store).resume_brief(job)
            self.assertTrue(brief['needs_you'])
            self.assertIn('Raise its budget', brief['next'])
            from kel.core import explain_failure
            self.assertIn('This work reached its budget.', explain_failure(waiting))
            raised = budget.raise_class(self.store, job)
            self.assertEqual((raised['from'], raised['to']), (cls, budget.ORDER[budget.ORDER.index(cls) + 1]))
            deadline = time.time() + 20
            while time.time() < deadline and self.store.get(job)['state'] != 'CLOSED':
                engine.tick()
                time.sleep(.02)
        finally:
            engine.close()
        self.assertEqual(self.store.get(job)['state'], 'CLOSED')
        self.assertEqual(fixture.calls, 1)
        from kel.activity import sentence_for
        self.assertIn('raised the budget', sentence_for('budget.raised', {'detail': {'to': 'deep'}}))

    def test_closing_the_engine_right_after_a_job_settles_keeps_it_closed(self):
        # Regression: close() paused every job with an entry in `active`, including one whose run
        # had finished and been assessed CLOSED in the same tick, turning finished work PAUSED.
        job = self.staffed(writing())
        fixture = FixtureAdapter(output='## Shopping\n- apples\n- bread')
        engine = Engine(self.store, {'fixture': fixture})
        try:
            deadline = time.time() + 20
            while time.time() < deadline and self.store.get(job)['state'] != 'CLOSED':
                engine.tick()
                time.sleep(.02)
            self.assertEqual(self.store.get(job)['state'], 'CLOSED')
            # Deterministically recreate the race: the finished run is still listed as active.
            done = concurrent.futures.Future()
            done.set_result(None)
            engine.active['finished-run'] = (done, threading.Event(), {'job_id': job})
        finally:
            engine.close()
        self.assertEqual(self.store.get(job)['state'], 'CLOSED')
        self.assertEqual(self.store.control(job, 'pause'), [])
        self.assertEqual(self.store.get(job)['state'], 'CLOSED', 'pausing settled work changes nothing')

    def test_a_review_of_finished_work_still_runs_when_the_budget_is_spent(self):
        contract = writing()
        contract['milestones'][0]['checks'].append({'kind': 'manual_review', 'rubric': 'Tidy.'})
        # D-85 would give a short list a quick sanity check only; this work is set to be reviewed.
        from unittest import mock
        with mock.patch('kel.proportional.verifier_decision',
                        return_value={'when': 'always', 'why': 'reviewed', 'size': None}):
            job = self.staffed(contract)

        class Reviewer:
            provider, model = 'claude', None
            reviewed = 0

            def execute(self, prompt, run_id=None, **kwargs):
                Reviewer.reviewed += 1
                import json
                return {'outcome': 'SUCCESS', 'text': json.dumps({'verdict': 'VERIFIED', 'findings': ['Tidy.']})}

        from kel.commander import Commander
        fixture = FixtureAdapter(output='## Shopping\n- apples\n- bread')
        engine = Engine(self.store, {'fixture': fixture}, reviewer=Commander(Reviewer()))
        try:
            deadline = time.time() + 20
            while time.time() < deadline and not fixture.calls:
                engine.tick()
                time.sleep(.02)
            cls = budget.job_class(self.store, self.store.get(job))
            self.spend(job, budget.CEILINGS[cls]['tokens'] * 2, call='late')
            while time.time() < deadline and self.store.get(job)['state'] != 'CLOSED':
                engine.tick()
                time.sleep(.02)
        finally:
            engine.close()
        self.assertEqual(Reviewer.reviewed, 1, 'the check of finished work is never skipped for budget')
        self.assertEqual(self.store.get(job)['verdict'], 'VERIFIED')

    def test_the_largest_class_cannot_be_raised(self):
        job = self.staffed(writing())
        for _ in range(3):
            try:
                budget.raise_class(self.store, job)
            except Exception:
                break
        from kel.core import PolicyError
        with self.assertRaises(PolicyError):
            budget.raise_class(self.store, job)


class ApiTests(unittest.TestCase):
    def test_raise_budget_through_the_work_view(self):
        from kel.service import Service
        with tempfile.TemporaryDirectory() as tmp:
            saved = dict(os.environ)
            try:
                os.environ.update(KEL_REVIEWER='none', KEL_SKIP_TELEMETRY='1', KEL_TURN_MODEL='none',
                                  CODEX_HOME=str(Path(tmp) / 'codex-home'))
                os.environ.pop('ANTHROPIC_API_KEY', None)
                service = Service(Path(tmp) / 'data')
                try:
                    contract = writing()
                    contract['staffing'] = staff.plan_job(service.store, contract)
                    job = service.store.create(contract)
                    before = budget.job_class(service.store, service.store.get(job))
                    shown = service.office_item(job)['budget']
                    # The card names the next size and its ceilings before Nick raises it.
                    self.assertEqual(shown['next'], budget.ORDER[budget.ORDER.index(before) + 1])
                    self.assertEqual(shown['next_ceilings'], budget.CEILINGS[shown['next']])
                    out = service.action('/api/office', {'action': 'raise_budget', 'id': job})
                    self.assertEqual(out['from'], before)
                    detail = service.office_item(job)
                    self.assertEqual(detail['budget']['class'], out['to'])
                finally:
                    service.shutdown()
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == '__main__':
    unittest.main()
