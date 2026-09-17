"""Repository work in isolated snapshots; deterministic test and patch evidence."""
import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import stat
import time
from .appserver import CodexConnection
from .core import PolicyError, digest, encode, uid, validate_contract
from .context import Context
from .coding_transport import DurableCodingConnection,host_alive


def git(root,*args,input=None):
    p=subprocess.run(['git','-c','core.hooksPath=NUL','-c','core.longpaths=true',*args],cwd=root,input=input,
                     capture_output=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode:raise PolicyError(p.stderr.decode('utf-8','replace')[:1000])
    return p.stdout


def compile_coding(request,root,tests,project_id='default',greenfield=False):
    root=Path(root).resolve(strict=True)
    if not isinstance(tests,list) or not tests or not all(isinstance(s,str) and s for s in tests):
        raise PolicyError('Coding needs an explicit test command as an argument list')
    if len(tests)>40:raise PolicyError('Test command is too long')
    git(root,'rev-parse','--show-toplevel')
    rubric=('The code diff satisfies the source request. Existing tests remain intact and pass. Review the actual diff and trusted test output.'
            if not greenfield else
            'The new project implements the source request and its smoke test passes. The project runs with only standard tooling unless the request requires otherwise.')
    contract={'request':request,'kind':'coding','root':str(root),'test_command':tests,
        'project_id':project_id,'compiler':'coding-contract-v2','runtime':'native-host',
        'non_goals':['unrequested source checkout changes','unrequested external publication'],
        'milestones':[{'id':'code','objective':request,'filename':'changes.md','depends_on':[],
            'checks':[{'kind':'min_chars','value':40},{'kind':'manual_review','rubric':rubric}]}]}
    if greenfield:contract['greenfield']=True
    return validate_contract(contract)


def file_manifest(root):
    root=Path(root)
    files={}
    def check(path):
        info=path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0):
            raise PolicyError('Linked paths are not allowed in coding evidence')
        if stat.S_ISREG(info.st_mode) and info.st_nlink>1:
            raise PolicyError('Hard-linked files are not allowed in coding evidence')
        return info
    if not stat.S_ISDIR(check(root).st_mode):raise PolicyError('Coding workspace must be a directory')
    def unreadable(error):
        raise PolicyError('Cannot inspect every coding workspace path') from error
    for directory,dirs,names in os.walk(root,followlinks=False,onerror=unreadable):
        parent=Path(directory)
        for name in dirs:check(parent/name)
        # Git owns its metadata. Other excluded trees still need link checks:
        # native commands can enter them even though they are not source evidence.
        dirs[:]=[name for name in dirs if name!='.git']
        for name in names:
            path=parent/name;info=check(path);relative=path.relative_to(root)
            if any(p in ('.git','__pycache__','.pytest_cache','node_modules','.venv') for p in relative.parts):continue
            if not stat.S_ISREG(info.st_mode):raise PolicyError('Special files are not allowed in coding evidence')
            if info.st_size>10_000_000:raise PolicyError('A source file exceeds the 10 MB evidence limit')
            files[relative.as_posix()]=digest(path.read_bytes())
    return files


