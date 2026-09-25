"""In-chat approvals (V1.6): a conversation view over the EXISTING durable approval records.

Chat is a presentation/action surface only - it decides nothing by itself:

- Folder/scope decisions are `boundary_expansion_requests` (kel.autonomy). Resolving delegates to
  `Autonomy.resolve_expansion`, and a grant wakes the paused job through the same
  `resume_after_grant` the Autonomy page relies on.
- Step approvals are `approvals` rows (kel.core). Resolving delegates to `Store.resolve_approval`
  and, when the user asks to remember it, to the same project permission cache Work uses.

Chat and Work therefore read and mutate the SAME rows; there is no second approval system. The
only state this module owns is the announcement index: which chat message announced which request,
so the conversation can render a card in place - buttons while the decision is open, a plain
sentence once it is settled.
"""
import contextlib
import json
import time

from .core import PolicyError

ACCESS = 'access'
ACTION = 'action'
ITEM_LIMIT = 200
MIGRATION_VERSION = 20
MIGRATION_NAME = 'chat_approval_announcements'

ANNOUNCE_DDL = """
CREATE TABLE IF NOT EXISTS approval_announcements(
  conversation_id TEXT NOT NULL, kind TEXT NOT NULL, ref_id TEXT NOT NULL,
  message_seq INTEGER NOT NULL, created REAL NOT NULL,
  PRIMARY KEY(kind, ref_id));
CREATE INDEX IF NOT EXISTS approval_announcements_conversation
  ON approval_announcements(conversation_id, created);
"""

_ACCESS_SCOPE_TITLE = {
    'root': 'Kel needs access to this folder',
    'repo': 'Kel needs access to this repository',
    'domain': 'Kel needs access to this website',
    'tool': 'Kel needs to use this tool',
    'external': 'Kel needs to take this outside action',
}


def ensure_schema(store):
    """Idempotent; every entry point that reads or writes announcements calls this.

    Verified cheap after the first call (audit APR-05): the read path runs on every UI poll (the
    approval card refreshes every 3 seconds), so once this module's migration row exists the call
    returns before any DDL — announcements, leases/requests and the coding tables included. A
    store written before this marker existed runs the idempotent body once and is then stamped.
    """
    from .memory import _table
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return True
    # The view reads leases/requests and conversation links, so it creates those schemas
    # on the same entry point - a fresh store can always answer a chat read.
    from .autonomy import ensure_schema as ensure_autonomy
    from .continuation import ensure_schema as ensure_continuation
    from .coding import CodingAdapter
    ensure_autonomy(store)
    ensure_continuation(store)
    CodingAdapter(store)  # schema only; owns approval_actions
    with contextlib.closing(store.connect()) as db:
        db.executescript(ANNOUNCE_DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), 'tables=2'))
    return True


def record_announcement(db, conversation_id, kind, ref_id, message_seq):
    """Link an already-inserted chat message to its request, inside the caller's transaction."""
    db.execute('INSERT OR REPLACE INTO approval_announcements VALUES(?,?,?,?,?)',
               (str(conversation_id), str(kind), str(ref_id), int(message_seq), time.time()))


def announce(store, conversation_id, kind, ref_id, text, job_id=None):
    """Post one chat message announcing a pending decision; idempotent per (kind, ref_id)."""
    ensure_schema(store)
    with store.transaction() as db:
        existing = db.execute(
            'SELECT message_seq FROM approval_announcements WHERE kind=? AND ref_id=?',
            (str(kind), str(ref_id))).fetchone()
        if existing:
            return None
        cur = db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?)',
                         (str(conversation_id), 'assistant', text, job_id, time.time()))
        record_announcement(db, conversation_id, kind, ref_id, cur.lastrowid)
    return {'message_seq': cur.lastrowid, 'conversation': str(conversation_id)}


