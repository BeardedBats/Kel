"""Measured tokens, wall-clock and approximate cost for every model call Kel's staff make (Routing 2).

Design: `docs/v2/design/ROUTING_2.md` §5.2. One store, reused: `provider_usage` (V1.4 migration 7),
one `{"event": "run", ...}` row per call (a work step's run, a Verifier check, an Oracle review),
idempotent per call id. Sources are what each runtime itself reports — never guessed:

- Claude Code `-p --output-format json` and Kel's Claude host: `usage` {input_tokens,
  cache_creation_input_tokens, cache_read_input_tokens, output_tokens} and `total_cost_usd`;
- Codex `exec --json`: `turn.completed.usage` {input_tokens, cached_input_tokens, output_tokens,
  reasoning_output_tokens} (input includes the cached part);
- Codex app-server: `thread/tokenUsage/updated` {tokenUsage: {total, last: {inputTokens,
  cachedInputTokens, outputTokens, reasoningOutputTokens, totalTokens}}};
- the Anthropic API worker: its responses' `usage`; OpenAI-compatible APIs (DeepSeek, OpenRouter):
  `usage` {prompt_tokens, completion_tokens, prompt_cache_hit_tokens | prompt_tokens_details.cached_tokens,
  completion_tokens_details.reasoning_tokens, cost}.

*Processed tokens* = uncached input (Claude: input + cache creation; Codex: input − cached) + output.
Cached tokens are kept apart; a runtime that reports nothing leaves every number unknown (None).
Cost: the runtime's own figure when it gives one (`reported`), else an estimate from the catalog's
list price (`estimated`), else unknown — an unpriced model is never "free". Subscription runtimes'
dollar figures are API-equivalent effort, not money charged. No prompt, answer or path is stored.
"""
import contextlib
import json
import statistics
import threading
import time

from .core import encode

DAY = 86400.0
WINDOW_DAYS = 30.0
KINDS = ('work', 'check', 'oracle', 'plan', 'turn', 'reply', 'calibration')
# D-72 item 6: Kel's own calls (a turn decision, a direct reply, a plan) are recorded too, with the
# conversation and submission they belong to, so each of Kel's messages can say what it used.
KEL_KINDS = ('turn', 'reply', 'plan')
EXTRA_KEYS = ('conversation_id', 'submission_id', 'role', 'asked_model', 'why')

_DDL = """
CREATE TABLE IF NOT EXISTS provider_usage(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL, at REAL NOT NULL,
  data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS provider_usage_provider ON provider_usage(provider, at);
CREATE INDEX IF NOT EXISTS provider_usage_call ON provider_usage(json_extract(data,'$.call_id'));
CREATE INDEX IF NOT EXISTS provider_usage_job ON provider_usage(json_extract(data,'$.job_id'));
CREATE INDEX IF NOT EXISTS provider_usage_submission ON provider_usage(json_extract(data,'$.submission_id'));
"""
_READY = set()
_STATS = {}
_STATS_LOCK = threading.Lock()
STATS_TTL = 10.0


def ensure(db, root=None):
    """The usage table and its call/job indexes (additive, idempotent)."""
    key = str(root) if root is not None else None
    if key and key in _READY:
        return
    # Statement by statement: executescript would COMMIT a caller's open transaction.
    for statement in [part.strip() for part in _DDL.split(';') if part.strip()]:
        db.execute(statement)
    if key:
        _READY.add(key)


def _int(value):
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None


