"""Detached worker brokers survive conversation/controller restarts.

Each broker owns one run, renews its lease, and commits one durable inbox result.
The controller adopts the same process; it never replays an unconfirmed writer.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from .core import Store, PolicyError, encode
from .instance_lock import InstanceLock


def process_identity(pid):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
        k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        k.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
        k.CloseHandle.argtypes=[wintypes.HANDLE]
        h=k.OpenProcess(0x1000,False,pid)
        if not h:return None
        try:
            exitcode=wintypes.DWORD()
            if not k.GetExitCodeProcess(h,ctypes.byref(exitcode)) or exitcode.value!=259:return None
            values=[wintypes.FILETIME() for _ in range(4)]
            if not k.GetProcessTimes(h,*[ctypes.byref(v) for v in values]):return None
            return str((values[0].dwHighDateTime<<32)+values[0].dwLowDateTime)
        finally:k.CloseHandle(h)
    try:return Path(f'/proc/{pid}/stat').read_text().split()[21]
    except OSError:return None


def init(store):
    with contextlib.closing(store.connect()) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS brokers(run_id TEXT PRIMARY KEY,epoch TEXT,
            provider TEXT,prompt TEXT,session_id TEXT,options TEXT,pid INTEGER,identity TEXT,
            state TEXT,heartbeat REAL,result TEXT)''')
        db.execute('CREATE TABLE IF NOT EXISTS native_processes(run_id TEXT PRIMARY KEY,pid INTEGER,identity TEXT,stdout_path TEXT,deadline REAL)')


def terminate_known_process(pid,identity):
    """Terminate through a handle bound to the recorded process, never a reused PID."""
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
        k.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
        k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];k.CloseHandle.argtypes=[wintypes.HANDLE]
        h=k.OpenProcess(0x1000|0x1,False,pid)
        if not h:return False
        try:
            times=[wintypes.FILETIME() for _ in range(4)]
            if not k.GetProcessTimes(h,*[ctypes.byref(t) for t in times]):return False
            actual=str((times[0].dwHighDateTime<<32)+times[0].dwLowDateTime)
            return actual==identity and bool(k.TerminateProcess(h,1))
        finally:k.CloseHandle(h)
    import signal
    if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):return False
    try:
        fd=os.pidfd_open(pid)
        try:
            if process_identity(pid)!=identity:return False
            signal.pidfd_send_signal(fd,signal.SIGTERM);return True
        finally:os.close(fd)
    except OSError:return False


def recover_readonly_result(store,run,row):
    """Recover only tool-disabled leaf output after the recorded child exits."""
    if row['provider']=='internal':
        return {'outcome':'FAILED','error':'Read-only model broker exited before saving its answer; retry the bounded request.'}
    if row['provider'] not in ('codex','claude'):return None
    with contextlib.closing(store.connect()) as db:
        child=db.execute('SELECT * FROM native_processes WHERE run_id=?',(run['id'],)).fetchone()
    if not child or not child['identity']:return None
    if process_identity(child['pid'])==child['identity']:
        if run['state']=='CANCEL_REQUESTED' or time.time()>child['deadline']:
            if not terminate_known_process(child['pid'],child['identity']):return None
        return 'LIVE'
    path=Path(child['stdout_path']).resolve()
    if not path.is_relative_to((store.root/'native-logs').resolve()):return None
    result={'outcome':'FAILED','error':'Native read-only worker exited before a complete result; retry from saved context.'}
    if path.is_file() and path.stat().st_size<=4_000_000:
        output=path.read_text(encoding='utf-8',errors='replace')
        try:
            if row['provider']=='claude':
                record=json.loads(output);terminal=record.get('type')=='result' and record.get('subtype')=='success'
            else:
                records=[json.loads(line) for line in output.splitlines() if line.strip()]
                terminal=bool(records) and records[-1].get('type')=='turn.completed'
            if terminal:
                from .native import NativeAdapter
                result=NativeAdapter(row['provider'],store.root/'workspaces'/row['provider'],store.root/'native-logs').parse(output,row['session_id'])
                result['recovered_from_native_log']=True
        except (ValueError,TypeError,AttributeError):pass
    return result


class DurableAdapter:
    def __init__(self,store,provider,capabilities=None,options=None):
        self.store,self.provider=store,provider
        self.capabilities=set(capabilities or {'text'})
        self.options=options or {}
        init(store)

    def execute(self,prompt,run_id=None,session_id=None,cancel=None):
        with self.store.transaction() as db:
            run=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
            if not run or run['state']!='RUNNING':raise PolicyError('Run is no longer active')
            db.execute('INSERT INTO brokers VALUES(?,?,?,?,?,?,NULL,NULL,?,?,NULL)',
                (run_id,run['epoch'],self.provider,prompt,session_id,encode(self.options),'STARTING',time.time()))
        folder=self.store.root/'broker-logs';folder.mkdir(exist_ok=True)
        with (folder/(run_id+'.log')).open('ab') as log:
            flags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)
            argv=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-X','utf8','-m','kel.runner']
            process=subprocess.Popen(argv+['--data',str(self.store.root),'--run',run_id],
                cwd=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1],stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,
                start_new_session=os.name!='nt')
            identity=process_identity(process.pid)
            with self.store.transaction() as db:
                db.execute('UPDATE brokers SET pid=?,identity=? WHERE run_id=? AND pid IS NULL',(process.pid,identity,run_id))
        return monitor(self.store,run_id,cancel)


def monitor(store,run_id,cancel=None):
    while True:
        with contextlib.closing(store.connect()) as db:
            row=db.execute('SELECT * FROM brokers WHERE run_id=?',(run_id,)).fetchone()
            run=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        if row['result']:return json.loads(row['result'])
        if run['state']=='ORPHANED':
            return {'outcome':'FAILED','uncertain':True,'error':'Run was fenced by durable recovery; monitor stopped.'}
        with contextlib.closing(store.connect()) as db:
            receipt=db.execute('SELECT payload FROM inbox WHERE run_id=? AND epoch=? ORDER BY rowid DESC LIMIT 1',(run_id,row['epoch'])).fetchone()
        if receipt:return json.loads(receipt['payload'])
        if row['pid'] and row['identity'] and process_identity(row['pid'])!=row['identity']:
            if row['provider'] in ('codex-code','claude-code'):
                from .coding import recover_checked_code,recover_pending_checks
                from .coding_transport import host_alive
                if host_alive(store,run_id):
                    if restart_checks_broker(store,run,row):
                        time.sleep(.2);continue
                recovered=recover_checked_code(store,run,row)
                if recovered is None:recovered=recover_pending_checks(store,run)
                if recovered=='RESUME_CHECKS':
                    if restart_checks_broker(store,run,row):
                        time.sleep(.2);continue
                    recovered=None
            else:recovered=recover_readonly_result(store,run,row)
            if recovered=='LIVE':
                time.sleep(.2);continue
            if isinstance(recovered,dict):
                if run['state']=='CANCEL_REQUESTED':store.acknowledge_stop(run_id,row['epoch'])
                elif run['state']=='RUNNING':store.enqueue_result(run_id+':result',run_id,row['epoch'],recovered)
                with store.transaction() as db:
                    db.execute("UPDATE brokers SET result=?,state='RECOVERED',heartbeat=? WHERE run_id=?",(encode(recovered),time.time(),run_id))
                return recovered
            if row['provider'] in ('codex-code','claude-code') and recover_isolated_loss(store,run_id):
                return {'outcome':'FAILED','isolated_copy_discarded':True,'error':'Abandoned isolated work was stopped; replacement work is bounded by the same contract.'}
            # Preserve the same native session and workspace for reconciliation. Do not retry effects.
            with store.transaction() as db:
                job=store._get(db,run['job_id'])
                if run['state'] in ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED'):
                    db.execute("UPDATE runs SET state='ORPHANED',reservation=0 WHERE id=?",(run_id,))
                    job['reserved']-=run['reservation'];job['spent']+=1
                    job['milestones'][run['milestone_id']].update(state='UNCERTAIN',error='Worker broker exited without a receipt')
                    job.update(state='WAITING_RESOURCE',verdict='UNCERTAIN')
                    store._save(db,job,'broker.lost',{'run_id':run_id,'native_session':run['native_session']})
            return {'outcome':'FAILED','error':'Worker receipt missing; native reconciliation required','uncertain':True}
        if not row['pid'] and time.time()-row['heartbeat']>20:
            raise PolicyError('Worker launch has no process receipt; refusing duplicate launch')
        time.sleep(.2)


def restart_checks_broker(store,run,row):
    """Launch one replacement broker for the same run, only after reconciliation."""
    with store.transaction() as db:
        options=json.loads(row['options'])
        attempts=options.get('_checks_restarts',0)
        if attempts>=2:return False
        options['_checks_restarts']=attempts+1
        changed=db.execute("UPDATE brokers SET pid=NULL,identity=NULL,state='STARTING',heartbeat=?,options=? WHERE run_id=? AND pid=? AND identity=? AND result IS NULL",
            (time.time(),encode(options),run['id'],row['pid'],row['identity'])).rowcount
    if not changed:return True
    folder=store.root/'broker-logs';folder.mkdir(exist_ok=True)
    with (folder/(run['id']+'.log')).open('ab') as log:
        argv=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-X','utf8','-m','kel.runner']
        process=subprocess.Popen(argv+['--data',str(store.root),'--run',run['id']],
            cwd=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1],
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),
            start_new_session=os.name!='nt')
        identity=process_identity(process.pid)
        with store.transaction() as db:
            db.execute('UPDATE brokers SET pid=?,identity=? WHERE run_id=? AND pid IS NULL',(process.pid,identity,run['id']))
    return True


class RunCancellation:
    def __init__(self,store,run_id,epoch):self.store,self.run_id,self.epoch=store,run_id,epoch
    def is_set(self):
        with contextlib.closing(self.store.connect()) as db:row=db.execute('SELECT epoch,state FROM runs WHERE id=?',(self.run_id,)).fetchone()
        return not row or row['epoch']!=self.epoch or row['state'] not in ('RUNNING','WAITING_APPROVAL')
    def wait(self,seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if self.is_set():return True
            time.sleep(min(.1,max(0,deadline-time.monotonic())))
        return self.is_set()


def run_broker(store,run_id):
    init(store)
    lockdir=store.root/'broker-locks'/run_id;lockdir.mkdir(parents=True,exist_ok=True)
    lock=InstanceLock(lockdir)
    stop=threading.Event()
    try:
        with store.transaction() as db:
            row=dict(db.execute('SELECT * FROM brokers WHERE run_id=?',(run_id,)).fetchone())
            if row['result']:return
            db.execute("UPDATE brokers SET pid=?,identity=?,state='RUNNING',heartbeat=? WHERE run_id=?",
                (os.getpid(),process_identity(os.getpid()),time.time(),run_id))
        cancel=RunCancellation(store,run_id,row['epoch'])
        def heartbeat():
            while not stop.wait(2):
                with store.transaction() as db:
                    db.execute('UPDATE brokers SET heartbeat=? WHERE run_id=?',(time.time(),run_id))
                    db.execute("UPDATE runs SET expires=? WHERE id=? AND epoch=? AND state IN ('RUNNING','WAITING_APPROVAL')",(time.time()+30,run_id,row['epoch']))
        thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
        try:
            provider=row['provider'];options=json.loads(row['options'])
            if provider in ('codex-code','claude-code'):
                from .coding import CodingAdapter
                adapter=CodingAdapter(store)
            elif provider=='research':
                from .research import ResearchAdapter
                adapter=ResearchAdapter(store,**options)
            elif provider=='internal':
                from .internal import InternalAdapter
                adapter=InternalAdapter(**options)
            elif provider in ('codex','claude'):
                from .native import NativeAdapter
                adapter=NativeAdapter(provider,store.root/'workspaces'/provider,store.root/'native-logs',timeout=180)
            else:raise PolicyError('Unsupported durable provider')
            kwargs={}
            if provider in ('codex','claude'):
                def observe(pid,path,timeout):
                    identity=process_identity(pid)
                    if not identity:raise PolicyError('Native process identity unavailable; no request was sent')
                    with store.transaction() as db:
                        db.execute('INSERT INTO native_processes VALUES(?,?,?,?,?)',(run_id,pid,identity,str(path),time.time()+timeout))
                kwargs['process_observer']=observe
            if provider=='internal':
                with contextlib.closing(store.connect()) as db:
                    job_id=db.execute('SELECT job_id FROM runs WHERE id=?',(run_id,)).fetchone()['job_id']
                files=store.get(job_id)['contract'].get('context',{}).get('files',[])
                images=[]
                import base64
                from .core import digest
                for f in files:
                    if not f.get('image_path'):continue
                    p=(store.root/f['image_path']).resolve()
                    if not p.is_relative_to(store.root/'attachments'):raise PolicyError('Image escaped attachment storage')
                    raw=p.read_bytes()
                    if digest(raw)!=f['sha256']:raise PolicyError('Image changed after handoff')
                    images.append({'mime':f['mime'],'data':base64.b64encode(raw).decode()})
                if images:kwargs['images']=images
            result=adapter.execute(row['prompt'],run_id=run_id,session_id=row['session_id'],cancel=cancel,**kwargs)
        except Exception as exc:result={'outcome':'FAILED','error':type(exc).__name__+': '+str(exc),'uncertain':row['provider'] in ('codex-code','claude-code')}
        if row['provider'] in ('codex-code','claude-code') and result.get('uncertain'):
            fence_uncertain_code(store,run_id,result.get('error') or 'Native execution outcome is unknown')
        elif cancel.is_set():store.acknowledge_stop(run_id,row['epoch'])
        else:store.enqueue_result(run_id+':result',run_id,row['epoch'],result)
        store.provider_outcome(row['provider'],result)
        with store.transaction() as db:
            db.execute("UPDATE brokers SET result=?,state='EXITED',heartbeat=? WHERE run_id=?",(encode(result),time.time(),run_id))
    finally:
        stop.set()
        if 'thread' in locals():thread.join(timeout=3)
        lock.close()


def fence_uncertain_code(store,run_id,reason):
    """Unknown native effects cannot become an ordinary retry or a stop receipt."""
    if recover_isolated_loss(store,run_id):return
    with store.transaction() as db:
        run=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        if not run or run['state'] not in ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED'):return
        job=store._get(db,run['job_id'])
        db.execute("UPDATE runs SET state='ORPHANED',reservation=0 WHERE id=?",(run_id,))
        job['reserved']-=run['reservation'];job['spent']+=1
        job['milestones'][run['milestone_id']].update(state='UNCERTAIN',error='The worker connection was interrupted. Kel preserved the project copy and stopped automatic retries because a command may already have run. Details: '+str(reason))
        job.update(state='WAITING_RESOURCE',verdict='UNCERTAIN')
        store._save(db,job,'coding.reconciliation_required',{'run_id':run_id,'reason':str(reason)})


def recover_isolated_loss(store,run_id):
    """Discard only an enforced sandbox with no expanded grants, after killing its cgroup."""
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='isolated_runs'").fetchone():return False
        isolated=db.execute('SELECT * FROM isolated_runs WHERE run_id=?',(run_id,)).fetchone()
        run=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        if not isolated or not run or run['state'] not in ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED'):return False
        if db.execute("SELECT 1 FROM approvals WHERE run_id=? AND status='APPROVED'",(run_id,)).fetchone():return False
        job=store._get(db,run['job_id'])
        if job['contract'].get('kind')!='coding':return False
        if job['contract'].get('runtime')=='native-host':return False
        workspace=db.execute('SELECT path FROM code_workspaces WHERE job_id=?',(run['job_id'],)).fetchone()
        if not workspace or not Path(workspace['path']).resolve().is_relative_to(store.root/'repositories'):return False
    try:
        from .wsl_runtime import stop_group
        if not stop_group(isolated['group_id']):return False
    except Exception:return False
    if run['state']=='CANCEL_REQUESTED':
        store.acknowledge_stop(run_id,run['epoch']);return True
    with store.transaction() as db:
        current=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        if current['state'] not in ('RUNNING','WAITING_APPROVAL'):return False
        job=store._get(db,run['job_id']);milestone=job['milestones'][run['milestone_id']]
        db.execute("UPDATE runs SET state='ORPHANED',reservation=0 WHERE id=?",(run_id,))
        job['reserved']-=current['reservation'];job['spent']+=1
        retry=milestone['attempts']<4 and job['budget']-job['spent']-job['reserved']>=2
        milestone.update(state='NEEDS_REPAIR' if retry else 'UNCERTAIN',artifact=None,checks=[],
            error='The isolated worker lost contact. Its entire process group has stopped. The abandoned copy is preserved; a fresh copy can safely retry without replaying changes to your original project.')
        job.update(state='READY' if retry else 'WAITING_RESOURCE',verdict='UNCERTAIN')
        store._save(db,job,'isolated_work.discarded',{'run_id':run_id,'group':isolated['group_id'],'remote':isolated['remote'],'retry':retry})
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',required=True);parser.add_argument('--run',required=True)
    args=parser.parse_args();run_broker(Store(args.data),args.run)
