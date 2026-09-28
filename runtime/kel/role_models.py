"""D-67: the model each staff role starts on, changeable per role, with a real reasoning level.

Design: `docs/v2/design/D-66_WORKFORCE_LIVE.md` §2. A role setting is Fixed (exactly this model, or
the step waits with a plain reason), Preferred (this model when it is available here, else fall back
and say so) or Automatic (today's routing). The catalog maps each model to the runtime that really
runs it and to the flags that runtime really accepts — verified on the installed CLIs, never guessed:

- Claude Code 2.1.215: `--model <id|alias>`, `--fallback-model <alias>`, `--effort low|medium|high|xhigh|max`.
- Codex 0.142.5: `codex exec -m <model> -c model_reasoning_effort="<level>"`; app-server
  `thread/start {model}` (the response reports `model` and `reasoningEffort`) and
  `turn/start {effort}`; each model's supported levels come from Codex's own model catalog.
- The Anthropic API worker takes a model id and has no reasoning setting here.

"Auto" reasoning means Kel does not override the model's own default level. Nothing here decides
which model *ran* — that is recorded from what the runtime reported (`kel.staff`).
"""
import contextlib
import json
import os
import time
from pathlib import Path

from .core import PolicyError

MODES = ('FIXED', 'PREFERRED', 'AUTOMATIC')
MODE_LABELS = {'FIXED': 'Fixed', 'PREFERRED': 'Preferred', 'AUTOMATIC': 'Automatic'}
REASONING = ('auto', 'low', 'medium', 'high', 'xhigh', 'max')
REASONING_LABELS = {'auto': 'Auto', 'low': 'Low', 'medium': 'Medium', 'high': 'High',
                    'xhigh': 'Extra high', 'max': 'Max', 'ultra': 'Ultra'}

# model id -> what it is and how it runs. `arg` is what the runtime is asked for; `cli_fallback` is
# the Claude Code alias its own --fallback-model uses when the exact id is refused or overloaded.
MODELS = {
    'gpt-6-luna': {'label': 'ChatGPT Luna', 'version': 'GPT-6 Luna', 'family': 'openai',
                   'runtime': 'codex', 'arg': 'gpt-6-luna'},
    'gpt-6-astra': {'label': 'GPT-6 Astra', 'version': 'GPT-6 Astra', 'family': 'openai',
                    'runtime': 'codex', 'arg': 'gpt-6-astra'},
    'codex': {'label': 'Codex', 'version': "Codex's default model", 'family': 'openai',
              'runtime': 'codex', 'arg': None},
    'claude-opus-5-5': {'label': 'Claude Opus 5.5', 'version': 'Opus 5.5', 'family': 'anthropic',
                        'runtime': 'claude', 'arg': 'claude-opus-5-5', 'cli_fallback': 'opus'},
    'claude-fable-5-1': {'label': 'Claude Fable 5.1', 'version': 'Fable 5.1', 'family': 'anthropic',
                         'runtime': 'claude', 'arg': 'claude-fable-5-1', 'cli_fallback': 'fable'},
    'claude-sonnet': {'label': 'Claude Sonnet', 'version': 'Sonnet', 'family': 'anthropic',
                      'runtime': 'claude', 'arg': 'sonnet', 'api_arg': 'claude-sonnet-4-6'},
    'deepseek-flash': {'label': 'DeepSeek Flash', 'version': 'Flash', 'family': 'deepseek',
                       'runtime': 'deepseek', 'arg': 'deepseek-flash'},
}

# runtime -> the engine adapters that run it, per purpose ('code' repository work, 'text' writing
# or review, 'web' live web research), and its own plain name.
RUNTIMES = {
    'codex': {'label': 'Codex', 'code': 'codex-code', 'text': 'codex', 'web': None},
    'claude': {'label': 'Claude Code', 'code': 'claude-code', 'text': 'claude', 'web': None},
    'api': {'label': 'Anthropic API', 'code': None, 'text': 'internal', 'web': 'research'},
    'deepseek': {'label': 'DeepSeek API', 'code': None, 'text': None, 'web': None},
}
CLAUDE_EFFORT = ('low', 'medium', 'high', 'xhigh', 'max')
CODEX_EFFORT = ('low', 'medium', 'high', 'xhigh')  # when Codex's own catalog is unreadable

ROLES = ('kel', 'discovery', 'designer', 'builder', 'verifier', 'oracle', 'utility',
         'architect', 'sentinel', 'release')
ROLE_LABELS = {'kel': 'Kel', 'discovery': 'Discovery (research)', 'designer': 'Designer',
               'builder': 'Builder', 'verifier': 'Verifier', 'oracle': 'Oracle (second opinion)',
               'utility': 'Utility work', 'architect': 'Architect', 'sentinel': 'Sentinel',
               'release': 'Release'}