def normalize(result, *, model=None):
    """{input, cached, output, reasoning, processed, cost_usd, cost_basis, runtime_ms} for one call."""
    result = result or {}
    raw = result.get('usage')
    usage = raw if isinstance(raw, dict) else {}
    if isinstance(usage.get('total'), dict):  # an app-server tokenUsage block
        usage = usage['total']
    inp = cached = out = reasoning = None
    if 'cache_read_input_tokens' in usage or 'cache_creation_input_tokens' in usage:  # Claude
        base, created = _int(usage.get('input_tokens')), _int(usage.get('cache_creation_input_tokens'))
        inp = None if base is None and created is None else (base or 0) + (created or 0)
        cached, out = _int(usage.get('cache_read_input_tokens')), _int(usage.get('output_tokens'))
    elif 'cached_input_tokens' in usage or 'reasoning_output_tokens' in usage:  # Codex exec
        total, cached = _int(usage.get('input_tokens')), _int(usage.get('cached_input_tokens'))
        inp = None if total is None else max(0, total - (cached or 0))
        out, reasoning = _int(usage.get('output_tokens')), _int(usage.get('reasoning_output_tokens'))
    elif 'inputTokens' in usage or 'outputTokens' in usage:  # Codex app-server
        total, cached = _int(usage.get('inputTokens')), _int(usage.get('cachedInputTokens'))
        inp = None if total is None else max(0, total - (cached or 0))
        out, reasoning = _int(usage.get('outputTokens')), _int(usage.get('reasoningOutputTokens'))
    elif 'prompt_tokens' in usage or 'completion_tokens' in usage:  # OpenAI-compatible APIs
        total = _int(usage.get('prompt_tokens'))
        details = usage.get('prompt_tokens_details') if isinstance(usage.get('prompt_tokens_details'), dict) else {}
        cached = _int(usage.get('prompt_cache_hit_tokens'))
        if cached is None:
            cached = _int(details.get('cached_tokens'))
        inp = None if total is None else max(0, total - (cached or 0))
        out = _int(usage.get('completion_tokens'))
        completion = usage.get('completion_tokens_details') if isinstance(
            usage.get('completion_tokens_details'), dict) else {}
        reasoning = _int(completion.get('reasoning_tokens'))
    elif 'input_tokens' in usage or 'output_tokens' in usage:  # Anthropic API without caching
        inp, out = _int(usage.get('input_tokens')), _int(usage.get('output_tokens'))
    elif _int(result.get('output_tokens')) is not None:  # the internal worker's own count
        out = _int(result.get('output_tokens'))
    processed = None if inp is None and out is None else (inp or 0) + (out or 0)
    cost, basis = None, 'unknown'
    reported = result.get('cost_usd')
    if reported is None and isinstance(raw, dict):
        reported = raw.get('cost')
    if isinstance(reported, (int, float)) and not isinstance(reported, bool) and reported >= 0:
        cost, basis = float(reported), 'reported'
    elif model and (inp is not None or out is not None):
        from .role_models import PRICES
        price = PRICES.get(model)
        if price:
            cost = ((inp or 0) * price[0] + (cached or 0) * price[1] + (out or 0) * price[2]) / 1e6
            basis = 'estimated'
    runtime_ms = _int(result.get('runtime_ms'))
    return {'input': inp, 'cached': cached, 'output': out, 'reasoning': reasoning,
            'processed': processed, 'cost_usd': None if cost is None else round(cost, 6),
            'cost_basis': basis, 'runtime_ms': runtime_ms}


class TurnTokens:
    """One coding turn's tokens from the runtime's own notices. Codex's app-server sends the thread's
    running total with the last request's share, so this turn = final total − (first total − first
    last); Kel's Claude host reports the turn's usage, cost and duration when the turn completes."""
    KEYS = ('inputTokens', 'cachedInputTokens', 'outputTokens', 'reasoningOutputTokens', 'totalTokens')

    def __init__(self):
        self.base = self.total = self.claude = None
        self.extra = {}

    def observe(self, method, params):
        params = params or {}
        info = params.get('tokenUsage') if isinstance(params.get('tokenUsage'), dict) else {}
        if method == 'thread/tokenUsage/updated' and isinstance(info.get('total'), dict):
            last = info.get('last') if isinstance(info.get('last'), dict) else {}
            if self.base is None:
                self.base = {k: max(0, (_int(info['total'].get(k)) or 0) - (_int(last.get(k)) or 0))
                             for k in self.KEYS}
            self.total = info['total']
        if method == 'turn/completed' and isinstance(params.get('usage'), dict):
            self.claude = params['usage']
            if isinstance(params.get('cost_usd'), (int, float)):
                self.extra['cost_usd'] = params['cost_usd']
            if isinstance(params.get('duration_ms'), (int, float)):
                self.extra['runtime_ms'] = int(params['duration_ms'])

    def apply(self, result):
        if self.total is not None:
            result['usage'] = {k: max(0, (_int(self.total.get(k)) or 0) - self.base.get(k, 0))
                               for k in self.KEYS}
        elif self.claude is not None:
            result['usage'] = self.claude
        result.update(self.extra)
        return result


def wall_ms(result):
    """The wall-clock a call took, as measured around it (broker / engine / reviewer)."""
    value = (result or {}).get('wall_ms')
    if isinstance(value, (int, float)) and value >= 0:
        return int(value)
    duration = (result or {}).get('duration')
    if isinstance(duration, (int, float)) and duration >= 0:
        return int(duration * 1000)
    return None


