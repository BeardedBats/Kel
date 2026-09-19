"""Campaign B auditor probe #2 - memory battery (read-only on product code).
Run: cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_2_memory.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from kel.core import Store, PolicyError  # noqa: E402
from kel.context import Context  # noqa: E402
from kel.memory import Memory, ensure_schema as mem_ensure, ensure_proposals  # noqa: E402


def log(s):
    print(s, flush=True)


def section(t):
    log('\n== %s ==' % t)


def attempt(label, fn):
    try:
        r = fn()
        short = r if not isinstance(r, dict) else {k: r.get(k) for k in list(r)[:5]}
        log('RESULT %s -> NO ERROR (%r)' % (label, short))
        return r
    except PolicyError as e:
        log('RESULT %s -> PolicyError: %s' % (label, str(e)[:150]))
    except Exception as e:  # noqa: BLE001
        log('RESULT %s -> %s: %s' % (label, type(e).__name__, str(e)[:150]))


tmp = tempfile.TemporaryDirectory()
st = Store(Path(tmp.name) / 'kel.sqlite3')
ctx = Context(st)
p1 = ctx.project('P1', project_id='p1')
p2 = ctx.project('P2', project_id='p2')
c1 = ctx.conversation('p1')
c2 = ctx.conversation('p2')
mem_ensure(st)
ensure_proposals(st)
M = Memory(st)
Z = 'ZEBRAFOX-MEM-UNIQUE-1'

section('A. provenance / trust / secret rules')
r_ok = M.record(p1, 'fact', 'audit.beta', {'statement': Z + ' beta'}, Z + ' beta',
                source_type='user_instruction', actor='user', user_confirmed=1)
attempt('A1 web @trust4 refused', lambda: M.record(p1, 'fact', 'audit.w', {'statement': 'x'}, 'x', source_type='web', trust=4))
attempt('A2 web @trust7 accepted', lambda: M.record(p1, 'fact', 'audit.w2', {'statement': 'web note'}, 'web note', source_type='web'))
attempt('A3 preference from inference refused', lambda: M.record(p1, 'preference', 'audit.pref', {'statement': 'p'}, 'p', source_type='workforce_inferred', confidence=0.9))
attempt('A4 preference from user accepted', lambda: M.record(p1, 'preference', 'audit.pref2', {'statement': 'p2'}, 'p2', source_type='user_confirmation', actor='user', user_confirmed=1))
attempt('A5 decision from worker_evidence refused', lambda: M.record(p1, 'decision', 'audit.dec', {'statement': 'd'}, 'd', source_type='worker_evidence'))
attempt('A6 model inference w/o confidence refused', lambda: M.record(p1, 'fact', 'audit.i1', {'statement': 'i'}, 'i', source_type='model_inference'))
attempt('A7 model inference w/ confidence accepted', lambda: M.record(p1, 'fact', 'audit.i2', {'statement': 'i2'}, 'i2', source_type='model_inference', confidence=0.5))
attempt('A8 synthetic secret refused', lambda: M.record(p1, 'fact', 'audit.secret', {'statement': 'token sk-ant-0123456789abcdefXYZ'}, 'token sk-ant-0123456789abcdefXYZ', source_type='user_instruction', actor='user', user_confirmed=1))
with st.connect() as db:
    n = db.execute("SELECT count(*) FROM memories WHERE project_id=? AND (summary LIKE '%sk-ant%' OR value LIKE '%sk-ant%')", (p1,)).fetchone()[0]
log('A9 secret-like rows stored: %d (expect 0)' % n)
try:
    with st.connect() as db:
        ev = db.execute("SELECT count(*) FROM memory_events WHERE project_id=? AND action='refused'", (p1,)).fetchone()[0]
    log('A10 refused audit events: %d (expect >=1)' % ev)
except Exception as e:  # noqa: BLE001
    log('A10 events query failed: %s' % str(e)[:100])

section('B. correction / confirmation / retraction rules')
rid = r_ok
new_id = attempt('B1 correct active record', lambda: M.correct(rid, value={'statement': 'updated'}, summary='updated'))
with st.connect() as db:
    row = db.execute('SELECT status FROM memories WHERE id=?', (rid,)).fetchone()
log('B2 previous record status after correct: %r' % (row['status'] if row else None))
attempt('B3 confirm superseded refused', lambda: M.confirm(rid))
attempt('B4 retract superseded refused', lambda: M.retract(rid))
attempt('B5 retract active succeeds', lambda: M.retract(new_id))
attempt('B6 retract again refused', lambda: M.retract(new_id))

section('C. forget / purge / recovery')
rid2 = M.record(p1, 'fact', 'audit.forget', {'statement': Z + ' forget target'}, Z + ' forget target',
                source_type='user_instruction', actor='user', user_confirmed=1)
M.forget(rid2)
sel = M.select(p1, query='ZEBRAFOX-MEM-UNIQUE-1')
log('C1 select(query) hits after forget: %r (expect empty)' % [x.get('id') for x in sel])
recs = M.records(p1)
tomb = [r for r in recs if r.get('id') == rid2]
log('C2 tombstone visible in records(): %r' % ({k: tomb[0].get(k) for k in ('id', 'status', 'summary', 'value')} if tomb else None))
hist = M.history(rid2)
log('C3 history content after forget: %r' % [{k: h.get(k) for k in ('id', 'status', 'summary')} for h in hist])
attempt('C4 forget a tombstone again', lambda: M.forget(rid2))
sel2 = M.select(p1)
log('C5 select() includes tombstone id: %r (expect False)' % any(x.get('id') == rid2 for x in sel2))

section('D. proposals lifecycle + isolation')
pr = M.propose_change(p1, kind='vetting', type='decision', topic='audit.chan', value={'statement': 'A'}, summary='A', why='audit why', evidence={'sig': 'e1'})
pr2 = M.propose_change(p1, kind='vetting', type='decision', topic='audit.chan', value={'statement': 'A'}, summary='A', why='audit why', evidence={'sig': 'e1'})
log('D1 identical pending dedupe: %r' % (pr['id'] == pr2['id']))
log('D2 proposals p1=%d p2=%d (expect p2=0)' % (len(M.proposals(p1, state='open')), len(M.proposals(p2, state='open'))))
M.reject_proposal(pr['id'], reason='no')
pr3 = M.propose_change(p1, kind='vetting', type='decision', topic='audit.chan', value={'statement': 'A'}, summary='A', why='audit why', evidence={'sig': 'e1'})
log('D3 identical evidence after reject suppressed: %r' % pr3.get('suppressed'))
pr4 = M.propose_change(p1, kind='vetting', type='decision', topic='audit.chan', value={'statement': 'A'}, summary='A', why='audit why', evidence={'sig': 'e2'})
log('D4 changed evidence asks again: suppressed=%r' % pr4.get('suppressed'))
dec = M.accept_proposal(pr4['id'])
log('D5 accept -> state=%r' % dec.get('state'))
attempt('D5b accept twice refused', lambda: M.accept_proposal(pr4['id']))

section('E. service-layer cross-project attacks (conversation-to-project mapping)')
try:
    from kel.service import Service  # noqa: E402
    svc = Service(str(Path(tmp.name) / 'kel.sqlite3'))
    sctx = Context(svc.store)
    sctx.project('SP1', project_id='sp1')
    sctx.project('SP2', project_id='sp2')
    s_c1 = sctx.conversation('sp1')
    s_c2 = sctx.conversation('sp2')
    SM = Memory(svc.store)
    mem_ensure(svc.store)
    ensure_proposals(svc.store)
    rid_p2 = SM.record('sp2', 'fact', 'srv.foreign', {'statement': 'foreign record'}, 'foreign record',
                       source_type='user_instruction', actor='user', user_confirmed=1)

    def srv(label, data):
        attempt('SRV %s' % label, lambda: svc._memory_action(data))

    srv('E1 confirm foreign via p1 conversation', {'conversation': s_c1, 'action': 'confirm', 'id': rid_p2})
    srv('E2 correct foreign', {'conversation': s_c1, 'action': 'correct', 'id': rid_p2, 'summary': 'hack'})
    srv('E3 forget foreign', {'conversation': s_c1, 'action': 'forget', 'id': rid_p2})
    srv('E4 retract foreign', {'conversation': s_c1, 'action': 'retract', 'id': rid_p2})
    srv('E5 unknown conversation', {'conversation': 'no-such-conv', 'action': 'proposals'})
    srv('E6 own-project proposals list', {'conversation': s_c2, 'action': 'proposals'})
    srv('E7 omission (default main)', {'action': 'proposals'})
    try:
        cf = 'cf-audit-1'
        with svc.store.transaction() as db:
            db.execute("INSERT INTO memory_conflicts(id,project_id,memory_a,memory_b,state,created) VALUES(?,?,?,?,?,?)",
                       (cf, 'sp1', 'm_a', 'm_b', 'open', time.time()))
        srv('E8 resolve foreign conflict via SP2', {'conversation': s_c2, 'action': 'resolve_conflict', 'id': cf, 'choice': 'a'})
    except Exception as e:  # noqa: BLE001
        log('E8 conflict setup skipped: %s: %s' % (type(e).__name__, str(e)[:120]))
except Exception as e:  # noqa: BLE001
    log('SERVICE setup failed: %s: %s' % (type(e).__name__, str(e)[:160]))

log('\nPROBE-2-END')
