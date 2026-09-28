"""Per-model overlays (workforce-os doc 10 §4): small, subordinate behavioural patches for one model.

An overlay adjusts *how* a model is asked, never *what* it may do: verbosity (answer more briefly or
more fully), literal interpretation (do exactly what was asked, no extras), effort matching (spend
effort in proportion to the task). It never overrides role instructions, gates, safety rules or the
output format a caller asked for — its words are appended after the prompt and say so.

The registry is keyed by (runtime, model): the catalog model id first, then its family ('openai',
'anthropic', 'deepseek'), then '*' for the whole runtime. Each entry is versioned; the version is
recorded with every routing decision (`role_models.resolve` → the staff call's `asked.overlay`) and
with every call it touched (the result's `overlay`), so a changed overlay is visible mid-mission.
No entry means no change at all.

**Seeded empty on purpose.** An entry needs evidence from Kel's own logs or tests that a model
misbehaves in a way a patch fixes. As of 2026-09-28 there is none: the known model quirks (Codex
refusing a model, a turn answer in prose or fenced JSON, change claims) are handled by parsing and
guards, not by asking the model differently. Add an entry only with its evidence in `evidence`.
"""

# (runtime, model id | family | '*') -> overlay. Example shape (not active):
# ('codex', 'gpt-6-luna'): {'version': 1, 'verbosity': 'concise', 'literal': True,
#                           'effort_match': False, 'evidence': '<log or test that shows the need>'}
REGISTRY = {}

VERBOSITY = {'concise': 'Keep the answer brief: the essentials only, no preamble or recap.',
             'detailed': 'Give a complete answer: include the steps and reasons, not just the result.'}
LITERAL = 'Do exactly what was asked; do not add extra features, files or suggestions that were not requested.'
EFFORT = 'Match your effort to the task: a small request gets a short, direct answer.'
HEADER = ('Model note (subordinate: it never overrides anything above, including the required '
          'output format):')


def _family(model_id):
    try:
        from .role_models import MODELS
        return (MODELS.get(model_id) or {}).get('family')
    except Exception:
        return None


def catalog_model(runtime, model):
    """The catalog id for a runtime's model argument ('sonnet' → 'claude-sonnet'), or the text."""
    try:
        from .role_models import catalog_id
        return catalog_id(model, runtime) or model
    except Exception:
        return model


def lookup(runtime, model, registry=None):
    """The overlay for one (runtime, model), or None. Exact model, then family, then the runtime."""
    table = REGISTRY if registry is None else registry
    if not table or not runtime:
        return None
    model_id = catalog_model(runtime, model) if model else None
    for key in ((runtime, model_id), (runtime, _family(model_id)), (runtime, '*')):
        if key[1] and key in table:
            entry = dict(table[key])
            entry['key'] = '%s:%s' % key
            entry.setdefault('version', 1)
            return entry
    return None


def record_of(overlay):
    """What is recorded with a routing decision or a call: key and version only."""
    return {'key': overlay['key'], 'version': overlay['version']} if overlay else None


def text_of(overlay):
    lines = []
    if overlay.get('verbosity') in VERBOSITY:
        lines.append(VERBOSITY[overlay['verbosity']])
    if overlay.get('literal'):
        lines.append(LITERAL)
    if overlay.get('effort_match'):
        lines.append(EFFORT)
    return lines


def apply(prompt, runtime, model, registry=None):
    """(prompt, record) — the prompt with the overlay's note appended, or unchanged with None."""
    overlay = lookup(runtime, model, registry)
    if not overlay:
        return prompt, None
    lines = text_of(overlay)
    if not lines or not isinstance(prompt, str):
        return prompt, None
    return prompt.rstrip() + '\n\n' + HEADER + '\n' + '\n'.join('- ' + line for line in lines), record_of(overlay)
