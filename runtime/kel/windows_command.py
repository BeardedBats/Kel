"""Own one Windows command tree's lifetime, without changing its permissions."""
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import threading
import time

class START(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('reserved',wintypes.LPWSTR),('desktop',wintypes.LPWSTR),
        ('title',wintypes.LPWSTR),*[(name,wintypes.DWORD) for name in
        ('x','y','cx','cy','chars_x','chars_y','fill','flags')],('show',wintypes.WORD),
        ('reserved_size',wintypes.WORD),('reserved_bytes',ctypes.POINTER(ctypes.c_byte)),
        ('stdin',wintypes.HANDLE),('stdout',wintypes.HANDLE),('stderr',wintypes.HANDLE)]
class STARTEX(ctypes.Structure):
    _fields_=[('startup',START),('attributes',ctypes.c_void_p)]
class INFO(ctypes.Structure):
    _fields_=[('process',wintypes.HANDLE),('thread',wintypes.HANDLE),('pid',wintypes.DWORD),('tid',wintypes.DWORD)]

class WindowsAPI:
    def __init__(self):
        import msvcrt
        self.msvcrt=msvcrt
        self.k=k=ctypes.WinDLL('kernel32',use_last_error=True)
        signatures={
            'CreateProcessW':([wintypes.LPCWSTR,wintypes.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,
                wintypes.BOOL,wintypes.DWORD,ctypes.c_void_p,wintypes.LPCWSTR,ctypes.c_void_p,ctypes.POINTER(INFO)],wintypes.BOOL),
            'InitializeProcThreadAttributeList':([ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.c_size_t)],wintypes.BOOL),
            'UpdateProcThreadAttribute':([ctypes.c_void_p,wintypes.DWORD,ctypes.c_size_t,ctypes.c_void_p,
                ctypes.c_size_t,ctypes.c_void_p,ctypes.c_void_p],wintypes.BOOL),
            'DeleteProcThreadAttributeList':([ctypes.c_void_p],None),
            'GetCurrentProcess':([],wintypes.HANDLE),
            'DuplicateHandle':([wintypes.HANDLE,wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.HANDLE),
                wintypes.DWORD,wintypes.BOOL,wintypes.DWORD],wintypes.BOOL),
            'AssignProcessToJobObject':([wintypes.HANDLE,wintypes.HANDLE],wintypes.BOOL),
            'ResumeThread':([wintypes.HANDLE],wintypes.DWORD),
            'TerminateProcess':([wintypes.HANDLE,wintypes.UINT],wintypes.BOOL),
            'TerminateJobObject':([wintypes.HANDLE,wintypes.UINT],wintypes.BOOL),
            'WaitForSingleObject':([wintypes.HANDLE,wintypes.DWORD],wintypes.DWORD),
            'GetExitCodeProcess':([wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)],wintypes.BOOL),
            'QueryInformationJobObject':([wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p],wintypes.BOOL),
            'CloseHandle':([wintypes.HANDLE],wintypes.BOOL)}
        for name,(args,result) in signatures.items():
            fn=getattr(k,name);fn.argtypes=args;fn.restype=result

    def check(self,value):
        if not value:raise ctypes.WinError(ctypes.get_last_error())
    def create_job(self):
        from .windows_job import create_command_job
        return create_command_job(self.k)
    def create_suspended(self,argv,cwd,stdout,stderr,env):
        handles=[];initialized=False;created=None
        with open(os.devnull,'rb') as stdin:
            try:
                for stream in (stdin,stdout,stderr):
                    handle=wintypes.HANDLE();current=self.k.GetCurrentProcess()
                    self.check(self.k.DuplicateHandle(current,wintypes.HANDLE(self.msvcrt.get_osfhandle(stream.fileno())),
                        current,ctypes.byref(handle),0,True,2))
                    handles.append(handle.value)
                size=ctypes.c_size_t()
                self.k.InitializeProcThreadAttributeList(None,1,0,ctypes.byref(size))
                if not size.value:raise ctypes.WinError(ctypes.get_last_error())
                attrs=ctypes.create_string_buffer(size.value)
                self.check(self.k.InitializeProcThreadAttributeList(attrs,1,0,ctypes.byref(size)))
                initialized=True
                allowed=(wintypes.HANDLE*3)(*handles)
                # Only duplicated stdio handles may reach the child, never the private job.
                self.check(self.k.UpdateProcThreadAttribute(attrs,0,0x20002,ctypes.byref(allowed),ctypes.sizeof(allowed),None,None))
                start=STARTEX();start.startup.cb=ctypes.sizeof(start);start.startup.flags=0x100
                start.startup.stdin,start.startup.stdout,start.startup.stderr=handles
                start.attributes=ctypes.cast(attrs,ctypes.c_void_p)
                info=INFO();line=ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
                environment=ctypes.create_unicode_buffer('\0'.join(key+'='+value for key,value in
                    sorted(env.items(),key=lambda pair:pair[0].upper()))+'\0\0')
                # Suspended, hidden, Unicode environment, explicit handle allowlist.
                self.check(self.k.CreateProcessW(argv[0],line,None,None,True,
                    0x4|0x08000000|0x400|0x80000,environment,str(cwd),ctypes.byref(start),ctypes.byref(info)))
                created=(info.process,info.thread,info.pid)
                return created
            finally:
                primary=sys.exc_info()[1]
                cleanup_error=None
                if initialized:
                    try:self.k.DeleteProcThreadAttributeList(attrs)
                    except BaseException as error:cleanup_error=error
                for handle in handles:
                    try:self.close(handle)
                    except BaseException as error:
                        if cleanup_error is None:cleanup_error=error
                if cleanup_error is not None:
                    # A return cannot transfer child ownership if local cleanup raises.
                    if created is not None:
                        process,thread,_=created
                        try:self.terminate_process(process)
                        except BaseException:pass
                        for handle in (thread,process):
                            try:self.close(handle)
                            except BaseException:pass
                    if primary is None:raise cleanup_error
    def assign(self,job,process):self.check(self.k.AssignProcessToJobObject(job,process))
    def resume(self,thread):
        if self.k.ResumeThread(thread)==0xffffffff:raise ctypes.WinError(ctypes.get_last_error())
    def terminate_process(self,process):self.check(self.k.TerminateProcess(process,1))
    def terminate_job(self,job):self.check(self.k.TerminateJobObject(job,1))
    def close(self,handle):self.check(self.k.CloseHandle(handle))
    def poll(self,process):
        status=self.k.WaitForSingleObject(process,0)
        if status==0x102:return None
        if status!=0:raise ctypes.WinError(ctypes.get_last_error())
        code=wintypes.DWORD();self.check(self.k.GetExitCodeProcess(process,ctypes.byref(code)))
        return code.value
    def wait_group(self,job,timeout=5):
        class ACCOUNT(ctypes.Structure):
            _fields_=[(name,ctypes.c_int64) for name in ('user','kernel','period_user','period_kernel')]+[
                (name,wintypes.DWORD) for name in ('faults','total','active','terminated')]
        deadline=time.monotonic()+timeout
        while True:
            info=ACCOUNT()
            self.check(self.k.QueryInformationJobObject(job,1,ctypes.byref(info),ctypes.sizeof(info),None))
            if info.active==0:return
            if time.monotonic()>=deadline:raise subprocess.TimeoutExpired('trusted command tree',timeout)
            time.sleep(.01)

