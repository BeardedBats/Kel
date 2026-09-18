"""Parallel mission teams: disjoint-write streams, mission leases, announce chain, integration.

Design: `ux-audit/workforce-os/15_PHASE5_IMPLEMENTATION_SPEC.md` §5.5 (parallel teams + mission
worktrees), doc 05 (tier D3 "up to three parallel streams", R8/R9 hard rules), doc 13 §2 class 3
and §4 (integration-conflict metrics), doc 07 (message/announce discipline).

The isolation primitive is `coding.snapshot` — a stream workspace is a copy of the real tracked +
untracked source state, cloned and committed, never the caller's checkout. On top of that this
module adds the part a copy cannot give you: **leases**, so two streams can never be told the same
paths are theirs to write.

Guarantees are structural, not conventional (the lesson of audits 16-19 on the finding ledger):

- A stream workspace only exists through `open_stream`, which writes the row itself.
- `run_stream` is the only execution path, and it re-derives writability from the lease row it
  reads back *inside* the same transaction that checks disjointness — there is no bypass argument.
- Disjointness is checked when a lease is taken **and** re-checked when it is used, so a lease
  granted before another stream appeared cannot be used to write into it.
- Leases carry liveness (heartbeat/expiry); reclamation only ever moves a lease out of `ACTIVE`,
  never back into it. Announce rows are append-only (SQLite triggers, mirroring migration 16).

Non-goals (spec §5.5): no depth-2 spawning, no live concurrency requirement — a caller may run
streams in threads or sequentially; this module guarantees the *isolation and accounting*, not the
scheduling. `workforce.parallel` gates every entry point and defaults off.
"""
import contextlib
import json
import time
from pathlib import Path, PurePosixPath

from .coding import git, snapshot
from .core import PolicyError, digest
from .workforce import new_id, require_text

MIGRATION_VERSION = 19
MIGRATION_NAME = 'v16-workforce-parallel'

LEASE_STATES = ('ACTIVE', 'RELEASED', 'EXPIRED', 'REVOKED')
STREAM_LIMIT = 3                 # doc 05 D3: "up to three parallel streams"
WORKER_LIMIT = 6                 # doc 05 R8: concurrent worker cap
LEASE_TTL_SECONDS = 900          # 15 minutes without a heartbeat means the owner is gone

