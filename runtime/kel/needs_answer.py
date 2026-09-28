"""D-70 item 1 — the question a "Needs you" work card asks, and how its answer reaches Kel.

A card that needs Nick shows Kel's question in plain words, the quick picks Kel has for it, and an
answer box. There is no second answer system here: every answer goes to Kel in that work's own
conversation through a path that already exists —

- a gated step (`approval`): the in-chat approval's own approve/deny route (`/api/approvals`);
- a checked change Kel would not apply on its own (Full access held it, or Ask first is on), or an
  independent second opinion that raised a problem (`apply`, `second_opinion`): "Apply anyway" (just
  "Apply" under Ask first) is the existing apply path with the user as the actor (`/api/apply`),
  "Leave it" records Nick's choice on that same route;
- paused or interrupted work (`paused`, `interrupted`): the existing resume control or a "continue"
  message for that job;
- work no model here can run (`no_model`: a Fixed model that can't run, or nothing set up can do the
  step) or work out of tries (`out_of_tries`): "Try again" is the same "continue" message for that
  job; "Change the model in Staff & models" (`open_staff`, `action: 'open_settings'`) only opens
  Settings → Staff & models — nothing is sent;
- anything else (`clarification`, `blocked`): a normal message in the conversation, so the D-55
  restart rule applies to it like any other message.

This module only reads engine truth to phrase the question and records the one choice that had no
record before ("Leave it"), durably and idempotently, with one Activity line.
"""
import contextlib
import time

from .core import PolicyError

DDL = """
CREATE TABLE IF NOT EXISTS needs_you_answers(
  job_id TEXT PRIMARY KEY, kind TEXT NOT NULL, choice TEXT NOT NULL, actor TEXT NOT NULL, at REAL NOT NULL);
"""

APPLY_ANYWAY = 'apply_anyway'
LEAVE = 'leave'
CHOICES = (APPLY_ANYWAY, LEAVE)
# LIVE-3: the quick picks for stalled work. 'continue' goes to Kel as a "continue" message for the
# job (the existing resume path); 'open_staff' is a navigation the renderer performs.
TRY_AGAIN = {'id': 'continue', 'label': 'Try again'}
OPEN_STAFF = {'id': 'open_staff', 'label': 'Change the model in Staff & models', 'action': 'open_settings',
              'target': 'staff'}

# What kind of wait it is, in words a person reads beside the question.
WAIT_WORDS = {
    'approval': 'Waiting for your OK',
    'apply': 'Waiting for you to apply it',
    'second_opinion': 'A second opinion raised a problem',
    'paused': 'Paused',
    'interrupted': 'Interrupted',
    'no_model': 'No model can run it',
    'out_of_tries': 'Out of tries',
    'blocked': 'Stopped by a safety rule',
    'clarification': 'Waiting for your answer',
}


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()


def recorded(store, job_id):
    """Nick's recorded answer to an apply / second-opinion wait: {'choice','kind','at'} or None."""
    with contextlib.closing(store.connect()) as db:
        if not _table(db, 'needs_you_answers'):
            return None
        row = db.execute('SELECT kind, choice, at FROM needs_you_answers WHERE job_id=?', (str(job_id),)).fetchone()
    return dict(row) if row else None


def settled_line(store, job):
    """(state, line) once Nick answered an apply or second-opinion wait on the card, else None."""
    answer = recorded(store, job['id'])
    if not answer:
        return None
    if answer['choice'] == APPLY_ANYWAY:
        if (job.get('contract') or {}).get('kind') == 'coding':
            from .auto_apply import describe
            application = describe(store, [job['id']]).get(job['id']) or {}
            if application.get('state') == 'UNDONE':
                return 'done', 'Checked, applied at your request, then undone.'
        return 'done', 'Checked, and applied at your request.'
    if (job.get('contract') or {}).get('kind') == 'coding':
        return 'done', 'Checked; you chose to leave it unapplied.'
    return 'done', 'Checked; you chose to keep the result as it is.'


def _first_sentence(text, limit=220):
    words = ' '.join(str(text or '').split())
    if len(words) <= limit:
        return words
    cut = words[:limit].rsplit(' ', 1)[0].rstrip(',;:')
    return cut + '…'


