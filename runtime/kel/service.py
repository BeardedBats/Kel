"""Authenticated loopback service for the local Kel desktop shell."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import contextlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlparse,parse_qs
from .core import Store,PolicyError,Conflict,encode
from .context import Context
from .engine import Engine,compile_document
from .commander import Commander
from .internal import InternalAdapter
from .native import NativeAdapter
from .coding import CodingAdapter,compile_coding
from .runner import DurableAdapter
from .research import needs_research
from .router import needs_work

# Single source for the engine's identity (audit R8.B): the desktop refuses to reuse a live engine
# whose reported version differs from the app it shipped with, so this literal must match
# `desktop/package.json`'s version (what `app.getVersion()` reports in the packaged app).
from . import __version__ as ENGINE_VERSION

# Verbs that mean "change code in an existing project". These are the only
# requests that need a project root; greenfield ("create an app") is classified
# separately and never prompts.
CODING_VERBS=('fix','build','implement','change','add','remove','update','refactor','test')

def _restore_outcome(root):
    """The last restore attempt recorded beside the data (audit PER-02); None if never attempted."""
    path=Path(root)/'restore-outcome.json'
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    return {'ok':bool(data.get('ok')),'detail':data.get('detail') or '','at':data.get('at')}


class Service:
    def __init__(self,root):
        started=time.time()
        self.lifecycle_lock=threading.RLock();self.draining=False
        self.store=Store(root)
        # A staged restore (chosen by the user in Settings) applies before anything opens
        # the databases; the previous data is kept beside it as .pre-restore-*.
        try:
            from .backup import _record_outcome,apply_pending_restore
            apply_pending_restore(self.store)
        except Exception as exc:
            # PER-02 (audit): boot must survive a restore that cannot even start, and the failure
            # must not be silent — it is recorded beside the data and surfaced in `state()`.
            _record_outcome(self.store.root,False,type(exc).__name__)
        self.context=Context(self.store)
        CodingAdapter(self.store)  # Schema only; actual execution lives in detached brokers.
        self.model=InternalAdapter() if os.environ.get('ANTHROPIC_API_KEY') else None
        # The independent reviewer must not depend on a separate API key when real
        # native agents are installed; reuse an available CLI so manual_review
        # criteria can actually be judged.
        review_model=None;review_alternates=[]
        if self.model:
            review_model=InternalAdapter(model=self.model.model,timeout=90)
            if os.environ.get('KEL_REVIEWER')!='none':
                # Installed CLIs are eligible alternatives so a job executed by
                # one model family can be reviewed by a genuinely different one.
                for provider in ('claude','codex'):
                    adapter=NativeAdapter(provider,self.store.root/'workspaces'/provider,self.store.root/'logs')
                    if adapter.probe().get('installed'):review_alternates.append(adapter)
        elif os.environ.get('KEL_REVIEWER')!='none':
            # Native fallback (default when no internal key): reuse an installed
            # CLI so manual_review criteria can actually be judged. Tests and
            # headless setups opt out with KEL_REVIEWER=none. The first installed
            # provider stays the default; the rest are diversity alternatives.
            for provider in ('claude','codex'):
                adapter=NativeAdapter(provider,self.store.root/'workspaces'/provider,self.store.root/'logs')
                if adapter.probe().get('installed'):
                    if review_model is None:review_model=adapter
                    else:review_alternates.append(adapter)
        self.commander=Commander(review_model,review_alternates) if review_model else None
        adapters={}
        for provider in ('codex','claude'):
            if NativeAdapter(provider,self.store.root/'workspaces'/provider,self.store.root/'logs').probe().get('installed'):
                adapters[provider]=DurableAdapter(self.store,provider)
        if 'codex' in adapters:adapters['codex-code']=DurableAdapter(self.store,'codex-code',{'repository_edit','native_session','approval_stream'})
        if 'claude' in adapters:adapters['claude-code']=DurableAdapter(self.store,'claude-code',{'repository_edit','native_session'})
        if self.model:adapters['internal']=DurableAdapter(self.store,'internal',{'text','image'},options={'model':self.model.model})
        if self.model:adapters['research']=DurableAdapter(self.store,'research',{'text','web_research'},options={'model':self.model.model})
        self.engine=Engine(self.store,adapters,reviewer=self.commander)
        # Kel V1.4 diagnostics: record the real startup cost of store + adapters + engine so the
        # diagnostics surface can show a measured timeline instead of a claimed one.
        try:
            from .diagnostics import Diagnostics
            Diagnostics(self.store,ENGINE_VERSION).record_startup(
                'engine-start',round((time.time()-started)*1000,2))
        except Exception:
            pass  # a missing span costs one observation, never a boot
        self.requests=ThreadPoolExecutor(max_workers=2,thread_name_prefix='kel-conversation')
        from .apply_changes import recover_prepared
        self.requests.submit(recover_prepared,self.store)
        self.stop=threading.Event();self.error=None
        with contextlib.closing(self.store.connect()) as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY,conversation_id TEXT,text TEXT,state TEXT,error TEXT,job_id TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS project_tests(project_id TEXT PRIMARY KEY,command TEXT);
            CREATE TABLE IF NOT EXISTS message_files(submission_id TEXT,attachment_id TEXT,PRIMARY KEY(submission_id,attachment_id));''')
            db.execute('CREATE TABLE IF NOT EXISTS submission_packets(id TEXT PRIMARY KEY,packet TEXT,kind TEXT)')
            db.execute("UPDATE submissions SET state='DISPATCHED',job_id=(SELECT job_id FROM job_intakes WHERE job_intakes.id=submissions.id) WHERE id IN (SELECT id FROM job_intakes)")
            # Planning is read-only: interrupted intake can be resumed without replaying worker effects.
            db.execute("UPDATE submissions SET state='INTERRUPTED',error='The app closed during planning. Retry this request.' WHERE state='PLANNING'")
        from .continuation import Continuation
        from .connections import Connections
        from .memory import Memory
        from .projectmap import ProjectMap
        from .recipes import RecipeLibrary
        from .workforce import ensure_schema as ensure_workforce_schema
        from .assignment import ensure_schema as ensure_assignment_schema
        from .delegation import ensure_schema as ensure_delegation_schema
        from .parallel import ensure_schema as ensure_parallel_schema
        Memory(self.store)
        ProjectMap(self.store)
        Continuation(self.store)
        RecipeLibrary(self.store).install_builtins()
        ensure_workforce_schema(self.store)
        ensure_assignment_schema(self.store)
        ensure_delegation_schema(self.store)
        ensure_parallel_schema(self.store)
        Connections(self.store)
        self.supervisor=threading.Thread(target=self._tick,daemon=True);self.supervisor.start()
        def telemetry():
            while not self.stop.is_set():
                try:
                    if 'codex' in self.engine.adapters and not os.environ.get('KEL_SKIP_TELEMETRY'):
                        from .telemetry import refresh_codex
                        refresh_codex(self.store)
                except Exception:pass  # A missing observation is not a zero quota or a free price.
                self.stop.wait(60)
        self.telemetry=threading.Thread(target=telemetry,daemon=True);self.telemetry.start()

    def shutdown(self):
        """In-process shutdown: stop supervision, close the engine, join workers."""
        self.stop.set()
        if self.supervisor.is_alive():
            self.supervisor.join(timeout=5)
        self.engine.close()
        self.requests.shutdown(wait=True,cancel_futures=True)
        # The telemetry thread may be inside a provider call (bounded by that call's own timeout);
        # joining it releases its stderr handle before the caller cleans the data root up.
        if self.telemetry.is_alive():
            self.telemetry.join(timeout=30)

    def _tick(self):
        while not self.stop.wait(.2):
            try:self.engine.tick();self.error=None
            except Exception as exc:self.error=type(exc).__name__+': '+str(exc)

    def submit(self,data):
        sid=data.get('id') or secrets.token_hex(16);cid=data.get('conversation','main');text=data.get('text','')
        if not isinstance(text,str):
            # PERSIST-CANONICAL (Round 2.5 R5): a malformed request answers in a plain sentence.
            raise PolicyError('Request must be 1 to 20000 characters')
        text=text.strip()
        if not text or len(text)>20000:raise PolicyError('Request must be 1 to 20000 characters')
        attachments=data.get('attachments',[])
        if not isinstance(attachments,list) or len(attachments)>10:raise PolicyError('Choose at most ten attachments')
        job_id=data.get('job_id')
        if job_id is not None:
            job_id=str(job_id).lower()
            hexish=job_id.replace('-','')
            if len(hexish)!=32 or any(ch not in '0123456789abcdef' for ch in hexish):
                raise PolicyError('Invalid job id')
        kind=data.get('kind')
        greenfield_flag=False
        if kind is None:
            # Deterministic initial routing: the client omitted an explicit kind,
            # so classify locally instead of paying for a frontier-model decision.
            from .router import classify
            result=classify(text)
            kind=result['kind'];greenfield_flag=bool(result.get('greenfield'))
        packet=self.context.handoff(cid,text,attachments)
        try:
            from .memory import Memory
            from .projectmap import ProjectMap
            from .composer import Composer
            with contextlib.closing(self.store.connect()) as db:
                project_row=db.execute('SELECT project_id FROM conversations WHERE id=?',
                                       (cid,)).fetchone()
            if project_row:
                packet['context_packet']=Composer(
                    self.store,Memory(self.store),ProjectMap(self.store)).build(
                    project_row['project_id'],text,conversation_id=cid,purpose='submit')
        except Exception:
            pass  # enrichment is additive; the handoff packet remains the fallback
        if job_id:packet['continuation']={'job_id':job_id}
        recipe_run=data.get('recipe')
        if recipe_run is not None:
            if not isinstance(recipe_run,dict) or not isinstance(recipe_run.get('recipe_id'),str):
                raise PolicyError('Invalid recipe invocation')
            packet['recipe_invocation']={'recipe_id':recipe_run['recipe_id'],
                                         'inputs':recipe_run.get('inputs') or {}}
        with self.store.transaction() as db:
            old=db.execute('SELECT * FROM submissions WHERE id=?',(sid,)).fetchone()
            if old:
                if old['conversation_id']!=cid or old['text']!=text:raise PolicyError('Request ID belongs to different content')
                return sid
            db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',(sid,cid,text,'PLANNING',None,None,time.time()))
            db.execute('INSERT INTO submission_packets VALUES(?,?,?)',(sid,encode(packet),kind))
            for aid in attachments:db.execute('INSERT INTO message_files VALUES(?,?)',(sid,aid))
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',(cid,'user',text,time.time()))
            db.execute("UPDATE conversations SET title=? WHERE id=? AND title='New conversation'",(text[:65],cid))
        self.requests.submit(self._plan,sid,cid,text,packet,kind,greenfield_flag)
        return sid

    def _plan(self,sid,cid,text,packet,kind=None,greenfield_flag=False):
        try:
            lower=text.lower().strip()
            coding_verb=lower.startswith(CODING_VERBS)
            explicit_job=(packet.get('continuation') or {}).get('job_id')
            continue_verb=lower.startswith(('continue','resume','pick up','carry on','keep going'))
            if kind=='status' or lower in ('status','what are you working on?','what is running?'):
                jobs=[j for j in self.store.list_jobs() if j['conversation']==cid and j['state'] not in ('CLOSED','CANCELLED')]
                answer='No work is running.' if not jobs else '\n'.join(j['contract']['request']+' — '+j['state'].lower().replace('_',' ') for j in jobs)
                self.store.add_message(answer,'assistant',cid);jid=None
            elif kind=='recipe' or packet.get('recipe_invocation'):
                jid=self._recipe_run(sid,cid,text,packet)
            elif kind=='continue' or explicit_job or continue_verb:
                jid=self._continuation(cid,text,packet)
            elif coding_verb and not greenfield_flag and not packet['project']['root']:
                # Coding intent with no selected project and no explicit
                # greenfield request: ask instead of guessing or silently
                # adopting a temp/donor workspace as the project root.
                self.store.add_message('This looks like a request to change code, but no project is selected. Open Saved context and choose the project to work in (it needs a test command), or ask me to create a new project and I will build it from scratch.', 'assistant', cid)
                jid=None
            elif not needs_work(text) and ((kind in ('chat','conversation') and not coding_verb) or (kind is None and not needs_research(text) and not lower.startswith(('research','search','look up','find current','write','create','draft','summarize','fix','build','implement','change','add','remove','update','make','refactor','test','review','analyze','compare','prepare')))):
                model=self.model
                if model is None:
                    available=next((n for n in ('codex','claude') if n in self.engine.adapters),None)
                    if not available:raise PolicyError('Connect a model before sending a message')
                    model=NativeAdapter(available,self.store.root/'workspaces'/available,self.store.root/'logs')
                kwargs={}
                image_files=[f for f in packet['files'] if f.get('image_path')]
                if image_files:
                    if model is not self.model:raise PolicyError('The image worker is not connected')
                    kwargs['images']=[{'mime':f['mime'],'data':base64.b64encode((self.store.root/f['image_path']).read_bytes()).decode()} for f in image_files]
                result=model.execute('Answer as Kel, one helpful assistant. Keep the reply plain and concise. '
                    'Do not imply you performed external actions. You may answer questions about the saved context.\n'+encode(packet),**kwargs)
                if result.get('outcome')!='SUCCESS':raise PolicyError(result.get('error','The model did not respond'))
                self.store.add_message(result['text'],'assistant',cid);jid=None
            else:
                coding=kind=='coding' or (packet['project']['root'] and coding_verb)
                if coding:
                    root=packet['project']['root']
                    # Greenfield intent ("create me an app") always wins, even when the
                    # active project already has a root such as a desktop temp workspace.
                    greenfield=bool(greenfield_flag) or not bool(root)
                    if greenfield:
                        # Greenfield build: the user asked Kel to CREATE an app. Kel owns the
                        # workspace: a fresh git repo under Documents/Kel Projects with a
                        # deterministic smoke-test command the worker must make pass.
                        slug='-'.join(''.join(ch if ch.isalnum() else ' ' for ch in lower).split())[:36] or 'app'
                        root=Path.home()/'Documents'/'Kel Projects'/f'{slug}-{secrets.token_hex(2)}'
                        # V1.5: creating project files is an effect; it crosses the boundary under the
                        # user-project-create policy (user actor, confined to the Kel Projects root).
                        from .authorize import authorize
                        decision=authorize(self.store,{'actor':'user','action_kind':'write','target':str(root),
                            'metadata':{'operation':'create-project','what':'create a new project folder',
                                        'why':'the user asked Kel to build a new project'}})
                        if decision['outcome']!='ALLOW':
                            raise PolicyError('Kel cannot create the project folder: '+
                                              str(decision.get('reason') or decision.get('rule')))
                        root.mkdir(parents=True,exist_ok=True)
                        import subprocess as _sp
                        _sp.run(['git','init',str(root)],capture_output=True,check=False)
                        # Keep worker bytecode and caches out of the change set.
                        (root/'.gitignore').write_text('__pycache__/\n*.pyc\n*.pyo\n',encoding='utf-8')
                        # A coding snapshot diffs against HEAD; give the new repo an
                        # empty initial commit so HEAD exists before the worker runs.
                        _sp.run(['git','-C',str(root),'-c','user.name=Kel','-c','user.email=kel@localhost',
                                 'commit','--allow-empty','-m','Initial empty project (created by Kel)'],
                                capture_output=True,check=False)
                        tests=['python','smoke_test.py']
                        project_id=self.context.project(slug,str(root),'Created by Kel for: '+text[:120])
                        with self.store.transaction() as db:
                            db.execute('INSERT OR REPLACE INTO project_tests VALUES(?,?)',(project_id,encode(tests)))
                    else:
                        with contextlib.closing(self.store.connect()) as db:
                            row=db.execute('SELECT command FROM project_tests WHERE project_id=?',(packet['project']['id'],)).fetchone()
                        if not row:raise PolicyError('This project needs a test command. Set it in Project context before coding.')
                        project_id=packet['project']['id'];tests=json.loads(row['command'])
                    contract=compile_coding(text,root,tests,project_id,greenfield=greenfield)
                    contract['planner']={'provider':None,'model':None,'compiler':contract.get('compiler')}
                elif kind=='research' or needs_research(text):
                    from .research import compile_research
                    contract=compile_research(text,self.commander,packet)
                    contract['planner']={'provider':None,'model':None,'compiler':contract.get('compiler')}
                else:
                    if self.commander:
                        contract, meta = self.commander.plan(text, context=packet)
                        contract['planner'] = {**self.commander.descriptor(), 'compiler': contract.get('compiler')} if meta.get('mode')=='model_proposal' else {'provider': None, 'model': None, 'compiler': contract.get('compiler')}
                    else:
                        contract = compile_document(text)
                        contract['planner'] = {'provider': None, 'model': None, 'compiler': contract.get('compiler')}
                contract['context']=packet
                if any(f.get('image_path') for f in packet['files']):contract['required_capabilities']=['image','text']
                contract['submission_id']=sid
                # Create and link the job atomically with intake to prevent duplicate effects on restart.
                jid=self.engine.submit(contract,budget=max(12,len(contract['milestones'])*4),conversation=cid)
                self._link_origin(jid,cid,sid)
                with self.store.transaction() as db:
                    # create() records the source request; remove only its duplicate intake message.
                    dup=db.execute('SELECT seq FROM messages WHERE conversation_id=? AND role=? AND text=? AND job_id IS NULL ORDER BY seq DESC LIMIT 1',(cid,'user',text)).fetchone()
                    if dup:db.execute('DELETE FROM messages WHERE seq=?',(dup['seq'],))
            with self.store.transaction() as db:db.execute("UPDATE submissions SET state='DISPATCHED',job_id=? WHERE id=?",(jid,sid))
        except Exception as exc:
            with self.store.transaction() as db:db.execute("UPDATE submissions SET state='FAILED',error=? WHERE id=?",(str(exc),sid))

    def _recipe_run(self,sid,cid,text,packet):
        """Run a validated recipe through the existing engine (no second runtime)."""
        from .recipes import RecipeLibrary, compile_recipe
        library=RecipeLibrary(self.store)
        invocation=packet.get('recipe_invocation') or {}
        project_id=(packet.get('project') or {}).get('id') or 'default'
        try:
            info=library.get(invocation.get('recipe_id',''),project_id=project_id)
        except PolicyError as exc:
            self.store.add_message('I could not find that recipe. '+str(exc),'assistant',cid)
            return None
        recipe=info['recipe']
        if recipe['recipe_id']=='continue-work':
            return self._continuation(cid,text,packet)
        root=tests=None
        needs_code=recipe['kind']=='coding' or any(
            step.get('kind_override')=='coding' for step in recipe['steps'])
        if needs_code:
            root=(packet.get('project') or {}).get('root')
            with contextlib.closing(self.store.connect()) as db:
                row=db.execute('SELECT command FROM project_tests WHERE project_id=?',(project_id,)).fetchone()
            tests=json.loads(row['command']) if row else None
        try:
            contract=compile_recipe(recipe,invocation.get('inputs') or {},project_id,root=root,tests=tests)
        except PolicyError as exc:
            self.store.add_message(str(exc),'assistant',cid)
            return None
        contract['planner']={'provider':None,'model':None,'compiler':contract.get('compiler')}
        contract['submission_id']=sid
        jid=self.engine.submit(contract,budget=max(12,len(contract['milestones'])*4),conversation=cid)
        self._link_origin(jid,cid,sid)
        with self.store.transaction() as db:
            dup=db.execute('SELECT seq FROM messages WHERE conversation_id=? AND role=? AND text=? AND job_id IS NULL ORDER BY seq DESC LIMIT 1',(cid,'user',text)).fetchone()
            if dup:db.execute('DELETE FROM messages WHERE seq=?',(dup['seq'],))
        return jid

    def _project_of(self,cid):
        with contextlib.closing(self.store.connect()) as db:
            row=db.execute('SELECT project_id FROM conversations WHERE id=?',(cid,)).fetchone()
        if not row:raise PolicyError('Conversation missing')
        return row['project_id']

    def _work(self,cid):
        """Compact project work context for the shell's Work panel."""
        from .memory import Memory
        from .projectmap import ProjectMap
        from .recipes import RecipeLibrary
        project_id=self._project_of(cid)
        memory=Memory(self.store)
        data={'schema':1,'project_id':project_id,
              'memory':{'records':[{'id':r['id'],'type':r['type'],'topic':r['topic'],
                                    'summary':r['summary'],'value':r['value'],'trust':r['trust'],
                                    'status':r['status'],'user_confirmed':r['user_confirmed'],
                                    'source_type':r['source_type'],'source_ref':r['source_ref'],
                                    'confidence':r['confidence'],'updated':r['updated']}
                                   for r in memory.records(project_id,limit=100)],
                        'proposals':memory.proposals(project_id,state='open'),
                        'conflicts':memory.conflicts(project_id)},
              'map':None,
              'recipes':{'entries':RecipeLibrary(self.store).entries(project_id=project_id)}}
        latest=ProjectMap(self.store).get(project_id)
        if latest:
            data['map']={'version':latest['version'],'fingerprint':latest['fingerprint'],
                         'updated':latest['updated'],'note':latest['note'],
                         'sections':[{'name':name,'trust':section.get('trust','verified'),
                                      'stale':bool(section.get('stale')),
                                      'updated':section.get('updated'),
                                      'digest':section.get('digest'),
                                      'sources':section.get('sources',[])}
                                     for name,section in latest['sections'].items()]}
        # V2-11: the work brief the person sees. Live facts only — what shipped, what is open, why
        # it stopped, and what (if anything) only they can do. Nothing here re-runs any work.
        from .continuation import Continuation
        cont=Continuation(self.store)
        now=time.time()
        with contextlib.closing(self.store.connect()) as db:
            pending={row['job_id']:row['n'] for row in db.execute(
                "SELECT job_id,COUNT(*) AS n FROM approvals WHERE status='PENDING' GROUP BY job_id")}
            last={row['aggregate_id']:row['at'] for row in db.execute(
                "SELECT aggregate_id,MAX(at) AS at FROM events GROUP BY aggregate_id")}
        jobs=[]
        needs=0
        closed_shown=0
        for job in self.store.list_jobs():
            if job['conversation']!=cid:
                continue
            active=job['state'] not in ('CLOSED','CANCELLED')
            if not active:
                if closed_shown>=3 or (last.get(job['id']) or 0)<now-86400:
                    continue
                closed_shown+=1
            milestones=job.get('milestones') or {}
            brief=cont.resume_brief(job['id'])
            entry={'job_id':job['id'],'title':brief['title'],'state':job['state'],
                   'verdict':job.get('verdict'),
                   'accepted':len(brief['shipped']),'total':len(milestones),
                   'open':len(brief['open']),'fenced':brief['fenced'],
                   'needs_you':brief['needs_you'],'why':brief['why'],'next':brief['next'],
                   'last_at':last.get(job['id'])}
            if pending.get(job['id']):
                entry.update(needs_you=True,why='Waiting for your decision on a gated step.',
                             next='Decide on the request card in the conversation — or in Work context.')
            if not active:
                entry.update(needs_you=False,
                             why=('Done and verified.' if job.get('verdict')=='VERIFIED'
                                  else 'Settled: '+str(job.get('verdict') or 'unresolved').lower()+'.'),
                             next='Nothing needed — ask for a new change for more work.')
            if entry['needs_you']:
                needs+=1
            jobs.append(entry)
        jobs.sort(key=lambda item:(not item['needs_you'],-(item['last_at'] or 0)))
        data['work']={'generated':now,'needs_you':needs,'jobs':jobs}
        return data

    def _owned_memory(self,project_id,memory_id):
        with contextlib.closing(self.store.connect()) as db:
            row=db.execute('SELECT project_id FROM memories WHERE id=?',(memory_id,)).fetchone()
        if not row or row['project_id']!=project_id:
            raise PolicyError('Memory belongs to another project')

    def _memory_action(self,data):
        from .memory import Memory
        cid=data.get('conversation','main')
        project_id=self._project_of(cid)
        memory=Memory(self.store)
        action=data.get('action')
        memory_id=data.get('id')
        if action=='confirm':
            self._owned_memory(project_id,memory_id)
            memory.confirm(memory_id)
            return {'ok':True}
        if action=='correct':
            self._owned_memory(project_id,memory_id)
            summary=data.get('summary')
            value=data.get('value')
            if value is None and isinstance(summary,str) and summary.strip():
                value={'statement':summary}
            return {'id':memory.correct(memory_id,value=value,summary=summary)}
        if action=='retract':
            self._owned_memory(project_id,memory_id)
            memory.retract(memory_id,reason=data.get('reason',''))
            return {'ok':True}
        if action=='forget':
            self._owned_memory(project_id,memory_id)
            memory.forget(memory_id)
            return {'ok':True}
        if action=='resolve_conflict':
            with contextlib.closing(self.store.connect()) as db:
                row=db.execute('SELECT project_id FROM memory_conflicts WHERE id=?',(memory_id,)).fetchone()
            if not row or row['project_id']!=project_id:
                raise PolicyError('Conflict belongs to another project')
            return {'resolution':memory.resolve_conflict(memory_id,data.get('choice'))}
        if action=='proposals':
            wanted=data.get('state') or 'open'
            return {'proposals':memory.proposals(project_id,state=None if wanted=='all' else wanted,
                                                 limit=data.get('limit') or 100)}
        if action=='proposal':
            item=memory.proposal(memory_id)
            if item['project_id']!=project_id:
                raise PolicyError('Proposal belongs to another project')
            return item
        if action in ('accept_proposal','reject_proposal','defer_proposal'):
            item=memory.proposal(memory_id)
            if item['project_id']!=project_id:
                raise PolicyError('Proposal belongs to another project')
            if action=='accept_proposal':
                return memory.accept_proposal(memory_id,note=data.get('note',''))
            if action=='reject_proposal':
                return {'ok':True,'id':memory.reject_proposal(memory_id,reason=data.get('reason',''))}
            return {'ok':True,'id':memory.defer_proposal(memory_id,note=data.get('note',''))}
        if action=='history':
            return {'entries':memory.history_view(project_id,limit=data.get('limit') or 50)}
        if action=='learnings':
            # V2-10: what Kel learned, on the person's own surface. Switched-off and stale learnings
            # stay inspectable when asked for; only enabled ones ever reach context.
            from .learning import learnings_view
            return {'learnings':learnings_view(self.store,project_id=project_id,
                                               include_stale=bool(data.get('include_stale')),
                                               include_disabled=bool(data.get('include_disabled')))}
        if action=='learning':
            from .learning import explain_learning
            self._owned_memory(project_id,memory_id)
            return explain_learning(self.store,memory_id)
        if action in ('disable_learning','enable_learning'):
            from .learning import set_enabled
            self._owned_memory(project_id,memory_id)
            return set_enabled(self.store,memory_id,action=='enable_learning')
        if action=='suggest_learnings':
            # Evidence-thresholded suggestions; nothing is applied — they land in the review queue.
            from .learning import suggest_learnings
            return suggest_learnings(self.store,project_id=project_id,minimum=data.get('minimum'))
        raise PolicyError('Unknown memory action')

    def _map_action(self,data):
        from .projectmap import ProjectMap
        cid=data.get('conversation','main')
        project_id=self._project_of(cid)
        maps=ProjectMap(self.store)
        action=data.get('action')
        if action=='refresh':
            latest=maps.refresh(project_id,force=bool(data.get('force')),reason='work-context')
            return {'version':latest['version'],'fingerprint':latest['fingerprint'],
                    'note':latest['note']}
        if action=='stale':
            return {'sections':maps.stale_sections(project_id,data.get('changed') or [])}
        raise PolicyError('Unknown map action')

    def _recipes_action(self,data):
        from .recipes import RecipeLibrary, compile_recipe
        cid=data.get('conversation','main')
        project_id=self._project_of(cid)
        library=RecipeLibrary(self.store)
        action=data.get('action')
        if action=='list':
            return {'entries':library.entries(project_id=project_id)}
        if action=='get':
            info=library.get(data.get('recipe_id',''),project_id=project_id)
            return {'recipe':info['recipe'],'scope':info['scope'],'version':info['version'],
                    'digest':info['digest']}
        if action=='preview':
            info=library.get(data.get('recipe_id',''),project_id=project_id)
            recipe=info['recipe']
            if recipe['recipe_id']=='continue-work':
                compiled=compile_recipe(recipe,data.get('inputs') or {},project_id)
                return {'continuation':True,'stages':compiled['stages'],'request':compiled['request']}
            root=tests=None
            needs_code=recipe['kind']=='coding' or any(
                step.get('kind_override')=='coding' for step in recipe['steps'])
            if needs_code:
                with contextlib.closing(self.store.connect()) as db:
                    project=db.execute('SELECT root FROM projects WHERE id=?',(project_id,)).fetchone()
                    row=db.execute('SELECT command FROM project_tests WHERE project_id=?',(project_id,)).fetchone()
                root=project['root'] if project else None
                tests=json.loads(row['command']) if row else None
            try:
                contract=compile_recipe(recipe,data.get('inputs') or {},project_id,root=root,tests=tests)
            except PolicyError as exc:
                return {'needs_project':True,'message':str(exc)}
            return {'request':contract['request'],'kind':contract['kind'],
                    'milestones':[{'id':m['id'],'objective':m['objective'],
                                   'depends_on':m['depends_on'],'checks':m['checks']}
                                  for m in contract['milestones']],
                    'permissions':recipe['permissions'],
                    'terminal_states':recipe['terminal_states'],
                    'budget':contract['budget'],'recipe':contract['recipe']}
        if action=='run':
            info=library.get(data.get('recipe_id',''),project_id=project_id)
            sid=self.submit({'text':'Run recipe '+info['recipe']['name'],'conversation':cid,
                             'kind':'recipe',
                             'recipe':{'recipe_id':data.get('recipe_id'),
                                       'inputs':data.get('inputs') or {}}})
            return {'submission':sid}
        if action=='propose_from_job':
            return library.propose_from_job(data.get('job_id',''))
        if action=='save':
            recipe=data.get('recipe')
            if not isinstance(recipe,dict):
                raise PolicyError('A recipe object is required')
            return library.save(recipe,scope='project',project_id=project_id,
                                confirm=data.get('confirm') is True)
        raise PolicyError('Unknown recipe action')

    def _link_origin(self,job_id,conversation_id,sid):
        from .continuation import Continuation
        try:
            Continuation(self.store).attach(job_id,conversation_id,kind='origin',reason='submission '+str(sid)[:8])
        except Exception:
            pass  # linking is auxiliary metadata; never fail an accepted submission over it

    def _continuation(self,cid,text,packet):
        """Natural-language continuation: durable state decides, never transcript text."""
        from .continuation import Continuation
        cont=Continuation(self.store)
        project_id=(packet.get('project') or {}).get('id')
        explicit=(packet.get('continuation') or {}).get('job_id')
        if explicit:
            try:
                job=self.store.get(explicit)
            except (KeyError, PolicyError):
                self.store.add_message('I could not find that job id.','assistant',cid)
                return None
            candidates={c['job_id'] for c in cont.candidates(project_id)}
            if explicit in candidates:
                out=cont.execute_resume(explicit,cid,reason='user: '+text[:120])
                self.store.add_message(cont.explain(explicit)+' Current state: '+out['state'].lower()+'.','assistant',cid)
            elif job.get('verdict')=='VERIFIED':
                self.store.add_message('That work is already verified and closed. Ask for a new change if you want more done.','assistant',cid)
            else:
                self.store.add_message('That job belongs to another project or is not continuable. Continue Work only resumes unfinished jobs inside the current project.','assistant',cid)
            return None
        result=cont.resolve(project_id,cid,text)
        if result['kind']=='single':
            top=result['candidate']
            out=cont.execute_resume(top['job_id'],cid,reason='user: '+text[:120])
            self.store.add_message(cont.explain(top['job_id'])+' Current state: '+out['state'].lower()+'.','assistant',cid)
        elif result['kind']=='choice':
            lines=['I found several unfinished jobs in this project. Which one should I continue?']
            for choice in result['candidates']:
                lines.append('- %s — %s, %d/%d milestones accepted (job %s)'%(choice['title'] or 'Untitled work',choice['state'].lower().replace('_',' '),choice['accepted'],choice['total'],choice['job_id']))
            lines.append('Reply with "continue <job id>", or use the Continue Work controls in Work context.')
            self.store.add_message('\n'.join(lines),'assistant',cid)
        else:
            self.store.add_message('There is no unfinished work in this project to continue. New requests start fresh work.','assistant',cid)
        return None

    def state(self,cid='main'):
        with contextlib.closing(self.store.connect()) as db:
            projects=[dict(r) for r in db.execute('SELECT * FROM projects ORDER BY name')]
            for p in projects:
                row=db.execute('SELECT command FROM project_tests WHERE project_id=?',(p['id'],)).fetchone();p['test_command']=json.loads(row['command']) if row else None
            conversations=[dict(r) for r in db.execute('SELECT * FROM conversations ORDER BY created DESC')]
            messages=[dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY seq',(cid,))]
            submissions=[dict(r) for r in db.execute('SELECT * FROM submissions WHERE conversation_id=? ORDER BY created',(cid,))]
            approvals=[dict(r) for r in db.execute("SELECT a.*,x.action FROM approvals a JOIN approval_actions x ON x.approval_id=a.id WHERE a.status='PENDING'")]
            from .chat_approvals import plain_summary
            for a in approvals:
                try:
                    action=json.loads(a['action']) if isinstance(a['action'],str) else (a['action'] or {})
                except Exception:
                    action={}
                a['action_summary']=plain_summary(action)
            files=[dict(r) for r in db.execute('SELECT id,name,size,mime FROM attachments WHERE conversation_id=?',(cid,))]
        project_id=next((c['project_id'] for c in conversations if c['id']==cid),None)
        continuation=[]
        if project_id:
            from .continuation import Continuation
            try:
                continuation=Continuation(self.store).candidates(project_id)
            except Exception:
                continuation=[]  # the Work surface must render even if continuation state is unavailable
        jobs=[j for j in self.store.list_jobs() if j['conversation']==cid]
        # D12 — the routing decision behind each active run (why this provider/model). The engine
        # already records it on run.claimed; user surfaces translate it into plain language.
        routes={}
        active={j['id'] for j in jobs if j['state'] not in ('CLOSED','CANCELLED')}
        for event in self.store.events():
            if event.get('type')!='run.claimed' or event.get('aggregate_id') not in active:
                continue
            try:
                detail=(json.loads(event.get('payload') or '{}') or {}).get('detail') or {}
            except (TypeError, ValueError):
                continue
            route=detail.get('route')
            if route:
                routes[event['aggregate_id']]={'provider':detail.get('provider'),'route':route,'at':event.get('at')}
        return {'projects':projects,'conversations':conversations,'messages':messages,'jobs':jobs,
                'submissions':submissions,'approvals':approvals,'attachments':files,'continuation':continuation,'error':self.error,
                'providers':list(self.engine.adapters),'routes':routes,'connected':True,'engine_version':ENGINE_VERSION,'guardrails_ok':self.engine.tampered is None,'draining':self.draining,
                'restore':_restore_outcome(self.store.root)}

    def action(self,path,data):
        with self.lifecycle_lock:
            if self.draining:raise PolicyError('Kel is restarting for an update. Try again after it opens.')
            if path=='/api/shutdown-idle':
                with self.engine.lock:
                    with contextlib.closing(self.store.connect()) as db:
                        planning=db.execute("SELECT count(*) FROM submissions WHERE state='PLANNING'").fetchone()[0]
                    if planning or self.engine.active or self.engine.reviews or any(j['state'] not in ('CLOSED','CANCELLED') for j in self.store.list_jobs()):
                        raise PolicyError('Work is still open. Finish or cancel it before updating Kel.')
                    self.draining=True;self.stop.set()
                return {'ok':True,'draining':True}
            return self._action(path,data)

    def _action(self,path,data):
        # V1.5: one identity rule for every engine action family. Actor identity is bound by the
        # authenticated session, never by the request payload.
        if 'actor' in data:
            raise PolicyError('Actor identity comes from the authenticated Kel session, not from the request payload')
        if path=='/api/send':return {'id':self.submit(data)}
        if path=='/api/memory':return self._memory_action(data)
        if path=='/api/map':return self._map_action(data)
        if path=='/api/recipes':return self._recipes_action(data)
        if path=='/api/retry':
            with self.store.transaction() as db:
                row=db.execute('SELECT s.*,p.packet,p.kind FROM submissions s JOIN submission_packets p ON p.id=s.id WHERE s.id=?',(self._required(data,'id','Pick a request to retry first.'),)).fetchone()
                if not row or row['state'] not in ('FAILED','INTERRUPTED'):raise PolicyError('This request is not ready for retry')
                db.execute("UPDATE submissions SET state='PLANNING',error=NULL WHERE id=?",(row['id'],))
            self.requests.submit(self._plan,row['id'],row['conversation_id'],row['text'],json.loads(row['packet']),row['kind'])
            return {'id':row['id']}
        if path=='/api/conversation':return {'id':self.context.conversation(data.get('project','default'))}
        if path=='/api/project':
            pid=self.context.project(data['name'],data.get('root') or None,data.get('context',''),data.get('id'))
            command=data.get('test_command')
            if command:
                if not isinstance(command,list) or not all(isinstance(s,str) and s for s in command):raise PolicyError('Test command must be a list of arguments')
                with self.store.transaction() as db:db.execute('INSERT OR REPLACE INTO project_tests VALUES(?,?)',(pid,encode(command)))
            return {'id':pid}
        if path=='/api/attach':return {'id':self.context.attach(data['conversation'],data['name'],base64.b64decode(data['content'],validate=True),data.get('mime','text/plain'))}
        if path=='/api/control':
            self.engine.control(self._required(data,'job','Pick a request first.'),
                                self._required(data,'action','Pick what Kel should do first.'));return {'ok':True}
        if path=='/api/apply':
            from .apply_changes import apply_checked
            return apply_checked(self.store,self._required(data,'job','Kel could not find that change to apply.'),actor='user')
        if path=='/api/approval':
            if 'actor' in data:
                raise PolicyError('Actor identity comes from the authenticated Kel session, not from the request payload')
            with contextlib.closing(self.store.connect()) as db:
                row=db.execute('SELECT x.action,a.job_id FROM approval_actions x JOIN approvals a ON a.id=x.approval_id WHERE x.approval_id=?',(self._required(data,'id','Permission request missing'),)).fetchone()
            if not row:raise PolicyError('Permission request missing')
            # Campaign C AUD-MAJOR-001: this route may not resolve unscoped by id - the same
            # ownership check as the chat path runs here, with omission acting as `main`.
            from .chat_approvals import require_owned
            require_owned(self.store,'action',data.get('id'),data.get('conversation'))
            action=json.loads(row['action']);status=self.store.resolve_approval(data.get('id'),action,bool(data.get('allow')))
            if status=='APPROVED' and data.get('remember'):
                job=self.store.get(row['job_id']);self.context.grant(job['contract'].get('project_id','default'),action)
            return {'status':status}
        if path=='/api/revoke':self.context.revoke(data['project']);return {'ok':True}
        if path=='/api/brief':
            from .solution import SolutionBriefs
            payload=dict(data);payload.setdefault('project_id',self._project_of(data.get('conversation','main')))
            return SolutionBriefs(self.store).apply(payload)
        if path=='/api/team':
            from .team import Team
            return Team(self.store).apply(data)
        if path=='/api/providers':
            from .providers import Providers
            return Providers(self.store).apply(data)
        if path=='/api/autonomy':
            from .autonomy import Autonomy
            # Lease issuance is Kel's decision; the shell can inspect, resolve, and revoke only.
            if data.get('action') not in ('leases','requests','guardrails','decisions','check','revoke','resolve','emergency_stop'):
                raise PolicyError("Lease issuance is Kel's decision; this action is not available through the shell")
            payload=dict(data);payload['actor']='user'
            result=Autonomy(self.store).apply(payload)
            if data.get('action')=='emergency_stop':
                for job_id in result.get('paused_jobs',[]):
                    self.engine.control(job_id,'pause')
            if data.get('action')=='resolve' and result.get('status')=='GRANTED':
                # A granted boundary request wakes exactly the job that was waiting on it.
                from .authorize import resume_after_grant
                resume_after_grant(self.store,result['request_id'])
            if data.get('action')=='resolve' and result.get('status')=='DENIED':
                # The conversation gets one plain sentence about the consequence.
                from .chat_approvals import announce_denial
                announce_denial(self.store,result['request_id'])
            return result
        if path=='/api/diagnostics':
            from .diagnostics import Diagnostics
            return Diagnostics(self.store,ENGINE_VERSION).apply(data)
        if path=='/api/vetting':return self._vetting_action(data)
        if path=='/api/transcription':return self._transcription_action(data)
        if path=='/api/dogfood':return self._dogfood_action(data)
        if path=='/api/connections':return self._connections_action(data)
        if path=='/api/model':return self._model_action(data)
        if path=='/api/capabilities':return self._capabilities_action(data)
        if path=='/api/data-path':return {'root':str(self.store.root),'database':str(self.store.db_path)}
        if path=='/api/backup':return self._backup_action(data)
        if path=='/api/search':
            from .search import Search
            return Search(self.store).run(data.get('q',''))
        if path=='/api/approvals':
            return self._approvals_action(data)
        raise PolicyError('Unknown action')

    def _approvals_action(self,data):
        # In-chat approvals: presentation surface only - resolution runs through the SAME
        # durable paths as Work (the actor guard above already refused a payload identity).
        from .chat_approvals import resolve
        if data.get('action','resolve')!='resolve':
            raise PolicyError('Unknown approvals action')
        return resolve(self.store,data.get('kind'),data.get('id'),bool(data.get('allow')),
                       grant_kind=data.get('grant_kind','once'),remember=bool(data.get('remember')),
                       conversation=data.get('conversation'))

    def _approvals_list(self,conversation):
        from .chat_approvals import items
        return {'items':items(self.store,conversation or 'main')}

    def _vetting_action(self,data):
        # Design Vetting Sessions. One ingestion service serves chat answers, panel actions,
        # pasted text and direct callers; this layer only routes and persists the durable
        # out-of-band messages (panel-driven start/process/finish) as conversation content.
        from .vetting_session import Vetting
        # The acting conversation is the session scope (audit SEC-01): a by-id vetting action can
        # only touch a session that belongs to the conversation the caller is acting in.
        vetting=Vetting(self.store,conversation=(data.get('conversation') or 'main'))
        try:
            result=self._vetting_route(vetting,data)
        except PolicyError:
            raise
        except Exception:
            # Same contract as the transcription family (audit COR-06/ERR-01): a missing or
            # unexpected payload never surfaces as a raw exception string.
            raise PolicyError('Kel could not finish that design action. Try again.') from None
        # Confirmed decisions are compared against saved project knowledge once the session
        # transaction has committed; a disagreeing stored rule queues on the review surface.
        created=vetting.flush_memory_checks()
        if created and isinstance(result,dict):
            result['memory_proposals']=created
        return result

    def _vetting_route(self,vetting,data):
        action=data.get('action')
        conversation=data.get('conversation') or 'main'
        if action=='start':
            result=vetting.start(self._project_of(conversation),conversation,data.get('topic',''))
            self.store.add_message(result['message'],'assistant',conversation)
            result['panel']=vetting.panel(conversation=conversation)
            return result
        if action=='ingest_chat':
            result=vetting.ingest_chat(conversation,data.get('text',''),source=data.get('source','chat'))
            kind=result.get('kind');message=result.get('message') or ''
            # Durable acknowledgments: the donor transcript renders stored engine messages, so the
            # batch and each 'Recorded: n of m recorded.' line are written as conversation content
            # (a lightweight progress state, never a synthesis or an assistant turn).
            durable=(kind in ('started','ingested','proposal')
                     or (kind=='control' and result.get('verb') in ('process','finish_spec')))
            if durable and message:
                self.store.add_message(message,'assistant',conversation)
            return result
        if action=='ingest':
            session=self._required(data,'session','Open a design-vetting session first.')
            result=vetting.ingest(session,data.get('text',''),source=data.get('source','direct'))
            return {'kind':'ingested','session_id':session,'progress':result['progress'],
                    'applied':result['applied']['applied'],'conflicts':result['conflicts_open'],
                    'proposals':result['proposals'],'unmatched':result['unmatched']}
        if action=='panel':
            return vetting.panel(conversation=conversation,session_id=data.get('session'))
        if action=='process':
            result=vetting.process(self._required(data,'session','Open a design-vetting session first.'))
            self.store.add_message(result['message'],'assistant',conversation)
            return result
        if action=='finish':
            result=vetting.finish(self._required(data,'session','Open a design-vetting session first.'))
            self.store.add_message(result['message'],'assistant',conversation)
            return result
        if action=='preview':
            return {'markdown':vetting.preview(self._required(data,'session','Open a design-vetting session first.'))}
        if action=='resurface':
            session=vetting.active(conversation)
            if not session:
                return {'message':''}
            with contextlib.closing(self.store.connect()) as db:
                questions=vetting._questions(db,session['id'])
            return {'message':vetting._format_resurface(questions) if not self._vetting_all_answered(questions) else '',
                    'progress':vetting._progress(questions)}
        if action=='help':
            return vetting.help(self._required(data,'session','Open a design-vetting session first.'),
                                self._required(data,'question','Pick a question first.'),
                                data.get('kind','explain'))
        if action=='conflict':
            return vetting.conflict_action(self._required(data,'session','Open a design-vetting session first.'),
                                           self._required(data,'conflict','Pick a design conflict first.'),
                                           self._required(data,'choice','Choose how to settle that conflict first.'))
        if action=='greybox':
            return vetting.greybox(self._required(data,'session','Open a design-vetting session first.'),
                                   self._required(data,'question','Pick a question first.'),
                                   action=data.get('mode','design'),
                                   feedback_kind=data.get('feedback_kind',''),
                                   greybox_id=data.get('greybox_id',''),note=data.get('note',''))
        if action=='apply_pending':
            return vetting.apply_pending(self._required(data,'session','Open a design-vetting session first.'),
                                         accept=bool(data.get('accept',True)),
                                         correction=data.get('correction',''))
        if action=='transcript_preview':
            return self._plain_errors(lambda: vetting.preview_transcript(
                conversation,data.get('text',''),mode=data.get('mode','answers')))
        if action=='transcript_apply':
            return self._plain_errors(lambda: vetting.apply_transcript(
                conversation,data.get('text',''),mode=data.get('mode','answers'),
                accept_all=bool(data.get('accept_all',False)),
                then_process=bool(data.get('then_process',False))))
        raise PolicyError('Unknown vetting action')

    def _backup_action(self,data):
        # Local backup/restore of the engine data. Credentials never leave the machine and are
        # stripped from the copied database; restore stages files and applies on the next start.
        from .backup import Backup
        action=data.get('action')
        backup=Backup(self.store)
        if action=='create':
            return backup.create(data.get('target'))
        if action=='inspect':
            return backup.inspect(data.get('source'))
        if action=='restore':
            return backup.stage_restore(data.get('source'))
        raise PolicyError('Unknown backup action')

    def _capabilities_action(self,data):
        # Conversation-scoped tool controls. One plain capability name (Web, Files, Terminal,
        # GitHub, Drive, Connected apps) with one state per conversation; the UI control and the
        # natural-language directives both write this same state. Design: docs/session-tools/.
        from .capabilities import (apply_directive, grant_once, reset, set_override,
                                   set_global, snapshot)
        action=data.get('action')
        conversation=data.get('conversation')
        if action in ('get','list'):
            return snapshot(self.store,conversation)
        if action=='set':
            return set_override(self.store,conversation,data.get('capability'),data.get('state'))
        if action=='set_global':
            return set_global(self.store,data.get('capability'),data.get('state'))
        if action=='reset':
            return reset(self.store,conversation)
        if action=='allow_once':
            return grant_once(self.store,conversation,data.get('capability'))
        if action=='directive':
            reply=apply_directive(self.store,conversation,data.get('text') or '')
            return {'applied':bool(reply),'reply':reply}
        raise PolicyError('Unknown capabilities action')

    def _model_action(self,data):
        # Default Kel model + per-conversation override. Plain labels only; routing keeps its
        # fallbacks (the preference is a soft ordering hint, never an exclusion).
        from .providers import DEFINITIONS, Providers
        from .model_prefs import ModelPrefs, provider_label, model_label
        action=data.get('action')
        prefs=ModelPrefs(self.store)
        if action=='why':
            # V2-09 — “Why this model?”: the authoritative explanation is the one the engine stored
            # with the run it actually chose, read back rather than recomputed.
            conversation=str(data.get('conversation') or 'main')
            jobs=[j['id'] for j in self.store.list_jobs() if j.get('conversation')==conversation]
            latest=None
            for event in self.store.events():
                if event.get('type')!='run.claimed' or event.get('aggregate_id') not in jobs:
                    continue
                try:
                    detail=(json.loads(event.get('payload') or '{}') or {}).get('detail') or {}
                except (TypeError, ValueError):
                    continue
                route=detail.get('route')
                if route and (latest is None or (event.get('at') or 0) > latest['at']):
                    latest={'job_id':event['aggregate_id'],'provider':detail.get('provider'),
                            'route':route,'at':event.get('at') or 0}
            if latest is None:
                return {'answer':'No model choice has been made for this conversation yet.'}
            route=latest['route']
            chosen=route.get('selected') or latest.get('provider') or ''
            label=provider_label(chosen) or chosen
            why=str(route.get('why') or '')
            if why in ('your chosen model','your preferred model'):
                answer='Kel is using %s because you chose it.' % label
            elif why=='recent results moved a failing model down':
                answer=('Kel is using %s; recent results moved another model down for now.' % label)
            else:
                answer=('Kel is using %s: the lowest cost among the models that are healthy and '
                        'capable here.' % label)
            return {'job':latest['job_id'],'provider':latest.get('provider'),'selected':chosen,
                    'why':why,'chain':route.get('chain') or ([chosen]+list(route.get('fallbacks') or [])),
                    'demoted':route.get('demoted') or [],'evidence':route.get('evidence') or {},
                    'excluded':route.get('excluded') or {},'answer':answer}
        if action in ('get','list'):
            # Both actions carry the provider listing: the Kel model control reads the choice
            # and the choices from one payload, and a missing list is what made the settings
            # card and the chat pill fail to render.
            snapshot=prefs.snapshot(data.get('conversation'))
            providers=Providers(self.store)
            listing=[]
            for item in DEFINITIONS:
                status=providers.status(item['id'])
                usable=status['status'] in ('healthy','quota','quota_not_reported')
                listing.append({
                    'id':item['id'],
                    'label':provider_label(item['id']),
                    'available':usable,
                    'options':[{'id':model.get('id'),
                                'label':model_label(model.get('id')) or model.get('id'),
                                'available':usable} for model in item.get('models',())],
                })
            snapshot['providers']=listing
            snapshot['auto_label']='Auto'
            return snapshot
        if action in ('set_default','set_conversation','clear_conversation'):
            choice=data.get('choice') or None
            if action=='set_default':
                if choice and choice.get('provider'):
                    prefs.set_default(choice.get('provider'),choice.get('model'))
                else:
                    prefs.clear('default')
            elif action=='set_conversation':
                if choice and choice.get('provider'):
                    prefs.set_conversation(data.get('conversation'),choice.get('provider'),choice.get('model'))
                else:
                    prefs.clear_conversation(data.get('conversation'))
            else:
                prefs.clear_conversation(data.get('conversation'))
            return prefs.snapshot(data.get('conversation'))
        raise PolicyError('Unknown model action')

    def _transcription_action(self,data):
        # Unexpected failures still answer in one plain sentence; PolicyError keeps its own copy.
        try:
            return self._transcription_dispatch(data)
        except PolicyError:
            raise
        except Exception:
            raise PolicyError('Kel could not finish that recording action. Try again.') from None

    def _plain_errors(self,call):
        try:
            return call()
        except PolicyError:
            raise
        except Exception:
            raise PolicyError('Kel could not finish that voice action. Try again.') from None

    def _required(self,data,key,sentence):
        """A required request field, or PolicyError with the sentence a person should read.

        Audit COR-06/ERR-01: dispatch layers used to index payloads directly, so a missing field
        surfaced as the handler's raw `str(exc)` (e.g. "'session'") instead of a plain sentence.
        """
        value=data.get(key)
        if value in (None,''):
            raise PolicyError(sentence)
        return value

    def _transcription_dispatch(self,data):
        # Transcription is an input source: this family stores/inspects audio artifacts and text.
        # Vetting answers derived from transcripts flow through /api/vetting's transcript actions,
        # never through a second parser.
        from .transcription import Transcription
        service=Transcription(self.store)
        action=data.get('action')
        if action=='status':return service.status()
        if action=='library':return service.library()
        if action=='folder_create':return service.folder_create(data.get('name',''))
        if action=='folder_rename':return service.folder_rename(
            self._required(data,'id','Pick a folder first.'),data.get('name',''))
        if action=='folder_delete':return service.folder_delete(
            self._required(data,'id','Pick a folder first.'))
        if action=='rename':return service.transcript_rename(
            self._required(data,'id','Pick a recording first.'),data.get('name',''))
        if action=='delete':return service.transcript_delete(
            self._required(data,'id','Pick a recording first.'))
        if action=='assign':return service.assign(self._required(data,'id','Pick a recording first.'),
                                                  data.get('folder') or None)
        if action=='combine':return service.combine(self._required(data,'id','Pick a recording first.'),
                                                    self._required(data,'source','Pick a recording to add first.'))
        if action=='save_recording':
            return service.save_recording(data.get('text',''),data.get('duration_ms',0),data.get('audio',''),
                                          extension=data.get('extension','wav'),
                                          append_to=data.get('append_to') or None,
                                          name_hint=data.get('name',''))
        if action=='upload':
            return service.transcribe_upload(data.get('filename','audio.wav'),data.get('audio',''),
                                             title_hint=data.get('title',''))
        if action=='quick_transcribe':
            return service.quick_transcribe(data.get('filename','audio.wav'),data.get('audio',''),
                                            data.get('duration_ms'))
        if action=='stream_start':return service.stream_start(data.get('conversation'))
        if action=='stream_chunk':return service.stream_chunk(
            self._required(data,'session','That recording session has ended.'),
            data.get('pcm',''),data.get('conversation'))
        if action=='stream_status':return service.stream_status(
            self._required(data,'session','That recording session has ended.'),data.get('conversation'))
        if action=='stream_finish':return service.stream_finish(
            self._required(data,'session','That recording session has ended.'),data.get('conversation'))
        if action=='export_text':return service.export_text(
            self._required(data,'id','Pick a recording first.'))
        if action=='export_audio':return service.export_audio(
            self._required(data,'id','Pick a recording first.'))
        if action=='set_key':return service.set_key(data.get('key',''))
        if action=='clear_key':return service.clear_key()
        raise PolicyError('Unknown transcription action')

    # -- Fix Capture (V2.0 preflight) --------------------------------------------------------------
    def _dogfood_action(self,data):
        # Same contract as the other families: an unexpected failure answers in one plain sentence,
        # and PolicyError keeps the sentence it was raised with.
        try:
            return self._dogfood_dispatch(data)
        except PolicyError:
            raise
        except Exception:
            raise PolicyError('Kel could not finish that fix action. Try again.') from None

    def _dogfood_list(self,status=None):
        from .dogfood import Dogfood
        return Dogfood(self.store).list(status or None)

    def _dogfood_dispatch(self,data):
        from .dogfood import Dogfood
        service=Dogfood(self.store)
        action=data.get('action')
        if action=='list':return service.list(data.get('status') or None)
        if action=='get':return service.get(self._required(data,'id','Pick a fix first.'))
        if action=='save':
            return service.save(data.get('transcript',''),screenshot=data.get('screenshot'),
                                route=data.get('route'),page_title=data.get('page_title'),
                                element=data.get('element'),window=data.get('window'),
                                diagnostics=data.get('diagnostics'),version=data.get('version'),
                                conversation=data.get('conversation'))
        if action=='set_status':
            return service.set_status(self._required(data,'id','Pick a fix first.'),
                                      self._required(data,'status','Pick a status first.'))
        if action=='prepare_prompt':
            return service.prepare_prompt(data.get('fix_ids') or None)
        if action=='discard':
            return service.discard_tmp(self._required(data,'screenshot','Pick a capture first.'))
        raise PolicyError('Unknown fix action')

    # -- Connections (V2.0) ------------------------------------------------------------------------
    def _oauth_callback(self,query):
        # One place the browser's sign-in answer lands: state-validated, single-use, plain words out.
        from .connection_oauth import complete
        state=(query.get('state') or [''])[0]
        code=(query.get('code') or [''])[0]
        refused=(query.get('error') or [''])[0]
        return complete(self.store,state,code=code or None,refused=refused or None)

    def _connections_action(self,data):
        # Same contract as the other families: one plain sentence for an unexpected failure, and
        # PolicyError keeps the sentence it was raised with.
        try:
            return self._connections_dispatch(data)
        except PolicyError:
            raise
        except Exception:
            raise PolicyError('Kel could not finish that connection action. Try again.') from None

    def _connections_list(self):
        from .connections import Connections
        from .connection_framework import templates
        listing=Connections(self.store).list()
        # V2-04: the three kinds travel with the list, so a surface never has to invent their words.
        listing['templates']=templates()
        return listing

    def _connections_dispatch(self,data):
        from .connections import Connections
        service=Connections(self.store)
        action=data.get('action')
        if action in ('list',None):return self._connections_list()
        if action=='get':return service.get(self._required(data,'id','Pick a connection first.'))
        if action=='save':
            return service.save(data.get('name',''),connection_id=data.get('id'),
                                kind=data.get('kind'),base_url=data.get('base_url'),
                                auth_method=data.get('auth_method'),auth_header=data.get('auth_header'),
                                auth_prefix=data.get('auth_prefix'),
                                docs_url=data.get('docs_url'),test_endpoint=data.get('test_endpoint'),
                                notes=data.get('notes'),oauth_provider=data.get('oauth_provider'))
        if action=='catalogue':
            # V2-03: what Kel already knows about the services Nick uses. Data, not behaviour.
            from .connection_services import catalogue
            return {'services':catalogue()}
        if action=='remove':
            return service.remove(self._required(data,'id','Pick a connection first.'))
        if action=='set_credential':
            return service.set_credential(self._required(data,'id','Pick a connection first.'),
                                          data.get('fields') or [],data.get('credential_ref',''))
        if action=='delete_credential':
            return service.delete_credential(self._required(data,'id','Pick a connection first.'))
        if action=='test':
            # The shell passes the credential for this one request; the engine records only the result.
            target=self._required(data,'id','Pick a connection first.')
            return service.test(target,data.get('credentials') or {},
                                context={'tool':'%s.test'%target})
        if action=='network':
            # V2-14: the network rules themselves — modes, per-scope lists, pending asks, history.
            from . import network_policy
            op=data.get('op') or 'get'
            if op=='get':
                return network_policy.get_policy(self.store)
            if op=='set_mode':
                return network_policy.set_mode(self.store,data.get('mode'),
                                               scope=data.get('scope') or 'default',
                                               domains=data.get('domains'))
            if op=='set_tool':
                return network_policy.set_tool_rule(self.store,data.get('tool'),data.get('mode'),
                                                    domains=data.get('domains'))
            if op=='clear_tool':
                return network_policy.clear_tool_rule(self.store,data.get('tool'))
            if op=='requests':
                return network_policy.requests(self.store,state=data.get('state') or 'pending')
            if op=='resolve':
                return network_policy.resolve_request(
                    self.store,self._required(data,'id','Which request?'),
                    bool(data.get('allow')))
            if op=='history':
                return network_policy.history(self.store,limit=data.get('limit') or 50)
            raise PolicyError('Unknown network action.')
        if action=='actions':
            # V2-04: what Kel can do with this connection, as data.
            from .connection_actions import actions, actions_for
            if data.get('id'):
                item=service.get(self._required(data,'id','Pick a connection first.'))
                return {'connection':item['id'],'actions':actions_for(item['id'])}
            return {'actions':actions()}
        if action=='run':
            # The shell passes the credential for this one request; the answer goes back to the caller
            # and only the fact of the call is written down.
            target=self._required(data,'id','Pick a connection first.')
            action_id=data.get('action_id')
            return service.run(target,action_id,data.get('credentials') or {},
                               data.get('params') or {},bool(data.get('confirmed')),
                               context={'tool':'%s.%s'%(target,action_id),
                                        'project':data.get('project')})
        if action=='supply':
            # V2-04a: the shell hands the engine the values the assistant runtime needs. They stay in
            # this process's memory only (kel.connections custody); the runtime never receives one.
            from .connections import supply_credentials, clear_credentials
            if not data.get('id'):
                raise PolicyError('Pick a connection first.')
            if data.get('clear'):
                clear_credentials(data.get('id'))
                return {'id':str(data.get('id')),'fields':[],'stored':False}
            return {'id':str(data.get('id')),
                    'fields':supply_credentials(data.get('id'),data.get('credentials') or {}),
                    'stored':True}
        if action=='catalog':
            # V2-04a: what the assistant runtime may do right now, resolved through the same
            # capability controls the app shows.
            from .connection_tools import catalog
            return catalog(self.store,job=data.get('job'),conversation=data.get('conversation'))
        if action=='call':
            # V2-04a: one action, through the bridge. No credential is accepted from the caller —
            # the engine uses what the shell pushed, once, in memory.
            from .connection_tools import call
            return call(self.store,data.get('action_id'),data.get('params') or {},
                        connection_id=data.get('id') or data.get('connection'),
                        job=data.get('job'),run=data.get('run'),
                        conversation=data.get('conversation'),confirmation=data.get('confirm'))
        if action=='events':
            return {'events':service.events(data.get('id'),data.get('limit') or 20)}
        if action=='oauth-initiate':
            # V2-04b: build the sign-in URL for one connection; state + PKCE live in the flow table.
            from .connection_oauth import begin
            item=service.get(self._required(data,'id','Pick a connection first.'))
            return begin(self.store,item,str(data.get('_redirect_base') or ''),
                         provider_id=data.get('provider'),scopes=data.get('scopes'))
        if action=='oauth-claim':
            # The shell takes custody of a finished sign-in exactly once (the engine keeps memory).
            from .connection_oauth import claim
            return claim(self.store,self._required(data,'id','Pick a connection first.'))
        if action=='oauth-revoke':
            # Sign out: the provider's revoke endpoint when it has one, then local custody, plainly.
            from .connection_oauth import revoke
            item=service.get(self._required(data,'id','Pick a connection first.'))
            return revoke(self.store,item)
        raise PolicyError('Unknown connection action')

    def _vetting_all_answered(self,questions):
        return all((q.get('answer') or {}).get('status') in ('ANSWERED','PARTIALLY_ANSWERED','SKIPPED','DEFERRED')
                   for q in questions)


def serve(root,port=0):
    service=Service(root);token=secrets.token_urlsafe(32);assets=Path(__file__).parent/'web'
    # V2-04a: everything spawned under this engine (runtimes, helpers) finds the session file here,
    # and `python -m kel...` keeps working in descendant shells (the runtime's kel.conn helper).
    os.environ['KEL_DATA_DIR']=str(root)
    _runtime_dir=str(Path(__file__).resolve().parent.parent)
    if _runtime_dir not in (os.environ.get('PYTHONPATH') or '').split(os.pathsep):
        os.environ['PYTHONPATH']=_runtime_dir+os.pathsep+(os.environ.get('PYTHONPATH') or '')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,value,kind='application/json'):
            raw=encode(value).encode() if kind=='application/json' else value
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(raw)
        def authorized(self):
            host=f'127.0.0.1:{self.server.server_port}'
            origin=self.headers.get('Origin')
            return self.headers.get('Host')==host and (not origin or origin=='http://'+host) and secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path=='/oauth/callback':
                # V2-04b: the browser's sign-in answer comes back here. It carries no bearer — the
                # single-use state is the proof, checked inside complete(); no token ever reaches
                # this page, only a plain sentence about what happened.
                query=parse_qs(parsed.query)
                try:
                    outcome=service._oauth_callback(query)
                except Exception:
                    outcome={'ok':False,'note':'Kel could not finish that sign-in.'}
                escape=lambda text:str(text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                title='Kel — sign-in finished' if outcome.get('ok') else 'Kel — sign-in not finished'
                html=('<!doctype html><html><head><meta charset="utf-8"><title>'+title+'</title>'
                      '</head><body><h1>'+title+'</h1><p>'+escape(outcome.get('note') or '')+'</p>'
                      '<p>You can close this tab and return to Kel.</p></body></html>')
                self.reply(200,html.encode('utf-8'),'text/html; charset=utf-8');return
            if parsed.path.startswith('/api/'):
                if not self.authorized():self.reply(403,{'error':'Local session authorization required'});return
                try:
                    query=parse_qs(parsed.query)
                    if parsed.path=='/api/state':self.reply(200,service.state(query.get('conversation',['main'])[0]));return
                    if parsed.path=='/api/work':self.reply(200,service._work(query.get('conversation',['main'])[0]));return
                    if parsed.path=='/api/dogfood':self.reply(200,service._dogfood_list(query.get('status',[None])[0]));return
                    if parsed.path=='/api/connections':self.reply(200,service._connections_list());return
                    if parsed.path=='/api/artifact':
                        if 'lineage' in query:
                            out=service.store.lineage_artifact(query['lineage'][0])
                            self.reply(200,out['text'].encode(),'text/markdown; charset=utf-8');return
                        job=service.store.get(query['job'][0]);mid=query['milestone'][0];m=job['milestones'][mid]
                        if m['state']!='ACCEPTED':raise PolicyError('Artifact has not passed its checks')
                        self.reply(200,service.store.artifact_text(m['artifact']).encode(),'text/markdown; charset=utf-8');return
                    if parsed.path=='/api/lineage':
                        if 'milestone' in query:
                            rows=service.store.lineage(query['job'][0],query['milestone'][0])
                        else:
                            rows=service.store.lineage(query['job'][0])
                        self.reply(200,{'versions':rows});return
                    if parsed.path=='/api/approvals':
                        self.reply(200,service._approvals_list(query.get('conversation',['main'])[0]));return
                    self.reply(404,{'error':'Not found'})
                except Exception as exc:self.reply(400,{'error':str(exc)})
                return
            mapping={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            name=mapping.get(parsed.path)
            if not name or not (assets/name).is_file():self.reply(404,{'error':'Not found'});return
            kind={'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8'}[name]
            self.reply(200,(assets/name).read_bytes(),kind)
        def do_POST(self):
            if not self.authorized():self.reply(403,{'error':'Local session authorization required'});return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<8_000_000:raise PolicyError('Request body is too large or empty')
                data=json.loads(self.rfile.read(size))
                route=urlparse(self.path).path
                if route=='/api/connections':
                    # The engine's own address, never the caller's: where a sign-in can come back to.
                    data={**data,'_redirect_base':f'http://127.0.0.1:{self.server.server_port}'}
                result=service.action(route,data)
                self.reply(200,result)
                if route=='/api/shutdown-idle':threading.Thread(target=self.server.shutdown,daemon=True).start()
            except Exception as exc:self.reply(400,{'error':str(exc)})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    descriptor={'url':f'http://127.0.0.1:{server.server_port}/','token':token,'pid':os.getpid(),'engine_version':ENGINE_VERSION}
    path=service.store.root/'desktop-session.json';path.write_text(encode(descriptor),encoding='utf-8')
    print(encode({'url':descriptor['url'],'pid':descriptor['pid'],'engine_version':ENGINE_VERSION}),flush=True)
    try:server.serve_forever()
    finally:
        service.stop.set();service.supervisor.join(timeout=2)
        service.requests.shutdown(wait=True)
        service.engine.close();server.server_close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--port',type=int,default=0)
    args=p.parse_args()
    try:serve(args.data,args.port)
    except Conflict as exc:print(str(exc),flush=True);raise SystemExit(2)
