import contextlib,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from kel.core import Store,digest,encode
from kel.engine import compile_document
from kel.coding import CodingAdapter,file_manifest,recover_checked_code,recover_pending_checks
from kel.runner import init,monitor


class CodingRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.s=Store(self.temp.name);init(self.s);CodingAdapter(self.s)
  self.j=self.s.create(dict(compile_document('Fix the source.',['Recovered repository change']),kind='coding'))
  self.run=self.s.claim(self.j,'document',provider='codex-code')
  self.workspace=self.s.root/'repository';self.workspace.mkdir();(self.workspace/'app.py').write_text('answer=42\n')
  diff='diff --git a/app.py b/app.py\n+answer=42\n'
  tests={'exit_code':0,'stdout':'one test passed','stderr':'','existing_tests_preserved':True,'source_stable_during_tests':True}
  with self.s.transaction() as db:
   db.execute("INSERT INTO brokers VALUES(?,?,?,?,?,?,?,?,'RUNNING',0,NULL)",(self.run['id'],self.run['epoch'],'codex-code','prompt','session','{}',101,'broker'))
   db.execute('INSERT INTO native_processes VALUES(?,?,?,?,?)',(self.run['id'],102,'child','unused',time.time()+300))
   db.execute('INSERT INTO native_progress(run_id,method,data,at) VALUES(?,?,?,?)',(self.run['id'],'turn/completed',encode({'turn':{'id':'turn','status':'completed'}}),time.time()))
   db.execute('INSERT INTO code_evidence VALUES(?,?,?,?,?,?,?,?)',(self.run['id'],str(self.workspace),encode(file_manifest(self.workspace)),diff,digest(diff.encode()),encode(tests),'{}',time.time()))
 def tearDown(self):self.temp.cleanup()
 def test_complete_evidence_recovers_without_replaying_code_or_tests(self):
  with patch('kel.runner.process_identity',return_value=None):result=monitor(self.s,self.run['id'])
  self.assertTrue(result['recovered_from_code_evidence']);self.s.consume();self.s.verify(self.j,'document');self.assertEqual(self.s.assess(self.j),'VERIFIED')
  with contextlib.closing(self.s.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM runs').fetchone()[0],1)
 def test_changed_workspace_is_not_accepted(self):
  (self.workspace/'app.py').write_text('changed after capture')
  with patch('kel.runner.process_identity',return_value=None):result=monitor(self.s,self.run['id'])
  self.assertTrue(result['uncertain']);self.assertEqual(self.s.get(self.j)['state'],'WAITING_RESOURCE')
 def test_missing_test_receipt_stays_fenced(self):
  with self.s.transaction() as db:db.execute('DELETE FROM code_evidence')
  with patch('kel.runner.process_identity',return_value=None):result=monitor(self.s,self.run['id'])
  self.assertTrue(result['uncertain'])
  with contextlib.closing(self.s.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM inbox').fetchone()[0],0)
 def test_quiesces_only_recorded_native_process(self):
  with contextlib.closing(self.s.connect()) as db:run=dict(db.execute('SELECT * FROM runs').fetchone());row=dict(db.execute('SELECT * FROM brokers').fetchone())
  with patch('kel.runner.process_identity',return_value='child'),patch('kel.runner.terminate_known_process',return_value=True) as stop:
   self.assertEqual(recover_checked_code(self.s,run,row),'LIVE');stop.assert_called_once_with(102,'child')

 def pending_checks(self,phase='TURN_COMPLETED'):
  with self.s.transaction() as db:
   db.execute('DELETE FROM code_evidence')
   db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',(self.j,str(self.workspace),'base','{}'))
   db.execute('INSERT INTO coding_phases VALUES(?,?,?,?)',(self.run['id'],phase,encode({'outcome':'SUCCESS','turn_id':'turn','_checkpoint_manifest':file_manifest(self.workspace)}),time.time()))
  with contextlib.closing(self.s.connect()) as db:return dict(db.execute('SELECT * FROM runs').fetchone())

 def test_only_undispatched_tests_can_resume(self):
  run=self.pending_checks()
  with patch('kel.runner.process_identity',return_value=None):self.assertEqual(recover_pending_checks(self.s,run),'RESUME_CHECKS')
  for phase in ('TURN_DISPATCHED','TESTS_DISPATCHED','EVIDENCE_CAPTURED'):
   with self.s.transaction() as db:db.execute('UPDATE coding_phases SET phase=?',(phase,))
   with patch('kel.runner.process_identity',return_value=None):self.assertIsNone(recover_pending_checks(self.s,run))

 def test_pending_checks_reject_tamper_and_cancel(self):
  run=self.pending_checks()
  with patch('kel.runner.process_identity',return_value=None):
   self.assertIsNone(recover_pending_checks(self.s,dict(run,state='CANCEL_REQUESTED')))
   (self.workspace/'app.py').write_text('tampered')
   self.assertIsNone(recover_pending_checks(self.s,run))

 def test_pending_checks_stop_old_native_child_before_resume(self):
  run=self.pending_checks()
  with patch('kel.runner.process_identity',return_value='child'),patch('kel.runner.terminate_known_process',return_value=True) as stop:
   self.assertEqual(recover_pending_checks(self.s,run),'LIVE')
   stop.assert_called_once_with(102,'child')

 def test_repeated_recovery_is_bounded(self):
  from kel.runner import restart_checks_broker
  run=self.pending_checks()
  with contextlib.closing(self.s.connect()) as db:row=dict(db.execute('SELECT * FROM brokers').fetchone())
  row['options']=encode({'_checks_restarts':2})
  with patch('kel.runner.subprocess.Popen') as spawn:
   self.assertFalse(restart_checks_broker(self.s,run,row));spawn.assert_not_called()
