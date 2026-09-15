import contextlib,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from kel.core import Store,PolicyError,encode
from kel.engine import compile_document
from kel.runner import init as runner_init,process_identity,fence_uncertain_code
from kel.coding_transport import init,DurableCodingConnection,SavedEvents,host_alive


class CodingTransportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(self.tmp.name);init(self.s);runner_init(self.s)
  self.j=self.s.create(dict(compile_document('Fix code.'),kind='coding'))
  self.run=self.s.claim(self.j,'document',provider='codex-code');self.rid=self.run['id']
  with self.s.transaction() as db:
   db.execute('INSERT INTO coding_hosts VALUES(?,?,?,?,?,?)',(self.rid,self.tmp.name,os.getpid(),process_identity(os.getpid()),'RUNNING',time.time()+60))
  self.c=DurableCodingConnection(self.s,self.rid,self.tmp.name)
 def tearDown(self):self.tmp.cleanup()

 def test_reconnect_returns_same_rpc_receipt_without_dispatch(self):
  params={'command':['python','tests.py']}
  with self.s.transaction() as db:db.execute('INSERT INTO coding_calls VALUES(?,?,?,?,?)',(self.rid,'command/exec',encode(params),'FINISHED',encode({'result':{'exitCode':0}})))
  self.assertEqual(self.c.call('command/exec',params),{'exitCode':0})
  other=DurableCodingConnection(self.s,self.rid,self.tmp.name)
  self.assertEqual(other.call('command/exec',params),{'exitCode':0})
  with contextlib.closing(self.s.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM coding_calls').fetchone()[0],1)

 def test_changed_rpc_action_cannot_reuse_receipt(self):
  with self.s.transaction() as db:db.execute('INSERT INTO coding_calls VALUES(?,?,?,?,?)',(self.rid,'command/exec','{}','FINISHED',encode({'result':{}})))
  with self.assertRaises(PolicyError):self.c.call('command/exec',{'command':['different']})

 def test_unknown_dispatched_call_is_not_requeued_after_host_loss(self):
  with self.s.transaction() as db:
   db.execute('INSERT INTO coding_calls VALUES(?,?,?,?,NULL)',(self.rid,'command/exec','{}','DISPATCHED'))
   db.execute("UPDATE coding_hosts SET state='STOPPED'")
  with self.assertRaises(PolicyError):self.c.call('command/exec',{})
  with contextlib.closing(self.s.connect()) as db:self.assertEqual(db.execute('SELECT state FROM coding_calls').fetchone()[0],'DISPATCHED')

 def test_permission_reply_is_immutable_and_replay_does_not_prompt(self):
  event={'id':'approval-1','method':'item/commandExecution/requestApproval','params':{}}
  done={'method':'turn/completed','params':{'turn':{'status':'completed'}}}
  with self.s.transaction() as db:
   for e in (event,done):db.execute('INSERT INTO coding_events(run_id,event) VALUES(?,?)',(self.rid,encode(e)))
  self.c.send({'id':'approval-1','result':{'decision':'decline'}})
  self.assertEqual(SavedEvents(self.c).get(),done)
  with self.assertRaises(PolicyError):self.c.send({'id':'approval-1','result':{'decision':'accept'}})

 def test_unknown_effect_cannot_become_cancel_ack_or_retry(self):
  self.s.control(self.j,'cancel')
  fence_uncertain_code(self.s,self.rid,'connection lost after dispatch')
  job=self.s.get(self.j)
  self.assertEqual(job['state'],'WAITING_RESOURCE');self.assertEqual(job['verdict'],'UNCERTAIN')
  self.assertEqual(job['milestones']['document']['state'],'UNCERTAIN')
  with contextlib.closing(self.s.connect()) as db:
   self.assertEqual(db.execute('SELECT state FROM runs').fetchone()[0],'ORPHANED')
   self.assertEqual(db.execute('SELECT count(*) FROM publications').fetchone()[0],0)

 def test_host_identity_and_workspace_must_match(self):
  with self.s.transaction() as db:db.execute("UPDATE coding_hosts SET identity='wrong'")
  self.assertFalse(host_alive(self.s,self.rid))
  with self.assertRaises(PolicyError):DurableCodingConnection(self.s,self.rid,Path(self.tmp.name)/'other')

 def test_host_becoming_ready_between_reads_is_not_a_failure(self):
  with patch('kel.coding_transport.host_alive',side_effect=[False,True]):
   connection=DurableCodingConnection(self.s,self.rid,self.tmp.name)
  self.assertEqual(connection.run_id,self.rid)


if __name__=='__main__':unittest.main()
