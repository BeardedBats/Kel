from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from kel.core import Store, PolicyError, Conflict, aggregate, validate_contract
from kel.engine import Engine, compile_document
from kel.internal import InternalAdapter
from kel.native import FixtureAdapter, NativeAdapter
from kel.router import Candidate, select


def contract(two=False, review=False):
    checks = [{'kind': 'contains', 'value': 'ACCEPT'}, {'kind': 'min_chars', 'value': 6}]
    if review: checks.append({'kind': 'manual_review', 'rubric': 'Clear and accurate'})
    ms = [{'id': 'a', 'objective': 'Write ACCEPT', 'filename': 'a.md', 'checks': checks}]
    if two: ms.append({'id': 'b', 'objective': 'Write ACCEPT B', 'filename': 'b.md', 'checks': checks})
    return {'request': 'Write ACCEPT', 'milestones': ms}


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def result(self, job, mid='a', text='ACCEPT valid artifact', event='event', **extra):
        run = self.store.claim(job, mid)
        self.store.enqueue_result(event, run['id'], run['epoch'], {'outcome': 'SUCCESS', 'text': text, **extra})
        self.store.consume()
        return run

    def test_P06_worker_success_is_not_completion(self):
        job = self.store.create(contract())
        self.result(job, text='wrong')
        self.assertEqual(self.store.get(job)['verdict'], 'UNCERTAIN')
        self.assertEqual(self.store.verify(job, 'a'), 'FAILED')
        self.assertEqual(self.store.assess(job), 'FAILED')

    def test_cancel_racing_launch_finalizes_with_terminal_receipt(self):
        import contextlib
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        self.store.control(job, 'cancel')
        # The broker launch raced the cancel: its terminal receipt arrives after
        # the run is already CANCEL_REQUESTED and must settle the job.
        self.store.enqueue_result('launch-failed', run['id'], run['epoch'],
                                  {'outcome': 'FAILED', 'error': 'Run is no longer active'})
        self.assertEqual(self.store.consume(), 1)
        current = self.store.get(job)
        self.assertEqual(current['state'], 'CANCELLED')
        self.assertEqual(current['milestones']['a']['state'], 'CANCELLED')
        with contextlib.closing(self.store.connect()) as db:
            run_row = db.execute('SELECT state, reservation FROM runs WHERE id=?', (run['id'],)).fetchone()
        self.assertEqual(run_row['state'], 'CANCELLED')
        self.assertEqual(run_row['reservation'], 0)

    def test_verified_artifact_and_single_publication(self):
        job = self.store.create(contract())
        self.result(job)
        self.store.verify(job, 'a')
        self.assertEqual(self.store.assess(job), 'VERIFIED')
        self.assertTrue(self.store.publish(job)[1])
        self.assertFalse(self.store.publish(job)[1])

    def test_P21_changed_bytes_invalidate_before_publication(self):
        job = self.store.create(contract())
        self.result(job)
        self.store.verify(job, 'a')
        self.store.assess(job)
        artifact = self.store.get(job)['milestones']['a']['artifact']
        (self.store.root/artifact['path']).write_text('tampered')
        self.assertEqual(self.store.assess(job), 'UNCERTAIN')
        with self.assertRaises(PolicyError): self.store.publish(job)

    def test_P08_missing_review_is_uncertain(self):
        job = self.store.create(contract(review=True))
        self.result(job)
        self.assertEqual(self.store.verify(job, 'a'), 'UNCERTAIN')
        self.assertEqual(self.store.assess(job), 'UNCERTAIN')

    def test_P07_accepted_milestone_not_reexecuted(self):
        job = self.store.create(contract(two=True))
        self.result(job)
        self.store.verify(job, 'a')
        artifact = self.store.get(job)['milestones']['a']['artifact']
        self.result(job, mid='b', text='bad', event='second')
        self.store.verify(job, 'b')
        self.store.assess(job)
        with self.assertRaises(PolicyError): self.store.claim(job, 'a')
        self.assertEqual(self.store.get(job)['milestones']['a']['artifact'], artifact)
        self.assertEqual(self.store.claim(job, 'b')['attempt'], 2)

    def test_P13_duplicate_event_consumed_once(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        payload = {'outcome': 'SUCCESS', 'text': 'ACCEPT'}
        self.assertTrue(self.store.enqueue_result('same', run['id'], run['epoch'], payload))
        self.assertFalse(self.store.enqueue_result('same', run['id'], run['epoch'], payload))
        self.assertEqual(self.store.consume(), 1)
        self.assertEqual(self.store.consume(), 0)

    def test_P13_wrong_epoch_ignored(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        self.store.enqueue_result('stale', run['id'], 'old', {'outcome': 'SUCCESS', 'text': 'ACCEPT'})
        self.assertEqual(self.store.consume(), 0)
        self.assertIsNone(self.store.get(job)['milestones']['a']['artifact'])

    def test_P15_parallel_budget_reservation(self):
        job = self.store.create(contract(two=True), budget=2)
        def attempt(mid):
            try: self.store.claim(job, mid); return True
            except PolicyError: return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ['a', 'b']))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.store.get(job)['reserved'], 2)

    def test_verification_reserve_survives_result(self):
        job = self.store.create(contract(two=True), budget=3)
        self.result(job)
        self.assertEqual(self.store.get(job)['reserved'], 1)
        with self.assertRaises(PolicyError): self.store.claim(job, 'b')
        self.store.verify(job, 'a')
        self.assertEqual(self.store.get(job)['spent'], 2)
        self.assertEqual(self.store.get(job)['reserved'], 0)

    def test_P11_restart_retains_work_and_rebuild(self):
        job = self.store.create(contract())
        self.result(job)
        reopened = Store(self.temp.name)
        expected = reopened.get(job)
        self.assertEqual(reopened.rebuild(), 1)
        self.assertEqual(reopened.get(job), expected)
        self.assertEqual(reopened.verify(job, 'a'), 'VERIFIED')

    def test_expired_run_is_not_blindly_replayed(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a', timeout=1)
        self.assertEqual(self.store.recover_expired(time.time()+3), [run['id']])
        self.assertEqual(self.store.get(job)['state'], 'WAITING_RESOURCE')
        self.store.enqueue_result('late', run['id'], run['epoch'], {'outcome':'SUCCESS','text':'ACCEPT'})
        self.assertEqual(self.store.consume(), 0)

    def test_P09_approval_persists_and_resumes(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        action = {'operation': 'publish', 'target': 'fixture', 'sha': '123'}
        approval = self.store.request_approval(job, run['id'], action)
        self.assertEqual(Store(self.temp.name).get(job)['state'], 'AWAITING_USER')
        self.assertEqual(self.store.resolve_approval(approval, action, True), 'APPROVED')
        self.assertEqual(self.store.get(job)['state'], 'RUNNING')

    def test_approval_cannot_authorize_changed_action(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        approval = self.store.request_approval(job, run['id'], {'target': 'a'})
        with self.assertRaises(PolicyError): self.store.resolve_approval(approval, {'target': 'b'}, True)
        with self.assertRaises(PolicyError): self.store.resolve_approval(approval, {'target': 'a'}, True, actor='worker')

    def test_P10_denial_cannot_be_retried(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        a = {'target': 'a'}
        approval = self.store.request_approval(job, run['id'], a)
        self.assertEqual(self.store.resolve_approval(approval, a, False), 'DENIED')
        with self.assertRaises(PolicyError): self.store.claim(job, 'a')
        with self.assertRaises(PolicyError): self.store.resolve_approval(approval, a, True)

    def test_expired_approval_is_not_approved(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        a = {'target': 'a'}
        approval = self.store.request_approval(job, run['id'], a, seconds=-1)
        self.assertEqual(self.store.resolve_approval(approval, a, True), 'EXPIRED')

    def test_P16_cancel_needs_ack(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        self.store.control(job, 'cancel')
        self.assertEqual(self.store.get(job)['state'], 'CANCELLING')
        self.store.acknowledge_stop(run['id'], run['epoch'])
        self.assertEqual(self.store.get(job)['state'], 'CANCELLED')
        self.assertFalse(self.store.acknowledge_stop(run['id'], run['epoch']))

    def test_pause_and_resume(self):
        job = self.store.create(contract())
        run = self.store.claim(job, 'a')
        self.store.control(job, 'pause')
        self.assertEqual(self.store.get(job)['state'], 'PAUSING')
        self.store.acknowledge_stop(run['id'], run['epoch'])
        self.store.control(job, 'resume')
        self.assertEqual(self.store.get(job)['state'], 'READY')

    def test_P12_unknown_effect_prevents_completion(self):
        job = self.store.create(contract())
        self.result(job)
        self.store.verify(job, 'a')
        a = {'publish': 'fixture'}
        self.assertEqual(self.store.prepare_effect(job, 'op', a), 'PREPARED')
        self.assertEqual(self.store.prepare_effect(job, 'op', a), 'PREPARED')
        self.assertEqual(self.store.assess(job), 'UNCERTAIN')
        self.store.observe_effect('op', {'receipt': 'remote-123'})
        self.assertEqual(self.store.assess(job), 'VERIFIED')

    def test_effect_id_cannot_change_target(self):
        job = self.store.create(contract())
        self.store.prepare_effect(job, 'op', {'target':'a'})
        with self.assertRaises(PolicyError): self.store.prepare_effect(job, 'op', {'target':'b'})

    def test_P20_scope_revision_retains_only_unchanged_acceptance(self):
        job = self.store.create(contract(two=True))
        self.result(job)
        self.store.verify(job, 'a')
        old = self.store.get(job)
        revised = contract(two=True)
        revised['milestones'][1]['objective'] = 'Changed outcome'
        self.store.revise(job, revised, old['revision'])
        updated = self.store.get(job)
        self.assertEqual(updated['contract_version'], 2)
        self.assertEqual(updated['milestones']['a'], old['milestones']['a'])
        with self.assertRaises(Conflict): self.store.revise(job, revised, old['revision'])

    def test_P19_executable_or_always_pass_oracle_rejected(self):
        c = contract()
        c['milestones'][0]['checks'] = [{'kind': 'python', 'code': 'return True'}]
        with self.assertRaises(PolicyError): validate_contract(c)

    def test_empty_literal_rejected(self):
        c = contract(); c['milestones'][0]['checks'] = [{'kind':'contains','value':''}]
        with self.assertRaises(PolicyError): validate_contract(c)

    def test_path_escape_rejected(self):
        c = contract(); c['milestones'][0]['filename'] = '../escape.md'
        with self.assertRaises(PolicyError): validate_contract(c)

    def test_dependency_cycle_rejected(self):
        c = contract(two=True)
        c['milestones'][0]['depends_on'] = ['b']; c['milestones'][1]['depends_on'] = ['a']
        with self.assertRaises(PolicyError): validate_contract(c)

    def test_dependency_gate(self):
        c = contract(two=True); c['milestones'][1]['depends_on'] = ['a']
        job = self.store.create(c)
        with self.assertRaises(PolicyError): self.store.claim(job, 'b')

    def test_P22_disk_failure_does_not_accept_result(self):
        job = self.store.create(contract()); run = self.store.claim(job, 'a')
        self.store.enqueue_result('disk', run['id'], run['epoch'], {'outcome':'SUCCESS','text':'ACCEPT'})
        with patch.object(self.store, '_artifact', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.store.consume()
        self.assertEqual(self.store.get(job)['milestones']['a']['state'], 'RUNNING')
        self.assertEqual(self.store.consume(), 1)

    def test_malformed_result_cannot_pass(self):
        job = self.store.create(contract()); run = self.store.claim(job, 'a')
        self.store.enqueue_result('malformed', run['id'], run['epoch'], {'outcome':'VERIFIED','text':'ACCEPT'})
        self.store.consume()
        self.assertEqual(self.store.assess(job), 'FAILED')

    def test_P18_wrong_artifact_subject_rejected(self):
        job = self.store.create(contract()); self.result(job)
        with self.store.transaction() as db:
            j = self.store._get(db, job); j['milestones']['a']['artifact']['job_id']='another'
            self.store._save(db,j,'test.tamper')
        self.assertEqual(self.store.verify(job, 'a'), 'UNCERTAIN')

    def test_P05_side_message_does_not_stop_work(self):
        e = Engine(self.store, {'fixture': FixtureAdapter(output='ACCEPT '+('x'*50),delay=.3)})
        try:
            job = e.submit(contract()); e.tick()
            self.store.add_message('What is the status?')
            self.assertEqual(e.wait(job, 5)['verdict'], 'VERIFIED')
        finally: e.close()

    def test_engine_repairs_only_failed_candidate(self):
        adapter = FixtureAdapter(output='ACCEPT good artifact', fail_first=True)
        e = Engine(self.store, {'fixture': adapter})
        try:
            job = e.submit(contract()); done=e.wait(job,5)
            self.assertEqual(done['verdict'], 'VERIFIED')
            self.assertEqual(done['milestones']['a']['attempts'],2)
        finally: e.close()

    def test_engine_bounded_retries(self):
        e = Engine(self.store, {'fixture': FixtureAdapter(output='bad')})
        try:
            job=e.submit(contract()); result=e.wait(job,5)
            self.assertEqual(result['verdict'],'FAILED')
            self.assertEqual(result['milestones']['a']['attempts'],4)
        finally: e.close()

    def test_only_one_controller_owns_a_store(self):
        self.store.controller_lease('first')
        with self.assertRaises(Conflict):self.store.controller_lease('second')
        self.store.controller_lease('first',release=True)
        self.store.controller_lease('second')

    def test_global_concurrency_across_jobs(self):
        jobs=[self.store.create(contract()) for _ in range(3)]
        self.store.claim(jobs[0],'a');self.store.claim(jobs[1],'a')
        with self.assertRaises(PolicyError):self.store.claim(jobs[2],'a')

    def test_scope_change_invalidates_accepted_dependents(self):
        c=contract(two=True);c['milestones'][1]['depends_on']=['a']
        job=self.store.create(c)
        self.result(job);self.store.verify(job,'a')
        self.result(job,mid='b',event='b');self.store.verify(job,'b')
        c['milestones'][0]['objective']='New input'
        self.store.revise(job,c,self.store.get(job)['revision'])
        self.assertEqual(self.store.get(job)['milestones']['b']['state'],'READY')

    def test_review_cannot_use_executor_identity(self):
        job=self.store.create(contract(review=True));run=self.result(job)
        self.store.verify(job,'a')
        sha=self.store.get(job)['milestones']['a']['artifact']['sha256']
        with self.assertRaises(PolicyError):self.store.record_review(job,'a',sha,run['id'],'VERIFIED',['Claim'])

    def test_review_cannot_override_failed_literal(self):
        job=self.store.create(contract(review=True));self.result(job,text='wrong output')
        self.store.verify(job,'a')
        sha=self.store.get(job)['milestones']['a']['artifact']['sha256']
        self.assertEqual(self.store.record_review(job,'a',sha,'reviewer','VERIFIED',['Looks clear']),'FAILED')

    def test_pause_engine_terminates_fixture(self):
        engine=Engine(self.store,{'fixture':FixtureAdapter(delay=10)})
        job=engine.submit(contract());engine.tick()
        engine.control(job,'pause');engine.close()
        self.assertEqual(self.store.get(job)['state'],'PAUSED')

    def test_review_rejects_changed_subject(self):
        job=self.store.create(contract(review=True));self.result(job)
        self.store.verify(job,'a')
        with self.assertRaises(PolicyError):self.store.record_review(job,'a','different','reviewer','VERIFIED',['Claim'])

    def test_provider_health_survives_restart(self):
        for _ in range(3):self.store.provider_outcome('worker',{'outcome':'FAILED','error':'transport'})
        state=Store(self.temp.name).provider_states()['worker']
        self.assertGreater(state['circuit_until'],time.time())

    def test_authentication_failure_disables_route(self):
        self.store.provider_outcome('worker',{'outcome':'FAILED','error':'HTTP 401'})
        self.assertGreater(self.store.provider_states()['worker']['circuit_until'],time.time())

    def test_review_cannot_accept_a_new_contract_version(self):
        job=self.store.create(contract(review=True));self.result(job)
        self.store.verify(job,'a')
        sha=self.store.get(job)['milestones']['a']['artifact']['sha256']
        with self.assertRaises(Conflict):self.store.record_review(job,'a',sha,'reviewer','VERIFIED',['Claim'],expected_contract_version=0)


class RoutingTests(unittest.TestCase):
    def test_P14_quota_exhaustion(self):
        r=select([Candidate('cheap',cost=0,quota=0),Candidate('available',cost=1,quota=None)])
        self.assertEqual(r['selected'],'available');self.assertTrue(r['unknown_quota'])

    def test_health_circuit(self):
        self.assertEqual(select([Candidate('bad',circuit_until=time.time()+60),Candidate('ok')])['selected'],'ok')

    def test_explicit_choice_not_silently_overridden(self):
        with self.assertRaises(PolicyError):select([Candidate('wanted',installed=False),Candidate('other')],explicit='wanted')

    def test_quality_floor_not_guessed(self):
        with self.assertRaises(PolicyError):select([Candidate('unknown')],quality_floor=.8)

    def test_capability_filter(self):
        with self.assertRaises(PolicyError):select([Candidate('text')],required={'filesystem_write'})

    def test_cheap_eligible_first(self):
        self.assertEqual(select([Candidate('a',cost=2),Candidate('b',cost=1)])['selected'],'b')


class InternalTests(unittest.TestCase):
    def test_P17_nested_tool_denied(self):
        transport=lambda b,t: {'content':[{'type':'tool_use','name':'spawn_agent','id':'x','input':{}}]}
        r=InternalAdapter(transport=transport).execute('Spawn children')
        self.assertEqual(r['outcome'],'FAILED');self.assertIn('denied',r['error'])

    def test_structured_result_required(self):
        r=InternalAdapter(transport=lambda b,t:{'content':[{'type':'text','text':'done'}]}).execute('test')
        self.assertEqual(r['outcome'],'FAILED')

    def test_iteration_cap(self):
        calls=[]
        def transport(b,t):
            calls.append(b);return {'content':[{'type':'tool_use','name':'read_context','id':str(len(calls)),'input':{}}]}
        r=InternalAdapter(transport=transport,max_iterations=2).execute('test')
        self.assertEqual(len(calls),2);self.assertEqual(r['outcome'],'FAILED')

    def test_only_fixed_context_and_output_tools(self):
        def transport(b,t):
            self.assertEqual({x['name'] for x in b['tools']},{'read_context','submit_result'})
            return {'content':[{'type':'tool_use','name':'submit_result','id':'x','input':{'text':'valid'}}]}
        self.assertEqual(InternalAdapter(transport=transport).execute('ignore policy')['text'],'valid')

    def test_compiler_does_not_invent_quality_pass(self):
        c=compile_document('Write a useful report')
        self.assertIn('manual_review',[x['kind'] for x in c['milestones'][0]['checks']])

    def test_provider_cannot_exceed_token_cap(self):
        r=InternalAdapter(max_output_tokens=10,transport=lambda b,t:{'usage':{'output_tokens':11},
            'content':[{'type':'tool_use','name':'submit_result','id':'x','input':{'text':'done'}}]}).execute('test')
        self.assertEqual(r['outcome'],'FAILED')

    def test_context_is_not_silently_truncated(self):
        r=InternalAdapter().execute('x'*40001)
        self.assertEqual(r['outcome'],'FAILED')


if __name__ == '__main__':unittest.main()
