"""D3 for code: parallel coding streams, each in its own project copy, then one integration step.

Design: `docs/v2/design/D-66_WORKFORCE_LIVE.md` §3b (phase 3); workforce-os doc 05 (D3, R1/R2/R6/R8/R9)
and doc 15 §5.5. The isolation primitive is `coding.snapshot` (through `parallel.open_stream`); the
disjoint-write rule, the leases and the stream rows are `kel/parallel.py`'s.

Shape of a parallel coding contract (frozen at intake, never re-decided):

- `stream-1..stream-N` (N = 2..3, no dependencies): one Builder each, in its own project copy, owning
  only its declared files. Each part runs the project's tests and the D-71 original-tests check in its
  own copy, like any code change; a part that changes a file it does not own fails its check.
- `code` (depends on every part): the integration step. Kel applies each part's checked patch in plan
  order onto one fresh copy of the project — that copy is the job's one `code_workspaces` row, so
  apply, Undo, the Verifier, Sentinel, the Oracle, the Red Team and the work card read it exactly as
  they read a one-step change — then runs the full tests and the original-tests check on the combined
  result. A part that does not fit (its patch is refused, or two parts touched one file) is a
  conflict: the integration step falls back to sequential work — a Builder does the remaining parts
  one after another on top of the combined code — and the normal checks follow.

Restart safety: a stream's copy and baseline are written in one transaction with its `mission_streams`
row; the combined copy is built in a scratch folder and becomes visible (`code_workspaces` +
`code_integrations`, one transaction) only after every patch was applied, so a crash mid-merge is
rebuilt from a fresh copy and a patch is never applied twice.
"""
import contextlib
import json
import os
import re
import time
from pathlib import Path

from .core import PolicyError, digest, encode, validate_contract

INTEGRATION = 'code'
STREAM_PREFIX = 'stream-'
MAX_PATHS = 8
LEASE_TTL = 3600  # a coding turn plus two test runs; the lease is checked once the turn is over
MERGE_STRATEGY = ("Kel applies each part's checked change in plan order onto one fresh copy of the project, "
                  "then runs all the project's tests and the original-tests check on the combined result")

# "Never parallelise sequential work": words that order the parts keep them in one step.
SEQUENTIAL = re.compile(r"\b(?:then|after (?:that|this|which|it)|afterwards|once (?:that|this|it)|"
                        r"based on|building on|build on|depend\w*|on top of|uses? the new|using the new|"
                        r"so that it uses|step by step)\b", re.I)
MANY = re.compile(r'\b(?:two|three|2|3|several|multiple|each|both|separate|independent)\b', re.I)
CODE_FILE = re.compile(r'\b[\w./-]+\.(?:py|js|mjs|cjs|ts|tsx|jsx|go|rs|rb|java|kt|cs|cpp|cc|c|h|hpp|php|'
                       r'swift|sql|sh|ps1|html|css|scss|json|toml|ya?ml|md)\b', re.I)
LIST_ITEM = re.compile(r'^\s*(?:[-*•]|\d+[.)])\s+\S', re.M)

DDL = """
CREATE TABLE IF NOT EXISTS code_stream_workspaces(
  job_id TEXT NOT NULL, milestone_id TEXT NOT NULL, stream_id TEXT NOT NULL, path TEXT NOT NULL,
  base TEXT NOT NULL, manifest TEXT NOT NULL, PRIMARY KEY(job_id, milestone_id));
CREATE TABLE IF NOT EXISTS code_integrations(
  job_id TEXT PRIMARY KEY, state TEXT NOT NULL, applied TEXT NOT NULL, conflicts TEXT NOT NULL,
  manifest TEXT NOT NULL, at REAL NOT NULL);
"""


def ensure_schema(store):
    from .parallel import ensure_schema as ensure_parallel
    ensure_parallel(store)
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)


def _short(text, limit=70):
    words = ' '.join(str(text or '').split())
    return words if len(words) <= limit else words[:limit - 1].rsplit(' ', 1)[0] + '…'


# ---- planning (intake) ------------------------------------------------------------------------

def worth_planning(text):
    """A cheap first reading: could this request hold two or three separate code changes? Only then
    does Kel ask its planner (one model call). Ordered work never qualifies."""
    text = str(text or '')
    if SEQUENTIAL.search(text):
        return False
    files = {m.group(0).lower() for m in CODE_FILE.finditer(text)}
    return bool(MANY.search(text) or len(files) >= 2 or len(LIST_ITEM.findall(text)) >= 2)


