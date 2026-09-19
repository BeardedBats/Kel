"""Campaign B auditor probe #1 — independent attacks (read-only on product code).
Run: cd runtime && python ../docs/v1.6/audit-final/probes/auditor_probe_1.py
"""
import json
import os
import sqlite3
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from workforce_fixtures import contract as wf_contract, job_contract  # noqa: E402

from kel.core import Store, PolicyError, encode  # noqa: E402
import kel.workforce as workforce  # noqa: E402
import kel.delegation as delegation  # noqa: E402
import kel.assignment as assignment  # noqa: E402
import kel.chat_approvals as chat  # noqa: E402
from kel.contracts import validate_task_contract  # noqa: E402
import kel.capabilities as caps  # noqa: E402

_TMPS = []


def fresh_store():
    tmp = tempfile.TemporaryDirectory()
    _TMPS.append(tmp)
    st = Store(Path(tmp.name) / 'kel.sqlite3')
    for mod in (workforce, delegation, assignment, chat):
        try:
            mod.ensure_schema(st)
        except Exception as exc:
            print('schema %s: %s' % (mod.__name__, exc))
    return st


def section(t):
    print('\n== %s ==' % t)


def attempt(label, fn):
    try:
        r = fn()
        print('RESULT %s -> NO ERROR (%r)' % (label, r))
        return ('ok', r)
    except PolicyError as exc:
        print('RESULT %s -> PolicyError: %s' % (label, str(exc)[:170]))
        return ('policy', str(exc))
    except Exception as exc:
        print('RESULT %s -> %s: %s' % (label, type(exc).__name__, str(exc)[:170]))
        return ('other', str(exc))


def arm(st, approval_id, action):
    """Seed the approval_actions row exactly as coding.py:140 writes it (post-creation state)."""
    with st.transaction() as db:
        db.execute('INSERT OR IGNORE INTO approval_actions VALUES(?,?)',
                   (approval_id, encode(action)))


ACTION = {'method': 'command', 'workspace': 'proj', 'command': 'echo audited',
          'permissions': None, 'grantRoot': None, 'network': None}


def make_approval(st, conversation, seconds=300):
    job = st.create(job_contract(), conversation=conversation)
    claim = st.claim(job, 'm1', provider='fixture', model='fixture')
    ap = st.request_approval(job, claim['id'], ACTION, seconds=seconds)
    arm(st, ap, ACTION)
    return ap


# ---------------- A. conversation scoping (APR-02 attack) ----------------
section('A. chat approval conversation scoping (APR-02 attack)')
stA = fresh_store()
apA = make_approval(stA, 'convA')
attempt('A1 convB DECLARED resolving convA-owned approval', lambda: chat.resolve(stA, 'action', apA, True, conversation='convB'))
attempt('A2 NO conversation declared resolving convA-owned approval', lambda: chat.resolve(stA, 'action', apA, True))
print('A3 items(convB): %r' % [i.get('id') for i in chat.items(stA, 'convB')])
print('A4 items(convA): %r' % [i.get('id') for i in chat.items(stA, 'convA')])

stA2 = fresh_store()
apM = make_approval(stA2, 'main')
attempt('A5 convA DECLARED resolving main-owned approval', lambda: chat.resolve(stA2, 'action', apM, True, conversation='convA'))
attempt('A6 NO conversation declared resolving main-owned approval', lambda: chat.resolve(stA2, 'action', apM, True))

# ---------------- B. approval window + double resolution ----------------
section('B. approval window + duplicate resolution (spot)')
stB = fresh_store()
apB = make_approval(stB, 'convA', seconds=1)
time.sleep(1.3)
attempt('B1 resolve after the window (declared)', lambda: chat.resolve(stB, 'action', apB, True, conversation='convA'))
stB2 = fresh_store()
apB2 = make_approval(stB2, 'convA')
attempt('B2 first resolution', lambda: chat.resolve(stB2, 'action', apB2, True, conversation='convA'))
attempt('B3 second resolution (duplicate)', lambda: chat.resolve(stB2, 'action', apB2, True, conversation='convA'))

# ---------------- C. effect idempotency / replay ----------------
section('C. effect idempotency / replay (spot)')
stC = fresh_store()
jobC = stC.create(job_contract(), conversation='convA')
attempt('C1 prepare op then prepare same op different target', lambda: (stC.prepare_effect(jobC, 'op_audit1', {'target': 'a'}), stC.prepare_effect(jobC, 'op_audit1', {'target': 'b'})))
stC.observe_effect('op_audit1', {'outcome': 'ok', 'exit_code': 0})
attempt('C2 observe identical receipt again (noop expected)', lambda: stC.observe_effect('op_audit1', {'outcome': 'ok', 'exit_code': 0}))
attempt('C3 observe contradictory receipt', lambda: stC.observe_effect('op_audit1', {'outcome': 'failed', 'exit_code': 1}))

# ---------------- D. canonical persistence primitives ----------------
section('D. canonical persistence primitives')
for label, val in [('NaN', float('nan')), ('Infinity', float('inf')), ('bytes', b'b'), ('set', {1, 2})]:
    attempt('D encode(%s)' % label, lambda val=val: encode({'x': val}))

# ---------------- E. delegation widening ----------------
section('E. AUTH-DELEGATION widening (spot attacks)')
parent = {'class': 'leased-write', 'write_scope': ['src'], 'external_effects': 'none',
          'allowed_tools': ['read_context', 'write_files']}
attempt('E1 child wider class', lambda: validate_task_contract(
    wf_contract(role='release', authority={'class': 'external-effect', 'write_scope': [], 'external_effects': ['publish']},
                allowed_tools=['read_context'], write_boundaries=[]), parent_authority=parent))
