"""Deterministic hard filters before cost ordering. Unknown inputs stay unknown."""
from dataclasses import dataclass, field
import re
import time
from .core import PolicyError

# Greenfield coding intent: a build/create verb within a short distance of a
# deliverable noun. Runs BEFORE the document prefixes so "write a little app"
# and "create a small tool" route to coding instead of a Markdown document.
GREENFIELD_RE = re.compile(
    r'\b(create|build|make|write|develop|code)\b.{0,100}\b(app|application|program|tool|script|bot|game|cli|website|utility|extension|project)\b',
    re.IGNORECASE)

# Explicit tool/work requests (V2-09). Measured gap: a phone turn that asked Kel to run
# `python -m kel.conn list` and use a connected service was answered conversationally by the
# saved-context path, so nothing ran. A message that asks for a command or a connected service is a
# work request; the runtime is the only part of Kel that can honour it.
TOOL_REQUEST_RE = re.compile(
    r'`(?:python\w*|git|npm|npx|bun|node|cargo|go|pytest|pip|kel)\b[^`\n]*`'  # a real command
    r'|\bpython3?\s+-m\s+\S+'                                                 # python -m <module>
    r'|\bpython3?\s+[\w./\\-]+\.py\b'                                        # python script.py
    r'|\b(?:git|npm|npx|bun|node|cargo|pytest|pip)\s+[a-z][\w-]*'              # git status, npm test
    r'|\buse\s+the\s+connected\s+(?:service|services|accounts?|connections?)\b'
    r'|\b(?:run|use|call)\s+the\s+(?:connected|connection)\b'
    r'|\b(?:run|execute)\s+the\s+(?:command|commands|tests?|script|scripts?)\b'
    r'|\b(?:check|read|look\s+(?:at|in))\s+the\s+(?:repository|repo|project\s+files?|source\s+tree)\b',
    re.IGNORECASE)


def needs_work(text):
    """True when the message asks for something only real work can do (a command, a service)."""
    return bool(TOOL_REQUEST_RE.search(str(text or '')))


@dataclass
class Candidate:
    name: str
    capabilities: set = field(default_factory=lambda: {'text'})
    installed: bool = True
    authenticated: bool = True
    quota: float | None = None
    circuit_until: float = 0
    quality: float | None = None
    cost: float | None = None
    latency: float | None = None
    privacy: str = 'cloud'


def select(candidates, required=None, explicit=None, quality_floor=None, local_only=False, prefer=None,
           evidence=None):
    required = required or {'text'}
    eligible, excluded = [], {}
    for c in candidates:
        reasons = []
        if explicit and c.name != explicit: reasons.append('user choice')
        if not c.installed: reasons.append('not installed')
        if not c.authenticated: reasons.append('authentication unavailable')
        if not required.issubset(c.capabilities): reasons.append('missing capability')
        if c.quota is not None and c.quota <= 0: reasons.append('quota exhausted')
        if c.circuit_until > time.time(): reasons.append('health circuit open')
        if local_only and c.privacy != 'local': reasons.append('privacy scope')
        if quality_floor is not None and (c.quality is None or c.quality < quality_floor): reasons.append('quality floor not established')
        if reasons: excluded[c.name] = reasons
        else: eligible.append(c)
    if not eligible:
        raise PolicyError('No eligible route: '+str(excluded))
    eligible.sort(key=lambda c: (0 if (prefer and c.name == prefer) else 1,
                    c.cost is None, c.cost if c.cost is not None else 0,
                    c.latency is None, c.latency if c.latency is not None else 0,
                    -(c.quota if c.quota is not None else -1), c.name))
    # V2-09: measured outcomes may move a recently-failing provider DOWN — never out of the list,
    # never past an explicit choice or a preference (the person's own ordering is not evidence), and
    # only when the evidence floor was met (`routing_evidence.summary` decides that, not this file).
    protected = {name for name in (prefer, explicit) if name}
    demoted = [c.name for c in eligible
               if c.name not in protected and (evidence or {}).get(c.name, {}).get('demote')]
    if demoted:
        eligible.sort(key=lambda c: (1 if c.name in demoted else 0))
    chosen = eligible[0]
    return {'selected': chosen.name, 'fallbacks': [c.name for c in eligible[1:]],
            'excluded': excluded, 'policy': 'eligible-cost-v2',
            'preferred': prefer or None, 'explicit': explicit or None,
            'demoted': demoted, 'chain': [c.name for c in eligible],
            'evidence': {c.name: (evidence or {})[c.name] for c in eligible
                         if (evidence or {}).get(c.name)},
            'why': _why(chosen, explicit, prefer, demoted),
            'unknown_cost': chosen.cost is None, 'unknown_quota': chosen.quota is None}


def _why(chosen, explicit, prefer, demoted):
    """One plain fragment for "Why this model?": the first fact that actually decided it."""
    if explicit and chosen.name == explicit:
        return 'your chosen model'
    if prefer and chosen.name == prefer:
        return 'your preferred model'
    if demoted:
        return 'recent results moved a failing model down'
    return 'lowest cost among the models that are healthy and capable here'


def classify(text):
    word = text.strip().lower()
    if word in ('status', '/status', 'jobs', '/jobs'):
        return {'kind': 'status', 'confidence': 1.0}
    if GREENFIELD_RE.search(word):
        return {'kind': 'coding', 'confidence': .7, 'greenfield': True}
    if word.startswith(('write ', 'create ', 'draft ', 'summarize ')):
        return {'kind': 'document', 'confidence': .8}
    return {'kind': 'conversation', 'confidence': .5}
