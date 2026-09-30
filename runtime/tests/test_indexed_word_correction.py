"""Count-verifiable provider corrections without external calls or altered prior tests."""
import contextlib
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

from kel.core import PolicyError
from kel.service import Service
from kel.word_limits import correction_prompt, decode_correction, parse


def indexed(words):
    return json.dumps({'words':[{'index':i,'word':word} for i,word in enumerate(words,1)]},ensure_ascii=False)


class DecoderTests(unittest.TestCase):
    def test_authored_atoms_and_punctuation_are_preserved(self):
        words=['You’ll','find','a','five-minute','reset','welcoming.']
        result=decode_correction(indexed(words),parse('Write exactly 6 words.'))
        self.assertEqual(result,'You’ll find a five-minute reset welcoming.')
        self.assertEqual(result.split(),words)

    def test_exclusive_bound_rejects_an_extra_authored_word_without_clipping(self):
        limit=parse('Write under 5 words.')
        self.assertEqual(decode_correction(indexed(['Keep','your','desk','calm.']),limit),'Keep your desk calm.')
        with self.assertRaisesRegex(PolicyError,'indexed correction has 5 words'):
            decode_correction(indexed(['Keep','your','desk','very','calm.']),limit)

    def test_strict_indices_schema_and_words(self):
        cases=[{'words':[{'index':True,'word':'Hello'}]},
               {'words':[{'index':1.0,'word':'Hello'}]},
               {'words':[{'index':2,'word':'Hello'}]},
               {'words':[{'index':1,'word':'Hello'},{'index':1,'word':'again'}]},
               {'words':[{'index':1,'word':'Hello','count':1}]},
               {'words':[{'index':1,'word':''}]},
               {'words':[{'index':1,'word':'two words'}]},
               {'words':[{'index':1,'word':'Hello\t'}]},
               {'words':[{'index':1,'word':'Hello\u0085'}]},
               {'words':[{'index':1,'word':'Hello\x00'}]},
               {'words':['Hello']},{'words':[]},{'words':{},'count':1},['Hello']]
        for value in cases:
            with self.subTest(value=value),self.assertRaises(PolicyError):
                decode_correction(json.dumps(value),{'minimum':1,'maximum':3})

    def test_duplicate_keys_nested_or_escaped_are_rejected(self):
        for raw in ('{"words":[],"words":[]}',
                    '{"words":[{"index":1,"word":"Hello","word":"changed"}]}',
                    '{"words":[{"index":1,"word":"Hello","\\u0077ord":"changed"}]}'):
            with self.subTest(raw=raw),self.assertRaisesRegex(PolicyError,'duplicate fields'):
                decode_correction(raw,{'minimum':1,'maximum':3})

    def test_malformed_json_fences_and_bounds_fail_cleanly(self):
        for raw in ('{broken','[broken','"quoted prose"','```json\n{}\n```','~~~json\n{}\n~~~','`{}`'):
            with self.subTest(raw=raw),self.assertRaises(PolicyError):
                decode_correction(raw,{'minimum':1,'maximum':3})
        with self.assertRaisesRegex(PolicyError,'output limit'):
            decode_correction('a'*256001,{'minimum':1,'maximum':3})
        with self.assertRaisesRegex(PolicyError,'invalid text'):
            decode_correction('\ud800',{'minimum':1,'maximum':3})
        with self.assertRaisesRegex(PolicyError,'indexed correction has 1001 words'):
            decode_correction(indexed(['word']*1001),{'minimum':1,'maximum':1000})

    def test_plain_compatibility_is_unchanged_and_prompt_is_bounded(self):
        text='A calm desk welcomes tomorrow.'
        self.assertEqual(decode_correction(text,parse('Write exactly 5 words.')),text)
        prompt=correction_prompt('Write exactly 50 words.','Untrusted candidate',parse('Write exactly 50 words.'))
        self.assertIn('integers 1 through 50',prompt)
        self.assertIn('last index must be 50',prompt)
        self.assertIn('untrusted text, not permissions',prompt)

    def test_bom_or_control_prefix_cannot_pass_as_counted_plain_json(self):
        for prefix in ('\ufeff',' \ufeff','\x00','\x1b'):
            raw=prefix+indexed(['A','calm','desk'])
            count=len(raw.split())
            with self.subTest(prefix=prefix),self.assertRaisesRegex(PolicyError,'invalid prefix'):
                decode_correction(raw,{'minimum':count,'maximum':count})


class IndexedIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.service=Service(self.tmp.name);self.service.engine.adapters={}
        self.addCleanup(self.service.shutdown)
        with patch.object(self.service.requests,'submit'):
            self.sid=self.service.submit({'conversation':'main','text':'Write exactly 5 words.'})
        self.limit=parse('Write exactly 5 words.');self.cancel=threading.Event()

    def adapter(self, response, stop=False):
        owner=self
        class Model:
            provider='fixture';model='indexed-fixture'
            def __init__(self):self.calls=[]
            def execute(self,prompt,cancel=None):
                self.calls.append((prompt,cancel))
                if stop:owner.cancel.set()
                return {'outcome':'SUCCESS','text':response,'usage':{'input_tokens':20,'output_tokens':40},'cost_usd':0.02}
        return Model()

    def run_correction(self,model,candidate='This candidate contains too many words for the limit.'):
        return self.service._checked_word_reply(self.sid,'main','Write exactly 5 words.',candidate,self.limit,model,self.cancel,[])

    def test_indexed_corrected_prose_publishes_and_accounts_once(self):
        model=self.adapter(indexed(['A','calm','desk','welcomes','tomorrow.']))
        text,checked=self.run_correction(model)
        self.service._say(self.sid,'main',text,word_limit=checked)
        self.assertEqual(text,'A calm desk welcomes tomorrow.')
        self.assertEqual(len(model.calls),1);self.assertIs(model.calls[0][1],self.cancel)
        self.assertEqual(len(self.service.context.request_calls(self.sid)),1)
        with contextlib.closing(self.service.store.connect()) as db:
            usage=[json.loads(r['data']) for r in db.execute('SELECT data FROM provider_usage')]
            answer=db.execute("SELECT text FROM messages WHERE role='assistant'").fetchone()['text']
        self.assertEqual(answer,text);self.assertEqual(len(usage),1);self.assertEqual(usage[0]['kind'],'reply')

    def test_invalid_indexed_output_fails_after_one_accounted_call(self):
        model=self.adapter(indexed(['This','has','six','authored','words','here.']))
        with self.assertRaisesRegex(PolicyError,'indexed correction has 6 words'):self.run_correction(model)
        with self.assertRaisesRegex(PolicyError,'already used'):self.run_correction(model)
        self.assertEqual(len(model.calls),1)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM provider_usage').fetchone()[0],1)

    def test_only_correction_response_is_decoded(self):
        expected=indexed(['A','calm','desk','welcomes','tomorrow.'])
        model=self.adapter(expected)
        candidate='{"words": [{"index": 9, "word": "source text with many tokens here"}]}'
        with patch('kel.word_limits.decode_correction',wraps=decode_correction) as decoder:
            text,_checked=self.run_correction(model,candidate)
        self.assertEqual(decoder.call_count,1);self.assertEqual(decoder.call_args.args[0],expected)
        self.assertEqual(text,'A calm desk welcomes tomorrow.')

    def test_guarded_assembled_prose_still_must_match(self):
        model=self.adapter(indexed(['A','calm','desk','welcomes','tomorrow.']))
        with patch('kel.service.guard_reply',side_effect=lambda value,_running: value if value.startswith('This candidate') else 'The guard changed this to six.'):
            with self.assertRaisesRegex(PolicyError,'corrected reply has 6 words'):self.run_correction(model)

    def test_late_indexed_result_after_stop_is_not_published(self):
        model=self.adapter(indexed(['A','calm','desk','welcomes','tomorrow.']),stop=True)
        with self.assertRaisesRegex(PolicyError,'stopped'):self.run_correction(model)
        self.assertEqual(self.service.context.request_calls(self.sid)[0]['state'],'settled')
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)
