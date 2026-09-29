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
import re
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
    'deepseek-flash': {'label': 'DeepSeek Flash', 'version': 'V4.1 Flash', 'family': 'deepseek',
                       'runtime': 'deepseek', 'arg': 'deepseek-flash',
                       'openrouter_arg': 'deepseek/deepseek-v4.1-flash'},
}

# Routing 2 (ROUTING_2.md §5.1): a coarse strength per model (1 fast and cheap, 2 balanced, 3 the
# strongest) that dispatch tiers aim at, and a list price in USD per million tokens (input, cached
# input, output) used only to *estimate* a run's cost when its runtime reports tokens but no cost.
# Sources, read 2026-09-27: DeepSeek's own pricing page (peak rates) and OpenRouter's public model
# list. None = no published price Kel can rely on (the cost stays unknown, never "free").
PRICES = {'gpt-6-luna': (0.10, 0.01, 0.50), 'gpt-6-astra': (10.0, 1.0, 50.0),
          'claude-opus-5-5': (4.0, 0.20, 20.0), 'claude-fable-5-1': (10.0, 0.25, 50.0),
          'deepseek-flash': (0.30, 0.006, 1.20), 'codex': None, 'claude-sonnet': None}
PRICE_SOURCE = 'list price (DeepSeek pricing page, OpenRouter model list), read 2026-09-27'
# D-72 item 3: strength ranks start from the list-price estimate (output price per million tokens:
# under $5 → 1, under $15 → 2, else 3); a model with no published price is "balanced" (2). Outcome
# evidence then moves a model within its class ranking (`task_routing`, promote / demote) — the
# starting rank itself is never rewritten.
STRENGTH_BANDS = ((5.0, 1), (15.0, 2))
UNPRICED_STRENGTH = 2


def strength_from_price(model_id):
    """The starting strength rank (1–3) a model's list price implies (D-72 item 3)."""
    price = PRICES.get(model_id)
    if not price:
        return UNPRICED_STRENGTH
    for ceiling, rank in STRENGTH_BANDS:
        if price[2] < ceiling:
            return rank
    return 3


STRENGTH = {model_id: strength_from_price(model_id) for model_id in PRICES}

# runtime -> the engine adapters that run it, per purpose ('code' repository work, 'text' writing
# or review, 'web' live web research), and its own plain name.
RUNTIMES = {
    # D-74.1: the coding runtimes search the web themselves on Nick's subscriptions (Codex
    # `web_search="live"`, Claude Code's WebSearch/WebFetch tools), so research needs no API key.
    'codex': {'label': 'Codex', 'code': 'codex-code', 'text': 'codex', 'web': 'codex-web'},
    'claude': {'label': 'Claude Code', 'code': 'claude-code', 'text': 'claude', 'web': 'claude-web'},
    'api': {'label': 'Anthropic API', 'code': None, 'text': 'internal', 'web': 'research'},
    'deepseek': {'label': 'DeepSeek API', 'code': None, 'text': 'deepseek', 'web': None},
}
# Routing 2 §5.6: OpenRouter is a second route to catalog models that name an `openrouter_arg`.
# D-72 item 4: for now that is DeepSeek Flash only (one catalog model names an `openrouter_arg`,
# and the OpenRouter worker refuses any other model id).
OPENROUTER = 'openrouter'
# D-72 item 5: Codex and Claude Code run on Nick's subscriptions — their calls cost nothing extra per
# run when Kel ranks models (the dollar figure they report is API-equivalent effort, shown as
# "included in your plan"); the plan's quota still counts.
SUBSCRIPTION_ADAPTERS = ('codex', 'codex-code', 'codex-web', 'claude', 'claude-code', 'claude-web')


def is_subscription(adapter):
    return adapter in SUBSCRIPTION_ADAPTERS
CLAUDE_EFFORT = ('low', 'medium', 'high', 'xhigh', 'max')
CODEX_EFFORT = ('low', 'medium', 'high', 'xhigh')  # when Codex's own catalog is unreadable

