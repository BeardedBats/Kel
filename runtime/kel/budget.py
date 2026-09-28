"""The budget governor (Routing 2 §5.4, workforce-os doc 10 §5, doc 05 §6).

Every staffed job has a budget class — tiny | standard | deep | high-assurance — frozen with its
staffing decision, each with ceilings on processed tokens, run time and (API-equivalent) cost. Before
a staffed step is claimed the engine estimates the step plus its review (measured medians for that
task class and model, else the class defaults below), checks what the job has measurably used plus
its open reservations plus the estimate against each ceiling, and reserves the estimate in the claim
transaction (`budget_reservations`, reservation id = run id). The measured usage settles it.

Exhaustion stops the job before its next step with a plain reason ("Budget reached: …") and marks it
Needs you. It is never retried on its own and never continued on a cheaper model; reviews of work
already done and the Oracle always run on their assured model (their share was reserved with the
step). Nick raises the class (`raise_class`, one Activity line) or stops the work.

The ceilings are starting values until Nick sets his own (ROUTING_2.md "Needs Nick").
"""
import contextlib
import time

from .core import PolicyError

ORDER = ('tiny', 'standard', 'deep', 'high-assurance')
LABELS = {'tiny': 'tiny', 'standard': 'standard', 'deep': 'deep', 'high-assurance': 'high-assurance'}
CEILINGS = {
    'tiny': {'tokens': 300_000, 'minutes': 20, 'cost': 2.0},
    'standard': {'tokens': 3_000_000, 'minutes': 90, 'cost': 10.0},
    'deep': {'tokens': 8_000_000, 'minutes': 240, 'cost': 30.0},
    'high-assurance': {'tokens': 15_000_000, 'minutes': 480, 'cost': 60.0},
}
# What one step is expected to use when nothing has been measured for its class and model yet
# (processed tokens, run time in ms, API-equivalent cost). Deliberately modest: a step is only
# stopped by what was actually measured plus a reasonable next step.
STEP_DEFAULTS = {'coding': (250_000, 8 * 60_000, 1.50), 'research': (60_000, 3 * 60_000, 0.40),
                 'design': (60_000, 3 * 60_000, 0.60), 'writing': (40_000, 2 * 60_000, 0.30),
                 'utility': (20_000, 60_000, 0.05), 'planning': (20_000, 60_000, 0.10),
                 'quick_answer': (10_000, 30_000, 0.05), 'review': (60_000, 3 * 60_000, 0.60)}
BUDGET_WAIT = 'Budget reached: '
RISK_FLAGS = ('security_boundary', 'irreversible', 'release', 'data_migration')

DDL = ("CREATE TABLE IF NOT EXISTS job_budgets(job_id TEXT PRIMARY KEY, budget_class TEXT NOT NULL, "
       "raised_at REAL NOT NULL, actor TEXT NOT NULL)")


def class_for(tier, flags=(), features=None):
    """The budget class a staffing decision starts with (doc 05 §6)."""
    features = features or {}
    if tier == 'D4' or any(flag in RISK_FLAGS for flag in flags or ()):
        return 'high-assurance'
    if tier == 'D3' or (tier == 'D2' and (features.get('complexity') or 0) >= 2):
        return 'deep'
    if tier == 'D0':
        return 'tiny'
    return 'standard'


def _ensure(db):
    db.execute(DDL)


def job_class(store, job):
    """The job's current class: raised by Nick, else frozen with its staffing, else standard."""
    from .staff import staffing_of
    with contextlib.closing(store.connect()) as db:
        _ensure(db)
        row = db.execute('SELECT budget_class FROM job_budgets WHERE job_id=?', (job['id'],)).fetchone()
    if row and row['budget_class'] in ORDER:
        return row['budget_class']
    record = staffing_of(job) or {}
    chosen = (record.get('budget') or {}).get('class') or record.get('budget_class')
    return chosen if chosen in ORDER else 'standard'


def _measured_step(store, task_class, model):
    try:
        from .usage import model_stats
        stats = model_stats(store, task_class=task_class).get(model) or {}
    except Exception:
        stats = {}
    base = STEP_DEFAULTS.get(task_class, STEP_DEFAULTS['writing'])
    tokens = stats.get('avg_processed') if stats.get('avg_processed') is not None else base[0]
    ms = stats.get('median_ms') if stats.get('median_ms') is not None else base[1]
    cost = stats.get('avg_cost') if stats.get('avg_cost') is not None else base[2]
    return int(tokens), int(ms), float(cost), bool(stats)


def estimate(store, task_class, model=None, reviewed=True):
    """{'tokens','ms','cost','measured'} for one step (plus its review when it has one)."""
    tokens, ms, cost, measured = _measured_step(store, task_class or 'writing', model)
    if reviewed:
        r_tokens, r_ms, r_cost, _ = _measured_step(store, 'review', None)
        tokens, ms, cost = tokens + r_tokens, ms + r_ms, cost + r_cost
    return {'tokens': tokens, 'ms': ms, 'cost': round(cost, 4), 'measured': measured}


