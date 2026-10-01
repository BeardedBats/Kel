import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

from kel.core import PolicyError
from kel.host_runtime import HostConnection
from kel.windows_command import WindowsAPI,WindowsCommand,launch_windows_command
from kel.windows_job import create_command_job


class FakeAPI:
    def __init__(self,fail=None):self.events=[];self.fail=fail;self.code=0
    def record(self,name,*values):
        self.events.append((name,*values))
        if self.fail==name:raise OSError(name+' fixture failure')
    def create_job(self):self.record('job');return 11
    def create_suspended(self,*args):self.record('suspended',args[0]);return 21,22,23
    def assign(self,*args):self.record('assign',*args)
    def resume(self,*args):self.record('resume',*args)
    def close(self,*args):self.record('close',*args)
    def terminate_process(self,*args):self.record('terminate_process',*args)
    def terminate_job(self,*args):self.record('terminate_job',*args)
    def wait_group(self,*args):self.record('wait_group',*args)
    def poll(self,*args):return self.code


class CommandGroupTests(unittest.TestCase):
    def launch(self,api):
        return launch_windows_command(['fixture.exe','literal & argument'],cwd='owned',
            stdout=None,stderr=None,env={},_api=api)

    def test_attachment_precedes_execution_and_normal_exit_closes_entire_tree(self):
        api=FakeAPI();process=self.launch(api)
        self.assertEqual([event[0] for event in api.events],['job','suspended','assign','resume','close'])
        self.assertEqual(api.events[1][1],['fixture.exe','literal & argument'])
        self.assertEqual(process.poll(),0)
        process.close_tree();process.close_tree()
        self.assertIn(('terminate_job',11),api.events)
        self.assertIn(('wait_group',11),api.events)
        self.assertEqual(api.events.count(('close',11)),1)
        self.assertEqual(api.events.count(('close',21)),1)

    def test_creation_and_attachment_failures_never_resume_or_retry(self):
        for failure in ('job','suspended','assign','resume'):
            with self.subTest(failure=failure):
                api=FakeAPI(failure)
                with self.assertRaises(OSError):self.launch(api)
                self.assertEqual(sum(event[0]=='suspended' for event in api.events),int(failure!='job'))
                if failure in ('job','suspended','assign'):
                    self.assertNotIn('resume',[event[0] for event in api.events])
                if failure=='assign':self.assertIn(('terminate_process',21),api.events)
                if failure=='resume':self.assertIn(('terminate_job',11),api.events)
                if failure!='job':self.assertIn(('close',11),api.events)

    def test_stop_terminates_group_even_when_launcher_exited(self):
        api=FakeAPI();process=self.launch(api);self.assertEqual(process.poll(),0)
        connection=object.__new__(HostConnection)
        with patch('kel.host_runtime.subprocess.run') as taskkill:
            connection._stop_test_process(process)
        self.assertIn(('terminate_job',11),api.events);taskkill.assert_not_called()
        process.close_tree()

    def test_private_job_has_only_kill_on_close_flag(self):
        kernel=Mock();kernel.CreateJobObjectW.return_value=99
        flags=[]
        def setup(handle,kind,pointer,size):
            # flags follows two 64-bit durations in BASIC.
            flags.append(ctypes.c_uint32.from_address(ctypes.cast(pointer,ctypes.c_void_p).value+16).value)
            return True
        kernel.SetInformationJobObject.side_effect=setup
        self.assertEqual(create_command_job(kernel),99)
        kernel.CreateJobObjectW.assert_called_once_with(None,None)
        self.assertEqual(flags,[0x2000])

    def test_invalid_argv_never_creates_group(self):
        api=FakeAPI()
        with self.assertRaises(OSError):launch_windows_command('cmd /c data',cwd='owned',stdout=None,stderr=None,env={},_api=api)
        self.assertEqual(api.events,[])

    def test_group_failure_still_closes_process_handle_and_preserves_error(self):
        for failure in ('terminate_job','wait_group','poll'):
            with self.subTest(failure=failure):
                api=FakeAPI();process=self.launch(api)
                if failure=='poll':api.poll=Mock(side_effect=OSError('poll fixture failure'))
                else:api.fail=failure
                with self.assertRaisesRegex(OSError,failure+' fixture failure'):process.close_tree()
                self.assertIn(('close',11),api.events);self.assertIn(('close',21),api.events)
                self.assertIsNone(process._job);self.assertIsNone(process._process)

    def test_stdio_cleanup_failure_reclaims_unreturned_suspended_child(self):
        api=object.__new__(WindowsAPI);api.k=Mock();api.msvcrt=Mock()
        api.msvcrt.get_osfhandle.return_value=7
        next_handle=iter((101,102,103))
        def duplicate(*args):args[3]._obj.value=next(next_handle);return True
        def attributes(*args):args[3]._obj.value=32;return True
        def create(*args):
            info=args[-1]._obj;info.process=21;info.thread=22;info.pid=23;return True
        api.k.DuplicateHandle.side_effect=duplicate
        api.k.InitializeProcThreadAttributeList.side_effect=attributes
        api.k.CreateProcessW.side_effect=create
        closed=[]
        def close(handle):
            closed.append(handle)
            if handle==101:raise OSError('stdio cleanup fixture failure')
        api.close=Mock(side_effect=close);api.terminate_process=Mock()
        stream=Mock();stream.fileno.return_value=4
        with self.assertRaisesRegex(OSError,'stdio cleanup fixture failure'):
            api.create_suspended(['fixture.exe'],'owned',stream,stream,{})
        api.terminate_process.assert_called_once_with(21)
        self.assertEqual(closed,[101,102,103,22,21])
        api.k.ResumeThread.assert_not_called()


class HostCommandLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        root=Path(self.folder.name)
        c=self.c=object.__new__(HostConnection)
        c.workspace=str(root/'work');Path(c.workspace).mkdir()
        c.logs=root/'engine'/'native-logs'/'test';c.logs.mkdir(parents=True)
        c.engine_root=c.logs.parent.parent;c.temp=root/'temp';c.temp.mkdir()
        c.provider='codex';c.network=False
        self.addCleanup(patch.stopall)
        patch.object(c,'_trusted_test_argv',return_value=(['codex.exe','sandbox','literal'],False)).start()

    def test_success_closes_group_before_result_and_retains_exact_sandbox_argv(self):
        process=Mock(_kel_lifetime_group=True);process.poll.return_value=0;process.returncode=0
        with patch('kel.host_runtime.launch_trusted_command',return_value=process) as launch:
            result=self.c.call('command/exec',{'command':['python','-V']})
        self.assertEqual(launch.call_args.args[0],['codex.exe','sandbox','literal'])
        process.close_tree.assert_called_once();self.assertIsNone(self.c._test_process)
        self.assertEqual(result['_kel_execution']['command_lifetime'],'windows-job-tree')
        self.assertFalse(result['_kel_execution']['complete_read_confinement'])

    def test_launch_failure_has_no_ordinary_process_fallback(self):
        with patch('kel.host_runtime.launch_trusted_command',side_effect=OSError('group refused')) as launch,\
             patch('kel.host_runtime.subprocess.Popen') as ordinary:
            with self.assertRaises(PolicyError):self.c.call('command/exec',{'command':['python','-V']})
        launch.assert_called_once();ordinary.assert_not_called()

    def test_stop_and_output_and_timeout_paths_close_group_and_withhold_result(self):
        for reason in ('stop','output','timeout'):
            with self.subTest(reason=reason):
                self.c._tests_closed=False
                process=Mock(_kel_lifetime_group=True);process.poll.return_value=None
                def launch(*args,**kwargs):
                    if reason=='stop':self.c._tests_closed=True
                    if reason=='output':kwargs['stdout'].write(b'x'*2_000_001);kwargs['stdout'].flush()
                    return process
                clock=patch('kel.host_runtime.time.monotonic',side_effect=[0,200]) if reason=='timeout' else patch('kel.host_runtime.time.monotonic',return_value=0)
                with patch('kel.host_runtime.launch_trusted_command',side_effect=launch) as launched,clock:
                    with self.assertRaises(PolicyError):self.c.call('command/exec',{'command':['python','-V']})
                process.kill.assert_called_once();process.close_tree.assert_called_once()
                self.assertIsNone(self.c._test_process);self.assertEqual(launched.call_count,1)

    def test_normal_completion_group_failure_cannot_produce_passing_receipt(self):
        process=Mock(_kel_lifetime_group=True);process.poll.return_value=0
        process.close_tree.side_effect=OSError('group cleanup refused')
        with patch('kel.host_runtime.launch_trusted_command',return_value=process):
            with self.assertRaises(OSError):self.c.call('command/exec',{'command':['python','-V']})
        self.assertIsNone(self.c._test_process)

    def test_transport_loss_stops_group_without_recording_success(self):
        self.c.process=Mock();self.c.process.poll.side_effect=[None,1]
        process=Mock(_kel_lifetime_group=True);process.poll.return_value=None
        with patch('kel.host_runtime.launch_trusted_command',return_value=process) as launch:
            with self.assertRaisesRegex(PolicyError,'transport ended during'):
                self.c.call('command/exec',{'command':['python','-V']})
        process.kill.assert_called_once();process.close_tree.assert_called_once();launch.assert_called_once()

    def test_dead_transport_refuses_before_launch(self):
        self.c.process=Mock();self.c.process.poll.return_value=1
        with patch('kel.host_runtime.launch_trusted_command') as launch:
            with self.assertRaisesRegex(PolicyError,'transport ended before'):
                self.c.call('command/exec',{'command':['python','-V']})
        launch.assert_not_called()