# D-67 starting models (Preferred). Builder falls back to Codex; the rest to Kel's routing.
DEFAULTS = {
    'kel': ('PREFERRED', 'gpt-6-luna', 'auto'),
    'discovery': ('PREFERRED', 'claude-sonnet', 'auto'),
    'designer': ('PREFERRED', 'claude-fable-5-1', 'auto'),
    'builder': ('PREFERRED', 'claude-opus-5-5', 'auto'),
    'verifier': ('PREFERRED', 'gpt-6-astra', 'auto'),
    'oracle': ('PREFERRED', 'gpt-6-astra', 'auto'),
    'utility': ('PREFERRED', 'deepseek-flash', 'auto'),
    'architect': ('AUTOMATIC', None, 'auto'),
    'sentinel': ('AUTOMATIC', None, 'auto'),
    'release': ('AUTOMATIC', None, 'auto'),
}
FALLBACKS = {'builder': ('codex',)}
# Independence (handoff §16): reviewers step to another family's strongest model when the preferred
# one shares the Builder's family.
INDEPENDENT = {'openai': ('gpt-6-astra', 'codex'), 'anthropic': ('claude-opus-5-5', 'claude-sonnet')}
REVIEW_ROLES = ('verifier', 'oracle', 'sentinel')
ADAPTER_FAMILIES = {'claude': 'anthropic', 'claude-code': 'anthropic', 'internal': 'anthropic',
                    'research': 'anthropic', 'codex': 'openai', 'codex-code': 'openai'}
REJECTION_HOURS = 24