# D-88: the Writer (all writing that was the Builder's, D-69.4 superseded) and the Animator (motion).
ROLES = ('kel', 'discovery', 'designer', 'writer', 'builder', 'animator', 'verifier', 'oracle',
         'utility', 'architect', 'sentinel', 'release')
ROLE_LABELS = {'kel': 'Kel', 'discovery': 'Discovery (research)', 'designer': 'Designer',
               'writer': 'Writer', 'builder': 'Builder', 'animator': 'Animator',
               'verifier': 'Verifier', 'oracle': 'Oracle (second opinion)',
               'utility': 'Utility work', 'architect': 'Architect', 'sentinel': 'Sentinel',
               'release': 'Release'}
# D-67 starting models (Preferred). Builder falls back to Codex; the rest to Kel's routing.
DEFAULTS = {
    'kel': ('PREFERRED', 'gpt-6-luna', 'auto'),
    'discovery': ('PREFERRED', 'claude-sonnet', 'auto'),
    'designer': ('PREFERRED', 'claude-fable-5-1', 'auto'),
    'builder': ('PREFERRED', 'claude-opus-5-5', 'auto'),
    # D-88: Writer on Fable 5.1 (Opus 5.5 fallback); Animator on Opus 5.5 at High (motion is exact
    # numeric work and interruption logic), Codex as its fallback; Astra reviews both as the Verifier.
    'writer': ('PREFERRED', 'claude-fable-5-1', 'auto'),
    'animator': ('PREFERRED', 'claude-opus-5-5', 'high'),
    'verifier': ('PREFERRED', 'gpt-6-astra', 'auto'),
    'oracle': ('PREFERRED', 'gpt-6-astra', 'auto'),
    'utility': ('PREFERRED', 'deepseek-flash', 'auto'),
    'architect': ('AUTOMATIC', None, 'auto'),
    'sentinel': ('AUTOMATIC', None, 'auto'),
    'release': ('AUTOMATIC', None, 'auto'),
}
FALLBACKS = {'builder': ('codex',), 'writer': ('claude-opus-5-5',), 'animator': ('codex',)}
# Independence (handoff §16): reviewers step to another family's strongest model when the preferred
# one shares the Builder's family.
INDEPENDENT = {'openai': ('gpt-6-astra', 'codex'), 'anthropic': ('claude-opus-5-5', 'claude-sonnet')}
REVIEW_ROLES = ('verifier', 'oracle', 'sentinel')
ADAPTER_FAMILIES = {'claude': 'anthropic', 'claude-code': 'anthropic', 'internal': 'anthropic',
                    'research': 'anthropic', 'claude-web': 'anthropic', 'codex': 'openai', 'codex-code': 'openai',
                    'codex-web': 'openai',
                    # OpenRouter only routes DeepSeek Flash today (ROUTING_2.md "Needs Nick" 5).
                    'deepseek': 'deepseek', 'openrouter': 'deepseek'}
REJECTION_HOURS = 24
# LIVE-3: the work a role exists for. A model that can't do it is not offered for that role.
ROLE_PURPOSE = {'builder': 'code', 'animator': 'code', 'discovery': 'web'}
PURPOSE_WORDS = {'code': ("can't change code", "the Builder's code work"),
                 'web': ("can't search the web", "Discovery's research")}


def capable(model_id, purpose):
    """(True, None) when this model can do this kind of work anywhere Kel runs it, else
    (False, plain reason). Independent of what is installed here (that is `adapter_for`)."""
    info = MODELS.get(model_id)
    if not info:
        return False, 'is not a model Kel knows'
    if purpose in ('code', 'web') and info['runtime'] not in ('claude', 'codex'):
        cannot, work = PURPOSE_WORDS[purpose]
        return False, "%s %s, so it can't do %s" % (info['label'], cannot, work)
    return True, None


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
    if model and mode == 'FIXED' and ROLE_PURPOSE.get(role):
        able, why_not = capable(model, ROLE_PURPOSE[role])
        if not able:
            # LIVE-3: Fixed means "only this model" — one that can't do the role's work would leave
            # every step of it waiting for ever.
            raise PolicyError(why_not[:1].upper() + why_not[1:] + '. Choose another model, or Preferred.')
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

