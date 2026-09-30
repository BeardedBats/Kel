"""Internal schema transport without providers or changes to prior expectations."""
import io
import contextlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from kel.native import NativeAdapter, _schema_final, _schema_session
from kel.word_limits import correction_schema, decode_correction, parse
from kel.service import Service


class SchemaTests(unittest.TestCase):
    def test_trusted_exact_and_exclusive_maximum_bounds(self):
        exact = correction_schema(parse('Write exactly 50 words.'))['properties']['words']
        maximum = correction_schema(parse('Write under 50 words.'))['properties']['words']
        self.assertEqual((exact['minItems'],exact['maxItems']),(50,50))
        self.assertEqual((maximum['minItems'],maximum['maxItems']),(1,49))
        self.assertFalse(exact['items']['additionalProperties'])
        for bounds in ({'minimum':True,'maximum':2},{'minimum':0,'maximum':2},{'minimum':1,'maximum':1001}):
            with self.assertRaises(Exception):correction_schema(bounds)

    def run_fake(self, final=b'{"words":[{"index":1,"word":"Hello"},{"index":2,"word":"there."}]}',
                 completed=True, code=0, cancel=False, resume=None):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root); adapter=NativeAdapter('codex',base/'work',base/'logs',model='chosen')
            seen=[]
            def start(argv,**kwargs):
                seen.append(argv)
                target=Path(argv[argv.index('--output-last-message')+1])
                if final is not None:target.write_bytes(final)
                records=[{'type':'item.completed','item':{'type':'agent_message','text':'intermediate prose must not win'}}]
                if completed:records.append({'type':'turn.completed','usage':{'input_tokens':7,'output_tokens':3}})
                kwargs['stdout'].write(('\n'.join(json.dumps(r) for r in records)+'\n').encode());kwargs['stdout'].flush()
                class Process:
                    pid=123;stdin=io.BytesIO();returncode=code
                    def poll(self):return None if cancel and self.returncode==code else self.returncode
                    def kill(self):self.returncode=-1
                    def wait(self,timeout=None):return self.returncode
                return Process()
            event=threading.Event()
            if cancel:event.set()
            with patch('kel.native.executable',return_value=['codex.exe']),patch('kel.native.subprocess.Popen',side_effect=start),patch('kel.native.runtime_version',return_value='fixture'):
                result=adapter.execute('trusted correction',session_id=resume,cancel=event,output_schema=correction_schema(parse('Write exactly 2 words.')))
            self.assertFalse(any((base/'sessions').glob('*')))
            return result,seen

    def test_terminal_file_replaces_intermediate_and_preserves_usage_model(self):
        result,seen=self.run_fake()
        self.assertEqual(result['outcome'],'SUCCESS')
        self.assertEqual(decode_correction(result['text'],parse('Write exactly 2 words.')),'Hello there.')
        self.assertEqual(result['usage'],{'input_tokens':7,'output_tokens':3})
        self.assertEqual(result['model_used'],'chosen')
        self.assertTrue(result['structured_output'])
        self.assertEqual(len(seen),1)
        self.assertIn('--output-schema',seen[0])
        self.assertIn('shell_tool',seen[0])

    def test_resume_keeps_schema_on_same_single_invocation(self):
        result,seen=self.run_fake(resume='session-123')
        self.assertEqual(result['session_id'],'session-123')
        self.assertLess(seen[0].index('--output-schema'),seen[0].index('resume'))
        self.assertEqual(len(seen),1)

    def test_terminal_missing_empty_oversize_invalid_utf8_fail_without_retry(self):
        for final in (None,b'',b' '*2,b'\xff',b'x'*256001):
            with self.subTest(final_size=None if final is None else len(final)):
                result,seen=self.run_fake(final=final)
                self.assertEqual(result['outcome'],'FAILED')
                self.assertEqual(result['text'],'')
                self.assertEqual(result['usage']['input_tokens'],7)
                self.assertEqual(len(seen),1)

    def test_completion_and_successful_exit_are_both_required(self):
        for options in ({'completed':False},{'code':1}):
            result,seen=self.run_fake(**options)
            self.assertEqual(result['outcome'],'FAILED')
            self.assertNotIn('structured_output',result)
            self.assertEqual(len(seen),1)

    def test_stop_retains_partial_usage_and_never_reads_terminal(self):
        result,seen=self.run_fake(cancel=True)
        self.assertEqual(result['outcome'],'CANCELLED')
        self.assertNotIn('structured_output',result)
        self.assertEqual(result['usage']['output_tokens'],3)
        self.assertEqual(len(seen),1)

    def test_claude_and_streaming_schema_refused_before_process(self):
        with tempfile.TemporaryDirectory() as root,patch('kel.native.subprocess.Popen') as start:
            for provider,on_text in (('claude',None),('codex',lambda text:None)):
                adapter=NativeAdapter(provider,Path(root)/'work',Path(root)/'logs')
                self.assertEqual(adapter.execute('x',on_text=on_text,output_schema={})['outcome'],'FAILED')
            start.assert_not_called()

    def test_existing_run_and_hardlinked_terminal_refused(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);schema=correction_schema(parse('Write exactly 2 words.'))
            session,_,final=_schema_session(base,'owned',schema)
            with self.assertRaises(FileExistsError):_schema_session(base,'owned',schema)
            final.write_text('valid',encoding='utf-8');os.link(final,session/'other')
            with self.assertRaisesRegex(RuntimeError,'private plain'):_schema_final(final)

    def test_linked_ancestor_refused_without_writing_outside(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);outside=base/'outside';outside.mkdir()
            try:(base/'sessions').symlink_to(outside,target_is_directory=True)
            except OSError:self.skipTest('OS does not permit test symlink')
            with self.assertRaisesRegex(RuntimeError,'linked'):_schema_session(base,'owned',{})
            self.assertEqual(list(outside.iterdir()),[])


class CorrectionSeamTests(unittest.TestCase):
    def test_codex_only_schema_uses_one_durable_accounted_correction(self):
        for provider in ('codex','claude'):
            with self.subTest(provider=provider),tempfile.TemporaryDirectory() as root:
                service=Service(root);service.engine.adapters={}
                try:
                    with patch.object(service.requests,'submit'):
                        sid=service.submit({'conversation':'main','text':'Write exactly 2 words.'})
                    calls=[]
                    class Model(NativeAdapter):
                        def __init__(self):self.provider=provider;self.model='fixture-model'
                        def execute(self,prompt,cancel=None,output_schema=None):
                            calls.append(output_schema)
                            return {'outcome':'SUCCESS','text':'{"words":[{"index":1,"word":"Hello"},{"index":2,"word":"there."}]}',
                                    'usage':{'input_tokens':7,'output_tokens':3},'cost_usd':0.01}
                    text,_=service._checked_word_reply(sid,'main','Write exactly 2 words.','The original has too many words.',
                        parse('Write exactly 2 words.'),Model(),threading.Event(),[])
                    self.assertEqual(text,'Hello there.')
                    self.assertEqual(len(calls),1)
                    self.assertEqual(calls[0] is not None,provider=='codex')
                    ledger=service.context.request_calls(sid)
                    self.assertEqual(len(ledger),1);self.assertEqual(ledger[0]['state'],'settled')
                    with contextlib.closing(service.store.connect()) as db:
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM provider_usage').fetchone()[0],1)
                finally:service.shutdown()
