"""Task classes, dispatch tiers and the per-class ranked model list (Routing 2, workforce-os doc 10).

Design: `docs/v2/design/ROUTING_2.md` §5.1. Every staffed step carries a task class (what kind of
work it is) and a dispatch tier (fast | standard | deep | assurance: how much model and reasoning it
deserves), frozen in the job's contract with the staffing decision. The ranked list says, per task
class, which model Kel would use and why:

1. the governing role's Settings row first — Fixed: only that model; Preferred: that model, then its
   D-67 fallbacks. These are Nick's choices: protected, never moved by evidence (D-69 always wins);
2. then every other model that can run here, by tier fit (how close its strength is to what the tier
   aims at), then measured evidence (promote / demote, `routing_evidence`), then measured cost, then
   measured latency, then name;
3. models that cannot run here last, each with the plain reason.

Nothing here runs a model; `role_models.resolve` uses the ranking to pick one, and the engine records
what was asked, what ran and why.
"""
from .core import PolicyError

TASK_CLASSES = ('quick_answer', 'planning', 'research', 'coding', 'design', 'writing', 'review',
                'utility')
CLASS_LABELS = {'quick_answer': 'Quick answers', 'planning': 'Planning', 'research': 'Research',
                'coding': 'Coding', 'design': 'Design', 'writing': 'Writing', 'review': 'Review',
                'utility': 'Utility work'}
# The Settings row (D-67 role) that governs each class. Writing stays on the Builder (D-69 item 4).
CLASS_ROLE = {'quick_answer': 'kel', 'planning': 'kel', 'research': 'discovery', 'coding': 'builder',
              'design': 'designer', 'writing': 'builder', 'review': 'verifier', 'utility': 'utility'}
CLASS_PURPOSE = {'coding': 'code', 'research': 'text'}  # web research picks 'web' per step

TIERS = ('fast', 'standard', 'deep', 'assurance')
TIER_LABELS = {'fast': 'Fast', 'standard': 'Standard', 'deep': 'Deep', 'assurance': 'Assurance'}
# doc 10 §2: Discovery standard (fast for lookups), Builder standard, Verifier/Sentinel assurance.
BASE_TIER = {'quick_answer': 'fast', 'planning': 'standard', 'research': 'standard',
             'coding': 'standard', 'design': 'standard', 'writing': 'standard',
             'review': 'assurance', 'utility': 'fast'}
# The model strength each tier aims at (role_models.STRENGTH: 1 fast/cheap … 3 strongest).
TIER_TARGET = {'fast': 1, 'standard': 2, 'deep': 3, 'assurance': 3}
# What "Auto" reasoning means per tier: fast → Low, standard → the model's own default (unchanged
# from D-66), deep and assurance → High. An explicit level in Settings always wins.
TIER_REASONING = {'fast': 'low', 'standard': None, 'deep': 'high', 'assurance': 'high'}
RISK_FLAGS = ('security_boundary', 'irreversible', 'data_migration', 'release')


def label(task_class):
    return CLASS_LABELS.get(task_class, str(task_class))


def class_for_role(role, kind):
    """The task class a staffed step does, from its role and the job's kind."""
    if role in ('verifier', 'oracle', 'sentinel'):
        return 'review'
    if role == 'discovery':
        return 'research'
    if role == 'designer':
        return 'design'
    if role == 'utility':
        return 'utility'
    if kind == 'code':
        return 'coding'
    if kind == 'research':
        return 'research'
    return 'writing'  # the Builder writing (D-69 item 4) and Kel's own D0 / combine steps