def snapshot(source,target):
    """Copy the actual tracked and untracked source state, never alter its checkout."""
    source=Path(source).resolve(strict=True);target=Path(target).resolve()
    if target.exists():raise PolicyError('Snapshot target already exists')
    file_manifest(source)
    # Git may materialize symlinks as ordinary files on Windows. Check index mode
    # before cloning so that behavior cannot silently hide a linked source path.
    if any(entry.startswith(b'120000 ') for entry in git(source,'ls-files','--stage','-z').split(b'\0')):
        raise PolicyError('Tracked symbolic links are not supported in coding snapshots')
    git(source,'clone','--no-local','--no-hardlinks',str(source),str(target))
    git(target,'remote','remove','origin')
    patch=git(source,'diff','--binary','HEAD')
    if patch:git(target,'apply','--binary','-',input=patch)
    git(target,'config','core.autocrlf','false')
    # Preserve actual source bytes across Windows and Linux Git defaults.
    for raw in git(source,'ls-files','-z').split(b'\0'):
        if not raw:continue
        relative=Path(os.fsdecode(raw));candidate=source/relative
        if candidate.is_file():
            dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(candidate,dest)
    for raw in git(source,'ls-files','--others','--exclude-standard','-z').split(b'\0'):
        if not raw:continue
        relative=Path(os.fsdecode(raw));candidate=source/relative
        if candidate.is_symlink() or candidate.is_junction():raise PolicyError('Untracked path is linked')
        src=candidate.resolve(strict=True)
        if not src.is_relative_to(source):raise PolicyError('Untracked path escaped source')
        if any(part.startswith('.env') for part in relative.parts):continue
        if src.stat().st_size>10_000_000:raise PolicyError('Untracked file exceeds 10 MB')
        dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    file_manifest(target)
    git(target,'add','-A')
    git(target,'-c','user.name=Kel','-c','user.email=kel@localhost','commit','--allow-empty','-m','Kel source snapshot')
    return git(target,'rev-parse','HEAD').decode().strip()


