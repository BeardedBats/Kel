"""Final publication deadline and deterministic executor receipt regressions."""
import contextlib
import json
import tempfile
import time
import unittest
from unittest.mock import patch
from kel.core import PolicyError
from kel.service import Service
from kel.prose_review import executor
from kel.word_limits import parse
from test_direct_prose_review import FakeNative, GOOD


class PublicationFences(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.service=Service(self.tmp.name);self.service.engine.adapters={};self.addCleanup(self.service.shutdown)
        request='Write under 50 words in two paragraphs. Notes preserve decisions and reasons. Notes help someone resume after a break.'
        with patch.object(self.service.requests,'submit'):self.sid=self.service.submit({'conversation':'main','text':request})
        self.limit=parse(request);self.writer=FakeNative('codex','gpt-6-luna',answer=GOOD)
        self.service._kel_usage('reply',self.sid,'main',self.writer,{'outcome':'SUCCESS','model_used':'gpt-6-luna'},1)

    def test_deadline_crossed_after_verified_review_cannot_publish(self):
        reviewer=FakeNative();clock=[time.time()]
        original=self.service._usage_meta
        def delayed(*args,**kwargs):
            with contextlib.closing(self.service.store.connect()) as db:
                verdict=db.execute('SELECT verdict FROM prose_reviews WHERE submission_id=?',(self.sid,)).fetchone()[0]
            self.assertEqual(verdict,'VERIFIED')
            clock[0]+=121
            return original(*args,**kwargs)
        with patch.object(self.service.commander,'_reviewer',return_value=reviewer),\
                patch('kel.prose_review.time.time',side_effect=lambda:clock[0]),\
                patch.object(self.service,'_usage_meta',side_effect=delayed):
            with self.assertRaisesRegex(PolicyError,'time limit'):
                self.service._say(self.sid,'main',GOOD,word_limit=self.limit)
        self.assertEqual(len(reviewer.calls),1)
        with contextlib.closing(self.service.store.connect()) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM messages WHERE role='assistant'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT state FROM submissions WHERE id=?',(self.sid,)).fetchone()[0],'PLANNING')

    def test_executor_uses_latest_sequence_not_clock_or_review_receipt(self):
        def insert(call_id,adapter,model,at,task='writing',outcome='SUCCESS',sid=None,event='run'):
            data={'call_id':call_id,'submission_id':sid or self.sid,'adapter':adapter,'raw_model':model,
                  'task_class':task,'outcome':outcome,'event':event}
            with self.service.store.transaction() as db:
                db.execute('INSERT INTO provider_usage(provider,at,data) VALUES(?,?,?)',(adapter,at,json.dumps(data)))
        insert('newest-executor','claude','claude-opus-5-5',1)
        insert('later-review','codex','gpt-6-astra',999,'review')
        insert('later-failed','codex','gpt-6-astra',1000,outcome='FAILED')
        insert('other-request','codex','gpt-6-astra',1001,sid='different')
        insert('non-run-event','codex','gpt-6-astra',1002,event='quota')
        connect=self.service.store.connect
        def reversed_reads():
            db=connect();db.execute('PRAGMA reverse_unordered_selects=ON');return db
        with patch.object(self.service.store,'connect',side_effect=reversed_reads):
            self.assertEqual(executor(self.service,self.sid),{'provider':'claude','model':'claude-opus-5-5'})
