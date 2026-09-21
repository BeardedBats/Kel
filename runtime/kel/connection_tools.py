"""The assistant bridge to Connections (V2-04a).

Kel's coding runtime can call a Connection action the same way a click can — through the same
framework, the same one-request rule and the same access history — but the runtime never sees a
credential: the shell pushes values into this process's memory (`connections.supply_credentials`),
the bridge reads them there for one request, and `connections.run()` still owns the only outbound
path. Discovery and invocation are one HTTP surface (`catalog` / `call` on `/api/connections`) used
by the `kel.conn` helper the runtime runs as a normal shell command.

Nothing here is a second tool, permission, credential or history system:

- the capability control is `capabilities.resolve('connections', …)` — the same rows, overrides,
  grants and recommendations the app shows, and a one-shot grant is spent atomically at execution
  time (the final gate re-resolves with `consume=True`);
- a mutating action is refused until an APPROVED approval row matches the exact action digest,
  created through the same `request_approval` / `announce_approval` machinery the native runtime's
  asks already use, resolved only by the user, and it resurfaces in the conversation through the
  existing in-chat approval card;
- provenance is `connection_events` (connection, action, domain, status, attempts, ms, source) —
  never a payload, never a value.
"""
import contextlib
import json
import time

from . import capabilities
from . import connection_actions
from .core import PolicyError, digest, encode

TOOL_ACTION_LIMIT = 40
TOOL_PARAM_LIMIT = 20
TOOL_ANSWER_LIMIT = 8000
SOURCE = 'runtime'


def _decide(store, conversation, job, consume=False):
    return capabilities.resolve(store, 'connections', conversation=conversation, job=job,
                                consume=consume)


def _refusal(decision):
    out = {'state': 'not_allowed', 'capability': 'connections', 'allowed': False,
           'rule': decision.get('rule') or '',
           'note': decision.get('reason') or 'Connected services are not allowed here.'}
    recommendation = capabilities.recommendation('connections', decision)
    if recommendation:
        out['recommendation'] = recommendation
    return out


def catalog(store, job=None, conversation=None):
    """What the runtime may do right now: bounded action rows, resolved through the live controls."""
    decision = _decide(store, conversation, job)
    if not decision.get('allowed'):
        return {**_refusal(decision), 'actions': []}
    from .connections import Connections, custody_for
    service = Connections(store)
    items = []
    for connection in service.list()['connections']:
        rows = connection_actions.actions_for(connection['id'])
        if not rows:
            continue
        custody = custody_for(connection['id'])
        if str(connection.get('auth_state') or '') == 'needs_reconnect':
            usable, why = False, 'Kel needs you to reconnect %s.' % connection['name']
        elif not connection.get('has_credentials'):
            usable, why = False, 'Store a credential for %s first.' % connection['name']
        elif not custody:
            usable, why = False, ('Kel cannot reach the stored credential for %s on this '
                                  'computer yet.' % connection['name'])
        else:
            usable, why = True, ''
        for row in rows:
            items.append({'id': row['id'], 'name': row['name'],
                          'connection': connection['id'],
                          'connection_name': connection['name'],
                          'mutating': bool(row['mutating']),
                          'params': [str(name) for name in (row.get('params') or ())]
                          [:TOOL_PARAM_LIMIT],
                          'usable': usable, 'reason': why})
    return {'state': 'ok', 'capability': 'connections', 'allowed': True,
            'reason': decision.get('reason') or '', 'rule': decision.get('rule') or '',
            'actions': items[:TOOL_ACTION_LIMIT]}


def _action_record(connection, row, params):
    """The exact, stable identity of the thing being confirmed — digest-matched, no credential."""
    ordered = {str(key): params[key] for key in sorted(params)}
    return {'kind': 'connection', 'connection': connection['id'],
            'connection_name': connection['name'], 'action': row['id'],
            'action_name': row['name'], 'params': ordered}


def _ensure_approval_tables(store):
    with contextlib.closing(store.connect()) as db:
        db.execute('CREATE TABLE IF NOT EXISTS approval_actions('
                   'approval_id TEXT PRIMARY KEY, action TEXT)')


def _ask_for_confirmation(store, action, job, run):
    """Reuse a pending ask for the exact action, or create and announce one. Never stacks duplicates."""
    wanted = digest(action)
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='approvals'").fetchone():
            return 'no_run', None
        pending = db.execute(
            "SELECT id FROM approvals WHERE status='PENDING' AND action_digest=? "
            "AND IFNULL(job_id,'')=IFNULL(?,'') ORDER BY rowid DESC LIMIT 1",
            (wanted, str(job or ''))).fetchone()
    if pending:
        return 'pending', pending['id']
    if not job or not run:
        return 'no_run', None
    try:
        approval_id = store.request_approval(str(job), str(run), action, seconds=300)
    except PolicyError:
        return 'no_run', None
    _ensure_approval_tables(store)
    with store.transaction() as db:
        db.execute('INSERT INTO approval_actions VALUES(?,?)', (approval_id, encode(action)))
    from .chat_approvals import announce_approval, ensure_schema
    ensure_schema(store)
    announce_approval(store, approval_id, store.get(str(job)), action)
    return 'asked', approval_id


