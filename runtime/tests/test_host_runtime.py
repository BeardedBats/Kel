import unittest,os,subprocess,sys,time
from unittest.mock import patch
from kel.host_runtime import host_command,HostConnection
from kel.appserver import CodexConnection
from kel.core import PolicyError

class NativeHostTests(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','Windows process groups')
 def test_transport_death_stops_descendant_process(self):
  from kel.runner import process_identity
  code='from kel.windows_job import contain_current_process;import subprocess,sys,time;handle=contain_current_process();p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);print(p.pid,flush=True);time.sleep(60)'
  parent=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   pid=int(parent.stdout.readline());self.assertIsNotNone(process_identity(pid))
   parent.kill();parent.wait(timeout=5)
   end=time.monotonic()+5
   while process_identity(pid) and time.monotonic()<end:time.sleep(.05)
   self.assertIsNone(process_identity(pid))
  finally:
   if parent.poll() is None:parent.kill();parent.wait(timeout=5)
   parent.stdout.close()
 def test_executable_preserves_arguments(self):
  with patch('kel.host_runtime.shutil.which',return_value='C:/Windows/powershell.exe'):
   self.assertEqual(host_command(['powershell','-Command','Write-Output "hello & world"']),['C:/Windows/powershell.exe','-Command','Write-Output "hello & world"'])
 def test_batch_argument_cannot_expand_commands(self):
  with patch('kel.host_runtime.shutil.which',return_value='C:/npm.cmd'):
   with self.assertRaises(PolicyError):host_command(['npm','test & whoami'])
   self.assertIn('"C:/npm.cmd" "test"',host_command(['npm','test']))
 @unittest.skipUnless(os.name=='nt','Windows batch invocation')
 def test_real_batch_file_preserves_spaced_argument(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as folder:
   script=Path(folder)/'test command.cmd';script.write_text('@echo off\necho %~1\n')
   result=subprocess.run(host_command([str(script),'two words']),capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'two words')
 def test_full_access_is_applied_to_native_session(self):
  c=object.__new__(HostConnection);c.provider='codex'
  with patch.object(CodexConnection,'call',return_value={}) as rpc:
   c.call('thread/resume',{'threadId':'id','sandbox':'workspace-write','approvalPolicy':'on-request'})
   p=rpc.call_args.args[1]
   self.assertEqual(p['sandbox'],'danger-full-access');self.assertEqual(p['approvalPolicy'],'never')
 def test_full_access_applies_to_turn(self):
  c=object.__new__(HostConnection);c.provider='codex'
  with patch.object(CodexConnection,'call',return_value={}) as rpc:
   c.call('turn/start',{'threadId':'id','input':[]})
   self.assertEqual(rpc.call_args.args[1]['sandboxPolicy'],{'type':'dangerFullAccess'})
