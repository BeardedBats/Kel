"""Digest-bound source application with a durable per-file recovery journal."""
import contextlib
import json
import os
import time
from pathlib import Path
from .core import Conflict, PolicyError, digest, encode
from .guardrails import protected_reason
from .coding import file_manifest, check_evidence, git
from .instance_lock import InstanceLock


# D-65's per-job decision (kel.auto_apply owns it; created here too so the final write can update it).
AUTO_DDL=('CREATE TABLE IF NOT EXISTS auto_applications(job_id TEXT PRIMARY KEY, decision TEXT NOT NULL,'
          ' reason TEXT, mode TEXT, at REAL NOT NULL)')


def init(store):
    with contextlib.closing(store.connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS change_applications(job_id TEXT PRIMARY KEY,root TEXT,plan TEXT,state TEXT)')
        db.execute(AUTO_DDL)


def application(store,job_id):
    """The saved application journal row for a job (plan parsed), or None."""
    init(store)
    with contextlib.closing(store.connect()) as db:
        row=db.execute('SELECT * FROM change_applications WHERE job_id=?',(str(job_id),)).fetchone()
    if not row:return None
    out=dict(row)
    try:out['plan']=json.loads(row['plan'])
    except (TypeError,ValueError):out['plan']={}
    return out


def apply_checked(store,job_id,actor='kel',auto=False):
    """Write a verified change into the project.

    `auto` marks D-65's automatic apply under Full access: its Activity line says so, and the result
    message published right after reports it instead of a separate "Applied" message.
    """
    init(store)
    job=store.get(job_id)
    if job['contract'].get('kind')!='coding':raise PolicyError('This job has no repository change')
    root=Path(job['contract']['root']).resolve(strict=True)
    reason=protected_reason(root)
    if reason:raise PolicyError('Refusing to apply changes into a protected location: '+reason)
    # V1.5: the real effect point. Writing into the user's project requires an authorized write
    # intent (valid execution lease); revoked or missing permission refuses before any write.
    if actor not in ('user','kel'):raise PolicyError('Unknown actor for change application')
    from .authorize import authorize
    decision=authorize(store,{'actor':actor,'job':job_id,'action_kind':'write','target':str(root),
        'capability':'files',
        'metadata':{'what':'update the project files','why':'apply the changes you approved',
                    'fallback':'leave the project unchanged and report'}})
    if decision['outcome']!='ALLOW':
        raise PolicyError('Application is not authorized: '+
                          (decision.get('reason') or decision.get('rule') or 'permission required'))
    from .containment import assert_usable_root
    assert_usable_root(root,purpose='an application of changes',store=store)
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
            if saved['state']=='UNDOING':raise PolicyError('Kel is still putting the earlier files back. Try again when that finishes.')
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
        count=len(plan['changes'])
        with store.transaction() as db:
            db.execute("UPDATE change_applications SET state='APPLIED' WHERE job_id=?",(job_id,))
            db.execute(AUTO_DDL)
            if auto:
                # D-65: one Activity line, in the D-64 "Full access: Kel went ahead to ..." style.
                db.execute("UPDATE auto_applications SET decision='applied',reason=NULL,at=? WHERE job_id=?",(time.time(),job_id))
                store._save(db,store._get(db,job_id),'changes.auto_applied',
                    {'files':count,'root':str(root),'authority':'full',
                     'summary':'apply the checked change to %s (%d file%s)'%(root.name or str(root),count,'' if count==1 else 's')})
            else:
                db.execute("UPDATE auto_applications SET decision='manual',reason=NULL,at=? WHERE job_id=?",(time.time(),job_id))
                store._save(db,store._get(db,job_id),'changes.applied',{'files':count,'root':str(root)})
                db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                    (job['conversation'],'assistant','Applied the checked changes to your project. A backup is saved.',None,time.time()))
        return {'state':'APPLIED','files':count,'backup':str(vault),'auto':bool(auto)}
    finally:lock.close()


def _auto_pending(store,job_id):
    with contextlib.closing(store.connect()) as db:
        row=db.execute('SELECT decision FROM auto_applications WHERE job_id=?',(job_id,)).fetchone()
    return bool(row and row['decision']=='applying')


def recover_prepared(store):
    """Finish, at start-up, an application or an undo a crash interrupted (never repeating a write)."""
    init(store)
    with contextlib.closing(store.connect()) as db:
        pending=[(r[0],r[1]) for r in db.execute("SELECT job_id,state FROM change_applications WHERE state IN ('PREPARED','UNDOING')")]
    for job_id,state in pending:
        # D-65: an automatic apply a crash interrupted is still automatic when it finishes.
        auto=state=='PREPARED' and _auto_pending(store,job_id)
        try:
            if state=='UNDOING':undo_applied(store,job_id,actor='kel')
            else:apply_checked(store,job_id,auto=auto)
        except Conflict:
            continue  # the engine holds this project's application lock right now; it is not stuck
        except Exception as exc:
            with store.transaction() as db:
                db.execute("UPDATE change_applications SET state='BLOCKED' WHERE job_id=?",(job_id,))
                if auto:
                    db.execute("UPDATE auto_applications SET decision='waiting',reason=?,at=? WHERE job_id=? AND decision='applying'",
                               ('the automatic apply stopped: '+str(exc).rstrip('.'),time.time(),job_id))
                job=store._get(db,job_id)
                db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                    (job['conversation'],'assistant',('Undo' if state=='UNDOING' else 'Change application')+' stopped: '+str(exc)+' The saved backup is intact.',None,time.time()))


