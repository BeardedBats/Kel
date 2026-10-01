"""Recorded count-valid W3 fragment cannot pass the narrow prose-ending boundary."""
import contextlib
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from kel.core import PolicyError
from kel.service import Service
from kel.word_limits import parse,matches,prose_ending_ok,correction_prompt
from kel.activity import timeline

RECORDED='In 2020, project notes helped teams keep track of decisions and the reasons behind them. When someone stepped away, the notes offered a clear place to pick up again. They made it easier to resume after a break without losing sight of what had been decided or why. A few'


class Endings(unittest.TestCase):
    def test_recorded_count_pass_is_not_an_ending_pass(self):
        limit=parse('Write exactly 50 words about project notes in 2020, in one paragraph.')
        self.assertEqual(len(RECORDED.split()),50)
        self.assertTrue(matches(RECORDED,limit))
        self.assertFalse(prose_ending_ok(RECORDED,limit))
        self.assertEqual(limit['prose_ending_basis'],'sentence-punctuation')
        prompt=correction_prompt('request',RECORDED,limit)
        self.assertIn('complete grammatical sentences',prompt)
        self.assertIn('never take its first N words',prompt)

    def test_closing_tokens_are_inspected_without_changing_authored_bytes(self):
        limit=parse('Write one paragraph.')
        for text in ('Finished.', 'Finished!', 'Finished?', 'Finished…', '“Finished.”', '(Finished.)',
                     '**Finished.**', '*Finished.*[^note-1]', 'Finished.[^1]'):
            with self.subTest(text=text):
                before=text;self.assertTrue(prose_ending_ok(text,limit));self.assertEqual(text,before)
        for text in ('A few', 'Finished. more', 'Finished.[arbitrary]', 'Finished.[^invalid label]', 'Finished.** hidden'):
            with self.subTest(text=text):self.assertFalse(prose_ending_ok(text,limit))
        self.assertFalse(prose_ending_ok('First ends.\n\nSecond fragment',parse('Write two paragraphs.')))

    def test_explicit_structured_formats_keep_only_unambiguous_word_bounds(self):
        for shape in ('bullet points','a list','headings','a table','a numbered list','bulleted headings','a Markdown table','an unordered list'):
            with self.subTest(shape=shape):
                limit=parse('Write exactly 50 words in two paragraphs using '+shape+'.')
                self.assertEqual(limit,{'minimum':50,'maximum':50})
                self.assertTrue(prose_ending_ok(RECORDED,limit))

    def test_one_accounted_correction_not_two_and_final_guard(self):
        with tempfile.TemporaryDirectory() as root:
            service=Service(root);service.engine.adapters={}
            try:
                request='Write exactly 50 words in one paragraph.'
                with patch.object(service.requests,'submit'):sid=service.submit({'conversation':'main','text':request})
                class Model:
                    provider='fixture';model='ending-fixture';calls=0
                    def execute(self,prompt,cancel=None):
                        self.calls+=1
                        return {'outcome':'SUCCESS','text':json.dumps({'words':[{'index':i,'word':word,'paragraph':1} for i,word in enumerate(RECORDED.split(),1)]}),
                                'usage':{'input_tokens':2,'output_tokens':50}}
                model=Model();limit=parse(request)
                with self.assertRaisesRegex(PolicyError,'missing sentence-ending punctuation'):
                    service._checked_word_reply(sid,'main',request,RECORDED,limit,model,threading.Event(),[])
                with self.assertRaisesRegex(PolicyError,'already used'):
                    service._checked_word_reply(sid,'main',request,RECORDED,limit,model,threading.Event(),[])
                self.assertEqual(model.calls,1)
                self.assertEqual(service.context.request_calls(sid)[0]['state'],'settled')
                rows=timeline(service.store,project_id='default')['entries']
                self.assertTrue(any(row['what']=='Kel is correcting sentence endings with one more model call.' for row in rows))
                with patch.object(service,'_with_choice',return_value=(RECORDED,None)):
                    with self.assertRaisesRegex(PolicyError,'missing sentence-ending punctuation'):
                        service._say(sid,'main',RECORDED+'.',word_limit=limit)
                with contextlib.closing(service.store.connect()) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM provider_usage').fetchone()[0],1)
            finally:service.shutdown()

    def test_valid_format_only_prose_needs_no_call_and_retains_basis(self):
        with tempfile.TemporaryDirectory() as root:
            service=Service(root);service.engine.adapters={}
            try:
                request='Write two paragraphs.'
                with patch.object(service.requests,'submit'):sid=service.submit({'conversation':'main','text':request})
                text='Keep decisions clear.\n\nResume after breaks.'
                with patch.object(service,'_admit_planning_call') as admit:
                    answer,checked=service._checked_word_reply(sid,'main',request,text,parse(request),None,threading.Event(),[])
                    admit.assert_not_called()
                with patch('kel.prose_review.review',return_value='mechanical-fixture'),patch('kel.prose_review.assert_bound'):
                    service._say(sid,'main',answer,word_limit=checked)
                with contextlib.closing(service.store.connect()) as db:
                    meta=json.loads(db.execute("SELECT meta FROM messages WHERE role='assistant'").fetchone()[0])
                self.assertEqual(meta['reply_constraints']['prose_ending_basis'],'sentence-punctuation')
                self.assertNotIn('word_limit',meta)
            finally:service.shutdown()