class CodingAdapter:
    provider='codex-code'
    capabilities={'text','repository_edit','native_session','approval_stream'}
    def __init__(self,store):
        self.store=store
        self.context=Context(store)
        with contextlib.closing(store.connect()) as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS code_workspaces(job_id TEXT PRIMARY KEY,path TEXT,base TEXT,manifest TEXT);
            CREATE TABLE IF NOT EXISTS native_progress(seq INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,method TEXT,data TEXT,at REAL);
            CREATE TABLE IF NOT EXISTS approval_actions(approval_id TEXT PRIMARY KEY,action TEXT);
            CREATE TABLE IF NOT EXISTS code_evidence(run_id TEXT PRIMARY KEY,workspace TEXT,manifest TEXT,patch TEXT,patch_digest TEXT,tests TEXT,baseline_tests TEXT,at REAL);
            CREATE TABLE IF NOT EXISTS coding_phases(run_id TEXT PRIMARY KEY,phase TEXT,result TEXT,at REAL);
            ''')

    def approval(self,run,method,params,cancel):
        job=self.store.get(run['job_id'])
        # Stable action identity excludes delivery IDs and timestamps, retaining the exact command and scope.
        action={'method':method,'workspace':params.get('cwd'),'command':params.get('command'),
                'permissions':params.get('permissions'),'grantRoot':params.get('grantRoot'),
                'network':params.get('networkApprovalContext')}
        if method=='item/fileChange/requestApproval':
            with contextlib.closing(self.store.connect()) as db:
                events=db.execute("SELECT data FROM native_progress WHERE run_id=? AND method='item/started' ORDER BY seq DESC",(run['id'],)).fetchall()
            item=next((json.loads(e['data']).get('item',{}) for e in events if json.loads(e['data']).get('item',{}).get('id')==params.get('itemId')),None)
            action['changes']=item.get('changes') if item else None
            # Missing patch details cannot create a reusable wildcard grant.
            if not action['changes']:action['unrepeatable_request']=params.get('itemId')
        pid=job['contract'].get('project_id','default')
        if self.context.allowed(pid,action):return True
        with contextlib.closing(self.store.connect()) as db:
            prior=db.execute('SELECT a.id FROM approvals a JOIN approval_actions x ON x.approval_id=a.id WHERE a.run_id=? AND x.action=? ORDER BY a.rowid DESC LIMIT 1',(run['id'],encode(action))).fetchone()
        if prior:aid=prior['id']
        else:
            aid=self.store.request_approval(job['id'],run['id'],action,seconds=300)
            with self.store.transaction() as db:db.execute('INSERT INTO approval_actions VALUES(?,?)',(aid,encode(action)))
            # The conversation shows a decision card for this ask (in-chat approvals, V1.6).
            from .chat_approvals import announce_approval
            announce_approval(self.store, aid, job, action)
        while not (cancel and cancel.is_set()):
            with contextlib.closing(self.store.connect()) as db:
                row=db.execute('SELECT * FROM approvals WHERE id=?',(aid,)).fetchone()
            if row['status']!='PENDING':return row['status']=='APPROVED'
            if row['expires']<time.time():
                self.store.resolve_approval(aid,action,False)
                return False
            time.sleep(.2)
        return False

    def execute(self,prompt,run_id=None,session_id=None,cancel=None):
        with contextlib.closing(self.store.connect()) as db:
            run=dict(db.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone())
            row=db.execute('SELECT * FROM code_workspaces WHERE job_id=?',(run['job_id'],)).fetchone()
            phase=db.execute('SELECT * FROM coding_phases WHERE run_id=?',(run_id,)).fetchone()
        if phase and phase['phase'] not in ('TURN_COMPLETED','TURN_DISPATCHED','TESTS_DISPATCHED'):
            raise PolicyError('Coding execution already dispatched; reconcile its durable phase')
        job=self.store.get(run['job_id']);contract=job['contract']
        # V1.5: the real effect point. A worker cannot start repository work or run the configured
        # test command without a valid lease and role policy; a revoked lease stops it here.
        from .authorize import authorize,role_for
        from .capabilities import capability_for_tool
        role_info=role_for(self.store,run['job_id'],run['milestone_id'])
        for tool in ('git','run_tests','write'):
            decision=authorize(self.store,{'actor':'worker','worker':run_id,'job':run['job_id'],
                'milestone':run['milestone_id'],'role':(role_info or {}).get('template_id'),
                'role_tool_policy':(role_info or {}).get('tool_policy'),
                'capability':capability_for_tool(tool),
                'action_kind':'repo','tool':tool,'target':str(contract.get('root') or ''),
                'metadata':{'what':'make the planned changes in a safe copy of the project',
                            'why':'the task needs repository changes',
                            'fallback':'stop before any change and report'}})
            if decision['outcome']!='ALLOW':
                return {'outcome':'BLOCKED','error':'Kel paused this work before any change: '+
                        str(decision.get('reason') or decision.get('rule') or 'authorization required'),
                        'authorization':decision.get('outcome')}
        if row:
            workspace=Path(row['path']);base=row['base'];baseline=json.loads(row['manifest'])
        else:
            workspace=self.store.root/'repositories'/job['id'];workspace.parent.mkdir(exist_ok=True)
            base=snapshot(contract['root'],workspace);baseline=file_manifest(workspace)
            with self.store.transaction() as db:db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)',
                (job['id'],str(workspace),base,encode(baseline)))
        if phase and phase['phase']=='TURN_COMPLETED' and file_manifest(workspace)!=json.loads(phase['result']).get('_checkpoint_manifest'):
            raise PolicyError('Workspace changed before pending checks resumed')
        if phase and phase['phase'] in ('TURN_DISPATCHED','TESTS_DISPATCHED') and not host_alive(self.store,run_id):
            raise PolicyError('Native transport lost; unresolved effects cannot be replayed')
        connection=DurableCodingConnection(self.store,run_id,workspace)
        def progress(event):
            method=event.get('method','');params=event.get('params',{})
            # Persist bounded user-visible native events, not token-by-token reasoning.
            if method in ('kel/session','item/started','item/completed','turn/completed'):
                with self.store.transaction() as db:
                    data=encode(params)
                    if not db.execute('SELECT 1 FROM native_progress WHERE run_id=? AND method=? AND data=?',(run_id,method,data)).fetchone():
                        db.execute('INSERT INTO native_progress(run_id,method,data,at) VALUES(?,?,?,?)',
                            (run_id,method,data,time.time()))
                    if method=='kel/session':db.execute('UPDATE runs SET native_session=? WHERE id=?',(params['threadId'],run_id))
        try:
            if phase and phase['phase']!='TURN_DISPATCHED':
                result=json.loads(phase['result'])
            else:
                if not phase:
                    with self.store.transaction() as db:
                        db.execute('INSERT INTO coding_phases VALUES(?,?,?,?)',(run_id,'TURN_DISPATCHED','{}',time.time()))
                result=connection.run('Source request: '+contract['request']+'\nWork in this isolated repository. '
                    'Implement the requested change. Preserve existing tests. Do not change the source checkout. '
                    'Do not delete caches or clean the workspace. Kel runs tests after your turn. Avoid generating bytecode. '
                    'Test command: '+encode(contract['test_command'])
                    +('\nThis is a brand-new empty project: create the complete application source AND a smoke test file that the configured test command runs and passes. '
                      'Keep everything inside the project root. Prefer the Python standard library; only add dependencies the project can install and document them.' if contract.get('greenfield') else '')
                    +'\nContext:\n'+prompt,
                    session_id=session_id,cancel=cancel,on_event=progress,
                    on_approval=lambda m,p:self.approval(run,m,p,cancel))
            if result['outcome']!='SUCCESS':return result
            if not phase or phase['phase']=='TURN_DISPATCHED':
                result['_checkpoint_manifest']=file_manifest(workspace)
                with self.store.transaction() as db:
                    db.execute("UPDATE coding_phases SET phase='TURN_COMPLETED',result=?,at=? WHERE run_id=?",(encode(result),time.time(),run_id))
            before=result['_tests_before'] if phase and phase['phase']=='TESTS_DISPATCHED' else file_manifest(workspace)
            protected={p:h for p,h in baseline.items() if Path(p).name.startswith('test') or 'tests' in Path(p).parts}
            preserved=all(before.get(p)==h for p,h in protected.items())
            if cancel and cancel.is_set() and not (phase and phase['phase']=='TESTS_DISPATCHED'):
                return {'outcome':'CANCELLED','session_id':result.get('session_id')}
            if not phase or phase['phase']!='TESTS_DISPATCHED':
                result['_tests_before']=before
                with self.store.transaction() as db:
                    changed=db.execute("UPDATE coding_phases SET phase='TESTS_DISPATCHED',result=?,at=? WHERE run_id=? AND phase='TURN_COMPLETED'",(encode(result),time.time(),run_id)).rowcount
                    if changed!=1:raise PolicyError('Tests already dispatched; refusing duplicate execution')
            tests=connection.call('command/exec',{'command':contract['test_command'],'cwd':str(workspace),
                'timeoutMs':90000,'sandboxPolicy':{'type':'workspaceWrite',
                'writableRoots':[str(workspace)],'networkAccess':False},
                'env':{'ANTHROPIC_API_KEY':None,'OPENAI_API_KEY':None}},timeout=100)
            after=file_manifest(workspace)
            stable=before==after
            git(workspace,'add','-A')
            patch=git(workspace,'diff','--cached','--binary',base).decode('utf-8','replace')
            evidence={'exit_code':tests['exitCode'],'stdout':tests['stdout'],'stderr':tests['stderr'],
                      'existing_tests_preserved':preserved,'source_stable_during_tests':stable,
                      'command':contract['test_command']}
            if tests.get('_kel_execution'):evidence['execution']=tests['_kel_execution']
            with self.store.transaction() as db:
                db.execute('INSERT OR REPLACE INTO code_evidence VALUES(?,?,?,?,?,?,?,?)',
                    (run_id,str(workspace),encode(after),patch,digest(patch.encode()),encode(evidence),encode(protected),time.time()))
                db.execute("UPDATE coding_phases SET phase='EVIDENCE_CAPTURED',at=? WHERE run_id=?",(time.time(),run_id))
            # Trusted evidence stays outside the writable worker folder.
            verdict=tests['exitCode']==0 and preserved and stable and bool(patch.strip())
            report='# Repository change\n\n'+result.get('text','')+'\n\n## Trusted checks\n'+json.dumps(evidence,indent=2)+'\n\n## Diff\n```diff\n'+patch+'\n```\n'
            result.update(text=report,code_verified=verdict)
            return result
        finally:connection.close()


def check_evidence(store,run_id):
    with contextlib.closing(store.connect()) as db:
        row=db.execute('SELECT * FROM code_evidence WHERE run_id=?',(run_id,)).fetchone()
    if not row:return 'UNCERTAIN'
    tests=json.loads(row['tests'])
    if tests['exit_code']!=0 or not tests['existing_tests_preserved'] or not tests['source_stable_during_tests']:return 'FAILED'
    if not row['patch'].strip():return 'UNCERTAIN'
    if digest(row['patch'].encode())!=row['patch_digest']:return 'UNCERTAIN'
    if file_manifest(Path(row['workspace']))!=json.loads(row['manifest']):return 'UNCERTAIN'
    return 'VERIFIED'


def recover_checked_code(store,run,row):
    """Recover already-captured tests and diff; never start another coding turn."""
    from .runner import process_identity,terminate_known_process
    with contextlib.closing(store.connect()) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'code_evidence','native_processes','native_progress'}.issubset(tables):return None
        evidence=db.execute('SELECT * FROM code_evidence WHERE run_id=?',(run['id'],)).fetchone()
        child=db.execute('SELECT * FROM native_processes WHERE run_id=?',(run['id'],)).fetchone()
        events=db.execute("SELECT data FROM native_progress WHERE run_id=? AND method='turn/completed' ORDER BY seq DESC LIMIT 1",(run['id'],)).fetchone()
    if not evidence or not child or not child['identity'] or not events:return None
    try:
        turn=json.loads(events['data']).get('turn',{})
        if turn.get('status')!='completed':return None
        # Test receipt is captured after command/exec returned. With its broker gone,
        # this app-server has no remaining authorized work; stop only its exact handle.
        if process_identity(child['pid'])==child['identity']:
            if not terminate_known_process(child['pid'],child['identity']):return None
            return 'LIVE'
        if check_evidence(store,run['id'])!='VERIFIED':return None
        tests=json.loads(evidence['tests'])
        text='# Recovered repository change\n\nThe native coding turn and configured tests completed before the broker exited.\n\n## Trusted checks\n'+json.dumps(tests,indent=2)+'\n\n## Diff\n```diff\n'+evidence['patch']+'\n```\n'
        return {'outcome':'SUCCESS','text':text,'session_id':run['native_session'],'turn_id':turn.get('id'),'code_verified':True,'recovered_from_code_evidence':True}
    except (ValueError,TypeError,KeyError,OSError,PolicyError):return None


def recover_pending_checks(store,run):
    """Identify the narrow window where tests provably have not been dispatched."""
    from .runner import process_identity,terminate_known_process
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='coding_phases'").fetchone():return None
        phase=db.execute('SELECT * FROM coding_phases WHERE run_id=?',(run['id'],)).fetchone()
        child=db.execute('SELECT * FROM native_processes WHERE run_id=?',(run['id'],)).fetchone()
        workspace=db.execute('SELECT * FROM code_workspaces WHERE job_id=?',(run['job_id'],)).fetchone()
    if not phase or phase['phase']!='TURN_COMPLETED' or not child or not workspace:return None
    if run['state']!='RUNNING':return None
    try:
        result=json.loads(phase['result'])
        if result.get('outcome')!='SUCCESS' or not result.get('turn_id'):return None
        if not child['identity']:return None
        if process_identity(child['pid'])==child['identity']:
            return 'LIVE' if terminate_known_process(child['pid'],child['identity']) else None
        if file_manifest(Path(workspace['path']))!=result.get('_checkpoint_manifest'):return None
        return 'RESUME_CHECKS'
    except (ValueError,TypeError,OSError,PolicyError):return None