def _approval(store, job):
    """The pending in-chat approval for this job, as the approvals surface describes it."""
    from .chat_approvals import items
    try:
        rows = items(store, job.get('conversation') or 'main')
    except Exception:
        return None
    return next((row for row in rows if row.get('job_id') == job['id'] and row.get('state') == 'pending'), None)


def question(store, job, why=None, nxt=None):
    """The question a needs-you card asks: {kind, wait, text, detail, options, answer_box, ref}.

    `options` are the quick picks Kel has for this wait ({id, label}); `ref` names the record the
    existing route resolves (an approval's kind and id, the job for apply/resume). Plain words only.
    """
    coding = (job.get('contract') or {}).get('kind') == 'coding'
    base = {'conversation_id': job.get('conversation'), 'job_id': job['id'], 'answer_box': True}
    pending = _approval(store, job)
    if pending:
        subject = pending.get('summary') or pending.get('what') or pending.get('target') or ''
        text = pending.get('title') or 'Kel needs your OK to continue'
        detail = _first_sentence(' '.join(part for part in (subject, pending.get('why') or '') if part))
        return dict(base, kind='approval', wait=WAIT_WORDS['approval'],
                    text=text + ('?' if not text.endswith('?') else ''), detail=detail or None,
                    options=[{'id': 'allow', 'label': 'Allow'}, {'id': 'deny', 'label': 'Don’t allow'}],
                    ref={'approval_kind': pending.get('kind'), 'approval_id': pending.get('id')})
    state = job.get('state')
    if state == 'CLOSED' and job.get('verdict') == 'VERIFIED':
        from .oracle import attention
        needed = attention(store, job)
        if needed:
            options = ([{'id': APPLY_ANYWAY, 'label': 'Apply anyway'}, {'id': LEAVE, 'label': 'Leave it'}]
                       if coding else [{'id': LEAVE, 'label': 'Keep the result as it is'}])
            return dict(base, kind='second_opinion', wait=WAIT_WORDS['second_opinion'],
                        text=('An independent second opinion raised a problem. Apply the change anyway?'
                              if coding else 'An independent second opinion raised a problem with this result.'),
                        detail=needed['why'], options=options, ref={'job': job['id']})
        if coding:
            from .auto_apply import describe
            application = describe(store, [job['id']]).get(job['id']) or {}
            reason = application.get('waiting_reason')
            if reason and application.get('ask_first'):
                from .auto_apply import place
                contract = job.get('contract') or {}
                where = place(store, contract.get('root'), contract.get('project_id'))['words']
                return dict(base, kind='apply', wait=WAIT_WORDS['apply'],
                            text='The change passed its checks. Apply it to %s?' % where,
                            detail=reason + ', so Kel waits for you before it changes your project. '
                                   'Kel checks for conflicts and saves a backup first, so you can undo it.',
                            options=[{'id': APPLY_ANYWAY, 'label': 'Apply'}, {'id': LEAVE, 'label': 'Leave it'}],
                            ref={'job': job['id']})
            if reason:
                return dict(base, kind='apply', wait=WAIT_WORDS['apply'],
                            text='The change passed its checks, but Kel didn’t apply it on its own. Apply it?',
                            detail='Kel waited because ' + reason + '.',
                            options=[{'id': APPLY_ANYWAY, 'label': 'Apply anyway'}, {'id': LEAVE, 'label': 'Leave it'}],
                            ref={'job': job['id']})
    if state in ('PAUSED', 'PAUSING'):
        return dict(base, kind='paused', wait=WAIT_WORDS['paused'], text='This work is paused. Continue it?',
                    detail=None, options=[{'id': 'resume', 'label': 'Continue'}], ref={'job': job['id']})
    from .core import interrupted, route_wait_kind, route_wait_words
    milestones = (job.get('milestones') or {}).values()
    if state == 'WAITING_RESOURCE' and any(interrupted(m) for m in milestones):
        return dict(base, kind='interrupted', wait=WAIT_WORDS['interrupted'],
                    text='Kel’s worker stopped unexpectedly (the app restarted). Start that step again?',
                    detail='Kel won’t repeat it on its own, because part of it may already have run.',
                    options=[dict(TRY_AGAIN)], ref={'job': job['id']})
    wait_kind = route_wait_kind(job.get('route_block')) if state == 'WAITING_RESOURCE' and job.get('route_block') else None
    if wait_kind in ('fixed', 'no_route'):
        return dict(base, kind='no_model', wait=WAIT_WORDS['no_model'],
                    text='No model here can run this work. Change the model, then try again?',
                    detail=_first_sentence(route_wait_words(job['route_block']), 300),
                    options=[dict(TRY_AGAIN), dict(OPEN_STAFF)], ref={'job': job['id']})
    if wait_kind == 'stuck':
        return dict(base, kind='out_of_tries', wait=WAIT_WORDS['out_of_tries'],
                    text='This work ran out of tries before it passed its checks. Give it more tries?',
                    detail=_first_sentence(route_wait_words(job['route_block']), 300),
                    options=[dict(TRY_AGAIN)], ref={'job': job['id']})
    if state == 'BLOCKED':
        from .core import explain_failure
        reason = explain_failure(job) or why or 'A safety rule stopped this work before its next step.'
        return dict(base, kind='blocked', wait=WAIT_WORDS['blocked'],
                    text='A safety rule stopped this work. How should Kel go on?',
                    detail=_first_sentence(reason.split('\n')[0]), options=[], ref={'job': job['id']})
    text = (why or '').strip() or 'Kel needs a word from you to continue.'
    return dict(base, kind='clarification', wait=WAIT_WORDS['clarification'], text=text,
                detail=(nxt or '').strip() or None, options=[], ref={'job': job['id']})


