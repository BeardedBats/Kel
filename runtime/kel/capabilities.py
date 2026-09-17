"""Conversation-scoped capability controls.

One plain word the user recognises - Web, Files, Terminal, GitHub - resolved by Kel to whatever tool
it owns for the runtime in play. Two layers decide a capability, and each layer only narrows the one
above it:

  1. hard guardrails          kel.guardrails / BLOCKED_KINDS      (always win)
  2. global availability      what is actually configured         (nothing to enable when absent)
  3. conversation override    Use default / Enabled / Disabled    (this module, per conversation)
  4. role / runtime policy    kel.team tool policy                (narrows further)
  5. execution authorization  kel.authorize lease + approvals     (final gate)

A conversation override may disable anything, may enable a capability that is available and not
globally denied by policy, and may grant exactly one action ("Enable once") which expires when it is
consumed or after a short window. It can never bypass a guardrail, invent credentials, widen a scope
or replace an approval. Explicit chat commands ("web: use default", "don't use the terminal here")
write the same state as the control, so there is one policy and two doors to it.
"""
import contextlib
import re
import time

from .core import PolicyError

MIGRATION_VERSION = 14
MIGRATION_NAME = 'v15-conversation-capabilities'

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
  version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS capability_global(
  capability TEXT PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS conversation_capabilities(
  conversation_id TEXT NOT NULL, capability TEXT NOT NULL, state TEXT NOT NULL, updated REAL NOT NULL,
  PRIMARY KEY(conversation_id, capability));
CREATE TABLE IF NOT EXISTS capability_grants(
  grant_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, capability TEXT NOT NULL,
  created REAL NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);
"""

# Plain names only; the tools behind them stay hidden (they differ per runtime and are Kel's problem).
# Google Drive and Connected apps are deliberately absent: this release has no production effect path
# that could honour them, so they are not offered as switches that could not be kept.
CAPABILITIES = (
    {'id': 'web', 'label': 'Web', 'description': 'Look things up and browse the web',
     'tools': ('browser', 'web', 'research'), 'probe': 'engine'},
    {'id': 'files', 'label': 'Files', 'description': 'Read and change files in this project',
     'tools': ('write', 'read_files'), 'probe': 'files'},
    {'id': 'terminal', 'label': 'Terminal', 'description': 'Run commands on this computer',
     'tools': ('shell', 'run_tests', 'run_command'), 'probe': 'runtime'},
    {'id': 'github', 'label': 'GitHub', 'description': 'Work with repositories and their history',
     'tools': ('git', 'repo'), 'probe': 'runtime'},
)
BY_ID = {entry['id']: entry for entry in CAPABILITIES}
STATES = ('default', 'on', 'off')
AVAILABILITY = ('available', 'needs_setup', 'unavailable')

# Which capability an effect belongs to; callers of kel.authorize pass the tool they are about to use.
_TOOL_MAP = {}
for _entry in CAPABILITIES:
    for _tool in _entry['tools']:
        _TOOL_MAP[_tool] = _entry['id']

_ONCE_TTL_SECONDS = 15 * 60


def _table(db, name):
    return db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)
        if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                          (MIGRATION_VERSION,)).fetchone():
            db.execute('INSERT INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                       (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                        'Conversation-scoped capability controls'))


def capability_for_tool(tool):
    """The capability an effect tool belongs to, or None when the tool is not user-facing."""
    return _TOOL_MAP.get(str(tool or '').strip().lower())


def listing():
    return [{'id': entry['id'], 'label': entry['label'], 'description': entry['description']}
            for entry in CAPABILITIES]


def _validate(capability):
    if capability not in BY_ID:
        raise PolicyError('That is not a Kel capability.')
    return capability


def _runtime_available(store):
    """True when a coding runtime Kel could hand repository/terminal work to exists."""
    try:
        from .providers import Providers
        providers = Providers(store)
        for provider in ('codex', 'claude-code'):
            status = str(providers.status(provider).get('status') or '')
            if status in ('healthy', 'quota', 'quota_not_reported'):
                return True
    except Exception:
        return False
    return False


def availability(store, capability):
    """(state, plain reason) for one capability: what is actually configured right now."""
    _validate(capability)
    probe = BY_ID[capability]['probe']
    if probe == 'files':
        return 'available', 'Kel can read and change files in this project'
    if probe == 'engine':
        return 'available', 'Kel can look things up for you'
    if probe == 'runtime':
        if _runtime_available(store):
            return 'available', 'A coding assistant is ready on this computer'
        return 'needs_setup', 'Connect a coding assistant to use this here'


def global_state(store, capability):
    """The default for new conversations. Absent rows mean 'on' for what is configured."""
    _validate(capability)
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'capability_global'):
            return 'on'
        row = db.execute('SELECT state FROM capability_global WHERE capability=?', (capability,)).fetchone()
    return row['state'] if row else 'on'


def set_global(store, capability, state):
    _validate(capability)
    if state not in ('on', 'off'):
        raise PolicyError('A default is either on or off.')
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        db.execute('INSERT INTO capability_global VALUES(?,?,?) ON CONFLICT(capability) '
                   'DO UPDATE SET state=excluded.state, updated=excluded.updated',
                   (capability, state, time.time()))


def overrides(store, conversation):
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        rows = db.execute('SELECT capability, state FROM conversation_capabilities WHERE conversation_id=?',
                          (str(conversation or ''),)).fetchall()
    return {row['capability']: row['state'] for row in rows}


def set_override(store, conversation, capability, state):
    """Write one conversation override; 'default' removes it. The global setting is never touched."""
    _validate(capability)
    if state not in STATES:
        raise PolicyError('A conversation choice is Use default, Enabled for this chat or '
                          'Disabled for this chat.')
    conversation = str(conversation or '')
    if not conversation:
        raise PolicyError('Open a conversation before choosing what Kel may use here.')
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        if state == 'default':
            db.execute('DELETE FROM conversation_capabilities WHERE conversation_id=? AND capability=?',
                       (conversation, capability))
        else:
            db.execute('INSERT INTO conversation_capabilities VALUES(?,?,?,?) '
                       'ON CONFLICT(conversation_id, capability) DO UPDATE SET state=excluded.state, '
                       'updated=excluded.updated', (conversation, capability, state, time.time()))
    return state


def reset(store, conversation):
    """Back to 'Use default' for every capability in this conversation, and drop one-shot grants."""
    conversation = str(conversation or '')
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        removed = db.execute('DELETE FROM conversation_capabilities WHERE conversation_id=?',
                             (conversation,)).rowcount
        db.execute('DELETE FROM capability_grants WHERE conversation_id=?', (conversation,))
    return int(removed or 0)


def grant_once(store, conversation, capability):
    """Enable exactly one action: the next authorized effect of this capability consumes it."""
    _validate(capability)
    conversation = str(conversation or '')
    if not conversation:
        raise PolicyError('Open a conversation before allowing a single action.')
    ensure_schema(store)
    grant_id = 'grant-' + str(int(time.time() * 1000)) + '-' + capability
    with contextlib.closing(store.connect()) as db:
        db.execute('DELETE FROM capability_grants WHERE conversation_id=? AND capability=?',
                   (conversation, capability))
        db.execute('INSERT INTO capability_grants VALUES(?,?,?,?,?,0)',
                   (grant_id, conversation, capability, time.time(),
                    time.time() + _ONCE_TTL_SECONDS))
    return grant_id


def _take_grant(store, conversation, capability):
    """Consume a live one-shot grant atomically: single use, and it expires on its own.

    One statement, so two effects racing inside the same conversation cannot both spend the grant.
    """
    now = time.time()
    with contextlib.closing(store.connect()) as db:
        cursor = db.execute(
            'UPDATE capability_grants SET used=1 WHERE grant_id IN ('
            'SELECT grant_id FROM capability_grants WHERE conversation_id=? AND capability=? '
            'AND used=0 AND expires>? ORDER BY created LIMIT 1)',
            (str(conversation or ''), capability, now))
        return cursor.rowcount > 0


def _conversation_for_job(store, job_id):
    """The conversation a job belongs to; execution paths know the job, not the chat.

    Prefers the submission that produced the job and falls back to the job's own conversation, so
    every durable job (chat, scheduled or engine-submitted) resolves to the chat it belongs to.
    """
    try:
        with contextlib.closing(store.connect()) as db:
            if _table(db, 'submissions'):
                row = db.execute('SELECT conversation_id FROM submissions WHERE job_id=? LIMIT 1',
                                 (str(job_id or ''),)).fetchone()
                if row and row['conversation_id']:
                    return str(row['conversation_id'])
    except Exception:
        pass
    try:
        return str((store.get(str(job_id or '')) or {}).get('conversation') or '')
    except Exception:
        return ''


def resolve(store, capability, conversation=None, job=None, consume=False):
    """The one decision every caller shares.

    Returns {allowed, effective, availability, global, override, rule, reason}. `consume` marks a
    one-shot grant as used; pre-flight checks pass False so a single grant is spent once.
    """
    _validate(capability)
    if not conversation and job:
        conversation = _conversation_for_job(store, job)
    state, why = availability(store, capability)
    default = global_state(store, capability)
    override = overrides(store, conversation).get(capability, 'default')
    base = {'capability': capability, 'availability': state, 'global': default,
            'override': override, 'reason': why}
    if state == 'unavailable':
        return {**base, 'allowed': False, 'effective': 'off',
                'rule': 'capability-unavailable', 'reason': '%s is not available on this computer.' % BY_ID[capability]['label']}
    effective = override if override != 'default' else default
    if effective == 'on' and state == 'needs_setup':
        # An override must not pretend an unconfigured capability works.
        return {**base, 'allowed': False, 'effective': 'off', 'rule': 'capability-needs-setup',
                'reason': '%s needs setup before it can be used.' % BY_ID[capability]['label']}
    if effective == 'off':
        if consume and _take_grant(store, conversation, capability):
            return {**base, 'allowed': True, 'effective': 'on', 'rule': 'capability-once',
                    'reason': 'Allowed once for this request.'}
        if not consume:
            with contextlib.closing(store.connect()) as db:
                live = db.execute('SELECT 1 FROM capability_grants WHERE conversation_id=? AND capability=? '
                                  'AND used=0 AND expires>? LIMIT 1',
                                  (str(conversation or ''), capability, time.time())).fetchone()
            if live:
                return {**base, 'allowed': True, 'effective': 'on', 'rule': 'capability-once',
                        'reason': 'Allowed once for this request.'}
        return {**base, 'allowed': False, 'effective': 'off',
                'rule': 'capability-conversation-off',
                'reason': '%s is disabled for this conversation.' % BY_ID[capability]['label']}
    return {**base, 'allowed': True, 'effective': 'on', 'rule': 'capability-enabled',
            'reason': why}


def snapshot(store, conversation):
    """Everything a surface needs to draw the control, with plain words and honest states."""
    ensure_schema(store)
    rows = []
    for entry in CAPABILITIES:
        decision = resolve(store, entry['id'], conversation)
        rows.append({
            'id': entry['id'], 'label': entry['label'], 'description': entry['description'],
            'availability': decision['availability'], 'availability_reason': decision['reason'],
            'global': decision['global'], 'override': decision['override'],
            'effective': decision['effective'], 'usable': decision['allowed'],
        })
    return rows


# -- explicit commands ------------------------------------------------------------------------
# Strict, unambiguous commands only. A whole message may be one command because `fullmatch` proves
# the whole message is intended as a control:
#
#   "web: use default"   "terminal: off"   "don't use the browser here"   "use GitHub for this
#   conversation"
#
# Inside a larger substantive request, only the deliberately explicit bracketed control form counts:
#
#   "Please refactor parser.py. [terminal: off]"   "[web: use default] Please research this topic."
#
# Ordinary prose never mutates state and is never altered: text containing "web: off" (colons, tool
# words, quoted commands, code samples, URLs, malformed brackets) passes through byte-identical.
# Anything ambiguous — an unpaired quote, an unclosed code fence, uncertain syntax — matches
# nothing and the message is sent unchanged.
_SCOPE = r'(?:in this (?:chat|conversation)|for this (?:chat|conversation|thread)|here)'
_SCOPE_RX = r'(?:,?\s*' + _SCOPE + r')?'
_ARTICLE = r'(?:the\s+|my\s+|our\s+)?'
_VERB = r'(?:use|using|browse|browsing|access|accessing|touch|touching|run|running|call|calling|open|opening)'
_WORD = {
    'web': ('web', 'browsing', 'browser'),
    'files': ('files', 'file access', 'local files', 'my files'),
    'terminal': ('terminal', 'shell', 'shell commands', 'terminal commands', 'command line'),
    'github': ('github', 'repositories', 'repos', 'repository'),
}
_ALIASES = {alias: capability for capability, aliases in _WORD.items() for alias in aliases}
_ALIAS_PATTERN = '|'.join(sorted((re.escape(alias) for alias in _ALIASES), key=len, reverse=True))
_STATES = {'use default': 'default', 'default': 'default', 'reset': 'default',
           'on': 'on', 'enable': 'on', 'enabled': 'on',
           'off': 'off', 'disable': 'off', 'disabled': 'off'}
_STATE_PATTERN = '|'.join(sorted((re.escape(state) for state in _STATES), key=len, reverse=True))
_COLON_RX = re.compile(r'^' + _ARTICLE + r'(?P<cap>' + _ALIAS_PATTERN + r')\s*[:=]\s*'
                       r'(?P<state>' + _STATE_PATTERN + r')[.!]?$', re.I)
_OFF_RX = re.compile(r'^(?:please\s+)?(?:don.?t|do\s+not|never|stop\s+using|no)\s+(?:to\s+)?'
                     r'(?:' + _VERB + r'\s+)?' + _ARTICLE + r'(?P<cap>' + _ALIAS_PATTERN + r')'
                     + _SCOPE_RX + r'[.!]?$', re.I)
_ON_RX = re.compile(r'^(?:please\s+)?(?:use|enable|allow|turn\s+on)\s+' + _ARTICLE +
                    r'(?P<cap>' + _ALIAS_PATTERN + r')' + _SCOPE_RX + r'[.!]?$', re.I)
_DEFAULT_RX = re.compile(r'^(?:please\s+)?(?:use|back\s+to|go\s+back\s+to|set\s+to|reset\s+to)\s+'
                         r'(?:the\s+)?default\s+(?:for\s+)?' + _ARTICLE +
                         r'(?P<cap>' + _ALIAS_PATTERN + r')' + _SCOPE_RX + r'[.!]?$', re.I)
_TO_DEFAULT_RX = re.compile(r'^(?:please\s+)?(?:set|reset|switch|put|change)\s+' + _ARTICLE +
                            r'(?P<cap>' + _ALIAS_PATTERN + r')\s+(?:back\s+)?to\s+(?:the\s+)?default'
                            + _SCOPE_RX + r'[.!]?$', re.I)
# The embedded control clause is bracketed on purpose: ordinary prose cannot accidentally match it,
# and quoted or code text is excluded by _excluded_spans() before any clause is considered.
_CLAUSE_RX = re.compile(r'(?<!\w)\[\s*(?P<cap>' + _ALIAS_PATTERN + r')\s*[:=]\s*'
                        r'(?P<state>' + _STATE_PATTERN + r')\s*\](?!\w)', re.I)


def _excluded_spans(text):
    """Spans where an embedded clause never counts: code (fenced/inline) and quoted text.

    Fail-safe by construction: an unpaired double quote, curly quote or backtick excludes everything
    after it, so ambiguous text is never treated as a control.
    """
    spans = []
    fences = [m.start() for m in re.finditer('```', text)]
    for index in range(0, len(fences) - 1, 2):
        spans.append((fences[index], fences[index + 1] + 3))
    if len(fences) % 2:
        spans.append((fences[-1], len(text)))

    def add(pattern):
        for match in re.finditer(pattern, text):
            spans.append((match.start(), match.end()))

    add(r'`[^`\n]*`')            # inline code
    add(r'"[^"\n]*"')            # double quotes
    add(r'“[^”\n]*”')            # curly double quotes
    add(r"(?<![A-Za-z])'[^'\n]*'(?![A-Za-z])")    # single quotes (apostrophes do not pair)
    add(r'(?<![A-Za-z])‘[^’\n]*’(?![A-Za-z])')    # curly single quotes

    def uncovered(marker):
        for match in re.finditer(re.escape(marker), text):
            position = match.start()
            if not any(left <= position < right for left, right in spans):
                return position
        return None

    for marker in ('"', '`', '“'):
        position = uncovered(marker)
        if position is not None:
            spans.append((position, len(text)))    # an unpaired opener: nothing after it is a control
    return spans


def directive(text):
    """Parse a whole message that is one capability command. Returns (capability, state) or None."""
    stripped = str(text or '').strip()
    if not stripped or len(stripped) > 200:
        return None
    for pattern, fixed_state in ((_COLON_RX, None), (_DEFAULT_RX, 'default'),
                                 (_TO_DEFAULT_RX, 'default'), (_OFF_RX, 'off'), (_ON_RX, 'on')):
        match = pattern.fullmatch(stripped)
        if not match:
            continue
        capability = _ALIASES.get(match.group('cap').lower())
        if not capability:
            continue
        return capability, fixed_state or _STATES[match.group('state').lower()]
    return None


def directive_clauses(text):
    """Explicit `[capability: state]` clauses (outside quotes and code); [] when there are none.

    Used for a larger message where the user deliberately included a bracketed control. A quoted
    command stays literal text; an unclosed code fence, an unpaired quote or a malformed bracket
    matches nothing and the message is forwarded unchanged. Multiple clauses are supported; only the
    exact bracketed token is removed from the forwarded request.
    """
    text = str(text or '')
    if not text or len(text) > 2000:
        return []
    spans = _excluded_spans(text)

    def excluded(start, end):
        return any(left < end and start < right for left, right in spans)

    found = []
    for match in _CLAUSE_RX.finditer(text):
        if excluded(match.start(), match.end()):
            continue
        # A URL or technical token containing the bracket is not a control either.
        segment_start = max(text.rfind(' ', 0, match.start()), text.rfind('\n', 0, match.start())) + 1
        if '://' in text[segment_start:match.start()]:
            continue
        capability = _ALIASES.get(match.group('cap').lower())
        if not capability:
            continue
        state = _STATES[match.group('state').lower()]
        found.append({'capability': capability, 'state': state,
                      'text': match.group(0), 'inner': '%s: %s' % (capability, state),
                      'start': match.start(), 'end': match.end()})
    return found


def apply_directive(store, conversation, text):
    """Apply a directive and return a plain confirmation sentence, or None when it is not one."""
    parsed = directive(text)
    if not parsed:
        return None
    capability, state = parsed
    label = BY_ID[capability]['label']
    set_override(store, conversation, capability, state)
    if state == 'default':
        return '%s follows your usual setting again in this conversation.' % label
    if state == 'off':
        return "Okay - I won't use %s in this conversation. Say \"use %s here\" when you want it back." % (label, label)
    decision = resolve(store, capability, conversation)
    if decision['allowed']:
        return 'Okay - I can use %s in this conversation.' % label
    return "I can't use %s here yet: %s" % (label, decision['reason'])