def project_files(root, limit=300):
    """Tracked and untracked (not ignored) project files for the planner, bounded."""
    from .coding import git
    try:
        names = git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')
    except PolicyError:
        return []
    listed = sorted({os.fsdecode(n) for n in names if n})
    return listed[:limit]


def validate_parts(request, value, command):
    """The planner's proposal, validated deterministically (doc 05 R2/R9). Returns the stream specs
    or raises PolicyError with the plain reason the parts will run as one step."""
    from .coding import suite_role
    from .parallel import STREAM_LIMIT, _clean_path, plan_streams
    if not isinstance(value, dict) or value.get('independent') is not True:
        raise PolicyError('the plan found one change, or parts that depend on each other')
    parts = value.get('parts')
    if not isinstance(parts, list) or not 2 <= len(parts) <= STREAM_LIMIT:
        raise PolicyError('the plan did not split into two or three parts')
    if SEQUENTIAL.search(request or ''):
        raise PolicyError('the request orders its parts, so they run one after another')
    out, quotes = [], set()
    for index, part in enumerate(parts, 1):
        if not isinstance(part, dict):
            raise PolicyError('a planned part was not readable')
        quote = str(part.get('source_quote') or '').strip()
        if not quote or quote not in request:
            raise PolicyError('every part must quote the request exactly')
        if quote.lower() in quotes:
            raise PolicyError('two parts quoted the same words')
        quotes.add(quote.lower())
        paths = part.get('write_paths')
        if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_PATHS:
            raise PolicyError('every part must name the files it writes (at most %d)' % MAX_PATHS)
        cleaned = sorted({_clean_path(p, 'part file') for p in paths})
        shared = [p for p in cleaned if suite_role(p, command) == 'setup']
        if shared:
            raise PolicyError('part %d changes shared test setup (%s), so the parts cannot run side by side'
                              % (index, shared[0]))
        objective = _short(part.get('objective') or quote, 400)
        out.append({'id': STREAM_PREFIX + str(index), 'quote': quote, 'objective': objective,
                    'label': _short(objective, 70), 'write_paths': cleaned})
    plan_streams({'streams': [{'name': s['id'], 'objective': s['objective'], 'write_paths': s['write_paths']}
                              for s in out], 'merge_strategy': MERGE_STRATEGY})  # disjoint writes (R9)
    return out


def parallel_contract(single, parts):
    """A compiled one-step coding contract turned into parallel parts plus the integration step."""
    spec = next(m for m in single['milestones'] if m['id'] == INTEGRATION)
    total = len(parts)
    milestones = []
    for index, part in enumerate(parts, 1):
        milestones.append({
            'id': part['id'], 'filename': part['id'] + '.md', 'depends_on': [],
            'objective': ('Complete part %d of %d of the source request: %s\nKel planned it as: %s\n'
                          'You own only these files: %s. The other parts are built at the same time by other '
                          'Builders in separate copies of the project; do not create, change or delete any '
                          'other file.' % (index, total, part['quote'], part['objective'],
                                           ', '.join(part['write_paths']))),
            'write_paths': list(part['write_paths']),
            'checks': [{'kind': 'min_chars', 'value': 40}]})
    integration = dict(spec, depends_on=[p['id'] for p in parts])
    contract = dict(single)
    contract['milestones'] = milestones + [integration]
    contract['final_milestone'] = INTEGRATION
    contract['compiler'] = 'coding-parallel-v1'
    contract['code_streams'] = {'schema': 1, 'order': [p['id'] for p in parts], 'streams': parts,
                                'merge_strategy': MERGE_STRATEGY,
                                'single': {'milestones': single['milestones'], 'compiler': single['compiler']}}
    return validate_contract(contract)


def collapse(contract, why):
    """Back to the one-step coding contract (the parts run as one Builder's change), with the reason."""
    record = contract.get('code_streams')
    if not record:
        return contract
    contract['milestones'] = record['single']['milestones']
    contract['compiler'] = record['single']['compiler']
    contract.pop('final_milestone', None)
    contract.pop('code_streams', None)
    contract['code_plan'] = {'parts': len(record['streams']), 'ran_as': 'one step', 'why': str(why)[:300]}
    return validate_contract(contract)