# What a runtime's refusal of a model means, in plain words (the live check: Codex answered HTTP 400
# "The 'gpt-6-luna' model is not supported when using Codex with a ChatGPT account" and "The
# 'gpt-6-astra' model requires a newer version of Codex"). Order matters: the first match wins.
_REFUSALS = (
    ('runtime_old', re.compile(r'requires? a newer version|newer version of (?:codex|claude)|upgrade to the '
                               r'latest|please (?:upgrade|update) (?:codex|claude|the cli)|cli (?:is )?too old',
                               re.IGNORECASE)),
    ('account', re.compile(r'not supported (?:when|with|for) (?:using )?(?:codex )?(?:with )?(?:a |your )?'
                           r'(?:chatgpt|plan|account|subscription)|not (?:available|supported) (?:on|for|with) '
                           r'(?:your|this) (?:plan|account|subscription)|(?:plan|account|subscription) does not '
                           r'(?:include|support|allow)', re.IGNORECASE)),
    ('no_access', re.compile(r'(?:no|not have|lacks?) access to (?:the |this )?model|model[^.]{0,60}\b(?:not '
                             r'allowed|access denied|permission denied)', re.IGNORECASE)),
    ('not_found', re.compile(r'(?:model|model_id)\b.{0,80}\b(?:not found|not supported|not available|does not '
                             r"exist|not exist|unknown|invalid|isn't available|is not available|unsupported|not "
                             r'recognized)|\b(?:unknown|invalid|unsupported) model\b|model_not_found',
                             re.IGNORECASE)),
)
RUNTIME_NAMES = {'codex': 'Codex', 'claude': 'Claude Code', 'api': 'the Anthropic API',
                 'deepseek': 'the DeepSeek API'}


def classify_refusal(error, model_id=None):
    """(kind, plain reason) when `error` is a runtime refusing the model, else None."""
    text = str(error or '')
    if not text:
        return None
    runtime = RUNTIME_NAMES.get((MODELS.get(model_id) or {}).get('runtime'), 'its runtime')
    for kind, pattern in _REFUSALS:
        if pattern.search(text):
            if kind == 'runtime_old':
                return kind, 'the %s on this computer is too old for it (update %s)' % (runtime, runtime)
            if kind == 'account':
                return kind, ("your ChatGPT account doesn't offer it in Codex" if runtime == 'Codex'
                              else "your account doesn't offer it in %s" % runtime)
            if kind == 'no_access':
                return kind, "your account doesn't have access to it"
            return kind, '%s does not know this model' % runtime
    return None


def _ensure_status_columns(db):
    columns = {row[1] for row in db.execute('PRAGMA table_info(staff_model_status)')}
    for name in ('kind', 'runtime_version'):
        if columns and name not in columns:
            db.execute('ALTER TABLE staff_model_status ADD COLUMN %s TEXT' % name)


def note_refusal(store, model_id, error, runtime_version=None, db=None):
    """Remember that a runtime refused this model, with its plain reason (True when it was one).

    Recorded at the first refusal from any call site, so the same model is not tried again: a
    runtime-too-old refusal lasts until that runtime's version changes, the others for a day."""
    if not model_id or model_id not in MODELS:
        return False
    found = classify_refusal(error, model_id)
    if not found:
        return False
    kind, reason = found

    def write(conn):
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='staff_model_status'").fetchone():
            return False
        _ensure_status_columns(conn)
        conn.execute('INSERT INTO staff_model_status(model,status,reason,at,kind,runtime_version) '
                     'VALUES(?,?,?,?,?,?) ON CONFLICT(model) DO UPDATE SET status=excluded.status, '
                     'reason=excluded.reason, at=excluded.at, kind=excluded.kind, '
                     'runtime_version=excluded.runtime_version',
                     (model_id, 'rejected', reason, time.time(), kind, runtime_version))
        return True

    if db is not None:
        return write(db)
    from .staff import ensure_schema
    ensure_schema(store)
    with store.transaction() as conn:
        return write(conn)


