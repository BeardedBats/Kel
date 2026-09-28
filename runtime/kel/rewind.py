"""D-75.2: edit a sent message and regenerate Kel's last reply.

Nick can edit a message he sent (Kel answers again from there) and ask Kel to answer its last
reply again — ChatGPT/Claude parity. The conversation is rewound: the edited message and the
direct replies after it leave Kel's view of the conversation (its history, the chat's state and
what later turns read) and the edited request is sent again as an ordinary message.

What was handed off is never silently re-run (D-53): a job, its card, its acknowledgement and its
result stay where they are. Editing a message that itself started work is an amendment (D-55): the
next message in that conversation is read as the change to that work — Kel restarts it with the
change, or starts it anew when it can no longer be changed, and says so plainly.

The desktop hides the chat rows that showed the rewound messages; it records their ids here so a
reload (and another window) hides them too.
"""
import contextlib
import json
import time

from .core import PolicyError

SCHEMA = '''
CREATE TABLE IF NOT EXISTS rewound_messages(seq INTEGER PRIMARY KEY,conversation_id TEXT,reason TEXT,at REAL);
CREATE TABLE IF NOT EXISTS hidden_rows(conversation_id TEXT,row_id TEXT,at REAL,PRIMARY KEY(conversation_id,row_id));
CREATE TABLE IF NOT EXISTS pending_amendments(conversation_id TEXT PRIMARY KEY,submission_id TEXT,at REAL);
'''
# SQL fragment for "a message Kel still sees" (history, state, search).
VISIBLE = 'seq NOT IN (SELECT seq FROM rewound_messages)'
AMEND_WINDOW = 600  # seconds an edit waits for its amended message before it lapses
ROW_LIMIT = 400

STILL_ANSWERING = 'Kel is still answering. Wait for the reply, then try again.'
NOT_FOUND = "Kel couldn't find that message in this chat any more. Reload the chat and try again."
NOTHING_TO_REGENERATE = 'There is no reply of Kel\'s here to answer again yet.'
WORK_REPLY = ("That reply started work, and Kel doesn't run work again on its own. Use the work's card "
              'to retry it, or tell Kel what to change.')


def ensure(db):
    """Create the tables (Context does this at start-up, outside any transaction)."""
    db.executescript(SCHEMA)


def _visible(db, cid):
    return [dict(r) for r in db.execute(
        'SELECT seq,role,text,job_id,meta FROM messages WHERE conversation_id=? AND ' + VISIBLE + ' ORDER BY seq',
        (cid,))]


def _submissions(db, cid):
    """{intake seq: submission} for this conversation, with its acknowledgement (if any)."""
    out = {}
    for row in db.execute('SELECT s.id,s.state,s.job_id,s.text,p.packet,a.message_seq AS ack_seq FROM submissions s '
                          'JOIN submission_packets p ON p.id=s.id '
                          'LEFT JOIN submission_acks a ON a.submission_id=s.id WHERE s.conversation_id=?', (cid,)):
        try:
            intake = (json.loads(row['packet']) or {}).get('intake_seq')
        except (TypeError, ValueError):
            intake = None
        if intake is not None:
            out[intake] = dict(row)
    return out


def _started_work(submission):
    return bool(submission and (submission.get('ack_seq') or submission.get('job_id')))


def _attachments(db, submission):
    if not submission:
        return []
    return [r['name'] for r in db.execute(
        'SELECT a.name FROM message_files f JOIN attachments a ON a.id=f.attachment_id WHERE f.submission_id=?',
        (submission['id'],))]


def _work_tied(message, acks):
    return bool(message.get('job_id')) or message['seq'] in acks


def _rewind(db, cid, messages, start, submissions, reason):
    """Rewind `messages[start:]` except what belongs to handed-off work. Returns (rewound, kept)."""
    acks = {s['ack_seq'] for s in submissions.values() if s.get('ack_seq')}
    rewound, kept = [], []
    for message in messages[start:]:
        submission = submissions.get(message['seq']) if message['role'] == 'user' else None
        keep = _work_tied(message, acks) or (message['seq'] != messages[start]['seq'] and _started_work(submission))
        (kept if keep else rewound).append({'seq': message['seq'], 'role': message['role'], 'text': message['text']})
    now = time.time()
    for item in rewound:
        db.execute('INSERT OR IGNORE INTO rewound_messages VALUES(?,?,?,?)', (item['seq'], cid, reason, now))
    return rewound, kept


def _answering(submissions):
    return any(s['state'] == 'PLANNING' and not s.get('ack_seq') for s in submissions.values())


