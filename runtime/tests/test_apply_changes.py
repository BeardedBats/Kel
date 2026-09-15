import contextlib,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from kel.core import Store,PolicyError,encode,digest
from kel.coding import CodingAdapter,compile_coding,snapshot,file_manifest,git
from kel.apply_changes import apply_checked

class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();base=Path(self.tmp.name)
        self.root=base/'source';self.root.mkdir();git(self.root,'init')
        (self.root/'app.txt').write_text('old');(self.root/'remove.txt').write_text('remove')
        git(self.root,'add','-A');git(self.root,'-c','user.name=Kel','-c','user.email=kel@localhost','commit','-m','base')
        self.s=Store(base/'data');CodingAdapter(self.s)
        self.j=self.s.create(compile_coding('Change app.txt, remove remove.txt, add new.txt.',self.root,['python','-m','unittest']))
        self.w=base/'copy';revision=snapshot(self.root,self.w);baseline=file_manifest(self.w)
        (self.w/'app.txt').write_text('new');(self.w/'new.txt').write_text('added');(self.w/'remove.txt').unlink()
        git(self.w,'add','-A');diff=git(self.w,'diff','--cached','--binary',revision).decode()
        run=self.s.claim(self.j,'code',provider='codex-code')
        tests={'exit_code':0,'existing_tests_preserved':True,'source_stable_during_tests':True}
        with self.s.transaction() as db:
            db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',(self.j,str(self.w),revision,encode(baseline)))
            db.execute('INSERT INTO code_evidence VALUES(?,?,?,?,?,?,?,?)',(run['id'],str(self.w),encode(file_manifest(self.w)),diff,digest(diff.encode()),encode(tests),'{}',time.time()))
        self.s.enqueue_result('result',run['id'],run['epoch'],{'outcome':'SUCCESS','text':'Verified fixture change with complete trusted evidence.'})
        self.s.consume();self.s.verify(self.j,'code')
        artifact=self.s.get(self.j)['milestones']['code']['artifact']
        self.s.record_review(self.j,'code',artifact['sha256'],'reviewer','VERIFIED',['Fixture output meets the requested diff.'])
        self.assertEqual(self.s.assess(self.j),'VERIFIED')
    def tearDown(self):self.tmp.cleanup()
    def test_greenfield_contract_carries_flag_and_rubric(self):
        c=compile_coding('Build a small mic mute app.',self.root,['python','smoke_test.py'],project_id='p1',greenfield=True)
        self.assertTrue(c['greenfield'])
        self.assertIn('smoke test',c['milestones'][0]['checks'][1]['rubric'])
        self.assertEqual(c['test_command'],['python','smoke_test.py'])
    def test_apply_and_repeat_never_overwrite_later_edit(self):
        self.assertEqual(apply_checked(self.s,self.j)['state'],'APPLIED')
        self.assertEqual((self.root/'app.txt').read_text(),'new');self.assertFalse((self.root/'remove.txt').exists())
        (self.root/'app.txt').write_text('user edit')
        self.assertTrue(apply_checked(self.s,self.j)['already_applied'])
        self.assertEqual((self.root/'app.txt').read_text(),'user edit')
    def test_source_conflict_leaves_project_unchanged(self):
        (self.root/'app.txt').write_text('user edit')
        with self.assertRaises(PolicyError):apply_checked(self.s,self.j)
        self.assertFalse((self.root/'new.txt').exists())
    def test_crash_after_first_replace_resumes_without_repeating_it(self):
        import os
        replace=os.replace;calls=[]
        def interrupt(a,b):
            calls.append(str(b));replace(a,b)
            if len(calls)==1:raise RuntimeError('injected crash after rename')
        with patch('kel.apply_changes.os.replace',side_effect=interrupt):
            with self.assertRaises(RuntimeError):apply_checked(self.s,self.j)
        with patch('kel.apply_changes.os.replace',wraps=replace) as resumed:
            self.assertEqual(apply_checked(Store(self.s.root),self.j)['state'],'APPLIED')
            self.assertNotIn(calls[0],[str(c.args[1]) for c in resumed.call_args_list])
    def test_crash_before_replace_recovers_staging_file(self):
        with patch('kel.apply_changes.os.replace',side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError):apply_checked(self.s,self.j)
        self.assertEqual(apply_checked(self.s,self.j)['state'],'APPLIED')
    def test_changed_evidence_cannot_apply(self):
        (self.w/'app.txt').write_text('tampered')
        with self.assertRaises(PolicyError):apply_checked(self.s,self.j)
        self.assertEqual((self.root/'app.txt').read_text(),'old')

if __name__=='__main__':unittest.main()
