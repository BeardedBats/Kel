"""Routing evidence (V2-09): durable outcomes, decayed, with small samples kept honest.

One store — the `routing_outcomes` table V1.5 already writes. This module only *reads and writes it
well*: a richer fact row per run (model, observed span, when, which source, reviewer provenance,
approximate cost), a decayed score with a floor, and plain-words summaries. Nothing here chooses a
provider: `kel.router.select` does, and it takes the evidence as data so the choice stays
deterministic, reviewable and testable.

The rules the rest of the system relies on:

- **Decay**: an outcome's influence halves every `HALF_LIFE_DAYS`. A provider that failed last month
  is not punished today, and one that failed an hour ago weighs fully.
- **A floor**: below `MIN_WEIGHT` of recent evidence there is no rate at all (`verified_rate is
  None`) — small samples never overrule the safe cost/health defaults.
- **Sources**: an inferred failure (`source='milestone'`) may be refined by a reviewed verdict
  (`source='review'`); a review record is never overwritten by an inferred one.
- **No payloads**: only outcome facts live here — never a prompt, an answer, a path or a credential.
"""
import contextlib
import time

DAY = 86400.0
WINDOW_DAYS = 30.0
HALF_LIFE_DAYS = 7.0
# Decayed weight a provider needs before a rate is reported at all (roughly three fresh runs).
MIN_WEIGHT = 3.0
# A provider whose decayed verified rate sits below this steps aside for other eligible models.
DEMOTION_RATE = 0.5

COLUMNS = (('model', 'TEXT'), ('ms', 'INTEGER'), ('at', 'REAL'), ('fallback', 'INTEGER'),
           ('source', 'TEXT'), ('review_provider', 'TEXT'), ('review_model', 'TEXT'),
           ('cost', 'REAL'), ('task_class', 'TEXT'))
# Routing 2 §5.3 — per (task class, model): a first-try verified outcome counts 1, a verified outcome
# that needed rework counts half, a failure 0. Promote at or above PROMOTION_RATE, demote below
# DEMOTION_RATE; only with at least MIN_SAMPLES outcomes *and* the decayed weight floor.
PROMOTION_RATE = 0.85
MIN_SAMPLES = 3
# Three fresh outcomes weigh just under 3.0; the weight floor for a class keeps them (≥ 2.5) while
# three outcomes a week old (≈ 1.5) no longer move anything.
CLASS_MIN_WEIGHT = 2.5
REWORK_CREDIT = 0.5
# Older rows carry only the job's kind; these kinds map to one class without guessing.
KIND_CLASSES = {'coding': 'coding', 'research': 'research'}

_RECORD_SQL = (
    'INSERT INTO routing_outcomes(run_id,provider,verdict,job_kind,attempts,escalated,model,ms,at,'
    'fallback,source,review_provider,review_model,cost,task_class) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) '
    'ON CONFLICT(run_id) DO UPDATE SET verdict=excluded.verdict,'
    ' job_kind=COALESCE(excluded.job_kind, job_kind), attempts=COALESCE(excluded.attempts, attempts),'
    ' escalated=COALESCE(excluded.escalated, escalated), model=COALESCE(excluded.model, model),'
    ' ms=COALESCE(excluded.ms, ms), at=excluded.at,'
    ' fallback=COALESCE(excluded.fallback, fallback), source=COALESCE(excluded.source, source),'
    ' review_provider=COALESCE(excluded.review_provider, review_provider),'
    ' review_model=COALESCE(excluded.review_model, review_model),'
    ' cost=COALESCE(excluded.cost, cost), task_class=COALESCE(excluded.task_class, task_class) '
    "WHERE IFNULL(routing_outcomes.source,'')<>'review' OR IFNULL(excluded.source,'')='review'"
)


def ensure_columns(store, db=None):
    """Additive, safe to re-run: the fuller evidence row, on a store that predates it."""

    def run(connection):
        existing = {row[1] for row in connection.execute('PRAGMA table_info(routing_outcomes)')}
        for name, kind in COLUMNS:
            if name not in existing:
                connection.execute('ALTER TABLE routing_outcomes ADD COLUMN %s %s' % (name, kind))

    if db is not None:
        run(db)
        return
    with contextlib.closing(store.connect()) as connection:
        run(connection)


def weight(age_seconds, half_life_days=HALF_LIFE_DAYS):
    """How much one outcome counts right now."""
    if age_seconds is None or age_seconds < 0:
        return 0.0
    return 0.5 ** (age_seconds / (half_life_days * DAY))


def record(store, run_id, provider, verdict, *, job_kind=None, attempts=None, escalated=None,
           model=None, ms=None, cost=None, fallback=None, source='review', review_provider=None,
           review_model=None, at=None, task_class=None, db=None):
    """Write one outcome for one run — idempotent per run, with review precedence."""
    row = (str(run_id), str(provider), str(verdict), job_kind, attempts,
           None if escalated is None else int(bool(escalated)), model, ms,
           float(at if at is not None else time.time()), fallback, source, review_provider,
           review_model, cost, task_class)
    if db is not None:
        db.execute(_RECORD_SQL, row)
        return
    with store.transaction() as connection:
        connection.execute(_RECORD_SQL, row)


def observed_ms(store, run_id, db=None):
    """The span between a run's first and last native event, when it left any. None otherwise.

    Honest about what it is: an observation from the run's own event trail, not a stopwatch.
    """

    def run(connection):
        try:
            row = connection.execute('SELECT MIN(at) AS first, MAX(at) AS last FROM native_progress'
                                     ' WHERE run_id=?', (str(run_id),)).fetchone()
        except Exception:
            return None
        if not row or row['first'] is None or row['last'] is None:
            return None
        return int(max(0.0, (float(row['last']) - float(row['first'])) * 1000))

    if db is not None:
        return run(db)
    try:
        with contextlib.closing(store.connect()) as connection:
            return run(connection)
    except Exception:
        return None