TABLES = ('mission_streams', 'mission_leases', 'stream_announces')

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
  version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS mission_streams(
  stream_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, task_id TEXT NOT NULL, name TEXT NOT NULL,
  workspace TEXT NOT NULL, source_root TEXT NOT NULL, base TEXT NOT NULL,
  write_paths TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS mission_streams_by_mission ON mission_streams(mission_id, created);
CREATE TABLE IF NOT EXISTS mission_leases(
  lease_id TEXT PRIMARY KEY, stream_id TEXT NOT NULL, mission_id TEXT NOT NULL,
  owner TEXT NOT NULL, state TEXT NOT NULL, write_paths TEXT NOT NULL,
  heartbeat REAL NOT NULL, expires REAL NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
  note TEXT);
CREATE INDEX IF NOT EXISTS mission_leases_by_stream ON mission_leases(stream_id, state);
CREATE INDEX IF NOT EXISTS mission_leases_by_mission ON mission_leases(mission_id, state);
CREATE TABLE IF NOT EXISTS stream_announces(
  announce_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, stream_id TEXT NOT NULL,
  seq INTEGER NOT NULL, previous TEXT, write_paths TEXT NOT NULL, digest TEXT NOT NULL,
  summary TEXT NOT NULL, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS stream_announces_by_mission ON stream_announces(mission_id, seq);
CREATE TRIGGER IF NOT EXISTS stream_announces_no_update BEFORE UPDATE ON stream_announces
  BEGIN SELECT RAISE(ABORT, 'stream_announces is append-only'); END;
CREATE TRIGGER IF NOT EXISTS stream_announces_no_delete BEFORE DELETE ON stream_announces
  BEGIN SELECT RAISE(ABORT, 'stream_announces is append-only'); END;
"""


def ensure_schema(store):
    """Migration 19: parallel-mission streams, leases and the announce chain (additive)."""
    with contextlib.closing(store.connect()) as db:
        db.executescript(DDL)
        if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                          (MIGRATION_VERSION,)).fetchone():
            db.execute('INSERT INTO schema_migrations(version,name,applied,note) VALUES(?,?,?,?)',
                       (MIGRATION_VERSION, MIGRATION_NAME, time.time(),
                        'mission_streams/mission_leases/stream_announces (doc 15 5.5)'))
    return True


# ---- path discipline -------------------------------------------------------------------------

def _clean_path(value, field='write path'):
    require_text(value, field)
    text = str(value).replace('\\', '/')
    # Absolute, drive-letter and home-relative forms are refused *before* any normalisation:
    # stripping a leading slash would silently turn '/etc/passwd' into an accepted relative path.
    if (text.startswith('/') or text.startswith('~')
            or (len(text) > 1 and text[1] == ':')):
        raise PolicyError('%s must be a relative path inside the mission source (got %r)'
                          % (field, value))
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in ('..', '.') for part in path.parts) or not path.parts:
        raise PolicyError('%s must be a relative path inside the mission source (got %r)'
                          % (field, value))
    return path.as_posix()


def _clean_paths(values, field='write_paths'):
    if isinstance(values, str) or not values:
        raise PolicyError('%s must be a non-empty list of relative paths' % field)
    cleaned = [_clean_path(item, field) for item in values]
    return sorted(set(cleaned))


def _fold(path):
    """Case-folded comparison key (audit 20, F20-4)."""
    return str(path).casefold()


def _overlap(left, right):
    """The first pair of declared paths that could touch the same file (equal or nested).

    Comparison is case-folded: `Src/alpha` and `src/alpha` are the same file on the hosts these
    mission copies run on, so they can never be handed to two streams (audit 20, F20-4). The
    original spellings are returned so the message shows what the caller actually wrote.
    """
    for one in left:
        for two in right:
            folded_one, folded_two = _fold(one), _fold(two)
            if (folded_one == folded_two or folded_one.startswith(folded_two + '/')
                    or folded_two.startswith(folded_one + '/')):
                return (one, two)
    return None


def _pairs(items):
    for index, first in enumerate(items):
        for second in items[index + 1:]:
            yield first, second


# ---- decomposition statement (doc 05 R9) -----------------------------------------------------

def plan_streams(decomposition, *, max_streams=STREAM_LIMIT):
    """Validate the D3 decomposition statement: what runs in parallel, why it is independent, how
    the outputs merge (doc 05 R9). Refuses anything the later steps would have to guess about."""
    if not isinstance(decomposition, dict):
        raise PolicyError('A parallel mission needs a decomposition statement')
    streams = decomposition.get('streams')
    if not isinstance(streams, list) or not 2 <= len(streams) <= STREAM_LIMIT:
        raise PolicyError('Parallel streams are 2..%d (doc 05 D3); got %s'
                          % (STREAM_LIMIT, len(streams)
                             if isinstance(streams, list) else type(streams).__name__))
    if len(streams) > max_streams:
        raise PolicyError('This mission allows at most %d parallel streams' % max_streams)
    if len(streams) > WORKER_LIMIT:
        raise PolicyError('Concurrent worker cap is %d (doc 05 R8)' % WORKER_LIMIT)
    require_text(decomposition.get('merge_strategy'),
                 'merge strategy (how the stream outputs are combined)')
    plan = []
    for entry in streams:
        if not isinstance(entry, dict):
            raise PolicyError('Each stream is an object with a name, an objective and write_paths')
        name = entry.get('name')
        require_text(name, 'stream name')
        goal = entry.get('objective')
        require_text(goal, 'stream objective (what this stream is doing)')
        paths = _clean_paths(entry.get('write_paths'))
        entry_paths = {'name': str(name), 'objective': str(goal), 'write_paths': paths}
        if 'task_id' in entry:
            require_text(entry['task_id'], 'stream task_id')
            entry_paths['task_id'] = entry['task_id']
        plan.append(entry_paths)
    names = [item['name'] for item in plan]
    if len(set(names)) != len(names):
        raise PolicyError('Stream names must be unique: %s' % ', '.join(names))
    for first, second in _pairs(plan):
        clash = _overlap(first['write_paths'], second['write_paths'])
        if clash:
            raise PolicyError('Streams "%s" and "%s" both write %s (disjoint-write rule, doc 05 '
                              'R9): %s' % (first['name'], second['name'], clash[0], clash[1]))
    return {'streams': plan, 'merge_strategy': decomposition['merge_strategy'],
            'stream_count': len(plan),
            'rationale': ['%s writes %s' % (item['name'], ', '.join(item['write_paths']))
                          for item in plan]}


# ---- streams ---------------------------------------------------------------------------------

def _stream_row(store, stream_id):
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM mission_streams WHERE stream_id=?',
                         (stream_id,)).fetchone()
    if row is None:
        raise PolicyError('Unknown stream: %s' % stream_id)
    record = dict(row)
    # Decode once, here: every caller of this helper compares or stores the path list, and a
    # double-encoded value would silently turn "src/a" into a per-character string.
    record['write_paths'] = json.loads(record['write_paths'])
    return record


def open_stream(store, *, mission_id, task_id, name, source_root, write_paths,
                streams_root=None, now=None):
    """Create one isolated stream workspace from the real source state (never the checkout)."""
    require_text(mission_id, 'mission_id')
    require_text(task_id, 'task_id')
    require_text(name, 'stream name')
    paths = _clean_paths(write_paths)
    source = Path(source_root).resolve(strict=True)
    stamp = time.time() if now is None else now
    root = Path(streams_root) if streams_root is not None else (store.root / 'missions')
    workspace = root / mission_id / 'streams' / str(name)
    base = snapshot(source, workspace)
    stream_id = new_id('str_')
    with store.transaction() as db:
        db.execute('INSERT INTO mission_streams(stream_id,mission_id,task_id,name,workspace,'
                   'source_root,base,write_paths,state,created,updated) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (stream_id, mission_id, task_id, str(name), str(workspace), str(source), base,
                    json.dumps(paths), 'OPEN', stamp, stamp))
    return {'stream_id': stream_id, 'mission_id': mission_id, 'task_id': task_id,
            'name': str(name), 'workspace': str(workspace), 'source_root': str(source),
            'base': base, 'write_paths': paths, 'state': 'OPEN'}


def streams(store, *, mission_id):
    """Read-only stream list for a mission."""
    with contextlib.closing(store.connect()) as db:
        rows = [dict(row) for row in db.execute(
            'SELECT * FROM mission_streams WHERE mission_id=? ORDER BY created, rowid',
            (mission_id,))]
    for row in rows:
        row['write_paths'] = json.loads(row['write_paths'])
    return rows


# ---- leases ----------------------------------------------------------------------------------

def _active_leases(db, *, mission_id, exclude=None):
    rows = [dict(row) for row in db.execute(
        'SELECT * FROM mission_leases WHERE mission_id=? AND state=?', (mission_id, 'ACTIVE'))]
    for row in rows:
        row['write_paths'] = json.loads(row['write_paths'])
    if exclude is not None:
        rows = [row for row in rows if row['lease_id'] != exclude]
    return rows


def leases(store, *, mission_id=None, stream_id=None, state=None):
    """Read-only lease list."""
    query, args = 'SELECT * FROM mission_leases', []
    clauses = []
    if mission_id is not None:
        clauses.append('mission_id=?')
        args.append(mission_id)
    if stream_id is not None:
        clauses.append('stream_id=?')
        args.append(stream_id)
    if state is not None:
        clauses.append('state=?')
        args.append(state)
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    with contextlib.closing(store.connect()) as db:
        rows = [dict(row) for row in db.execute(query + ' ORDER BY created, rowid', args)]
    for row in rows:
        row['write_paths'] = json.loads(row['write_paths'])
    return rows


def acquire_lease(store, *, stream_id, owner, ttl=LEASE_TTL_SECONDS, now=None, note=None):
    """Take the exclusive lease for a stream's declared paths.

    Refused when the stream already holds a live lease, when another live lease overlaps the
    declared paths, or when the ttl is not a sane positive number.
    """
    stream = _stream_row(store, stream_id)
    require_text(owner, 'lease owner')
    if not isinstance(ttl, (int, float)) or ttl <= 0:
        raise PolicyError('Lease ttl must be a positive number of seconds')
    stamp = time.time() if now is None else now
    paths = stream['write_paths']
    lease_id = new_id('lse_')
    with store.transaction() as db:
        for row in _active_leases(db, mission_id=stream['mission_id']):
            if row['stream_id'] == stream_id:
                raise PolicyError('Stream %s already holds an active lease (%s)'
                                  % (stream['name'], row['lease_id']))
            if row['expires'] <= stamp:
                # Lapsed: retire it here, in the same transaction that grants the new lease. A
                # lease nobody heartbeats must not be able to block new work, and it must not be
                # able to come back either (audit 20, F20-5).
                db.execute('UPDATE mission_leases SET state=?, updated=?, note=? WHERE lease_id=?',
                           ('EXPIRED', stamp, 'reclaimed at acquisition', row['lease_id']))
                continue
            clash = _overlap(paths, row['write_paths'])
            if clash:
                raise PolicyError('Lease refused: stream "%s" and stream of lease %s overlap on '
                                  '%s/%s (disjoint-write rule)' % (stream['name'], row['lease_id'],
                                                                   clash[0], clash[1]))
        db.execute('INSERT INTO mission_leases(lease_id,stream_id,mission_id,owner,state,'
                   'write_paths,heartbeat,expires,created,updated,note) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (lease_id, stream_id, stream['mission_id'], str(owner), 'ACTIVE',
                    json.dumps(paths), stamp, stamp + ttl, stamp, stamp, note))
    return {'lease_id': lease_id, 'stream_id': stream_id, 'mission_id': stream['mission_id'],
            'owner': str(owner), 'state': 'ACTIVE', 'write_paths': paths,
            'heartbeat': stamp, 'expires': stamp + ttl}


def heartbeat(store, lease_id, *, now=None, ttl=LEASE_TTL_SECONDS):
    """Refresh a live lease. A retired lease can never be revived."""
    stamp = time.time() if now is None else now
    with store.transaction() as db:
        row = db.execute('SELECT * FROM mission_leases WHERE lease_id=?', (lease_id,)).fetchone()
        if row is None:
            raise PolicyError('Unknown lease: %s' % lease_id)
        if row['state'] != 'ACTIVE':
            raise PolicyError('Lease %s is %s; a retired lease cannot be revived'
                              % (lease_id, row['state']))
        if row['expires'] <= stamp:
            # A lapsed lease is reclaimed, never resurrected: reviving it could leave two
            # unexpired leases over the same territory (audit 20, F20-5).
            raise PolicyError('Lease %s lapsed at %.3f; reclaim it before any heartbeat'
                              % (lease_id, row['expires']))
        db.execute('UPDATE mission_leases SET heartbeat=?, expires=?, updated=? WHERE lease_id=?',
                   (stamp, stamp + ttl, stamp, lease_id))
    return {'lease_id': lease_id, 'state': 'ACTIVE', 'heartbeat': stamp, 'expires': stamp + ttl}


def reclaim_stale_leases(store, *, now=None):
    """Retire every lease whose owner stopped heartbeating before its expiry (doc 15 §5.5:
    heartbeat reclamation from the existing runner patterns). Returns the reclaimed ids."""
    stamp = time.time() if now is None else now
    reclaimed = []
    with store.transaction() as db:
        rows = [dict(row) for row in db.execute(
            'SELECT * FROM mission_leases WHERE state=? AND expires<=?', ('ACTIVE', stamp))]
        for row in rows:
            db.execute('UPDATE mission_leases SET state=?, updated=?, note=? WHERE lease_id=?',
                       ('EXPIRED', stamp, 'reclaimed: no heartbeat before expiry', row['lease_id']))
            reclaimed.append(row['lease_id'])
    return reclaimed


def release_lease(store, lease_id, *, state='RELEASED', note=None, now=None):
    """Retire a lease deliberately (owner finished or aborted)."""
    if state not in ('RELEASED', 'REVOKED'):
        raise PolicyError('A deliberate release is RELEASED or REVOKED (got %s)' % state)
    stamp = time.time() if now is None else now
    with store.transaction() as db:
        row = db.execute('SELECT * FROM mission_leases WHERE lease_id=?', (lease_id,)).fetchone()
        if row is None:
            raise PolicyError('Unknown lease: %s' % lease_id)
        if row['state'] == 'ACTIVE':
            db.execute('UPDATE mission_leases SET state=?, updated=?, note=COALESCE(?,note) '
                       'WHERE lease_id=?', (state, stamp, note, lease_id))
        final = db.execute('SELECT state FROM mission_leases WHERE lease_id=?',
                           (lease_id,)).fetchone()
    # Report the row's actual state: a lease that was already retired is not silently reported as
    # freshly released (audit 20, F20-8).
    return {'lease_id': lease_id, 'state': final['state']}


def assert_writable(store, lease_id, paths, *, now=None):
    """The single lease check. Fails closed; used by every write path.

    The lease must be ACTIVE and unexpired, and each path must sit inside the lease's declared
    paths. Overlapping live leases are refused here too, so a lease that became ambiguous after
    it was granted cannot be used to write into another stream's territory.
    """
    stamp = time.time() if now is None else now
    wanted = _clean_paths(list(paths), 'paths')
    with contextlib.closing(store.connect()) as db:
        row = db.execute('SELECT * FROM mission_leases WHERE lease_id=?', (lease_id,)).fetchone()
        if row is None:
            raise PolicyError('Unknown lease: %s' % lease_id)
        record = dict(row)
        if record['state'] != 'ACTIVE':
            raise PolicyError('Lease %s is %s; writes are refused' % (lease_id, record['state']))
        if record['expires'] <= stamp:
            raise PolicyError('Lease %s expired at %.3f without a heartbeat; writes are refused'
                              % (lease_id, record['expires']))
        allowed = json.loads(record['write_paths'])
        for path in wanted:
            if not any(_fold(path) == _fold(item) or _fold(path).startswith(_fold(item) + '/')
                       for item in allowed):
                raise PolicyError('Path %s is outside the lease for stream %s (declared: %s)'
                                  % (path, record['stream_id'], ', '.join(allowed)))
        others = _active_leases(db, mission_id=record['mission_id'], exclude=lease_id)
    for other in others:
        if other['expires'] <= stamp:
            continue
        clash = _overlap(json.loads(record['write_paths']), other['write_paths'])
        if clash:
            raise PolicyError('Lease %s overlaps live lease %s on %s/%s; writes are refused until '
                              'one of them is retired' % (lease_id, other['lease_id'], clash[0],
                                                          clash[1]))
    return {'lease_id': lease_id, 'stream_id': record['stream_id'], 'paths': wanted,
            'mission_id': record['mission_id']}


# ---- streams in flight -----------------------------------------------------------------------

def run_stream(store, stream_id, worker, *, lease_id, paths, now=None):
    """Run one stream's worker inside its leased paths.

    The worker is `worker(stream, allowed_paths, lease)` and must return a dict; this module owns
    the lease check, the mission/task stamping and the accounting of what the stream produced.
    """
    stream = _stream_row(store, stream_id)
    check = assert_writable(store, lease_id, paths, now=now)
    if check['stream_id'] != stream_id:
        raise PolicyError('Lease %s belongs to stream %s, not %s'
                          % (lease_id, check['stream_id'], stream_id))
    stamp = time.time() if now is None else now
    result = worker(stream, check['paths'], check)
    if result is None:
        result = {}
    if not isinstance(result, dict):
        raise PolicyError('A stream worker returns an object (got %s)' % type(result).__name__)
    with store.transaction() as db:
        db.execute('UPDATE mission_streams SET state=?, updated=? WHERE stream_id=?',
                   ('RUN', stamp, stream_id))
    return {'stream_id': stream_id, 'mission_id': stream['mission_id'], 'name': stream['name'],
            'lease_id': lease_id, 'paths': check['paths'], 'result': result, 'at': stamp}


def close_stream(store, stream_id, *, state='DONE', now=None):
    """Mark a stream finished. Only a finished stream can announce its output."""
    if state not in ('DONE', 'ABANDONED'):
        raise PolicyError('A stream closes DONE or ABANDONED (got %s)' % state)
    stamp = time.time() if now is None else now
    with store.transaction() as db:
        changed = db.execute('UPDATE mission_streams SET state=?, updated=? WHERE stream_id=? '
                             'AND state IN (?, ?)', (state, stamp, stream_id, 'OPEN', 'RUN')
                             ).rowcount
        if changed != 1:
            raise PolicyError('Stream %s is not open; it cannot be closed twice' % stream_id)
    return {'stream_id': stream_id, 'state': state}


def announce(store, *, stream_id, lease_id, summary, write_paths, now=None):
    """Append one announce row and chain it to the mission's previous announce (doc 07 discipline:
    a stream states what it changed, with a digest, in order).

    The digest is taken over the stream's staged change set and there is no caller override: the
    row must attest the output, not a claim about it (audit 21, N21-2).
    """
    stream = _stream_row(store, stream_id)
    if stream['state'] != 'DONE':
        raise PolicyError('Stream %s must be DONE before it announces its output' % stream['name'])
    assert_writable(store, lease_id, write_paths, now=now)
    require_text(summary, 'announce summary')
    paths = _clean_paths(write_paths)
    stamp = time.time() if now is None else now
    # The announce must attest the stream's real output: a stream can only announce paths it
    # actually changed, and the digest is taken over its staged change set rather than over the
    # prose (audit 20, F20-2).
    changed = _changed_paths(stream)
    for path in paths:
        if not any(_fold(item) == _fold(path)
                   or _fold(item).startswith(_fold(path) + '/') for item in changed):
            raise PolicyError('Stream %s did not change %s, so it cannot announce it (changed: %s)'
                              % (stream['name'], path, ', '.join(changed) or 'nothing'))
    workspace = Path(stream['workspace'])
    git(workspace, 'add', '-A')
    patch = git(workspace, 'diff', '--cached', '--binary', stream['base'])
    digest_value = 'sha256:' + digest(patch.decode('utf-8', 'replace'))
    announce_id = new_id('ann_')
    with store.transaction() as db:
        previous = db.execute('SELECT announce_id FROM stream_announces WHERE mission_id=? '
                              'ORDER BY seq DESC, rowid DESC LIMIT 1',
                              (stream['mission_id'],)).fetchone()
        seq = db.execute('SELECT COUNT(*) FROM stream_announces WHERE mission_id=?',
                         (stream['mission_id'],)).fetchone()[0] + 1
        db.execute('INSERT INTO stream_announces(announce_id,mission_id,stream_id,seq,previous,'
                   'write_paths,digest,summary,created) VALUES(?,?,?,?,?,?,?,?,?)',
                   (announce_id, stream['mission_id'], stream_id, seq,
                    previous['announce_id'] if previous else None, json.dumps(paths),
                    digest_value, str(summary), stamp))
    return {'announce_id': announce_id, 'stream_id': stream_id, 'seq': seq,
            'previous': previous['announce_id'] if previous else None, 'write_paths': paths,
            'digest': digest_value, 'summary': str(summary), 'created': stamp}


def announce_chain(store, mission_id):
    """The mission's announce chain in order (read-only)."""
    with contextlib.closing(store.connect()) as db:
        rows = [dict(row) for row in db.execute(
            'SELECT * FROM stream_announces WHERE mission_id=? ORDER BY seq', (mission_id,))]
    for row in rows:
        row['write_paths'] = json.loads(row['write_paths'])
    chain_ok = True
    for index, row in enumerate(rows):
        expected = None if index == 0 else rows[index - 1]['announce_id']
        if row['previous'] != expected:
            chain_ok = False
    return {'mission_id': mission_id, 'announces': rows, 'chain_ok': chain_ok,
            'streams_announced': len({row['stream_id'] for row in rows})}


def synthesize(store, mission_id):
    """Synthesize the streams' announcements into one ordered report with the merged path set."""
    chain = announce_chain(store, mission_id)
    merged = {}
    for row in chain['announces']:
        for path in row['write_paths']:
            merged.setdefault(path, []).append(row['stream_id'])
    report = {
        'mission_id': mission_id,
        'streams': [row['stream_id'] for row in streams(store, mission_id=mission_id)],
        'announced': chain['streams_announced'],
        'chain_ok': chain['chain_ok'],
        'paths': sorted(merged),
        'merged_digest': 'sha256:' + digest(json.dumps(sorted(
            (row['announce_id'], row['digest']) for row in chain['announces']))),
        'narrative': '\n'.join('%d. %s -> %s' % (row['seq'], row['stream_id'], row['summary'])
                               for row in chain['announces']),
    }
    return report


# ---- integration -----------------------------------------------------------------------------

def integrate(store, mission_id, *, integrator, target_root=None, now=None):
    """Merge the finished streams into one integration workspace (doc 15 §5.5 integration checks).

    `integrator(integration)` applies one stream's patch and returns True on success; the default
    applies each stream's diff with `git apply` and reports a conflict instead of guessing. A
    declared-path overlap between two streams is a conflict *before* any patch is attempted.
    """
    rows = streams(store, mission_id=mission_id)
    if not rows:
        raise PolicyError('Mission %s has no streams to integrate' % mission_id)
    finished = [row for row in rows if row['state'] == 'DONE']
    abandoned = [row for row in rows if row['state'] != 'DONE']
    if not finished:
        raise PolicyError('Mission %s has no finished stream to integrate (abandoned: %s)'
                          % (mission_id,
                             ', '.join(row['stream_id'] for row in abandoned) or 'none'))
    stamp = time.time() if now is None else now
    conflicts, applied = [], []
    for first, second in _pairs(finished):
        clash = _overlap(first['write_paths'], second['write_paths'])
        if clash:
            conflicts.append({'kind': 'declared-overlap', 'streams': [first['stream_id'],
                                                                     second['stream_id']],
                              'paths': sorted(set(clash))})
    root = Path(target_root) if target_root is not None else (
        Path(finished[0]['source_root']).parent / ('.kel-integration-' + mission_id))
    base = snapshot(Path(finished[0]['source_root']), root)
    def apply_patch(patch):
        """The default merge: `git apply` accepts the patch whole or raises (never half-applies)."""
        git(root, 'apply', '--binary', '-', input=patch)
        return True

    for row in finished:
        # Stage the stream's own copy first: its new files are untracked, and an unstaged diff
        # would report an empty patch and "integrate" successfully with nothing applied.
        git(Path(row['workspace']), 'add', '-A')
        patch = git(Path(row['workspace']), 'diff', '--cached', '--binary', row['base'])
        if not patch.strip():
            applied.append({'stream_id': row['stream_id'], 'applied': True, 'empty': True})
            continue
        ok, detail = True, None
        if integrator is None:
            try:
                apply_patch(patch)
            except PolicyError as exc:
                ok, detail = False, str(exc)[:200]
        else:
            # The caller's merge hook replaces the default apply; a falsy return is a conflict,
            # never a silent success (audit 20, F20-1).
            ok = bool(integrator({'stream': row, 'patch': patch, 'root': str(root)}))
            detail = None if ok else 'integrator refused the patch'
        if ok:
            applied.append({'stream_id': row['stream_id'], 'applied': True, 'empty': False})
        else:
            conflicts.append({'kind': 'patch-refused', 'streams': [row['stream_id']],
                              'detail': detail})
            applied.append({'stream_id': row['stream_id'], 'applied': False, 'empty': False})
    # Real changed-path overlaps are conflicts too: a same-file collision that `git apply` happens
    # to accept (different regions) is still a seam, so `integration_ok` can never be True over it
    # (audit 20, F20-3).
    for first, second in _pairs(finished):
        overlap = _overlap(_changed_paths(first), _changed_paths(second))
        if overlap:
            conflicts.append({'kind': 'changed-overlap', 'streams': [first['stream_id'],
                                                                     second['stream_id']],
                              'paths': sorted(set(overlap))})
    changed = git(root, 'status', '--porcelain').decode('utf-8', 'replace').strip()
    git(root, 'add', '-A')
    merged = git(root, 'diff', '--cached', '--binary', base).decode('utf-8', 'replace')
    result = {'mission_id': mission_id, 'integration_root': str(root), 'base': base,
              'streams': len(rows), 'integrated': len(finished), 'abandoned': [row['stream_id']
                                                                              for row in abandoned],
              'applied': applied, 'conflicts': conflicts, 'integration_ok': not conflicts,
              'merged_digest': 'sha256:' + digest(merged), 'changed_paths': len(
                  [line for line in changed.splitlines() if line.strip()]), 'at': stamp}
    return result


def _changed_paths(row):
    """The paths a finished stream actually changed (read-only; [] while it is not DONE).

    `git status` is used rather than `git diff`: a stream's new files are untracked until
    something stages them, and a diff-only view reports an empty change set for them — which is
    exactly how a real integration seam would go unnoticed.
    """
    if row['state'] != 'DONE':
        return []
    listing = git(Path(row['workspace']), 'status', '--porcelain', '-uall')
    changed = []
    for line in listing.decode('utf-8', 'replace').splitlines():
        if not line.strip():
            continue
        path = line[3:].split(' -> ')[-1].strip().strip('"')
        if path:
            changed.append(path)
    return sorted(set(changed))


def conflict_metrics(store, mission_id):
    """Integration-conflict metrics for the mission (doc 13 §4 'integration conflicts').

    Two measures, because they answer different questions: `declared_overlaps` are overlaps in
    the plan (which `plan_streams` already forbids, so a non-empty value means a plan was
    tampered with), and `actual_overlaps` are overlaps between what the streams *really* changed
    — the integration-seam measurement, including a stream that wrote outside its declared paths.
    `undeclared_writes` is reported separately and is deliberately **not** part of
    `conflict_count`/`conflict_rate` or of `integration_ok`: a stream that strayed inside its own
    copy is a contract deviation, not (yet) an integration conflict (audit 21, N21-5).
    """
    rows = streams(store, mission_id=mission_id)
    pairs = list(_pairs(rows))
    declared, actual_overlaps = [], []
    changed = {row['stream_id']: _changed_paths(row) for row in rows}
    undeclared = {row['stream_id']: sorted(
        path for path in changed[row['stream_id']]
        if not any(_fold(path) == _fold(item) or _fold(path).startswith(_fold(item) + '/')
                   for item in row['write_paths'])) for row in rows}
    for first, second in pairs:
        clash = _overlap(first['write_paths'], second['write_paths'])
        if clash:
            declared.append({'streams': [first['stream_id'], second['stream_id']],
                             'paths': sorted(set(clash))})
        real = _overlap(changed[first['stream_id']], changed[second['stream_id']])
        if real:
            actual_overlaps.append({'streams': [first['stream_id'], second['stream_id']],
                                    'paths': sorted(set(real))})
    chain = announce_chain(store, mission_id)
    conflicts = len(declared) + len(actual_overlaps)
    return {'mission_id': mission_id, 'streams': len(rows), 'pairs': len(pairs),
            'declared_overlaps': declared, 'actual_overlaps': actual_overlaps,
            'changed_paths': changed, 'undeclared_writes': undeclared,
            'undeclared_count': sum(len(items) for items in undeclared.values()),
            'conflict_count': conflicts,
            'announced': chain['streams_announced'], 'chain_ok': chain['chain_ok'],
            'conflict_rate': round(conflicts / len(pairs), 2) if pairs else 0.0}


def run_parallel(store, *, mission_id, decomposition, workers, source_root, task_id,
                 streams_root=None, lease_ttl=LEASE_TTL_SECONDS, tier, now=None):
    """Hands-off D3 flow: plan the decomposition, open one isolated stream per worker, lease each
    stream's paths, run the workers, close and announce in order, then integrate.

    `workers` maps a stream name to `worker(stream, allowed_paths, lease)`. Deterministic: streams
    run in plan order (a caller that wants real concurrency can run its own workers in threads —
    the leases, not the scheduler, are what this module guarantees).

    Parallel streams are a D3/D4 capability (doc 05: D3 is "up to three parallel streams"); a
    lower tier is refused rather than silently serialised.
    """
    if tier not in ('D3', 'D4'):
        raise PolicyError('Parallel streams need a D3/D4 staffing decision (doc 05); got %s' % tier)
    plan = plan_streams(decomposition, max_streams=STREAM_LIMIT)
    by_name = {}
    for entry in plan['streams']:
        by_name[entry['name']] = entry
    unknown = sorted(set(workers) - set(by_name))
    if unknown:
        raise PolicyError('No stream in the plan for worker(s): %s' % ', '.join(unknown))
    missing = sorted(set(by_name) - set(workers))
    if missing:
        raise PolicyError('Every planned stream needs a worker; missing: %s' % ', '.join(missing))
    results, opens = [], []
    for entry in plan['streams']:
        opened = open_stream(store, mission_id=mission_id, task_id=entry.get('task_id', task_id),
                             name=entry['name'], source_root=source_root,
                             write_paths=entry['write_paths'], streams_root=streams_root,
                             now=now)
        opens.append(opened)
        lease = acquire_lease(store, stream_id=opened['stream_id'], owner='stream:%s'
                              % entry['name'], ttl=lease_ttl, now=now)
        try:
            ran = run_stream(store, opened['stream_id'], workers[entry['name']],
                             lease_id=lease['lease_id'], paths=entry['write_paths'], now=now)
            close_stream(store, opened['stream_id'], state='DONE', now=now)
            announced = announce(store, stream_id=opened['stream_id'],
                                  lease_id=lease['lease_id'],
                                  summary=entry['objective'],
                                  write_paths=entry['write_paths'], now=now)
        except BaseException as exc:
            # Any failure - a PolicyError, a crash in the worker, a KeyboardInterrupt - must leave
            # the mission in a state a retry can reason about, and cleanup must never replace the
            # causal error (audit 21, N21-1). The lease is the one resource a retry cannot
            # re-derive, so it is revoked first and unconditionally; the stream is abandoned only
            # while it is still open, because a failure raised by announce leaves it DONE - a
            # valid terminal state that must not be transitioned a second time.
            try:
                release_lease(store, lease['lease_id'], state='REVOKED',
                              note='abandoned after %s' % type(exc).__name__, now=now)
            except PolicyError:
                pass  # already retired; the causal error still wins
            try:
                if _stream_row(store, opened['stream_id'])['state'] in ('OPEN', 'RUN'):
                    close_stream(store, opened['stream_id'], state='ABANDONED', now=now)
            except PolicyError:
                pass
            raise
        release_lease(store, lease['lease_id'], now=now)
        results.append({'stream': opened, 'lease': lease, 'run': ran, 'announce': announced})
    integration = integrate(store, mission_id=mission_id, integrator=None, now=now)
    return {'mission_id': mission_id, 'plan': plan, 'streams': results,
            'announce_chain': announce_chain(store, mission_id),
            'synthesis': synthesize(store, mission_id), 'integration': integration,
            'conflict_metrics': conflict_metrics(store, mission_id)}