def plain_summary(action, limit=160):
    """One plain fragment for a pending step approval: what it wants to do. No ids, no jargon.

    Handles both the run-approval payload the coding adapter records (method/command/
    grantRoot/changes/permissions) and the older kind-shaped payloads.
    """
    if isinstance(action, str):
        try:
            action = json.loads(action)
        except (TypeError, ValueError):
            action = {}
    action = action or {}
    command = str(action.get('command') or '').strip()
    if command:
        return 'run ' + command[:limit]
    if action.get('grantRoot'):
        return 'work in the whole project folder for this step'
    if action.get('changes'):
        return 'apply these file changes'
    if action.get('permissions'):
        return 'use extra permissions for this step'
    method = str(action.get('method') or '')
    if 'fileChange' in method:
        return 'apply these file changes'
    if 'commandexecution' in method.lower():
        return 'run a command'
    if 'permission' in method.lower():
        return 'use extra permissions for this step'
    kind = action.get('kind') or (action.get('action') or {}).get('type') or 'permission'
    if kind == 'connection':
        return 'use "%s" on %s' % (str(action.get('action_name') or 'that action')[:80],
                                   str(action.get('connection_name') or 'a connected service')[:80])
    if kind == 'command':
        return 'run a command'
    if kind == 'permissions':
        return 'use extra permissions for this step'
    if kind == 'grantRoot':
        return 'work in the whole project folder for this step'
    if kind == 'changes':
        return 'apply these file changes'
    return 'take the requested ' + str(kind) + ' step'


def plain_block_reason(decision):
    """A plain sentence for why Kel paused. No rule ids, no machinery words."""
    outcome = str(decision.get('outcome') or '')
    rule = str(decision.get('rule') or '')
    if outcome == 'REQUIRES_BOUNDARY_EXPANSION':
        return 'this step needs to work outside the folder Kel is allowed to use.'
    if outcome == 'REQUIRES_USER_APPROVAL':
        return 'this step needs your explicit OK first.'
    if outcome == 'DENY' and rule == 'boundary-denied':
        return 'you denied this access earlier, and Kel will not ask again for the same thing.'
    if outcome in ('EXPIRED_LEASE', 'REVOKED_LEASE'):
        return 'the permission for this work is no longer active.'
    if outcome == 'GUARDRAIL_TAMPERED':
        return 'a safety rule looks modified, so Kel stopped.'
    if outcome == 'INVALID_CONTEXT':
        return 'this step came from context Kel no longer trusts.'
    return str(decision.get('reason') or 'it needs your decision.')


def announce_approval(store, approval_id, job, action):
    """Announce a pending step approval once, in the conversation that owns the job."""
    conversation = str(job.get('conversation') or 'main')
    text = ('Kel needs your OK to continue: it wants to ' + plain_summary(action) +
            '. You can decide right in this chat.')
    return announce(store, conversation, ACTION, str(approval_id), text,
                    job_id=job.get('id'))


def _job_ids_for(db, conversation_id):
    """Jobs that belong to this conversation: origin and continuation links both count."""
    ids = set()
    for row in db.execute('SELECT data FROM jobs'):
        try:
            job = json.loads(row['data'])
        except (TypeError, ValueError):
            continue
        if str(job.get('conversation')) == conversation_id:
            ids.add(str(job.get('id')))
    # Bare stores (engine tests, very early boots) have no continuation links yet; the read path
    # and the resolution scope share this helper, so a missing table must not break either.
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='job_links'").fetchone():
        for row in db.execute('SELECT job_id FROM job_links WHERE conversation_id=?',
                              (conversation_id,)):
            ids.add(str(row['job_id']))
    return ids


def _access_item(row, ann):
    if row['status'] == 'GRANTED':
        state = 'allowed_project' if row.get('grant_kind') == 'project' else 'allowed_once'
    elif row['status'] == 'DENIED':
        state = 'denied'
    else:
        state = 'pending'
    scope = str(row.get('scope') or 'root')
    return {
        'id': row['request_id'], 'kind': ACCESS, 'state': state,
        'created': row['created'], 'resolved_at': row['resolved_at'],
        'job_id': row['job_id'], 'message_seq': ann.get('message_seq') if ann else None,
        'message_at': ann.get('message_at') if ann else None,
        'title': _ACCESS_SCOPE_TITLE.get(scope, 'Kel needs access to continue'),
        'target': row['target'], 'grant_kind': row.get('grant_kind'),
        'what': row.get('what') or '', 'why': row.get('why') or '',
        'benefit': row.get('benefit') or '', 'fallback': row.get('fallback') or '',
        'summary': None, 'repeatable': None, 'seconds_left': None,
    }