def _current_runtime_version(model_id):
    runtime = (MODELS.get(model_id) or {}).get('runtime')
    if runtime not in ('codex', 'claude'):
        return None
    try:
        from .native import runtime_version
        return runtime_version(runtime)
    except Exception:
        return None


def rejected(store, model_id, now=None):
    """A plain reason when this model's runtime refused it (and the refusal still applies), else None.

    Also reads Codex's own model list for this account (`~/.codex/models_cache.json`) when it was
    fetched by the very Codex version Kel runs: a model missing from it is not offered here."""
    with contextlib.closing(store.connect()) as db:
        row = None
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='staff_model_status'").fetchone():
            row = db.execute('SELECT * FROM staff_model_status WHERE model=?', (model_id,)).fetchone()
    stamp = time.time() if now is None else now
    if row and row['status'] == 'rejected':
        row = dict(row)
        current = _current_runtime_version(model_id) if row.get('runtime_version') else None
        if current and current != row['runtime_version']:
            # Another runtime version (an updated CLI) gets to try the model again: the live check's
            # "not supported with a ChatGPT account" came from an old Codex, not from the account.
            pass
        elif row.get('kind') == 'runtime_old' and row.get('runtime_version'):
            return row['reason']
        elif stamp - row['at'] < REJECTION_HOURS * 3600:
            return row['reason'] or 'its runtime refused it recently'
    offered = codex_offers(model_id)
    if offered is False:
        return "the Codex on this computer doesn't list it for your account"
    return None


_CACHE_READ = {}


def _models_cache():
    """Codex's `models_cache.json` (parsed once per file change), or None."""
    home = os.environ.get('CODEX_HOME') or os.path.join(os.path.expanduser('~'), '.codex')
    path = Path(home, 'models_cache.json')
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    cached = _CACHE_READ.get(str(path))
    if cached and cached[0] == stamp:
        return cached[1]
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    _CACHE_READ[str(path)] = (stamp, data if isinstance(data, dict) else None)
    return _CACHE_READ[str(path)][1]


def codex_offers(model_id):
    """True / False when Codex's cached model list (fetched by the same Codex version Kel runs) says
    whether it offers this model; None when that list is missing, stale for this version, or the
    model is not a Codex model."""
    info = MODELS.get(model_id) or {}
    if info.get('runtime') != 'codex' or not info.get('arg'):
        return None
    data = _models_cache()
    if data is None:
        return None
    try:
        from .native import codex_executable, parse_version
        running = parse_version(codex_executable().get('version'))
    except Exception:
        running = None
    fetched_by = None
    try:
        from .native import parse_version as _parse
        fetched_by = _parse(data.get('client_version'))
    except Exception:
        fetched_by = None
    if not running or not fetched_by or running[:3] != fetched_by[:3]:
        return None  # another Codex (the desktop app) fetched it; its list says nothing about ours
    slugs = {item.get('slug') for item in data.get('models') or [] if isinstance(item, dict)}
    return info['arg'] in slugs


def adapter_for(model_id, purpose, adapters, set_aside=None):
    """(adapter name, why-not) for running this model for a purpose with the adapters present.

    `set_aside` ({adapter: plain reason}) names runtimes that are installed but not offered for
    this step (e.g. the engine's provider diversity after two failed tries) — so the reason says
    that, never "not set up on this computer" for a runtime that is set up (the live check)."""
    info = MODELS.get(model_id)
    if not info:
        return None, 'is not a model Kel knows'
    runtime = info['runtime']
    name = RUNTIMES.get(runtime, {}).get(purpose)
    if runtime == 'claude' and purpose == 'web' and name not in adapters and 'research' in adapters:
        runtime, name = 'api', 'research'  # the Anthropic API worker's own web search
    if name and name not in adapters and info.get('openrouter_arg') and OPENROUTER in adapters             and not (set_aside and OPENROUTER in set_aside):
        return OPENROUTER, None  # the same model through OpenRouter (Routing 2 §5.6)
    if runtime == 'deepseek' and name and name not in adapters:
        if set_aside and name in set_aside:
            return None, 'runs on the DeepSeek API, which %s' % set_aside[name]
        return None, 'needs a DeepSeek API key (or an OpenRouter key), which is not set up on this computer'
    if not name:
        return None, "can't do this kind of work here"
    if name not in adapters:
        what = RUNTIMES[runtime]['label']
        if set_aside and name in set_aside:
            return None, 'runs on %s, which %s' % (what, set_aside[name])
        return None, ('needs %s, which is not set up on this computer' % what)
    return name, None


