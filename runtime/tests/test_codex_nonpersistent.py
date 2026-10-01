"""Kel-owned native sessions stay out of persisted Codex history; no model calls."""
import copy
import io
import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from kel.native import NativeAdapter, require_ephemeral_codex, local_session_id
from kel.appserver import CodexConnection
from kel.host_runtime import HostConnection
from kel.engine import Engine


class NonpersistentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)

    def connection(self,reply,provider='codex'):
        connection=CodexConnection.__new__(CodexConnection)
        connection.provider=provider;connection.pending={};connection.lock=threading.Lock();connection.next_id=0
        connection._private_codex_command=['codex.exe'];connection.frames=[]
        def send(frame):
            connection.frames.append(frame)
            connection.pending[frame['id']].put({'id':frame['id'],'result':reply})
        connection.send=send
        return connection

    def test_exec_variants_request_nonpersistence_and_refuse_remote_resume(self):
        for web,stream in ((False,False),(False,True),(True,False)):
            adapter=NativeAdapter('codex',self.base/'work',self.base/'logs',web=web)
            with patch('kel.native.executable',return_value=['codex.exe']):
                argv=adapter.argv(stream=stream)
                self.assertEqual(argv.count('--ephemeral'),1)
                self.assertNotIn('resume',argv)
                self.assertIn('--ignore-user-config',argv)
                with self.assertRaisesRegex(RuntimeError,'cannot resume'):adapter.argv('old-private-id')

    def test_actual_buffered_schema_and_image_launch_arguments_keep_ephemeral(self):
        from test_native_image_inputs import payload
        for name,kwargs in [('ordinary',{}),('schema',{'output_schema':{'type':'object'}}),('image',{'images':[payload()]})]:
            adapter=NativeAdapter('codex',self.base/('work-'+name),self.base/('logs-'+name))
            captured=[]
            def capture(argv,**unused):
                captured.append(argv);raise RuntimeError('Controlled launch stopped before provider execution')
            with patch('kel.native.executable',return_value=['codex.exe']),patch('kel.native.subprocess.Popen',side_effect=capture):
                result=adapter.execute('Current supplied context.',**kwargs)
            self.assertEqual(result['outcome'],'FAILED')
            self.assertEqual(len(captured),1)
            self.assertIn('--ephemeral',captured[0])
            if name=='schema':self.assertIn('--output-schema',captured[0])
            if name=='image':self.assertIn('--image',captured[0])

    def test_appserver_forces_ephemeral_and_requires_exact_confirmation(self):
        for flag in (True,False,None,'true'):
            connection=self.connection({'thread':{'id':'new','ephemeral':flag}})
            with patch('kel.native.version_of',return_value='codex-cli 0.159.2'):
                if flag is True:connection.call('thread/start',{'ephemeral':False,'cwd':'owned'})
                else:
                    with self.assertRaisesRegex(RuntimeError,'No Kel prompt was sent'):connection.call('thread/start',{})
            self.assertEqual(connection.frames[0]['params']['ephemeral'],True)
            self.assertEqual([f['method'] for f in connection.frames],['thread/start'])

    def test_unsupported_runtime_stops_before_thread_creation(self):
        for version in (None,'codex-cli 0.158.0','codex-cli 0.159.2-alpha.1','WSL version: 2.6.1'):
            connection=self.connection({'thread':{'id':'new','ephemeral':True}})
            with patch('kel.native.version_of',return_value=version),self.assertRaisesRegex(RuntimeError,'cannot confirm'):
                connection.call('thread/start',{})
            self.assertEqual(connection.frames,[])

    def test_remote_resume_refuses_before_any_dispatch(self):
        connection=self.connection({'thread':{'id':'old','ephemeral':False}})
        with self.assertRaisesRegex(RuntimeError,'cannot resume'):connection.call('thread/resume',{'threadId':'old'})
        with self.assertRaisesRegex(RuntimeError,'cannot resume'):connection.run('Continue.',session_id='old')
        adapter=NativeAdapter('codex',self.base/'work',self.base/'logs')
        with patch('kel.native.subprocess.Popen') as launch:
            self.assertEqual(adapter.execute('Continue.',session_id='old')['outcome'],'FAILED')
        launch.assert_not_called();self.assertEqual(connection.frames,[])

    def test_custom_claude_transport_keeps_existing_contract(self):
        connection=self.connection({'thread':{'id':'claude'}} ,provider='claude')
        with patch('kel.appserver.require_ephemeral_codex') as gate:
            connection.call('thread/resume',{'threadId':'claude'})
        gate.assert_not_called()
        self.assertEqual(connection.frames[0]['method'],'thread/resume')
        self.assertNotIn('ephemeral',connection.frames[0]['params'])

    def test_host_thread_wrapper_requests_ephemeral_without_changing_claude(self):
        for provider in ('codex','claude'):
            host=HostConnection.__new__(HostConnection);host.provider=provider;host._memory=lambda:self.base
            with patch.object(CodexConnection,'call',return_value={'thread':{'id':'t','ephemeral':True}}) as wire:
                host.call('thread/start',{'cwd':str(self.base)})
            params=wire.call_args.args[1]
            self.assertEqual(params.get('ephemeral'),True if provider=='codex' else None)

    def test_stream_requests_private_thread_and_blocks_missing_ack_before_turn(self):
        for acknowledged in (True,False):
            class Stream:
                def __init__(self):
                    self.calls=[];self.events=queue.Queue();self.closed=False
                    self.events.put({'method':'item/completed','params':{'item':{'id':'a','type':'agentMessage','text':'Answer.'}}})
                    self.events.put({'method':'turn/completed','params':{'turn':{'status':'completed'}}})
                def call(self,method,params,**unused):
                    self.calls.append((method,params))
                    return {'thread':{'id':'new','ephemeral':acknowledged}} if method=='thread/start' else {'turn':{'id':'turn'}}
                def close(self):self.closed=True
            stream=Stream();adapter=NativeAdapter('codex',self.base/'work',self.base/'logs')
            with patch('kel.native.require_ephemeral_codex'):
                result=adapter._codex_stream('Current context.','run',None,None,lambda text:None,lambda unused:stream)
            self.assertEqual(stream.calls[0][1]['ephemeral'],True)
            self.assertTrue(stream.closed)
            self.assertEqual(result['outcome'],'SUCCESS' if acknowledged else 'FAILED')
            self.assertEqual(any(method=='turn/start' for method,_ in stream.calls),acknowledged)

    def test_worker_restart_replays_local_contract_and_keeps_old_receipt_local(self):
        job={'contract':{'request':'Write from the supplied facts.','context':{'history':[{'role':'user','text':'Local chat fact.'}]}},'milestones':{}}
        before=copy.deepcopy(job)
        store=Mock();store.get.return_value=job
        database=Mock();database.execute.return_value.fetchone.return_value={'native_session':'old-private-id'}
        store.connect.return_value=database
        engine=Engine.__new__(Engine);engine.store=store
        adapter=Mock();adapter.execute.return_value={'outcome':'SUCCESS','text':'Answer.'}
        run={'id':'run','job_id':'job','milestone_id':'document','provider':'codex','attempt':1,'epoch':1,
             'spec':{'id':'document','objective':'Write from supplied facts.','checks':[]}}
        with patch('kel.packs.worker_brief',return_value=''),patch('kel.staff.step_role',return_value='writer'):
            engine._execute(run,adapter,threading.Event())
        self.assertIsNone(adapter.execute.call_args.kwargs['session_id'])
        self.assertIn('Local chat fact.',adapter.execute.call_args.args[0])
        self.assertIn('Write from supplied facts.',adapter.execute.call_args.args[0])
        self.assertEqual(job,before)
        self.assertEqual(database.execute.return_value.fetchone.return_value['native_session'],'old-private-id')

    def test_internal_codex_variants_use_local_replay_other_providers_keep_resume(self):
        for provider in ('codex','codex-code','codex-web'):self.assertIsNone(local_session_id(provider,'receipt'))
        for provider in ('claude','claude-code','claude-web','internal'):self.assertEqual(local_session_id(provider,'receipt'),'receipt')


if __name__=='__main__':unittest.main()
