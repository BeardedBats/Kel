import contextlib
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

from kel.core import PolicyError
from kel.service import Service
from kel.word_limits import parse, matches
from kel.activity import timeline


class ParserTests(unittest.TestCase):
    def test_exact_and_exclusive_limits(self):
        for request in ('Write a 50-word paragraph.', 'Write exactly 50 words.'):
            self.assertEqual(parse(request), {'minimum':50,'maximum':50})
        self.assertEqual(parse('Revise that paragraph to stay under 50 words.'), {'minimum':1,'maximum':49})
        self.assertEqual(parse('Write fewer than 50 words.'), {'minimum':1,'maximum':49})
        self.assertEqual(parse('Write no more than 50 words.'), {'minimum':1,'maximum':50})
        self.assertTrue(matches('word '*49,parse('Write under 50 words.')))
        self.assertFalse(matches('word '*50,parse('Write under 50 words.')))

    def test_quotes_examples_approximate_and_separate_targets_defer(self):
        for request in ('Explain "Write exactly 50 words".', "Explain 'write under 50 words'.",
                        'Explain `write exactly 50 words`.', 'Explain ```write exactly 50 words```.',
                        'Explain the following text:\n> Write exactly 50 words about desks.\nA quoted continuation.',
                        'Explain the following text:\n```\nWrite exactly 50 words about desks.',
                        'Explain the following text:\n"Write exactly 50 words\nabout desks."',
                        'Write about 50 words.', 'Write roughly 50 words.', 'Write between 40 and 50 words.',
                        'Write a 100-word summary with a 20-word quote.', 'Write two 50-word paragraphs.',
                        'What is a 50-word paragraph?', 'Write exactly 1001 words.'):
            with self.subTest(request=request):self.assertIsNone(parse(request))

    def test_contradictory_limits_do_not_guess(self):
        with self.assertRaisesRegex(PolicyError,'Choose one word limit'):
            parse('Write exactly 50 words, under 50 words.')


class DirectLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.service=Service(self.tmp.name);self.service.engine.adapters={}
        self.addCleanup(self.service.shutdown)
        with patch.object(self.service.requests,'submit'):
            self.sid=self.service.submit({'conversation':'main','text':'Write exactly 5 words.'})
        self.cancel=threading.Event();self.limit=parse('Write exactly 5 words.')

    def model(self, text='A calm desk welcomes tomorrow.', stop=False):
        owner=self
        class Fake:
            provider='fixture';model='word-fixture'
            def __init__(self):self.calls=[]
            def execute(self,prompt,**kwargs):
                self.calls.append(kwargs)
                if stop:owner.cancel.set()
                return {'outcome':'SUCCESS','text':text,'usage':{'input_tokens':10,'output_tokens':5},'cost_usd':0.01}
        return Fake()

    def checked(self, model, candidate='Too many words appear in this candidate.'):
        return self.service._checked_word_reply(self.sid,'main','Write exactly 5 words.',candidate,self.limit,model,self.cancel,[])

    def test_matching_reply_uses_no_call(self):
        model=self.model()
        answer,limit=self.checked(model,'A calm desk welcomes tomorrow.')
        self.assertEqual(model.calls,[]);self.assertFalse(limit['correction_used'])
        self.assertEqual(self.service.context.request_calls(self.sid),[])

    def test_one_correction_accounted_once_and_scoped_activity(self):
        model=self.model();answer,limit=self.checked(model)
        self.assertEqual(len(model.calls),1);self.assertIs(model.calls[0]['cancel'],self.cancel)
        self.assertTrue(limit['correction_used']);self.assertEqual(len(answer.split()),5)
        self.service._say(self.sid,'main',answer,word_limit=limit)
        calls=self.service.context.request_calls(self.sid)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0]['state'],'settled')
        self.assertEqual(calls[0]['estimate']['purpose'],'word_limit_correction')
        with contextlib.closing(self.service.store.connect()) as db:
            usage=[json.loads(r['data']) for r in db.execute('SELECT data FROM provider_usage')]
            meta=json.loads(db.execute("SELECT meta FROM messages WHERE role='assistant' ORDER BY seq DESC LIMIT 1").fetchone()['meta'])
        self.assertEqual(len(usage),1);self.assertEqual(usage[0]['kind'],'reply');self.assertEqual(usage[0]['task_class'],'writing')
        self.assertEqual(meta['word_limit']['count'],5)
        rows=timeline(self.service.store,project_id='default')['entries']
        self.assertTrue(any(r['what']=='Kel is correcting the word count with one more model call.' for r in rows))
        self.assertEqual(timeline(self.service.store,project_id='other')['entries'],[])

    def test_second_mismatch_fails_and_cannot_repeat_durably(self):
        model=self.model('Still too many words appear in this reply.')
        with self.assertRaisesRegex(PolicyError,'corrected reply has 8 words'):self.checked(model)
        with self.assertRaisesRegex(PolicyError,'already used'):self.checked(model)
        self.assertEqual(len(model.calls),1)

    def test_cancel_after_admission_does_not_execute_or_record_provider_usage(self):
        admit=self.service._admit_planning_call
        def cancelling(*args,**kwargs):
            call=admit(*args,**kwargs);self.cancel.set();return call
        model=self.model()
        with patch.object(self.service,'_admit_planning_call',side_effect=cancelling):
            with self.assertRaisesRegex(PolicyError,'stopped'):self.checked(model)
        self.assertEqual(model.calls,[])
        call=self.service.context.request_calls(self.sid)[0]
        self.assertEqual(call['state'],'settled');self.assertEqual(call['usage']['execution_state'],'not_started')
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM provider_usage').fetchone()[0],0)

    def test_cancelled_late_correction_is_not_published(self):
        model=self.model(stop=True)
        with self.assertRaisesRegex(PolicyError,'stopped'):self.checked(model)
        self.assertEqual(len(model.calls),1)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)

    def test_final_publication_guard_checks_after_reply_guard(self):
        model=self.model()
        with patch('kel.service.guard_reply',return_value='Guard changed the reply to seven words.'):
            with self.assertRaisesRegex(PolicyError,'corrected reply has 7 words'):self.checked(model)

    def test_fallback_disclosure_cannot_publish_an_over_limit_reply(self):
        choice={'answered_by':{'label':'Fixture model'},'fallback_from':{'provider':'fixture-missing','label':'Chosen model'}}
        with self.assertRaisesRegex(PolicyError,'final reply has'):
            self.service._say(self.sid,'main','A calm desk welcomes tomorrow.',choice,word_limit=self.limit)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)

    def test_constrained_turn_does_not_stream_unchecked_candidate(self):
        model=self.model()
        with contextlib.closing(self.service.store.connect()) as db:
            packet=json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?',(self.sid,)).fetchone()['packet'])
        def decide(*args,**kwargs):
            self.assertIsNone(kwargs['on_text'])
            return {'action':'reply','text':'Too many words appear in this candidate.'}
        with patch.object(self.service,'_turn_choice',return_value=(model,None)),patch('kel.service.decide_turn',side_effect=decide):
            self.service._plan(self.sid,'main','Write exactly 5 words.',packet,'chat')
        with contextlib.closing(self.service.store.connect()) as db:
            submission=db.execute('SELECT state,error FROM submissions WHERE id=?',(self.sid,)).fetchone()
            answers=[r['text'] for r in db.execute("SELECT text FROM messages WHERE role='assistant'")]
        self.assertEqual(tuple(submission),('SETTLED',None));self.assertEqual(answers,['A calm desk welcomes tomorrow.'])
        self.assertEqual(self.service.draft(self.sid)['text'],'')

    def test_conflicting_prose_limits_do_not_block_background_intake(self):
        with contextlib.closing(self.service.store.connect()) as db:
            packet=json.loads(db.execute('SELECT packet FROM submission_packets WHERE id=?',(self.sid,)).fetchone()['packet'])
        packet['project']['root']=self.tmp.name
        decision={'action':'start_background_work','title':'Build page','acknowledgement':'Starting the page.'}
        with patch.object(self.service,'_turn_choice',return_value=(None,None)),patch('kel.service.needs_work',return_value=True),\
                patch.object(self.service,'_handoff',return_value='owned-background') as dispatch:
            self.service._plan(self.sid,'main','Create a page with exactly 50 words, under 50 words.',packet,'coding')
        dispatch.assert_called_once()
