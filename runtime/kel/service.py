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
from .router import coding_intent, needs_work, file_action
from . import handoff
from .turn import decide as decide_turn, amend_ack, guard_ack, guard_reply, template_ack, title_for

# Single source for the engine's identity (audit R8.B): the desktop refuses to reuse a live engine
# whose reported version differs from the app it shipped with, so this literal must match
# `desktop/package.json`'s version (what `app.getVersion()` reports in the packaged app).
from . import __version__ as ENGINE_VERSION

# Verbs that mean "change code in an existing project". These are the only
# requests that need a project root; greenfield ("create an app") is classified
# separately and never prompts.
CODING_VERBS=('fix','build','implement','change','add','remove','update','refactor','test')
# Today's keyword gate (the fallback when no turn model is available, D-53): these openings mean work.
WORK_PREFIXES=('research','search','look up','find current','write','create','draft','summarize','fix','build',
               'implement','change','add','remove','update','make','refactor','test','review','analyze',
               'compare','prepare')
# Explicit research openings are a work floor even when a turn model is available (D-53).
RESEARCH_PREFIXES=('research ','search ','look up','find current')
# The /api/state scope that reads every conversation's work (Work and Activity pages).
ALL_CONVERSATIONS='*'
# Client-declared kinds that are always work (chat kinds and the earlier floors are excluded).
CONVERSATION_KINDS=('chat','conversation')
# CH-10: supervision pace (seconds) while work moves, and while Kel is idle.
BUSY_TICK=.2
IDLE_TICK=2.0
# CH-3: the one plain note the chat gets when the person stops a reply.
STOPPED_NOTE='You stopped this reply.'
# D-54: what a coding request hears when its project cannot be coded in yet.
NO_FOLDER_NOTE=('This looks like a code change, but this project has no folder yet. Open Projects, choose this '
                'project and set its folder and test command — or ask me to create a new project.')
NO_TEST_COMMAND_NOTE='This project needs a test command. Set it in Projects before coding.'


def fallback_line(choice):
    """The one plain line a reply carries when it did not come from the chosen model (CH-2)."""
    used=((choice or {}).get('answered_by') or {}).get('label') or "Kel's default model"
    wanted=((choice or {}).get('fallback_from') or {})
    name=wanted.get('label') or 'your chosen model'
    if wanted.get('note')=='Not supported for chat yet':
        return 'Used '+used+' — '+name+" isn't available for chat yet."
    return 'Used '+used+' — '+name+" isn't available right now."


def _accepts(model,name):
    """Whether a model adapter's execute() takes this keyword."""
    import inspect
    try:
        return name in inspect.signature(model.execute).parameters
    except (TypeError,ValueError):
        return False

