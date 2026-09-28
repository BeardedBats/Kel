"""Subscription quota: how much of Nick's Claude and ChatGPT (Codex) plan limits is used, and how fast.

Routing 2 "Still open" (quota-pace projection, subscription burn). Sources are what each CLI itself
reports — verified on this PC (2026-09-28), never guessed:

- **Claude Code 2.1.283**, `-p --output-format stream-json --verbose`: one line
  `{"type":"rate_limit_event","rate_limit_info":{"status":"allowed"|"allowed_warning"|"rejected",
  "resetsAt":<unix s>,"rateLimitType":"five_hour"|…,"utilization":0.99,"unifiedWindows":{"five_hour":
  {"utilization":0.99,"resetsAt":…},"seven_day":{…}},"isUsingOverage":false,…}}`. The plain `json`
  output format carries no quota at all, so Kel's Claude calls use stream-json.
- **Codex 0.157.1** app-server: `account/rateLimits/read` and the `account/rateLimits/updated`
  notification — `{rateLimits:{primary|secondary:{usedPercent,resetsAt,windowDurationMins},
  planType,rateLimitReachedType}}` (the installed binary's generated JSON schema). `codex exec --json`
  reports no limits, but the session's own rollout file (`~/.codex/sessions/…/rollout-*-<thread>.jsonl`)
  carries the same snapshot in snake case on its `token_count` event.

Each observation is kept on the runtime's adapters' provider state (`providers` table): `quota` stays
the percent left (the router's existing input), plus the windows and a few samples per window from
which the pace is projected. A window whose reset time has passed no longer counts (a used-up plan
becomes usable again at its reset even if no new observation arrives). Routing reads `standing()`:
**exhausted** → the plan's models can't run, with the plain reason and when it resets; **low** (≤ 10%
left, or on pace to run out before the reset with ≤ 25% left) → ranked below the others, never past
Nick's own Fixed/Preferred choice; otherwise unchanged. Unknown stays unknown.
"""
import json
import time

from .core import encode

RUNTIME_ADAPTERS = {'claude': ('claude', 'claude-code', 'claude-web'),
                    'codex': ('codex', 'codex-code', 'codex-web')}
PLAN_LABELS = {'claude': 'Claude plan', 'codex': 'ChatGPT plan (Codex)'}
LOW_LEFT = 10.0          # percent left at or below which a plan is "nearly used up"
PACE_LEFT = 25.0         # a plan on pace to run out before its reset counts as low below this
MIN_PACE_SPAN = 300.0    # seconds of samples needed before a pace is projected
MAX_SAMPLES = 24
_WINDOW_LABELS = {'five_hour': '5-hour', 'seven_day': 'weekly', 'seven_day_opus': 'weekly Opus',
                  'seven_day_sonnet': 'weekly Sonnet', 'seven_day_oauth_apps': 'weekly apps'}


def runtime_of(adapter):
    for runtime, names in RUNTIME_ADAPTERS.items():
        if adapter in names:
            return runtime
    return None