def _action_item(row, action, ann, now, conversation_title=''):
    status = row['status']
    if status == 'PENDING':
        state = 'expired' if float(row.get('expires') or 0) < now else 'pending'
    elif status == 'APPROVED':
        state = 'approved'
    elif status == 'DENIED':
        state = 'denied'
    else:
        state = 'expired'  # EXPIRED or CANCELLED: no longer live either way
    seconds_left = None
    if state == 'pending':
        seconds_left = max(0, int(float(row['expires']) - now))
    return {
        'id': row['id'], 'kind': ACTION, 'state': state,
        'created': ann.get('created') if ann else None,
        'resolved_at': None, 'job_id': row['job_id'],
        'message_seq': ann.get('message_seq') if ann else None,
        'message_at': ann.get('message_at') if ann else None,
        'title': 'Kel needs your OK to continue',
        'target': str(action.get('command') or '').strip() or None,
        'context_title': conversation_title or None, 'grant_kind': None,
        'what': '', 'why': '', 'benefit': '', 'fallback': '',
        'summary': plain_summary(action),
        'repeatable': not bool(action.get('unrepeatable_request')),
        'seconds_left': seconds_left,
    }


def items(store, conversation_id='main'):
    """Conversation-scoped view of both approval kinds: pending and recently settled.

    This is a read surface over the durable records; it never changes them.
    """
    conversation_id = str(conversation_id or 'main')
    ensure_schema(store)
    now = time.time()
    out = []
    with contextlib.closing(store.connect()) as db:
        ids = _job_ids_for(db, conversation_id)
        conversation = db.execute('SELECT title FROM conversations WHERE id=?', (conversation_id,)).fetchone()
        conversation_title = str(conversation['title'] or '').strip() if conversation else ''
        announcements = {(row['kind'], str(row['ref_id'])): dict(row) for row in db.execute(
            'SELECT a.kind, a.ref_id, a.message_seq, a.created, m.at AS message_at '
            'FROM approval_announcements a LEFT JOIN messages m ON m.seq=a.message_seq '
            'WHERE a.conversation_id=?', (conversation_id,))}
        if ids:
            marks = ','.join('?' * len(ids))
            ordered = tuple(sorted(ids))
            for row in db.execute(
                    'SELECT r.*, l.job_id AS job_id FROM boundary_expansion_requests r '
                    'JOIN capability_leases l ON l.lease_id=r.lease_id '
                    'WHERE l.job_id IN (%s) ORDER BY r.created DESC LIMIT %d' % (marks, ITEM_LIMIT),
                    ordered):
                row = dict(row)
                out.append(_access_item(row, announcements.get((ACCESS, str(row['request_id'])))))
            for row in db.execute(
                    'SELECT a.*, x.action FROM approvals a LEFT JOIN approval_actions x '
                    'ON x.approval_id=a.id WHERE a.job_id IN (%s) '
                    'ORDER BY a.rowid DESC LIMIT %d' % (marks, ITEM_LIMIT), ordered):
                row = dict(row)
                try:
                    action = json.loads(row['action']) if row.get('action') else {}
                except (TypeError, ValueError):
                    action = {}
                out.append(_action_item(row, action,
                                        announcements.get((ACTION, str(row['id']))), now,
                                        conversation_title))
    out.sort(key=lambda item: -(item.get('message_at') or item.get('created') or 0))
    return out