def _restore_outcome(root):
    """The last restore attempt recorded beside the data (PER-02), in plain words (FN-02); None if never."""
    from .backup import read_outcome
    return read_outcome(root)


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
        # Routing 2 §5.6: DeepSeek and OpenRouter run when their keys reached the engine's environment
        # (the desktop injects them from its OS-backed custody); without a key they are not offered.
        from .api_models import has_key
        for api in ('deepseek','openrouter'):
            if has_key(api):adapters[api]=DurableAdapter(self.store,api,{'text'})
        self.engine=Engine(self.store,adapters,reviewer=self.commander)
        if self.commander is not None:
            self.commander.staff=self  # D-67: the Verifier runs on its role's model for staffed work
        # Kel V1.4 diagnostics: record the real startup cost of store + adapters + engine so the
        # diagnostics surface can show a measured timeline instead of a claimed one.
        try:
            from .diagnostics import Diagnostics
            Diagnostics(self.store,ENGINE_VERSION).record_startup(
                'engine-start',round((time.time()-started)*1000,2))
        except Exception:
            pass  # a missing span costs one observation, never a boot
        self.requests=ThreadPoolExecutor(max_workers=2,thread_name_prefix='kel-conversation')
        # D-53: starting hand-off work (planning, project creation, job intake) has its own pool so a
        # conversational reply never queues behind a slow planner.
        self.planning=ThreadPoolExecutor(max_workers=2,thread_name_prefix='kel-planning')
        # D-55: creating a hand-off's job and restarting it with a change never interleave, so an
        # amendment can never leave the old job and a new one running side by side.
        self.handoff_lock=threading.RLock()
        # CH-3: the Stop signal for each message still being answered (submission id -> Event).
        self._cancels={};self._cancels_lock=threading.Lock()
        self.drafts={}  # D-75.1: submission id -> the words of a direct reply written so far
        # KEL_TURN_MODEL=none keeps the deterministic keyword gate (tests, headless setups).
        self.turn_mode=(os.environ.get('KEL_TURN_MODEL') or '').strip().lower()
        self._last_follow_up=0.0
        from .apply_changes import recover_prepared
        self.requests.submit(recover_prepared,self.store)
        self.stop=threading.Event();self.error=None
        self.wake=threading.Event()  # CH-10: an engine action wakes idle supervision at once
        with contextlib.closing(self.store.connect()) as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY,conversation_id TEXT,text TEXT,state TEXT,error TEXT,job_id TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS project_tests(project_id TEXT PRIMARY KEY,command TEXT);
            CREATE TABLE IF NOT EXISTS message_files(submission_id TEXT,attachment_id TEXT,PRIMARY KEY(submission_id,attachment_id));''')
            db.execute('CREATE TABLE IF NOT EXISTS submission_packets(id TEXT PRIMARY KEY,packet TEXT,kind TEXT)')
            db.execute("UPDATE submissions SET state='DISPATCHED',job_id=(SELECT job_id FROM job_intakes WHERE job_intakes.id=submissions.id) WHERE id IN (SELECT id FROM job_intakes)")
            handoff.ensure_schema(self.store)
            # D-53: a hand-off whose work never started was already acknowledged in the chat; say
            # once, in that chat, that it did not start and how to start it again.
            with self.store.transaction() as tx:
                for row in tx.execute("SELECT s.id,s.conversation_id,a.title FROM submissions s JOIN submission_acks a "
                                      "ON a.submission_id=s.id WHERE s.state='PLANNING'").fetchall():
                    tx.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                               (row['conversation_id'],'assistant',
                                "Kel closed before it could start '"+str(row['title'] or 'your request')+"'. Use Retry on its card.",
                                time.time()))
                    tx.execute("UPDATE submissions SET state='INTERRUPTED',error='Kel closed before this work started. Retry it from its card.' WHERE id=?",(row['id'],))
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
        from .staff import ensure_schema as ensure_staff_schema
        ensure_staff_schema(self.store)  # D-66/D-67: migration 36
        from .calibration import ensure_schema as ensure_routing_schema
        ensure_routing_schema(self.store)  # Routing 2: migration 37 (calibration runs, raised budgets)
        Connections(self.store)
        # D-54: projects are the one context boundary (migration 32 runs here, once).
        from .projects import Projects
        self.projects=Projects(self.store)
        # D-57: scheduled tasks fire from supervision (migration 33 runs here, once).
        from .schedules import Scheduler
        self.schedules=Scheduler(self)
        # D-64: Full access by default (migration 34 runs here, once).
        from .authority import ensure_schema as ensure_authority_schema
        ensure_authority_schema(self.store)
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
        self.stop.set();self.wake.set()
        if self.supervisor.is_alive():
            self.supervisor.join(timeout=5)
        self.engine.close()
        self.requests.shutdown(wait=True,cancel_futures=True)
        self.planning.shutdown(wait=True,cancel_futures=True)
        # The telemetry thread may be inside a provider call (bounded by that call's own timeout);
        # joining it releases its stderr handle before the caller cleans the data root up.
        if self.telemetry.is_alive():
            self.telemetry.join(timeout=30)

    def _tick(self):
        # CH-10: 5 passes a second while something moves; one every IDLE_TICK seconds when nothing
        # does. Any engine action (a new job, an approval, a control) wakes supervision at once.
        busy=True
        while not self.stop.is_set():
            self.wake.wait(BUSY_TICK if busy else IDLE_TICK)
            self.wake.clear()
            if self.stop.is_set():
                break
            try:busy=self.engine.tick() is not False;self.error=None
            except Exception as exc:self.error=type(exc).__name__+': '+str(exc);busy=True
            try:self.schedules.maybe_tick()  # D-57: at most every 5 s, never while restarting
            except Exception:pass  # a schedule that cannot fire records why; supervision goes on
            if time.time()-self._last_follow_up>=(1 if busy else IDLE_TICK):
                self._last_follow_up=time.time()
                try:handoff.follow_up(self.store)
                except Exception:pass  # a missed notice is retried on the next pass; never stop supervision

    def submit(self,data,origin=None):
        """`origin` (D-57): the schedule that started this run. Python callers only."""
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
        kind_source='client' if kind is not None else 'router'
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
        packet['kind_source']=kind_source
        if origin:packet['schedule']=dict(origin)
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
            # D-53: the person's own message is the one a hand-off job keeps (user before acknowledgement).
            meta=encode({'kind':'scheduled','schedule_id':origin.get('id'),'name':origin.get('name'),
                         'slot':origin.get('slot')}) if origin else None
            packet['intake_seq']=db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',(cid,'user',text,time.time(),meta)).lastrowid
            db.execute('INSERT INTO submission_packets VALUES(?,?,?)',(sid,encode(packet),kind))
            for aid in attachments:db.execute('INSERT INTO message_files VALUES(?,?)',(sid,aid))
            db.execute("UPDATE conversations SET title=? WHERE id=? AND title='New conversation'",(text[:65],cid))
        self.requests.submit(self._plan,sid,cid,text,packet,kind,greenfield_flag)
        return sid

    def staff_adapters(self):
        """The model runtimes Kel can hand a staff role right now (D-67): installed CLIs and, when
        their keys are present, the Anthropic API worker and the DeepSeek / OpenRouter workers."""
        names={name for name in ('codex','claude','deepseek','openrouter') if name in self.engine.adapters}
        if isinstance(self.model,InternalAdapter):
            names.add('internal')
        return names

    def staff_model(self,binding,timeout=100,turn=False):
        """An adapter that runs a resolved role binding with its real flags, or None."""
        name=(binding or {}).get('adapter')
        if name in ('codex','claude') and name in self.engine.adapters:
            from .native import DEFAULT_EFFORT
            adapter=NativeAdapter(name,self.store.root/'workspaces'/name,self.store.root/'logs',timeout=timeout,
                                  model=binding.get('model_arg'),fallback_model=binding.get('fallback_arg'),
                                  effort='low' if turn else binding.get('effort_arg'))
            model_id=binding.get('model')
            if model_id and binding.get('model_arg'):
                # The live check: a refused model is remembered at its first refusal (turn, plan,
                # review), so Kel does not ask for it again and the Settings row says why.
                from .role_models import note_refusal
                adapter.on_refusal=lambda error,version:note_refusal(self.store,model_id,error,version)
            return adapter
        if name=='internal' and isinstance(self.model,InternalAdapter):
            return InternalAdapter(model=binding.get('model_arg') or self.model.model,
                                   timeout=20 if turn else self.model.timeout)
        if name in ('deepseek','openrouter') and name in self.engine.adapters:
            # Routing 2 §5.6: a bounded text worker on its API (the key stays in the environment).
            from .api_models import OpenAICompatAdapter
            from .role_models import note_refusal
            adapter=OpenAICompatAdapter(name,model=binding.get('model_arg'),timeout=20 if turn else min(timeout,180))
            model_id=binding.get('model')
            if model_id:
                adapter.on_refusal=lambda error,version:note_refusal(self.store,model_id,error,version)
            return adapter
        return None

    def _kel_usage(self,kind,sid,cid,model,result,wall,task_class=None):
        """D-72 item 6: one of Kel's own calls (a turn decision, a direct reply or a plan) in the usage
        record, with the conversation and submission it belongs to. Additive; never blocks a reply."""
        try:
            from .usage import record
            binding=getattr(model,'kel_binding',None) or {}
            asked=(binding.get('asked') or {}).get('model')
            record(self.store,'%s:%s:%s'%(kind,sid or '-',secrets.token_hex(6)),kind=kind,
                   adapter=getattr(model,'provider',None),model=getattr(model,'model',None),
                   task_class=task_class or ('planning' if kind=='plan' else 'quick_answer'),
                   result=result if isinstance(result,dict) else {},wall=wall,
                   extra={'conversation_id':cid,'submission_id':sid,'role':'kel','asked_model':asked,
                          'why':binding.get('why')})
        except Exception:
            pass

    def _kel_model(self,turn,images=False):
        """D-67: Kel (the Commander) answers and plans on its role's model when no chat model is
        saved. A message with images keeps the Anthropic API worker, which can read them."""
        from . import staff
        if not staff.enabled() or (images and isinstance(self.model,InternalAdapter)):
            return None
        from .role_models import resolve
        try:
            # Routing 2: quick answers (turns) and plans are Kel's own task classes; the class's
            # ranking is where a refused Kel model falls back to.
            binding=resolve(self.store,'kel',adapters=self.staff_adapters(),purpose='text',
                            task_class='quick_answer' if turn else 'planning')
        except Exception:
            return None
        adapter=self.staff_model(binding,timeout=30 if turn else 100,turn=turn)
        if adapter is not None:
            try:
                adapter.kel_binding=binding  # what Kel's role asked for, for the usage record
            except Exception:
                pass
        return adapter

    def _model_for(self,preference,turn,images=False):
        """An adapter for one saved preference ({provider, model}), or today's fallback when None.

        None when the preferred provider is not available here (the caller then tries the next
        preference). Turn calls run on short timeouts (internal 20 s, native 30 s)."""
        native_timeout=30 if turn else 100
        if not preference:
            kel=self._kel_model(turn,images)
            if kel is not None:
                return kel
        if preference:
            provider=preference.get('provider')
            if provider=='internal':
                if not isinstance(self.model,InternalAdapter):
                    return None
                chosen=preference.get('model') or self.model.model
                if not turn and chosen==self.model.model:
                    return self.model
                return InternalAdapter(model=chosen,timeout=20 if turn else self.model.timeout)
            if provider in ('deepseek','openrouter'):
                if provider not in self.engine.adapters:
                    return None
                from .api_models import OpenAICompatAdapter
                return OpenAICompatAdapter(provider,model=preference.get('model'),timeout=20 if turn else 100)
            cli={'claude-code':'claude','claude':'claude','codex':'codex','codex-code':'codex'}.get(provider)
            if cli and cli in self.engine.adapters:
                return NativeAdapter(cli,self.store.root/'workspaces'/cli,self.store.root/'logs',timeout=native_timeout)
            return None
        if self.model is not None:
            if turn and isinstance(self.model,InternalAdapter):
                return InternalAdapter(model=self.model.model,timeout=20)
            return self.model
        available=next((n for n in ('codex','claude') if n in self.engine.adapters),None)
        if not available:
            return None
        return NativeAdapter(available,self.store.root/'workspaces'/available,self.store.root/'logs',timeout=native_timeout)

    def _chat_choice(self,cid,turn=False,images=False):
        """(model, choice) for a conversational reply: the conversation's saved choice, then the
        default choice (the model pill writes both through /api/model), then Kel's own role model
        (D-67), then Kel's own fallback.

        `choice` records who answers (`answered_by`) and, when the first saved choice could not be
        used, what it fell back from (`fallback_from`, CH-2) — message metadata, shown on demand."""
        from .model_prefs import ModelPrefs
        try:
            snapshot=ModelPrefs(self.store).snapshot(cid)
        except Exception:
            snapshot={}
        chosen=None
        for preference in (snapshot.get('conversation'),snapshot.get('default')):
            if preference and preference.get('provider'):
                chosen=chosen or preference
                model=self._model_for(preference,turn)
                if model is not None:
                    return model,self._choice(model,None if preference is chosen else chosen)
        model=self._model_for(None,turn,images)
        return model,self._choice(model,chosen)

    def _chat_model(self,cid,turn=False,images=False):
        return self._chat_choice(cid,turn,images)[0]

    def _turn_choice(self,cid='main',images=False):
        """The model that decides one conversational turn (D-53) and its choice record; (None, None)
        means the keyword gate decides."""
        if self.turn_mode=='none':
            return None,None
        return self._chat_choice(cid,turn=True,images=images)

    def _turn_model(self,cid='main'):
        return self._turn_choice(cid)[0]

    def _staff_why(self,job_id):
        """"Why this model?" for staffed work (Routing 2 §5.3): the latest step's own record — its
        role, task class and tier, the model that ran (or was asked for) and the recorded reason."""
        from . import staff
        from .role_models import MODE_LABELS,describe_model
        from .staff import ROLE_LABELS
        from .task_routing import TIER_LABELS,label
        calls=[c for c in staff.calls(self.store,job_id) if c['kind']=='work']
        if not calls:
            return None
        call=calls[-1];asked=call.get('asked') or {};ran=call.get('ran') or {}
        confirmed=bool(ran.get('model_confirmed') and ran.get('model'))
        name=(describe_model(raw=ran.get('model'))[0] if confirmed else None) or asked.get('label') or "its runtime's default model"
        role=ROLE_LABELS.get(call['role'],call['role'])
        reason=call.get('why') or ('your %s choice for %s'%(MODE_LABELS.get(asked.get('mode'),'saved').lower(),role))
        where=''
        if asked.get('task_class'):
            where=' (%s, %s tier)'%(label(asked['task_class']).lower(),TIER_LABELS.get(asked.get('dispatch'),'standard').lower())
        answer='Kel used %s as the %s%s: %s.'%(name,role,where,str(reason).rstrip('.'))
        if not confirmed:
            answer+=' The runtime has not confirmed the model yet.'
        return {'job':job_id,'role':call['role'],'task_class':asked.get('task_class'),'tier':asked.get('dispatch'),
                'model':ran.get('model') if confirmed else None,'asked':asked.get('model'),'why':call.get('why'),
                'ranking':asked.get('ranking') or [],'answer':answer}

    def _code_in_project(self,text,packet):
        """The coding floor beyond "starts with a coding verb" (the live check): a code change asked
        for after a lead-in, or naming a code file, inside a project with a folder and a test command."""
        project=(packet or {}).get('project') or {}
        if not project.get('root') or not project.get('id') or not coding_intent(text):
            return False
        with contextlib.closing(self.store.connect()) as db:
            return db.execute('SELECT 1 FROM project_tests WHERE project_id=?',(project['id'],)).fetchone() is not None

    @staticmethod
    def _model_key(model):
        return (type(model).__name__,getattr(model,'provider',None),getattr(model,'model',None))

    def _runnable_provider(self,provider_id):
        """Whether a registered engine adapter can run this catalog provider right now (CH-2)."""
        from .model_prefs import adapter_names
        from .providers import DEFINITIONS
        item=next((entry for entry in DEFINITIONS if entry['id']==provider_id),None)
        names=tuple((item or {}).get('adapters') or ()) or adapter_names(provider_id)
        return bool(item and item.get('adapters')) and any(name in self.engine.adapters for name in names)

    def _choice(self,model,fell_back_from):
        """Who answers (catalog provider, plain label, model) and what the saved choice was if unused."""
        from .model_prefs import provider_label,model_label
        if model is None:
            return None
        if isinstance(model,NativeAdapter):
            provider={'claude':'claude-code','codex':'codex'}.get(model.provider,model.provider)
            answered={'provider':provider,'label':provider_label(provider),'model':None}
            if model.model:
                # D-67: Kel's role model (asked for with the runtime's own -m/--model flag).
                from .role_models import describe_model
                answered.update(model=model.model,label=describe_model(raw=model.model)[0] or answered['label'])
        elif isinstance(model,InternalAdapter):
            answered={'provider':'internal','label':model_label(model.model) or 'Claude','model':model.model}
        else:
            answered={'provider':getattr(model,'provider',None),'label':getattr(model,'label',None),
                      'model':getattr(model,'model',None)}
        choice={'answered_by':answered}
        if fell_back_from:
            wanted=fell_back_from.get('provider')
            note=None
            try:
                from .providers import Providers
                note=Providers(self.store,runnable=self._runnable_provider).status(wanted).get('available_note')
            except Exception:
                note=None
            choice['fallback_from']={'provider':wanted,'model':fell_back_from.get('model'),
                                     'label':provider_label(wanted),'note':note}
        return choice

    def _usage_meta(self,sid,meta):
        """The message's metadata with what Kel's own calls for this message used (tokens, time,
        approximate cost, which model) — shown as the usage chips under the reply."""
        try:
            from .usage import submission_usage
            used=submission_usage(self.store,sid)
        except Exception:
            used=None
        if used and used.get('tokens') is None and used.get('cost') is None and not used.get('model_label'):
            used=None  # nothing was measured (a runtime that reports no usage): no chips, never zeros
        return dict(meta or {},usage=used) if used else meta

    def _with_choice(self,db,cid,text,choice):
        """The message text and its metadata for one answer. The first answer in a conversation that
        fell back from the saved choice says so in one plain line (CH-2); every answer records it."""
        if not choice:
            return text,None
        meta={'answered_by':choice.get('answered_by')}
        fallback=choice.get('fallback_from')
        if fallback:
            meta['fallback_from']=fallback
            marker='%"fallback_noted":'+json.dumps(fallback.get('provider'))+'%'
            if not db.execute('SELECT 1 FROM messages WHERE conversation_id=? AND meta LIKE ? LIMIT 1',
                              (cid,marker)).fetchone():
                meta['fallback_noted']=fallback.get('provider')
                text=str(text).rstrip()+'\n\n'+fallback_line(choice)
        return text,meta

    def _images(self,packet):
        return [{'mime':f['mime'],'data':base64.b64encode((self.store.root/f['image_path']).read_bytes()).decode()}
                for f in packet.get('files') or [] if f.get('image_path')]

    def _still_planning(self,db,sid):
        row=db.execute('SELECT state FROM submissions WHERE id=?',(sid,)).fetchone()
        return row is None or row['state']=='PLANNING'  # an unrecorded message (direct callers) is live

    def _say(self,sid,cid,text,choice=None):
        """One direct answer for this submission, and the submission settles with it.

        Written only while the submission is still being answered: a reply the person stopped
        (CH-3) is dropped here — never posted later, never part of the conversation's history.
        `choice` (from `_chat_choice`) becomes the message's metadata. Returns False when dropped.
        """
        usage_meta=self._usage_meta(sid,None)
        with self.store.transaction() as db:
            if not self._still_planning(db,sid):
                return False
            text,meta=self._with_choice(db,cid,text,choice)
            if usage_meta:
                meta=dict(meta or {},**usage_meta)
            db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                       (cid,'assistant',text,time.time(),encode(meta) if meta else None))
            db.execute("UPDATE submissions SET state='SETTLED',job_id=NULL WHERE id=?",(sid,))
        return True

    def cancel_submission(self,cid,sid):
        """POST /api/cancel (CH-3): the composer's Stop for one message still being answered.

        A reply still being decided or written is stopped: the submission is CANCELLED, any
        in-flight model call is told to stop, whatever it returns later is dropped, and the chat
        gets one plain note. Stop never cancels handed-off work — its card does that (D-53).
        """
        with self.handoff_lock:
            with self.store.transaction() as db:
                row=db.execute('SELECT s.conversation_id,s.state,s.job_id,a.submission_id AS acked FROM submissions s '
                               'LEFT JOIN submission_acks a ON a.submission_id=s.id WHERE s.id=?',(sid,)).fetchone()
                if not row or row['conversation_id']!=cid:
                    raise PolicyError('That message is not part of this conversation')
                if row['acked'] or row['job_id']:
                    return {'cancelled':False,'handed_off':True,'state':row['state']}
                if row['state']!='PLANNING':
                    return {'cancelled':False,'handed_off':False,'state':row['state']}
                db.execute("UPDATE submissions SET state='CANCELLED',error='You stopped this reply.' WHERE id=?",(sid,))
                seq=db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                               (cid,'assistant',STOPPED_NOTE,time.time(),
                                encode({'kind':'stopped','submission':sid}))).lastrowid
        with self._cancels_lock:
            event=self._cancels.get(sid)
        if event is not None:
            event.set()
        return {'cancelled':True,'handed_off':False,'state':'CANCELLED','message_seq':seq}

    def _plan(self,sid,cid,text,packet,kind=None,greenfield_flag=False):
        """Route one message. Returns the hand-off's start future when work was handed off, else None."""
        cancel=threading.Event()
        with self._cancels_lock:
            self._cancels[sid]=cancel
        try:
            with contextlib.closing(self.store.connect()) as db:
                if not self._still_planning(db,sid):
                    return None  # stopped before it was picked up
            lower=text.lower().strip()
            coding_verb=lower.startswith(CODING_VERBS)
            code_floor=coding_verb or self._code_in_project(text,packet)
            explicit_job=(packet.get('continuation') or {}).get('job_id')
            continue_verb=lower.startswith(('continue','resume','pick up','carry on','keep going'))
            jid=None
            if not packet.get('schedule') and not packet.get('recipe_invocation') and not explicit_job \
                    and kind not in ('recipe','continue','status'):
                # D-70 item 4: while a scoping card is open, answers typed here (and "start" / "go")
                # go to that card through the same vetting ingestion; nothing new starts.
                from . import scoping
                try:
                    handled=scoping.typed_answers(self,sid,cid,text)
                except PolicyError:
                    handled=False
                if handled:
                    return None
                # D-75.2 / D-55: the message after an edit of one that started work changes that work.
                from .rewind import take_amendment
                amended=take_amendment(self.store,cid)
                if amended:
                    return self._amend(sid,cid,text,packet,kind,greenfield_flag,
                                       {'action':'amend_background_work','work_id':amended,'amended_request':text,'title':None})
            if packet.get('schedule') and (packet.get('recipe_invocation') or {}).get('recipe_id')!='continue-work':
                # D-57: a scheduled run is work by definition; its acknowledgement is a plain template.
                from .schedules import ACK
                name=packet['schedule'].get('name') or 'your task'
                return self._handoff(sid,cid,text,packet,kind,False,
                                     {'title':name,'acknowledgement':ACK%name,'scheduled':True})
            if kind=='status' or lower in ('status','what are you working on?','what is running?'):
                jobs=[j for j in self.store.list_jobs() if j['conversation']==cid and j['state'] not in ('CLOSED','CANCELLED')]
                answer='No work is running.' if not jobs else '\n'.join(j['contract']['request']+' — '+j['state'].lower().replace('_',' ') for j in jobs)
                self._say(sid,cid,answer)
            elif kind=='recipe' or packet.get('recipe_invocation'):
                jid=self._recipe_run(sid,cid,text,packet)
            elif kind=='continue' or explicit_job or continue_verb:
                jid=self._continuation(cid,text,packet)
            elif coding_verb and not greenfield_flag and not packet['project']['root'] and not file_action(text):
                # Coding intent with no selected project and no explicit
                # greenfield request: ask instead of guessing or silently
                # adopting a temp/donor workspace as the project root.
                self._say(sid,cid,NO_FOLDER_NOTE)
            else:
                # D-53 floors: these messages are work no matter what the turn model says.
                forced=bool(needs_work(text) or file_action(text) or kind in ('research','coding') or lower.startswith(RESEARCH_PREFIXES)
                            or (code_floor and packet['project']['root'])
                            or (packet.get('kind_source')=='client' and kind not in CONVERSATION_KINDS))
                running=handoff.running_work(self.store,cid)
                has_images=any(f.get('image_path') for f in packet.get('files') or [])
                turn_model,choice=self._turn_choice(cid,images=has_images)
                decision=None
                if turn_model is not None:
                    images=self._images(packet) if isinstance(turn_model,InternalAdapter) else None
                    decision=decide_turn(turn_model,packet,text,running,forced=forced,images=images,cancel=cancel,
                                         on_result=lambda result,wall,m=turn_model:self._kel_usage('turn',sid,cid,m,result,wall),
                                         on_text=lambda words:self._draft(sid,words))
                    if decision is None and not cancel.is_set():
                        # The live check: Kel's model was refused and the turn fell to the keyword
                        # gate. The refusal is now remembered, so a second look picks the next model.
                        retry_model,retry_choice=self._turn_choice(cid,images=has_images)
                        if retry_model is not None and self._model_key(retry_model)!=self._model_key(turn_model):
                            turn_model,choice=retry_model,retry_choice
                            images=self._images(packet) if isinstance(turn_model,InternalAdapter) else None
                            self.drafts.pop(sid,None)
                            decision=decide_turn(turn_model,packet,text,running,forced=forced,images=images,cancel=cancel,
                                                 on_result=lambda result,wall,m=turn_model:self._kel_usage('turn',sid,cid,m,result,wall),
                                                 on_text=lambda words:self._draft(sid,words))
                if cancel.is_set():
                    return None  # stopped while deciding: nothing is said and nothing starts
                model_decided=decision is not None
                if decision is None:
                    # Today's keyword gate: no turn model, or it could not be reached.
                    gate_reply=not needs_work(text) and ((kind in CONVERSATION_KINDS and not code_floor) or (kind is None and not needs_research(text) and not lower.startswith(WORK_PREFIXES)))
                    choice=None  # no model spoke: the template or the reply model below does
                    if forced or not gate_reply:
                        decision={'action':'start_background_work','title':title_for(text),
                                  'acknowledgement':template_ack(),'related_topic':None}
                    else:
                        decision={'action':'direct'}
                if decision['action']=='amend_background_work':
                    return self._amend(sid,cid,text,packet,kind,greenfield_flag,decision)
                if decision['action']=='start_background_work':
                    # FN-01 / D-55: a request that asks to touch Kel's own data or app, or a credential
                    # folder, is answered plainly before anything starts — never promised, then failed.
                    from .runtime_guard import request_refusal
                    refusal=request_refusal(text+'\n'+str(decision.get('request') or ''),self.store.root)
                    if refusal:
                        self._say(sid,cid,refusal,choice)
                        return None
                    if decision.get('request') and decision['request']!=text:
                        text=self._rewrite_request(sid,decision['request'])
                    # D-70 item 4: big work (or a plan with open questions) is scoped first; nothing starts.
                    from . import scoping
                    if model_decided and scoping.maybe_ask(self,sid,cid,text,packet,kind,greenfield_flag,decision,choice):
                        return None
                    return self._handoff(sid,cid,text,packet,kind,greenfield_flag,decision,choice)
                if decision['action']=='reply':
                    self._say(sid,cid,decision['text'],choice)
                else:
                    model,choice=self._chat_choice(cid,images=has_images)
                    if model is None:raise PolicyError('Connect a model before sending a message')
                    kwargs={}
                    if any(f.get('image_path') for f in packet['files']):
                        if not (model is self.model or isinstance(model,InternalAdapter)):raise PolicyError('The image worker is not connected')
                        kwargs['images']=self._images(packet)
                    if _accepts(model,'cancel'):
                        kwargs['cancel']=cancel
                    if _accepts(model,'on_text'):
                        from .turn import ReplyStream
                        kwargs['on_text']=ReplyStream(lambda words:self._draft(sid,words),prose=True)
                    answer_packet=dict(packet,running_work=running)
                    started=time.monotonic()
                    result=model.execute('Answer as Kel, one helpful assistant. Keep the reply plain and concise. '
                        'Do not imply you performed external actions. You may answer questions about the saved context. '
                        "running_work is the true state of this conversation's work; never call unfinished or unverified work done.\n"+encode(answer_packet),**kwargs)
                    self._kel_usage('reply',sid,cid,model,result,int((time.monotonic()-started)*1000))
                    if cancel.is_set():
                        return None  # the person stopped this reply; what came back is dropped
                    if result.get('outcome')!='SUCCESS':raise PolicyError(result.get('error','The model did not respond'))
                    self._say(sid,cid,guard_reply(result['text'],running),choice)
            # A direct answer or a refused recipe has no job to dispatch. Mark the request
            # settled so every client can stop waiting without inventing running work.
            with self.store.transaction() as db:db.execute(
                "UPDATE submissions SET state=?,job_id=? WHERE id=? AND state='PLANNING'",
                ('DISPATCHED' if jid else 'SETTLED', jid, sid))
        except Exception as exc:
            with self.store.transaction() as db:db.execute("UPDATE submissions SET state='FAILED',error=? WHERE id=? AND state='PLANNING'",(str(exc),sid))
        finally:
            with self._cancels_lock:
                self._cancels.pop(sid,None)
            self.drafts.pop(sid,None)
            self.wake.set()
        return None

    def _draft(self,sid,words):
        """D-75.1: the words of a direct reply so far, while its submission is still being answered."""
        if sid in self._cancels and not self._cancels[sid].is_set():
            self.drafts[sid]=str(words)

    def draft(self,sid):
        """GET /api/draft: a reply's words so far (empty once it is posted, stopped or handed off)."""
        return {'id':sid,'text':self.drafts.get(sid) or ''}

    def _classify(self,sid,text,packet,kind,greenfield_flag,decision):
        """Routing 2 §5.5: what kind of work this is and how much it deserves. The turn model's reading
        is primary; the deterministic floors are a safety net that may force coding (a code change in a
        project Kel can test, an explicit coding request, a new app) or research (an explicit research
        request) but never turn the model's coding or research into writing. Without a model reading the
        floors classify on their own. Recorded in the hand-off packet (and its saved copy)."""
        from .staff import MECHANICAL,USER_FACING
        lower=str(text or '').lower().strip()
        root=(packet.get('project') or {}).get('root')
        code_floor=kind=='coding' or bool(greenfield_flag) or (root and (lower.startswith(CODING_VERBS) or self._code_in_project(text,packet)))
        research_floor=kind=='research' or lower.startswith(RESEARCH_PREFIXES)
        model_class=(decision or {}).get('task_class')
        out={'task_class':model_class,'tier':(decision or {}).get('tier'),'source':'model' if model_class else 'floors'}
        forced=('coding' if code_floor else 'research' if research_floor else None)
        if forced and model_class not in ('coding','research') and model_class!=forced:
            out.update(task_class=forced,forced_by='floor')
        if not out['task_class']:
            if needs_research(text):out['task_class']='research'
            elif MECHANICAL.search(lower) and len(lower.split())<=40:out['task_class']='utility'
            elif USER_FACING.search(lower):out['task_class']='design'
            else:out['task_class']='writing'
        packet['classification']={k:v for k,v in out.items() if v}
        try:
            with self.store.transaction() as db:
                db.execute('UPDATE submission_packets SET packet=? WHERE id=?',(encode(packet),sid))
        except Exception:
            pass  # the in-memory packet carries it into this start; the saved copy is additive
        return packet['classification']

    def _handoff(self,sid,cid,text,packet,kind,greenfield_flag,decision,choice=None):
        """D-53: acknowledge now (one transaction), start the work on the planning pool, return."""
        if not decision.get('scheduled'):
            self._classify(sid,text,packet,kind,greenfield_flag,decision)
        title=title_for(text,decision.get('title'))
        ack=decision['acknowledgement'] if decision.get('scheduled') else \
            guard_ack(decision.get('acknowledgement'),decision.get('related_topic'))
        usage_meta=self._usage_meta(sid,None)
        with self.handoff_lock:
            with self.store.transaction() as db:
                if not self._still_planning(db,sid):
                    return None  # stopped before the hand-off was said: nothing starts
                row=db.execute('SELECT title FROM submission_acks WHERE submission_id=?',(sid,)).fetchone()
                if not row:
                    ack,meta=self._with_choice(db,cid,ack,choice)
                    if usage_meta:
                        meta=dict(meta or {},**usage_meta)
                    seq=db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                                   (cid,'assistant',ack,time.time(),encode(meta) if meta else None)).lastrowid
                    db.execute('INSERT INTO submission_acks VALUES(?,?,?,?)',(sid,seq,title,time.time()))
        return self.planning.submit(self._start_work,sid,cid,text,packet,kind,greenfield_flag)

    def _rewrite_request(self,sid,request):
        """The submission records the whole request its work runs (the person's message is kept as
        they wrote it); returns that request."""
        with self.store.transaction() as db:
            db.execute("UPDATE submissions SET text=? WHERE id=? AND state='PLANNING'",(request,sid))
        return request

    def _amend(self,sid,cid,text,packet,kind,greenfield_flag,decision):
        """D-55: restart this conversation's still-changeable hand-off with the person's change.

        One transaction stops the old job (if it exists), points the original hand-off (and its
        card) at the amended request, and says so plainly; the amending message itself becomes no
        work of its own. Work that can no longer be changed is not amended: the amended request is
        then new work. Never two live jobs for one hand-off.
        """
        target=decision['work_id'];amended=decision['amended_request']
        stopped=[];restart=None
        with self.handoff_lock:
            with self.engine.lock:
                with self.store.transaction() as db:
                    row=db.execute('SELECT s.*,p.packet,p.kind AS packet_kind,a.title AS ack_title FROM submissions s '
                                   'JOIN submission_packets p ON p.id=s.id JOIN submission_acks a ON a.submission_id=s.id '
                                   'WHERE s.id=? AND s.conversation_id=?',(target,cid)).fetchone()
                    mine=db.execute('SELECT state FROM submissions WHERE id=?',(sid,)).fetchone()
                    if not mine or mine['state']!='PLANNING':
                        return None  # this message was stopped before its turn finished
                    old_job=row['job_id'] if row else None
                    changeable=bool(row) and row['id']!=sid and (
                        (row['state']=='PLANNING' and not old_job) or
                        (row['state']=='DISPATCHED' and old_job and
                         self.store._get(db,old_job)['state'] not in handoff.AMENDABLE_JOB_STATES_EXCLUDED))
                    if changeable:
                        title=title_for(amended,decision.get('title') or row['ack_title'])
                        if old_job:
                            stopped=self.store._control(db,old_job,'cancel')
                            db.execute('INSERT OR IGNORE INTO handoff_restarts VALUES(?,?,?,?)',(target,old_job,sid,time.time()))
                            db.execute('DELETE FROM job_intakes WHERE id=?',(target,))
                            restart=(json.loads(row['packet']),row['packet_kind'])
                        # A hand-off still planning picks the new request up before it creates its job.
                        db.execute("UPDATE submissions SET text=?,state='PLANNING',job_id=NULL,error=NULL WHERE id=?",(amended,target))
                        db.execute('UPDATE submission_acks SET title=? WHERE submission_id=?',(title,target))
                        db.execute('INSERT INTO messages(conversation_id,role,text,at,meta) VALUES(?,?,?,?,?)',
                                   (cid,'assistant',amend_ack(title,stopped_a_run=bool(old_job)),time.time(),
                                    encode({'kind':'amendment','submission':target,'replaced_job':old_job})))
                        db.execute("UPDATE submissions SET state='SETTLED' WHERE id=?",(sid,))
                if changeable:
                    for run_id in stopped:
                        if run_id in self.engine.active:
                            self.engine.active[run_id][1].set()
        if not changeable:
            # Nothing it could change is still running: the whole amended request is new work.
            return self._handoff(sid,cid,self._rewrite_request(sid,amended),packet,kind,greenfield_flag,
                                 {'title':decision.get('title'),'acknowledgement':None,'related_topic':None})
        if restart:
            old_packet,old_kind=restart
            from .router import classify
            greenfield=bool(classify(amended).get('greenfield')) if old_packet.get('kind_source')!='client' else False
            return self.planning.submit(self._start_work,target,cid,amended,old_packet,old_kind,greenfield)
        return None

    def _project_for_folder(self,folder):
        """(root, project_id, tests) for the saved project whose root holds `folder`, else None."""
        try:
            target=Path(os.path.expandvars(os.path.expanduser(folder))).resolve()
        except (OSError,RuntimeError,ValueError):
            return None
        with contextlib.closing(self.store.connect()) as db:
            rows=[dict(r) for r in db.execute('SELECT p.id,p.root,t.command FROM projects p JOIN project_tests t '
                                              'ON t.project_id=p.id WHERE p.root IS NOT NULL AND p.root<>\'\'')]
        best=None
        for row in rows:
            try:
                root=Path(row['root']).resolve()
            except (OSError,RuntimeError,ValueError):
                continue
            if (target==root or root in target.parents) and (best is None or len(str(root))>len(str(best[0]))):
                best=(str(root),row['id'],json.loads(row['command']))
        return best

    def _document_contract(self,text,packet,sid=None,cid=None):
        if self.commander:
            # D-67: Kel plans on its own role model when one is set up here (else the planner it had).
            kel=self._kel_model(False,bool(any(f.get('image_path') for f in packet.get('files') or [])))
            contract, meta = self.commander.plan(
                text, context=packet, model=kel,
                on_result=lambda model,result,wall:self._kel_usage('plan',sid,cid,model,result,wall,'planning'))
            planner = {'provider': meta.get('provider'), 'model': meta.get('model')} \
                if kel is not None else self.commander.descriptor()
            contract['planner'] = {**planner, 'compiler': contract.get('compiler')} if meta.get('mode')=='model_proposal' else {'provider': None, 'model': None, 'compiler': contract.get('compiler')}
        else:
            contract = compile_document(text)
            contract['planner'] = {'provider': None, 'model': None, 'compiler': contract.get('compiler')}
        return contract

    def _compile_work(self,sid,cid,text,packet,kind,greenfield_flag):
        """The work contract for one request (a file action, coding, research, or a planned document)."""
        lower=text.lower().strip()
        coding_verb=lower.startswith(CODING_VERBS) or self._code_in_project(text,packet)
        classified=(packet.get('classification') or {}).get('task_class')
        # Routing 2 §5.5: the classification (the turn model's, floors as the safety net) is primary.
        coding=kind=='coding' or (packet['project']['root'] and coding_verb) or classified=='coding'
        target=file_action(text)
        if target and kind=='coding' and packet.get('kind_source')=='client':
            target=None  # an explicit coding request keeps its own project routing
        if target:
            # A named file in a named folder: only the coding path can write into a saved project.
            # Anywhere else the result is text, and publication says plainly that no file was made.
            found=self._project_for_folder(target['folder'])
            if found:
                root,project_id,tests=found
                contract=compile_coding(text,root,tests,project_id,greenfield=False)
                contract['planner']={'provider':None,'model':None,'compiler':contract.get('compiler')}
            else:
                contract=self._document_contract(text,packet,sid,cid)
                contract['file_request']=target
        elif coding:
            root=packet['project']['root']
            # Greenfield intent ("create me an app") always wins, even when the
            # active project already has a root such as a desktop temp workspace.
            greenfield=bool(greenfield_flag) or not bool(root)
            if not greenfield:
                from .projects import ensure_folder
                ensure_folder(self.store,root)  # D-62: General's default folder is made when work needs it
            if greenfield:
                # Greenfield build: the user asked Kel to CREATE an app. Kel owns the
                # workspace: a fresh git repo under Documents/Kel Projects with a
                # deterministic smoke-test command the worker must make pass.
                # VIS-16: a short human name (the work's own title when it has one) and a tidy folder.
                from .projects import new_project_folder,readable_project_name
                with contextlib.closing(self.store.connect()) as db:
                    ack=db.execute('SELECT title FROM submission_acks WHERE submission_id=?',(sid,)).fetchone()
                    taken=[row['name'] for row in db.execute('SELECT name FROM projects')]
                name=readable_project_name(text,ack['title'] if ack else None,taken)
                root=new_project_folder(name)
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
                # D-54: a project Kel makes for the person is theirs (a user project), folder and test set.
                project_id=self.projects.create(name,root=str(root),test_command=tests,
                                                context='Created by Kel for: '+text[:120])['id']
            else:
                with contextlib.closing(self.store.connect()) as db:
                    row=db.execute('SELECT command FROM project_tests WHERE project_id=?',(packet['project']['id'],)).fetchone()
                if not row:raise PolicyError(NO_TEST_COMMAND_NOTE)
                project_id=packet['project']['id'];tests=json.loads(row['command'])
            contract=compile_coding(text,root,tests,project_id,greenfield=greenfield)
            contract['planner']={'provider':None,'model':None,'compiler':contract.get('compiler')}
        elif kind=='research' or classified=='research' or (not classified and needs_research(text)):
            from .research import compile_research
            contract=compile_research(text,self.commander,packet)
            contract['planner']={'provider':None,'model':None,'compiler':contract.get('compiler')}
        else:
            contract=self._document_contract(text,packet,sid,cid)
        contract['context']=packet
        if packet.get('classification'):
            contract['classification']=dict(packet['classification'])  # staffing reads the class and tier
        if any(f.get('image_path') for f in packet['files']):contract['required_capabilities']=['image','text']
        contract['submission_id']=sid
        return contract

    def _start_work(self,sid,cid,text,packet,kind=None,greenfield_flag=False):
        """Planning-pool half of a hand-off: compile, create the job, link it; or say it failed.

        D-55: a change that arrives while this is still planning rewrites the submission's request;
        the job is only created (under `handoff_lock`) from the request as it stands, so the change
        is planned in before anything runs and exactly one job ever exists for the hand-off.
        """
        try:
            while True:
                contract=self._scheduled_contract(sid,cid,text,packet,kind) if packet.get('schedule') else \
                    self._compile_work(sid,cid,text,packet,kind,greenfield_flag)
                with self.handoff_lock:
                    with contextlib.closing(self.store.connect()) as db:
                        current=db.execute('SELECT text,state FROM submissions WHERE id=?',(sid,)).fetchone()
                        ack=db.execute('SELECT message_seq,title FROM submission_acks WHERE submission_id=?',(sid,)).fetchone()
                    if current and current['state']!='PLANNING':
                        return None  # stopped or restarted elsewhere; nothing to create
                    if current and current['text']!=text:
                        text=current['text'];continue  # changed while planning: plan the change in
                    contract['handoff']={'submission_id':sid,'ack_seq':ack['message_seq'] if ack else None,
                                         'title':ack['title'] if ack else title_for(text)}
                    self._staff_contract(contract,text)
                    # Create and link the job atomically with intake to prevent duplicate effects on restart.
                    jid=self.engine.submit(contract,budget=max(12,len(contract['milestones'])*4),conversation=cid)
                    self._record_staffing(jid,contract)
                    self._link_origin(jid,cid,sid)
                    intake=packet.get('intake_seq')
                    with self.store.transaction() as db:
                        if intake and db.execute('SELECT 1 FROM messages WHERE seq=? AND conversation_id=?',(intake,cid)).fetchone():
                            # The person's own message stays where it was (before the acknowledgement)
                            # and becomes the job's source message; the copy create() recorded goes.
                            db.execute("DELETE FROM messages WHERE conversation_id=? AND role='user' AND job_id=? AND seq<>?",(cid,jid,intake))
                            db.execute('UPDATE messages SET job_id=? WHERE seq=?',(jid,intake))
                        else:
                            dup=db.execute('SELECT seq FROM messages WHERE conversation_id=? AND role=? AND text=? AND job_id IS NULL ORDER BY seq DESC LIMIT 1',(cid,'user',text)).fetchone()
                            if dup:db.execute('DELETE FROM messages WHERE seq=?',(dup['seq'],))
                        db.execute("UPDATE submissions SET state='DISPATCHED',job_id=?,error=NULL WHERE id=?",(jid,sid))
                    self.wake.set()
                    return jid
        except Exception as exc:
            reason=str(exc).strip().rstrip('.') or type(exc).__name__
            with self.store.transaction() as db:
                db.execute("UPDATE submissions SET state='FAILED',error=? WHERE id=?",(str(exc),sid))
                db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                           (cid,'assistant',"I wasn't able to get that started — "+reason+'. You can retry it from the card above.',time.time()))
            return None

    def _recipe_contract(self,sid,packet,info=None):
        """The job contract for a recipe invocation; PolicyError in plain words when it cannot compile."""
        from .recipes import RecipeLibrary, compile_recipe
        invocation=packet.get('recipe_invocation') or {}
        project_id=(packet.get('project') or {}).get('id') or 'default'
        if info is None:
            info=RecipeLibrary(self.store).get(invocation.get('recipe_id',''),project_id=project_id)
        recipe=info['recipe']
        root=tests=None
        needs_code=recipe['kind']=='coding' or any(
            step.get('kind_override')=='coding' for step in recipe['steps'])
        if needs_code:
            root=(packet.get('project') or {}).get('root')
            with contextlib.closing(self.store.connect()) as db:
                row=db.execute('SELECT command FROM project_tests WHERE project_id=?',(project_id,)).fetchone()
            tests=json.loads(row['command']) if row else None
        contract=compile_recipe(recipe,invocation.get('inputs') or {},project_id,root=root,tests=tests)
        contract['planner']={'provider':None,'model':None,'compiler':contract.get('compiler')}
        contract['submission_id']=sid
        return contract

    def _scheduled_contract(self,sid,cid,text,packet,kind):
        """D-57: a scheduled run's contract — its recipe, or its instruction (never a new project, never
        code without the project's folder) — carrying the schedule, whose model choice it prefers."""
        if packet.get('recipe_invocation'):
            contract=self._recipe_contract(sid,packet)
        else:
            from .schedules import instruction_refusal
            refusal=instruction_refusal(text,(packet.get('project') or {}).get('root'))
            if refusal:raise PolicyError(refusal)
            contract=self._compile_work(sid,cid,text,packet,kind,False)
        origin=packet['schedule']
        contract['schedule']={'id':origin.get('id'),'name':origin.get('name'),'slot':origin.get('slot'),
                              'model':origin.get('model')}
        return contract

    def _recipe_run(self,sid,cid,text,packet):
        """Run a validated recipe through the existing engine (no second runtime)."""
        from .recipes import RecipeLibrary
        invocation=packet.get('recipe_invocation') or {}
        project_id=(packet.get('project') or {}).get('id') or 'default'
        try:
            info=RecipeLibrary(self.store).get(invocation.get('recipe_id',''),project_id=project_id)
        except PolicyError as exc:
            self.store.add_message('I could not find that recipe. '+str(exc),'assistant',cid)
            return None
        if info['recipe']['recipe_id']=='continue-work':
            return self._continuation(cid,text,packet)
        try:
            contract=self._recipe_contract(sid,packet,info)
        except PolicyError as exc:
            self.store.add_message(str(exc),'assistant',cid)
            return None
        self._staff_contract(contract,text)
        jid=self.engine.submit(contract,budget=max(12,len(contract['milestones'])*4),conversation=cid)
        self._record_staffing(jid,contract)
        self._link_origin(jid,cid,sid)
        with self.store.transaction() as db:
            dup=db.execute('SELECT seq FROM messages WHERE conversation_id=? AND role=? AND text=? AND job_id IS NULL ORDER BY seq DESC LIMIT 1',(cid,'user',text)).fetchone()
            if dup:db.execute('DELETE FROM messages WHERE seq=?',(dup['seq'],))
        return jid

    def _staff_contract(self,contract,text):
        """D-66: every real-work job carries its recorded staffing decision, frozen in its contract.

        With the workforce off (KEL_WORKFORCE=0) nothing is added and the job runs as before. A
        decision that cannot be made never blocks the work: the job runs unstaffed and says why."""
        from . import staff
        if not staff.enabled():
            return None
        try:
            contract['staffing']=staff.plan_job(self.store,contract,text)
        except Exception as exc:
            contract.pop('staffing',None)
            contract['staffing_error']=type(exc).__name__
        return contract.get('staffing')

    def _record_staffing(self,job_id,contract):
        if not contract.get('staffing'):
            return
        from . import staff
        try:
            staff.record_decision(self.store,job_id,contract['staffing'])
        except Exception:
            pass  # the decision is frozen in the contract; the history event is additive

    def _project_of(self,cid):
        with contextlib.closing(self.store.connect()) as db:
            row=db.execute('SELECT project_id FROM conversations WHERE id=?',(cid,)).fetchone()
        if not row:
            # ST-04: a chat opened in the app has a reserved id and no row until its first message;
            # until then it belongs where it will be created (D-54: its binding, else the active project).
            import uuid
            try:
                uuid.UUID(str(cid))
            except ValueError:
                raise PolicyError('Conversation missing') from None
            return self.projects.pending_project(str(cid))
        return row['project_id']

    def _scope(self,data,write=False):
        """D-54: the project a Knowledge/Map/Recipes/brief/Activity call acts in ('*' = every project,
        reads only)."""
        return self.projects.scope(data,write,self._project_of)

    def _work(self,cid,project=None):
        """Compact project work context for the shell's Work panel.

        D-54: with `project` (an id or '*') the jobs are every job in that scope, not one chat's;
        for '*' the memory and map blocks are None (they belong to one project)."""
        from .memory import Memory
        from .projectmap import ProjectMap
        from .recipes import RecipeLibrary
        from .projects import ALL,job_projects,primary_project,recipes_everywhere
        if project not in (None,''):
            project_id=self._scope({'project':project})
        else:
            project=None
            project_id=self._project_of(cid)
        memory=Memory(self.store)
        everywhere=project_id==ALL
        data={'schema':1,'project_id':project_id,
              'memory':None if everywhere else
                       {'records':[{'id':r['id'],'type':r['type'],'topic':r['topic'],
                                    'summary':r['summary'],'value':r['value'],'trust':r['trust'],
                                    'status':r['status'],'user_confirmed':r['user_confirmed'],
                                    'source_type':r['source_type'],'source_ref':r['source_ref'],
                                    'confidence':r['confidence'],'updated':r['updated']}
                                   for r in memory.records(project_id,limit=100)],
                        'proposals':memory.proposals(project_id,state='open'),
                        'conflicts':memory.conflicts(project_id)},
              'map':None,
              'recipes':{'entries':recipes_everywhere(self.projects) if everywhere else
                         RecipeLibrary(self.store).entries(project_id=project_id)}}
        latest=None if everywhere else ProjectMap(self.store).get(project_id)
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
            # V2-06 follow-through: a row's one action has to be dispatchable, so the row carries the id
            # the route needs — the pending approval to answer, or the saved request a retry would
            # resubmit. Nothing else in the row has to guess it.
            pending_ids={row['job_id']:row['id'] for row in db.execute(
                "SELECT job_id,id FROM approvals WHERE status='PENDING'")}
            submission_of={row['job_id']:row['id'] for row in db.execute(
                "SELECT job_id,id FROM submissions WHERE job_id IS NOT NULL")}
            # CP-2: the last activity of this scope's jobs only, not of the whole event log.
            conv_map={r['id']:r['project_id'] for r in db.execute('SELECT id,project_id FROM conversations')}
            if project is None:
                mine=[job for job in self.store.list_jobs() if job['conversation']==cid]
            else:
                mine=[job for job in self.store.list_jobs()
                      if everywhere or project_id in job_projects(job,conv_map)]
            last={}
            ids=[job['id'] for job in mine]
            for start in range(0,len(ids),400):
                part=ids[start:start+400]
                last.update({row['aggregate_id']:row['at'] for row in db.execute(
                    'SELECT aggregate_id,MAX(at) AS at FROM events WHERE aggregate_id IN (%s) GROUP BY aggregate_id'
                    %','.join('?'*len(part)),part)})
            # D-55: a job stopped because its hand-off restarted with a change is not separate work.
            replaced=handoff.replaced_jobs(db)
        jobs=[]
        needs=0
        closed_shown={}
        for job in mine:
            if (project is None and job['conversation']!=cid) or job['id'] in replaced:
                continue
            active=job['state'] not in ('CLOSED','CANCELLED')
            if not active:
                # At most three recently settled jobs per chat (a project scope spans many chats).
                shown=closed_shown.get(job['conversation'],0)
                if shown>=3 or (last.get(job['id']) or 0)<now-86400:
                    continue
                closed_shown[job['conversation']]=shown+1
            milestones=job.get('milestones') or {}
            brief=cont.resume_brief(job['id'])
            created=job.get('created') or now
            entry={'job_id':job['id'],'title':brief['title'],'state':job['state'],
                   'verdict':job.get('verdict'),
                   'accepted':len(brief['shipped']),'total':len(milestones),
                   'open':len(brief['open']),'fenced':brief['fenced'],
                   'needs_you':brief['needs_you'],'why':brief['why'],'next':brief['next'],
                   'last_at':last.get(job['id'])}
            if pending.get(job['id']):
                entry.update(needs_you=True,why='Waiting for your decision on a gated step.',
                             next='Decide on the request card in the conversation — or on its work card at the top of the chat.')
            if not active:
                stopped=job['state'] in ('CANCELLED','CANCELLING')
                entry.update(needs_you=False,
                             why=('You stopped this work.' if stopped else
                                  ('Done and verified.' if job.get('verdict')=='VERIFIED'
                                   else "It finished, but it didn't pass its checks." if job.get('verdict')=='FAILED'
                                   else "It finished, but Kel couldn't fully verify the result.")),
                             next=('This work was stopped. Its saved request is kept in this '
                                   'conversation.' if stopped else
                                   'Nothing needed — ask for a new change for more work.'))
                if job['contract'].get('staffing'):
                    # D-66: the independent second opinion found a blocker (or could not run), so
                    # Kel did not act on it by itself — that is Nick's decision now.
                    from .oracle import attention
                    needed=attention(self.store,job)
                    if needed:
                        entry.update(needs_you=True,why=needed['why'],next=needed['next'])
            # V2-06: a row says what it is, why it is here, how old it is, how urgent it is, what
            # belongs with it, and the one action the person can take right now. All of it is
            # derived from authoritative state — nothing here resolves, snoozes or re-runs anything.
            if entry['needs_you']:
                priority='now'
            elif job['state'] in ('BLOCKED','CANCELLING','PAUSING'):
                priority='soon'
            elif active:
                priority='running'
            elif job.get('verdict') not in ('VERIFIED',None):
                priority='soon'
            else:
                priority='later'
            approval_count=pending.get(job['id']) or 0
            if approval_count:
                direct={'action':'answer','route':'/api/approval','id':pending_ids.get(job['id']),
                        'hint':'Answer the request in this conversation.'}
            elif entry['fenced']:
                # A fenced run resumes as a conversation continuation, not as a job control call.
                direct={'action':'resume','route':'/api/send',
                        'hint':'Say "continue" in this conversation.'}
            elif job['state'] in ('PAUSED','BLOCKED'):
                direct={'action':'resume','route':'/api/control',
                        'hint':'Resume when you are ready.'}
            elif active:
                direct={'action':'stop','route':'/api/control','hint':'Stop this work.'}
            elif job['state']=='CLOSED' and job.get('verdict') not in ('VERIFIED',None):
                # Only a settled failure can be retried: /api/retry accepts a submission whose own
                # state is FAILED/INTERRUPTED. Measured before this fix: a cancelled row offered
                # retry and the endpoint refused it in plain words — a row must not promise an
                # action the product cannot honour.
                direct={'action':'retry','route':'/api/retry','id':submission_of.get(job['id']),
                        'hint':'Try this work again from its saved request.'}
            else:
                direct=None
            entry.update(priority=priority,age_seconds=int(max(0,now-created)),
                         reason=entry['why'],
                         related={'project_id':primary_project(job,conv_map) if everywhere else project_id,
                                  'conversation':job['conversation'],
                                  'approvals':approval_count,'milestones':len(milestones)},
                         direct=direct)
            if entry['needs_you']:
                needs+=1
            jobs.append(entry)
        order={'now':0,'soon':1,'running':2,'later':3}
        jobs.sort(key=lambda item:(order.get(item['priority'],9),-(item['last_at'] or 0)))
        groups={}
        for entry in jobs:
            groups.setdefault(entry['related']['project_id'],[]).append(entry['job_id'])
        data['work']={'generated':now,'needs_you':needs,'jobs':jobs,
                      'grouping':'project',
                      'groups':[{'project_id':key,'job_ids':groups[key]} for key in groups],
                      'filters':{'needs_you':sum(1 for item in jobs if item['needs_you']),
                                 'running':sum(1 for item in jobs if item['priority']=='running'),
                                 'failed':sum(1 for item in jobs
                                              if item.get('verdict') not in ('VERIFIED',None)),
                                 'settled':sum(1 for item in jobs
                                               if item['state'] in ('CLOSED','CANCELLED'))},
                      'sorting':['priority','age']}
        return data

    def _owned_memory(self,project_id,memory_id):
        with contextlib.closing(self.store.connect()) as db:
            row=db.execute('SELECT project_id FROM memories WHERE id=?',(memory_id,)).fetchone()
        if not row or row['project_id']!=project_id:
            raise PolicyError('Memory belongs to another project')

    def _memory_action(self,data):
        from .memory import Memory
        from .projects import ALL,MEMORY_READS,memory_everywhere
        action=data.get('action')
        project_id=self._scope(data,write=action not in MEMORY_READS)
        if project_id==ALL:
            return memory_everywhere(self.projects,action,data)
        memory=Memory(self.store)
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
        action=data.get('action')
        project_id=self._scope(data,write=action=='refresh')
        if project_id=='*':
            raise PolicyError('Choose a project to see its map.')
        maps=ProjectMap(self.store)
        if action=='refresh':
            latest=maps.refresh(project_id,force=bool(data.get('force')),reason='work-context')
            return {'version':latest['version'],'fingerprint':latest['fingerprint'],
                    'note':latest['note']}
        if action=='stale':
            return {'sections':maps.stale_sections(project_id,data.get('changed') or [])}
        raise PolicyError('Unknown map action')

    def _recipes_action(self,data):
        from .recipes import RecipeLibrary, compile_recipe
        from .projects import ALL,recipe_writes,recipes_everywhere
        action=data.get('action')
        project_id=self._scope(data,write=recipe_writes(data))
        everywhere=project_id==ALL
        if everywhere and action in ('list','search'):
            return {'entries':recipes_everywhere(self.projects,query=data.get('query') if action=='search' else None)}
        if everywhere:
            project_id=''  # the built-in library: '*' reads never name a project that is not there
        library=RecipeLibrary(self.store)
        if action=='list':
            return {'entries':library.entries(project_id=project_id)}
        if action=='get':
            info=library.get(data.get('recipe_id',''),project_id=project_id)
            if not everywhere:
                library.mark(project_id,info['recipe']['recipe_id'],opened=True)
            return {'recipe':info['recipe'],'scope':info['scope'],'version':info['version'],
                    'digest':info['digest']}
        # V2-07: the library's own surfaces — search, favourites, recent, categories, duplicate,
        # run history and the last result. All read what the engine already keeps.
        if action=='search':
            return {'entries':library.search(project_id,data.get('query'))}
        if action=='categories':
            return {'categories':library.categories(project_id)}
        if action=='favourites':
            if data.get('recipe_id'):
                return library.mark(project_id,str(data['recipe_id']),
                                     favourite=bool(data.get('favourite')))
            return {'favourites':library.favourites(project_id)}
        if action=='recent':
            return {'recent':library.recent(project_id,limit=data.get('limit'))}
        if action=='duplicate':
            return library.duplicate(data.get('recipe_id',''),project_id)
        if action=='history':
            return {'history':library.history(project_id,data.get('recipe_id',''),
                                              limit=data.get('limit'))}
        if action=='last_result':
            return library.last_result(project_id,data.get('recipe_id',''))
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
                from .projects import ensure_folder
                ensure_folder(self.store,root)  # D-62
                tests=json.loads(row['command']) if row else None
            try:
                contract=compile_recipe(recipe,data.get('inputs') or {},project_id,root=root,tests=tests)
            except PolicyError as exc:
                # D-54: say which project and what it lacks, so the page can offer "Set project folder".
                missing=([] if root else ['folder'])+([] if tests else ['test_command'])
                return {'needs_project':True,'message':str(exc),'project_id':project_id or None,
                        'missing':missing}
            return {'request':contract['request'],'kind':contract['kind'],
                    'milestones':[{'id':m['id'],'objective':m['objective'],
                                   'depends_on':m['depends_on'],'checks':m['checks']}
                                  for m in contract['milestones']],
                    'permissions':recipe['permissions'],
                    'terminal_states':recipe['terminal_states'],
                    'budget':contract['budget'],'recipe':contract['recipe']}
        if action=='run':
            info=library.get(data.get('recipe_id',''),project_id=project_id)
            cid=data.get('conversation') or 'main'
            if data.get('project') not in (None,'') and (not data.get('conversation') or self._project_of(cid)!=project_id):
                # D-54: a run started from the Projects page lands in that project's hidden chat.
                cid=self.projects.utility_conversation(project_id)
            library.mark(project_id,info['recipe']['recipe_id'],run=True)
            sid=self.submit({'text':'Run recipe '+info['recipe']['name'],'conversation':cid,
                             'kind':'recipe',
                             'recipe':{'recipe_id':data.get('recipe_id'),
                                       'inputs':data.get('inputs') or {}}})
            return {'submission':sid,'conversation':cid}
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
            lines.append('Reply with "continue <job id>", or open that work\'s card at the top of the chat.')
            self.store.add_message('\n'.join(lines),'assistant',cid)
        else:
            self.store.add_message('There is no unfinished work in this project to continue. New requests start fresh work.','assistant',cid)
        return None

    def state(self,cid='main',project=None):
        from .projects import ALL,job_projects
        with contextlib.closing(self.store.connect()) as db:
            projects=[dict(r) for r in db.execute('SELECT * FROM projects ORDER BY name')]
            for p in projects:
                row=db.execute('SELECT command FROM project_tests WHERE project_id=?',(p['id'],)).fetchone();p['test_command']=json.loads(row['command']) if row else None
            from .schedules import hidden_ids
            hidden=hidden_ids(db)  # D-57: chats of a deleted schedule the person chose to remove
            conversations=[dict(r) for r in db.execute('SELECT * FROM conversations ORDER BY created DESC')
                           if r['id'] not in hidden]
            from .rewind import VISIBLE
            messages=[dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? AND '+VISIBLE+' ORDER BY seq',(cid,))]  # D-75.2
            for message in messages:
                # CH-2/CP-14: per-message details (who answered, what the checks found), on demand.
                try:
                    message['meta']=json.loads(message['meta']) if message.get('meta') else None
                except (TypeError,ValueError):
                    message['meta']=None
            # D-53: a hand-off carries its acknowledgement message and its short title.
            submissions=[dict(r) for r in db.execute('SELECT s.*,a.message_seq AS ack_seq,a.title AS title FROM submissions s '
                                                     'LEFT JOIN submission_acks a ON a.submission_id=s.id '
                                                     'WHERE s.conversation_id=? ORDER BY s.created',(cid,))]
            # Older releases recorded completed direct answers as DISPATCHED without a job.
            # Normalize the read without rewriting preserved conversation history.
            for submission in submissions:
                if submission['state'] == 'DISPATCHED' and not submission['job_id']:
                    submission['state'] = 'SETTLED'
            approvals=[dict(r) for r in db.execute("SELECT a.*,x.action FROM approvals a JOIN approval_actions x ON x.approval_id=a.id WHERE a.status='PENDING'")]
            from .chat_approvals import plain_summary
            for a in approvals:
                try:
                    action=json.loads(a['action']) if isinstance(a['action'],str) else (a['action'] or {})
                except Exception:
                    action={}
                a['action_summary']=plain_summary(action)
            files=[dict(r) for r in db.execute('SELECT id,name,size,mime FROM attachments WHERE conversation_id=?',(cid,))]
            # D-55: a job stopped because its hand-off restarted with a change is not separate work.
            replaced=handoff.replaced_jobs(db)
        # conversation='*' is the all-conversations scope the Work and Activity pages read: every job,
        # every project's continuation candidates, and no per-conversation messages or submissions.
        everywhere=cid==ALL_CONVERSATIONS
        project_id=next((c['project_id'] for c in conversations if c['id']==cid),None)
        # D-54: each project says what it is (general/user/system, archived); `project` narrows jobs
        # and continuation to one project ('*' or None: no narrowing).
        kinds=self.projects.kinds()
        for p in projects:
            p.update(kinds.get(p['id']) or {'kind':'user','archived':None})
        utility=self.projects.utility_ids()
        for c in conversations:
            if c['id'] in utility:c['utility']=True
        narrow=project if project not in (None,'',ALL) else None
        continuation=[]
        scopes=[narrow] if narrow else [p['id'] for p in projects] if everywhere else ([project_id] if project_id else [])
        if scopes:
            from .continuation import Continuation
            for scope in scopes:
                try:
                    continuation.extend(Continuation(self.store).candidates(scope))
                except Exception:
                    pass  # the Work surface must render even if continuation state is unavailable
        jobs=[j for j in self.store.list_jobs() if (everywhere or j['conversation']==cid) and j['id'] not in replaced]
        if narrow:
            conv_map={c['id']:c['project_id'] for c in conversations}
            jobs=[j for j in jobs if narrow in job_projects(j,conv_map)]
        # D12 — the routing decision behind each active run (why this provider/model). The engine
        # already records it on run.claimed; user surfaces translate it into plain language.
        # CP-2: only the active jobs' run.claimed events are read (indexed by job), never the whole
        # event log on every poll.
        routes=self._claimed_routes(j['id'] for j in jobs if j['state'] not in ('CLOSED','CANCELLED'))
        # D-65: a verified coding change says whether it was applied (on its own or by you), can be
        # undone, or is waiting for you and why. Read-only; the engine owns the decision.
        from .auto_apply import describe as describe_applications
        applications=describe_applications(self.store,[j['id'] for j in jobs if j.get('contract',{}).get('kind')=='coding'])
        jobs=[dict(j,application=applications.get(j['id'])) if j.get('contract',{}).get('kind')=='coding' else j for j in jobs]
        return {'projects':projects,'conversations':conversations,'messages':messages,'jobs':jobs,
                'submissions':submissions,'approvals':approvals,'attachments':files,'continuation':continuation,'error':self.error,
                'providers':list(self.engine.adapters),'routes':routes,'connected':True,'engine_version':ENGINE_VERSION,'guardrails_ok':self.engine.tampered is None,'draining':self.draining,
                'restore':_restore_outcome(self.store.root),'scope':'all' if everywhere else 'conversation',
                'project':project or None,'active_project':self.projects.active()}

    def rename_conversation(self,cid,title):
        """POST /api/conversation-title (CH-9): the name the person gave a chat, kept by the engine.

        A chat opened but not yet used (a reserved id, ST-04) is created with that name, since
        renaming it is the person's own act."""
        title=' '.join(str(title or '').split()) if isinstance(title,str) else ''
        if not title or len(title)>120:
            raise PolicyError('A chat name must be 1 to 120 characters.')
        with self.store.transaction() as db:
            renamed=db.execute('UPDATE conversations SET title=? WHERE id=?',(title,str(cid))).rowcount
        if not renamed:
            project=self._project_of(cid)  # refuses anything that is not a reserved chat id
            cid=self.context.conversation(project,title=title,conversation_id=cid)
            with self.store.transaction() as db:
                db.execute('UPDATE conversations SET title=? WHERE id=?',(title,cid))
        return {'id':str(cid),'title':title}

    def _claimed_routes(self,job_ids):
        """Job id -> the routing decision of its latest claimed run (D12), read only for these jobs."""
        ids=list(dict.fromkeys(job_ids));routes={}
        with contextlib.closing(self.store.connect()) as db:
            for start in range(0,len(ids),400):
                part=ids[start:start+400]
                for row in db.execute("SELECT aggregate_id,at,payload FROM events WHERE type='run.claimed' "
                                      'AND aggregate_id IN (%s) ORDER BY seq'%','.join('?'*len(part)),part):
                    try:
                        detail=(json.loads(row['payload'] or '{}') or {}).get('detail') or {}
                    except (TypeError,ValueError):
                        continue
                    if detail.get('route'):
                        routes[row['aggregate_id']]={'provider':detail.get('provider'),'route':detail['route'],'at':row['at']}
        return routes

    def conversations(self):
        """GET /api/conversations (ST-23): every conversation with its message and job counts, in
        two grouped queries — so start-up can skip empty chats without reading each one's state."""
        with contextlib.closing(self.store.connect()) as db:
            from .schedules import hidden_ids,scheduled_conversations
            hidden=hidden_ids(db);scheduled=scheduled_conversations(db)  # D-57
            rows=[dict(r) for r in db.execute('SELECT * FROM conversations ORDER BY created DESC')
                  if r['id'] not in hidden]
            messages={r['conversation_id']:r['n'] for r in db.execute(
                'SELECT conversation_id,COUNT(*) AS n FROM messages GROUP BY conversation_id')}
            jobs={r['c']:r['n'] for r in db.execute(
                "SELECT json_extract(data,'$.conversation') AS c,COUNT(*) AS n FROM jobs GROUP BY c")}
        utility=self.projects.utility_ids()
        for row in rows:
            row['message_count']=messages.get(row['id'],0)
            if row['id'] in scheduled:row['schedule_id']=scheduled[row['id']]
            row['job_count']=jobs.get(row['id'],0)
            if row['id'] in utility:row['utility']=True
        return {'conversations':rows}

    def handoff_view(self,cid,sid):
        """GET /api/handoff (D-53): one hand-off's live state for its in-chat card."""
        with contextlib.closing(self.store.connect()) as db:
            row=db.execute('SELECT s.*,a.message_seq AS ack_seq,a.title AS title FROM submissions s '
                           'LEFT JOIN submission_acks a ON a.submission_id=s.id WHERE s.id=?',(sid,)).fetchone()
            pending=0
            if row and row['job_id']:
                pending=db.execute("SELECT COUNT(*) FROM approvals WHERE job_id=? AND status='PENDING'",
                                   (row['job_id'],)).fetchone()[0]
        if not row or row['conversation_id']!=cid:
            raise PolicyError('That work is not part of this conversation')
        state=row['state']
        if state=='DISPATCHED' and not row['job_id']:
            state='SETTLED'
        view={'submission_id':sid,'conversation':cid,'submission_state':state,'title':row['title'],
              'ack_seq':row['ack_seq'],'job_id':row['job_id'],'state':None,'verdict':None,
              'accepted':0,'total':0,'why':None,'next':None,'error':row['error'],
              'phase':'starting','can_stop':False,'can_retry':state in ('FAILED','INTERRUPTED')}
        if not row['job_id']:
            if state in ('FAILED','INTERRUPTED'):
                view.update(phase='failed_to_start',why=row['error'],
                            next='Retry to start it again.')
            elif state=='SETTLED':
                view.update(phase='needs_look')
            return view
        try:
            job=self.store.get(row['job_id'])
        except KeyError:
            view.update(phase='failed_to_start',why='The work record is missing.')
            return view
        from .continuation import Continuation
        try:
            brief=Continuation(self.store).resume_brief(job['id'])
        except Exception:
            brief={'shipped':[],'why':None,'next':None,'needs_you':False}
        job_state=job.get('state');verdict=job.get('verdict')
        view.update(state=job_state,verdict=verdict if job_state=='CLOSED' else None,
                    accepted=len(brief.get('shipped') or []),total=len(job.get('milestones') or {}),
                    why=brief.get('why'),next=brief.get('next'))
        if job_state in ('CANCELLED','CANCELLING'):
            phase='stopped'
        elif job_state=='CLOSED' and verdict=='VERIFIED' and job['contract'].get('kind')=='coding' and not self._published(job['id']):
            phase='running'  # D-65: settling (maybe applying) the change; the card must not stop on "done" before it
        elif job_state=='CLOSED' and verdict=='VERIFIED' and job['contract'].get('staffing') and self._oracle_attention(job):
            needed=self._oracle_attention(job)  # D-66: a second opinion's blocker needs Nick
            phase='needs_you'
            view.update(why=needed['why'],next=needed['next'])
        elif job_state=='CLOSED' and verdict=='VERIFIED' and job['contract'].get('kind')=='coding' and (waiting:=self._apply_wait(job)):
            phase='needs_you'  # D-70: a checked change waits for Nick's Apply / Leave it on its card
            view.update(why=('Checked and ready. %s, so it waits for you to apply it.'%waiting['waiting_reason'] if waiting.get('ask_first')
                             else 'Checked, but Kel did not apply it on its own: %s.'%waiting['waiting_reason']),
                        next='Choose Apply on its card when you are ready, or Leave it.')
        elif job_state=='CLOSED':
            phase='done' if verdict=='VERIFIED' else 'needs_look'
        elif pending or job_state=='AWAITING_USER' or brief.get('needs_you'):
            phase='needs_you'
            if pending:
                view.update(why='Waiting for your decision on a gated step.',
                            next='Decide on the request card in this conversation.')
        elif job_state in ('WAITING_RESOURCE','BLOCKED'):
            phase='waiting'
            from .core import explain_failure
            note=explain_failure(job)
            if note:view['why']=note
            elif job_state=='BLOCKED':view['why']='A safety rule stopped this work before its next step.'
        else:
            phase='running'
        view.update(phase=phase,can_stop=job_state not in ('CLOSED','CANCELLED','CANCELLING'))
        if job['contract'].get('kind')=='coding':
            # D-65: applied (on its own or by you) with Undo, undone, or waiting for you and why.
            from .auto_apply import describe as describe_applications
            view['application']=describe_applications(self.store,[job['id']]).get(job['id'])
        if job['contract'].get('staffing'):
            # D-70 item 2: staffed work has a top card; the in-thread card becomes one line that
            # names the same state the top card shows.
            from .office import state_of as office_state
            view['staffed']=True
            try:view['office_state']=office_state(self.store,job,brief)[0]
            except Exception:view['office_state']=None
        return view

    def _apply_wait(self,job):
        """The D-65 application entry when a checked change waits for Nick (unanswered), else None."""
        from .auto_apply import describe
        try:
            entry=describe(self.store,[job['id']]).get(job['id']) or {}
        except Exception:
            return None
        return entry if entry.get('waiting_reason') else None

    def _oracle_attention(self,job):
        from .oracle import attention
        try:
            return attention(self.store,job)
        except Exception:
            return None

    def _published(self,job_id):
        with contextlib.closing(self.store.connect()) as db:
            return db.execute('SELECT 1 FROM publications WHERE job_id=? LIMIT 1',(job_id,)).fetchone() is not None

    def action(self,path,data):
        with self.lifecycle_lock:
            if self.draining:raise PolicyError('Kel is restarting for an update. Try again after it opens.')
            if path=='/api/shutdown-idle':
                with self.engine.lock:
                    with contextlib.closing(self.store.connect()) as db:
                        planning=db.execute("SELECT count(*) FROM submissions WHERE state='PLANNING'").fetchone()[0]
                    if planning or self.engine.active or self.engine.reviews or any(j['state'] not in ('CLOSED','CANCELLED') for j in self.store.list_jobs()):
                        raise PolicyError('Work is still open. Finish or cancel it before updating Kel.')
                    self.draining=True;self.stop.set();self.wake.set()
                return {'ok':True,'draining':True}
            try:
                return self._action(path,data)
            finally:
                self.wake.set()  # CH-10: whatever changed, supervision looks at it now

    def _action(self,path,data):
        # V1.5: one identity rule for every engine action family. Actor identity is bound by the
        # authenticated session, never by the request payload.
        if 'actor' in data:
            raise PolicyError('Actor identity comes from the authenticated Kel session, not from the request payload')
        if path=='/api/send':return {'id':self.submit(data)}
        if path=='/api/cancel':
            return self.cancel_submission(str(data.get('conversation') or 'main'),
                                          self._required(data,'id','Pick the message to stop first.'))
        if path=='/api/memory':return self._memory_action(data)
        if path=='/api/map':return self._map_action(data)
        if path=='/api/recipes':return self._recipes_action(data)
        if path=='/api/schedules':return self.schedules.apply(data)
        if path=='/api/activity':
            # V2-08: the historical timeline. Read-only, project-scoped by default, and it can be
            # asked for every project explicitly.
            from .activity import timeline
            scope=data.get('project_id')
            if scope is None and not data.get('all_projects'):
                scope=self._scope(data)
            if scope=='*':scope=None
            return timeline(self.store,project_id=scope,since=data.get('since'),
                            until=data.get('until'),kind=data.get('kind'),
                            failures_only=bool(data.get('failures')),query=data.get('query'),
                            limit=data.get('limit'))
        if path=='/api/retry':
            with self.store.transaction() as db:
                row=db.execute('SELECT s.*,p.packet,p.kind FROM submissions s JOIN submission_packets p ON p.id=s.id WHERE s.id=?',(self._required(data,'id','Pick a request to retry first.'),)).fetchone()
                if not row or row['state'] not in ('FAILED','INTERRUPTED'):raise PolicyError('This request is not ready for retry')
                db.execute("UPDATE submissions SET state='PLANNING',error=NULL WHERE id=?",(row['id'],))
                acked=db.execute('SELECT 1 FROM submission_acks WHERE submission_id=?',(row['id'],)).fetchone()
            packet=json.loads(row['packet'])
            if acked:
                # D-53: the hand-off was already acknowledged in the chat; retrying starts the work
                # again without a second acknowledgement or a second routing decision.
                from .router import classify
                greenfield=bool(classify(row['text']).get('greenfield')) if packet.get('kind_source')!='client' else False
                self.planning.submit(self._start_work,row['id'],row['conversation_id'],row['text'],packet,row['kind'],greenfield)
            else:
                self.requests.submit(self._plan,row['id'],row['conversation_id'],row['text'],packet,row['kind'])
            return {'id':row['id']}
        if path=='/api/conversation':
            # D-54: explicit project → the shell's binding for its chat (`donor`) → active → General.
            # An id the ACP host reserved (ST-04) that already exists keeps its own project.
            return self.projects.create_conversation(self.context,data)
        if path=='/api/conversation-title':
            return self.rename_conversation(self._required(data,'conversation','Pick a chat to rename first.'),
                                            data.get('title'))
        if path=='/api/project':
            if data.get('action'):return self.projects.apply(data)
            return self.projects.legacy_save(self.context,data)  # compat: create-or-overwrite
        if path=='/api/rewind':
            from .rewind import action as rewind_action
            return rewind_action(self,data)  # D-75.2: edit a sent message, regenerate the last reply
        if path=='/api/attach':return {'id':self.context.attach(data['conversation'],data['name'],base64.b64decode(data['content'],validate=True),data.get('mime','text/plain'))}
        if path=='/api/control':
            self.engine.control(self._required(data,'job','Pick a request first.'),
                                self._required(data,'action','Pick what Kel should do first.'));return {'ok':True}
        if path=='/api/apply':
            from .apply_changes import apply_checked,undo_applied
            job=self._required(data,'job','Kel could not find that change to apply.')
            if data.get('action')=='undo':return undo_applied(self.store,job,actor='user')  # D-65 Undo
            if data.get('action') in ('apply_anyway','leave'):
                # D-70: a needs-you card's "Apply anyway" / "Leave it", answered with you as the actor.
                from .needs_answer import answer_apply
                return answer_apply(self.store,job,data['action'],actor='user')
            if data.get('action') not in (None,'apply'):raise PolicyError('Choose Apply or Undo.')
            return apply_checked(self.store,job,actor='user')
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
            payload=dict(data)
            if 'project_id' not in payload:
                payload['project_id']=self._scope(data,write=data.get('action') not in ('get','list'))
            if payload['project_id']=='*' and data.get('action')=='list':
                return {'briefs':[dict(brief,project_id=pid) for pid in self.projects.live_ids()
                                  for brief in SolutionBriefs(self.store).list(pid)]}
            return SolutionBriefs(self.store).apply(payload)
        if path=='/api/team':
            from .team import Team
            return Team(self.store).apply(data)
        if path=='/api/providers':
            from .providers import Providers
            return Providers(self.store,runnable=self._runnable_provider).apply(data)
        if path=='/api/autonomy':
            from .autonomy import Autonomy
            if data.get('action') in ('mode','set_mode'):
                # D-64: Full access (default) or Ask first; only the person's own request changes it.
                from . import authority
                return authority.apply(self.store,dict(data,actor='user'))
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
        if path=='/api/scoping':
            # D-70 item 4: Start (with the answers) or "Just start with your best guess".
            from .scoping import action as scoping_action
            return scoping_action(self,data)
        if path=='/api/office':
            # D-68: the one write the live work view has — remove a finished card (Nick's own act) —
            # and Routing 2 §5.4: raise a budget-stopped job's budget so it continues.
            if data.get('action')=='raise_budget':
                from .budget import raise_class
                result=raise_class(self.store,str(data.get('id') or data.get('job') or ''),actor='user')
                self.wake.set()
                return result
            if data.get('action')!='dismiss':
                raise PolicyError('The work view can only remove a finished card or raise a budget.')
            from .office import dismiss
            return dismiss(self.store,str(data.get('id') or data.get('job') or ''),actor='user')
        raise PolicyError('Unknown action')

    def office(self,query):
        """GET /api/office (D-66/D-68): the work cards for one chat, one project, or everything."""
        from .office import items
        first=lambda name:(query.get(name) or [None])[0]
        return items(self.store,conversation=first('conversation'),project=first('project'))

    def usage_view(self,conversation=None,job=None):
        """GET /api/usage: per message of one conversation ({seq: usage}) and/or one job's totals."""
        from .usage import conversation_usage,job_usage
        if not conversation and not job:
            raise PolicyError('Pick a conversation or a piece of work first.')
        out={}
        if conversation:
            out['conversation']=conversation
            out['messages']=conversation_usage(self.store,conversation)
        if job:
            try:
                record=self.store.get(job)
            except KeyError:
                raise PolicyError('Kel could not find that work.') from None
            out['job']=job
            out['usage']=job_usage(self.store,record)
        return out

    def office_item(self,job):
        """GET /api/office/item (D-66): one piece of work in full, in plain words."""
        from .office import detail
        return detail(self.store,self._required({'job':job},'job','Pick the work to open first.'))

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
        # Local backup/restore of the whole Data tree (engine, chat store, host config; ST-01).
        # Credentials never leave the machine; restore stages files and applies on the next start.
        from .backup import Backup
        action=data.get('action')
        backup=Backup(self.store)
        if action=='create':
            return backup.create(data.get('target'))
        if action=='inspect':
            return backup.inspect(data.get('source'))
        if action=='inventory':
            # V2-17: the manual-upgrade before/after — every table with its row count.
            # ST-01: plus `summary`, in the backup's words (chats counted from the chat store).
            return backup.inventory()
        if action=='restore':
            return backup.stage_restore(data.get('source'))
        if action in ('outcome','outcome-seen','outcome-dismiss'):
            # FN-02: the last restore's outcome for Settings; the one-time notice marks it seen.
            from .backup import mark_outcome,read_outcome
            if action=='outcome':return {'outcome':read_outcome(self.store.root)}
            changes={'notice':False} if action=='outcome-seen' else {'notice':False,'dismissed':True}
            return {'outcome':mark_outcome(self.store.root,**changes)}
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
            for job_id,claimed in self._claimed_routes(jobs).items():
                if latest is None or (claimed['at'] or 0) > latest['at']:
                    latest={'job_id':job_id,'provider':claimed['provider'],'route':claimed['route'],
                            'at':claimed['at'] or 0}
            if latest is None:
                return {'answer':'No model choice has been made for this conversation yet.'}
            staffed=self._staff_why(latest['job_id'])
            if staffed:
                return staffed
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
        if action=='ranking':
            # Routing 2 §5.8: read-only — per task class, the governing role, its tier, and every model
            # in the order Kel would use it, each with the plain reason.
            from . import task_routing
            present=self.staff_adapters()|{name for name in ('codex-code','claude-code','research')
                                           if name in self.engine.adapters}
            return task_routing.overview(self.store,present)
        if action in ('roles','set_role','reset_role'):
            # D-67: the model each staff role runs on (Fixed / Preferred / Automatic) and its
            # reasoning level. Plain labels; the engine owns the catalog and what can run here.
            from . import role_models
            if action=='set_role':
                role_models.set_role(self.store,self._required(data,'role','Pick a role first.'),
                                     data.get('mode'),data.get('model'),data.get('reasoning') or 'auto')
            elif action=='reset_role':
                role_models.reset_role(self.store,self._required(data,'role','Pick a role first.'))
            present=self.staff_adapters()|{name for name in ('codex-code','claude-code','research')
                                           if name in self.engine.adapters}
            return role_models.listing(self.store,present)
        if action in ('get','list'):
            # Both actions carry the provider listing: the Kel model control reads the choice
            # and the choices from one payload, and a missing list is what made the settings
            # card and the chat pill fail to render.
            snapshot=prefs.snapshot(data.get('conversation'))
            providers=Providers(self.store,runnable=self._runnable_provider)
            listing=[]
            for item in DEFINITIONS:
                status=providers.status(item['id'])
                # CH-2/CP-3: available only when Kel can actually answer with it here.
                usable=status['available'];note=status['available_note']
                listing.append({
                    'id':item['id'],
                    'label':provider_label(item['id']),
                    'available':usable,
                    'note':note,
                    'options':[{'id':model.get('id'),
                                'label':model_label(model.get('id')) or model.get('id'),
                                'available':usable,'note':note} for model in item.get('models',())],
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
        if action=='build_update':
            # Kibble Build Update (D-46): a development mission and a reviewable candidate, on the
            # existing work machinery. The runtime entry is the same action/bridge pattern as the
            # rest of Kel; installation is NOT part of it and `promote` refuses by design.
            from .build_update import BuildUpdate
            builder=BuildUpdate(self.store)
            op=data.get('op') or 'status'
            if op=='start':
                return builder.start(data.get('findings') or [],
                                     source_root=self._required(data,'source_root','Pick the repository folder first.'),
                                     tests=data.get('tests') or [],
                                     scope=data.get('scope'),
                                     conversation=data.get('conversation') or 'main',
                                     project_id=data.get('project_id'))
            if op=='status':
                return builder.status(self._required(data,'mission','Which development mission?'))
            if op=='candidate':
                return builder.candidate(self._required(data,'mission','Which development mission?'))
            if op=='review':
                return builder.review(self._required(data,'candidate','Which candidate?'),
                                      data.get('decision'),note=data.get('note',''))
            if op=='promote':
                return builder.promote(data.get('candidate'))
            raise PolicyError('Unknown Build Update action.')
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
                    if parsed.path=='/api/state':self.reply(200,service.state(query.get('conversation',['main'])[0],(query.get('project') or [None])[0]));return
                    if parsed.path=='/api/work':self.reply(200,service._work(query.get('conversation',['main'])[0],(query.get('project') or [None])[0]));return
                    if parsed.path=='/api/conversations':self.reply(200,service.conversations());return
                    if parsed.path=='/api/health':
                        # CP-2: the desktop's 5 s liveness ping — no database work at all.
                        self.reply(200,{'ok':True,'engine_version':ENGINE_VERSION,'draining':service.draining});return
                    if parsed.path=='/api/office':self.reply(200,service.office(query));return
                    if parsed.path=='/api/draft':
                        # D-75.1: the chat's cheap poll for a reply's words while they are written.
                        self.reply(200,service.draft((query.get('id') or [''])[0]));return
                    if parsed.path=='/api/scoping':
                        from .scoping import view as scoping_view
                        self.reply(200,scoping_view(service.store,(query.get('id') or [''])[0],
                                                    (query.get('conversation') or [None])[0]));return
                    if parsed.path=='/api/usage':
                        # D-72: what Kel's messages and one piece of work used (tokens, time, cost).
                        self.reply(200,service.usage_view((query.get('conversation') or [None])[0],
                                                          (query.get('job') or [None])[0]));return
                    if parsed.path=='/api/office/item':
                        self.reply(200,service.office_item((query.get('job') or [''])[0]));return
                    if parsed.path=='/api/handoff':
                        self.reply(200,service.handoff_view(query.get('conversation',['main'])[0],
                                                            (query.get('submission') or [''])[0]));return
                    if parsed.path=='/api/dogfood':self.reply(200,service._dogfood_list(query.get('status',[None])[0]));return
                    if parsed.path=='/api/activity':
                        from .activity import timeline
                        def _first(name):
                            return (query.get(name) or [None])[0]
                        self.reply(200,timeline(service.store,
                                                project_id=None if _first('project')=='*' else _first('project'),
                                                since=_first('since'),until=_first('until'),
                                                kind=_first('kind'),
                                                failures_only=_first('failures') in ('1','true','yes'),
                                                query=_first('query'),limit=_first('limit')));return
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
        service.stop.set();service.wake.set();service.supervisor.join(timeout=2)
        service.requests.shutdown(wait=True)
        service.planning.shutdown(wait=True)
        service.engine.close();server.server_close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--port',type=int,default=0)
    args=p.parse_args()
    try:serve(args.data,args.port)
    except Conflict as exc:print(str(exc),flush=True);raise SystemExit(2)