def stream_of(contract, milestone_id):
    record = (contract or {}).get('code_streams')
    if not isinstance(record, dict):
        return None
    return next((s for s in record.get('streams') or [] if s.get('id') == milestone_id), None)


def is_integration(contract, milestone_id):
    return isinstance((contract or {}).get('code_streams'), dict) and milestone_id == INTEGRATION


def step_label(contract, milestone_id):
    """Plain words for a step of a parallel coding job (the work card), else None."""
    record = (contract or {}).get('code_streams')
    if not isinstance(record, dict):
        return None
    if milestone_id == INTEGRATION:
        return 'combining the parts'
    order = record.get('order') or []
    stream = stream_of(contract, milestone_id)
    if not stream or milestone_id not in order:
        return None
    return 'part %d of %d: %s' % (order.index(milestone_id) + 1, len(order), stream.get('label') or stream['quote'])


# ---- stream copies and leases (execution) -----------------------------------------------------

def workspace_row(store, job_id, milestone_id):
    """{path, base, manifest} of the copy a step works in: a part's own copy, else the job's one copy."""
    with contextlib.closing(store.connect()) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='code_stream_workspaces'").fetchone():
            row = db.execute('SELECT path, base, manifest, stream_id FROM code_stream_workspaces '
                             'WHERE job_id=? AND milestone_id=?', (job_id, milestone_id)).fetchone()
            if row:
                return dict(row)
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='code_workspaces'").fetchone():
            return None
        row = db.execute('SELECT path, base, manifest FROM code_workspaces WHERE job_id=?', (job_id,)).fetchone()
    return dict(row) if row else None


def stream_workspace(store, job, milestone_id):
    """The part's own project copy, made on first use (restart-safe: the copy, its baseline and its
    stream row are recorded in one transaction; an unrecorded leftover copy is rebuilt)."""
    from .coding import _remove_tree, file_manifest
    from .parallel import open_stream
    ensure_schema(store)
    row = workspace_row(store, job['id'], milestone_id)
    if row and row.get('stream_id'):
        return row
    stream = stream_of(job['contract'], milestone_id)
    if not stream:
        raise PolicyError('Unknown part of this coding job: %s' % milestone_id)
    target = store.root / 'missions' / job['id'] / 'streams' / milestone_id
    _remove_tree(target)  # a copy made before a crash that never got its row

    def record(db, opened):
        manifest = file_manifest(opened['workspace'])
        db.execute('INSERT INTO code_stream_workspaces VALUES(?,?,?,?,?,?)',
                   (job['id'], milestone_id, opened['stream_id'], opened['workspace'], opened['base'],
                    encode(manifest)))
    open_stream(store, mission_id=job['id'], task_id=milestone_id, name=milestone_id,
                source_root=job['contract']['root'], write_paths=stream['write_paths'], record=record)
    return workspace_row(store, job['id'], milestone_id)


def take_lease(store, job_id, milestone_id, run_id):
    """The part's exclusive write lease for this run (a lease an earlier run of the part left behind is
    revoked first; two parts' leases can never overlap — `parallel.acquire_lease`)."""
    from .parallel import acquire_lease, leases, release_lease
    row = workspace_row(store, job_id, milestone_id)
    for lease in leases(store, stream_id=row['stream_id'], state='ACTIVE'):
        release_lease(store, lease['lease_id'], state='REVOKED', note='replaced by run %s' % run_id)
    return acquire_lease(store, stream_id=row['stream_id'], owner='run:' + str(run_id), ttl=LEASE_TTL)


def release(store, lease):
    from .parallel import release_lease
    if lease:
        try:
            release_lease(store, lease['lease_id'])
        except PolicyError:
            pass


def _owned(path, write_paths):
    folded = path.casefold()
    return any(folded == p.casefold() or folded.startswith(p.casefold() + '/') for p in write_paths)


def ownership(store, lease, baseline, after, write_paths):
    """What the part changed, and anything it changed outside its own files (which fails its check).
    The files it owns are re-checked against its live lease (fails closed)."""
    from .parallel import assert_writable
    changed = sorted(p for p in set(baseline) | set(after) if baseline.get(p) != after.get(p))
    outside = [p for p in changed if not _owned(p, write_paths)]
    inside = [p for p in changed if _owned(p, write_paths)]
    if inside and lease:
        assert_writable(store, lease['lease_id'], inside)
    return {'owned': list(write_paths), 'changed': changed, 'outside': outside}


