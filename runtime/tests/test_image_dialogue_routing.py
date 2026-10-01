"""Image correction routing uses local request receipts, never imported dialogue."""
import contextlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from kel.core import Store, PolicyError, encode
from kel.router import classify, image_generation_intent
from kel.service import Service


class ImageDialogueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.service=Service.__new__(Service)
        self.store=self.service.store=Store(Path(self.tmp.name)/'engine')
        self.service._cancels={};self.service._cancels_lock=threading.RLock()
        self.service.drafts={};self.service.wake=threading.Event()
        self.service.lifecycle_lock=threading.RLock();self.service.draining=False
        self.service.requests=Mock();self.service.planning=Mock()
        with self.store.transaction() as db:
            db.execute('CREATE TABLE submissions(id TEXT PRIMARY KEY,conversation_id TEXT,text TEXT,state TEXT,error TEXT,job_id TEXT,created REAL)')
            db.execute('CREATE TABLE submission_packets(id TEXT PRIMARY KEY,packet TEXT,kind TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS project_tests(project_id TEXT PRIMARY KEY,command TEXT)')
            db.execute('CREATE TABLE request_calls(submission_id TEXT)')
            db.execute('CREATE TABLE submission_acks(submission_id TEXT PRIMARY KEY)')

    def record(self,sid,text,kind='document',cid='main',packet=None,jid=None):
        with self.store.transaction() as db:
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',(sid,cid,text,'PLANNING',None,jid,1))
            db.execute('INSERT INTO submission_packets VALUES(?,?,?)',(sid,encode(packet or {}),kind))

    def test_initial_visual_is_image_before_app_floor(self):
        for text in ('Create an infographic about this app','Generate an image about Kel',
                     'Please draw a picture of a desk','Make an infographic showing how this app works',
                     'Create a generated infographic image titled How Kel Works'):
            with self.subTest(text=text):self.assertEqual(classify(text)['kind'],'image')

    def test_prompt_analysis_and_imported_examples_are_not_image_output(self):
        for text in ('Create an image prompt about Kel','Generate an image generation tool',
                     'Write a prompt to generate an infographic','Analyze this image',
                     '> Create an infographic about Kel','```\nGenerate an image\n```',
                     '"Create an infographic about Kel"','Fix image_generation.py'):
            with self.subTest(text=text):self.assertFalse(image_generation_intent(text))

    def test_exact_correction_dialogue_keeps_original_request(self):
        original='Create an infographic about Kel and its architecture'
        self.record('original',original)
        for sid,text in enumerate(('No, this should be an image generated','Where is the image','Fix this')):
            follow=self.service._image_followup('main',text)
            self.assertEqual(follow['request'],original)
            self.assertEqual(follow['mode'],'status' if sid==1 else 'generate')
            self.record(str(sid),text,'image',packet={'image_request':follow})

    def test_other_chat_and_intervening_code_do_not_inherit(self):
        self.record('image','Generate an image about Kel','image',cid='other')
        self.assertIsNone(self.service._image_followup('main','Fix this'))
        self.record('own','Generate an image about Kel','image')
        self.record('code','Fix parser.py','coding')
        self.assertIsNone(self.service._image_followup('main','Fix this'))

    def test_initial_image_lane_never_calls_scoping_or_turn_model(self):
        text='Create an infographic about this app'
        self.record('image',text,'image')
        packet={'project':{'root':str(Path(self.tmp.name))},'files':[]}
        self.service._handoff=Mock(return_value='started')
        with patch('kel.scoping.typed_answers',side_effect=AssertionError('coding scoping')), \
             patch('kel.service.decide_turn',side_effect=AssertionError('model call')):
            self.assertEqual(self.service._plan('image','main',text,packet,'image'),'started')
        args=self.service._handoff.call_args.args
        self.assertEqual(args[4],'image')
        self.assertEqual(packet['output_contract'],{'kind':'image'})
        self.assertNotIn('started',args[6]['acknowledgement'])

    def test_correction_rewrites_work_but_not_typed_message(self):
        original='Create an infographic about Kel'
        self.record('fix','Fix this','image')
        packet={'image_request':{'mode':'generate','request':original},'files':[]}
        self.service._handoff=Mock()
        self.service._plan('fix','main','Fix this',packet,'image')
        self.assertEqual(self.service._handoff.call_args.args[2],original)
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT text FROM submissions WHERE id=?',('fix',)).fetchone()[0],original)

    def test_status_settles_without_dispatch(self):
        self.record('status','Where is the image','image')
        packet={'image_request':{'mode':'status','job_id':None},'files':[]}
        self.service._say=Mock();self.service._handoff=Mock()
        self.service._plan('status','main','Where is the image',packet,'image')
        self.service._handoff.assert_not_called()
        self.assertIn('No generated image',self.service._say.call_args.args[2])
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT state FROM submissions WHERE id=?',('status',)).fetchone()[0],'SETTLED')

    def test_image_compilation_does_not_enter_coding_gate(self):
        self.record('image','Fix this','image')
        packet={'project':{'root':str(Path(self.tmp.name))},'files':[]}
        with patch('kel.service.compile_coding',side_effect=AssertionError('coding compiler')), \
             patch.object(self.service,'_document_contract',side_effect=AssertionError('document compiler')):
            contract=self.service._compile_work('image','main','Fix this',packet,'image',False)
        self.assertEqual(contract['output_contract'],{'kind':'image'})
        self.assertEqual(contract['required_capabilities'],['image_generation'])
        self.assertEqual(contract['milestones'][0]['filename'],'image.png')

    def test_closed_text_job_does_not_claim_image_available(self):
        with patch.object(self.store,'get',return_value={'state':'CLOSED','contract':{'final_milestone':'image'}}), \
             patch('kel.image_jobs.image_artifact',side_effect=PolicyError('missing receipt')):
            result=self.service._image_status({'job_id':'old-text-job'})
        self.assertIn('No verified generated image',result)

    def test_real_coding_still_requires_project_test_command(self):
        self.record('code','Fix parser.py','coding')
        packet={'project':{'root':str(Path(self.tmp.name)),'id':'existing'},'files':[]}
        self.service.commander=None
        with patch('kel.projects.ensure_folder'), \
             patch('kel.service.compile_coding') as compiler:
            with self.assertRaisesRegex(PolicyError,'This project needs a test command'):
                self.service._compile_work('code','main','Fix parser.py',packet,'coding',False)
        compiler.assert_not_called()

    def test_image_staffing_does_not_assign_text_writer(self):
        with patch('kel.staff.plan_job',side_effect=AssertionError('text staffing')):
            self.assertIsNone(self.service._staff_contract({'output_contract':{'kind':'image'}},'Generate an image'))

    def test_infographic_component_is_coding_and_keeps_test_command_gate(self):
        text='Create an infographic component in React'
        generated='Create a generated infographic component in React'
        self.assertFalse(image_generation_intent(generated))
        self.assertEqual(classify(generated)['kind'],'coding')
        self.assertFalse(image_generation_intent(text))
        self.assertEqual(classify(text)['kind'],'coding')
        self.record('component',text,'coding')
        packet={'project':{'root':str(Path(self.tmp.name)),'id':'existing'},'files':[]}
        with patch('kel.projects.ensure_folder'),patch('kel.image_jobs.compile_image') as image:
            with self.assertRaisesRegex(PolicyError,'This project needs a test command'):
                self.service._compile_work('component','main',text,packet,classify(text)['kind'],False)
        image.assert_not_called()

    def legacy_chain(self):
        original='Make me an infographic showing how kel works to my staff'
        self.record('original',original,'conversation',packet={'kind_source':'router'},jid='image-job')
        self.record('status-old','Where is the image?','conversation',packet={'kind_source':'router'})
        self.record('fix-old','Fix this.','conversation',packet={'kind_source':'router'})
        self.record('fix-current','Fix this.','conversation',packet={'kind_source':'router','classification':{'task_class':'coding'}})
        with self.store.transaction() as db:
            db.execute("UPDATE submissions SET state='SETTLED' WHERE id='status-old'")
            db.execute("UPDATE submissions SET state='FAILED',error='This project needs a test command.' WHERE id IN ('fix-old','fix-current')")
        return original

    def test_legacy_failed_short_corrections_and_status_do_not_block_image_reference(self):
        original=self.legacy_chain()
        self.assertEqual(self.service._image_followup('main','Fix this.')['request'],original)
        self.assertEqual(self.service._image_followup('main','Where is the image?')['job_id'],'image-job')

    def test_retry_rebinds_legacy_receipt_before_self_and_future_with_no_model_call(self):
        for acked in (False,True):
            with self.subTest(acked=acked):
                # A separate conversation gives each retry its own original receipt.
                cid='retry-'+str(acked)
                original='Generate an infographic about the original facts'
                target='fix-'+str(acked)
                self.record('image-'+str(acked),original,'conversation',cid,{'kind_source':'router'})
                self.record(target,'Fix this.','conversation',cid,{'kind_source':'router','classification':{'task_class':'coding'}})
                self.record('future-'+str(acked),'Generate an image about unrelated future facts','image',cid)
                with self.store.transaction() as db:
                    db.execute("UPDATE submissions SET state='FAILED' WHERE id=?",(target,))
                    if acked:db.execute('INSERT INTO submission_acks VALUES(?)',(target,))
                self.service.action('/api/retry',{'id':target})
                executor=self.service.planning if acked else self.service.requests
                args=executor.submit.call_args.args
                self.assertEqual(args[5],'image')
                self.assertEqual(args[4]['image_request']['request'],original)
                self.assertEqual(args[3],original if acked else 'Fix this.')
                with contextlib.closing(self.store.connect()) as db:
                    row=db.execute('SELECT packet,kind FROM submission_packets WHERE id=?',(target,)).fetchone()
                    self.assertEqual(row['kind'],'image')
                    self.assertEqual(json.loads(row['packet'])['classification']['task_class'],'image')

    def test_legacy_skipping_stops_at_substantive_or_explicit_client_coding(self):
        for sid,text,kind,packet in (
                ('substantive','Fix parser.py','conversation',{'kind_source':'router'}),
                ('explicit','Fix this.','coding',{'kind_source':'client'})):
            with self.subTest(sid=sid):
                cid=sid
                self.record('image-'+sid,'Generate an image about Kel','image',cid)
                self.record(sid,text,kind,cid,packet)
                with self.store.transaction() as db:
                    db.execute("UPDATE submissions SET state='FAILED' WHERE id=?",(sid,))
                self.assertIsNone(self.service._image_followup(cid,'Fix this.'))
                self.service.action('/api/retry',{'id':sid})
                self.assertEqual(self.service.requests.submit.call_args.args[5],kind)