def _num(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _minutes_label(minutes):
    if not minutes:
        return None
    if minutes == 10080:
        return 'weekly'
    if minutes % 1440 == 0:
        return '%d-day' % (minutes // 1440)
    if minutes % 60 == 0:
        return '%d-hour' % (minutes // 60)
    return '%d-minute' % minutes


# ---- reading what each CLI reports --------------------------------------------------------------

def from_claude(info):
    """A snapshot from Claude Code's `rate_limit_info`, or None."""
    if not isinstance(info, dict):
        return None
    windows = []
    unified = info.get('unifiedWindows') if isinstance(info.get('unifiedWindows'), dict) else {}
    for key, value in unified.items():
        if isinstance(value, dict) and _num(value.get('utilization')) is not None:
            windows.append({'id': str(key), 'label': _WINDOW_LABELS.get(key, str(key).replace('_', ' ')),
                            'used': round(_num(value['utilization']) * 100, 1),
                            'resets_at': _num(value.get('resetsAt'))})
    kind = info.get('rateLimitType')
    if not windows and _num(info.get('utilization')) is not None:
        windows.append({'id': str(kind or 'limit'), 'label': _WINDOW_LABELS.get(kind, str(kind or 'usage')),
                        'used': round(_num(info['utilization']) * 100, 1), 'resets_at': _num(info.get('resetsAt'))})
    status = str(info.get('status') or '')
    blocked = status == 'rejected' and not info.get('isUsingOverage')
    if blocked:
        hit = next((w for w in windows if w['id'] == kind), None)
        if hit is None:
            windows.append({'id': str(kind or 'limit'), 'label': _WINDOW_LABELS.get(kind, 'usage'),
                            'used': 100.0, 'resets_at': _num(info.get('resetsAt'))})
        else:
            hit['used'] = max(hit['used'], 100.0)
    if not windows and not blocked:
        return None
    return {'runtime': 'claude', 'windows': windows, 'blocked': blocked, 'status': status or None,
            'plan': None, 'source': 'Claude Code rate_limit_event'}


def from_codex(bucket, source='Codex account/rateLimits'):
    """A snapshot from a Codex rate-limit bucket (app-server camelCase or rollout snake case)."""
    if not isinstance(bucket, dict):
        return None
    if isinstance(bucket.get('rateLimits'), dict):
        bucket = bucket['rateLimits']
    windows = []
    for key in ('primary', 'secondary'):
        value = bucket.get(key)
        if not isinstance(value, dict):
            continue
        used = _num(value.get('usedPercent', value.get('used_percent')))
        if used is None:
            continue
        minutes = _num(value.get('windowDurationMins', value.get('window_minutes')))
        windows.append({'id': key, 'label': _minutes_label(int(minutes)) if minutes else key,
                        'used': round(used, 1), 'minutes': int(minutes) if minutes else None,
                        'resets_at': _num(value.get('resetsAt', value.get('resets_at')))})
    reached = bucket.get('rateLimitReachedType', bucket.get('rate_limit_reached_type'))
    if not windows and not reached:
        return None
    return {'runtime': 'codex', 'windows': windows, 'blocked': bool(reached),
            'status': str(reached) if reached else None,
            'plan': bucket.get('planType', bucket.get('plan_type')), 'source': source}


def from_codex_read(response):
    """A snapshot from an `account/rateLimits/read` response (the `codex` limit when it is split)."""
    response = response or {}
    bucket = (response.get('rateLimitsByLimitId') or {}).get('codex') or response.get('rateLimits')
    return from_codex(bucket, 'Codex account/rateLimits/read')


def codex_rollout_limits(thread_id, home=None, now=None):
    """The last rate-limit snapshot Codex wrote into this thread's rollout file, or None."""
    import os
    from pathlib import Path
    if not thread_id:
        return None
    home = Path(home or os.environ.get('CODEX_HOME') or os.path.join(os.path.expanduser('~'), '.codex'))
    stamp = time.time() if now is None else now
    found = None
    for delta in (0, -86400, 86400):
        day = time.localtime(stamp + delta)
        folder = home / 'sessions' / ('%04d' % day.tm_year) / ('%02d' % day.tm_mon) / ('%02d' % day.tm_mday)
        try:
            matches = list(folder.glob('rollout-*%s.jsonl' % thread_id))
        except OSError:
            matches = []
        if matches:
            found = matches[0]
            break
    if found is None:
        return None
    snapshot = None
    try:
        with found.open('r', encoding='utf-8', errors='replace') as handle:
            for line in handle:
                if '"rate_limits"' not in line:
                    continue
                try:
                    payload = (json.loads(line).get('payload') or {})
                except ValueError:
                    continue
                limits = payload.get('rate_limits') if isinstance(payload, dict) else None
                if isinstance(limits, dict):
                    snapshot = from_codex(limits, 'Codex session log') or snapshot
    except OSError:
        return None
    return snapshot


# ---- keeping observations -----------------------------------------------------------------------

def _live(windows, now):
    return [w for w in windows or () if not (w.get('resets_at') and w['resets_at'] <= now)]


def _merge_samples(samples, windows, now):
    samples = dict(samples or {})
    for window in windows:
        key = window['id']
        kept = [s for s in samples.get(key) or () if s[2] == window.get('resets_at')]
        if kept and kept[-1][1] == window['used'] and now - kept[-1][0] < 60:
            continue
        kept.append([now, window['used'], window.get('resets_at')])
        samples[key] = kept[-MAX_SAMPLES:]
    return samples


def _left_from(windows, blocked, reset, now):
    if blocked and (reset is None or reset > now):
        return 0.0
    live = _live(windows, now)
    if not live:
        return None
    return max(0.0, round(100.0 - max(w['used'] for w in live), 1))


def apply(state, snapshot, now=None):
    """The provider state with one observation merged in (pure; returns a new dict)."""
    now = time.time() if now is None else now
    state = dict(state or {})
    windows = list(snapshot.get('windows') or ())
    blocked = bool(snapshot.get('blocked'))
    exhausted = [w for w in windows if w['used'] >= 100 and w.get('resets_at')]
    reset = min((w['resets_at'] for w in exhausted), default=None)
    if blocked and reset is None:
        reset = max((w['resets_at'] for w in windows if w.get('resets_at')), default=None)
    state.update(quota=_left_from(windows, blocked, reset, now), quota_unit='percent_remaining',
                 quota_observed_at=now, quota_reset=reset, quota_source=snapshot.get('source'),
                 quota_windows=windows, quota_blocked=blocked,
                 quota_samples=_merge_samples(state.get('quota_samples'), windows, now))
    if snapshot.get('plan'):
        state['planType'] = snapshot['plan']
    state.setdefault('failures', 0)
    state.setdefault('circuit_until', 0)
    return state


def observe(store, snapshot, db=None, now=None):
    """Record one observation on every adapter of its runtime (additive; returns the new quota)."""
    if not snapshot or snapshot.get('runtime') not in RUNTIME_ADAPTERS:
        return None
    now = time.time() if now is None else now

    def write(conn):
        left = None
        for adapter in RUNTIME_ADAPTERS[snapshot['runtime']]:
            old = conn.execute('SELECT data FROM providers WHERE id=?', (adapter,)).fetchone()
            try:
                state = json.loads(old['data']) if old else {}
            except (TypeError, ValueError):
                state = {}
            state = apply(state, snapshot, now)
            left = state['quota']
            conn.execute('INSERT INTO providers VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                         (adapter, encode(state)))
        return left

    if db is not None:
        return write(db)
    with store.transaction() as conn:
        return write(conn)


def observe_result(store, adapter, result, db=None):
    """Record the quota a call's result carried (`rate_limits`, set by the adapters), if any."""
    snapshot = (result or {}).get('rate_limits') if isinstance(result, dict) else None
    if isinstance(snapshot, dict) and snapshot.get('runtime') in RUNTIME_ADAPTERS:
        return observe(store, snapshot, db=db)
    return None


def expire(store, now=None):
    """Rewrite `quota` for states whose windows have reset since they were observed (so readers of
    the raw field — the reviewer picker, diagnostics — do not see a used-up plan for ever)."""
    now = time.time() if now is None else now
    changed = 0
    with store.transaction() as db:
        for row in db.execute('SELECT id, data FROM providers').fetchall():
            try:
                state = json.loads(row['data'])
            except (TypeError, ValueError):
                continue
            if 'quota_windows' not in state and not state.get('quota_reset'):
                continue
            fresh = left(state, now)
            if fresh != state.get('quota'):
                state['quota'] = fresh
                if fresh is None or fresh > 0:
                    state['quota_blocked'] = False
                db.execute('UPDATE providers SET data=? WHERE id=?', (encode(state), row['id']))
                changed += 1
    return changed


# ---- what routing reads -------------------------------------------------------------------------

def left(state, now=None):
    """Percent of the plan left now (None = unknown), honouring resets that have passed."""
    state = state or {}
    now = time.time() if now is None else now
    if state.get('quota_unit') not in (None, 'percent_remaining'):
        return _num(state.get('quota'))
    reset = _num(state.get('quota_reset'))
    if 'quota_windows' in state:
        return _left_from(state.get('quota_windows'), bool(state.get('quota_blocked')), reset, now)
    quota = _num(state.get('quota'))
    if quota is not None and quota <= 0 and reset and reset <= now:
        return None  # an older observation of a used-up plan whose window has since reset
    return quota


def _pace(state, window, now):
    samples = [s for s in (state.get('quota_samples') or {}).get(window['id']) or ()
               if s[2] == window.get('resets_at')]
    if len(samples) < 2 or samples[-1][0] - samples[0][0] < MIN_PACE_SPAN:
        return None
    rate = (samples[-1][1] - samples[0][1]) / (samples[-1][0] - samples[0][0])  # percent per second
    out = {'per_hour': round(rate * 3600, 2)}
    if rate > 0 and window['used'] < 100:
        runs_out = now + (100.0 - window['used']) / rate
        out['runs_out_at'] = int(runs_out)
        out['before_reset'] = bool(window.get('resets_at') and runs_out < window['resets_at'])
    return out


def when(stamp, now=None):
    """'15:40', or 'Tue 15:40' when it is not today (local time)."""
    now = time.time() if now is None else now
    then = time.localtime(stamp)
    if time.strftime('%Y%m%d', then) == time.strftime('%Y%m%d', time.localtime(now)):
        return time.strftime('%H:%M', then)
    return time.strftime('%a %H:%M', then)


def standing(state, runtime, now=None):
    """{'level': exhausted|low|ok|unknown, 'left', 'reason', 'resets_at', 'windows'} for one plan."""
    now = time.time() if now is None else now
    state = state or {}
    plan = PLAN_LABELS.get(runtime, 'plan')
    percent = left(state, now)
    windows = []
    for window in _live(state.get('quota_windows'), now):
        entry = dict(window)
        entry['pace'] = _pace(state, window, now)
        windows.append(entry)
    out = {'level': 'unknown', 'left': percent, 'reason': None, 'resets_at': None, 'windows': windows,
           'observed_at': state.get('quota_observed_at'), 'source': state.get('quota_source'),
           'plan_type': state.get('planType')}
    if percent is None:
        return out
    tightest = max(windows, key=lambda w: w['used'], default=None)
    name = (tightest or {}).get('label') or 'usage'
    if percent <= 0:
        reset = _num(state.get('quota_reset')) or (tightest or {}).get('resets_at')
        until = (' until %s' % when(reset, now)) if reset else ''
        out.update(level='exhausted', resets_at=reset,
                   reason=("your %s's %s limit is used up%s" % (plan, name, until)) if tightest else
                   ("your %s's usage limit is reached%s" % (plan, until)))
        return out
    if percent <= LOW_LEFT:
        out.update(level='low', resets_at=(tightest or {}).get('resets_at'),
                   reason='your %s has %s%% of its %s limit left' % (plan, _pct(percent), name))
        return out
    for window in windows:
        pace = window.get('pace') or {}
        if pace.get('before_reset') and 100 - window['used'] <= PACE_LEFT:
            out.update(level='low', resets_at=window.get('resets_at'),
                       reason='your %s is on pace to use up its %s limit by %s, before it resets'
                              % (plan, window['label'], when(pace['runs_out_at'], now)))
            return out
    out['level'] = 'ok'
    return out


def _pct(value):
    return ('%d' % value) if float(value).is_integer() else ('%.1f' % value)


def adapter_standing(states, adapter, now=None):
    runtime = runtime_of(adapter)
    if runtime is None:
        return {'level': 'unknown', 'left': None, 'reason': None}
    return standing((states or {}).get(adapter) or {}, runtime, now)


def candidate_fields(state, adapter, now=None):
    """The router's quota inputs for one adapter: percent left (reset-aware) and whether it is low."""
    runtime = runtime_of(adapter)
    if runtime is None:
        return {'quota': (state or {}).get('quota'), 'quota_low': False}
    view = standing(state, runtime, now)
    return {'quota': view['left'], 'quota_low': view['level'] == 'low'}


def plans(store, now=None):
    """Both subscription plans for Settings (`/api/model`): level, percent left, windows with pace."""
    try:
        states = store.provider_states()
    except Exception:
        states = {}
    now = time.time() if now is None else now
    out = []
    for runtime, adapters in RUNTIME_ADAPTERS.items():
        state = next((states[a] for a in adapters if 'quota_windows' in (states.get(a) or {})), None) \
            or next((states[a] for a in adapters if (states.get(a) or {}).get('quota') is not None), None) or {}
        view = standing(state, runtime, now)
        view.update(runtime=runtime, label=PLAN_LABELS[runtime],
                    summary=_summary(view, runtime, now))
        out.append(view)
    return out


def _summary(view, runtime, now):
    if view['level'] == 'unknown':
        return ('Not reported yet: Kel reads it from %s as it runs.'
                % ('Claude Code' if runtime == 'claude' else 'Codex'))
    if view['level'] in ('exhausted', 'low'):
        return view['reason'][0].upper() + view['reason'][1:] + '.'
    parts = []
    for window in view['windows']:
        text = '%s: %s%% used' % (window['label'][0].upper() + window['label'][1:], _pct(window['used']))
        if window.get('resets_at'):
            text += ', resets %s' % when(window['resets_at'], now)
        parts.append(text)
    return '; '.join(parts) or '%s%% left.' % _pct(view['left'])

