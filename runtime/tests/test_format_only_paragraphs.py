"""Paragraph-only requests never acquire invented word limits."""
import contextlib
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from kel.core import PolicyError
from kel.service import Service
from kel.word_limits import parse, matches, decode_correction, correction_schema


class FormatOnly(unittest.TestCase):
    def test_no_word_bound_and_authored_text_preserved(self):
        limit=parse('Write two paragraphs about planning.')
        self.assertEqual(limit,{'paragraphs':2,'prose_ending_basis':'sentence-punctuation'})
        source={'paragraphs':[{'index':1,'text':'  Keep decisions clear.\nA soft wrap.'},
                              {'index':2,'text':'Resume after breaks.  '}]}
        answer=decode_correction(json.dumps(source),limit)
        self.assertEqual(answer,'  Keep decisions clear.\nA soft wrap.\n\nResume after breaks.  ')
        self.assertTrue(matches(answer,limit))
        self.assertEqual(correction_schema(limit)['properties']['paragraphs']['minItems'],2)

    def test_quoted_ranges_and_per_part_do_not_acquire_constraints(self):
        for text in ('Explain "Write two paragraphs".', 'Write 1-3 paragraphs.',
                     'Write two paragraphs of six words each.', 'Write two paragraphs and three paragraphs for another part.'):
            with self.subTest(text=text):self.assertIsNone(parse(text))

    def test_structured_output_rejects_duplicates_indices_and_multiple_blocks(self):
        limit={'paragraphs':2}
        bad=('\ufeff{"paragraphs":[]}', '{"paragraphs":[],"paragraphs":[]}',
             '{"paragraphs":[{"index":true,"text":"One"},{"index":2,"text":"Two"}]}',
             '{"paragraphs":[{"index":2,"text":"One"},{"index":1,"text":"Two"}]}',
             '{"paragraphs":[{"index":1,"text":"One\\n\\nOther"},{"index":2,"text":"Two"}]}',
             '{"paragraphs":[{"index":1,"text":" "},{"index":2,"text":"Two"}]}')
        for raw in bad:
            with self.subTest(raw=raw),self.assertRaises(PolicyError):decode_correction(raw,limit)

    def test_one_accounted_correction_and_final_publication_guard(self):
        with tempfile.TemporaryDirectory() as root:
            service=Service(root);service.engine.adapters={}
            try:
                request='Write two paragraphs about planning.'
                with patch.object(service.requests,'submit'):sid=service.submit({'conversation':'main','text':request})
                class Model:
                    provider='fixture';model='format-fixture';calls=0
                    def execute(self,prompt,cancel=None):
                        self.calls+=1
                        return {'outcome':'SUCCESS','text':json.dumps({'paragraphs':[{'index':1,'text':'Keep decisions clear.'},{'index':2,'text':'Resume after breaks.'}]}),'usage':{'input_tokens':2,'output_tokens':6}}
                model=Model()
                answer,limit=service._checked_word_reply(sid,'main',request,'One block.',parse(request),model,threading.Event(),[])
                self.assertEqual(model.calls,1)
                self.assertEqual(len(service.context.request_calls(sid)),1)
                with patch.object(service,'_with_choice',return_value=(answer.replace('\n\n',' '),None)):
                    with self.assertRaisesRegex(PolicyError,'paragraphs'):service._say(sid,'main',answer,word_limit=limit)
                with patch('kel.prose_review.review',return_value='mechanical-fixture'),patch('kel.prose_review.assert_bound'):
                    service._say(sid,'main',answer,word_limit=limit)
                with contextlib.closing(service.store.connect()) as db:
                    meta=json.loads(db.execute("SELECT meta FROM messages WHERE role='assistant'").fetchone()[0])
                self.assertNotIn('word_limit',meta)
                self.assertEqual(meta['reply_constraints']['paragraph_count'],2)
                self.assertNotIn('count',meta['reply_constraints'])
            finally:service.shutdown()
