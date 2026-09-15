import contextlib,json,tempfile,unittest,time,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from kel.core import Store
from kel.engine import compile_document
from kel.runner import init,monitor,recover_readonly_result,process_identity,terminate_known_process

class BrokerRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.s=Store(self.temp.name);init(self.s)
  self.j=self.s.create(compile_document('Write a result.',['RECOVERED']))
  self.r=self.s.claim(self.j,'document',provider='codex')
  self.log=self.s.root/'native-logs'/('result.stdout');self.log.parent.mkdir();self.log.write_text('')
  with self.s.transaction() as db:
   db.execute("INSERT INTO brokers VALUES(?,?,?,?,?,?,?,?,'RUNNING',0,NULL)",(self.r['id'],self.r['epoch'],'codex','prompt',None,'{}',101,'old-broker'))
   db.execute('INSERT INTO native_processes VALUES(?,?,?,?,?)',(self.r['id'],102,'old-child',str(self.log),time.time()+300))
 def tearDown(self):self.temp.cleanup()
 def test_fenced_run_stops_monitor_even_if_broker_still_alive(self):
  with self.s.transaction() as db:db.execute("UPDATE runs SET state='ORPHANED' WHERE id=?",(self.r['id'],))
  with patch('kel.runner.process_identity',return_value='old-broker'):
   result=monitor(self.s,self.r['id'])
  self.assertEqual(result['outcome'],'FAILED');self.assertTrue(result['uncertain'])
 def rows(self):
  with contextlib.closing(self.s.connect()) as db:return dict(db.execute('SELECT * FROM runs').fetchone()),dict(db.execute('SELECT * FROM brokers').fetchone())
 def test_terminal_log_recovers_one_receipt_without_new_run(self):
  self.log.write_text('\n'.join(json.dumps(x) for x in [{'type':'thread.started','thread_id':'native-session'},{'type':'item.completed','item':{'type':'agent_message','text':'RECOVERED complete result with enough useful text to meet the existing minimum length criterion.'}},{'type':'turn.completed'}]))
  with patch('kel.runner.process_identity',return_value=None):
   result=monitor(self.s,self.r['id']);monitor(self.s,self.r['id'])
  self.assertEqual(result['outcome'],'SUCCESS');self.s.consume();self.s.verify(self.j,'document');self.assertEqual(self.s.assess(self.j),'VERIFIED')
  with contextlib.closing(self.s.connect()) as db:
   self.assertEqual(db.execute('SELECT count(*) FROM runs').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT count(*) FROM inbox').fetchone()[0],1)
 def test_partial_agent_message_is_not_a_complete_result(self):
  self.log.write_text(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'RECOVERED partial'}}))
  with patch('kel.runner.process_identity',return_value=None):result=monitor(self.s,self.r['id'])
  self.assertEqual(result['outcome'],'FAILED');self.s.consume();self.assertEqual(self.s.get(self.j)['milestones']['document']['state'],'NEEDS_REPAIR')
 def test_live_child_is_observed_not_replayed(self):
  run,row=self.rows()
  with patch('kel.runner.process_identity',return_value='old-child'):self.assertEqual(recover_readonly_result(self.s,run,row),'LIVE')
 def test_unknown_writer_never_uses_leaf_recovery(self):
  run,row=self.rows();row['provider']='codex-code'
  self.assertIsNone(recover_readonly_result(self.s,run,row))
 def test_cancellation_does_not_publish_recovered_result(self):
  self.s.control(self.j,'pause')
  with patch('kel.runner.process_identity',return_value=None):monitor(self.s,self.r['id'])
  self.assertEqual(self.s.get(self.j)['state'],'PAUSED')
  with contextlib.closing(self.s.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM inbox').fetchone()[0],0)
 def test_process_handle_fences_identity_before_termination(self):
  p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
  try:
   identity=process_identity(p.pid);self.assertIsNotNone(identity)
   self.assertFalse(terminate_known_process(p.pid,'wrong-identity'));self.assertIsNone(p.poll())
   self.assertTrue(terminate_known_process(p.pid,identity));p.wait(timeout=5)
  finally:
   if p.poll() is None:p.kill();p.wait()
 def test_cancel_reaches_surviving_readonly_child(self):
  p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
  try:
   identity=process_identity(p.pid)
   with self.s.transaction() as db:db.execute('UPDATE native_processes SET pid=?,identity=?',(p.pid,identity))
   self.s.control(self.j,'pause');run,row=self.rows()
   self.assertEqual(recover_readonly_result(self.s,run,row),'LIVE');p.wait(timeout=5)
   monitor(self.s,self.r['id']);self.assertEqual(self.s.get(self.j)['state'],'PAUSED')
  finally:
   if p.poll() is None:p.kill();p.wait()