# The adapters whose calls apply a per-model overlay (kel.native, kel.api_models), and the runtime
# kel.overlays keys it by. The coding bridge and the Anthropic API worker do not apply overlays yet,
# so nothing is recorded for them.
OVERLAY_RUNTIME = {'codex': 'codex', 'codex-web': 'codex', 'claude': 'claude', 'claude-web': 'claude',
                   'deepseek': 'deepseek', 'openrouter': 'openrouter'}


def plan_used_up(store, adapter, now=None):
    """The plain reason when the subscription plan behind this adapter is used up now (kel.quota),
    else None. A plan's limit resets on its own; unknown is never "used up"."""
    try:
        from .quota import adapter_standing
        view = adapter_standing(store.provider_states(), adapter, now)
    except Exception:
        return None
    return (view.get('reason') or "your plan's usage limit is reached") if view.get('level') == 'exhausted' else None


def model_arg(model_id, adapter):
    info = MODELS.get(model_id) or {}
    if adapter in ('internal', 'research'):
        return info.get('api_arg')
    if adapter == OPENROUTER:
        return info.get('openrouter_arg')
    return info.get('arg')


def effort_arg(model_id, reasoning):
    """The flag value for a reasoning level on this model's runtime (None = the model's default)."""
    if not reasoning or reasoning == 'auto':
        return None
    return reasoning if reasoning in reasoning_options(model_id) else None


# ---- resolution ----------------------------------------------------------------------------------

