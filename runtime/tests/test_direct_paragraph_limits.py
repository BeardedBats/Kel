"""Explicit word/paragraph constraints, without models or changed prior tests."""
import contextlib
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from kel.core import PolicyError
from kel.service import Service
from kel.word_limits import parse, matches, paragraph_count, correction_prompt, correction_schema, decode_correction


def indexed(words,labels):
    return json.dumps({'words':[{'index':i,'word':word,'paragraph':label}
                              for i,(word,label) in enumerate(zip(words,labels),1)]})


class ParagraphParserTests(unittest.TestCase):
    def test_explicit_numeric_and_spelled_counts(self):
        for request in ('Write exactly 6 words in two paragraphs.','Write exactly 6 words. Use 2 paragraphs.',
                        'Write a two-paragraph reply in exactly 6 words.','Write exactly 6 words. Return only two paragraphs.'):
            with self.subTest(request=request):
                self.assertEqual(parse(request),{'minimum':6,'maximum':6,'paragraphs':2,'prose_ending_basis':'sentence-punctuation'})
        self.assertEqual(parse('Write exactly 10 words in ten paragraphs.')['paragraphs'],10)
        self.assertEqual(parse('Write exactly 6 words in one paragraph.')['paragraphs'],1)

    def test_quoted_and_ambiguous_paragraph_constraints_do_not_become_metadata(self):
        for request in ('Write exactly 6 words about "use two paragraphs".',
                        'Write exactly 6 words in about two paragraphs.',
                        'Write exactly 6 words in 1-3 paragraphs.',
                        'Write exactly 6 words. Use two paragraphs for one part and three paragraphs for another.',
                        'Write exactly 6 words in 11 paragraphs.'):
            with self.subTest(request=request):self.assertNotIn('paragraphs',parse(request))
        self.assertIsNone(parse('Write two paragraphs of exactly 6 words each.'))
        self.assertEqual(parse('Write two paragraphs.'),{'paragraphs':2,'prose_ending_basis':'sentence-punctuation'})

    def test_impossible_word_and_paragraph_bounds_fail_plainly(self):
        with self.assertRaisesRegex(PolicyError,'at least one word'):
            parse('Write exactly 2 words in three paragraphs.')

    def test_soft_wraps_do_not_create_paragraphs(self):
        self.assertEqual(paragraph_count('One line\nsoft wrapped line.'),1)
        self.assertEqual(paragraph_count('\nFirst block.\n \nSecond block.\n'),2)
        self.assertFalse(matches('One two three four five six.',parse('Write exactly 6 words in two paragraphs.')))
        self.assertTrue(matches('One two three.\n\nFour five six.',parse('Write exactly 6 words in two paragraphs.')))


class ParagraphDecoderTests(unittest.TestCase):
    def test_preserves_authored_words_and_paragraph_boundaries(self):
        limit=parse('Write exactly 6 words in two paragraphs.')
        text=decode_correction(indexed(['Keep','decisions','clear.','Resume','after','breaks.'],[1,1,1,2,2,2]),limit)
        self.assertEqual(text,'Keep decisions clear.\n\nResume after breaks.')
        self.assertTrue(matches(text,limit))

    def test_indices_cannot_skip_reverse_empty_or_fake_paragraphs(self):
        limit=parse('Write exactly 6 words in two paragraphs.')
        for labels in ([2,2,2,2,2,2],[1,1,2,2,1,1],[1,1,3,3,3,3],[1,1,1,1,1,1],[True]*6,[1.0]*6):
            with self.subTest(labels=labels),self.assertRaises(PolicyError):
                decode_correction(indexed(['word']*6,labels),limit)

    def test_schema_requires_bounded_paragraphs_and_keeps_global_indices(self):
        schema=correction_schema(parse('Write exactly 6 words in two paragraphs.'))
        item=schema['properties']['words']['items']
        self.assertEqual(set(item['required']),{'index','word','paragraph'})
        self.assertEqual(item['properties']['paragraph'],{'type':'integer','minimum':1,'maximum':2})
        bad={'words':[{'index':1,'word':'First','paragraph':1},{'index':1,'word':'second','paragraph':2}]}
        with self.assertRaises(PolicyError):decode_correction(json.dumps(bad),parse('Write exactly 2 words in two paragraphs.'))

    def test_maximum_prompt_allows_natural_shorter_authored_reply(self):
        limit=parse('Write under 50 words in two paragraphs.')
        prompt=correction_prompt('request','candidate',limit)
        self.assertIn('Do not pad to the maximum',prompt)
        self.assertNotIn('exactly 49 indexed words',prompt)
        text=decode_correction(indexed(['Keep','decisions','clear.','Resume','after','breaks.'],[1,1,1,2,2,2]),limit)
        self.assertEqual(len(text.split()),6)
        self.assertTrue(matches(text,limit))


class ParagraphServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.service=Service(self.tmp.name);self.service.engine.adapters={};self.addCleanup(self.service.shutdown)
        # This fixture tests mechanical constraints; dedicated prose-review tests cover verdict authority.
        for name in ('review','assert_bound'):
            mock=patch('kel.prose_review.'+name,return_value='mechanical-fixture');mock.start();self.addCleanup(mock.stop)
        self.request='Write exactly 6 words in two paragraphs.'
        with patch.object(self.service.requests,'submit'):
            self.sid=self.service.submit({'conversation':'main','text':self.request})
        self.limit=parse(self.request);self.cancel=threading.Event()

    def model(self,response):
        class Model:
            provider='fixture';model='paragraph-fixture';calls=0
            def execute(self,prompt,cancel=None):
                self.calls+=1
                return {'outcome':'SUCCESS','text':response,'usage':{'input_tokens':2,'output_tokens':6},'cost_usd':0.01}
        return Model()

    def check(self,candidate,model):
        return self.service._checked_word_reply(self.sid,'main',self.request,candidate,self.limit,model,self.cancel,[])

    def test_correct_words_wrong_paragraphs_still_uses_one_correction(self):
        model=self.model(indexed(['Keep','decisions','clear.','Resume','after','breaks.'],[1,1,1,2,2,2]))
        text,checked=self.check('Keep decisions clear. Resume after breaks.',model)
        self.assertEqual(model.calls,1);self.assertEqual(paragraph_count(text),2)
        self.service._say(self.sid,'main',text,word_limit=checked)
        self.assertEqual(len(self.service.context.request_calls(self.sid)),1)
        with contextlib.closing(self.service.store.connect()) as db:
            row=db.execute("SELECT meta FROM messages WHERE role='assistant'").fetchone()
            self.assertEqual(json.loads(row['meta'])['word_limit']['paragraph_count'],2)

    def test_valid_candidate_needs_no_model_call(self):
        model=self.model('unused')
        text,checked=self.check('Keep decisions clear.\n\nResume after breaks.',model)
        self.assertEqual(model.calls,0);self.assertFalse(checked['correction_used'])

    def test_plain_compatible_correction_reports_format_error_not_false_count_error(self):
        with self.assertRaisesRegex(PolicyError,'corrected reply has 1 paragraphs'):
            self.check('Too many words originally existed in this reply.',self.model('Keep decisions clear. Resume after breaks.'))
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)

    def test_final_publication_rechecks_format_after_choice(self):
        text='Keep decisions clear.\n\nResume after breaks.'
        with patch.object(self.service,'_with_choice',return_value=(text.replace('\n\n',' '),None)):
            with self.assertRaisesRegex(PolicyError,'final reply has 1 paragraphs'):
                self.service._say(self.sid,'main',text,word_limit=self.limit)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)
