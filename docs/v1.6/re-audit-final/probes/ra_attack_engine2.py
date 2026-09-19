#!/usr/bin/env python
"""RA attack battery part 2 - budget aggregation, credential containment, path
containment, and the AUD-SUG-001 directive wording.

Run from `runtime/`:  python ../docs/v1.6/re-audit-final/probes/ra_attack_engine2.py
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())

from kel import assignment
from kel.assignment import reserve_budget, release_budget, reservations
from kel.authorize import Authorizer, block_job
from kel.coding import CodingAdapter, compile_coding, git
from kel.context import Context
from kel.core import PolicyError, Store
from kel import guardrails, parallel, native, internal, host_runtime, capabilities

RESULTS = []


def check(name, ok, note=''):
    RESULTS.append((name, bool(ok), note))
    print(('PASS' if ok else 'FAIL'), '|', name, '|', note, flush=True)


def make_project(base, name):
    root = Path(base) / name
    root.mkdir(parents=True, exist_ok=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old', encoding='utf-8')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@local', 'commit', '-m', 'base')
    return root


def budget_store(base):
    store = Store(Path(base) / 'data')
    CodingAdapter(store)
    Context(store).project('General', project_id='default')
    assignment.ensure_schema(store)
    return store


def make_job(store, tmp, budget=8):
    project = make_project(tmp, 'proj%d' % int(time.time() * 1000000 % 1000000))
    contract = compile_coding('Change app.txt.', project, ['python', '-m', 'unittest'])
    return store.create(contract, budget=budget)


def try_reserve(store, job, cost):
    try:
        return reserve_budget(store, job, budget_class='standard', tokens=100,
                              wallclock=60, cost=cost)
    except PolicyError as exc:
        return exc


def section_c():
    tmp = tempfile.TemporaryDirectory()
    try:
        store = budget_store(tmp.name)

        # C1 a single reservation
        job = make_job(store, tmp.name)
        got = try_reserve(store, job, 1)
        check('C1 single reservation accepted', not isinstance(got, PolicyError), repr(got)[:90])

        # C2 cumulative commitments cannot oversubscribe the envelope
        job = make_job(store, tmp.name)
        ok = (not isinstance(try_reserve(store, job, 3), PolicyError)
              and not isinstance(try_reserve(store, job, 4), PolicyError))
        third = try_reserve(store, job, 2)          # 3 + 4 + 2 = 9 > 8
        exact = try_reserve(store, job, 1)          # exactly fills to 8
        check('C2 cumulative fill/exceed/exact',
              ok and isinstance(third, PolicyError) and 'remaining job budget' in str(third)
              and not isinstance(exact, PolicyError),
              'third=%r exact=%r' % (third, exact))

        # C3 release frees the envelope
        job = make_job(store, tmp.name)
        first = try_reserve(store, job, 1)
        blocked = try_reserve(store, job, 8)
        release_budget(store, first['reservation_id'])
        after = try_reserve(store, job, 8)
        check('C3 release frees room', isinstance(blocked, PolicyError)
              and not isinstance(after, PolicyError), repr(after)[:80])

        # C4 consumed keeps narrowing
        job = make_job(store, tmp.name)
        first = try_reserve(store, job, 5)
        release_budget(store, first['reservation_id'], consumed=True)
        blocked = try_reserve(store, job, 4)
        tail = try_reserve(store, job, 3)
        check('C4 consumed narrows (only 3 remains)', isinstance(blocked, PolicyError)
              and not isinstance(tail, PolicyError), repr(blocked)[:80])

        # C5 exact boundary and minimum overage
        job = make_job(store, tmp.name)
        full = try_reserve(store, job, 8)
        over = try_reserve(store, job, 0.0001)
        zero = try_reserve(store, job, 0)
        check('C5 boundary: exact allowed, +0.0001 refused',
              not isinstance(full, PolicyError) and isinstance(over, PolicyError),
              'over=%r zero=%r' % (over, zero))

        # C6 restart coherence (new process-level Store instance, same DB)
        job = make_job(store, tmp.name)
        try_reserve(store, job, 3)
        store2 = Store(Path(tmp.name) / 'data')
        after = try_reserve(store2, job, 5)         # 3 + 5 <= 8
        blocked = try_reserve(store2, job, 1)       # 3 + 5 + 1 > 8
        check('C6 commitments survive restart',
              not isinstance(after, PolicyError) and isinstance(blocked, PolicyError),
              repr(blocked)[:80])

        # C7 disjoint jobs do not share the envelope
        j1, j2 = make_job(store, tmp.name), make_job(store, tmp.name)
        a = try_reserve(store, j1, 8)
        b = try_reserve(store, j2, 8)
        check('C7 disjoint job envelopes independent',
              not isinstance(a, PolicyError) and not isinstance(b, PolicyError), '')

        # C8 concurrency storm: parallel reservations must not oversubscribe
        oversubscribed = []
        for round_no in range(15):
            job = make_job(store, tmp.name)
            barrier = threading.Barrier(5)
            outcomes = []

            def worker():
                barrier.wait(timeout=10)
                outcomes.append(try_reserve(store, job, 3))

            threads = [threading.Thread(target=worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=15)
            wins = [o for o in outcomes if not isinstance(o, PolicyError)]
            committed = float(len(wins)) * 3.0
            if committed > 8:
                oversubscribed.append((round_no, len(wins), committed, len(outcomes)))
        check('C8 concurrent reservations cannot oversubscribe',
              not oversubscribed,
              'oversubscribed rounds: %s' % oversubscribed[:5])

        # C9 no automated close path in the shipped engine (documented residual)
        callers = subprocess.run(
            [sys.executable, '-c',
             "import subprocess,sys,glob;src=open('kel/delegation.py').read()+open('kel/pods.py').read();print('release_budget' in src)"],
            capture_output=True, text=True, cwd=os.getcwd()).stdout.strip()
        check('C9 release_budget has no production caller (dormant feature; fail-closed)',
              callers == 'False', 'delegation/pods mention release_budget=%s' % callers)
    finally:
        tmp.cleanup()


def section_d():
    """Synthetic sentinel credentials; verify unrelated provider keys are absent everywhere."""
    sentinels = {'ANTHROPIC_API_KEY': 'SENTINEL-ANTHROPIC-aaa11111',
                 'OPENAI_API_KEY': 'SENTINEL-OPENAI-bbb22222',
                 'DEEPSEEK_API_KEY': 'SENTINEL-DEEPSEEK-ccc33333'}
    saved = {k: os.environ.get(k) for k in sentinels}
    os.environ.update(sentinels)
    os.environ['CLAUDECODE'] = '1'
    tmp = tempfile.TemporaryDirectory()
    try:
        # D1 native provider envs
        codex = native.child_env('codex')
        claude = native.child_env('claude')
        unknown = native.child_env('weird-provider')
        check('D1a codex child keeps only OPENAI sentinel',
              codex.get('OPENAI_API_KEY') == sentinels['OPENAI_API_KEY']
              and 'ANTHROPIC_API_KEY' not in codex and 'DEEPSEEK_API_KEY' not in codex
              and 'CLAUDECODE' not in codex, '')
        check('D1b claude child keeps only ANTHROPIC sentinel',
              claude.get('ANTHROPIC_API_KEY') == sentinels['ANTHROPIC_API_KEY']
              and 'OPENAI_API_KEY' not in claude and 'DEEPSEEK_API_KEY' not in claude
              and 'CLAUDECODE' not in claude, '')
        check('D1c unknown-provider child gets no provider key',
              not any(k in unknown for k in sentinels), '')

        # D2 internal child env + keep
        plain = internal.child_env()
        kept = internal.child_env(keep=('OPENAI_API_KEY',))
        check('D2a internal child env strips all three',
              not any(k in plain for k in sentinels), '')
        check('D2b keep names exactly the credential that is kept',
              kept.get('OPENAI_API_KEY') == sentinels['OPENAI_API_KEY']
              and 'ANTHROPIC_API_KEY' not in kept and 'DEEPSEEK_API_KEY' not in kept, '')

        # D3 test-command env strips all three
        tcm = host_runtime.test_command_env()
        check('D3 test command env strips all three',
              not any(k in tcm for k in sentinels) and 'PATH' in tcm, '')

        # D4 real subprocess boundary (cmd.exe child inherits only the filtered env)
        proc = subprocess.run(['cmd', '/c', 'set'], env=native.child_env('codex'),
                              capture_output=True, text=True, timeout=30)
        text = (proc.stdout or '') + (proc.stderr or '')
        check('D4a real codex-policy child: OPENAI present, others absent',
              sentinels['OPENAI_API_KEY'] in text
              and sentinels['ANTHROPIC_API_KEY'] not in text
              and sentinels['DEEPSEEK_API_KEY'] not in text, '')
        proc = subprocess.run(['cmd', '/c', 'set'], env=host_runtime.test_command_env(),
                              capture_output=True, text=True, timeout=30)
        text = (proc.stdout or '') + (proc.stderr or '')
        check('D4b real test-command child: no provider sentinel present',
              not any(v in text for v in sentinels.values()), '')

        # D5 the production spawn site (NativeAdapter.execute) honours child_env
        printer = 'import os,json;print(json.dumps(dict(os.environ)))'

        class ProbeNative(native.NativeAdapter):
            def argv(self, session_id=None):
                return [sys.executable, '-c', printer]

        adapter = ProbeNative('codex', Path(tmp.name) / 'ws', Path(tmp.name) / 'logs')
        adapter.execute('hello', run_id='ra_creds_exec')
        out = (Path(tmp.name) / 'logs' / 'ra_creds_exec.stdout').read_text(encoding='utf-8', errors='replace')
        child_env_seen = json.loads(out.strip().splitlines()[-1])
        check('D5 production native execute drops foreign credentials',
              child_env_seen.get('OPENAI_API_KEY') == sentinels['OPENAI_API_KEY']
              and 'ANTHROPIC_API_KEY' not in child_env_seen
              and 'DEEPSEEK_API_KEY' not in child_env_seen
              and 'CLAUDECODE' not in child_env_seen, '')

        # D6 redaction of anything durable
        durable = 'token=%s plus sk-ABCDEFGH12345XYZ' % sentinels['OPENAI_API_KEY']
        cleaned = internal.redact(durable)
        check('D6 durable text redacts live key values and secret shapes',
              sentinels['OPENAI_API_KEY'] not in cleaned and 'sk-ABCDEFGH12345XYZ' not in cleaned
              and '[redacted]' in cleaned, cleaned)
    finally:
        tmp.cleanup()
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        os.environ.pop('CLAUDECODE', None)


def section_e():
    """Path containment: canonical battery + the universal-root sibling probe.

    E5 is EXPECTED TO FAIL and is evidence for a re-audit finding: under the
    universal root '.', escape ('..') and absolute spellings are reported as
    contained, contradicting the repaired docstring's own rule that such paths
    "can never be contained in a relative scope".
    """
    from kel.workforce import _path_within, authority_within
    B = chr(92)

    cases = [
        ('..', 'src', False), ('a/../..', 'src', False), ('.', 'src', False),
        ('src', 'src', True), ('src/', 'src', True), ('src/child', 'src', True),
        ('src//child', 'src', True), ('src/./child', 'src', True),
        ('src' + B + 'child', 'src', True), ('src' + B + '..' + B + 'secrets', 'src', False),
        ('src/../src/child', 'src', True), ('..' + B + '..' + B + 'x', 'src', False),
        ('C:' + B + 'x', 'src', False), ('C:/x', 'src', False), ('/etc/passwd', 'src', False),
        ('C:evil', 'src', False), ('src2/child', 'src', False), ('src2', 'src', False),
        ('//srv/share', 'src', False), ('src/child/../..', 'src', False),
        ('SRC/child', 'src', False), ('src/child ', 'src', True), (' src/child', 'src', True),
        ('anything', '.', True), ('src/child', '.', True), ('', 'src', False),
    ]
    bad = []
    for path, root, expected in cases:
        got = _path_within(path, root)
        if got != expected:
            bad.append((path, root, expected, got))
    check('E1 concrete-root canonical battery (%d cases)' % len(cases), not bad, str(bad))

    aw = [
        ({'write_scope': ['src2']}, {'write_scope': ['src']}, 'write_scope'),
        ({'write_scope': ['src/../secrets']}, {'write_scope': ['src']}, 'write_scope'),
        ({'write_scope': ['src/child']}, {'write_scope': ['src']}, None),
        ({'write_scope': ['src']}, {'write_scope': ['src']}, None),
        ({'write_scope': ['C:/x']}, {'write_scope': ['src']}, 'write_scope'),
    ]
    bad2 = []
    for child, parent, expected in aw:
        got = authority_within(child, parent)
        if (got is None) != (expected is None) or (got is not None and expected and not got.startswith(expected)):
            bad2.append((child, parent, expected, got))
    check('E2 authority_within concrete-root narrowing', not bad2, str(bad2))

    clean_cases = [('..', True), ('.', True), ('a/../b', True), ('/abs', True),
                   ('C:/x', True), ('~/x', True), ('src/file.txt', False),
                   ('x..y', False), ('a/./b', False)]
    clean_bad = []
    for value, should_raise in clean_cases:
        try:
            parallel._clean_path(value)
            got_raise = False
        except PolicyError:
            got_raise = True
        if got_raise != should_raise:
            clean_bad.append((value, should_raise, got_raise))
    check('E3 parallel._clean_path refusals', not clean_bad, str(clean_bad))

    unresolved = guardrails.protected_reason(Path('C:/Users/Nick/../Windows/System32'))
    resolved = guardrails.protected_reason(Path('C:/Windows/System32').resolve())
    check('E4 guardrails observation (resolved denied; lexical spelling misses)',
          resolved is not None, 'unresolved=%r resolved=%r' % (unresolved, resolved))

    u1 = _path_within('..', '.')
    u2 = _path_within('../x', '.')
    u3 = _path_within('C:/x', '.')
    u4 = _path_within('/x', '.')
    u5 = authority_within({'write_scope': ['..']}, {'write_scope': ['.']})
    check('E5 universal-root escapes reported contained (expected FAIL = candidate finding)',
          (u1 is False and u2 is False and u3 is False and u4 is False and u5 is not None),
          '..->%s ../x->%s C:/x->%s /x->%s authority_within->%r' % (u1, u2, u3, u4, u5))


def section_f():
    dc = capabilities.directive_clauses
    fires = [
        ('GET /a/[kel:web=off] 200', True), ('A,[kel:web=off],B', True),
        ('[Kel:Web=OFF]', True), ('please [kel:terminal=on] now', True),
        ('[web: off]', False), ('[kel:web]', False), ('[kel:foo=off]', False),
        ('[kel:web=maybe]', False), ('[[kel:web=off]]', False), ('[kel:web=off]]', False),
        ('x[kel:web=off]', False), ('[kel:web=off]x', False),
        ('"[kel:web=off]"', False), ('`[kel:web=off]`', False),
        ('```\n[kel:web=off]\n```', False), ('https://[kel:web=off]', False),
        ('see https://x/[kel:web=off]', False), ('x' * 2001 + '[kel:web=off]', False),
    ]
    bad = []
    for text, expected in fires:
        got = len(dc(text)) > 0
        if got != expected:
            bad.append((text[:40], expected, got))
    check('F1 directive firing matrix matches the aligned wording', not bad, str(bad))
    multi = dc('[kel:web=off] and [kel:files=on] then [kel:web=on]')
    check('F2 multiple clauses in source order',
          [c['capability'] for c in multi] == ['web', 'files', 'web']
          and [c['state'] for c in multi] == ['off', 'on', 'on'], str(multi))


def main():
    print('cwd=%s' % os.getcwd())
    print('=== RA engine attack battery (part 2: budget / credentials / path / wording) ===')
    section_c()
    section_d()
    section_e()
    section_f()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print('=== SUMMARY: %d checks, %d failed ===' % (len(RESULTS), len(failed)))
    for name in failed:
        print('FAILED:', name)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