def _lock(root):
    metadata=Path(git(root,'rev-parse','--absolute-git-dir').decode().strip()).resolve(strict=True)
    if not metadata.is_relative_to(root):raise PolicyError('Linked Git metadata cannot own an application lock')
    lockroot=metadata/'kel-application';lockroot.mkdir(exist_ok=True)
    if lockroot.is_symlink() or lockroot.is_junction() or not lockroot.resolve().is_relative_to(metadata):raise PolicyError('The application lock directory is linked')
    return InstanceLock(lockroot)


def undo_applied(store,job_id,actor='user'):
    """Put back the files an application replaced (D-65 "Undo"), from the saved pre-apply backup.

    Refuses without writing anything when a changed file was edited after Kel applied it: the
    person's later work is never overwritten. Journaled like the apply (UNDOING is saved before the
    first write; each replacement is atomic) so a crash resumes without repeating a finished step.
    """
    init(store)
    if actor not in ('user','kel'):raise PolicyError('Unknown actor for undoing changes')
    saved=application(store,job_id)
    if not saved or saved['state'] not in ('APPLIED','UNDOING','UNDONE'):
        raise PolicyError('There is no applied change to undo.')
    if saved['state']=='UNDONE':return {'state':'UNDONE','already_undone':True}
    job=store.get(job_id)
    root=Path(saved['root']).resolve(strict=True)
    reason=protected_reason(root)
    if reason:raise PolicyError('Refusing to change a protected location: '+reason)
    from .authorize import authorize, ensure_job_lease
    try:ensure_job_lease(store,job)  # renews an expired lease; a revoked one stays revoked
    except Exception:pass
    decision=authorize(store,{'actor':actor,'job':job_id,'action_kind':'write','target':str(root),
        'capability':'files',
        'metadata':{'what':'put the earlier project files back','why':'undo the change Kel applied',
                    'fallback':'leave the project as it is and report'}})
    if decision['outcome']!='ALLOW':
        raise PolicyError('Undo is not authorized: '+(decision.get('reason') or decision.get('rule') or 'permission required'))
    from .containment import assert_usable_root
    assert_usable_root(root,purpose='undoing applied changes',store=store)
    lock=_lock(root)
    try:
        saved=application(store,job_id)
        if saved['state']=='UNDONE':return {'state':'UNDONE','already_undone':True}
        plan=saved['plan'];vault=store.root/'application-backups'/job_id
        current=file_manifest(root)
        for p,c in plan['changes'].items():
            stage=(Path(p).parent/('.kel-undo-'+digest([job_id,p])+'.tmp')).as_posix()
            if stage in current:
                if c['before'] is None or current[stage]!=c['before']:raise PolicyError('Undo staging file is not intact')
                (root/stage).unlink();current.pop(stage)
        resuming=saved['state']=='UNDOING'
        for p,c in plan['changes'].items():
            actual=current.get(p)
            if actual==c['after'] or (resuming and actual==c['before']):continue
            raise PolicyError(p+' changed after Kel applied it, so nothing was undone. Your later edits are kept.')
        for p,c in plan['changes'].items():
            if c['before'] is not None and digest((vault/c['before']).read_bytes())!=c['before']:
                raise PolicyError('The saved backup changed, so nothing was undone.')
        if not resuming:
            with store.transaction() as db:
                db.execute("UPDATE change_applications SET state='UNDOING' WHERE job_id=? AND state='APPLIED'",(job_id,))
        for p,c in plan['changes'].items():
            target=root/p
            actual=file_manifest(root).get(p)
            if actual==c['before']:continue
            if actual!=c['after']:raise PolicyError('Project changed during undo; the saved backup is intact')
            if c['before'] is None:
                target.unlink();continue
            raw=(vault/c['before']).read_bytes()
            target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.parent/('.kel-undo-'+digest([job_id,p])+'.tmp')
            with temporary.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(temporary,target)
        final=file_manifest(root)
        if any(final.get(p)!=c['before'] for p,c in plan['changes'].items()):
            raise PolicyError('Project changed during undo; the saved backup is intact')
        count=len(plan['changes'])
        with store.transaction() as db:
            db.execute("UPDATE change_applications SET state='UNDONE' WHERE job_id=?",(job_id,))
            store._save(db,store._get(db,job_id),'changes.undone',{'files':count,'root':str(root)})
            db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                (job['conversation'],'assistant','Undid the change in '+str(root)+': '+('the file is' if count==1 else 'the '+str(count)+' files are')+' back to how '+('it was' if count==1 else 'they were')+' before Kel applied it.',None,time.time()))
        return {'state':'UNDONE','files':count}
    finally:lock.close()
