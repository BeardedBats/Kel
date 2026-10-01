"""Bounded independent prose verdicts control publication; all models are fixtures."""
import contextlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from kel.core import PolicyError
from kel.native import NativeAdapter
from kel.service import Service
from kel.prose_review import AdmittedModel,executed
from kel.word_limits import parse
from kel.activity import timeline

GOOD='Notes preserve decisions and reasons.\n\nThey help someone resume after a break.'
BAD='In 2020, project notes helped teams remember decisions and the reasons behind them. After a break, anyone could return to those notes and pick up where the work had paused. The record kept each choice and its reason close at hand, so it was easier to continue with confidence. Together.'


class FakeNative(NativeAdapter):
    def __init__(self,provider='claude',model=None,answer=None,used=None,hook=None):
        self.provider=provider;self.model=model;self.timeout=999;self.calls=[]
        self.answer=answer or json.dumps({'verdict':'VERIFIED','findings':[]})
        self.used=used or ('claude-opus-5-5' if provider=='claude' else 'gpt-6-luna')
        self.hook=hook
    def execute(self,prompt,cancel=None,**kwargs):
        self.calls.append({'timeout':self.timeout,'prompt':prompt,'kwargs':kwargs})
        if self.hook:self.hook()
        return {'outcome':'SUCCESS','text':self.answer,'model_used':self.used,'usage':{'input_tokens':4,'output_tokens':8}}