def tier_for_step(task_class, record=None, hint=None):
    """(dispatch tier, reasons) for one step. Review is always assurance (never lowered). The
    turn classifier's hint sets a work step's tier; the staffing rules only raise it."""
    if task_class == 'review':
        return 'assurance', ['checks of finished work always get assurance-tier review']
    tier = BASE_TIER.get(task_class, 'standard')
    reasons = ['%s work starts at %s' % (label(task_class).lower(), TIER_LABELS[tier].lower())]
    if hint in TIERS:
        wanted = 'deep' if hint == 'assurance' else hint
        if wanted != tier:
            reasons.append("Kel's reading of the request asked for %s" % TIER_LABELS[wanted].lower())
        tier = wanted
    record = record or {}
    features = record.get('features') or {}
    flags = [flag for flag in (record.get('flags') or []) if flag in RISK_FLAGS]
    raise_to = None
    if flags:
        raise_to = ('deep', 'consequential work (%s)' % ', '.join(f.replace('_', ' ') for f in flags))
    elif record.get('tier') == 'D4':
        raise_to = ('deep', 'high-assurance staffing')
    elif task_class == 'coding' and (features.get('complexity') or 0) >= 2:
        raise_to = ('deep', 'a larger code change')
    if raise_to and TIERS.index(raise_to[0]) > TIERS.index(tier):
        tier = raise_to[0]
        reasons.append('raised to %s: %s' % (raise_to[0], raise_to[1]))
    return tier, reasons


def reasoning_for(tier, model_id):
    """The reasoning level a tier asks of a model whose role reasoning is Auto (None = the model's
    own default), clamped to the levels that model's runtime offers."""
    from .role_models import REASONING, reasoning_options
    wanted = TIER_REASONING.get(tier)
    if not wanted:
        return None
    offered = reasoning_options(model_id)
    if wanted in offered:
        return wanted
    # The nearest level the runtime offers below what the tier wants, never above it.
    order = [level for level in REASONING if level != 'auto']
    for level in reversed(order[:order.index(wanted) + 1] if wanted in order else order):
        if level in offered:
            return level
    return None


# ---- the ranking ------------------------------------------------------------------------------

def _measured(store, adapters_by_model, now=None):
    """{model: {'cost', 'latency_ms', 'runs', 'basis'}} from measured usage (Routing 2 §5.2), else the
    runtime's own recent averages; unknown stays unknown."""
    out = {}
    try:
        from .usage import model_stats
        stats = model_stats(store)
    except Exception:
        stats = {}
    try:
        health = store.provider_states()
    except Exception:
        health = {}
    for model_id, adapter in adapters_by_model.items():
        row = dict(stats.get(model_id) or {})
        state = health.get(adapter) or {}
        if row.get('avg_cost') is None and state.get('cost') is not None:
            row['avg_cost'] = state.get('cost')
            row['cost_basis'] = state.get('cost_basis') or 'recent runs on this runtime'
        if row.get('median_ms') is None and isinstance(state.get('latency'), (int, float)):
            row['median_ms'] = int(state['latency'] * 1000)
        # Two currencies (Forge's lesson; D-72 item 5): a Codex or Claude Code call runs on Nick's
        # subscription, so it costs nothing extra per run when ranking; its dollar figure stays
        # visible as API-equivalent effort. The plan's quota still counts: an observed quota that is
        # used up makes the model unrunnable in the ranking (as the engine's router excludes it).
        from .role_models import is_subscription
        subscription = is_subscription(adapter) or (
            state.get('cost') == 0 and str(state.get('cost_basis') or '').startswith('subscription'))
        row['marginal_cost'] = 0.0 if subscription else row.get('avg_cost')
        row['subscription'] = bool(subscription)
        from .quota import adapter_standing, runtime_of
        plan = adapter_standing(health, adapter, now) if adapter else {'level': 'unknown', 'left': None}
        if adapter and runtime_of(adapter) is None and                 isinstance(state.get('quota'), (int, float)) and not isinstance(state.get('quota'), bool):
            plan = {'level': 'exhausted' if state['quota'] <= 0 else 'unknown', 'left': state['quota'],
                    'reason': None}
        if plan.get('left') is not None:
            row['quota_left'] = plan['left']
        if plan['level'] in ('low', 'exhausted'):
            row['quota_level'] = plan['level']
            row['quota_reason'] = plan.get('reason')
        out[model_id] = row
    return out


def _evidence(store, task_class, models, now=None):
    try:
        from .routing_evidence import class_summary
        return class_summary(store, task_class, models, now=now)
    except Exception:
        return {}


