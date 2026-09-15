"""Durable native RPC transport. A broker may reconnect; dispatched RPCs never replay."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from .appserver import CodexConnection
from .core import Store,PolicyError,encode
from .instance_lock import InstanceLock


def init(store):
    with contextlib.closing(store.connect()) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS coding_hosts(run_id TEXT PRIMARY KEY,workspace TEXT,pid INTEGER,identity TEXT,state TEXT,deadline REAL);
        CREATE TABLE IF NOT EXISTS coding_calls(run_id TEXT,key TEXT,params TEXT,state TEXT,result TEXT,PRIMARY KEY(run_id,key));
        CREATE TABLE IF NOT EXISTS coding_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,event TEXT);
        CREATE TABLE IF NOT EXISTS coding_replies(run_id TEXT,key TEXT,payload TEXT,state TEXT,PRIMARY KEY(run_id,key));
        CREATE TABLE IF NOT EXISTS isolated_runs(run_id TEXT PRIMARY KEY,group_id TEXT,remote TEXT);
        ''')


def host_alive(store,run_id):
    from .runner import process_identity
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='coding_hosts'").fetchone():return False
        row=db.execute('SELECT * FROM coding_hosts WHERE run_id=?',(run_id,)).fetchone()
    return bool(row and row['state']=='RUNNING' and row['identity'] and
                process_identity(row['pid'])==row['identity'] and time.time()<row['deadline'])


class SavedEvents:
    def __init__(self,connection):self.connection=connection;self.cursor=0
    def get(self,timeout=.2):
        end=time.monotonic()+timeout
        while True:
            with contextlib.closing(self.connection.store.connect()) as db:
                row=db.execute('SELECT seq,event FROM coding_events WHERE run_id=? AND seq>? ORDER BY seq LIMIT 1',
                    (self.connection.run_id,self.cursor)).fetchone()
                if row:
                    self.cursor=row['seq'];event=json.loads(row['event'])
                    # An answered native approval must not ask again after reconnect.
                    if 'id' in event and db.execute('SELECT 1 FROM coding_replies WHERE run_id=? AND key=?',
                        (self.connection.run_id,encode(event['id']))).fetchone():continue
                    return event
            if not host_alive(self.connection.store,self.connection.run_id):
                return {'method':'kel/connectionClosed'}
            if time.monotonic()>=end:raise queue.Empty
            time.sleep(.03)


class DurableCodingConnection:
    run=CodexConnection.run
    def __init__(self,store,run_id,workspace):
        self.store,self.run_id=store,run_id
        self.workspace=str(Path(workspace).resolve());init(store)
        with store.transaction() as db:
            row=db.execute('SELECT * FROM coding_hosts WHERE run_id=?',(run_id,)).fetchone()
            if row and row['workspace']!=self.workspace:raise PolicyError('Native workspace changed')
            if not row:db.execute("INSERT INTO coding_hosts VALUES(?,?,NULL,NULL,'STARTING',?)",(run_id,self.workspace,time.time()+420))
        if not row:
            logs=store.root/'native-logs'/run_id;logs.mkdir(parents=True,exist_ok=True)
            argv=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-X','utf8','-m','kel.coding_transport']
            with (logs/'transport.log').open('ab') as log:
                subprocess.Popen(argv+['--data',str(store.root),'--rpc-run',run_id],
                    cwd=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1],
                    stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),
                    start_new_session=os.name!='nt')
        end=time.monotonic()+30
        while not host_alive(store,run_id):
            with contextlib.closing(store.connect()) as db:current=db.execute('SELECT state FROM coding_hosts WHERE run_id=?',(run_id,)).fetchone()
            # RUNNING may have appeared between the liveness read above and this
            # state read. Observe it again instead of treating readiness as failure.
            if current['state'] not in ('STARTING','RUNNING') or time.monotonic()>end:
                raise PolicyError('Native transport unavailable; dispatched work cannot be replayed')
            time.sleep(.05)
        self.events=SavedEvents(self)

    def call(self,method,params,timeout=25):
        # This runtime permits one of each RPC per coding run. A changed action
        # cannot reuse a prior receipt, and an interrupted call retains its identity.
        encoded=encode(params)
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM coding_calls WHERE run_id=? AND key=?',(self.run_id,method)).fetchone()
            if row and row['params']!=encoded:raise PolicyError('Native RPC identity cannot change its parameters')
            if not row:db.execute("INSERT INTO coding_calls VALUES(?,?,?,'QUEUED',NULL)",(self.run_id,method,encoded))
        end=time.monotonic()+timeout
        while True:
            with contextlib.closing(self.store.connect()) as db:row=db.execute('SELECT * FROM coding_calls WHERE run_id=? AND key=?',(self.run_id,method)).fetchone()
            if row['result']:
                reply=json.loads(row['result'])
                if 'error' in reply:raise RuntimeError(reply['error'])
                return reply['result']
            if not host_alive(self.store,self.run_id):raise PolicyError('Native transport lost with an unresolved RPC')
            if time.monotonic()>end:raise TimeoutError('Native RPC still lacks a receipt; do not replay it')
            time.sleep(.04)

    def send(self,message):
        if 'id' not in message:raise PolicyError('Only native request replies are supported')
        key=encode(message['id']);payload=encode(message)
        with self.store.transaction() as db:
            row=db.execute('SELECT payload FROM coding_replies WHERE run_id=? AND key=?',(self.run_id,key)).fetchone()
            if row and row['payload']!=payload:raise PolicyError('Native permission reply cannot change')
            if not row:db.execute("INSERT INTO coding_replies VALUES(?,?,?,'QUEUED')",(self.run_id,key,payload))

    def close(self):
        # The transport owns native lifetime. Broker loss must not close it.
        pass


def serve(store,run_id):
    from .runner import process_identity,init as runner_init
    init(store);runner_init(store)
    lockdir=store.root/'transport-locks'/run_id;lockdir.mkdir(parents=True,exist_ok=True)
    lock=InstanceLock(lockdir)
    connection=None;worker=None
    try:
        with contextlib.closing(store.connect()) as db:host=db.execute('SELECT * FROM coding_hosts WHERE run_id=?',(run_id,)).fetchone()
        if not host or host['state']!='STARTING':return
        with contextlib.closing(store.connect()) as db:
            run=db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
        native_host=store.get(run['job_id'])['contract'].get('runtime')=='native-host'
        if native_host:
            if os.name=='nt':
                from .windows_job import contain_current_process
                lifetime_handle=contain_current_process()
            from .host_runtime import HostConnection
            connection=HostConnection(host['workspace'],store.root/'native-logs'/run_id,provider='claude' if run['provider']=='claude-code' else 'codex')
        elif os.name=='nt':
            from .wsl_runtime import WSLCodexConnection
            with contextlib.closing(store.connect()) as db:provider=db.execute('SELECT provider FROM runs WHERE id=?',(run_id,)).fetchone()['provider']
            connection=WSLCodexConnection(host['workspace'],store.root/'native-logs'/run_id,provider='claude' if provider=='claude-code' else 'codex')
        else:connection=CodexConnection(host['workspace'],store.root/'native-logs'/run_id)
        identity=process_identity(os.getpid());native_identity=process_identity(connection.process.pid)
        if not identity or not native_identity:raise PolicyError('Native process identity unavailable')
        with store.transaction() as db:
            if hasattr(connection,'group'):db.execute('INSERT OR REPLACE INTO isolated_runs VALUES(?,?,?)',(run_id,connection.group,connection.remote))
            db.execute("UPDATE coding_hosts SET pid=?,identity=?,state='RUNNING' WHERE run_id=?",(os.getpid(),identity,run_id))
            db.execute('INSERT OR REPLACE INTO native_processes VALUES(?,?,?,?,?)',
                (run_id,connection.process.pid,native_identity,str(store.root/'native-logs'/run_id),host['deadline']))
        def dispatch(call):
            try:reply={'result':connection.call(call['key'],json.loads(call['params']),timeout=110)}
            except Exception as exc:reply={'error':type(exc).__name__+': '+str(exc)}
            with store.transaction() as db:
                db.execute("UPDATE coding_calls SET result=?,state='FINISHED' WHERE run_id=? AND key=?",(encode(reply),run_id,call['key']))
        while time.time()<host['deadline']:
            with contextlib.closing(store.connect()) as db:
                run=db.execute('SELECT state FROM runs WHERE id=?',(run_id,)).fetchone()
                receipt=db.execute('SELECT 1 FROM inbox WHERE run_id=?',(run_id,)).fetchone()
                call=db.execute("SELECT * FROM coding_calls WHERE run_id=? AND state='QUEUED' ORDER BY rowid LIMIT 1",(run_id,)).fetchone()
                replies=db.execute("SELECT * FROM coding_replies WHERE run_id=? AND state='QUEUED'",(run_id,)).fetchall()
            if not run or receipt or run['state'] not in ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED'):break
            for reply in replies:
                # Commit the dispatch intent before writing to the native pipe.
                with store.transaction() as db:db.execute("UPDATE coding_replies SET state='DISPATCHED' WHERE run_id=? AND key=?",(run_id,reply['key']))
                connection.send(json.loads(reply['payload']))
            if call and (worker is None or not worker.is_alive()):
                with store.transaction() as db:db.execute("UPDATE coding_calls SET state='DISPATCHED' WHERE run_id=? AND key=?",(run_id,call['key']))
                worker=threading.Thread(target=dispatch,args=(dict(call),),daemon=True);worker.start()
            while True:
                try:event=connection.events.get_nowait()
                except queue.Empty:break
                # Exclude reasoning/token deltas. Keep complete protocol receipts.
                if 'id' in event or event.get('method') in ('item/started','item/completed','turn/completed','kel/connectionClosed','kel/toolBoundary','kel/runtime'):
                    payload=encode(event)
                    if len(payload)>2_000_000:raise PolicyError('Native event exceeds the receipt limit')
                    with store.transaction() as db:db.execute('INSERT INTO coding_events(run_id,event) VALUES(?,?)',(run_id,payload))
            if connection.process.poll() is not None:break
            time.sleep(.03)
    finally:
        if connection:connection.close()
        if worker:worker.join(timeout=2)
        with store.transaction() as db:db.execute("UPDATE coding_hosts SET state='STOPPED' WHERE run_id=?",(run_id,))
        lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',required=True);parser.add_argument('--rpc-run',required=True)
    args=parser.parse_args();serve(Store(args.data),args.rpc_run)
