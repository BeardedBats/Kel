import contextlib,tempfile,unittest
from unittest.mock import patch
from kel.core import Store
from kel.coding import CodingAdapter,compile_coding
from kel.coding_transport import init
from kel.engine import compile_document
from kel.runner import recover_isolated_loss

class IsolatedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Store(self.temp.name);CodingAdapter(self.s);init(self.s)
        self.j=self.s.create(dict(compile_document('Fix this code.'),kind='coding'))
        self.r=self.s.claim(self.j,'document',provider='codex-code')
        workspace=self.s.root/'repositories'/'copy';workspace.mkdir(parents=True)
        with self.s.transaction() as db:
            db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',(self.j,str(workspace),'base','{}'))
            db.execute('INSERT INTO isolated_runs VALUES(?,?,?)',(self.r['id'],'a'*32,'/work/discarded'))
    def tearDown(self):self.temp.cleanup()
    def test_quiescent_contained_work_can_retry_without_old_session(self):
        with patch('kel.wsl_runtime.stop_group',return_value=True):self.assertTrue(recover_isolated_loss(self.s,self.r['id']))
        job=self.s.get(self.j);self.assertEqual(job['state'],'READY');self.assertEqual(job['reserved'],0)
        with contextlib.closing(self.s.connect()) as db:self.assertEqual(db.execute('SELECT state FROM runs').fetchone()[0],'ORPHANED')
    def test_expanded_permission_prevents_automatic_replay(self):
        aid=self.s.request_approval(self.j,self.r['id'],{'network':True});self.s.resolve_approval(aid,{'network':True},True)
        with patch('kel.wsl_runtime.stop_group') as stop:
            self.assertFalse(recover_isolated_loss(self.s,self.r['id']));stop.assert_not_called()
    def test_unknown_process_quiescence_remains_fenced(self):
        with patch('kel.wsl_runtime.stop_group',return_value=False):self.assertFalse(recover_isolated_loss(self.s,self.r['id']))
        self.assertNotEqual(self.s.get(self.j)['state'],'READY')
    def test_cancel_acknowledged_only_after_confirmed_group_stop(self):
        self.s.control(self.j,'cancel')
        with patch('kel.wsl_runtime.stop_group',return_value=True):self.assertTrue(recover_isolated_loss(self.s,self.r['id']))
        self.assertEqual(self.s.get(self.j)['state'],'CANCELLED')

if __name__=='__main__':unittest.main()