attempt('E2 child extra tool', lambda: validate_task_contract(
    wf_contract(allowed_tools=['read_context', 'write_files', 'deploy_app']),
    parent_authority={'class': 'leased-write', 'write_scope': ['src'], 'external_effects': 'none', 'allowed_tools': ['read_context']}))
attempt('E3 scope escape', lambda: validate_task_contract(
    wf_contract(authority={'class': 'leased-write', 'write_scope': ['secrets/x'], 'external_effects': 'none'},
                write_boundaries=['secrets']), parent_authority=parent))
attempt('E4 nested contract without a declared delegator', lambda: validate_task_contract(
    wf_contract(parent_task='tsk_' + 'd' * 12)))

stE = fresh_store()
jobE = stE.create({'request': 'audit budget', 'milestones': [
    {'id': 'm1', 'objective': 'x', 'filename': 'o.md', 'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 20}]}]})
attempt('E5 reserve cost far beyond envelope', lambda: delegation.reserve_budget(
    stE, jobE, budget_class='standard', tokens=10 ** 9, wallclock=10 ** 9, cost=10 ** 9, milestone_id='m1'))
attempt('E6 reserve tokens=1e12 wallclock=1e7 cost=1 (cost-only check?)', lambda: delegation.reserve_budget(
    stE, jobE, budget_class='standard', tokens=10 ** 12, wallclock=10 ** 7, cost=1, milestone_id='m1'))
attempt('E7 reserve cost=8 after the cost=1 reservation', lambda: delegation.reserve_budget(
    stE, jobE, budget_class='standard', tokens=10, wallclock=10, cost=8, milestone_id='m1'))

# ---------------- F. capability fail-closed + directive controls ----------------
section('F. capability fail-closed + directive negative controls')
stF = fresh_store()
attempt('F1 resolve an unknown capability', lambda: caps.resolve(stF, 'teleport'))
for label, text in [('plain', 'use [kel:web=off] now'), ('inline code', '`[kel:web=off]`'),
                    ('fenced', '```\n[kel:web=off]\n```'), ('quoted', 'say "[kel:web=off]"'),
                    ('nested', '[[kel:web=off]]'), ('word-embedded', 'pre[kel:web=off]post'),
                    ('mixed case', '[KEL:WEB=OFF]'), ('paren-adjacent', '([kel:web=off])')]:
    try:
        print('F2 directive[%s] -> %r' % (label, caps.directive(text)))
    except Exception as exc:
        print('F2 directive[%s] raised %s: %s' % (label, type(exc).__name__, str(exc)[:120]))

# ---------------- G. credential containment ----------------
section('G. credential containment (child envs + redact)')
KEYS = ('AUDIT_SENTINEL_SECRET', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY')
for k in KEYS:
    os.environ[k] = 'AUDIT-SENTINEL-%s' % k
try:
    from kel.internal import child_env as internal_child_env, redact as internal_redact
    def show(label, env):
        print('%s -> present: %s' % (label, {k: (k in env) for k in KEYS}))
    try:
        show('G1 internal.child_env(keep=ANTHROPIC)', internal_child_env(keep=('ANTHROPIC_API_KEY',)))
    except TypeError as exc:
        print('G1 TypeError: %s' % exc)
    try:
        show('G2 internal.child_env()', internal_child_env())
    except TypeError as exc:
        print('G2 TypeError: %s' % exc)
    try:
        masked = internal_redact('token sk-ant-AUDIT-SENTINEL-ANTHROPIC_API_KEY and AUDIT-SENTINEL-DEEPSEEK_API_KEY')
        print('G3 redact -> %r' % masked)
    except Exception as exc:
        print('G3 %s: %s' % (type(exc).__name__, str(exc)[:140]))
except Exception as exc:
    print('G import failed: %s: %s' % (type(exc).__name__, str(exc)[:140]))
try:
    from kel.native import child_env as native_child_env
    for prov in ('codex', 'claude'):
        try:
            env = native_child_env(prov)
            print('G4 native.child_env(%s) -> present: %s' % (prov, {k: (k in env) for k in KEYS}))
        except Exception as exc:
            print('G4 native.child_env(%s) %s: %s' % (prov, type(exc).__name__, str(exc)[:120]))
except Exception as exc:
    print('G4 import failed: %s' % exc)
for k in KEYS:
    os.environ.pop(k, None)

# ---------------- H. packaged fresh/upgrade DB migration receipts ----------------
section('H. packaged fresh/upgrade DB schema_migrations (read-only)')
for label, d in [('r12-fresh2', 'C:/Users/Nick/Desktop/Kel/ux-audit/runs/r12-fresh2'),
                 ('r12-upgrade', 'C:/Users/Nick/Desktop/Kel/ux-audit/runs/r12-upgrade'),
                 ('r12-upgrade-out', 'C:/Users/Nick/Desktop/Kel/ux-audit/runs/r12-upgrade-out')]:
    try:
        hits = sorted(Path(d).rglob('kel.sqlite3'))
        if not hits:
            print('H %s: no kel.sqlite3 found' % label)
        for p in hits:
            con = sqlite3.connect('file:%s?mode=ro' % str(p).replace('\\', '/'), uri=True)
            rows = con.execute('SELECT version,name FROM schema_migrations ORDER BY version').fetchall()
            print('H %s %s: %d rows; max=%s' % (label, p.name, len(rows), rows[-1] if rows else None))
            con.close()
    except Exception as exc:
        print('H %s: %s: %s' % (label, type(exc).__name__, str(exc)[:150]))

print('\nPROBE-END')