def resolve(store, role, *, adapters, purpose='text', avoid_family=None, now=None, exclude=(),
            set_aside=None, task_class=None, tier=None):
    """Resolve one staff role to what should run, with the truth of what was asked and why.

    Returns `{'role','mode','asked':{...},'adapter','model','model_arg','fallback_arg',
    'effort_arg','family','why','independence','waiting'}`. `adapter` None with `waiting` False
    means "Kel's usual routing decides" (Automatic without a task class, or nothing it ranked can
    run); `waiting` True means a Fixed model cannot run here and the step must wait with `why`.
    `exclude` names models already tried for this call (a review hands over to the next one);
    `set_aside` is passed to `adapter_for`. With a `task_class` (Routing 2 §5.1) the class's ranked
    list decides what Automatic picks and where a Preferred model falls back to, and `tier` sets the
    reasoning level of a role whose reasoning is Auto.
    """
    current = setting(store, role)
    asked = {'role': role, 'mode': current['mode'], 'model': current['model'],
             'label': (MODELS.get(current['model']) or {}).get('label'),
             'reasoning': current['reasoning']}
    out = {'role': role, 'mode': current['mode'], 'asked': asked, 'adapter': None, 'model': None,
           'model_arg': None, 'fallback_arg': None, 'effort_arg': None, 'family': None,
           'why': None, 'independence': None, 'waiting': False}
    ranked = None
    if task_class:
        from .task_routing import BASE_TIER, ranking
        tier = tier or BASE_TIER.get(task_class)
        asked.update(task_class=task_class, dispatch=tier)
        try:
            ranked = ranking(store, task_class, adapters=adapters, tier=tier, purpose=purpose,
                             set_aside=set_aside, now=now, protect=False)
        except Exception:
            ranked = None
    ranked_why = {entry['model']: entry['why'] for entry in ranked or ()}
    if ranked:
        # Every routing change is recorded with its plain reason (Routing 2 §5.3): the top of the
        # class's ranking as it stood when this call was resolved.
        asked['ranking'] = [{'model': entry['model'], 'why': entry['why']}
                            for entry in ranked if entry['runnable']][:4]
    ranked_order = [entry['model'] for entry in ranked or () if entry['runnable']]
    if current['mode'] == 'AUTOMATIC':
        if not ranked:
            out['why'] = 'Automatic: Kel chose by health, capability and cost'
            return out
        order = list(ranked_order)
    else:
        order = [current['model']]
        if current['mode'] == 'PREFERRED':
            order += [model for model in FALLBACKS.get(role, ()) if model not in order]
            if ranked and role not in REVIEW_ROLES:
                order += [model for model in ranked_order if model not in order]
    if role in REVIEW_ROLES and current['mode'] in ('PREFERRED', 'AUTOMATIC') and \
            (current['mode'] == 'PREFERRED' or ranked):
        # D-69: a reviewer (and the Oracle) always gets a model when any can run: another family
        # than the Builder first, then the Builder's own family with the reduced independence
        # recorded (coverage debt, workforce-os doc 10 §3).
        alternates = [model for models in INDEPENDENT.values() for model in models] + \
            (ranked_order if ranked else [model for model in MODELS if model not in order])
        if current['mode'] == 'AUTOMATIC':
            alternates = ranked_order
        candidates = list(dict.fromkeys(order + alternates))
        if avoid_family:
            different = [m for m in candidates if MODELS[m]['family'] != avoid_family]
            same = [m for m in candidates if MODELS[m]['family'] == avoid_family]
            candidates = different + same
        order = candidates
    skipped = []
    for model_id in order:
        label = (MODELS.get(model_id) or {}).get('label', model_id)
        if model_id in (exclude or ()):
            skipped.append('%s did not run for this call' % label)
            continue
        # A refusal is the truest reason (the runtime said so), so it is checked first.
        reason = rejected(store, model_id, now=now) if model_id in MODELS else None
        if reason:
            skipped.append("%s can't run here: %s" % (label, reason))
            continue
        adapter, why_not = adapter_for(model_id, purpose, adapters, set_aside)
        if adapter is None:
            skipped.append('%s %s' % (label, why_not))
            continue
        used_up = plan_used_up(store, adapter, now)
        if used_up:
            skipped.append("%s can't run right now: %s" % (label, used_up))
            continue
        info = MODELS[model_id]
        asked['resolved'] = model_id
        effort = effort_arg(model_id, current['reasoning'])
        if (current['reasoning'] or 'auto') == 'auto' and tier:
            from .task_routing import reasoning_for
            effort = reasoning_for(tier, model_id)
            asked['reasoning_source'] = 'tier'
        out.update(adapter=adapter, model=model_id, model_arg=model_arg(model_id, adapter),
                   fallback_arg=info.get('cli_fallback') if adapter in ('claude', 'claude-code') else None,
                   effort_arg=effort, family=info['family'])
        try:
            # workforce-os doc 10 §4: the per-model overlay (key and version) that applies to this
            # binding is recorded with the routing decision. None registered means nothing recorded.
            from .overlays import lookup, record_of
            overlay = record_of(lookup(OVERLAY_RUNTIME[adapter], model_id)) if adapter in OVERLAY_RUNTIME else None
        except Exception:
            overlay = None
        if overlay:
            asked['overlay'] = overlay
            out['overlay'] = overlay
        if current['mode'] == 'AUTOMATIC':
            out['why'] = 'Automatic: ' + (ranked_why.get(model_id) or 'the top of Kel\'s ranking')
            if skipped:
                out['why'] += ' (' + '; '.join(skipped) + ')'
        elif model_id != current['model']:
            preferred = MODELS.get(current['model']) or {}
            if role in REVIEW_ROLES and avoid_family and preferred.get('family') == avoid_family \
                    and info['family'] != avoid_family:
                skipped.insert(0, '%s is from the same model family as the Builder, so %s reviews '
                                  'instead' % (preferred.get('label', current['model']), info['label']))
            if ranked and model_id not in FALLBACKS.get(role, ()) and role not in REVIEW_ROLES:
                skipped.append('Kel picked %s next by its ranking for %s work (%s)'
                               % (info['label'], task_class.replace('_', ' '), ranked_why.get(model_id)))
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
    if current['mode'] == 'AUTOMATIC':
        out['why'] = 'Automatic: no ranked model can run this here' + \
            ((' (' + '; '.join(skipped) + ')') if skipped else '') + '; Kel used its usual routing instead'
        return out
    out['why'] = '; '.join(skipped) + '; Kel used its usual routing instead'
    return out