class ProseReview(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.service=Service(self.tmp.name);self.service.engine.adapters={};self.addCleanup(self.service.shutdown)
        self.request='Write under 50 words in two paragraphs. Use only these facts: notes preserve decisions and reasons; notes help someone resume after a break.'
        with patch.object(self.service.requests,'submit'):self.sid=self.service.submit({'conversation':'main','text':self.request})
        self.limit=parse(self.request);self.cancel=threading.Event();self.service._cancels[self.sid]=self.cancel
        self.writer=FakeNative('codex','gpt-6-luna',answer=GOOD)
        self.service._kel_usage('reply',self.sid,'main',self.writer,{'outcome':'SUCCESS','model_used':'gpt-6-luna','usage':{'input_tokens':1,'output_tokens':12}},1)
        self.reviewer=FakeNative()
        self.choose=patch.object(self.service.commander,'_reviewer',return_value=self.reviewer);self.choose.start();self.addCleanup(self.choose.stop)

    def posts(self):
        with contextlib.closing(self.service.store.connect()) as db:
            return [row['text'] for row in db.execute("SELECT text FROM messages WHERE role='assistant'")]

    def receipt(self):
        with contextlib.closing(self.service.store.connect()) as db:return dict(db.execute('SELECT * FROM prose_reviews WHERE submission_id=?',(self.sid,)).fetchone())

    def test_valid_candidate_same_bytes_actual_default_model_and_usage(self):
        self.assertTrue(self.service._say(self.sid,'main',GOOD,word_limit=self.limit))
        self.assertEqual(self.posts(),[GOOD]);self.assertEqual(len(self.reviewer.calls),1)
        self.assertLessEqual(self.reviewer.calls[0]['timeout'],30);self.assertEqual(self.reviewer.timeout,999)
        record=self.receipt();self.assertEqual(record['verdict'],'VERIFIED')
        self.assertEqual(json.loads(record['reviewer'])['model_used'],'claude-opus-5-5')
        self.assertEqual(json.loads(record['reviewer'])['factual_basis'],'request-only')
        payload=json.loads(self.reviewer.calls[0]['prompt'].split('\n',1)[1])
        self.assertNotIn('source_context',payload)
        self.assertIn('unseen history',self.reviewer.calls[0]['prompt'])
        with contextlib.closing(self.service.store.connect()) as db:
            data=json.loads(db.execute('SELECT data FROM provider_usage ORDER BY seq DESC LIMIT 1').fetchone()[0])
        self.assertEqual(data['role'],'verifier');self.assertEqual(data['raw_model'],'claude-opus-5-5')
        self.assertEqual(len(self.service.context.request_calls(self.sid)),1)
        self.assertTrue(any(row['what']=='The independent model accepted this prose reply.' for row in timeline(self.service.store,project_id='default')['entries']))

    def test_recorded_punctuated_fragment_is_withheld_no_repair(self):
        self.reviewer.answer=json.dumps({'verdict':'FAILED','findings':['Standalone Together. is filler; teams and confidence are unsupported.']})
        request='Write exactly 50 words in one paragraph. Use only these facts: notes preserve decisions and reasons; notes help someone resume after a break.'
        with self.service.store.transaction() as db:db.execute('UPDATE submissions SET text=? WHERE id=?',(request,self.sid))
        limit=parse(request)
        self.assertEqual(len(BAD.split()),50)
        with self.assertRaisesRegex(PolicyError,'did not accept'):self.service._say(self.sid,'main',BAD,word_limit=limit)
        self.assertEqual(self.posts(),[]);self.assertEqual(len(self.reviewer.calls),1)
        with self.assertRaisesRegex(PolicyError,'already used'):self.service._say(self.sid,'main',BAD,word_limit=limit)
        self.assertEqual(len(self.reviewer.calls),1);self.assertEqual(self.receipt()['verdict'],'FAILED')

    def test_uncertain_malformed_duplicate_and_unknown_actual_model_withhold(self):
        for answer,used in [(json.dumps({'verdict':'UNCERTAIN','findings':['Cannot establish source fidelity.']}),'claude-opus-5-5'),
                            ('{"verdict":"VERIFIED","verdict":"FAILED","findings":[]}','claude-opus-5-5'),
                            ('{"verdict":"VERIFIED","findings":[],"extra":true}','claude-opus-5-5'),
                            ('not JSON','claude-opus-5-5'),
                            (json.dumps({'verdict':'VERIFIED','findings':[]}),'gpt-6-luna'),
                            (json.dumps({'verdict':'VERIFIED','findings':[]}),'unknown-model')]:
            with self.subTest(answer=answer,used=used):
                # Each case has its own submitted request, never a repeated provider allowance.
                with patch.object(self.service.requests,'submit'):sid=self.service.submit({'conversation':'main','text':self.request})
                self.service._kel_usage('reply',sid,'main',self.writer,{'outcome':'SUCCESS','model_used':'gpt-6-luna'},1)
                reviewer=FakeNative(answer=answer,used=used)
                with patch.object(self.service.commander,'_reviewer',return_value=reviewer):
                    with self.assertRaises(PolicyError):self.service._say(sid,'main',GOOD,word_limit=self.limit)
                self.assertEqual(len(reviewer.calls),1);self.assertEqual(self.posts(),[])

    def test_same_family_unavailable_or_api_never_execute(self):
        for reviewer in (None,FakeNative('codex','gpt-6-astra'),object()):
            with self.subTest(reviewer=reviewer):
                with patch.object(self.service.requests,'submit'):sid=self.service.submit({'conversation':'main','text':self.request})
                self.service._kel_usage('reply',sid,'main',self.writer,{'outcome':'SUCCESS','model_used':'gpt-6-luna'},1)
                with patch.object(self.service.commander,'_reviewer',return_value=reviewer):
                    with self.assertRaisesRegex(PolicyError,'unavailable'):self.service._say(sid,'main',GOOD,word_limit=self.limit)
                if isinstance(reviewer,FakeNative):self.assertEqual(reviewer.calls,[])
        self.assertEqual(self.posts(),[])

    def test_stop_after_admission_and_late_success_cannot_publish(self):
        admit=self.service._admit_planning_call
        def stop(*args,**kwargs):
            call=admit(*args,**kwargs);self.cancel.set();return call
        with patch.object(self.service,'_admit_planning_call',side_effect=stop):
            with self.assertRaisesRegex(PolicyError,'stopped'):self.service._say(self.sid,'main',GOOD,word_limit=self.limit)
        self.assertEqual(self.reviewer.calls,[])
        calls=self.service.context.request_calls(self.sid)
        self.assertEqual(calls[0]['usage']['execution_state'],'not_started')
        self.assertEqual(self.posts(),[])

    def test_stale_request_and_changed_final_bytes_fail_after_review(self):
        def change():
            with self.service.store.transaction() as db:db.execute('UPDATE submissions SET text=? WHERE id=?',('Changed request.',self.sid))
        self.reviewer.hook=change
        with self.assertRaisesRegex(PolicyError,'request changed'):self.service._say(self.sid,'main',GOOD,word_limit=self.limit)
        self.assertEqual(self.posts(),[])

    def test_late_stop_and_context_change_cannot_publish(self):
        self.reviewer.hook=self.cancel.set
        with self.assertRaisesRegex(PolicyError,'stopped'):self.service._say(self.sid,'main',GOOD,word_limit=self.limit)
        self.assertEqual(self.posts(),[])
        self.assertEqual(json.loads(self.receipt()['reviewer'])['model_used'],'claude-opus-5-5')
        with patch.object(self.service.requests,'submit'):sid=self.service.submit({'conversation':'main','text':self.request})
        self.service._kel_usage('reply',sid,'main',self.writer,{'outcome':'SUCCESS','model_used':'gpt-6-luna'},1)
        def change():
            with self.service.store.transaction() as db:
                packet=json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?',(sid,)).fetchone()[0]);packet['history']=[{'role':'user','text':'Changed reference.'}]
                db.execute('UPDATE submission_packets SET packet=? WHERE id=?',(json.dumps(packet),sid))
        reviewer=FakeNative(hook=change)
        with patch.object(self.service.commander,'_reviewer',return_value=reviewer):
            with self.assertRaisesRegex(PolicyError,'request changed'):self.service._say(sid,'main',GOOD,word_limit=self.limit)
        self.assertEqual(self.posts(),[])

    def test_final_choice_bytes_are_reviewed_and_rechecked(self):
        first=GOOD;changed='Notes preserve choices and reasons.\n\nThey help someone resume after a break.'
        with patch.object(self.service,'_with_choice',side_effect=[(first,None),(changed,None)]):
            with self.assertRaisesRegex(PolicyError,'changed after'):self.service._say(self.sid,'main',GOOD,word_limit=self.limit)
        packet=json.loads(self.reviewer.calls[0]['prompt'].split('\n',1)[1])
        self.assertEqual(packet['candidate'],first);self.assertEqual(self.posts(),[])

    def test_internal_default_does_not_mask_native_alternative(self):
        from kel.internal import InternalAdapter
        self.choose.stop()
        internal=object.__new__(InternalAdapter);internal.provider='internal';internal.model='claude-sonnet-4-6'
        self.service.commander.model=internal;self.service.commander.alternates=[self.reviewer]
        self.assertTrue(self.service._say(self.sid,'main',GOOD,word_limit=self.limit))
        self.assertEqual(len(self.reviewer.calls),1);self.assertEqual(self.reviewer.calls[0]['timeout'],30)
        self.assertIs(self.service.commander.model,internal)

    def test_three_calls_durable_usage_dedup_and_isolated_initial_timeout(self):
        with patch.object(self.service.requests,'submit'):sid=self.service.submit({'conversation':'main','text':self.request})
        adapter=FakeNative('codex','gpt-6-luna',answer=GOOD)
        proxy=AdmittedModel(self.service,sid,adapter,threading.Event(),kind='turn')
        self.assertEqual(proxy.model,'gpt-6-luna');self.assertEqual(proxy.provider,'codex')
        for _ in range(3):
            result=proxy.execute('write')
            self.service._kel_usage('turn',sid,'main',adapter,result,1)
        self.assertEqual(executed(self.service,sid),3)
        with contextlib.closing(self.service.store.connect()) as db:
            data=json.loads(db.execute("SELECT data FROM provider_usage WHERE json_extract(data,'$.submission_id')=? ORDER BY seq DESC LIMIT 1",(sid,)).fetchone()[0])
        self.assertEqual(data['kind'],'turn')
        self.assertEqual(adapter.timeout,999)
        with self.assertRaisesRegex(PolicyError,'three-call'):proxy.execute('fourth')
        self.assertEqual(len(adapter.calls),3)
        with self.assertRaisesRegex(PolicyError,'three-call'):self.service._say(sid,'main',GOOD,word_limit=self.limit)
        self.assertEqual(self.reviewer.calls,[])

    def test_elapsed_deadline_and_ordinary_reply_scope(self):
        with self.service.store.transaction() as db:db.execute('UPDATE submissions SET created=created-121 WHERE id=?',(self.sid,))
        with self.assertRaisesRegex(PolicyError,'time limit'):self.service._say(self.sid,'main',GOOD,word_limit=self.limit)
        self.assertEqual(self.reviewer.calls,[])
        self.assertTrue(self.service._say(self.sid,'main','Ordinary factual answer.'))

    def test_live_plan_path_accounts_generation_and_review_once(self):
        with patch.object(self.service.requests,'submit'):sid=self.service.submit({'conversation':'main','text':self.request})
        with contextlib.closing(self.service.store.connect()) as db:packet=json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?',(sid,)).fetchone()[0])
        with patch.object(self.service,'_turn_choice',return_value=(None,None)),patch.object(self.service,'_chat_choice',return_value=(self.writer,None)):
            self.service._plan(sid,'main',self.request,packet,'chat')
        self.assertEqual(self.posts(),[GOOD]);self.assertEqual(len(self.writer.calls),1);self.assertEqual(len(self.reviewer.calls),1)
        self.assertEqual(executed(self.service,sid),2)
