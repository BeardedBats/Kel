"""Kel's authority mode (D-64, migration 34): Full access by default, one switch back to Ask first.

Nick granted Kel full access explicitly (D-64), so the default is **full**: file changes in any
project folder, terminal commands, web/network access, Connection reads *and* writes, and project
grants go ahead without an approval prompt. Nothing becomes invisible: every step that would have
asked is still written down — an auto-granted approval row (`actor='full-access'`), a granted
boundary request, the guardrail decision, and a job event (`approval.auto_granted`) that Activity
shows as a plain sentence.

**Ask first** (`'ask'`) restores the previous behaviour exactly: approval cards, boundary requests,
Connection confirmations and the approved-domains ask.

What this mode never changes (constitution rules, not permissions): the locked guardrails, the
protected locations (Kel's installed app, its Data root, system and credential folders — see
`kel.containment`), credential custody, a person's explicit "no" (a denied request, a capability
switched off for a conversation, a network scope set to no internet), and the record of every
action. Kel never widens this itself: only the person's own `set_mode` changes it.
"""
import contextlib
from pathlib import Path
import time

from .core import PolicyError, encode, uid

MIGRATION_VERSION = 34
MIGRATION_NAME = 'v2-full-access'

FULL = 'full'
ASK = 'ask'
MODES = (FULL, ASK)
DEFAULT_MODE = FULL
ACTOR = 'full-access'   # the actor recorded on everything this mode grants on the person's behalf
LABELS = {FULL: 'Full access', ASK: 'Ask first'}
DESCRIPTIONS = {
    FULL: ('Kel changes files in your project folders, runs commands, uses the web and your '
           'connected services without asking. Everything it does is recorded in Activity.'),
    ASK: ('Kel asks before it changes files, runs commands, reaches a new website or changes '
          'something in a connected service.'),
}

DDL = """
CREATE TABLE IF NOT EXISTS authority_prefs(
  key TEXT PRIMARY KEY, value TEXT NOT NULL, updated REAL NOT NULL, actor TEXT);
"""


def ensure_schema(store):
    """Migration 34: the preference table, and Full access for every install (D-64).

    Existing installs had no authority setting (they always asked), so the migration writes the
    decided default once. A value the person already chose is never overwritten.
    """
    with contextlib.closing(store.connect()) as db:
        db.executescript(
            'CREATE TABLE IF NOT EXISTS schema_migrations('
            'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);'
            + DDL)
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                      (MIGRATION_VERSION,)).fetchone():
            return False
        db.execute('INSERT OR IGNORE INTO authority_prefs(key,value,updated,actor) VALUES(?,?,?,?)',
                   ('mode', DEFAULT_MODE, time.time(), 'default'))
        db.execute('INSERT OR IGNORE INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'D-64: authority mode defaults to full access'))
    return True


def _ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='authority_prefs'")
                .fetchone())


def mode(store):
    """'full' or 'ask'. A store that has not run the migration yet reads the default."""
    try:
        with contextlib.closing(store.connect()) as db:
            if not _ready(db):
                ensure_schema(store)
                return DEFAULT_MODE
            row = db.execute("SELECT value FROM authority_prefs WHERE key='mode'").fetchone()
    except Exception:
        # Fail toward asking: a store whose setting cannot be read never grants on its own.
        return ASK
    value = row['value'] if row else DEFAULT_MODE
    return value if value in MODES else ASK


def is_full(store):
    return mode(store) == FULL


def describe(store):
    """What the settings surface shows: the mode, its plain label, and when it last changed."""
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        row = db.execute("SELECT value, updated, actor FROM authority_prefs WHERE key='mode'").fetchone()
    current = mode(store)
    return {'mode': current, 'authority_mode': current, 'label': LABELS[current], 'description': DESCRIPTIONS[current],
            'default': DEFAULT_MODE, 'modes': [{'mode': m, 'label': LABELS[m],
                                                'description': DESCRIPTIONS[m]} for m in MODES],
            'updated': row['updated'] if row else None,
            'changed_by_you': bool(row and row['actor'] == 'user')}


def set_mode(store, value, actor='user'):
    """Only the person changes this (D-64 §3: authority never grows by itself)."""
    if actor != 'user':
        raise PolicyError('Only you can change how much Kel may do without asking.')
    if value not in MODES:
        raise PolicyError('Choose Full access or Ask first.')
    ensure_schema(store)
    now = time.time()
    with store.transaction() as db:
        previous = db.execute("SELECT value FROM authority_prefs WHERE key='mode'").fetchone()
        db.execute('INSERT INTO authority_prefs(key,value,updated,actor) VALUES(?,?,?,?) '
                   'ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated,'
                   ' actor=excluded.actor', ('mode', value, now, actor))
        if not previous or previous['value'] != value:
            _authority_event(db, value, previous['value'] if previous else None)
    return describe(store)


def _authority_event(db, value, previous):
    aggregate = 'authority'
    revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM events WHERE aggregate_id=?',
                          (aggregate,)).fetchone()[0]
    payload = {'schema_version': 1, 'detail': {'mode': value, 'previous': previous,
                                               'label': LABELS[value]}}
    db.execute('INSERT INTO events(id,aggregate_id,revision,type,at,payload,dedupe)'
               ' VALUES(?,?,?,?,?,?,NULL)',
               (uid(), aggregate, revision, 'authority.changed', time.time(), encode(payload)))


# ---- granting on the person's behalf (always recorded) -----------------------------------------

