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
_BUILD_VERB_RE = re.compile(r'\b(?:create|build|make|write|develop|code)\b', re.IGNORECASE)
_DELIVERABLE_RE = re.compile(
    r'\b(?:app|application|program|tool|script|bot|game|cli|website|utility|extension|project)\b', re.IGNORECASE)
# LIVE-2 / D-74.2: "this/the/my/our/current project" (or app, tool…) is the one Kel is already in,
# never a new one. A deliverable counts only when nothing says it already exists.
_EXISTING_RE = re.compile(r"\b(?:this|that|the|my|our|your|current|existing|same|kel'?s)\s+(?:[\w'-]+\s+){0,2}$",
                          re.IGNORECASE)
# D-74.2: an explicit request for a new or separate project (the only way Kel starts one while a
# project with a folder is active).
EXPLICIT_NEW_RE = re.compile(
    r"\b(?:new|separate|another|fresh|standalone|brand[- ]new|different)\s+(?:[\w'-]+\s+){0,2}?"
    r"(?:project|repo(?:sitory)?|workspace|folder)\b"
    r"|\b(?:as|in|into)\s+(?:a|its\s+own|their\s+own)\s+(?:own\s+)?(?:new\s+|separate\s+)?(?:project|repo(?:sitory)?|folder)\b"
    r"|\bfrom\s+scratch\b"
    r"|\b(?:create|build|make|start|develop|code|write)\s+(?:me\s+|us\s+)?(?:a|an)\s+(?:new|separate|standalone)\s+"
    r"(?:[\w'-]+\s+){0,2}?(?:app|application|program|website|game|tool|bot|cli|script|utility|extension)\b",
    re.IGNORECASE)


def greenfield_intent(text):
    """True when the message asks Kel to build something new ("create a little app"), not to change
    something that already exists ("make this project's tests pass", "build the app in my project")."""
    text = str(text or '')
    for verb in _BUILD_VERB_RE.finditer(text):
        window = text[verb.end():verb.end() + 110]
        for noun in _DELIVERABLE_RE.finditer(window):
            before = text[:verb.end() + noun.start()]
            if not _EXISTING_RE.search(before):
                return True
    return False


def explicit_new_project(text):
    """True when the request explicitly asks for a new or separate project (D-74.2)."""
    return bool(EXPLICIT_NEW_RE.search(str(text or '')))

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


# A code change asked for after a short lead-in ("In this project, add…", "please fix…", "can you
# refactor…"), or a change verb together with a code file or a code noun. The live check: "In this
# project, add a multiply(a, b) function to calc.py and a pytest test for it" missed the old
# starts-with-a-verb floor and became a document job. A floor only: callers apply it inside a project
# that has a folder and a test command.
_CODE_VERBS = (r'(?:fix|build|implement|change|add|remove|update|refactor|test|write|create|rename|delete|'
               r'edit|modify|move|extract|replace|debug|port|migrate|optimi[sz]e|clean\s+up)')
_LEAD_IN = (r'^(?:(?:(?:in|for|inside|within|on)\s+(?:this|the|my|our)\s+(?:project|repo(?:sitory)?|codebase|'
            r'code|app|folder)|please|pls|kel|hey\s+kel|ok(?:ay)?|now|next|also|then)\s*[,:;-]?\s*'
            r'|(?:can|could|would|will)\s+you\s+(?:please\s+)?)*')
# Opening verbs exclude write/create: "write a blog post about unit tests" is writing. Those count
# only with a code file named (the second rule).
CODE_LEAD_RE = re.compile(_LEAD_IN + r'(?:fix|build|implement|change|add|remove|update|refactor|test|rename|'
                          r'delete|edit|modify|debug|optimi[sz]e)\b', re.IGNORECASE)
CODE_VERB_RE = re.compile(r'\b' + _CODE_VERBS + r'\b', re.IGNORECASE)
CODE_THING_RE = re.compile(
    r'\b[\w.-]+\.(?:py|pyi|js|jsx|ts|tsx|mjs|cjs|go|rs|java|kt|cs|cpp|cc|c|h|hpp|rb|php|swift|sql|sh|ps1|'
    r'vue|svelte|css|scss|html)\b'
    r'|\b(?:function|method|class|module|endpoint|unit\s+tests?|pytest|test\s+file|test\s+suite|'
    r'failing\s+tests?|stack\s+trace|traceback|exception|type\s+error|compile\s+error|build\s+error|bug)\b',
    re.IGNORECASE)


def coding_intent(text):
    """True when the message asks for a code change even though it does not open with the verb."""
    text = str(text or '').strip()
    if not text:
        return False
    if CODE_LEAD_RE.match(text) and CODE_THING_RE.search(text):
        return True
    return bool(CODE_VERB_RE.search(text) and CODE_THING_RE.search(text) and
                re.search(r'\.(?:py|pyi|js|jsx|ts|tsx|mjs|cjs|go|rs|java|kt|cs|cpp|cc|c|h|hpp|rb|php|swift|'
                          r'sql|sh|ps1|vue|svelte|css|scss|html)\b', text, re.IGNORECASE))


def needs_work(text):
    """True when the message asks for something only real work can do (a command, a service)."""
    return bool(TOOL_REQUEST_RE.search(str(text or '')))


# A file action names a file and the folder it should land in ("create a file named hello.txt
# containing hi in C:\Users\me\Desktop\notes"). Only real work that can write into that folder may
# honour it; a writing job must never report such a request as a completed file action (D-53).
FILE_ACTION_VERB_RE = re.compile(r'\b(?:create|write|save|make|put|add|generate|place)\b', re.IGNORECASE)
FILE_NAME_RE = re.compile(
    r'\b(?:file\s+(?:named|called)?|named|called'
    r'|(?:create|write|save|make|put|add|generate|place)\s+(?:(?:a|an|the)\s+)?(?:new\s+)?)\s*["\'`]?'
    r'([A-Za-z0-9_][A-Za-z0-9_.-]*\.[A-Za-z0-9]{1,10})["\'`]?(?=[\s,;:!?)]|\.(?:\s|$)|$)',
    re.IGNORECASE)
_PATH = r'(?:[A-Za-z]:[\\/]|~[\\/]|\\\\|/)'
FOLDER_RE = re.compile(
    r'\b(?:in|into|inside|under|to|at)\s+(?:the\s+|my\s+)?(?:folder|directory|dir)?\s*'
    r'(?:"(' + _PATH + r'[^"\n]*)"|\'(' + _PATH + r'[^\'\n]*)\'|`(' + _PATH + r'[^`\n]*)`|(' + _PATH + r'[^\s"\'`]*))',
    re.IGNORECASE)


def file_action(text):
    """{'filename', 'folder'} when the message asks for a named file in a named folder, else None."""
    text = str(text or '')
    if not FILE_ACTION_VERB_RE.search(text):
        return None
    name = FILE_NAME_RE.search(text)
    folder = FOLDER_RE.search(text)
    if not name or not folder:
        return None
    path = next(group for group in folder.groups() if group)
    path = path.rstrip('.,;:!?)').strip()
    if len(path) < 2 or '://' in path:
        return None
    return {'filename': name.group(1), 'folder': path}


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
    if greenfield_intent(word):
        return {'kind': 'coding', 'confidence': .7, 'greenfield': True}
    if word.startswith(('write ', 'create ', 'draft ', 'summarize ')):
        return {'kind': 'document', 'confidence': .8}
    return {'kind': 'conversation', 'confidence': .5}
