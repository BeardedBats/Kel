"""Conversational background hand-off (D-53): what the conversation hears while work runs.

`running_work` gives the turn model an honest picture of this conversation's work so "how's it
going?" is answered from durable state, never from memory of the chat. `follow_up` posts one plain
notice when a hand-off job stops making progress on its own (waiting for a worker, or blocked), so
the person is not left looking at a card that silently stalled.
"""
import contextlib
import json
import time

from .core import explain_failure


OPEN_STATES_EXCLUDED = ('CLOSED', 'CANCELLED')
NOTICE_STATES = ('WAITING_RESOURCE', 'BLOCKED')


def ensure_schema(store):
    with contextlib.closing(store.connect()) as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS submission_acks(
                submission_id TEXT PRIMARY KEY, message_seq INTEGER, title TEXT, at REAL);
            CREATE TABLE IF NOT EXISTS handoff_notices(
                job_id TEXT, state TEXT, at REAL, PRIMARY KEY(job_id, state));''')


def _entry(job, titles):
    milestones = job.get('milestones') or {}
    accepted = sum(1 for m in milestones.values() if m.get('state') == 'ACCEPTED')
    contract = job.get('contract') or {}
    title = (titles.get(job['id']) or ((contract.get('handoff') or {}).get('title'))
             or str(contract.get('request', ''))[:120])
    state = job.get('state')
    verdict = job.get('verdict')
    if state == 'CLOSED':
        summary = 'finished and checked' if verdict == 'VERIFIED' else 'finished but not fully verified'
    elif state in ('CANCELLED', 'CANCELLING'):
        summary = 'stopped'
    elif state == 'AWAITING_USER':
        summary = 'waiting for the person to approve a step'
    elif state in ('PAUSED', 'PAUSING'):
        summary = 'paused'
    elif state == 'WAITING_RESOURCE':
        summary = 'waiting for a worker to become available'
    elif state == 'BLOCKED':
        summary = 'blocked by a safety rule'
    else:
        summary = 'still running, not finished yet'
    return {'title': title, 'state': state, 'verdict': verdict if state == 'CLOSED' else None,
            'summary': summary, 'parts_checked': accepted, 'parts_total': len(milestones)}


def running_work(store, conversation_id):
    """This conversation's open jobs plus its last three closed ones, newest first."""
    with contextlib.closing(store.connect()) as db:
        titles = {row['job_id']: row['title'] for row in db.execute(
            'SELECT s.job_id, a.title FROM submission_acks a JOIN submissions s '
            'ON s.id=a.submission_id WHERE s.conversation_id=? AND s.job_id IS NOT NULL',
            (conversation_id,))}
        planning = [row['title'] for row in db.execute(
            "SELECT a.title FROM submission_acks a JOIN submissions s ON s.id=a.submission_id "
            "WHERE s.conversation_id=? AND s.state='PLANNING'", (conversation_id,))]
    out, closed = [], 0
    for title in planning:
        out.append({'title': title, 'state': 'STARTING', 'verdict': None,
                    'summary': 'just started, not finished yet', 'parts_checked': 0, 'parts_total': 0})
    for job in store.list_jobs():  # newest first
        if job.get('conversation') != conversation_id:
            continue
        if job.get('state') in OPEN_STATES_EXCLUDED:
            if closed >= 3:
                continue
            closed += 1
        out.append(_entry(job, titles))
    return out


def follow_up(store):
    """One notice per hand-off job and stalled state. Returns how many notices were posted."""
    posted = 0
    with contextlib.closing(store.connect()) as db:
        rows = [dict(r) for r in db.execute(
            "SELECT j.id, j.data, a.title FROM jobs j JOIN submissions s ON s.job_id=j.id "
            "JOIN submission_acks a ON a.submission_id=s.id "
            "WHERE json_extract(j.data,'$.state') IN ('WAITING_RESOURCE','BLOCKED') "
            "AND NOT EXISTS (SELECT 1 FROM handoff_notices n WHERE n.job_id=j.id "
            "AND n.state=json_extract(j.data,'$.state'))")]
    for row in rows:
        job = json.loads(row['data'])
        state = job.get('state')
        if state not in NOTICE_STATES:
            continue
        note = explain_failure(job)
        if not note:
            note = ('A safety rule stopped this work before its next step, so nothing else ran. '
                    'Open Activity to see what it needs.' if state == 'BLOCKED' else
                    'Kel is waiting for a worker to continue it.')
        text = 'An update on “' + str(row['title'] or 'your request') + '”: ' + note
        with store.transaction() as tx:
            cur = tx.execute('INSERT OR IGNORE INTO handoff_notices VALUES(?,?,?)',
                             (job['id'], state, time.time()))
            if cur.rowcount:
                tx.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                           (job.get('conversation') or 'main', 'assistant', text, time.time()))
                posted += 1
    return posted