def catalog_id(raw, adapter=None):
    """The catalog model a runtime-reported id stands for ('claude-opus-5-5[1m]' → 'claude-opus-5-5',
    'sonnet' → 'claude-sonnet'); a Codex run with no model named ran Codex's default ('codex');
    None when it is not a catalog model."""
    text = str(raw or '').strip().split('[')[0].lower()
    if not text:
        return 'codex' if adapter in ('codex', 'codex-code', 'codex-web') else None
    if text in MODELS:
        return text
    for model_id, info in MODELS.items():
        if text in {str(info.get('arg') or '').lower(), str(info.get('api_arg') or '').lower()} - {''}:
            return model_id
    for model_id in MODELS:
        if text.startswith(model_id + '-') or text.startswith(model_id + '@'):
            return model_id  # a dated or suffixed variant of a catalog model
    if 'sonnet' in text and text.startswith('claude'):
        return 'claude-sonnet'
    return None


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


def last_runs(store):
    """{role: what its last run asked for and what actually ran} — for "fell back to X last time".

    Staff roles read their newest staff call (the model the runtime confirmed, else the one Kel
    resolved to); Kel reads its newest own call in the usage record (D-72 item 6). `fell_back` is
    True only when a model was asked for and a different one ran."""
    out = {}
    try:
        with contextlib.closing(store.connect()) as db:
            found = db.execute("SELECT 1 FROM sqlite_master WHERE name='staff_calls'").fetchone()
            rows = db.execute('SELECT role, asked, ran, why, started FROM staff_calls ORDER BY started DESC').fetchall() \
                if found else []
    except Exception:
        rows = []
    for row in rows:
        role = row['role']
        if role in out or role not in ROLES:
            continue
        try:
            asked, ran = json.loads(row['asked'] or '{}'), json.loads(row['ran'] or '{}')
        except (TypeError, ValueError):
            continue
        confirmed = bool(ran.get('model_confirmed') and ran.get('model'))
        ran_model = catalog_id(ran.get('model'), ran.get('adapter')) if confirmed else asked.get('resolved')
        out[role] = _last_entry(asked.get('model'), ran_model, confirmed, row['started'], row['why'])
    try:
        from .usage import rows as usage_rows
        kel = [i for i in usage_rows(store) if i.get('role') == 'kel' and i.get('model')]
    except Exception:
        kel = []
    if kel:
        item = max(kel, key=lambda i: i.get('at') or 0)
        out['kel'] = _last_entry(item.get('asked_model'), item.get('model'), True, item.get('at'), item.get('why'))
    return out


def _last_entry(asked, ran, confirmed, at, why):
    label = lambda model_id: (MODELS.get(model_id) or {}).get('label') if model_id else None  # noqa: E731
    fell_back = bool(asked and ran and asked != ran)
    return {'asked': asked, 'asked_label': label(asked), 'ran': ran, 'ran_label': label(ran),
            'confirmed': confirmed, 'fell_back': fell_back, 'at': at, 'why': why if fell_back else None}


