"""Digest-bound source application with a durable per-file recovery journal."""
import contextlib
import json
import os
import time
from pathlib import Path
from .core import PolicyError, digest, encode
from .coding import file_manifest, check_evidence, git
from .instance_lock import InstanceLock


def init(store):
    with contextlib.closing(store.connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS change_applications(job_id TEXT PRIMARY KEY,root TEXT,plan TEXT,state TEXT)')


def apply_checked(store,job_id):
    init(store)
    job=store.get(job_id)
    if job['contract'].get('kind')!='coding':raise PolicyError('This job has no repository change')
    root=Path(job['contract']['root']).resolve(strict=True)
    metadata=Path(git(root,'rev-parse','--absolute-git-dir').decode().strip()).resolve(strict=True)
    if not metadata.is_relative_to(root):raise PolicyError('Linked Git metadata cannot own an application lock')
    lockroot=metadata/'kel-application';lockroot.mkdir(exist_ok=True)
    if lockroot.is_symlink() or lockroot.is_junction() or not lockroot.resolve().is_relative_to(metadata):raise PolicyError('The application lock directory is linked')
    lock=InstanceLock(lockroot)
    try:
        with contextlib.closing(store.connect()) as db:
            saved=db.execute('SELECT * FROM change_applications WHERE job_id=?',(job_id,)).fetchone()
        if saved:
            if saved['root']!=str(root):raise PolicyError('Application destination changed')
            plan=json.loads(saved['plan'])
            if saved['state']=='APPLIED':return {'state':'APPLIED','already_applied':True,'files':len(plan['changes'])}
        else:
            if store.assess(job_id)!='VERIFIED':raise PolicyError('The change no longer passes its checks')
            job=store.get(job_id);run_id=job['milestones']['code']['artifact']['run_id']
            if check_evidence(store,run_id)!='VERIFIED':raise PolicyError('Coding evidence changed')
            with contextlib.closing(store.connect()) as db:
                workspace=db.execute('SELECT * FROM code_workspaces WHERE job_id=?',(job_id,)).fetchone()
                evidence=db.execute('SELECT * FROM code_evidence WHERE run_id=?',(run_id,)).fetchone()
            baseline=json.loads(workspace['manifest']);after=json.loads(evidence['manifest'])
            if file_manifest(root)!=baseline:raise PolicyError('Your project changed since coding started. Application stopped without overwriting it.')
            changes={p:{'before':baseline.get(p),'after':after.get(p)} for p in sorted(set(baseline)|set(after)) if baseline.get(p)!=after.get(p)}
            vault=store.root/'application-backups'/job_id;vault.mkdir(parents=True,exist_ok=True)
            for p,change in changes.items():
                for key,source in [('before',root),('after',Path(workspace['path']))]:
                    sha=change[key]
                    if sha is None:continue
                    raw=(source/p).read_bytes()
                    if digest(raw)!=sha:raise PolicyError('File changed while preparing application')
                    target=vault/sha
                    with target.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            plan={'baseline':baseline,'changes':changes}
            with store.transaction() as db:
                db.execute('INSERT INTO change_applications VALUES(?,?,?,?)',(job_id,str(root),encode(plan),'PREPARED'))
        vault=store.root/'application-backups'/job_id
        current=file_manifest(root)
        # A crash can leave a fully saved staging file before its atomic rename.
        for p,c in plan['changes'].items():
            stage=(Path(p).parent/('.kel-'+digest([job_id,p])+'.tmp')).as_posix()
            if stage in current:
                if c['after'] is None or current[stage]!=c['after']:raise PolicyError('Application staging file is not intact')
                (root/stage).unlink()
                current.pop(stage)
        for p,sha in current.items():
            allowed=plan['changes'].get(p)
            if (allowed and sha not in (allowed['before'],allowed['after'])) or (not allowed and plan['baseline'].get(p)!=sha):
                raise PolicyError('Project conflict while recovering application; backups are preserved')
        for p,sha in plan['baseline'].items():
            if p not in plan['changes'] and current.get(p)!=sha:raise PolicyError('An unchanged source file is missing')
        for p,change in plan['changes'].items():
            actual=current.get(p)
            if actual==change['after']:continue
            if actual!=change['before']:raise PolicyError('Application target no longer matches either saved version')
            target=root/p
            # Recheck all link boundaries before each write; source remains locked against other Kel applications.
            latest=file_manifest(root)
            if latest.get(p)!=change['before']:raise PolicyError('Source changed before its replacement')
            if change['after'] is None:target.unlink()
            else:
                raw=(vault/change['after']).read_bytes()
                if digest(raw)!=change['after']:raise PolicyError('Saved application bytes changed')
                target.parent.mkdir(parents=True,exist_ok=True)
                temporary=target.parent/('.kel-'+digest([job_id,p])+'.tmp')
                with temporary.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
                os.replace(temporary,target)
        expected=dict(plan['baseline'])
        for p,c in plan['changes'].items():
            if c['after'] is None:expected.pop(p,None)
            else:expected[p]=c['after']
        if file_manifest(root)!=expected:raise PolicyError('Project changed during application; inspect the saved backup')
        with store.transaction() as db:
            db.execute("UPDATE change_applications SET state='APPLIED' WHERE job_id=?",(job_id,))
            store._save(db,store._get(db,job_id),'changes.applied',{'files':len(plan['changes'])})
            db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                (job['conversation'],'assistant','Applied the checked changes to your project. A backup is saved.',None,time.time()))
        return {'state':'APPLIED','files':len(plan['changes']),'backup':str(vault)}
    finally:lock.close()


def recover_prepared(store):
    init(store)
    with contextlib.closing(store.connect()) as db:pending=[r[0] for r in db.execute("SELECT job_id FROM change_applications WHERE state='PREPARED'")]
    for job_id in pending:
        try:apply_checked(store,job_id)
        except Exception as exc:
            with store.transaction() as db:
                db.execute("UPDATE change_applications SET state='BLOCKED' WHERE job_id=?",(job_id,))
                job=store._get(db,job_id)
                db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                    (job['conversation'],'assistant','Change application stopped: '+str(exc)+' The saved backup is intact.',None,time.time()))