def record(store, call_id, *, job_id=None, milestone_id=None, kind='work', adapter=None, model=None,
           task_class=None, result=None, wall=None, db=None, at=None, extra=None):
    """Write one usage row for one call (idempotent per call id). Returns the row's data.

    `extra` may carry the conversation and submission a call of Kel's own belongs to, its role and
    the model it was asked for (EXTRA_KEYS); nothing else is stored."""
    from .role_models import catalog_id, is_subscription
    catalog = catalog_id((result or {}).get('model_used') or model, adapter)
    data = {'event': 'run', 'call_id': str(call_id), 'job_id': job_id, 'milestone_id': milestone_id,
            'kind': kind if kind in KINDS else 'work', 'adapter': adapter, 'model': catalog,
            'raw_model': str((result or {}).get('model_used') or model or '')[:120] or None,
            'task_class': task_class, 'outcome': (result or {}).get('outcome'),
            'wall_ms': wall if wall is not None else wall_ms(result),
            'subscription': is_subscription(adapter)}
    for key in EXTRA_KEYS:
        value = (extra or {}).get(key)
        if value is not None:
            data[key] = str(value)[:300]
    data.update(normalize(result, model=catalog))

    def write(conn):
        ensure(conn, getattr(store, 'root', None))
        if conn.execute("SELECT 1 FROM provider_usage WHERE json_extract(data,'$.call_id')=?",
                        (str(call_id),)).fetchone():
            return data
        conn.execute('INSERT INTO provider_usage(provider, at, data) VALUES(?,?,?)',
                     (str(adapter or 'unknown'), float(at if at is not None else time.time()), encode(data)))
        return data

    with _STATS_LOCK:
        _STATS.clear()
    if db is not None:
        return write(db)
    with store.transaction() as conn:
        return write(conn)


def rows(store, *, job_id=None, submission_id=None, window_days=WINDOW_DAYS, now=None):
    now = float(now if now is not None else time.time())
    with contextlib.closing(store.connect()) as db:
        ensure(db, getattr(store, 'root', None))
        if job_id:
            found = db.execute("SELECT at, data FROM provider_usage WHERE json_extract(data,'$.job_id')=? "
                               "AND json_extract(data,'$.event')='run'", (job_id,)).fetchall()
        elif submission_id:
            found = db.execute("SELECT at, data FROM provider_usage WHERE json_extract(data,'$.submission_id')=? "
                               "AND json_extract(data,'$.event')='run'", (submission_id,)).fetchall()
        else:
            found = db.execute("SELECT at, data FROM provider_usage WHERE at>=? AND "
                               "json_extract(data,'$.event')='run'", (now - window_days * DAY,)).fetchall()
    out = []
    for row in found:
        try:
            item = json.loads(row['data'])
        except (TypeError, ValueError):
            continue
        item['at'] = row['at']
        out.append(item)
    return out


def model_stats(store, *, window_days=WINDOW_DAYS, now=None, task_class=None):
    """{catalog model: {runs, avg_cost, cost_basis, median_ms, avg_processed}} from measured calls."""
    key = (str(getattr(store, 'root', id(store))), window_days, task_class)
    stamp = time.time()
    with _STATS_LOCK:
        cached = _STATS.get(key)
        if cached and now is None and stamp - cached[0] < STATS_TTL:
            return cached[1]
    grouped = {}
    for item in rows(store, window_days=window_days, now=now):
        if not item.get('model') or (task_class and item.get('task_class') != task_class):
            continue
        grouped.setdefault(item['model'], []).append(item)
    out = {}
    for model, items in grouped.items():
        costs = [i['cost_usd'] for i in items if isinstance(i.get('cost_usd'), (int, float))]
        walls = [i['wall_ms'] for i in items if isinstance(i.get('wall_ms'), (int, float))]
        tokens = [i['processed'] for i in items if isinstance(i.get('processed'), (int, float))]
        bases = {i.get('cost_basis') for i in items if isinstance(i.get('cost_usd'), (int, float))}
        out[model] = {'runs': len(items),
                      'avg_cost': round(sum(costs) / len(costs), 6) if costs else None,
                      'cost_basis': ('reported' if bases == {'reported'} else
                                     'estimated' if bases else None),
                      'median_ms': int(statistics.median(walls)) if walls else None,
                      'avg_processed': int(sum(tokens) / len(tokens)) if tokens else None}
    with _STATS_LOCK:
        if now is None:
            _STATS[key] = (stamp, out)
    return out