def restore_outside(workspace, base, baseline, write_paths):
    """Before a part's next turn: put every file it does not own back as it was in its copy (an earlier
    try's stray change is refused, never carried into the retry). Returns the paths put back."""
    from .coding import _baseline_bytes, file_manifest
    current = file_manifest(workspace)
    restored = []
    for path in sorted(set(baseline) | set(current)):
        if baseline.get(path) == current.get(path) or _owned(path, write_paths):
            continue
        target = Path(workspace) / path
        if path not in baseline:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_baseline_bytes(workspace, base, path, baseline[path]))
        restored.append(path)
    return restored


def ownership_words(outside):
    from .coding import _names
    return ('This part changed %s it does not own: %s. Each part may change only its own files, because '
            'the other parts are built at the same time.' % ('a file' if len(outside) == 1 else 'files',
                                                            _names(outside)))


# ---- integration ------------------------------------------------------------------------------

def integration(store, job_id):
    ensure_schema(store)
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM code_integrations WHERE job_id=?', (job_id,)).fetchone()
    if not row:
        return None
    out = dict(row)
    for key in ('applied', 'conflicts', 'manifest'):
        out[key] = json.loads(out[key])
    return out


def _apply_change(source, target, changed, after, mid):
    """Apply one part's checked change: every file it changed, byte for byte from its own copy (each
    checked against the digest its tests ran on), and every file it removed."""
    for path in changed:
        dest = Path(target) / path
        if after.get(path) is None:
            if dest.exists():
                dest.unlink()
            continue
        raw = (Path(source) / path).read_bytes()
        if digest(raw) != after[path]:
            raise PolicyError('Part %s changed after its check (%s); nothing was combined' % (mid, path))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)


def integrate(store, job):
    """Combine the accepted parts in plan order onto one fresh project copy (the job's one copy).

    Idempotent: once recorded it is returned as it is. Before that, the copy is built in a scratch
    folder and recorded only after every patch was tried, so a crash can never apply a patch twice.
    """
    from .coding import _remove_tree, file_manifest, git, snapshot
    ensure_schema(store)
    done = integration(store, job['id'])
    if done and workspace_row(store, job['id'], INTEGRATION):
        return done
    contract = job['contract']
    record = contract['code_streams']
    repos = store.root / 'repositories'
    repos.mkdir(parents=True, exist_ok=True)
    final, scratch = repos / job['id'], repos / (job['id'] + '.merging')
    _remove_tree(scratch)
    _remove_tree(final)  # nothing recorded points at it yet
    base = snapshot(contract['root'], scratch)
    baseline = file_manifest(scratch)
    applied, conflicts, owners = [], [], {}
    with contextlib.closing(store.connect()) as db:
        for mid in record['order']:
            milestone = job['milestones'][mid]
            run_id = (milestone.get('artifact') or {}).get('run_id')
            if milestone.get('state') != 'ACCEPTED' or not run_id:
                raise PolicyError('Part %s is not checked yet; nothing was combined' % mid)
            evidence = db.execute('SELECT patch, manifest FROM code_evidence WHERE run_id=?', (run_id,)).fetchone()
            own = db.execute('SELECT path, manifest FROM code_stream_workspaces WHERE job_id=? AND milestone_id=?',
                             (job['id'], mid)).fetchone()
            if not evidence or not own:
                raise PolicyError('Kel has no record of the checked change for part %s' % mid)
            before, after = json.loads(own['manifest']), json.loads(evidence['manifest'])
            changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
            clash = sorted({owners[p.casefold()] for p in changed if p.casefold() in owners})
            if clash:
                conflicts.append({'stream': mid, 'kind': 'same-file', 'with': clash,
                                  'paths': [p for p in changed if p.casefold() in owners]})
                continue
            moved = [p for p in changed if baseline.get(p) != before.get(p)]
            if moved:
                # Like a patch that no longer applies: the project's own copy of these files changed
                # after this part copied it.
                conflicts.append({'stream': mid, 'kind': 'project-changed', 'paths': moved})
                continue
            _apply_change(Path(own['path']), scratch, changed, after, mid)
            for path in changed:
                owners[path.casefold()] = mid
            applied.append({'stream': mid, 'files': changed,
                            'patch': 'sha256:' + digest((evidence['patch'] or '').encode())})
    git(scratch, 'add', '-A')
    merged = file_manifest(scratch)
    os.replace(scratch, final)
    state = 'CONFLICT' if conflicts else 'CLEAN'
    with store.transaction() as db:
        if db.execute('SELECT 1 FROM code_workspaces WHERE job_id=?', (job['id'],)).fetchone():
            raise PolicyError('The combined copy was recorded twice')
        db.execute('INSERT INTO code_workspaces VALUES(?,?,?,?)', (job['id'], str(final), base, encode(baseline)))
        db.execute('INSERT INTO code_integrations VALUES(?,?,?,?,?,?)',
                   (job['id'], state, encode(applied), encode(conflicts), encode(merged), time.time()))
    _settle_streams(store, job['id'])
    return integration(store, job['id'])


