"""The workforce on the everyday path (D-66): staffing decisions for real work, and the record of
every model call made for it.

Design: `docs/v2/design/D-66_WORKFORCE_LIVE.md`. Nothing here is a second workflow engine: the
decision is frozen into the job's own contract (`contract['staffing']`), each step's binding rides
the job's own run (`staff_calls.id` = the run id, written in the claim transaction), and the review
and Oracle calls run on the engine's existing review pool. With the off-switch
(`KEL_WORKFORCE=0|false|off|no`) no contract carries a staffing record and every caller takes the
branch it took before.

Kel is the Commander and is never spawned; the roles below are spawned per step, and the same role
may have several live instances.
"""
import contextlib
import json
import os
import re
import time

from .core import PolicyError, encode, uid

MIGRATION_VERSION = 36  # 35 is General's default folder (projects.GENERAL_FOLDER_VERSION)
MIGRATION_NAME = 'v2-workforce-live'

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
  version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS staff_calls(
  id TEXT PRIMARY KEY, job_id TEXT NOT NULL, milestone_id TEXT, role TEXT NOT NULL,
  instance INTEGER NOT NULL DEFAULT 1, kind TEXT NOT NULL, subject TEXT, state TEXT NOT NULL,
  asked TEXT, ran TEXT, why TEXT, summary TEXT, started REAL NOT NULL, finished REAL);