def edit(store, cid, text, occurrence=0):
    """Rewind to the person's message `text` (the `occurrence`-th from the end with that text)."""
    target_text = str(text or '').strip()
    if not target_text:
        raise PolicyError('Pick the message to edit first.')
    with store.transaction() as db:
        messages = _visible(db, cid)
        submissions = _submissions(db, cid)
        matches = [i for i, m in enumerate(messages) if m['role'] == 'user' and m['text'].strip() == target_text]
        try:
            index = matches[::-1][int(occurrence or 0)]
        except (IndexError, TypeError, ValueError):
            raise PolicyError(NOT_FOUND) from None
        target = messages[index]
        submission = submissions.get(target['seq'])
        if _started_work(submission):
            # D-55: the edited request is a change to the work this message started.
            db.execute('INSERT OR REPLACE INTO pending_amendments VALUES(?,?,?)', (cid, submission['id'], time.time()))
            return {'mode': 'amend', 'submission': submission['id'], 'rewound': [], 'kept': []}
        if _answering(submissions):
            raise PolicyError(STILL_ANSWERING)
        db.execute('DELETE FROM pending_amendments WHERE conversation_id=?', (cid,))
        rewound, kept = _rewind(db, cid, messages, index, submissions, 'edit')
        return {'mode': 'rewind', 'rewound': rewound, 'kept': kept, 'attachments': _attachments(db, submission)}


def regenerate(store, cid):
    """Rewind Kel's last direct reply and the message it answered; returns that message to resend."""
    with store.transaction() as db:
        messages = _visible(db, cid)
        submissions = _submissions(db, cid)
        if _answering(submissions):
            raise PolicyError(STILL_ANSWERING)
        last_reply = next((i for i in range(len(messages) - 1, -1, -1) if messages[i]['role'] == 'assistant'), None)
        if last_reply is None:
            raise PolicyError(NOTHING_TO_REGENERATE)
        index = next((i for i in range(last_reply, -1, -1) if messages[i]['role'] == 'user'), None)
        if index is None:
            raise PolicyError(NOTHING_TO_REGENERATE)
        submission = submissions.get(messages[index]['seq'])
        acks = {s['ack_seq'] for s in submissions.values() if s.get('ack_seq')}
        if _started_work(submission) or any(_work_tied(m, acks) for m in messages[index:]):
            raise PolicyError(WORK_REPLY)
        rewound, kept = _rewind(db, cid, messages, index, submissions, 'regenerate')
        return {'mode': 'rewind', 'text': messages[index]['text'], 'rewound': rewound, 'kept': kept,
                'attachments': _attachments(db, submission)}


def take_amendment(store, cid):
    """The hand-off an edit asked to change (D-55), consumed by the next message; None if none."""
    with store.transaction() as db:
        row = db.execute('SELECT submission_id,at FROM pending_amendments WHERE conversation_id=?', (cid,)).fetchone()
        if not row:
            return None
        db.execute('DELETE FROM pending_amendments WHERE conversation_id=?', (cid,))
    return row['submission_id'] if time.time() - row['at'] <= AMEND_WINDOW else None


def hide(store, cid, rows):
    """Remember the chat rows (the desktop's own ids) that showed rewound messages."""
    if not isinstance(rows, list) or len(rows) > ROW_LIMIT:
        raise PolicyError('Pick at most %d chat rows to hide.' % ROW_LIMIT)
    now = time.time()
    with store.transaction() as db:
        for row in rows:
            if isinstance(row, str) and 0 < len(row) <= 200:
                db.execute('INSERT OR IGNORE INTO hidden_rows VALUES(?,?,?)', (cid, row, now))
    return hidden(store, cid)


def hidden(store, cid):
    with contextlib.closing(store.connect()) as db:
        return {'conversation': cid,
                'rows': [r['row_id'] for r in db.execute('SELECT row_id FROM hidden_rows WHERE conversation_id=? '
                                                         'ORDER BY at', (cid,))]}


def action(service, data):
    """POST /api/rewind: {action: edit|regenerate|hide|hidden, conversation, ...}."""
    kind = data.get('action')
    cid = data.get('conversation')
    if not isinstance(cid, str) or not cid:
        raise PolicyError('Pick a chat first.')
    with contextlib.closing(service.store.connect()) as db:
        if not db.execute('SELECT 1 FROM conversations WHERE id=?', (cid,)).fetchone():
            raise PolicyError(NOT_FOUND)
    if kind == 'edit':
        return edit(service.store, cid, data.get('text'), data.get('occurrence') or 0)
    if kind == 'regenerate':
        return regenerate(service.store, cid)
    if kind == 'hide':
        return hide(service.store, cid, data.get('rows'))
    if kind == 'hidden':
        return hidden(service.store, cid)
    raise PolicyError('Unknown rewind action')
