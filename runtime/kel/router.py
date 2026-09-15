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


def select(candidates, required=None, explicit=None, quality_floor=None, local_only=False):
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
    eligible.sort(key=lambda c: (c.cost is None, c.cost if c.cost is not None else 0,
                    c.latency is None, c.latency if c.latency is not None else 0,
                    -(c.quota if c.quota is not None else -1), c.name))
    return {'selected': eligible[0].name, 'fallbacks': [c.name for c in eligible[1:]],
            'excluded': excluded, 'policy': 'eligible-cost-v1',
            'unknown_cost': eligible[0].cost is None, 'unknown_quota': eligible[0].quota is None}


def classify(text):
    word = text.strip().lower()
    if word in ('status', '/status', 'jobs', '/jobs'):
        return {'kind': 'status', 'confidence': 1.0}
    if GREENFIELD_RE.search(word):
        return {'kind': 'coding', 'confidence': .7, 'greenfield': True}
    if word.startswith(('write ', 'create ', 'draft ', 'summarize ')):
        return {'kind': 'document', 'confidence': .8}
    return {'kind': 'conversation', 'confidence': .5}