class WindowsCommand:
    _kel_lifetime_group=True
    def __init__(self,api,job,process,pid):
        self._api,self._job,self._process=api,job,process
        self.pid,self.returncode=pid,None
        self._lock=threading.RLock()
    def poll(self):
        with self._lock:
            if self.returncode is None:self.returncode=self._api.poll(self._process)
            return self.returncode
    def wait(self,timeout=None):
        deadline=None if timeout is None else time.monotonic()+timeout
        while self.poll() is None:
            if deadline is not None and time.monotonic()>=deadline:
                raise subprocess.TimeoutExpired('trusted command',timeout)
            time.sleep(.01)
        return self.returncode
    def kill(self):
        with self._lock:
            # Descendants may remain even after the launcher exited.
            if self._job is not None:self._api.terminate_job(self._job)
    def close_tree(self):
        with self._lock:
            try:
                if self._job is not None:
                    job=self._job
                    try:
                        self._api.terminate_job(job)
                        self._api.wait_group(job)
                    finally:
                        self._job=None
                        self._api.close(job)
            finally:
                if self._process is not None:
                    process=self._process
                    try:self.wait(timeout=5)
                    finally:
                        self._process=None
                        self._api.close(process)

def launch_windows_command(argv,*,cwd,stdout,stderr,env,_api=None):
    """Attach the still-suspended launcher before command code can execute."""
    if not isinstance(argv,(list,tuple)) or not argv or not all(
            isinstance(arg,str) and arg and '\0' not in arg for arg in argv):
        raise OSError('Invalid trusted command arguments')
    api=_api or WindowsAPI();job=process=thread=None;assigned=False
    try:
        job=api.create_job()
        process,thread,pid=api.create_suspended(argv,cwd,stdout,stderr,env)
        api.assign(job,process);assigned=True
        api.resume(thread);api.close(thread);thread=None
        return WindowsCommand(api,job,process,pid)
    except BaseException:
        try:
            if process is not None:
                try:
                    if assigned:api.terminate_job(job)
                    else:api.terminate_process(process)
                finally:
                    try:
                        if thread is not None:api.close(thread)
                    finally:api.close(process)
        finally:
            if job is not None:api.close(job)
        raise
