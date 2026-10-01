"""Owned image bytes reach one tool-disabled Codex invocation; no providers."""
import base64
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from kel.context import Context
from kel.core import Store, PolicyError, digest
from kel.native import NativeAdapter, _input_session, _stage_image_inputs
from kel.service import Service
from kel.word_limits import parse

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j7l8AAAAASUVORK5CYII=')

def payload(raw=PNG):
    return {'mime':'image/png','data':base64.b64encode(raw).decode(),'sha256':digest(raw)}


class ImageCustody(unittest.TestCase):
    def test_conversation_packet_membership_type_and_digest_are_rechecked(self):
        with tempfile.TemporaryDirectory() as root:
            context=Context(Store(root));aid=context.attach('main','pixel.png',PNG)
            packet=context.handoff('main','Describe.',[aid])
            self.assertEqual(context.images(packet,'main'),[payload()])
            other=context.conversation()
            with self.assertRaisesRegex(PolicyError,'conversation'):context.images(packet,other)
            packet['files'][0]['mime']='image/jpeg'
            with self.assertRaisesRegex(PolicyError,'type changed'):context.images(packet,'main')
            packet['files'][0]['mime']='image/png'
            (context.store.root/packet['files'][0]['image_path']).write_bytes(PNG+b'changed')
            with self.assertRaisesRegex(PolicyError,'bytes changed'):context.images(packet,'main')

    def test_linked_selected_file_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            context=Context(Store(root));aid=context.attach('main','pixel.png',PNG)
            packet=context.handoff('main','Describe.',[aid]);path=context.store.root/packet['files'][0]['image_path']
            os.link(path,Path(root)/'linked-image')
            with self.assertRaisesRegex(PolicyError,'linked'):context.images(packet,'main')
            with self.assertRaisesRegex(PolicyError,'linked'):context.handoff('main','Describe.',[aid])

    def test_plain_path_outside_attachment_root_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            context=Context(Store(root));aid=context.attach('main','pixel.png',PNG)
            outside=Path(root)/'plain-outside';outside.write_bytes(PNG)
            with context.store.transaction() as db:
                db.execute('UPDATE attachments SET path=? WHERE id=?',('plain-outside',aid))
            with self.assertRaisesRegex(PolicyError,'escaped storage'):context.handoff('main','Describe.',[aid])

    def test_bad_second_input_cannot_silently_drop_from_request(self):
        with tempfile.TemporaryDirectory() as root:
            session=_input_session(root,'input')
            bad=payload();bad['sha256']='0'*64
            with self.assertRaises(Exception):_stage_image_inputs(session,[payload(),bad])
            self.assertEqual(list(session.iterdir()),[])


class ImageTransport(unittest.TestCase):
    def test_images_keep_configured_native_role_when_internal_worker_exists(self):
        from kel.internal import InternalAdapter
        service=Service.__new__(Service)
        service.model=object.__new__(InternalAdapter)
        native=object.__new__(NativeAdapter);native.provider='codex'
        binding={'adapter':'codex','model':'configured-native'}
        with patch('kel.staff.enabled',return_value=True),patch('kel.role_models.resolve',return_value=binding),\
                patch.object(service,'staff_adapters',return_value={}),patch.object(service,'staff_model',return_value=native):
            service.store=object()
            self.assertIs(service._model_for(None,True,images=True),native)
            self.assertEqual(native.kel_binding,binding)

    def test_buffered_exec_uses_fixed_owned_leaves_and_retains_usage(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);adapter=NativeAdapter('codex',base/'work',base/'logs',model='selected')
            seen=[]
            def start(argv,**kwargs):
                seen.append(argv)
                positions=[i for i,arg in enumerate(argv) if arg=='--image']
                self.assertEqual(len(positions),2)
                for i in positions:
                    path=Path(argv[i+1]);self.assertTrue(path.is_relative_to(base/'sessions'))
                    self.assertEqual(path.read_bytes(),PNG)
                records=[{'type':'item.completed','item':{'type':'agent_message','text':'Visible text.'}},
                         {'type':'turn.completed','usage':{'input_tokens':9,'output_tokens':3}}]
                kwargs['stdout'].write(('\n'.join(json.dumps(r) for r in records)+'\n').encode());kwargs['stdout'].flush()
                class Process:
                    pid=123;stdin=io.BytesIO();returncode=0
                    def poll(self):return self.returncode
                    def wait(self,timeout=None):return self.returncode
                    def kill(self):self.returncode=-1
                return Process()
            with patch('kel.native.executable',return_value=['codex.exe']),patch('kel.native.subprocess.Popen',side_effect=start),patch('kel.native.runtime_version',return_value='fixture'),patch.object(adapter,'_codex_stream') as streaming:
                result=adapter.execute('Describe images.',images=[payload(),payload()],on_text=lambda text:self.fail('Image output must remain buffered'))
            streaming.assert_not_called()
            self.assertEqual(result['outcome'],'SUCCESS');self.assertEqual(result['model_used'],'selected')
            self.assertEqual(result['usage']['input_tokens'],9)
            self.assertEqual(result['image_inputs'],{'count':2,'buffered':True})
            self.assertEqual(len(seen),1);self.assertIn('shell_tool',seen[0])
            self.assertFalse(any((base/'sessions').iterdir()))

    def test_unsupported_or_corrupt_images_fail_before_process(self):
        with tempfile.TemporaryDirectory() as root,patch('kel.native.subprocess.Popen') as process:
            for provider,images in [('claude',[payload()]),('codex',[]),('codex',[payload(b'not PNG')])]:
                adapter=NativeAdapter(provider,Path(root)/'work',Path(root)/'logs')
                self.assertEqual(adapter.execute('Describe.',images=images)['outcome'],'FAILED')
            process.assert_not_called()

    def test_same_verified_images_survive_the_single_correction(self):
        with tempfile.TemporaryDirectory() as root:
            service=Service(root);service.engine.adapters={}
            try:
                request='Write exactly 2 words about the image.'
                with patch.object(service.requests,'submit'):sid=service.submit({'conversation':'main','text':request})
                class Model(NativeAdapter):
                    def __init__(self):self.provider='codex';self.model='image-fixture';self.calls=[]
                    def execute(self,prompt,cancel=None,output_schema=None,images=None):
                        self.calls.append((images,output_schema))
                        return {'outcome':'SUCCESS','text':'{"words":[{"index":1,"word":"Visible"},{"index":2,"word":"text."}]}','usage':{'input_tokens':2,'output_tokens':2}}
                model=Model()
                answer,_=service._checked_word_reply(sid,'main',request,'An overlong initial image description.',parse(request),model,threading.Event(),[],images=[payload()])
                self.assertEqual(answer,'Visible text.')
                self.assertEqual(model.calls[0][0],[payload()]);self.assertIsNotNone(model.calls[0][1])
                self.assertEqual(len(model.calls),1)
                unsupported=NativeAdapter('claude',Path(root)/'work',Path(root)/'logs')
                with patch.object(unsupported,'execute') as execute:
                    with self.assertRaisesRegex(PolicyError,'does not support'):
                        service._checked_word_reply(sid,'main',request,'Too many words.',parse(request),unsupported,threading.Event(),[],images=[payload()])
                    execute.assert_not_called()
            finally:service.shutdown()