def ranking(store, task_class, *, adapters, tier=None, purpose=None, set_aside=None, now=None,
            protect=True, local_only=False):
    """The ranked models for one task class here, best first, each with a plain reason.

    Entries: {model, label, rank, runnable, adapter, protected, strength, fit, why, evidence,
    measured}. `adapters` are the engine adapters that can take this step."""
    from .role_models import MODELS, STRENGTH, FALLBACKS, adapter_for, rejected, setting
    if task_class not in TASK_CLASSES:
        raise PolicyError('Unknown task class: %s' % task_class)
    tier = tier or BASE_TIER[task_class]
    purpose = purpose or CLASS_PURPOSE.get(task_class, 'text')
    role = CLASS_ROLE[task_class]
    current = setting(store, role)
    head = []
    if protect and current['mode'] in ('FIXED', 'PREFERRED') and current['model']:
        head = [current['model']]
        if current['mode'] == 'PREFERRED':
            head += [model for model in FALLBACKS.get(role, ()) if model not in head]
    entries = {}
    for model_id in MODELS:
        adapter, why_not = adapter_for(model_id, purpose, adapters, set_aside)
        refused = rejected(store, model_id, now=now)
        runnable = adapter is not None and not refused
        if local_only and runnable:
            # Every catalog model runs in the cloud (router.local_models: Kel runs no local model yet).
            refused, runnable = 'it runs in the cloud, and this work is local-only', False
        entries[model_id] = {
            'model': model_id, 'label': MODELS[model_id]['label'], 'runnable': runnable,
            'adapter': adapter if runnable else None, 'protected': model_id in head,
            'strength': STRENGTH.get(model_id, 2),
            'fit': abs(STRENGTH.get(model_id, 2) - TIER_TARGET[tier]),
            'not_here': (("can't be used: " if local_only else "can't run here: ") + refused) if refused
            else (None if adapter else why_not)}
    measured = _measured(store, {m: e['adapter'] or adapter_for(m, purpose, adapters)[0] or ''
                                 for m, e in entries.items()}, now=now)
    evidence = _evidence(store, task_class, list(entries), now=now)
    top_strength = max((e['strength'] for e in entries.values() if e['runnable'] and not e['protected']),
                       default=None)
    for model_id, entry in entries.items():
        entry['measured'] = measured.get(model_id) or {}
        entry['evidence'] = evidence.get(model_id) or {}
        level = entry['measured'].get('quota_level')
        if entry['runnable'] and level == 'exhausted':
            # D-72 item 5: $0 marginal cost never means unlimited — a used-up plan quota counts.
            entry.update(runnable=False, adapter=None,
                         not_here="can't run here right now: " + (entry['measured'].get('quota_reason') or
                                                                 "your plan's usage limit is reached"))
        effective = entry['fit']
        if entry['runnable'] and level == 'low' and not entry['protected']:
            # kel.quota: a nearly used-up plan steps one band down (never past Nick's own choice,
            # never removed); the others take the work first.
            effective += 1
            entry['quota_low'] = True
        verdict = entry['evidence'].get('verdict')
        if verdict == 'promote':
            # One band up — but an assurance binding never moves to a weaker model (doc 10 §8).
            if not (tier == 'assurance' and top_strength is not None and entry['strength'] < top_strength):
                effective = max(0, effective - 1)
                entry['promoted'] = True
        if verdict == 'demote':
            effective = 99  # steps aside for every other runnable model; never removed
            entry['demoted'] = True
        entry['effective_fit'] = effective
    head_entries = [entries[m] for m in head if m in entries]
    rest = [e for m, e in entries.items() if m not in head]

    def cost_key(entry):
        cost = entry['measured'].get('marginal_cost')
        latency = entry['measured'].get('median_ms')
        return (cost is None, cost or 0, latency is None, latency or 0)

    rest.sort(key=lambda e: (0 if e['runnable'] else 1, e['effective_fit'], bool(e.get('quota_low')),
                             cost_key(e), e['label']))
    ordered = head_entries + rest
    for index, entry in enumerate(ordered, 1):
        entry['rank'] = index
        entry['why'] = _why(entry, current, tier, role)
    return ordered