def _rows(store, provider=None, window_days=WINDOW_DAYS, now=None, db=None):
    now = float(now if now is not None else time.time())
    floor = now - window_days * DAY
    sql = 'SELECT * FROM routing_outcomes WHERE at>=?' + (' AND provider=?' if provider else '')
    args = (floor, str(provider)) if provider else (floor,)

    def run(connection):
        return [dict(row) for row in connection.execute(sql, args)]

    if db is not None:
        return run(db)
    with contextlib.closing(store.connect()) as connection:
        return run(connection)


def score(store, provider, window_days=WINDOW_DAYS, now=None, db=None):
    """The decayed record for one provider: samples, weight, verified rate (None under the floor)."""
    now = float(now if now is not None else time.time())
    rows = _rows(store, provider, window_days, now, db=db)
    total = verified = 0.0
    samples = 0
    last = None
    for row in rows:
        at = row.get('at')
        if not at:
            continue  # rows older than the timestamp column: visible in the table, never weighted
        samples += 1
        current = float(at)
        total += weight(max(0.0, now - current))
        if str(row.get('verdict')) == 'VERIFIED':
            verified += weight(max(0.0, now - current))
        last = current if last is None else max(last, current)
    return {'provider': str(provider), 'samples': samples, 'weight': round(total, 2),
            'window_days': window_days, 'last_at': last,
            'verified_rate': (verified / total) if total >= MIN_WEIGHT else None}


def sentence(scored):
    """The evidence, said plainly — the same words every surface shows."""
    if not scored or not scored.get('samples'):
        return 'No finished work to judge yet.'
    if scored.get('verified_rate') is None:
        return 'Only a few recent runs so far; not enough to judge.'
    return ('Verified in about %d%% of its recent runs (last %d days).'
            % (round(float(scored['verified_rate']) * 100),
               int(scored.get('window_days') or WINDOW_DAYS)))


def summary(store, names, window_days=WINDOW_DAYS, now=None):
    """The evidence block a route explanation carries: only providers that have real samples."""
    out = {}
    for name in names or ():
        scored = score(store, name, window_days, now)
        if not scored['samples']:
            continue
        scored['sentence'] = sentence(scored)
        scored['demote'] = bool(scored['verified_rate'] is not None
                                and scored['verified_rate'] < (1 - DEMOTION_RATE))
        out[str(name)] = scored
    return out


def _class_of(row):
    return row.get('task_class') or KIND_CLASSES.get(row.get('job_kind'))


def class_score(store, task_class, model, window_days=WINDOW_DAYS, now=None, rows=None):
    """The decayed record of one catalog model for one task class (Routing 2 §5.3).

    `rate` is None under the floor (fewer than MIN_SAMPLES outcomes, or less than MIN_WEIGHT of
    recent weight): thin evidence never moves a model."""
    from .role_models import catalog_id
    now = float(now if now is not None else time.time())
    rows = rows if rows is not None else _rows(store, None, window_days, now)
    total = earned = 0.0
    samples = 0
    last = None
    for row in rows:
        if not row.get('at') or _class_of(row) != task_class:
            continue
        if catalog_id(row.get('model'), row.get('provider')) != model:
            continue
        verdict = str(row.get('verdict'))
        if verdict not in ('VERIFIED', 'FAILED'):
            continue
        samples += 1
        weighed = weight(max(0.0, now - float(row['at'])))
        total += weighed
        if verdict == 'VERIFIED':
            earned += weighed * (1.0 if (row.get('attempts') or 1) <= 1 else REWORK_CREDIT)
        last = float(row['at']) if last is None else max(last, float(row['at']))
    rate = (earned / total) if (samples >= MIN_SAMPLES and total >= CLASS_MIN_WEIGHT) else None
    verdict = None
    if rate is not None:
        verdict = 'promote' if rate >= PROMOTION_RATE else ('demote' if rate < DEMOTION_RATE else None)
    return {'model': model, 'task_class': task_class, 'samples': samples, 'weight': round(total, 2),
            'rate': None if rate is None else round(rate, 3), 'verdict': verdict, 'last_at': last,
            'window_days': window_days}


def class_sentence(scored):
    """"Verified in about 92% of its recent coding runs (5 runs, last 30 days)." — the same words
    everywhere a ranking reason is shown."""
    from .task_routing import label
    what = label(scored['task_class']).lower()
    if not scored.get('samples'):
        return 'No finished %s work to judge yet.' % what
    if scored.get('rate') is None:
        return 'Only %d recent %s run%s so far; not enough to judge.' % (
            scored['samples'], what, '' if scored['samples'] == 1 else 's')
    return ('Verified in about %d%% of its recent %s runs (%d runs, last %d days; rework counts half).'
            % (round(scored['rate'] * 100), what, scored['samples'], int(scored['window_days'])))


def class_summary(store, task_class, models, window_days=WINDOW_DAYS, now=None):
    """{model: scored + sentence} for the models that have outcomes in this class."""
    now = float(now if now is not None else time.time())
    rows = _rows(store, None, window_days, now)
    out = {}
    for model in models or ():
        scored = class_score(store, task_class, model, window_days, now, rows=rows)
        if not scored['samples']:
            continue
        scored['sentence'] = class_sentence(scored)
        out[model] = scored
    return out