def job_spend(store, job_id):
    """What one job's calls have measurably used: processed tokens, cost, run wall-clock, calls."""
    items = rows(store, job_id=job_id)
    return {'calls': len(items),
            'processed': sum(i['processed'] for i in items if isinstance(i.get('processed'), (int, float))),
            'cost_usd': round(sum(i['cost_usd'] for i in items if isinstance(i.get('cost_usd'), (int, float))), 6),
            'wall_ms': sum(i['wall_ms'] for i in items if isinstance(i.get('wall_ms'), (int, float))),
            'unmeasured': sum(1 for i in items if i.get('processed') is None)}


# ---- per message and per job (what Nick sees) ---------------------------------------------------

def _label(item):
    from .role_models import MODELS, describe_model
    if item.get('model') in MODELS:
        return MODELS[item['model']]['label']
    return describe_model(raw=item.get('raw_model'))[0]


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def summarize(items):
    """One compact usage figure for a set of calls, or None when there were none.

    {calls, tokens, ms, cost, cost_basis, billing, plan_calls, plan_cost_equivalent, model,
    model_label, models}. `billing` is 'plan' when every call ran on a subscription runtime (its
    cost is "included in your plan", never $0.00), 'metered' when none did and 'mixed' otherwise;
    `cost` is what the metered calls cost, None when any of them is unknown (never guessed as free).
    """
    items = [i for i in items or () if isinstance(i, dict)]
    if not items:
        return None
    tokens = [i['processed'] for i in items if _number(i.get('processed'))]
    walls = [i['wall_ms'] for i in items if _number(i.get('wall_ms'))]
    plan = [i for i in items if i.get('subscription')]
    metered = [i for i in items if not i.get('subscription')]
    costs = [i['cost_usd'] for i in metered if _number(i.get('cost_usd'))]
    plan_costs = [i['cost_usd'] for i in plan if _number(i.get('cost_usd'))]
    bases = {i.get('cost_basis') for i in metered if _number(i.get('cost_usd'))}
    labels = []
    for item in items:
        label = _label(item)
        if label and label not in labels:
            labels.append(label)
    last = items[-1]
    return {'calls': len(items),
            'tokens': int(sum(tokens)) if tokens else None,
            'ms': int(sum(walls)) if walls else None,
            'cost': round(sum(costs), 6) if metered and len(costs) == len(metered) else None,
            'cost_basis': 'reported' if bases == {'reported'} else ('estimated' if bases else None),
            'billing': 'plan' if not metered else ('mixed' if plan else 'metered'),
            'plan_calls': len(plan),
            'plan_cost_equivalent': round(sum(plan_costs), 6) if plan_costs else None,
            'model': last.get('model'), 'model_label': _label(last), 'models': labels}


def submission_usage(store, submission_id):
    """What Kel's own calls for one message used (its turn decision, direct reply or plan)."""
    if not submission_id:
        return None
    items = [i for i in rows(store, submission_id=str(submission_id)) if i.get('kind') in KEL_KINDS]
    return summarize(sorted(items, key=lambda i: i.get('at') or 0))


def job_usage(store, job):
    """One piece of work's totals: every staffed call, check and second opinion, plus Kel's plan."""
    job = job or {}
    items = rows(store, job_id=job['id']) if job.get('id') else []
    submission = (job.get('contract') or {}).get('submission_id')
    if submission:
        seen = {i.get('call_id') for i in items}
        items += [i for i in rows(store, submission_id=str(submission))
                  if i.get('kind') == 'plan' and i.get('call_id') not in seen]
    return summarize(sorted(items, key=lambda i: i.get('at') or 0))


def conversation_usage(store, conversation_id):
    """{message seq: usage} for Kel's messages in one conversation that recorded their usage."""
    out = {}
    with contextlib.closing(store.connect()) as db:
        found = db.execute("SELECT seq, meta FROM messages WHERE conversation_id=? AND role='assistant' "
                           "AND meta LIKE ?", (str(conversation_id), '%"usage"%')).fetchall()
    for row in found:
        try:
            meta = json.loads(row['meta'] or '{}')
        except (TypeError, ValueError):
            continue
        if isinstance(meta, dict) and isinstance(meta.get('usage'), dict):
            out[str(row['seq'])] = meta['usage']
    return out