def _why(entry, current, tier, role):
    from .role_models import MODE_LABELS, ROLE_LABELS
    if not entry['runnable']:
        return '%s %s' % (entry['label'], entry['not_here'] or "can't run here")
    if entry['protected']:
        if entry['model'] == current['model']:
            return 'your %s choice for %s' % (MODE_LABELS[current['mode']].lower(), ROLE_LABELS[role])
        return 'the fallback you set for %s' % ROLE_LABELS[role]
    parts = []
    sentence = (entry.get('evidence') or {}).get('sentence')
    if entry.get('promoted'):
        parts.append('moved up: ' + (sentence or 'recent results are strong'))
    elif entry.get('demoted'):
        parts.append('moved down: ' + (sentence or 'recent results are weak'))
    if entry.get('quota_low'):
        parts.append('moved down: ' + (entry['measured'].get('quota_reason') or "its plan's usage limit is nearly used up"))
    parts.append('%s fit for %s work' % ('a close' if entry['effective_fit'] == 0 else 'a looser', tier))
    cost = entry['measured'].get('avg_cost')
    if entry['measured'].get('subscription'):
        parts.append('included in your plan' + (' (about $%.3f a run API-equivalent)' % cost
                                                 if cost is not None else ''))
    elif cost is not None:
        parts.append('about $%.3f a run' % cost)
    latency = entry['measured'].get('median_ms')
    if latency is not None:
        parts.append('usually %s' % _duration(latency))
    return '; '.join(parts)


def _duration(ms):
    seconds = ms / 1000.0
    if seconds < 90:
        return '%d s' % max(1, round(seconds))
    return '%d min' % round(seconds / 60)


def top(store, task_class, *, adapters, tier=None, purpose=None, set_aside=None, exclude=(), now=None):
    """The best runnable, unprotected-or-protected model entry for a class (None when nothing runs)."""
    for entry in ranking(store, task_class, adapters=adapters, tier=tier, purpose=purpose,
                         set_aside=set_aside, now=now):
        if entry['runnable'] and entry['model'] not in exclude:
            return entry
    return None


def overview(store, adapters):
    """The read-only per-class ranking for the engine API (`/api/model {action:'ranking'}`)."""
    from .role_models import MODE_LABELS, ROLE_LABELS, setting
    try:
        from .calibration import summary as calibration_summary
        calibrated = calibration_summary(store, live_only=True)  # advisory: shown, never ranked by
    except Exception:
        calibrated = {}
    classes = []
    for task_class in TASK_CLASSES:
        role = CLASS_ROLE[task_class]
        current = setting(store, role)
        tier = BASE_TIER[task_class]
        models = []
        for entry in ranking(store, task_class, adapters=adapters, tier=tier):
            models.append({'id': entry['model'], 'label': entry['label'], 'rank': entry['rank'],
                           'runnable': entry['runnable'], 'protected': entry['protected'],
                           'why': entry['why'], 'strength': entry['strength'],
                           'evidence': {k: entry['evidence'].get(k) for k in
                                        ('sentence', 'rate', 'samples', 'verdict')}
                           if entry['evidence'] else None,
                           'measured': entry['measured'] or None,
                           'calibration': (calibrated.get(task_class) or {}).get(entry['model'])})
        classes.append({'task_class': task_class, 'label': label(task_class), 'role': role,
                        'role_label': ROLE_LABELS[role], 'mode': current['mode'],
                        'mode_label': MODE_LABELS[current['mode']], 'tier': tier,
                        'tier_label': TIER_LABELS[tier], 'models': models})
    try:
        from .quota import plans
        plan_view = plans(store)
    except Exception:
        plan_view = []
    try:
        from .router import local_models
        local = local_models()
    except Exception:
        local = None
    return {'classes': classes, 'plans': plan_view, 'local_models': local, 'calibration_note': 'Calibration results are advisory: they are shown, never used '
                                                    'to reorder models (real reviewed outcomes are).',
            'tiers': [{'id': t, 'label': TIER_LABELS[t], 'reasoning': TIER_REASONING[t] or 'model default'}
                      for t in TIERS]}