CREATE INDEX IF NOT EXISTS staff_calls_by_job ON staff_calls(job_id, started);
CREATE TABLE IF NOT EXISTS role_models(
  role TEXT PRIMARY KEY, mode TEXT NOT NULL, model TEXT, reasoning TEXT NOT NULL DEFAULT 'auto',
  updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS staff_model_status(
  model TEXT PRIMARY KEY, status TEXT NOT NULL, reason TEXT, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS office_dismissals(
  job_id TEXT PRIMARY KEY, at REAL NOT NULL, actor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS oracle_reviews(
  job_id TEXT NOT NULL, subject TEXT NOT NULL, attempts INTEGER NOT NULL, status TEXT NOT NULL,
  detail TEXT, updated REAL NOT NULL, PRIMARY KEY(job_id, subject));
"""

# Plain role names (D-66: no jargon). 'kel' is the Commander — Kel itself, never a template.
ROLE_LABELS = {'kel': 'Kel', 'discovery': 'Discovery', 'architect': 'Architect',
               'designer': 'Designer', 'builder': 'Builder', 'verifier': 'Verifier',
               'sentinel': 'Sentinel', 'release': 'Release', 'oracle': 'Oracle',
               'utility': 'Utility', 'red_team': 'Red Team'}
REVIEW_ROLES = ('verifier', 'oracle', 'sentinel')
# The authority template a step's executor runs under (the V1.5 frozen role snapshot). Utility is
# the Builder's fast tier (charter doc 04); Kel's own work keeps the legacy per-kind template.
EXECUTOR_TEMPLATES = {'builder': 'builder', 'utility': 'builder', 'discovery': 'discovery',
                      'designer': 'designer', 'architect': 'architect'}
LEGACY_TEMPLATES = {'coding': 'implementation-engineer', 'research': 'research-specialist'}

# `sentinel` and `red_team` are the other independent review passes (kel/oracle.py); like `check`
# and `oracle` they are review calls a killed engine leaves `stopped`.
CALL_KINDS = ('work', 'check', 'oracle', 'plan', 'sentinel', 'red_team')
REVIEW_KINDS = ('check', 'oracle', 'sentinel', 'red_team')
CALL_STATES = ('running', 'done', 'failed', 'stopped', 'waiting')

OFF_VALUES = ('0', 'false', 'off', 'no')


def enabled(env=None):
    """D-66: the workforce is on by default; `KEL_WORKFORCE=0|false|off|no` turns it off."""
    env = os.environ if env is None else env
    return str(env.get('KEL_WORKFORCE', '')).strip().lower() not in OFF_VALUES


def ensure_schema(store):
    """Migration 36 (additive, idempotent; no existing table is touched). The workforce ledgers it
    writes into (findings, evidence) are ensured too, so a bare engine store can run staffed work."""
    from .workforce import ensure_schema as ensure_workforce_schema
    ensure_workforce_schema(store)
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)
        # Routing 2 (live check): a refusal keeps its kind and the runtime version that refused it.
        columns = {row[1] for row in db.execute('PRAGMA table_info(staff_model_status)')}
        for name in ('kind', 'runtime_version'):
            if name not in columns:
                db.execute('ALTER TABLE staff_model_status ADD COLUMN %s TEXT' % name)
        if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                          (MIGRATION_VERSION,)).fetchone():
            db.execute('INSERT OR IGNORE INTO schema_migrations(version,name,applied,note) '
                       'VALUES(?,?,?,?)', (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                                           'staff calls, role models, Oracle reviews, removed work cards (D-66..D-68)'))
    return True


def _has_table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                      (name,)).fetchone() is not None


# ---- the feature vector (doc 05 §2), computed deterministically ------------------------------

def _rx(*words):
    return re.compile(r'\b(?:' + '|'.join(words) + r')\b', re.IGNORECASE)


# A positive scope signal is never negated by context (doc 05 §2: fail-safe toward more care).
FLAG_PATTERNS = {
    'security_boundary': _rx(r'passwords?', r'credentials?', r'secrets?', r'api[ -]?keys?', r'tokens?',
                             r'auth', r'authentication', r'authori[sz]ation', r'log ?in', r'sign[- ]?in',
                             r'permissions?', r'oauth', r'encrypt\w*', r'vulnerab\w*', r'security',
                             r'firewall', r'csrf', r'xss', r'injection'),
    'release': _rx(r'deploy\w*', r'release', r'ship (?:it|this|to)', r'production', r'go live'),
    'irreversible': _rx(r'send (?:an? |the )?(?:email|message|invoice|newsletter)', r'email (?:it|them|the)',
                        r'publish\w*', r'post (?:it|this|to)', r'tweet', r'pay', r'payment', r'charge',
                        r'transfer (?:money|funds)', r'purchase', r'refund'),
    'data_migration': _rx(r'migrat\w*', r'schema', r'database', r'sql', r'backfill', r'drop (?:the )?table',
                          r'truncate', r'wipe', r'erase',
                          r'delete (?:all |the |every )?(?:data|records|rows|users|accounts|files)'),
    'new_dependency': _rx(r'install', r'npm install', r'pip install',
                          r'(?:add|new) (?:a |the )?(?:dependency|package|library)'),
    # Sentinel's privacy class (handoff §16). Narrow phrases only; like every flag it never raises the
    # scoping size (FN-07) — it records the class and, for a code change, brings Sentinel's review.
    'privacy': _rx(r'privacy', r'personal (?:data|information|details)', r'pii',
                   r'personally identifiable', r'gdpr', r'telemetry'),
}
USER_FACING = _rx(r'ui', r'ux', r'screens?', r'pages?', r'buttons?', r'layout', r'design\w*', r'css',
                  r'styles?(?:heet)?', r'dialogs?', r'modals?', r'menus?', r'forms?', r'front-?end',
                  r'website', r'landing page', r'mock-?ups?', r'wireframes?', r'icons?', r'themes?',
                  r'dark mode')
MECHANICAL = _rx(r'format', r'reformat', r'convert', r'rename', r'translate', r'tidy', r'clean up',
                 r'proofread', r'spell ?check', r'sort', r'extract', r'list')
UNCERTAIN = _rx(r'figure out', r'investigate', r'explore', r'why', r'compare', r'evaluate',
                r'which is best', r'options')
BROAD = _rx(r'architecture', r'across', r'entire', r'whole', r'system', r'every', r'all of')
FEATURE_WORK = _rx(r'feature', r'refactor\w*', r'implement\w*', r'integrat\w*', r'redesign')


def kind_of(contract):
    """'code' | 'research' | 'recipe' | 'writing' — the plain kind of a work contract."""
    if contract.get('kind') == 'coding':
        return 'code'
    if contract.get('kind') == 'research' or 'web_research' in (contract.get('required_capabilities') or []):
        return 'research'
    if str(contract.get('compiler') or '').startswith('recipe') or contract.get('recipe'):
        return 'recipe'
    return 'writing'


def _parts(contract):
    """(independent parts, combine step id) for a plan whose parts do not depend on each other."""
    milestones = contract.get('milestones') or []
    final = contract.get('final_milestone')
    parts = [m for m in milestones if m.get('id') != final and not m.get('depends_on')]
    others = [m for m in milestones if m.get('id') != final and m.get('depends_on')]
    if others:
        return [], None  # a dependency chain between parts: sequential, not parallel
    return parts, final


def flags_for(text):
    return sorted(flag for flag, pattern in FLAG_PATTERNS.items() if pattern.search(text or ''))


def features_for(contract, request=None):
    """The doc-05 feature vector for one compiled contract (deterministic; recorded with reasons)."""
    text = str(request or contract.get('request') or '')
    words = len(text.split())
    kind = kind_of(contract)
    milestones = contract.get('milestones') or []
    parts, final = _parts(contract)
    flags = flags_for(text)
    user_facing = 1 if USER_FACING.search(text) else 0
    if kind == 'code':
        complexity = 1 + (1 if (words > 60 or FEATURE_WORK.search(text)) else 0) + \
            (1 if (words > 200 or BROAD.search(text)) else 0)
        sequentiality = 2  # one project copy: order-dependent state
        decomposability = 0
        tools = 2
        consequence = 1  # applied to Nick's folder in Full access (undoable)
        novelty = 2 if contract.get('greenfield') else 0
        breadth = 2 if user_facing else (1 if FEATURE_WORK.search(text) else 0)
    else:
        complexity = 0 if (words <= 30 and len(milestones) == 1) else 1
        if len(milestones) >= 3 or words > 150:
            complexity = 2
        if words > 400:
            complexity = 3
        if len(parts) >= 2 and final:
            decomposability = 3 if len(parts) >= 3 else 2
            sequentiality = 0
        else:
            decomposability = 0
            sequentiality = 1 if len(milestones) == 1 else 2
        tools = 1 if kind == 'research' else 0
        consequence = 0
        novelty = 1 if kind == 'research' else 0
        breadth = min(3, len(parts)) if decomposability else (1 if kind == 'research' else 0)
    uncertainty = 2 if kind == 'research' else (1 if UNCERTAIN.search(text) else 0)
    risky = [f for f in flags if f in ('security_boundary', 'irreversible', 'data_migration')]
    risk = 0 if not risky else (3 if len(risky) >= 2 else 2)
    if 'irreversible' in flags:
        consequence = 3
    elif 'release' in flags or 'data_migration' in flags:
        consequence = max(consequence, 2)
    features = {'complexity': min(3, complexity), 'decomposability': decomposability,
                'sequentiality': sequentiality, 'uncertainty': uncertainty, 'novelty': novelty,
                'risk': risk, 'domain_breadth': breadth, 'tool_requirements': tools,
                'consequence_of_failure': consequence, 'user_facing': user_facing,
                'release_proximity': 2 if 'release' in flags else 0}
    return features, flags


# ---- the staffing decision -------------------------------------------------------------------

REVIEW_LENSES = {'code': ('functional-testing', 'maintainability'),
                 'writing': ('requirements-coverage',), 'research': ('requirements-coverage',),
                 'recipe': ('requirements-coverage',)}
FLAG_LENSES = {'security_boundary': 'security', 'data_migration': 'data-integrity',
               'release': 'release-integrity'}
ORACLE_FLAGS = ('security_boundary', 'irreversible', 'release', 'data_migration')
# Sentinel (handoff §16): security, privacy, data integrity, migration risk — the flag and the lens
# Sentinel reviews it through (never-gate lenses, workforce-os doc 08 §6).
SENTINEL_FLAGS = {'security_boundary': 'security', 'privacy': 'privacy', 'data_migration': 'data-integrity'}
TIER_RANK = {'D0': 0, 'D1': 1, 'D2': 2, 'D3': 3, 'D4': 4}


def _role_for_step(kind, milestone, tier, user_facing, text, final_id, hint=None):
    if kind == 'code':
        return 'builder'
    if final_id and milestone.get('id') == final_id:
        return 'kel'  # the Commander combines the parts into one answer (announce-chain synthesis)
    if 'web_research' in (milestone.get('required_capabilities') or []) or kind == 'research':
        return 'discovery'
    if tier == 'D0':
        return 'kel'
    # Routing 2 §5.5: the turn model's class, when it gave one, decides design / utility / writing;
    # the word lists below are the fallback reading.
    if hint == 'design':
        return 'designer'
    if hint == 'utility' and TIER_RANK[tier] <= 1:
        return 'utility'
    if hint == 'writing':
        return 'builder'
    if user_facing:
        return 'designer'
    if MECHANICAL.search(text) and TIER_RANK[tier] <= 1:
        return 'utility'
    return 'builder'


def plan_job(store, contract, request=None, *, tier_max=None):
    """The recorded staffing decision for one real-work contract (frozen into the contract).

    Deterministic: the feature vector, `staffing.resolve` (R1–R10, tier_max, one-step history
    advice), then Kel's own application rules — each recorded as a plain reason.
    """
    from . import staffing
    from .parallel import plan_streams
    text = str(request or contract.get('request') or '')
    kind = kind_of(contract)
    features, flags = features_for(contract, text)
    decision = staffing.resolve(store, features, flags=tuple(flags), tier_max=tier_max)
    tier = decision['tier']
    reasons = list(decision['reasons'])
    if kind == 'code' and TIER_RANK[tier] < 1:
        tier = 'D1'
        reasons.append('code is always written by a Builder (at least one specialist)')
    parts, final = _parts(contract)
    parallel = None
    if kind == 'code' and tier in ('D3', 'D4'):
        reasons.append('the coding runtime keeps one project copy per job, so code runs as a pod, '
                       'not parallel streams')
    elif kind != 'code' and len(parts) >= 2 and final and TIER_RANK[tier] >= 2 \
            and features['decomposability'] >= 2 and features['sequentiality'] <= 1:
        try:
            parallel = plan_streams({
                'streams': [{'name': p['id'], 'objective': str(p.get('objective') or '')[:200],
                             'write_paths': [p.get('filename') or (p['id'] + '.md')]}
                            for p in parts],
                'merge_strategy': 'Kel combines the checked parts in step %s' % final})
            if tier == 'D2':
                reasons.append('%d independent parts with separate outputs run at the same time '
                               '(decomposability %d, sequentiality %d; doc 05 E4)'
                               % (len(parts), features['decomposability'], features['sequentiality']))
                tier = 'D3'
        except PolicyError as exc:
            reasons.append('parts are not run in parallel: %s' % exc)
            parallel = None
    if tier in ('D3', 'D4') and parallel is None and kind != 'code':
        reasons.append('no independent parts to run in parallel; the steps run one at a time')
    user_facing = bool(features['user_facing'])
    steps = {}
    from .task_routing import class_for_role, tier_for_step
    hint = (contract.get('classification') or {}).get('tier')
    for milestone in contract.get('milestones') or []:
        role = _role_for_step(kind, milestone, tier, user_facing, text, final if parallel else None,
                              (contract.get('classification') or {}).get('task_class'))
        # Routing 2 §5.1: the step's task class and dispatch tier, frozen with the decision.
        step_kind = 'research' if 'web_research' in (milestone.get('required_capabilities') or []) else kind
        task_class = class_for_role(role, step_kind)
        dispatch, dispatch_why = tier_for_step(task_class, {'features': features, 'flags': flags,
                                                            'tier': tier}, hint)
        steps[milestone['id']] = {'role': role, 'label': ROLE_LABELS[role], 'task_class': task_class,
                                  'dispatch': dispatch, 'dispatch_why': dispatch_why}
    from .budget import CEILINGS, class_for
    budget_class = class_for(tier, flags, features)
    reasons.append('budget class %s' % budget_class)
    pod = TIER_RANK[tier] >= 2
    lenses = list(REVIEW_LENSES[kind]) if pod else []
    for flag in flags:
        lens = FLAG_LENSES.get(flag)
        if pod and lens and lens not in lenses:
            lenses.append(lens)
    oracle_why = []
    if tier == 'D4':
        oracle_why.append('high-assurance work always gets an independent second opinion')
    elif pod:
        hit = [flag for flag in flags if flag in ORACLE_FLAGS]
        if hit:
            oracle_why.append('consequential work (%s)' % ', '.join(f.replace('_', ' ') for f in hit))
    sentinel = sentinel_decision(kind, tier, flags)
    red_team = red_team_decision(kind, tier, flags)
    return {'schema': 1, 'decided_at': time.time(), 'kind': kind, 'tier': tier,
            'decided_tier': decision['tier'], 'score': decision['score'],
            'rules': [item['id'] for item in decision['rules_fired']], 'reasons': reasons,
            'advice': decision.get('advice'), 'features': features, 'flags': flags,
            # Routing 2 §5.4: the budget class (and its ceilings) the governor holds this job to.
            'budget_class': budget_class, 'budget': {'class': budget_class, 'ceilings': CEILINGS[budget_class]},
            'steps': steps,
            'parallel': parallel, 'serial': parallel is None,
            'review': {'mode': 'pod' if pod else 'check', 'lenses': lenses},
            'oracle': {'required': bool(oracle_why), 'why': oracle_why},
            'sentinel': sentinel, 'red_team': red_team,
            'caps': {'workers_max': staffing.CAPS['workers_max'], 'engine_concurrency': 2}}


def sentinel_decision(kind, tier, flags):
    """Whether Sentinel reviews this work (recorded with reasons, frozen with the decision).

    Sentinel runs when the work can actually cause security, privacy or data harm: a code change
    carrying one of its flags, or high-assurance (D4) work carrying one. A flag on writing or
    research below D4 — a note that explains what an API token is — is a mention, not an exposure
    (FN-07: a word alone is not a reason for more ceremony); the Verifier's lens still covers it at
    D2, and the non-activation is recorded with its reason (charter 11).
    """
    hit = [flag for flag in flags if flag in SENTINEL_FLAGS]
    lenses = [SENTINEL_FLAGS[flag] for flag in hit]
    words = ', '.join(flag.replace('_boundary', '').replace('_', ' ') for flag in hit)
    if hit and (kind == 'code' or tier == 'D4'):
        why = ['a code change touching %s' % words] if kind == 'code' else [
            'high-assurance work touching %s' % words]
        return {'required': True, 'why': why, 'lenses': lenses}
    not_needed = ('the request mentions %s, but it changes no code, so there is nothing for Sentinel '
                  'to check' % words) if hit else None
    return {'required': False, 'why': [], 'lenses': lenses, 'not_needed': not_needed}


def red_team_decision(kind, tier, flags):
    """Whether the Red Team (Independent Assurance mode B) attacks the accepted result.

    Only when justified: high-assurance (D4) work always; a security-flagged code change only when
    the verified diff is larger than the size trigger (measured after the change is checked).
    """
    from .oracle import RED_TEAM_FILES, RED_TEAM_LINES
    why = ['high-assurance work is attacked once it is accepted'] if tier == 'D4' else []
    size = ({'files': RED_TEAM_FILES, 'lines': RED_TEAM_LINES}
            if kind == 'code' and 'security_boundary' in flags else None)
    return {'required': bool(why), 'why': why, 'size_trigger': size}


def staffing_of(job):
    """The frozen staffing record of a job, or None (an unstaffed job runs exactly as before)."""
    value = (job.get('contract') or {}).get('staffing')
    return value if isinstance(value, dict) and value.get('schema') == 1 else None


def step_role(job, milestone_id):
    record = staffing_of(job)
    if not record:
        return None
    return ((record.get('steps') or {}).get(milestone_id) or {}).get('role')


def step_routing(job, milestone_id):
    """(task class, dispatch tier) of a staffed step (Routing 2 §5.1); derived for decisions made
    before steps carried them; (None, None) for unstaffed work (routing as before)."""
    record = staffing_of(job)
    if not record:
        return None, None
    step = (record.get('steps') or {}).get(milestone_id) or {}
    if step.get('task_class') and step.get('dispatch'):
        return step['task_class'], step['dispatch']
    if not step.get('role'):
        return None, None
    from .task_routing import class_for_role, tier_for_step
    task_class = class_for_role(step['role'], record.get('kind'))
    return task_class, tier_for_step(task_class, record)[0]


def record_decision(store, job_id, record):
    """One job-scoped `staffing.decided` event (the V2-12 history reads it)."""
    from .team import Team
    Team(store)  # ensures the team tables exist
    detail = {'scope': 'job', 'tier': record['tier'], 'score': record['score'],
              'rules': record['rules'], 'reasons': record['reasons'][:12],
              'budget_class': record['budget_class'], 'kind': record['kind'],
              'roles': sorted({step['role'] for step in record['steps'].values()}),
              'advice': record.get('advice')}
    with store.transaction() as db:
        if db.execute("SELECT 1 FROM team_events WHERE kind='staffing.decided' AND job_id=? "
                      "AND assignment_id IS NULL", (job_id,)).fetchone():
            return False
        db.execute('INSERT INTO team_events(at,kind,actor,assignment_id,job_id,milestone_id,run_id,'
                   'refs,detail) VALUES(?,?,?,?,?,?,?,?,?)',
                   (time.time(), 'staffing.decided', 'kel', None, job_id, None, None, None,
                    encode(detail)))
    return True


def executor_template(job, milestone_id):
    """The authority template for a step's executor (roles only narrow; V1.5 G3)."""
    role = step_role(job, milestone_id)
    if role in EXECUTOR_TEMPLATES:
        return EXECUTOR_TEMPLATES[role]
    return LEGACY_TEMPLATES.get((job.get('contract') or {}).get('kind'), 'documentation-specialist')


def may_start(job, milestone_id):
    """Below D3 a staffed job runs one step at a time; D3 runs its independent parts together."""
    record = staffing_of(job)
    if not record or not record.get('serial'):
        return True
    return not any(m.get('state') == 'RUNNING' for mid, m in (job.get('milestones') or {}).items()
                   if mid != milestone_id)


# ---- the record of every staffed model call ---------------------------------------------------

def next_instance(db, job_id, role):
    row = db.execute('SELECT MAX(instance) AS n FROM staff_calls WHERE job_id=? AND role=?',
                     (job_id, role)).fetchone()
    return int(row['n'] or 0) + 1


def insert_call(db, *, call_id, job_id, milestone_id, role, kind, asked=None, ran=None, why=None,
                subject=None, state='running', summary=None, started=None):
    """Write one staff call inside the caller's transaction (claim, review start, Oracle start)."""
    if kind not in CALL_KINDS or state not in CALL_STATES:
        raise PolicyError('Unknown staff call kind or state')
    if not _has_table(db, 'staff_calls'):
        return None
    if db.execute('SELECT 1 FROM staff_calls WHERE id=?', (call_id,)).fetchone():
        return call_id
    db.execute('INSERT INTO staff_calls(id,job_id,milestone_id,role,instance,kind,subject,state,asked,'
               'ran,why,summary,started,finished) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)',
               (call_id, job_id, milestone_id, role, next_instance(db, job_id, role), kind, subject,
                state, encode(asked or {}), encode(ran or {}), why, summary,
                time.time() if started is None else started))
    return call_id


def start_call(store, **fields):
    fields.setdefault('call_id', uid())
    with store.transaction() as db:
        return insert_call(db, **fields)


def update_call(store, call_id, *, state=None, ran=None, why=None, summary=None, db=None):
    """Settle or enrich a staff call; `ran` merges into what is recorded (never erases it)."""
    def _apply(conn):
        if not _has_table(conn, 'staff_calls'):
            return False
        row = conn.execute('SELECT ran, why FROM staff_calls WHERE id=?', (call_id,)).fetchone()
        if row is None:
            return False
        merged = json.loads(row['ran'] or '{}')
        if ran:
            merged.update({k: v for k, v in ran.items() if v is not None})
        sets, args = ['ran=?'], [encode(merged)]
        if state is not None:
            if state not in CALL_STATES:
                raise PolicyError('Unknown staff call state')
            sets.append('state=?')
            args.append(state)
            if state != 'running':
                sets.append('finished=?')
                args.append(time.time())
        if why is not None:
            sets.append('why=?')
            args.append(why)
        if summary is not None:
            sets.append('summary=?')
            args.append(str(summary)[:300])
        conn.execute('UPDATE staff_calls SET %s WHERE id=?' % ', '.join(sets), args + [call_id])
        return True
    if db is not None:
        return _apply(db)
    with store.transaction() as conn:
        return _apply(conn)


def binding_for_run(store, run_id):
    """What a staffed run was asked to run on (model/fallback/effort flags); {} when unstaffed."""
    with contextlib.closing(store.connect()) as db:
        if not _has_table(db, 'staff_calls'):
            return {}
        row = db.execute('SELECT asked FROM staff_calls WHERE id=?', (run_id,)).fetchone()
    if not row:
        return {}
    try:
        asked = json.loads(row['asked'] or '{}')
    except (TypeError, ValueError):
        return {}
    return {key: asked.get(key) for key in ('model_arg', 'fallback_arg', 'effort_arg', 'model',
                                            'reasoning', 'role')}


def refusal_summary(db, call_id, error):
    """"<Model> can't run here: <plain reason>" when a staff call failed because its runtime refused
    the model (what the card shows), else None."""
    if not error or not _has_table(db, 'staff_calls'):
        return None
    row = db.execute('SELECT asked FROM staff_calls WHERE id=?', (call_id,)).fetchone()
    try:
        asked = json.loads(row['asked'] or '{}') if row else {}
    except (TypeError, ValueError):
        return None
    model = asked.get('resolved') or (asked.get('model') if asked.get('model_arg') else None)
    from .role_models import MODELS, classify_refusal
    found = classify_refusal(error, model) if model else None
    if not found:
        return None
    return "%s can't run here: %s" % ((MODELS.get(model) or {}).get('label', model), found[1])


def note_rejection(db, call_id, error):
    """A runtime that refused the model a staff call ran on: remember it with the plain reason
    (`role_models.note_refusal`) so the next step, review or plan falls back at once."""
    if not error or not _has_table(db, 'staff_model_status'):
        return False
    row = db.execute('SELECT asked, ran FROM staff_calls WHERE id=?', (call_id,)).fetchone()
    try:
        asked = json.loads(row['asked'] or '{}') if row else {}
        ran = json.loads(row['ran'] or '{}') if row else {}
    except (TypeError, ValueError):
        asked, ran = {}, {}
    # The model that was actually sent to the runtime (a fallback may differ from the role's pick).
    model = asked.get('resolved') or (asked.get('model') if asked.get('model_arg') else None)
    if not model:
        return False
    from .role_models import note_refusal
    return note_refusal(None, model, error, ran.get('runtime_version'), db=db)


def calls(store, job_id):
    with contextlib.closing(store.connect()) as db:
        if not _has_table(db, 'staff_calls'):
            return []
        rows = [dict(r) for r in db.execute('SELECT * FROM staff_calls WHERE job_id=? ORDER BY started',
                                            (job_id,))]
    for row in rows:
        row['asked'] = json.loads(row['asked'] or '{}')
        row['ran'] = json.loads(row['ran'] or '{}')
    return rows


def settle_interrupted(store):
    """At engine start: review calls (Verifier, Sentinel, Oracle, Red Team) a killed engine left
    running are stopped (work calls follow their run's own state, which V2-11 recovery owns)."""
    with store.transaction() as db:
        if not _has_table(db, 'staff_calls'):
            return 0
        return db.execute("UPDATE staff_calls SET state='stopped', finished=? WHERE state='running' "
                          "AND kind IN (%s)" % ','.join('?' * len(REVIEW_KINDS)),
                          (time.time(),) + REVIEW_KINDS).rowcount
