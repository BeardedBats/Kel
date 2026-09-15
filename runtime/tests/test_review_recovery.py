import contextlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from kel.core import Store,uid
from kel.engine import Engine,compile_document


class Verifier:
    def review(self,store,jid,mid):
        j=store.get(jid);m=j['milestones'][mid]
        return store.record_review(jid,mid,m['artifact']['sha256'],uid(),'VERIFIED',['Fixture criterion satisfied.'],j['contract_version'])


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Store(self.temp.name)
        self.j=self.s.create(compile_document('Write a plain guide.'))
        r=self.s.claim(self.j,'document')
        self.s.enqueue_result('receipt',r['id'],r['epoch'],{'outcome':'SUCCESS','text':'A completed artifact ready for independent review.'})
        self.s.consume();self.s.verify(self.j,'document')

    def tearDown(self):self.temp.cleanup()

    def finish(self,reviewer):
        e=Engine(self.s,{},reviewer=reviewer)
        try:
            for _ in range(100):
                e.tick()
                if self.s.get(self.j)['state']=='CLOSED':break
                time.sleep(.01)
            return self.s.get(self.j)
        finally:e.close()

    def test_actual_process_crash_resumes_review_without_worker_replay(self):
        script="""import os,sys,time
from kel.core import Store
from kel.engine import Engine
class Crash:
 def review(self,*args):os._exit(23)
e=Engine(Store(sys.argv[1]),{},reviewer=Crash())
e.tick()
time.sleep(5)
"""
        p=subprocess.run([sys.executable,'-c',script,self.temp.name],cwd=Path(__file__).resolve().parents[1],timeout=10,capture_output=True)
        self.assertEqual(p.returncode,23,p.stderr)
        j=self.finish(Verifier());self.assertEqual(j['verdict'],'VERIFIED')
        with contextlib.closing(self.s.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM runs').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM publications').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT attempts FROM review_runs').fetchone()[0],2)

    def test_missing_verdict_settles_uncertain_once(self):
        class Empty:
            def review(self,*args):return 'UNCERTAIN'
        j=self.finish(Empty());self.assertEqual(j['verdict'],'UNCERTAIN')
        self.assertIn('no usable',j['milestones']['document']['checks'][-1]['findings'][0])
        with contextlib.closing(self.s.connect()) as db:self.assertEqual(db.execute('SELECT attempts FROM review_runs').fetchone()[0],1)

    def test_recovery_budget_does_not_repeat_forever(self):
        e=Engine(self.s,{},reviewer=Verifier());e.close()
        j=self.s.get(self.j);subject=j['milestones']['document']['artifact']['sha256']
        with self.s.transaction() as db:db.execute('INSERT INTO review_runs VALUES(?,?,?,?,?,?)',(self.j,'document',subject,j['contract_version'],2,'INTERRUPTED'))
        j=self.finish(Verifier());self.assertEqual(j['verdict'],'UNCERTAIN')
        self.assertIn('interrupted twice',j['milestones']['document']['checks'][-1]['findings'][0])
