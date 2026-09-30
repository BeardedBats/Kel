"""Explicit current-request limits for direct prose; whitespace words, no clipping."""
import re
from .core import PolicyError


def parse(request):
    text = str(request or '')
    text = re.sub(r'(?m)^[ \t]*>[^\n]*(?:\n(?![ \t]*\n)[^\n]*)*', ' ', text)
    text = re.sub(r'```[\s\S]*?(?:```|$)|`[^`]*(?:`|$)|"[^"]*(?:"|$)|“[^”]*(?:”|$)|(?<!\w)\x27[^\x27\n]*\x27(?!\w)|(?<!\w)‘[^’\n]*’(?!\w)', ' ', text)
    if not re.match(r'^\s*(?:(?:please|can you|could you|would you)\s+)*(?:write|draft|rewrite|revise|summarize|summarise|explain|answer|describe|make|give|create)\b', text, re.I):
        return None
    if re.search(r'\b(?:about|roughly|approximately|around|at least|between)\s+\d+', text, re.I):
        return None
    named = list(re.finditer(r'\b(\d+)[- ]word\s+(?:paragraph|reply|response|summary|description|explanation|answer|draft)\b', text, re.I))
    # Separate targets are not a whole-response limit.
    if len(named) > 1 or re.search(r'\b\d+[- ]word\s+(?:paragraphs|replies|responses|summaries|quotes|quote|title|heading|caption)\b', text, re.I):
        return None
    constraints = [(int(m.group(1)), int(m.group(1))) for m in named]
    for m in re.finditer(r'\b(exactly|under|fewer than|less than|at most|no more than)\s*(\d+)\s+words?\b', text, re.I):
        count = int(m.group(2)); kind = m.group(1).lower()
        constraints.append((count, count) if kind == 'exactly' else (1, count - int(kind in ('under', 'fewer than', 'less than'))))
    if not constraints or any(maximum > 1000 or maximum < 1 for minimum, maximum in constraints):
        return None
    minimum = max(c[0] for c in constraints); maximum = min(c[1] for c in constraints)
    if minimum > maximum:
        raise PolicyError('Choose one word limit before I write this reply.')
    # Different valid clauses can describe separate parts; defer rather than guess.
    if len(constraints) > 1 and len(set(constraints)) > 1:
        return None
    return {'minimum': minimum, 'maximum': maximum}


def matches(text, limit):
    count = len(str(text or '').split())
    return limit['minimum'] <= count <= limit['maximum']


def description(limit):
    if limit['minimum'] == limit['maximum']:
        return 'exactly %d whitespace-separated words' % limit['maximum']
    return 'between %d and %d whitespace-separated words' % (limit['minimum'], limit['maximum'])