def _protected_roots(store):
    from .containment import _credential_roots, _protected_roots as env_roots, app_roots, data_roots
    return [Path(p) for p in (*env_roots(), *app_roots(), *data_roots(store), *_credential_roots())]


def _norm(text):
    return str(text or '').replace('/', '\\').rstrip('\\').lower()


def protected_hit(store, action, workspace=None):
    """A plain reason when a step would touch Kel's own app/data or a credential folder.

    Full access never covers those (handoff §21). The run's own working copy lives inside Kel's data
    folder by design, so paths inside `workspace` are the work itself and are allowed; everything
    else a step names — file-change paths, a granted root, permission paths, or a protected folder
    spelled out in a command — is compared with the protected locations.
    """
    from .containment import sensitive_reason
    roots = [_norm(root) for root in _protected_roots(store)]
    roots = [root for root in roots if root]
    own = _norm(workspace) if workspace else ''

    def inside_own(path):
        text = _norm(path)
        return bool(own) and (text == own or text.startswith(own + '\\'))

    paths = []
    changes = action.get('changes')
    if isinstance(changes, dict):
        paths.extend(str(key) for key in changes)
    elif isinstance(changes, list):
        for item in changes:
            if isinstance(item, dict):
                paths.extend(str(item.get(k)) for k in ('path', 'move_path', 'file') if item.get(k))
            elif isinstance(item, str):
                paths.append(item)
    if isinstance(action.get('workspace'), str):
        paths.append(action['workspace'])
    if action.get('grantRoot') not in (None, False, True, ''):
        paths.append(str(action.get('grantRoot')))
    permissions = action.get('permissions')
    if isinstance(permissions, dict):
        for value in permissions.values():
            if isinstance(value, (list, tuple)):
                paths.extend(str(v) for v in value if isinstance(v, str))
            elif isinstance(value, str):
                paths.append(value)
    for path in paths:
        if not path or inside_own(path) or not (Path(path).is_absolute() or ':' in path):
            continue
        reason = sensitive_reason(path, store=store)
        if reason:
            return reason
    command = action.get('command')
    if isinstance(command, (list, tuple)):
        command = ' '.join(str(part) for part in command)
    text = _norm(command).replace('"', '').replace("'", '')
    if own:
        text = text.replace(own, '')
    for root in roots:
        if root and root in text:
            return "Kel's own app or data folder"
    return None


def refuse(store, job_id, run_id, action, reason, source='runtime'):
    """Record a step Full access will not take (protected location) and return its id."""
    from .core import digest
    from .chat_approvals import plain_summary
    approval_id = uid()
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS approval_actions(approval_id TEXT PRIMARY KEY, action TEXT)')
        db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?)',
                   (approval_id, str(job_id) if job_id else None, str(run_id) if run_id else None,
                    digest(action), 'DENIED', time.time(), ACTOR))
        db.execute('INSERT OR REPLACE INTO approval_actions VALUES(?,?)', (approval_id, encode(action)))
        if job_id:
            try:
                job = store._get(db, str(job_id))
            except KeyError:
                job = None
            if job is not None:
                store._save(db, job, 'approval.refused',
                            {'approval_id': approval_id, 'summary': plain_summary(action),
                             'reason': reason, 'source': source})
    return approval_id


def auto_approve(store, job_id, run_id, action, source='runtime'):
    """Record a step approval as granted by Full access and return its id.

    The row is the same `approvals` record an in-chat approval would have produced (status
    APPROVED, actor `full-access`), so every consumer that checks "was this approved" — the
    exact-action digest check, the isolated-run recovery rule, the in-chat history — sees the truth.
    The job gets one `approval.auto_granted` event with a plain summary for Activity.
    """
    from .core import digest
    from .chat_approvals import plain_summary
    approval_id = uid()
    summary = plain_summary(action)
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS approval_actions(approval_id TEXT PRIMARY KEY, action TEXT)')
        db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?)',
                   (approval_id, str(job_id) if job_id else None, str(run_id) if run_id else None,
                    digest(action), 'APPROVED', time.time() + 300, ACTOR))
        db.execute('INSERT OR REPLACE INTO approval_actions VALUES(?,?)', (approval_id, encode(action)))
        if job_id:
            try:
                job = store._get(db, str(job_id))
            except KeyError:
                job = None
            if job is not None:
                store._save(db, job, 'approval.auto_granted',
                            {'approval_id': approval_id, 'summary': summary, 'source': source,
                             'authority': FULL})
    return approval_id


def record_boundary_grant(store, job_id, scope, target):
    """Activity line for a boundary Kel crossed under Full access (the lease row is the grant)."""
    if not job_id:
        return
    with store.transaction() as db:
        try:
            job = store._get(db, str(job_id))
        except KeyError:
            return
        store._save(db, job, 'authorization.auto_granted',
                    {'scope': scope, 'authority': FULL,
                     'summary': {'root': 'work in a folder outside the project',
                                 'repo': 'work in another repository',
                                 'domain': 'reach a website',
                                 'tool': 'use another tool',
                                 'external': 'take an outside action'}.get(scope, 'continue')})


def apply(store, data):
    """`/api/autonomy` actions `mode` (read) and `set_mode` (the person's switch)."""
    action = data.get('action')
    if action == 'mode':
        return describe(store)
    if action == 'set_mode':
        return set_mode(store, data.get('mode'), actor=data.get('actor', 'user'))
    raise PolicyError('Unknown authority action.')