def _confirmation_state(store, action, job, confirmation):
    """('execute'|'pending'|'not_approved'|'expired'|'unknown'|'other_job', approval_id)."""
    wanted = digest(action)
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='approvals'").fetchone():
            return 'unknown', None
        if str(confirmation).strip().lower() == 'auto':
            row = db.execute("SELECT * FROM approvals WHERE action_digest=? AND status='APPROVED' "
                             "ORDER BY rowid DESC LIMIT 1", (wanted,)).fetchone()
        else:
            row = db.execute('SELECT * FROM approvals WHERE id=?',
                             (str(confirmation),)).fetchone()
        if row and row['action_digest'] != wanted:
            return 'unknown', None
    if not row:
        return 'unknown', None
    if str(row['status']) == 'PENDING':
        return 'pending', str(row['id'])
    if str(row['status']) != 'APPROVED':
        return 'not_approved', str(row['id'])
    if row['expires'] is not None and float(row['expires']) < time.time():
        return 'expired', str(row['id'])
    if job and str(row['job_id']) != str(job):
        return 'other_job', str(row['id'])
    return 'execute', str(row['id'])


def _bounded(value):
    if value is None:
        return None, False
    if isinstance(value, str):
        if len(value) <= TOOL_ANSWER_LIMIT:
            return value, False
        return value[:TOOL_ANSWER_LIMIT] + '…', True
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(value)
    if len(text) <= TOOL_ANSWER_LIMIT:
        return value, False
    return text[:TOOL_ANSWER_LIMIT] + '…', True


def call(store, action_id, params=None, connection_id=None, job=None, run=None,
         conversation=None, confirmation=None, source=SOURCE):
    """Perform one Connection action for the runtime, with authority checked at every step."""
    decision = _decide(store, conversation, job)
    if not decision.get('allowed'):
        return _refusal(decision)
    row = connection_actions.action(action_id)
    if row is None:
        return {'state': 'unknown_action', 'capability': 'connections',
                'note': 'Kel does not know that action.'}
    from .connections import Connections, custody_for
    service = Connections(store)
    wanted = connection_id or row['service']
    if not wanted:
        return {'state': 'not_connected', 'capability': 'connections',
                'note': 'That action does not say which service it belongs to.'}
    try:
        connection = service.get(wanted)
    except PolicyError:
        return {'state': 'not_connected', 'capability': 'connections',
                'note': 'Kel has no connected service set up for that action.'}

    allowed_params = {str(name) for name in (row.get('params') or ())}
    clean = {}
    for key, value in (params or {}).items():
        key = str(key)
        if key not in allowed_params:
            return {'state': 'bad_arguments', 'capability': 'connections',
                    'note': '"%s" does not take a "%s" field.' % (row['name'], key[:60])}
        text = str(value)
        if len(text) > 200:
            return {'state': 'bad_arguments', 'capability': 'connections',
                    'note': 'Keep "%s" under 200 characters.' % key[:60]}
        if text:
            clean[key] = text

    custody = custody_for(connection['id'])
    if not connection.get('has_credentials') or not custody:
        return {'state': 'needs_credentials', 'capability': 'connections',
                'connection': connection['id'], 'action': row['id'],
                'note': ('Kel needs %s\'s credential stored on the computer that serves this page '
                         'before it can use it.' % connection['name'])}

    confirmed = False
    if row.get('mutating'):
        action_record = _action_record(connection, row, clean)
        if confirmation in (None, '', False):
            mode, approval_id = _ask_for_confirmation(store, action_record, job, run)
            if mode in ('pending', 'asked'):
                return {'state': 'needs_confirmation', 'capability': 'connections',
                        'connection': connection['id'], 'action': row['id'],
                        'approval': approval_id,
                        'note': ('This changes something in %s, so Kel asked before doing it. '
                                 'Approve it in Kel, then run the same call again with '
                                 '--confirm auto.' % connection['name'])}
            return {'state': 'needs_confirmation_no_run', 'capability': 'connections',
                    'connection': connection['id'], 'action': row['id'],
                    'note': ('This changes something in %s, so Kel needs an OK first, and it can '
                             'only ask about it inside a piece of work. Tell the user plainly.'
                             % connection['name'])}
        verdict, approval_id = _confirmation_state(store, action_record, job, confirmation)
        if verdict == 'pending':
            return {'state': 'needs_confirmation', 'capability': 'connections',
                    'connection': connection['id'], 'action': row['id'],
                    'approval': approval_id,
                    'note': 'That approval is still waiting; approve it in Kel, then try again.'}
        if verdict != 'execute':
            notes = {'not_approved': 'That approval was not granted, so Kel will not do it.',
                     'expired': 'That approval has expired; Nick can approve it once more.',
                     'other_job': 'That approval belongs to different work.',
                     'unknown': 'Kel has no approval that matches this exact action.'}
            return {'state': 'needs_confirmation', 'capability': 'connections',
                    'connection': connection['id'], 'action': row['id'],
                    'approval': approval_id,
                    'note': notes.get(verdict, 'That approval cannot be used for this action.')}
        confirmed = True

    # Final gate at execution time: a one-shot grant is spent atomically right where the effect happens.
    final = _decide(store, conversation, job, consume=True)
    if not final.get('allowed'):
        return _refusal(final)

    project=(store.get(job).get('contract') or {}).get('project_id') if job else None
    try:
        result = service.run(connection['id'], row['id'],
                             credentials=custody_for(connection['id']),
                             params=clean, confirmed=confirmed, source=source,
                             context={'tool':'%s.%s'%(connection['id'],row['id']),
                                      'project':project})
    except PolicyError as exc:
        return {'state': 'cannot_do', 'capability': 'connections',
                'connection': connection['id'], 'action': row['id'], 'note': str(exc)}
    bounded, truncated = _bounded(result.get('result'))
    return {'state': result['state'], 'capability': 'connections',
            'note': result['note'], 'result': bounded, 'truncated': truncated,
            'connection': connection['id'], 'connection_name': connection['name'],
            'action': row['id'], 'action_name': row['name'], 'status': result['status'],
            'attempts': result['attempts'], 'ms': result['ms'], 'at': result['at']}