def _codex_catalog():
    """Codex's own model catalog (supported and default reasoning levels), or {} when unreadable."""
    home = os.environ.get('CODEX_HOME') or os.path.join(os.path.expanduser('~'), '.codex')
    try:
        data = json.loads(Path(home, 'models_cache.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    out = {}
    for item in data.get('models') or []:
        slug = item.get('slug')
        if not slug:
            continue
        levels = [entry.get('effort') or entry.get('reasoningEffort')
                  for entry in item.get('supported_reasoning_levels') or []]
        out[slug] = {'levels': tuple(level for level in levels if level),
                     'default': item.get('default_reasoning_level')}
    return out


def reasoning_options(model_id):
    """The reasoning levels the model's runtime really accepts ('auto' always first)."""
    info = MODELS.get(model_id) or {}
    runtime = info.get('runtime')
    if runtime == 'claude':
        return ('auto',) + CLAUDE_EFFORT
    if runtime == 'codex':
        levels = (_codex_catalog().get(info.get('arg') or '') or {}).get('levels') or CODEX_EFFORT
        return ('auto',) + tuple(level for level in levels if level in REASONING_LABELS)
    return ('auto',)


def default_reasoning(model_id):
    """What 'Auto' resolves to when the runtime says (Codex's catalog), else None (runtime default)."""
    info = MODELS.get(model_id) or {}
    if info.get('runtime') == 'codex' and info.get('arg'):
        return (_codex_catalog().get(info['arg']) or {}).get('default')
    return None


def family_of_adapter(name):
    return ADAPTER_FAMILIES.get(name, name)


# ---- settings ---------------------------------------------------------------------------------

def _row(store, role):
    from .staff import ensure_schema
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM role_models WHERE role=?', (role,)).fetchone()
    return dict(row) if row else None


def setting(store, role):
    if role not in ROLES:
        raise PolicyError('Unknown staff role: %s' % role)
    mode, model, reasoning = DEFAULTS[role]
    row = _row(store, role)
    if row:
        return {'role': role, 'mode': row['mode'], 'model': row['model'],
                'reasoning': row['reasoning'] or 'auto', 'is_default': False}
    return {'role': role, 'mode': mode, 'model': model, 'reasoning': reasoning, 'is_default': True}


def set_role(store, role, mode, model=None, reasoning='auto'):
    """Nick's per-role choice (Settings). Fixed/Preferred need a catalog model; Automatic none."""
    if role not in ROLES:
        raise PolicyError('Unknown staff role: %s' % role)
    mode = str(mode or '').upper()
    if mode not in MODES:
        raise PolicyError('Choose Fixed, Preferred or Automatic.')
    reasoning = str(reasoning or 'auto').lower()
    if mode == 'AUTOMATIC':
        model = None
    elif model not in MODELS:
        raise PolicyError('That model is not one Kel can run for a role.')
    if reasoning not in REASONING:
        raise PolicyError('Choose a reasoning level: Auto, Low, Medium, High, Extra high or Max.')
    if model and reasoning not in reasoning_options(model):
        raise PolicyError('%s does not offer %s reasoning.'
                          % (MODELS[model]['label'], REASONING_LABELS[reasoning]))
    from .staff import ensure_schema
    ensure_schema(store)
    with store.transaction() as db:
        db.execute('INSERT INTO role_models(role,mode,model,reasoning,updated) VALUES(?,?,?,?,?) '
                   'ON CONFLICT(role) DO UPDATE SET mode=excluded.mode, model=excluded.model, '
                   'reasoning=excluded.reasoning, updated=excluded.updated',
                   (role, mode, model, reasoning, time.time()))
    return setting(store, role)


def reset_role(store, role):
    if role not in ROLES:
        raise PolicyError('Unknown staff role: %s' % role)
    from .staff import ensure_schema
    ensure_schema(store)
    with store.transaction() as db:
        db.execute('DELETE FROM role_models WHERE role=?', (role,))
    return setting(store, role)


# ---- availability and rejected models ----------------------------------------------------------

def rejected(store, model_id, now=None):
    """A plain reason when this model was refused by its runtime in the last day, else None."""
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='staff_model_status'").fetchone():
            return None
        row = db.execute('SELECT * FROM staff_model_status WHERE model=?', (model_id,)).fetchone()
    stamp = time.time() if now is None else now
    if row and row['status'] == 'rejected' and stamp - row['at'] < REJECTION_HOURS * 3600:
        return row['reason'] or 'its runtime refused it recently'
    return None


def adapter_for(model_id, purpose, adapters):
    """(adapter name, why-not) for running this model for a purpose with the adapters present."""
    info = MODELS.get(model_id)
    if not info:
        return None, 'is not a model Kel knows'
    runtime = info['runtime']
    if runtime == 'claude' and purpose == 'web':
        runtime = 'api'  # live web research runs on the Anthropic API worker
    name = RUNTIMES.get(runtime, {}).get(purpose)
    if runtime == 'deepseek':
        return None, 'has no DeepSeek connection in this version of Kel'
    if not name:
        return None, "can't do this kind of work here"
    if name not in adapters:
        what = RUNTIMES[runtime]['label']
        return None, ('needs %s, which is not set up on this computer' % what)
    return name, None


def model_arg(model_id, adapter):
    info = MODELS.get(model_id) or {}
    if adapter in ('internal', 'research'):
        return info.get('api_arg')
    return info.get('arg')


def effort_arg(model_id, reasoning):
    """The flag value for a reasoning level on this model's runtime (None = the model's default)."""
    if not reasoning or reasoning == 'auto':
        return None
    return reasoning if reasoning in reasoning_options(model_id) else None


# ---- resolution ----------------------------------------------------------------------------------

def resolve(store, role, *, adapters, purpose='text', avoid_family=None, now=None):
    """Resolve one staff role to what should run, with the truth of what was asked and why.

    Returns `{'role','mode','asked':{...},'adapter','model','model_arg','fallback_arg',
    'effort_arg','family','why','independence','waiting'}`. `adapter` None with `waiting` False
    means "Kel's usual routing decides" (Automatic, or a Preferred model that is not available);
    `waiting` True means a Fixed model cannot run here and the step must wait with `why`.
    """
    current = setting(store, role)
    asked = {'role': role, 'mode': current['mode'], 'model': current['model'],
             'label': (MODELS.get(current['model']) or {}).get('label'),
             'reasoning': current['reasoning']}
    out = {'role': role, 'mode': current['mode'], 'asked': asked, 'adapter': None, 'model': None,
           'model_arg': None, 'fallback_arg': None, 'effort_arg': None, 'family': None,
           'why': None, 'independence': None, 'waiting': False}
    if current['mode'] == 'AUTOMATIC':
        out['why'] = 'Automatic: Kel chose by health, capability and cost'
        return out
    order = [current['model']]
    if current['mode'] == 'PREFERRED':
        order += [model for model in FALLBACKS.get(role, ()) if model not in order]
    if role in REVIEW_ROLES and current['mode'] == 'PREFERRED':
        # D-69: a reviewer (and the Oracle) always gets a model when any can run: another family
        # than the Builder first, then the Builder's own family with the reduced independence
        # recorded (coverage debt, workforce-os doc 10 §3).
        alternates = [model for models in INDEPENDENT.values() for model in models] + \
            [model for model in MODELS if model not in order]
        candidates = list(dict.fromkeys(order + alternates))
        if avoid_family:
            different = [m for m in candidates if MODELS[m]['family'] != avoid_family]
            same = [m for m in candidates if MODELS[m]['family'] == avoid_family]
            candidates = different + same
        order = candidates
    skipped = []
    for model_id in order:
        adapter, why_not = adapter_for(model_id, purpose, adapters)
        if adapter is None:
            skipped.append('%s %s' % ((MODELS.get(model_id) or {}).get('label', model_id), why_not))
            continue
        reason = rejected(store, model_id, now=now)
        if reason:
            skipped.append('%s was refused recently (%s)' % (MODELS[model_id]['label'], reason))
            continue
        info = MODELS[model_id]
        out.update(adapter=adapter, model=model_id, model_arg=model_arg(model_id, adapter),
                   fallback_arg=info.get('cli_fallback') if adapter in ('claude', 'claude-code') else None,
                   effort_arg=effort_arg(model_id, current['reasoning']), family=info['family'])
        if model_id != current['model']:
            preferred = MODELS.get(current['model']) or {}
            if role in REVIEW_ROLES and avoid_family and preferred.get('family') == avoid_family \
                    and info['family'] != avoid_family:
                skipped.insert(0, '%s is from the same model family as the Builder, so %s reviews '
                                  'instead' % (preferred.get('label', current['model']), info['label']))
            out['why'] = '; '.join(skipped) or ('%s was chosen instead' % info['label'])
        if role in REVIEW_ROLES and avoid_family:
            out['independence'] = 'different' if info['family'] != avoid_family else 'reduced'
            if out['independence'] == 'reduced' and not out['why']:
                out['why'] = ('no model from another family is available, so the review is '
                              'less independent')
        return out
    if current['mode'] == 'FIXED':
        out.update(waiting=True, why='; '.join(skipped))
        return out
    out['why'] = '; '.join(skipped) + '; Kel used its usual routing instead'
    return out


def describe_model(model_id=None, adapter=None, raw=None):
    """Plain label/version for a model that ran (catalog id, runtime-reported id, or unknown)."""
    if model_id in MODELS:
        return MODELS[model_id]['label'], MODELS[model_id]['version']
    text = str(raw or model_id or '').strip().split('[')[0]
    if not text:
        return None, None
    for info in MODELS.values():
        if (info.get('arg') and text == info['arg']) or info.get('api_arg') == text:
            return info['label'], info['version']
    lowered = text.lower()
    if lowered.startswith('claude-'):
        parts = lowered.split('-')
        name = parts[1].capitalize() if len(parts) > 1 else 'Claude'
        numbers = [p for p in parts[2:] if p.isdigit()]
        version = '.'.join(numbers[:2]) if numbers else ''
        return ('Claude %s %s' % (name, version)).strip(), (name + (' ' + version if version else ''))
    if lowered.startswith('gpt-'):
        pretty = text.upper().replace('GPT-', 'GPT-', 1)
        return pretty, pretty
    return text, text


def listing(store, adapters):
    """Every role row for Settings, with the choosable models and whether each can run here."""
    rows = []
    for role in ROLES:
        current = setting(store, role)
        purpose = 'code' if role == 'builder' else 'text'
        available, note = True, None
        if current['model']:
            adapter, why_not = adapter_for(current['model'], purpose, adapters)
            if adapter is None and purpose == 'code':
                adapter, why_not = adapter_for(current['model'], 'text', adapters)
            available = adapter is not None
            note = None if available else '%s %s' % (MODELS[current['model']]['label'], why_not)
        default_mode, default_model, default_reasoning_level = DEFAULTS[role]
        rows.append({'role': role, 'label': ROLE_LABELS[role], 'mode': current['mode'],
                     'mode_label': MODE_LABELS[current['mode']], 'model': current['model'],
                     'model_label': (MODELS.get(current['model']) or {}).get('label'),
                     'reasoning': current['reasoning'],
                     'reasoning_label': REASONING_LABELS.get(current['reasoning']),
                     'reasoning_options': list(reasoning_options(current['model']))
                     if current['model'] else ['auto'],
                     'available': available, 'note': note, 'is_default': current['is_default'],
                     'fallbacks': [MODELS[m]['label'] for m in FALLBACKS.get(role, ())],
                     'default': {'mode': default_mode, 'model': default_model,
                                 'reasoning': default_reasoning_level}})
    models = []
    for model_id, info in MODELS.items():
        adapter, why_not = adapter_for(model_id, 'text', adapters)
        if adapter is None and info['runtime'] in ('claude', 'codex'):
            adapter, why_not = adapter_for(model_id, 'code', adapters)
        models.append({'id': model_id, 'label': info['label'], 'version': info['version'],
                       'runtime': RUNTIMES[info['runtime']]['label'],
                       'available': adapter is not None,
                       'note': None if adapter else '%s %s' % (info['label'], why_not),
                       'reasoning_options': list(reasoning_options(model_id))})
    return {'roles': rows, 'models': models, 'modes': [
        {'id': mode, 'label': MODE_LABELS[mode]} for mode in MODES]}
