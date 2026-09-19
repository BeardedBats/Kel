#!/usr/bin/env python
"""RA attack battery - Kel V1.6 final post-repair re-audit (engine; part 1).

AUD-MAJOR-001 approval conversation ownership + the recorded adjacent surfaces
(/api/state read list, /api/autonomy by-id resolve).

Run from `runtime/`:  python ../docs/v1.6/re-audit-final/probes/ra_attack_engine.py
No production file is written; all state lives in TemporaryDirectory copies.
"""
import contextlib
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())

from kel import chat_approvals
from kel.authorize import Authorizer, block_job
from kel.autonomy import Autonomy
from kel.coding import CodingAdapter, compile_coding, git
from kel.context import Context
from kel.core import PolicyError, Store, encode
from kel.service import Service

RESULTS = []


def check(name, ok, note=''):
    RESULTS.append((name, bool(ok), note))
    print(('PASS' if ok else 'FAIL'), '|', name, '|', note, flush=True)


def refused(fn, needle='another conversation'):
    try:
        fn()
        return False, 'no exception'
    except PolicyError as exc:
        msg = str(exc)
        return (needle in msg), ('refused: %s' % msg)
    except Exception as exc:
        return False, 'unexpected %r' % exc


def make_project(base, name):
    root = Path(base) / name
    root.mkdir(parents=True, exist_ok=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old', encoding='utf-8')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@local', 'commit', '-m', 'base')
    return root


def fresh_store(base):
    store = Store(Path(base) / 'data')
    CodingAdapter(store)
    Context(store).project('General', project_id='default')
    return store


def drain(store):
    """Fixture-only: close live runs so the next target job can claim (temp DB only)."""
    with store.transaction() as db:
        db.execute("UPDATE runs SET state='EXITED', reservation=0 "
                   "WHERE state IN ('RUNNING','CANCEL_REQUESTED')")
        for row in db.execute('SELECT data FROM jobs'):
            job = json.loads(row['data'])
            if job.get('reserved'):
                job['reserved'] = 0
                store._save(db, job, 'ra.probe.drain')


def make_step_approval(store, job, command='npm test'):
    drain(store)
    run = store.claim(job, 'code', provider='codex-code')
    action = {'kind': 'command', 'command': command}
    approval_id = store.request_approval(job, run['id'], action)
    with store.transaction() as db:
        db.execute('INSERT INTO approval_actions VALUES(?,?)', (approval_id, encode(action)))
    return run, approval_id


def make_access_request(store, job, project, other):
    drain(store)
    run = store.claim(job, 'code', provider='codex-code')
    intent = {'actor': 'worker', 'worker': run['id'], 'job': job, 'milestone': 'code',
              'action_kind': 'repo', 'tool': 'git', 'target': str(other)}
    decision = Authorizer(store).decide(intent)
    if decision['outcome'] != 'REQUIRES_BOUNDARY_EXPANSION':
        raise AssertionError('fixture expected a boundary request, got %s' % decision)
    with store.transaction() as db:
        db.execute("UPDATE runs SET state='RESULT_RECORDED' WHERE id=?", (run['id'],))
        row = store._get(db, job)
        row['milestones']['code'].update(state='NEEDS_REPAIR')
        store._save(db, row, 'ra.probe.blocked')
    block_job(store, job, 'code', decision)
    return run, decision['boundary_request_id']