def _settle_streams(store, job_id):
    """The parts are finished once combined: their stream rows close and any lease left is released."""
    from .parallel import close_stream, leases, release_lease, streams
    for row in streams(store, mission_id=job_id):
        if row['state'] in ('OPEN', 'RUN'):
            with contextlib.suppress(PolicyError):
                close_stream(store, row['stream_id'], state='DONE')
    for lease in leases(store, mission_id=job_id, state='ACTIVE'):
        with contextlib.suppress(PolicyError):
            release_lease(store, lease['lease_id'])


def integration_turn(store, job, run_id):
    """None when the combined copy needs no model turn (every part fitted and nothing was checked on it
    yet); otherwise the instructions for the Builder doing the remaining work in order."""
    record = integration(store, job['id'])
    if record is None:
        return None
    with contextlib.closing(store.connect()) as db:
        earlier = db.execute("SELECT 1 FROM code_evidence e JOIN runs r ON r.id=e.run_id WHERE r.job_id=? "
                             "AND r.milestone_id=? AND r.id<>?", (job['id'], INTEGRATION, run_id)).fetchone()
    if record['state'] == 'CLEAN' and not earlier:
        return None
    lines = []
    if record['conflicts']:
        lines.append('Kel combined the parts that fitted into this copy. These parts could not be combined '
                     'automatically, so do them now, one after another, on top of the combined code:')
        with contextlib.closing(store.connect()) as db:
            for conflict in record['conflicts']:
                stream = stream_of(job['contract'], conflict['stream']) or {}
                run = (job['milestones'].get(conflict['stream']) or {}).get('artifact') or {}
                row = db.execute('SELECT patch FROM code_evidence WHERE run_id=?', (run.get('run_id'),)).fetchone()
                patch = (row['patch'] if row else '') or ''
                lines.append('- Part: %s (files: %s). Its checked change in its own copy, for reference:\n```diff\n%s\n```'
                             % (stream.get('quote'), ', '.join(stream.get('write_paths') or []),
                                patch[:6000] + ('\n…' if len(patch) > 6000 else '')))
    else:
        lines.append('Kel combined every part into this copy. Fix what the last check found; keep the '
                     "parts' accepted work.")
    return '\n'.join(lines)


def merged_result(store, job):
    """The integration step's result when every part fitted and no model turn was needed."""
    record = integration(store, job['id']) or {'applied': []}
    names = [(stream_of(job['contract'], item['stream']) or {}).get('label') or item['stream']
             for item in record['applied']]
    text = ('Kel combined %d checked parts without conflicts (%s); no model turn was needed. '
            'The combined code now goes through the full tests.' % (len(names), '; '.join(names)))
    return {'outcome': 'SUCCESS', 'text': text, 'session_id': None, 'turn_id': 'kel-integration',
            'integrated': True}


def summary(store, job_id):
    """The integration in the evidence (plain words plus the per-part facts)."""
    record = integration(store, job_id)
    if record is None:
        return None
    return {'state': record['state'].lower(), 'applied': [a['stream'] for a in record['applied']],
            'conflicts': [{'stream': c['stream'], 'kind': c['kind'], 'paths': c.get('paths') or []}
                          for c in record['conflicts']],
            'summary': ('Kel combined every part without conflicts.' if record['state'] == 'CLEAN' else
                        '%d part%s did not fit automatically; a Builder did %s on top of the combined code.'
                        % (len(record['conflicts']), '' if len(record['conflicts']) == 1 else 's',
                           'it' if len(record['conflicts']) == 1 else 'them'))}