def announce_denial(store, request_id):
    """One plain sentence after a denied access request; safe to call from any surface.

    Nothing repeats: the sentence is written at most once per (job, text). The engine's claim
    gate skips jobs that are already waiting on the user, so without this a denial would leave
    the conversation without a plain explanation of the consequence.
    """
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT l.job_id AS job_id FROM boundary_expansion_requests r '
                         'JOIN capability_leases l ON l.lease_id=r.lease_id '
                         'WHERE r.request_id=?', (str(request_id),)).fetchone()
    if not row:
        return None
    job = store.get(row['job_id'])
    text = 'You denied this request \u2014 Kel will not ask again, and nothing was changed.'
    with store.transaction() as db:
        exists = db.execute('SELECT 1 FROM messages WHERE job_id=? AND text=?',
                            (row['job_id'], text)).fetchone()
        if exists:
            return None
        cur = db.execute('INSERT INTO messages(conversation_id,role,text,job_id,at) '
                         'VALUES(?,?,?,?,?)',
                         (job['conversation'], 'assistant', text, row['job_id'], time.time()))
    return {'message_seq': cur.lastrowid}


def require_owned(store, kind, ref_id, conversation):
    """Refuse a resolution whose record belongs to a different conversation (audit APR-02).

    One ownership check for every resolution entry point (the chat module and both service
    routes). It uses the same ownership set as the read path, and a caller that declares
    nothing acts as the `main` conversation - exactly like the read path - so omitting the
    scope can never bypass ownership (Campaign C AUD-MAJOR-001).
    """
    conversation = str(conversation or 'main')
    with contextlib.closing(store.connect()) as db:
        if kind == ACTION:
            row = db.execute('SELECT job_id FROM approvals WHERE id=?', (str(ref_id),)).fetchone()
        elif kind == ACCESS:
            row = db.execute('SELECT l.job_id AS job_id FROM boundary_expansion_requests r '
                             'JOIN capability_leases l ON l.lease_id=r.lease_id'
                             ' WHERE r.request_id=?', (str(ref_id),)).fetchone()
        else:
            row = None
        owned = str(row['job_id']) if row is not None and row['job_id'] is not None else ''
        ids = _job_ids_for(db, conversation) if owned else set()
    if not owned:
        raise PolicyError('Approval request missing')
    if owned not in ids:
        raise PolicyError('That request belongs to another conversation')


def resolve(store, kind, ref_id, allow, grant_kind='once', remember=False, actor='user',
            conversation=None):
    """Resolve through the EXISTING engines; never a parallel path.

    Boundary grants wake the paused job exactly like the Autonomy page; step approvals resolve
    the same row the coding adapter is polling, so work continues without repeating the ask.

    The resolution is always scoped to the acting conversation, exactly like the read path
    (audit APR-02; Campaign C AUD-MAJOR-001): a caller that declares nothing acts as the `main`
    conversation, so a crafted or stale id can never settle work the caller is not looking at.
    """
    if actor != 'user':
        raise PolicyError('Only user input can resolve an approval')
    kind = str(kind or '')
    require_owned(store, kind, ref_id, conversation)
    if kind == ACCESS:
        from .autonomy import Autonomy
        result = Autonomy(store).resolve_expansion(str(ref_id), bool(allow), actor='user',
                                                   grant_kind=grant_kind or 'once')
        if result.get('status') == 'GRANTED':
            from .authorize import resume_after_grant
            resume_after_grant(store, str(ref_id))
            return {'id': str(ref_id), 'kind': ACCESS,
                    'state': 'allowed_project' if (grant_kind or 'once') == 'project'
                    else 'allowed_once'}
        announce_denial(store, ref_id)
        return {'id': str(ref_id), 'kind': ACCESS, 'state': 'denied'}
    if kind == ACTION:
        with contextlib.closing(store.connect()) as db:
            row = db.execute('SELECT a.job_id, x.action FROM approvals a '
                             'LEFT JOIN approval_actions x ON x.approval_id=a.id WHERE a.id=?',
                             (str(ref_id),)).fetchone()
        if not row or not row['action']:
            raise PolicyError('Approval request missing')
        action = json.loads(row['action'])
        status = store.resolve_approval(str(ref_id), action, bool(allow), actor='user')
        if status == 'APPROVED' and remember:
            job = store.get(row['job_id'])
            from .context import Context
            Context(store).grant(job.get('contract', {}).get('project_id', 'default'), action)
        return {'id': str(ref_id), 'kind': ACTION,
                'state': {'APPROVED': 'approved', 'DENIED': 'denied'}.get(status, 'expired')}
    raise PolicyError('Unknown approval kind')