def spent(store, job_id):
    """What the job has measurably used, and what its running steps still hold in reserve."""
    from .usage import job_spend
    used = job_spend(store, job_id)
    held = {'tokens': 0, 'ms': 0, 'cost': 0.0}
    with contextlib.closing(store.connect()) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='budget_reservations'").fetchone():
            for row in db.execute(
                    "SELECT r.tokens, r.wallclock, r.cost FROM budget_reservations r JOIN runs u "
                    "ON u.id=r.reservation_id WHERE r.job_id=? AND r.state='reserved' "
                    "AND u.state IN ('RUNNING','WAITING_APPROVAL','CANCEL_REQUESTED')", (job_id,)):
                held['tokens'] += int(row['tokens'] or 0)
                held['ms'] += int(row['wallclock'] or 0)
                held['cost'] += float(row['cost'] or 0)
    return {'tokens': int(used['processed'] or 0), 'ms': int(used['wall_ms'] or 0),
            'cost': float(used['cost_usd'] or 0), 'held': held, 'calls': used['calls']}


def _tokens(value):
    return ('%.1fM' % (value / 1e6)) if value >= 1e6 else ('%dk' % round(value / 1e3))


def check(store, job, step):
    """None when the step fits the job's budget, else the plain reason it does not."""
    cls = job_class(store, job)
    ceiling = CEILINGS[cls]
    used = spent(store, job['id'])
    over = []
    if used['tokens'] + used['held']['tokens'] + step['tokens'] > ceiling['tokens']:
        over.append('about %s of its %s tokens' % (_tokens(used['tokens']), _tokens(ceiling['tokens'])))
    if used['ms'] + used['held']['ms'] + step['ms'] > ceiling['minutes'] * 60_000:
        over.append('about %d of its %d minutes of run time' % (round(used['ms'] / 60_000), ceiling['minutes']))
    if used['cost'] + used['held']['cost'] + step['cost'] > ceiling['cost']:
        over.append('about $%.2f of its $%.0f' % (used['cost'], ceiling['cost']))
    if not over:
        return None
    return ('this work has used %s (%s budget), so Kel stopped before the next step rather than '
            'continue on a cheaper model. Raise its budget to continue, or stop it.'
            % (' and '.join(over), LABELS[cls]))


def reserve(db, *, job_id, run_id, milestone_id, budget_class, step, note=None):
    """The reservation for one claimed step, written in the claim transaction."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='budget_reservations'").fetchone():
        from .assignment import DDL as RESERVATIONS
        for statement in [part.strip() for part in RESERVATIONS.split(';') if part.strip()]:
            db.execute(statement)
    now = time.time()
    db.execute('INSERT OR IGNORE INTO budget_reservations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
               (run_id, job_id, milestone_id, None, budget_class, max(1, int(step['tokens'])),
                max(1, int(step['ms'])), float(step['cost']), 'reserved', note, now, now))


def settle(db, run_id, consumed=True):
    """The run's measured usage replaced its reservation (consumed), or it never ran (released)."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='budget_reservations'").fetchone():
        return
    db.execute("UPDATE budget_reservations SET state=?, updated=? WHERE reservation_id=? AND state='reserved'",
               ('consumed' if consumed else 'released', time.time(), run_id))


def raise_class(store, job_id, actor='user'):
    """Nick raises a job's budget one class and lets it continue (never done on Kel's own)."""
    try:
        job = store.get(job_id)
    except KeyError:
        raise PolicyError('Kel could not find that work.') from None
    current = job_class(store, job)
    index = ORDER.index(current)
    if index + 1 >= len(ORDER):
        raise PolicyError('This work already has the largest budget (high-assurance).')
    raised = ORDER[index + 1]
    with store.transaction() as db:
        _ensure(db)
        db.execute('INSERT INTO job_budgets(job_id,budget_class,raised_at,actor) VALUES(?,?,?,?) '
                   'ON CONFLICT(job_id) DO UPDATE SET budget_class=excluded.budget_class, '
                   'raised_at=excluded.raised_at, actor=excluded.actor', (job_id, raised, time.time(), actor))
        record = store._get(db, job_id)
        store._save(db, record, 'budget.raised', {'from': current, 'to': raised, 'actor': actor})
    current_job = store.get(job_id)
    if current_job['state'] == 'WAITING_RESOURCE' and str(current_job.get('route_block') or '').startswith(BUDGET_WAIT):
        store.retry_route(job_id)
    return {'job_id': job_id, 'from': current, 'to': raised, 'ceilings': CEILINGS[raised]}


def view(store, job):
    """The job's budget in plain numbers (for the work detail): class, ceilings, used, held."""
    cls = job_class(store, job)
    used = spent(store, job['id'])
    return {'class': cls, 'ceilings': CEILINGS[cls], 'used': {k: used[k] for k in ('tokens', 'ms', 'cost')},
            'held': used['held']}