def section_a():
    tmp = tempfile.TemporaryDirectory()
    try:
        store = fresh_store(tmp.name)
        project = make_project(tmp.name, 'proj')
        other = make_project(tmp.name, 'other')
        contract = compile_coding('Change app.txt.', project, ['python', '-m', 'unittest'])
        main_job = store.create(contract)
        far_job = store.create(contract, conversation='elsewhere')

        _, main_id = make_step_approval(store, main_job)
        _, far_id = make_step_approval(store, far_job)

        # A1 omission cannot settle a foreign conversation's approval
        ok, note = refused(lambda: chat_approvals.resolve(store, 'action', far_id, True))
        check('A1 foreign omission refused', ok, note)

        # A2 declared-foreign refused
        ok, note = refused(lambda: chat_approvals.resolve(store, 'action', far_id, True,
                                                          conversation='main'))
        check('A2 declared-main on foreign refused', ok, note)

        # A3 owner can settle (legitimate behavior intact)
        resolved = chat_approvals.resolve(store, 'action', far_id, True, conversation='elsewhere')
        check('A3 owner settles (feature still works)', resolved['state'] == 'approved',
              str(resolved['state']))

        # A4 omission acts as main on a main-owned record (read-path parity)
        resolved = chat_approvals.resolve(store, 'action', main_id, True)
        check('A4 omission==main parity on main-owned', resolved['state'] == 'approved',
              str(resolved['state']))

        # A5 malformed conversation spellings cannot widen (fresh job: one ask at a time)
        _, far2 = make_step_approval(store, store.create(contract, conversation='elsewhere'))
        malformed = [{'a': 1}, ['x'], 123, 'MAIN', ' main', '', 0, 'elsewhere\x00', 'elsewhere. ']
        bad = []
        for value in malformed:
            ok, note = refused(lambda v=value: chat_approvals.resolve(store, 'action', far2, True,
                                                                      conversation=v))
            if not ok:
                bad.append((value, note))
        check('A5 malformed conversation spellings all refused', not bad, str(bad))

        # A5b the SAME record is still resolvable by its owner after the refusals
        resolved = chat_approvals.resolve(store, 'action', far2, True, conversation='elsewhere')
        check('A5b owner still settles after attack attempts', resolved['state'] == 'approved',
              str(resolved['state']))

        # A6 unknown kind refused
        ok, note = refused(lambda: chat_approvals.resolve(store, 'bogus', main_id, True,
                                                          conversation='main'), 'missing')
        check('A6 unknown kind refused', ok, note)

        # A7 missing id refused
        ok, note = refused(lambda: chat_approvals.resolve(store, 'action', None, True,
                                                          conversation='main'), 'missing')
        check('A7 missing id refused', ok, note)

        # A8 duplicate resolve refused and state unchanged
        _, dup_id = make_step_approval(store, store.create(contract))
        first = chat_approvals.resolve(store, 'action', dup_id, True, conversation='main')
        ok, note = refused(lambda: chat_approvals.resolve(store, 'action', dup_id, True,
                                                          conversation='main'),
                           'does not match')
        with contextlib.closing(store.connect()) as db:
            row = db.execute('SELECT status FROM approvals WHERE id=?', (dup_id,)).fetchone()
        check('A8 duplicate resolve refused, record intact',
              ok and first['state'] == 'approved' and row['status'] == 'APPROVED', note)

        # A9 another job in the SAME conversation is reachable (conversation is the boundary)
        _, second_main = make_step_approval(store, store.create(contract))
        resolved = chat_approvals.resolve(store, 'action', second_main, True, conversation='main')
        check('A9 same-conversation sibling job allowed (by design)',
              resolved['state'] == 'approved', str(resolved['state']))

        # A10 expired approval can never be approved as current
        _, expired_id = make_step_approval(store, store.create(contract))
        with contextlib.closing(store.connect()) as db:
            db.execute('UPDATE approvals SET expires=? WHERE id=?', (time.time() - 5, expired_id))
            db.commit()
        resolved = chat_approvals.resolve(store, 'action', expired_id, True, conversation='main')
        check('A10 expired cannot be approved (records expired)',
              str(resolved['state']).lower() == 'expired', str(resolved['state']))

        # A11 an approval row with no owning job is refused
        with store.transaction() as db:
            db.execute("INSERT INTO approvals VALUES('apr_orphan',NULL,'run_x','d','PENDING',?,NULL)",
                       (time.time() + 60,))
            db.execute("INSERT INTO approval_actions VALUES('apr_orphan',?)",
                       (encode({'kind': 'command', 'command': 'x'}),))
        ok, note = refused(lambda: chat_approvals.resolve(store, 'action', 'apr_orphan', True,
                                                          conversation='main'), 'missing')
        check('A11 jobless approval refused', ok, note)

        # A12 boundary (access-kind) ownership behaves identically
        far_project = make_project(tmp.name, 'farproj')
        _, req_id = make_access_request(store, store.create(contract, conversation='elsewhere'), far_project, other)
        ok, note = refused(lambda: chat_approvals.resolve(store, 'access', req_id, True))
        check('A12a foreign omission refused (access kind)', ok, note)
        ok, note = refused(lambda: chat_approvals.resolve(store, 'access', req_id, True,
                                                          conversation='main'))
        check('A12b declared-main on foreign refused (access kind)', ok, note)
        resolved = chat_approvals.resolve(store, 'access', req_id, True, conversation='elsewhere')
        check('A12c owner allowed once (access kind)', resolved['state'] == 'allowed_once',
              str(resolved['state']))
    finally:
        tmp.cleanup()


