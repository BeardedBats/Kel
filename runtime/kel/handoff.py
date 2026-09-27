"""Conversational background hand-off (D-53): what the conversation hears while work runs.

`running_work` gives the turn model an honest picture of this conversation's work so "how's it
going?" is answered from durable state, never from memory of the chat. `follow_up` posts one plain
notice when a hand-off job stops making progress on its own (waiting for a model, or blocked), so
the person is not left looking at a card that silently stalled.
"""
import contextlib
import json
import time

from .core import explain_failure


OPEN_STATES_EXCLUDED = ('CLOSED', 'CANCELLED')
NOTICE_STATES = ('WAITING_RESOURCE', 'BLOCKED')


MIGRATION_VERSION = 31
MIGRATION_NAME = 'v2-handoff-and-conversation-indexes'

# D-53/D-55 hand-off tables (previously created ad hoc on every start) and the indexes the
# conversation hot paths need (CP-2): a conversation's messages in order, its submissions, a job's
# submission, pending approvals, and a job's runs. `submissions` is created here too so a bare store
# (no service yet) can take the indexes.
DDL = """
CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY,conversation_id TEXT,text TEXT,state TEXT,
    error TEXT,job_id TEXT,created REAL);
CREATE TABLE IF NOT EXISTS submission_acks(
    submission_id TEXT PRIMARY KEY, message_seq INTEGER, title TEXT, at REAL);
CREATE TABLE IF NOT EXISTS handoff_notices(
    job_id TEXT, state TEXT, at REAL, PRIMARY KEY(job_id, state));
CREATE TABLE IF NOT EXISTS handoff_restarts(
    submission_id TEXT NOT NULL, replaced_job TEXT PRIMARY KEY, amended_by TEXT, at REAL);
CREATE INDEX IF NOT EXISTS messages_by_conversation ON messages(conversation_id, seq);
CREATE INDEX IF NOT EXISTS submissions_by_conversation ON submissions(conversation_id);
CREATE INDEX IF NOT EXISTS submissions_by_job ON submissions(job_id);
CREATE INDEX IF NOT EXISTS approvals_by_status ON approvals(status, job_id);
CREATE INDEX IF NOT EXISTS runs_by_job ON runs(job_id);
"""


def ensure_schema(store):
    """Migration 31 through the ledger: applied once, recorded in schema_migrations."""
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                   'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT)')
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return False
        fresh = not db.execute('SELECT 1 FROM submissions LIMIT 1').fetchone() if db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='submissions'").fetchone() else True
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            db.execute(statement)
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                    'fresh database' if fresh else 'pre-existing database'))
        return True


REQUEST_PREVIEW = 1500
AMENDABLE_JOB_STATES_EXCLUDED = ('CLOSED', 'CANCELLED', 'CANCELLING')


def replaced_jobs(db):
    """Jobs that were stopped because their hand-off restarted with a change (D-55)."""
    return {row['replaced_job'] for row in db.execute('SELECT replaced_job FROM handoff_restarts')}


def _entry(job, titles):
    milestones = job.get('milestones') or {}
    accepted = sum(1 for m in milestones.values() if m.get('state') == 'ACCEPTED')
    contract = job.get('contract') or {}
    title = (titles.get(job['id']) or ((contract.get('handoff') or {}).get('title'))
             or str(contract.get('request', ''))[:120])
    state = job.get('state')
    verdict = job.get('verdict')
    if state == 'CLOSED':
        summary = ('finished and checked' if verdict == 'VERIFIED' else
                   "finished, but it didn't pass its checks" if verdict == 'FAILED' else
                   'finished, but not fully verified')
    elif state in ('CANCELLED', 'CANCELLING'):
        summary = 'stopped'
    elif state == 'AWAITING_USER':
        summary = 'waiting for the person to approve a step'
    elif state in ('PAUSED', 'PAUSING'):
        summary = 'paused'
    elif state == 'WAITING_RESOURCE':
        summary = 'waiting for an available model'
    elif state == 'BLOCKED':
        summary = 'blocked by a safety rule'
    else:
        summary = 'still running, not finished yet'
    return {'title': title, 'state': state, 'verdict': verdict if state == 'CLOSED' else None,
            'summary': summary, 'parts_checked': accepted, 'parts_total': len(milestones)}


def running_work(store, conversation_id):
    """This conversation's open jobs plus its last three closed ones, newest first.

    Every hand-off carries its `work_id` (the submission id) and whether a new message may still
    change it (`can_amend`, D-55): a hand-off that is starting or whose job is still open. Jobs
    replaced by such a restart are left out — the restarted work stands in for them.
    """
    with contextlib.closing(store.connect()) as db:
        handoffs = {row['job_id']: dict(row) for row in db.execute(
            'SELECT s.job_id, s.id, s.text, a.title FROM submission_acks a JOIN submissions s '
            'ON s.id=a.submission_id WHERE s.conversation_id=? AND s.job_id IS NOT NULL',
            (conversation_id,))}
        planning = [dict(row) for row in db.execute(
            "SELECT s.id, s.text, a.title FROM submission_acks a JOIN submissions s ON s.id=a.submission_id "
            "WHERE s.conversation_id=? AND s.state='PLANNING' ORDER BY s.created DESC", (conversation_id,))]
        replaced = replaced_jobs(db)
    titles = {job_id: row['title'] for job_id, row in handoffs.items()}
    out, closed = [], 0
    for row in planning:
        out.append({'work_id': row['id'], 'title': row['title'], 'state': 'STARTING', 'verdict': None,
                    'summary': 'just started, not finished yet', 'parts_checked': 0, 'parts_total': 0,
                    'can_amend': True, 'request': str(row['text'] or '')[:REQUEST_PREVIEW]})
    for job in store.list_jobs():  # newest first
        if job.get('conversation') != conversation_id or job['id'] in replaced:
            continue
        if job.get('state') in OPEN_STATES_EXCLUDED:
            if closed >= 3:
                continue
            closed += 1
        entry = _entry(job, titles)
        source = handoffs.get(job['id'])
        entry['work_id'] = source['id'] if source else None
        entry['can_amend'] = bool(source) and job.get('state') not in AMENDABLE_JOB_STATES_EXCLUDED
        entry['request'] = str((source or {}).get('text') or (job.get('contract') or {}).get('request')
                               or '')[:REQUEST_PREVIEW]
        out.append(entry)
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
                    'Kel is waiting for an available model to continue it.')
        text = 'An update on “' + str(row['title'] or 'your request') + '”: ' + note
        with store.transaction() as tx:
            cur = tx.execute('INSERT OR IGNORE INTO handoff_notices VALUES(?,?,?)',
                             (job['id'], state, time.time()))
            if cur.rowcount:
                tx.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                           (job.get('conversation') or 'main', 'assistant', text, time.time()))
                posted += 1
    return posted