def _waiting_on_apply(store, job):
    """True while this job waits on Nick to apply (or leave) a checked change or a second opinion."""
    if job.get('state') != 'CLOSED' or job.get('verdict') != 'VERIFIED':
        return False
    from .oracle import attention
    if attention(store, job):
        return True
    if (job.get('contract') or {}).get('kind') != 'coding':
        return False
    from .auto_apply import describe
    return bool((describe(store, [job['id']]).get(job['id']) or {}).get('waiting_reason'))


def answer_apply(store, job_id, choice, actor='user'):
    """"Apply anyway" or "Leave it" on a card (`/api/apply`), with Nick as the actor.

    Apply anyway writes the checked change through the existing apply path (conflict check and
    backup first; Undo keeps working); Leave it changes nothing on disk. Either way the choice is
    recorded once, with one Activity line, and the card stops asking. Idempotent.
    """
    if actor != 'user':
        raise PolicyError('Only you can answer this.')
    if choice not in CHOICES:
        raise PolicyError('Choose Apply anyway or Leave it.')
    try:
        job = store.get(str(job_id))
    except KeyError:
        raise PolicyError('Kel could not find that work.') from None
    ensure_schema(store)
    already = recorded(store, job['id'])
    if already:
        return {'job_id': job['id'], 'choice': already['choice'], 'already': True}
    if not _waiting_on_apply(store, job):
        raise PolicyError('This work is not waiting for you to apply it.')
    kind = 'second_opinion' if _second_opinion(store, job) else 'ask_first' if _ask_first(store, job) else 'apply'
    result = None
    if choice == APPLY_ANYWAY:
        if (job.get('contract') or {}).get('kind') != 'coding':
            raise PolicyError('This work has no change to apply.')
        from .apply_changes import apply_checked
        result = apply_checked(store, job['id'], actor='user')
    with store.transaction() as db:
        inserted = db.execute('INSERT OR IGNORE INTO needs_you_answers(job_id, kind, choice, actor, at) '
                              'VALUES(?,?,?,?,?)', (job['id'], kind, choice, actor, time.time())).rowcount
        if inserted:
            record = store._get(db, job['id'])
            store._save(db, record, 'needs_you.answered', {'actor': actor, 'choice': choice, 'wait': kind})
    out = {'job_id': job['id'], 'choice': choice, 'already': not bool(inserted)}
    if result is not None:
        out['application'] = result
    return out


def _second_opinion(store, job):
    from .oracle import attention
    try:
        return bool(attention(store, job))
    except Exception:
        return False


def _ask_first(store, job):
    """True when the change waits only because Ask first is on (so Nick's Apply is not "anyway")."""
    from .auto_apply import describe
    return bool((describe(store, [job['id']]).get(job['id']) or {}).get('ask_first'))