@unittest.skipUnless(os.name=='nt','Windows lifetime proof')
class SyntheticWindowsTreeTests(unittest.TestCase):
    def test_exited_launcher_cannot_leave_child_and_grandchild(self):
        # One synthetic tree. No model, network, credentials or installed App involved.
        import ctypes
        from ctypes import wintypes
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            child="import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(30)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(30)"
            parent="import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-B','-c',sys.argv[1],sys.argv[2]]); pathlib.Path(sys.argv[3]).write_text(str(p.pid)); end=time.monotonic()+3\nwhile not pathlib.Path(sys.argv[2]).exists() and time.monotonic()<end:time.sleep(.01)"
            handles=[];process=None
            k=ctypes.WinDLL('kernel32',use_last_error=True)
            k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
            k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.WaitForSingleObject.restype=wintypes.DWORD
            k.CloseHandle.argtypes=[wintypes.HANDLE]
            try:
                with (root/'out').open('wb') as stdout,(root/'err').open('wb') as stderr:
                    process=launch_windows_command([sys.executable,'-B','-c',parent,child,str(root/'grand.pid'),str(root/'child.pid')],
                        cwd=root,stdout=stdout,stderr=stderr,env={'SystemRoot':os.environ['SystemRoot'],
                            'TEMP':str(root),'TMP':str(root),'PYTHONDONTWRITEBYTECODE':'1'})
                    self.assertEqual(process.wait(timeout=8),0)
                    for leaf in ('child.pid','grand.pid'):
                        handle=k.OpenProcess(0x100000,False,int((root/leaf).read_text()))
                        self.assertTrue(handle);handles.append(handle)
                        self.assertEqual(k.WaitForSingleObject(handle,0),0x102)
                    process.close_tree()
                    for handle in handles:self.assertEqual(k.WaitForSingleObject(handle,1000),0)
            finally:
                if process is not None:process.close_tree()
                for handle in handles:k.CloseHandle(handle)


if __name__=='__main__':unittest.main()
