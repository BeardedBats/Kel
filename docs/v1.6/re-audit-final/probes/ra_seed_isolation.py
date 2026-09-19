#!/usr/bin/env python
"""Seed the final-audit isolation root (offline) with scoped fixtures.

Run from `runtime/` (imports kel for canonical digest/encode):
    python ../docs/v1.6/re-audit-final/probes/ra_seed_isolation.py <kel.sqlite3> <B conversation id>

Seeds: one job+run+approval in conversation `main` (A) and one in conversation B, plus a
marker message and a FAILED submission in B (continuity + state-isolation markers).
"""
import json
import sqlite3
import sys
import time
import uuid

sys.path.insert(0, '.')
from kel.core import digest, encode

db_path, b_id = sys.argv[1], sys.argv[2]
db = sqlite3.connect(db_path)
now = time.time()
action = {'kind': 'command', 'command': 'npm test'}
adig = digest(action)

convs = {r[0] for r in db.execute('SELECT id FROM conversations').fetchall()}
assert 'main' in convs, convs
assert b_id in convs, (b_id, convs)


def seed_job(tag, conversation):
    jid, rid, aid = 'job_%s' % tag, 'run_%s' % tag, 'apr_%s' % tag
    job = {'id': jid, 'revision': 1, 'conversation': conversation, 'state': 'AWAITING_USER',
           'budget': 8, 'spent': 0, 'reserved': 2, 'verdict': 'UNCERTAIN',
           'milestones': {'code': {'state': 'RUNNING', 'attempts': 1, 'error': None}}}
    db.execute('INSERT INTO jobs VALUES(?,?,?)', (jid, 1, encode(job)))
    db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
               (rid, jid, 'code', uuid.uuid4().hex[:8], 'WAITING_APPROVAL', 2, now + 3600,
                None, None, 'fixture', None))
    db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?)',
               (aid, jid, rid, adig, 'PENDING', now + 3600, None))
    db.execute('INSERT INTO approval_actions VALUES(?,?)', (aid, encode(action)))
    return jid, rid, aid


job_a, run_a, apr_a = seed_job('ra_a', 'main')
job_b, run_b, apr_b = seed_job('ra_b', b_id)

seq = db.execute('SELECT COALESCE(MAX(seq), 0) + 1 FROM messages').fetchone()[0]
db.execute('INSERT INTO messages(seq,conversation_id,role,text,job_id,at) VALUES(?,?,?,?,?,?)',
           (seq, b_id, 'user', 'RA-MARKER-CONTINUITY-B', None, now))
db.execute('INSERT INTO submissions VALUES(?,?,?,?,?,?,?)',
           ('sub_ra_b', b_id, 'RA-MARKER-SUBMISSION-B', 'FAILED', 'RA seed', None, now))
db.commit()
print(json.dumps({'action_digest': adig, 'conv_a': 'main', 'conv_b': b_id,
                  'approval_a': apr_a, 'approval_b': apr_b, 'job_b': job_b}))