def section_b():
    """Service-route surface: /api/approvals, legacy /api/approval, /api/state, /api/autonomy."""
    tmp = tempfile.TemporaryDirectory()
    try:
        os.environ.pop('ANTHROPIC_API_KEY', None)
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        os.environ['KEL_REVIEWER'] = 'none'
        svc = Service(tmp.name)
        try:
            store = svc.store
            project = make_project(tmp.name, 'proj')
            contract = compile_coding('Change app.txt.', project, ['python', '-m', 'unittest'])
            main_job = store.create(contract, conversation='main')
            far_job = store.create(contract, conversation='elsewhere')
            _, main_id = make_step_approval(store, main_job)
            _, far_id = make_step_approval(store, far_job)

            # B1 route + conversation declared correct
            out = svc.action('/api/approvals', {'kind': 'action', 'id': main_id, 'allow': True,
                                                'conversation': 'main'})
            check('B1 /api/approvals owner settles', out.get('state') == 'approved', str(out))

            # B2 route with wrong conversation refused
            ok, note = refused(lambda: svc.action('/api/approvals', {
                'kind': 'action', 'id': far_id, 'allow': True, 'conversation': 'main'}))
            check('B2 /api/approvals wrong conversation refused', ok, note)

            # B3 route omission cannot settle a foreign record
            ok, note = refused(lambda: svc.action('/api/approvals',
                                                  {'kind': 'action', 'id': far_id, 'allow': True}))
            check('B3 /api/approvals omission on foreign refused', ok, note)

            # B4 omission on a main record keeps working (parity)
            _, main2 = make_step_approval(store, store.create(contract))
            out = svc.action('/api/approvals', {'kind': 'action', 'id': main2, 'allow': True})
            check('B4 /api/approvals omission on main allowed', out.get('state') == 'approved',
                  str(out))

            # B5 legacy singular route is scoped the same way
            _, far2 = make_step_approval(store, store.create(contract, conversation='elsewhere'))
            ok, note = refused(lambda: svc.action('/api/approval',
                                                  {'id': far2, 'allow': True}))
            check('B5a legacy /api/approval omission on foreign refused', ok, note)
            ok, note = refused(lambda: svc.action('/api/approval', {
                'id': far2, 'allow': True, 'conversation': 'main'}))
            check('B5b legacy /api/approval wrong conversation refused', ok, note)
            out = svc.action('/api/approval', {'id': far2, 'allow': True,
                                               'conversation': 'elsewhere'})
            check('B5c legacy /api/approval owner allowed',
                  str(out.get('status', out.get('state', ''))).lower() == 'approved', str(out))

            # B6 /api/state read list: reachability observation (recorded, not a pass/fail)
            state = svc.state('main')
            ids = [row.get('id') for row in state.get('approvals', [])]
            foreign_visible = far_id in ids or far2 in ids
            check('B6 /api/state (read-only) lists foreign pending approvals [observation]',
                  True, 'foreign pending ids visible in main state=%s ids=%s' % (foreign_visible, ids))

            # B7 /api/autonomy by-id resolve without any conversation (Work surface)
            far_project = make_project(tmp.name, 'farproj')
            other = make_project(tmp.name, 'other')
            _, req_id = make_access_request(store, store.create(contract, conversation='elsewhere'), far_project, other)
            listed = svc.action('/api/autonomy', {'action': 'requests'})
            seen = [r.get('request_id') for r in listed.get('requests', [])]
            out = svc.action('/api/autonomy', {'action': 'resolve', 'request_id': req_id,
                                               'allow': True, 'grant_kind': 'once'})
            check('B7 /api/autonomy resolves foreign boundary request by id (by design; observed)',
                  out.get('status') == 'GRANTED' and req_id in seen,
                  'status=%s listed=%s' % (out.get('status'), req_id in seen))
        finally:
            svc.shutdown()
    finally:
        tmp.cleanup()


def main():
    print('cwd=%s' % os.getcwd())
    print('=== RA engine attack battery (part 1: AUD-MAJOR-001 + surfaces) ===')
    section_a()
    section_b()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print('=== SUMMARY: %d checks, %d failed ===' % (len(RESULTS), len(failed)))
    for name in failed:
        print('FAILED:', name)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
