"""Durable work engine. SQLite transactions own budgets, leases and verdicts.

The prototype stores immutable aggregate snapshots in events. jobs is a rebuildable
projection, not completion authority. Only assess() produces completion records.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid


def uid():
    return str(uuid.uuid4())


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encode(value).encode()).hexdigest()


class Conflict(Exception):
    pass


class PolicyError(Exception):
    pass


def validate_contract(contract):
    if not isinstance(contract, dict) or not isinstance(contract.get("request"), str) or not contract["request"].strip():
        raise PolicyError("A nonempty source request is required")
    milestones = contract.get("milestones", [])
    if not isinstance(milestones, list) or not 1 <= len(milestones) <= 5:
        raise PolicyError("Provide one to five milestones")
    if any(not isinstance(m,dict) for m in milestones):
        raise PolicyError('Milestones must be objects')
    ids = {m.get("id") for m in milestones}
    if len(ids) != len(milestones) or any(not isinstance(i, str) or not i for i in ids):
        raise PolicyError("Milestone IDs must be unique nonempty strings")
    filenames = set()
    for m in milestones:
        if not isinstance(m.get("objective"), str) or not m["objective"].strip():
            raise PolicyError("Each milestone needs an objective")
        filename = m.get("filename", "")
        if not isinstance(filename, str) or not filename.endswith(".md") or any(c in filename for c in '/\\:') or filename.startswith('.'):
            raise PolicyError("Outputs must be simple Markdown filenames")
        if filename in filenames:
            raise PolicyError("Milestones cannot share an output filename")
        filenames.add(filename)
        checks = m.get("checks", [])
        if not checks or len(checks) > 20:
            raise PolicyError("Every milestone needs one to twenty acceptance checks")
        for check in checks:
            if not isinstance(check,dict):
                raise PolicyError('Checks must be objects')
            kind = check.get("kind")
            if kind not in ("contains", "min_chars", "manual_review"):
                raise PolicyError("Only trusted built-in checks are allowed; executable oracles are forbidden")
            if kind == "contains" and (not isinstance(check.get("value"), str) or not check["value"].strip()):
                raise PolicyError("Contains checks need a nonempty literal")
            if kind == "min_chars" and (type(check.get("value")) is not int or not 1 <= check["value"] <= 100000):
                raise PolicyError("Minimum length must be between 1 and 100000")
            if kind == "manual_review" and not check.get("rubric"):
                raise PolicyError("Review requires an explicit rubric")
        if not isinstance(m.get('depends_on',[]),list):
            raise PolicyError('Dependencies must be a list')
        if not set(m.get("depends_on", [])).issubset(ids - {m['id']}):
            raise PolicyError("Invalid milestone dependency")
    done = set()
    while len(done) < len(ids):
        ready = {m['id'] for m in milestones if set(m.get('depends_on', [])).issubset(done)} - done
        if not ready:
            raise PolicyError("Dependency cycle")
        done |= ready
    return contract


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "kel.sqlite3"
        (self.root / "artifacts").mkdir(exist_ok=True)
        with contextlib.closing(self.connect()) as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS events(
                seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                aggregate_id TEXT NOT NULL, revision INTEGER NOT NULL,
                type TEXT NOT NULL, at REAL NOT NULL, payload TEXT NOT NULL,
                dedupe TEXT UNIQUE, UNIQUE(aggregate_id,revision));
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS contracts(job_id TEXT, version INTEGER, digest TEXT,
                data TEXT, PRIMARY KEY(job_id,version));
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, job_id TEXT, milestone_id TEXT,
                epoch TEXT, state TEXT, reservation INTEGER, expires REAL, result TEXT,
                native_session TEXT, provider TEXT, model TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_milestone ON runs(job_id,milestone_id)
                WHERE state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED');
            CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, run_id TEXT, epoch TEXT,
                payload TEXT, handled INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, job_id TEXT, run_id TEXT,
                action_digest TEXT, status TEXT, expires REAL, actor TEXT);
            CREATE TABLE IF NOT EXISTS effects(id TEXT PRIMARY KEY, job_id TEXT, action_digest TEXT,
                state TEXT, receipt TEXT);
            CREATE TABLE IF NOT EXISTS assessments(id TEXT PRIMARY KEY, job_id TEXT,
                contract_version INTEGER, verdict TEXT, data TEXT, at REAL);
            CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY, job_id TEXT,
                assessment_id TEXT UNIQUE, text TEXT, at REAL);
            CREATE TABLE IF NOT EXISTS messages(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT, role TEXT, text TEXT, job_id TEXT, at REAL);
            CREATE TABLE IF NOT EXISTS providers(id TEXT PRIMARY KEY, data TEXT);
            CREATE TABLE IF NOT EXISTS controller(id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS job_intakes(id TEXT PRIMARY KEY,job_id TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS routing_outcomes(run_id TEXT PRIMARY KEY,provider TEXT,verdict TEXT);
            """)
            # B3: executor model provenance. Older data dirs predate the column.
            if 'model' not in {r[1] for r in db.execute('PRAGMA table_info(runs)')}:
                db.execute('ALTER TABLE runs ADD COLUMN model TEXT')

    def connect(self):
        # A killed Windows process can briefly retain a WAL mapping. Retry only
        # opening a connection, before any application transaction is submitted.
        for attempt in range(11):
            db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
            try:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA foreign_keys=ON")
                db.execute("PRAGMA synchronous=FULL")
                return db
            except sqlite3.OperationalError as exc:
                db.close()
                if os.name!='nt' or 'disk I/O error' not in str(exc) or attempt==10:raise
                time.sleep(.1)

    @contextlib.contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def _get(self, db, job_id):
        row = db.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        return json.loads(row['data'])

    def _save(self, db, job, event, detail=None):
        old = db.execute("SELECT revision FROM jobs WHERE id=?", (job['id'],)).fetchone()
        if old and old['revision'] != job['revision']:
            raise Conflict("Stale aggregate revision")
        job['revision'] += 1
        payload = {"schema_version": 1, "job": job, "detail": detail or {}}
        db.execute("INSERT INTO events(id,aggregate_id,revision,type,at,payload) VALUES(?,?,?,?,?,?)",
                   (uid(), job['id'], job['revision'], event, time.time(), encode(payload)))
        db.execute("INSERT INTO jobs VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,data=excluded.data",
                   (job['id'], job['revision'], encode(job)))

    def create(self, contract, budget=8, conversation="main"):
        validate_contract(contract)
        if type(budget) is not int or not 1 <= budget <= 100:
            raise PolicyError("Budget must be 1 to 100 attempt units")
        job_id = uid()
        job = dict(id=job_id, revision=0, contract_version=1, contract=contract,
                   state="READY", verdict="UNCERTAIN", budget=budget, spent=0, reserved=0,
                   conversation=conversation, assessment=None, created=time.time(),
                   milestones={m['id']: dict(state="READY", attempts=0, artifact=None,
                               checks=[], error=None, provider=None) for m in contract['milestones']})
        with self.transaction() as db:
            intake=contract.get('submission_id')
            if intake:
                prior=db.execute('SELECT job_id FROM job_intakes WHERE id=?',(intake,)).fetchone()
                if prior:return prior['job_id']
                db.execute('INSERT INTO job_intakes VALUES(?,?)',(intake,job_id))
            db.execute("INSERT INTO contracts VALUES(?,?,?,?)", (job_id, 1, digest(contract), encode(contract)))
            self._save(db, job, "job.created")
            db.execute("INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)",
                       (conversation, 'user', contract['request'], job_id, time.time()))
        return job_id

    def get(self, job_id):
        with contextlib.closing(self.connect()) as db:
            return self._get(db, job_id)

    def list_jobs(self):
        with contextlib.closing(self.connect()) as db:
            return [json.loads(r['data']) for r in db.execute("SELECT data FROM jobs ORDER BY rowid DESC")]

    def claim(self, job_id, milestone_id, provider="fixture", timeout=120, max_attempts=4, route=None, model=None):
        with self.transaction() as db:
            job = self._get(db, job_id)
            if job['state'] not in ('READY', 'RUNNING', 'VERIFYING'):
                raise PolicyError("Job is not runnable")
            m = job['milestones'][milestone_id]
            spec = next(x for x in job['contract']['milestones'] if x['id'] == milestone_id)
            if any(job['milestones'][d]['state'] != 'ACCEPTED' for d in spec.get('depends_on', [])):
                raise PolicyError("Dependencies not accepted")
            if m['state'] not in ('READY', 'NEEDS_REPAIR', 'INVALIDATED') or m['attempts'] >= max_attempts:
                raise PolicyError("Milestone cannot run")
            if db.execute("SELECT count(*) FROM runs WHERE state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')").fetchone()[0]>=2:
                raise PolicyError('Global worker concurrency limit reached')
            # One execution unit plus one verification unit must remain available.
            if job['budget'] - job['spent'] - job['reserved'] < 2:
                raise PolicyError("Execution and verification budget exhausted")
            run_id, epoch = uid(), uid()
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (run_id, job_id, milestone_id, epoch, 'RUNNING', 2, time.time()+timeout, None, None, provider, model))
            m.update(state='RUNNING', attempts=m['attempts']+1, provider=provider, model=model, error=None)
            job.update(state='RUNNING', reserved=job['reserved']+2, verdict='UNCERTAIN', assessment=None)
            self._save(db, job, "run.claimed", {"run_id": run_id, "epoch": epoch, "provider": provider,"route":route})
            return dict(id=run_id, epoch=epoch, job_id=job_id, milestone_id=milestone_id,
                        contract_version=job['contract_version'], spec=spec, attempt=m['attempts'], provider=provider, model=model)

    def enqueue_result(self, event_id, run_id, epoch, result):
        if not isinstance(result, dict):
            raise PolicyError("Worker result must be an object")
        with self.transaction() as db:
            cur = db.execute("INSERT OR IGNORE INTO inbox(id,run_id,epoch,payload) VALUES(?,?,?,?)",
                             (event_id, run_id, epoch, encode(result)))
            return cur.rowcount == 1

    def _artifact(self, job_id, milestone_id, run_id, text, filename='result.md'):
        if not isinstance(text, str) or len(text.encode('utf-8')) > 1_000_000:
            raise PolicyError("Output must be UTF-8 text under one megabyte")
        raw = text.encode('utf-8')
        relative = Path('artifacts') / job_id / run_id / filename
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        with temp.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        return dict(path=str(relative), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                    job_id=job_id, milestone_id=milestone_id, run_id=run_id, captured=time.time())

    def consume(self):
        """Idempotent inbox reduction. Worker claims never assign a verdict."""
        count = 0
        with self.transaction() as db:
            for event in db.execute("SELECT * FROM inbox WHERE handled=0 ORDER BY rowid").fetchall():
                run = db.execute("SELECT * FROM runs WHERE id=?", (event['run_id'],)).fetchone()
                if not run or run['epoch'] != event['epoch']:
                    db.execute("UPDATE inbox SET handled=1 WHERE id=?", (event['id'],))
                    continue
                if run['state'] == 'CANCEL_REQUESTED':
                    # A stop was requested while the worker was launching: the
                    # terminal receipt doubles as the stop acknowledgement.
                    # Without this, a cancel that races the broker launch leaves
                    # the job CANCELLING until the lease expires and then stuck.
                    job = self._get(db, run['job_id'])
                    result = json.loads(event['payload'])
                    job['reserved'] -= run['reservation']
                    job['spent'] += 1
                    job['milestones'][run['milestone_id']]['state'] = 'READY' if job['state'] == 'PAUSING' else 'CANCELLED'
                    db.execute("UPDATE runs SET state='CANCELLED',result=?,reservation=0 WHERE id=?",
                               (encode(result), run['id']))
                    n = db.execute("SELECT count(*) FROM runs WHERE job_id=? AND state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')",
                                   (job['id'],)).fetchone()[0]
                    if not n:
                        job['state'] = 'PAUSED' if job['state'] == 'PAUSING' else 'CANCELLED'
                    db.execute("UPDATE inbox SET handled=1 WHERE id=?", (event['id'],))
                    self._save(db, job, 'run.stopped', {'run_id': run['id'], 'receipt': result.get('outcome')})
                    count += 1
                    continue
                if run['state'] != 'RUNNING':
                    db.execute("UPDATE inbox SET handled=1 WHERE id=?", (event['id'],))
                    continue
                job = self._get(db, run['job_id'])
                result = json.loads(event['payload'])
                m = job['milestones'][run['milestone_id']]
                outcome = result.get('outcome')
                if outcome not in ('SUCCESS', 'PARTIAL', 'FAILED', 'BLOCKED', 'CANCELLED'):
                    result = {"outcome": "FAILED", "error": "Malformed worker result"}
                    outcome = 'FAILED'
                if outcome in ('SUCCESS', 'PARTIAL') and isinstance(result.get('text'), str):
                    spec=next(s for s in job['contract']['milestones'] if s['id']==run['milestone_id'])
                    m['artifact'] = self._artifact(job['id'], run['milestone_id'], run['id'], result['text'], spec['filename'])
                    m.update(state='CHECKING', error=None)
                else:
                    m.update(state='NEEDS_REPAIR', error=result.get('error', 'Missing output text'))
                held = 1 if m['state'] == 'CHECKING' else 0
                job['reserved'] -= run['reservation'] - held
                job['spent'] += 1  # The other reserved unit remains available for immediate verification.
                job['state'] = 'RUNNING'
                db.execute("UPDATE runs SET state='RESULT_RECORDED',result=?,native_session=?,reservation=? WHERE id=?",
                           (encode(result), result.get('session_id'), held, run['id']))
                db.execute("UPDATE inbox SET handled=1 WHERE id=?", (event['id'],))
                self._save(db, job, 'worker.result_recorded', {'run_id': run['id'], 'outcome': outcome})
                count += 1
        return count

    def artifact_text(self, artifact):
        path = (self.root / artifact['path']).resolve()
        if not path.is_relative_to((self.root / 'artifacts').resolve()):
            raise PolicyError("Artifact escaped its root")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != artifact['sha256']:
            raise PolicyError("Artifact changed after capture")
        return raw.decode('utf-8')

    def verify(self, job_id, milestone_id):
        with self.transaction() as db:
            job = self._get(db, job_id)
            m = job['milestones'][milestone_id]
            if m['state'] not in ('CHECKING', 'ACCEPTED'):
                raise PolicyError("No candidate to verify")
            spec = next(x for x in job['contract']['milestones'] if x['id'] == milestone_id)
            checks = []
            try:
                if m['artifact']['job_id'] != job_id or m['artifact']['milestone_id'] != milestone_id:
                    raise PolicyError("Evidence belongs to another subject")
                text = self.artifact_text(m['artifact'])
                checks.append(dict(kind='artifact_digest', verdict='VERIFIED', subject=m['artifact']['sha256']))
                if job['contract'].get('kind')=='coding':
                    from .coding import check_evidence
                    checks.append(dict(kind='repository_evidence',verdict=check_evidence(self,m['artifact']['run_id'])))
                if m['provider']=='research' or 'web_research' in spec.get('required_capabilities',job['contract'].get('required_capabilities',[])):
                    from .research import check_research_evidence
                    checks.append(dict(kind='research_evidence',verdict='VERIFIED' if check_research_evidence(self,m['artifact']['run_id'],text) else 'UNCERTAIN'))
                for criterion in spec['checks']:
                    kind = criterion['kind']
                    if kind == 'contains':
                        passed = criterion['value'] in text
                    elif kind == 'min_chars':
                        passed = len(text.strip()) >= criterion['value']
                    else:
                        checks.append(dict(kind=kind, verdict='UNCERTAIN', reason='Independent rubric review not recorded'))
                        continue
                    checks.append(dict(kind=kind, verdict='VERIFIED' if passed else 'FAILED', expected=criterion.get('value')))
            except (OSError, UnicodeError, PolicyError, TypeError, KeyError) as exc:
                checks.append(dict(kind='artifact_integrity', verdict='UNCERTAIN', reason=str(exc)))
            verdict = aggregate([c['verdict'] for c in checks])
            old_state = m['state']
            m.update(checks=checks, state='ACCEPTED' if verdict == 'VERIFIED' else ('NEEDS_REPAIR' if verdict == 'FAILED' else 'UNCERTAIN'))
            if old_state == 'CHECKING':
                job['spent'] += 1
                job['reserved'] -= 1
                db.execute("UPDATE runs SET reservation=0,state='EXITED' WHERE id=?", (m['artifact']['run_id'],))
            self._save(db, job, 'criterion.checked', {'milestone_id': milestone_id, 'verdict': verdict,
                                                   'oracle_version': 'builtins-v1'})
            return verdict

    def record_review(self, job_id, milestone_id, subject_digest, reviewer_id, verdict, findings, expected_contract_version=None, reviewer_provider=None, reviewer_model=None):
        """Trusted reviewer boundary. Executors cannot self-accept a quality criterion."""
        if verdict not in ('VERIFIED','FAILED','UNCERTAIN') or not isinstance(findings,list) or not findings:
            raise PolicyError('A review needs a verdict and concrete findings')
        with self.transaction() as db:
            job = self._get(db, job_id)
            if expected_contract_version is not None and job['contract_version']!=expected_contract_version:
                raise Conflict('Review belongs to a superseded contract')
            m = job['milestones'][milestone_id]
            if not m['artifact'] or m['artifact']['sha256'] != subject_digest:
                raise PolicyError('Review subject changed')
            if reviewer_id == m['artifact']['run_id']:
                raise PolicyError('Executor cannot serve as independent reviewer')
            self.artifact_text(m['artifact'])
            if not any(c['kind']=='manual_review' for c in m['checks']):
                raise PolicyError('No review criterion')
            for c in m['checks']:
                if c['kind']=='manual_review':
                    c.update(verdict=verdict, reviewer_id=reviewer_id, findings=findings,
                             subject=subject_digest, contract_version=job['contract_version'],
                             reviewer_provider=reviewer_provider, reviewer_model=reviewer_model)
                    c.pop('reason',None)
            combined=aggregate([c['verdict'] for c in m['checks']])
            m['state']='ACCEPTED' if combined=='VERIFIED' else ('NEEDS_REPAIR' if combined=='FAILED' else 'UNCERTAIN')
            if combined in ('VERIFIED','FAILED'):
                db.execute('INSERT OR IGNORE INTO routing_outcomes VALUES(?,?,?)',(m['artifact']['run_id'],m['provider'],combined))
                samples=db.execute('SELECT verdict FROM routing_outcomes WHERE provider=?',(m['provider'],)).fetchall()
                old=db.execute('SELECT data FROM providers WHERE id=?',(m['provider'],)).fetchone()
                provider_state=json.loads(old['data']) if old else {'failures':0,'circuit_until':0,'quota':None}
                provider_state.update(quality_samples=len(samples),quality=sum(r['verdict']=='VERIFIED' for r in samples)/len(samples) if len(samples)>=3 else None)
                db.execute('INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(m['provider'],encode(provider_state)))
            self._save(db,job,'review.recorded',{'reviewer_id':reviewer_id,'reviewer_provider':reviewer_provider,'reviewer_model':reviewer_model,'verdict':combined})
            return combined

    def assess(self, job_id):
        with self.transaction() as db:
            job = self._get(db, job_id)
            if job['state'] in ('CANCELLED', 'CANCELLING'):
                return 'UNCERTAIN'
            states = []
            for m in job['milestones'].values():
                if m['state'] == 'ACCEPTED':
                    try:
                        self.artifact_text(m['artifact'])
                        if job['contract'].get('kind')=='coding':
                            from .coding import check_evidence
                            states.append(check_evidence(self,m['artifact']['run_id']))
                        elif m['provider']=='research':
                            from .research import check_research_evidence
                            states.append('VERIFIED' if check_research_evidence(self,m['artifact']['run_id'],self.artifact_text(m['artifact'])) else 'UNCERTAIN')
                        else:
                            states.append('VERIFIED')
                    except (OSError, PolicyError, UnicodeError):
                        m['state'] = 'INVALIDATED'
                        states.append('UNCERTAIN')
                elif m['state'] in ('NEEDS_REPAIR', 'EXHAUSTED'):
                    states.append('FAILED')
                else:
                    states.append('UNCERTAIN')
            active = db.execute("SELECT count(*) FROM runs WHERE job_id=? AND state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')", (job_id,)).fetchone()[0]
            unresolved = db.execute("SELECT count(*) FROM effects WHERE job_id=? AND state!='OBSERVED'", (job_id,)).fetchone()[0]
            if active or unresolved:
                states.append('UNCERTAIN')
            verdict = aggregate(states)
            evidence = {"milestones": job['milestones'], "active_runs": active, "unresolved_effects": unresolved}
            assessment_id = digest([job_id, job['contract_version'], verdict, evidence])
            db.execute("INSERT OR IGNORE INTO assessments VALUES(?,?,?,?,?,?)",
                       (assessment_id, job_id, job['contract_version'], verdict, encode(evidence), time.time()))
            job.update(verdict=verdict, assessment=assessment_id)
            if verdict == 'VERIFIED':
                job['state'] = 'CLOSED'
            elif not active and job['state'] not in ('PAUSED', 'AWAITING_USER', 'WAITING_RESOURCE'):
                job['state'] = 'READY' if any(m['state'] in ('READY', 'NEEDS_REPAIR', 'INVALIDATED') and m['attempts'] < 4 for m in job['milestones'].values()) else 'CLOSED'
            self._save(db, job, 'completion.assessed', {'assessment_id': assessment_id, 'verdict': verdict})
            return verdict

    def publish(self, job_id):
        # Reassess immediately, including bytes, before a completion publication.
        self.assess(job_id)
        with self.transaction() as db:
            job = self._get(db, job_id)
            if job['state'] != 'CLOSED' or not job['assessment']:
                raise PolicyError("Job is not settled")
            accepted={mid:m for mid,m in job['milestones'].items() if m['state']=='ACCEPTED'}
            final_id=job['contract'].get('final_milestone')
            if final_id and final_id in accepted:accepted={final_id:accepted[final_id]}
            if job['verdict']=='VERIFIED':
                text='\n\n'.join(self.artifact_text(m['artifact']) for m in accepted.values())
                if job['contract'].get('kind')=='coding':
                    if job['contract'].get('greenfield'):
                        text=('Your new project is ready at '+str(job['contract'].get('root'))+
                              '. The code passed its tests and a separate review. '
                              'Download the change report to see what was built, then use Apply checked changes to write the files into the project folder.')
                    else:
                        text='The change passed its tests and a separate review. It is ready in an isolated project copy. Your original project is unchanged. Download the change report to inspect the diff.'
                        if job['contract'].get('runtime')=='native-host':
                            text='The change passed its tests and a separate review. Download the change report to inspect the project copy. Apply checked changes will check your original project for conflicts and save a backup.'
            else:
                text=(explain_failure(job)
                      or ('I could not verify the complete result.' if job['verdict']=='UNCERTAIN' else 'The result did not pass its checks.'))
            summary=verification_summary(job)
            if summary:
                text=(text+'\n\n'+summary) if text else summary
            key = digest([job_id, job['assessment']])
            cur = db.execute("INSERT OR IGNORE INTO publications VALUES(?,?,?,?,?)",
                             (key, job_id, job['assessment'], text, time.time()))
            if cur.rowcount:
                db.execute("INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)",
                           (job['conversation'], 'assistant', text, job_id, time.time()))
            return text, bool(cur.rowcount)

    def control(self, job_id, action):
        with self.transaction() as db:
            job = self._get(db, job_id)
            active = db.execute("SELECT * FROM runs WHERE job_id=? AND state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')", (job_id,)).fetchall()
            if action=='pause' and job['state'] in ('CANCELLING','CANCELLED','PAUSING','PAUSED'):
                return [r['id'] for r in active]
            if action=='cancel' and job['state'] in ('CANCELLING','CANCELLED'):
                return [r['id'] for r in active]
            if action == 'resume':
                if job['state'] != 'PAUSED':
                    raise PolicyError("Only a paused job can resume")
                job['state'] = 'READY'
            elif action in ('cancel', 'pause'):
                job['state'] = ('CANCELLING' if action == 'cancel' else 'PAUSING') if active else ('CANCELLED' if action == 'cancel' else 'PAUSED')
                for r in active:
                    db.execute("UPDATE runs SET state='CANCEL_REQUESTED' WHERE id=?", (r['id'],))
                db.execute("UPDATE approvals SET status='CANCELLED' WHERE job_id=? AND status='PENDING'", (job_id,))
            else:
                raise PolicyError("Unknown control")
            self._save(db, job, 'job.'+action)
            return [r['id'] for r in active]

    def acknowledge_stop(self, run_id, epoch):
        with self.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run or run['epoch'] != epoch or run['state'] not in ('CANCEL_REQUESTED', 'RUNNING', 'WAITING_APPROVAL'):
                return False
            job = self._get(db, run['job_id'])
            job['reserved'] -= run['reservation']
            job['spent'] += 1
            m = job['milestones'][run['milestone_id']]
            m['state'] = 'READY' if job['state'] == 'PAUSING' else 'CANCELLED'
            db.execute("UPDATE runs SET state='CANCELLED' WHERE id=?", (run_id,))
            n = db.execute("SELECT count(*) FROM runs WHERE job_id=? AND state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')", (job['id'],)).fetchone()[0]
            if not n:
                job['state'] = 'PAUSED' if job['state'] == 'PAUSING' else 'CANCELLED'
            self._save(db, job, 'run.stopped', {'run_id': run_id})
            return True

    def recover_expired(self, now=None):
        """Fence expired runs. Do not replay an unconfirmed external writer."""
        now = time.time() if now is None else now
        recovered = []
        with self.transaction() as db:
            for run in db.execute("SELECT * FROM runs WHERE state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED') AND expires<?", (now,)).fetchall():
                job = self._get(db, run['job_id'])
                db.execute("UPDATE runs SET state='ORPHANED',epoch=? WHERE id=?", (uid(), run['id']))
                job['reserved'] -= run['reservation']
                job['spent'] += 1
                job['milestones'][run['milestone_id']].update(state='UNCERTAIN', error='Expired run; native state requires reconciliation')
                job.update(state='WAITING_RESOURCE', verdict='UNCERTAIN')
                self._save(db, job, 'run.orphaned', {'run_id': run['id']})
                recovered.append(run['id'])
        return recovered

    def request_approval(self, job_id, run_id, action, seconds=60):
        approval_id = uid()
        with self.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=? AND job_id=? AND state='RUNNING'", (run_id, job_id)).fetchone()
            if not run:
                raise PolicyError("No active matching run")
            job = self._get(db, job_id)
            db.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?)",
                       (approval_id, job_id, run_id, digest(action), 'PENDING', time.time()+seconds, None))
            db.execute("UPDATE runs SET state='WAITING_APPROVAL' WHERE id=?", (run_id,))
            job['state'] = 'AWAITING_USER'
            self._save(db, job, 'approval.requested', {'approval_id': approval_id, 'action_digest': digest(action)})
        return approval_id

    def resolve_approval(self, approval_id, action, allow, actor='user'):
        if actor != 'user':
            raise PolicyError("Only user input can resolve an approval")
        with self.transaction() as db:
            a = db.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
            if not a or a['status'] != 'PENDING' or a['action_digest'] != digest(action):
                raise PolicyError("Approval does not match this action")
            run = db.execute("SELECT * FROM runs WHERE id=?", (a['run_id'],)).fetchone()
            status = 'EXPIRED' if a['expires'] < time.time() else ('APPROVED' if allow else 'DENIED')
            if run['state'] != 'WAITING_APPROVAL':
                raise PolicyError("Run no longer awaits this approval")
            db.execute("UPDATE approvals SET status=?,actor=? WHERE id=?", (status, actor, approval_id))
            job = self._get(db, a['job_id'])
            if status == 'APPROVED':
                db.execute("UPDATE runs SET state='RUNNING' WHERE id=?", (run['id'],))
                job['state'] = 'RUNNING'
            else:
                db.execute("UPDATE runs SET state='CANCEL_REQUESTED' WHERE id=?", (run['id'],))
                job['state'] = 'CANCELLING'
            self._save(db, job, 'approval.resolved', {'approval_id': approval_id, 'status': status})
            return status

    def prepare_effect(self, job_id, operation_id, action):
        with self.transaction() as db:
            old = db.execute("SELECT * FROM effects WHERE id=?", (operation_id,)).fetchone()
            if old:
                if old['action_digest'] != digest(action) or old['job_id'] != job_id:
                    raise PolicyError("Operation identity reused for a different effect")
                return old['state']
            job = self._get(db, job_id)
            db.execute("INSERT INTO effects VALUES(?,?,?,?,?)", (operation_id, job_id, digest(action), 'PREPARED', None))
            self._save(db, job, 'effect.prepared', {'operation_id': operation_id})
            return 'PREPARED'

    def observe_effect(self, operation_id, receipt):
        if not receipt:
            raise PolicyError("Effect needs a receipt")
        with self.transaction() as db:
            e = db.execute("SELECT * FROM effects WHERE id=?", (operation_id,)).fetchone()
            if not e:
                raise KeyError(operation_id)
            db.execute("UPDATE effects SET state='OBSERVED',receipt=? WHERE id=?", (encode(receipt), operation_id))
            job = self._get(db, e['job_id'])
            self._save(db, job, 'effect.observed', {'operation_id': operation_id})

    def revise(self, job_id, contract, expected_revision):
        validate_contract(contract)
        with self.transaction() as db:
            job = self._get(db, job_id)
            if job['revision'] != expected_revision:
                raise Conflict("Newer job changes exist")
            if db.execute("SELECT count(*) FROM runs WHERE job_id=? AND state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')", (job_id,)).fetchone()[0]:
                raise PolicyError("Pause and quiesce runs before changing scope")
            old_specs = {m['id']: m for m in job['contract']['milestones']}
            milestones = {}
            for spec in contract['milestones']:
                old = job['milestones'].get(spec['id'])
                milestones[spec['id']] = old if old and old['state'] == 'ACCEPTED' and old_specs[spec['id']] == spec else dict(state='READY', attempts=0, artifact=None, checks=[], error=None, provider=None)
            # Invalidate unchanged downstream specifications when an input changed.
            changed=True
            while changed:
                changed=False
                for spec in contract['milestones']:
                    if milestones[spec['id']]['state']=='ACCEPTED' and any(milestones[d]['state']!='ACCEPTED' for d in spec.get('depends_on',[])):
                        milestones[spec['id']]=dict(state='READY',attempts=0,artifact=None,checks=[],error='Dependency changed',provider=None)
                        changed=True
            job.update(contract=contract, contract_version=job['contract_version']+1, milestones=milestones,
                       state='READY', verdict='UNCERTAIN', assessment=None)
            db.execute("INSERT INTO contracts VALUES(?,?,?,?)", (job_id, job['contract_version'], digest(contract), encode(contract)))
            self._save(db, job, 'contract.revised')

    def rebuild(self):
        with self.transaction() as db:
            snapshots = {}
            for row in db.execute("SELECT payload FROM events ORDER BY seq"):
                payload = json.loads(row['payload'])
                job = payload['job']
                snapshots[job['id']] = job
            db.execute("DELETE FROM jobs")
            for job in snapshots.values():
                db.execute("INSERT INTO jobs VALUES(?,?,?)", (job['id'], job['revision'], encode(job)))
            return len(snapshots)

    def add_message(self, text, role='user', conversation='main'):
        with self.transaction() as db:
            db.execute("INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)", (conversation, role, text, time.time()))

    def events(self, after=0):
        with contextlib.closing(self.connect()) as db:
            return [dict(r) for r in db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq", (after,))]

    def controller_lease(self, owner, release=False, kernel_lock_acquired=False):
        with self.transaction() as db:
            row=db.execute('SELECT * FROM controller WHERE id=1').fetchone()
            if release:
                db.execute('DELETE FROM controller WHERE id=1 AND owner=?',(owner,))
                return
            if row and row['owner']!=owner and row['expires']>time.time() and not kernel_lock_acquired:
                raise Conflict('Another Kel engine owns this data directory')
            db.execute('INSERT INTO controller VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET owner=excluded.owner,expires=excluded.expires',
                       (owner,time.time()+120))

    def provider_outcome(self, provider, result):
        with self.transaction() as db:
            old=db.execute('SELECT data FROM providers WHERE id=?',(provider,)).fetchone()
            state=json.loads(old['data']) if old else {'failures':0,'circuit_until':0,'quota':None}
            if result.get('outcome')=='SUCCESS':
                state.update(failures=0,circuit_until=0)
            elif result.get('outcome')!='CANCELLED':
                state['failures']+=1
                error=str(result.get('error','')).lower()
                if any(s in error for s in ('401','403','authentication','not logged in')):
                    state.update(circuit_until=time.time()+86400,reason='Authentication needs repair')
                elif state['failures']>=3:
                    state.update(circuit_until=time.time()+60,reason='Repeated provider failure')
            state['observed_at']=time.time()
            if isinstance(result.get('duration'),(int,float)):
                state['latency']=result['duration'] if state.get('latency') is None else .7*state['latency']+.3*result['duration']
            if isinstance(result.get('cost_usd'),(int,float)):
                state.update(cost=result['cost_usd'] if state.get('cost') is None else .7*state['cost']+.3*result['cost_usd'],cost_basis='recent observed per-run cost',cost_is_estimate=True)
            db.execute('INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(provider,encode(state)))

    def provider_states(self):
        with contextlib.closing(self.connect()) as db:
            return {r['id']:json.loads(r['data']) for r in db.execute('SELECT * FROM providers')}

    def wait_for_route(self,job_id,reason):
        with self.transaction() as db:
            job=self._get(db,job_id)
            job.update(state='WAITING_RESOURCE',route_block=reason)
            self._save(db,job,'route.unavailable',{'reason':reason})

    def retry_route(self,job_id):
        with self.transaction() as db:
            job=self._get(db,job_id)
            if job['state']=='WAITING_RESOURCE' and job.get('route_block'):
                job.update(state='READY',route_block=None)
                self._save(db,job,'route.retry')


def aggregate(verdicts):
    if 'FAILED' in verdicts:
        return 'FAILED'
    return 'VERIFIED' if verdicts and all(v == 'VERIFIED' for v in verdicts) else 'UNCERTAIN'


def _explain(what, why, tried, nxt):
    return ('What happened: ' + what + '\n' +
            'Why: ' + why + '\n' +
            'What Kel already tried: ' + tried + '\n' +
            'What you can do next: ' + nxt)


def _route_block_reasons(route_block):
    """Turn 'No eligible route: {...}' into a readable 'name — reason' list."""
    marker = 'No eligible route:'
    if marker not in route_block:
        return route_block
    try:
        import ast
        excluded = ast.literal_eval(route_block.split(marker, 1)[1].strip())
        if isinstance(excluded, dict):
            parts = []
            for name, reasons in excluded.items():
                joined = ', '.join(map(str, reasons)) if isinstance(reasons, (list, tuple)) else str(reasons)
                parts.append(str(name) + ' — ' + joined)
            return '; '.join(parts)
    except Exception:
        pass
    return route_block


def explain_failure(job):
    """Human explanation for a job that is blocked or not fully verified.

    Reads only existing job state (route_block, milestone errors, checks,
    verdict) and never mutates routing, recovery, or completion semantics.
    Returns None when there is nothing to explain (verified, cancelled, paused,
    awaiting the user's permission, or still being prepared, which the ACP layer
    already describes).
    """
    state = job.get('state')
    verdict = job.get('verdict')
    if verdict == 'VERIFIED' or state in ('CANCELLED', 'CANCELLING', 'PAUSED', 'PAUSING', 'AWAITING_USER'):
        return None

    milestone_errors = [str(m['error']) for m in job.get('milestones', {}).values() if m.get('error')]

    if state == 'WAITING_RESOURCE':
        if milestone_errors:
            return _explain(
                'A worker stopped before this job finished.',
                milestone_errors[0],
                'Kel preserved your project copy and paused automatic retries so a partial change would not be replayed.',
                'Open Work context to review the preserved work, then retry or re-request the task.')
        if job.get('route_block'):
            return _explain(
                'No worker could start this job.',
                _route_block_reasons(job['route_block']),
                'Kel keeps re-checking in the background and will resume automatically when a worker becomes available.',
                'Wait for the worker to recover, or review provider status in Work context.')
        return _explain(
            'Kel is waiting for a worker to run this job.',
            'No failure was recorded; the job is blocked on worker availability.',
            'Kel keeps re-checking in the background and will resume automatically when a worker becomes available.',
            'Wait for the worker to recover, or review provider status in Work context.')

    # A verdict explains only a settled job: a job still being prepared carries the
    # placeholder UNCERTAIN verdict and is described by its state branch instead.
    if verdict in ('UNCERTAIN', 'FAILED') and state == 'CLOSED':
        blockers = []
        for m in job.get('milestones', {}).values():
            if m.get('error'):
                blockers.append(str(m['error']))
            for c in m.get('checks', []):
                if c.get('verdict') == 'UNCERTAIN' and c.get('reason'):
                    blockers.append(str(c['reason']))
                elif c.get('verdict') == 'FAILED':
                    blockers.append('failed check ' + str(c.get('kind')) + ': expected ' + str(c.get('expected')))
        why = blockers[0] if blockers else 'the required checks could not be confirmed.'
        if verdict == 'FAILED':
            return _explain(
                'The result did not pass its checks.',
                why,
                'Kel ran its verification checks and stopped before applying anything.',
                'Review the failed check, fix the issue, and re-request the task.')
        return _explain(
            'Kel could not fully verify the result.',
            why,
            'Kel ran its verification checks and an independent review where one was available.',
            'Provide the missing environment or evidence, then re-request the task.')

    return None


def explain_approval(summary):
    """Human explanation for a job paused at an approval gate.

    Mirrors explain_failure's four-part shape so every blocking state answers
    the same questions. Reads no job state; the caller supplies the action
    summary already shown to the user.
    """
    return _explain(
        'Kel needs your permission to continue: ' + (summary or 'a requested action') + '.',
        'This step is gated behind your explicit consent, so Kel paused the job instead of running it automatically.',
        'Kel paused the job at this gate and is holding the gated step; it has not run yet.',
        'Open \u201cWork context\u201d in the sidebar and allow or deny there. The job stays paused until you decide.')


_WORKER_NAMES = {'claude': 'Claude Code', 'claude-code': 'Claude Code',
                 'codex': 'Codex', 'codex-code': 'Codex'}


def _worker_label(provider, model=None):
    name = _WORKER_NAMES.get(provider)
    if model:
        model = str(model)
        if name:
            return name + ' (' + model + ')'
        parts = model.split('-')
        if len(parts) >= 2 and parts[0] == 'claude' and parts[1] in ('sonnet', 'opus', 'haiku'):
            return 'Claude ' + parts[1].capitalize()
        return model
    return name or provider or 'Unknown worker'


def verification_summary(job):
    """Concise trust summary for a settled job, from persisted state only.

    Reports the verdict, the evidence checks that actually ran, who executed
    and who reviewed, and any remaining limitations. Never includes worker
    text, prompts, routing details, or raw transcripts. Returns None while the
    job is unsettled or when nothing is supported by the persisted record.
    """
    verdict = job.get('verdict')
    if job.get('state') != 'CLOSED' or verdict not in ('VERIFIED', 'UNCERTAIN', 'FAILED'):
        return None
    milestones = list(job.get('milestones', {}).values())
    checks = [c for m in milestones for c in m.get('checks', []) if isinstance(c, dict)]
    lines = [{'VERIFIED': 'Verified', 'UNCERTAIN': 'Uncertain', 'FAILED': 'Failed'}[verdict]]
    repository = [c for c in checks if c.get('kind') == 'repository_evidence']
    if repository:
        lines.append('• Tests: ' + {'VERIFIED': 'passed', 'FAILED': 'failed'}.get(repository[0].get('verdict'), 'could not be confirmed'))
    research = [c for c in checks if c.get('kind') == 'research_evidence']
    if research:
        lines.append('• Sources: ' + ('citation evidence recorded' if research[0].get('verdict') == 'VERIFIED'
                                      else 'citation evidence could not be confirmed'))
    failures = [c for c in checks if c.get('verdict') == 'FAILED' and c.get('kind') != 'repository_evidence']
    if failures:
        lines.append('• Failed check: ' + str(failures[0].get('kind')) + ' (expected ' + str(failures[0].get('expected')) + ')')
    limits = []
    for c in checks:
        if c.get('verdict') == 'UNCERTAIN' and c.get('reason') and str(c['reason']) not in limits:
            limits.append(str(c['reason']))
    for m in milestones:
        if m.get('error') and str(m['error']) not in limits:
            limits.append(str(m['error']))
    for limit in limits[:2]:
        lines.append('• Limitation: ' + limit)
    executors = []
    for m in milestones:
        if m.get('provider'):
            label = _worker_label(m['provider'], m.get('model'))
            if label not in executors:
                executors.append(label)
    if executors:
        lines.append('• Executed by: ' + ', '.join(executors))
    reviewers = []
    for c in checks:
        if c.get('kind') == 'manual_review' and c.get('reviewer_provider'):
            label = _worker_label(c['reviewer_provider'], c.get('reviewer_model'))
            if label not in reviewers:
                reviewers.append(label)
    if reviewers:
        lines.append('• Reviewed by: ' + ', '.join(reviewers))
    return '\n'.join(lines) if len(lines) > 1 else None