def _role_option(store, model_id, purpose, adapters):
    """(available, note) for one model in one role's picker: can it do the role's work, and here?"""
    info = MODELS[model_id]
    able, why_not = capable(model_id, purpose)
    if not able:
        return False, why_not
    refused = rejected(store, model_id)
    if refused:
        # The live check: a runtime that refuses the model is the truth, whatever is installed.
        return False, "%s can't run here: %s" % (info['label'], refused)
    adapter, why_not = adapter_for(model_id, purpose, adapters)
    if adapter is None:
        return False, '%s %s' % (info['label'], why_not)
    used_up = plan_used_up(store, adapter)
    if used_up:
        return False, "%s can't run right now: %s" % (info['label'], used_up)
    return True, None


def listing(store, adapters):
    """Every role row for Settings, with the choosable models and whether each can run here.

    LIVE-3: availability is per role — a model that can't do a role's work (DeepSeek Flash as the
    Builder for code, a model with no web search as Discovery) is unavailable for that role, with
    the reason, in the row (`available`, `note`) and in the role's own picker (`model_options`)."""
    rows = []
    last = last_runs(store)
    for role in ROLES:
        current = setting(store, role)
        purpose = ROLE_PURPOSE.get(role, 'text')
        available, note = True, None
        if current['model']:
            available, note = _role_option(store, current['model'], purpose, adapters)
            if not available and current['mode'] == 'PREFERRED' and FALLBACKS.get(role):
                note += '; Kel uses %s instead' % ', then '.join(MODELS[m]['label'] for m in FALLBACKS[role])
        elif purpose == 'web' and not any(_role_option(store, m, 'web', adapters)[0] for m in MODELS):
            # D-74.1: Automatic research with no web route at all says so plainly.
            available, note = False, ('No model here can search the web: Kel needs Claude Code or Codex '
                                      'signed in on this computer, or an Anthropic API key.')
        options = []
        for model_id, info in MODELS.items():
            ok, why = _role_option(store, model_id, purpose, adapters)
            options.append({'id': model_id, 'label': info['label'], 'available': ok, 'note': why})
        default_mode, default_model, default_reasoning_level = DEFAULTS[role]
        rows.append({'role': role, 'label': ROLE_LABELS[role], 'mode': current['mode'],
                     'mode_label': MODE_LABELS[current['mode']], 'model': current['model'],
                     'model_label': (MODELS.get(current['model']) or {}).get('label'),
                     'reasoning': current['reasoning'],
                     'reasoning_label': REASONING_LABELS.get(current['reasoning']),
                     'reasoning_options': list(reasoning_options(current['model']))
                     if current['model'] else ['auto'],
                     'available': available, 'note': note, 'is_default': current['is_default'],
                     'purpose': purpose, 'model_options': options,
                     'fallbacks': [MODELS[m]['label'] for m in FALLBACKS.get(role, ())],
                     'last_run': last.get(role),
                     'default': {'mode': default_mode, 'model': default_model,
                                 'reasoning': default_reasoning_level}})
    models = []
    for model_id, info in MODELS.items():
        adapter, why_not = adapter_for(model_id, 'text', adapters)
        if adapter is None and info['runtime'] in ('claude', 'codex'):
            adapter, why_not = adapter_for(model_id, 'code', adapters)
        refused = rejected(store, model_id)
        models.append({'id': model_id, 'label': info['label'], 'version': info['version'],
                       'runtime': RUNTIMES[info['runtime']]['label'],
                       'available': adapter is not None and not refused,
                       'note': ("%s can't run here: %s" % (info['label'], refused)) if refused else
                       (None if adapter else '%s %s' % (info['label'], why_not)),
                       'reasoning_options': list(reasoning_options(model_id)),
                       'runtime_version': _current_runtime_version(model_id)})
    try:
        from .quota import plans
        plan_view = plans(store)  # how much of each subscription plan is used, and how fast
    except Exception:
        plan_view = []
    try:
        from .router import local_models
        local = local_models()  # which local models exist here (none can run in Kel yet)
    except Exception:
        local = None
    return {'roles': rows, 'models': models, 'plans': plan_view, 'local_models': local, 'modes': [
        {'id': mode, 'label': MODE_LABELS[mode]} for mode in MODES]}
