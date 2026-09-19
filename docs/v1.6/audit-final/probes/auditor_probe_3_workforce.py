"""Campaign B auditor probe #3 - workforce + liveness + retry durability (read-only on product code).
Run: cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_3_workforce.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from workforce_fixtures import contract as wf_contract, job_contract  # noqa: E402
from kel.core import Store, PolicyError  # noqa: E402
from kel import workforce, delegation, assignment  # noqa: E402
import kel.team as team_mod  # noqa: E402
from kel.assurance import waive_gate, gate  # noqa: E402


def log(s):
    print(s, flush=True)


def section(t):
    log('\n== %s ==' % t)


def attempt(label, fn):
    try:
        r = fn()
        log('RESULT %s -> NO ERROR (%r)' % (label, r))
        return r
    except PolicyError as e:
        log('RESULT %s -> PolicyError: %s' % (label, str(e)[:160]))
    except Exception as e:
        log('RESULT %s -> %s: %s' % (label, type(e).__name__, str(e)[:160]))


tmp = tempfile.TemporaryDirectory()
db = Path(tmp.name) / 'kel.sqlite3'
st = Store(db)
for m in (workforce, delegation, assignment):
    attempt('schema %s' % m.__name__, lambda m=m: m.ensure_schema(st))

# ---------------- A. Commander never spawnable ----------------
section('A. Commander is never spawnable')
for attr in ('TEMPLATES', 'ROLES', 'REGISTRY', 'SPAWNABLE_TEMPLATES', 'SPAWNABLE', 'TEMPLATE_IDS'):
    v = getattr(team_mod, attr, None)
    if v is not None:
        try:
            names = list(v.keys()) if isinstance(v, dict) else list(v)
        except Exception:
            names = repr(v)[:80]
        log('A team.%s = %r' % (attr, names))

t = team_mod.Team(st)
attempt('A1 resolve_role("commander")', lambda: t.resolve_role('commander', '', 'tsk_' + 'a' * 12))
attempt('A2 resolve_role("builder") control', lambda: {'authority_max': t.resolve_role('builder', '', 'tsk_' + 'b' * 12)['fields'].get('authority_max')})

# ---------------- B. flag-off performs zero writes ----------------
section('B. workforce.enabled off -> zero writes')
TABLES = ('task_contracts', 'budget_reservations', 'workforce_messages', 'findings', 'team_assignments', 'assignments')


def snapshot():
    out = {}
    with st.connect() as dbx:
        for tbl in TABLES:
            try:
                out[tbl] = dbx.execute('SELECT count(*) FROM %s' % tbl).fetchone()[0]
            except Exception:
                out[tbl] = None
    return out


before = snapshot()
r = attempt('B1 delegate with enabled=False (unknown job)', lambda: delegation.delegate(
    st, 'job_does_not_exist', 'm1', enabled=False))
attempt('B2 delegate with enabled=True (unknown job) control', lambda: delegation.delegate(
    st, 'job_does_not_exist', 'm1', enabled=True))
after = snapshot()
log('B3 table counts unchanged: %r (before=%r)' % (before == after, before))

# ---------------- C. never-gate / waive authorities (static + behavioral probe) ----------------
section('C. never-gate waiver authority')
attempt('C1 gate on a task with no findings', lambda: gate(st, task_id='tsk_' + 'c' * 12))
attempt('C2 waive with authority="kel" on empty task', lambda: waive_gate(
    st, task_id='tsk_' + 'c' * 12, authority='kel', rationale='audit probe'))
src = Path('kel/assurance.py').read_text(encoding='utf-8')
i = src.find('def waive_gate')
log('C3 waive_gate source excerpt:')
log(src[i:i + 700])
i2 = src.find('Never-gate')
log('C4 Never-gate mention @%d: %s' % (i2, src[max(0, i2 - 200):i2 + 260].replace('\n', ' | ')[:420]))

# ---------------- D. liveness / recovery classification ----------------
section('D. expired run -> ORPHANED + new epoch + UNCERTAIN; stale delivery never applies')
job = st.create(job_contract(), conversation='convA')
run = st.claim(job, 'm1', provider='fixture', model='fixture')
rid, epoch = run['id'], run['epoch']
with st.transaction() as dbx:
    dbx.execute('UPDATE runs SET expires=? WHERE id=?', (time.time() - 1, rid))
recovered = st.recover_expired()
with st.connect() as dbx:
    row = dict(dbx.execute('SELECT state,epoch FROM runs WHERE id=?', (rid,)).fetchone())
log('D1 run after recover_expired: state=%r epoch_changed=%r recovered_ids=%r' % (
    row['state'], row['epoch'] != epoch, [x for x in (recovered or [])][:4] if isinstance(recovered, list) else recovered))
jdata = st.get(job)
log('D2 milestone state: %r verdict: %r' % (
    (jdata.get('milestones') or {}).get('m1', {}).get('state'), jdata.get('verdict')))
attempt('D3 assess after expiry', lambda: st.assess(job))
st.enqueue_result('ev_audit_stale', rid, epoch, {'outcome': 'completed', 'summary': 'stale audit result'})
st.consume()
with st.connect() as dbx:
    row2 = dict(dbx.execute('SELECT state,epoch FROM runs WHERE id=?', (rid,)).fetchone())
    inbox = dict(dbx.execute('SELECT handled FROM inbox WHERE id=?', ('ev_audit_stale',)).fetchone())
log('D4 after stale delivery: run.state=%r handled=%r (expect not COMPLETED)' % (row2['state'], inbox['handled']))

# ---------------- E. retry durability across a fresh Store instance ----------------
section('E. retry budget survives a restart (fresh Store instance on same DB)')
job2 = st.create(job_contract(), conversation='convA')
r1 = st.claim(job2, 'm1', provider='fixture', model='fixture', max_attempts=2)
log('E1 first claim run=%s attempts-now=%r' % (r1['id'][:8], st.get(job2).get('milestones', {}).get('m1', {}).get('attempts')))
st.enqueue_result('ev_audit_f1', r1['id'], r1['epoch'], {'outcome': 'failed', 'summary': 'audit fail 1', 'error': 'audit'})
st.consume()
st2 = Store(db)  # simulated restart: fresh process-level instance on the same durable DB
r2 = attempt('E2 second claim after "restart"', lambda: st2.claim(job2, 'm1', provider='fixture', model='fixture', max_attempts=2))
if isinstance(r2, dict) and 'id' in r2:
    log('E2b attempts-now=%r' % st2.get(job2).get('milestones', {}).get('m1', {}).get('attempts'))
    st2.enqueue_result('ev_audit_f2', r2['id'], r2['epoch'], {'outcome': 'failed', 'summary': 'audit fail 2', 'error': 'audit'})
    st2.consume()
    log('E3 after failure 2: milestone=%r verdict=%r' % (
        st2.get(job2).get('milestones', {}).get('m1', {}).get('state'),
        st2.get(job2).get('verdict')))
    attempt('E4 third claim with budget spent (max_attempts=2)', lambda: st2.claim(job2, 'm1', provider='fixture', model='fixture', max_attempts=2))

# ---------------- F. static excerpts (clean UTF-8 via Python) ----------------
section('F. static excerpts')
psrc = Path('kel/parallel.py').read_text(encoding='utf-8')
i = psrc.find('def reclaim_stale_leases')
log('F1 reclaim_stale_leases:')
log(psrc[i:i + 620])
dsrc = Path('kel/delegation.py').read_text(encoding='utf-8')
i = dsrc.find('def close_d1')
log('F2 close_d1 (first 700 chars):')
log(dsrc[i:i + 700] if i >= 0 else 'close_d1 not found')
csrc = Path('kel/contracts.py').read_text(encoding='utf-8')
for needle in ('canonical_tool_policy', 'UNKNOWN'):
    pass
log('\nPROBE-3-END')
