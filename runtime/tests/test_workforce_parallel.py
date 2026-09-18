"""Phase 5.5: parallel mission teams — disjoint-write streams, leases, announce chain, integration.

Verification for `kel/parallel.py` (workforce-os docs 05, 13 §4, 15 §5.5): the decomposition
statement is validated, every stream works in its own isolated snapshot, this module's own write
paths are fail-closed behind a live lease (a worker's own filesystem writes are detected and
reported, never silently accepted), stale leases are reclaimed by heartbeat expiry, the announce
chain is ordered, append-only and bound to the change set, and integration reports real
conflicts.
"""
import contextlib
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from kel.core import PolicyError, Store, digest
from kel.parallel import (LEASE_TTL_SECONDS, STREAM_LIMIT, TABLES, acquire_lease, announce,
                          announce_chain, assert_writable, close_stream, conflict_metrics,
                          ensure_schema, heartbeat, integrate, leases, open_stream, plan_streams,
                          reclaim_stale_leases, release_lease, run_parallel, run_stream, streams,
                          synthesize)
from kel.workforce import ensure_schema as ensure_workforce_schema

MISSION = 'mis_' + 'a' * 8
TASK = 'tsk_' + 'b' * 8


def decomposition(*, names=('alpha', 'beta'), merge='apply each stream patch in stream order'):
    return {'streams': [{'name': name, 'objective': 'Build the %s slice.' % name,
                         'task_id': TASK, 'write_paths': ['src/%s' % name]}
                        for name in names],
            'merge_strategy': merge}


def write(path, text='content\n'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def git(root, *args, **kwargs):
    done = subprocess.run(['git', *args], cwd=root, capture_output=True, **kwargs)
    if done.returncode:
        raise AssertionError(done.stderr.decode('utf-8', 'replace'))
    return done.stdout


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / 'data')
        ensure_workforce_schema(self.store)
        ensure_schema(self.store)
        self.source = self.root / 'source'
        write(self.source / 'README.md', '# project\n')
        write(self.source / 'src' / 'alpha' / 'keep.txt', 'base alpha\n')
        write(self.source / 'src' / 'beta' / 'keep.txt', 'base beta\n')
        git(self.source, 'init', '-q')
        git(self.source, '-c', 'user.name=t', '-c', 'user.email=t@localhost',
            'add', '-A')
        git(self.source, '-c', 'user.name=t', '-c', 'user.email=t@localhost',
            'commit', '-q', '-m', 'source')

    def open(self, name='alpha', paths=('src/alpha',), mission=MISSION, now=1000.0):
        return open_stream(self.store, mission_id=mission, task_id=TASK, name=name,
                           source_root=str(self.source), write_paths=list(paths),
                           streams_root=self.root / 'streams', now=now)

    def worker(self, text='stream work\n', path=None):
        def run(stream, allowed, lease):
            target = Path(stream['workspace']) / (path or (allowed[0] + '/work.txt'))
            write(target, text)
            return {'wrote': target.relative_to(stream['workspace']).as_posix()}
        return run


class SchemaTests(Base):
    def test_migration_is_recorded_and_tables_exist(self):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM schema_migrations WHERE version=?', (19,)).fetchone()
            tables = {item[0] for item in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(row['name'], 'v16-workforce-parallel')
        self.assertTrue(set(TABLES).issubset(tables))

    def test_ensure_is_idempotent(self):
        self.assertTrue(ensure_schema(self.store))
        self.assertTrue(ensure_schema(self.store))

    def test_announce_ledger_is_append_only(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w', now=1000.0)
        run_stream(self.store, stream['stream_id'], self.worker(), lease_id=lease['lease_id'],
                   paths=['src/alpha'], now=1000.5)
        close_stream(self.store, stream['stream_id'], now=1001.0)
        announce(self.store, stream_id=stream['stream_id'], lease_id=lease['lease_id'],
                 summary='done', write_paths=['src/alpha'], now=1002.0)
        with contextlib.closing(self.store.connect()) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE stream_announces SET summary='tampered'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('DELETE FROM stream_announces')


class PlanTests(Base):
    def test_valid_plan_is_accepted(self):
        plan = plan_streams(decomposition())
        self.assertEqual(plan['stream_count'], 2)
        self.assertEqual([item['name'] for item in plan['streams']], ['alpha', 'beta'])
        self.assertEqual(plan['merge_strategy'], decomposition()['merge_strategy'])

    def test_stream_count_is_bounded(self):
        for names in (('only',), ('a', 'b', 'c', 'd')):
            with self.assertRaises(PolicyError):
                plan_streams(decomposition(names=names))

    def test_merge_strategy_is_required(self):
        body = decomposition()
        body['merge_strategy'] = '  '
        with self.assertRaises(PolicyError):
            plan_streams(body)

    def test_every_stream_states_what_it_writes(self):
        body = decomposition()
        body['streams'][1]['write_paths'] = []
        with self.assertRaises(PolicyError):
            plan_streams(body)

    def test_overlapping_paths_are_refused(self):
        body = decomposition()
        body['streams'][1]['write_paths'] = ['src/alpha']
        with self.assertRaises(PolicyError):
            plan_streams(body)
        nested = decomposition()
        nested['streams'][1]['write_paths'] = ['src/alpha/nested']
        with self.assertRaises(PolicyError):
            plan_streams(nested)

    def test_duplicate_names_are_refused(self):
        with self.assertRaises(PolicyError):
            plan_streams(decomposition(names=('same', 'same')))

    def test_absolute_and_escaping_paths_are_refused(self):
        for bad in ('/etc/passwd', '../outside', 'src/../../escape'):
            body = decomposition()
            body['streams'][0]['write_paths'] = [bad]
            with self.assertRaises(PolicyError):
                plan_streams(body)


class StreamTests(Base):
    def test_open_stream_creates_an_isolated_copy(self):
        stream = self.open()
        workspace = Path(stream['workspace'])
        self.assertTrue(workspace.is_dir())
        self.assertTrue((workspace / 'src' / 'alpha' / 'keep.txt').is_file())
        self.assertEqual(git(workspace, 'rev-parse', 'HEAD').decode().strip(), stream['base'])
        write(workspace / 'src' / 'alpha' / 'keep.txt', 'changed in the stream\n')
        self.assertEqual((self.source / 'src' / 'alpha' / 'keep.txt').read_text(),
                         'base alpha\n')
        self.assertEqual(stream['write_paths'], ['src/alpha'])

    def test_streams_reader_lists_the_mission_in_plan_order(self):
        self.open('alpha')
        self.open('beta', ('src/beta',))
        rows = streams(self.store, mission_id=MISSION)
        self.assertEqual([row['name'] for row in rows], ['alpha', 'beta'])
        self.assertEqual([row['write_paths'] for row in rows], [['src/alpha'], ['src/beta']])


class LeaseTests(Base):
    def test_a_lease_is_the_only_way_to_write(self):
        stream = self.open()
        with self.assertRaises(PolicyError):
            assert_writable(self.store, 'lse_missing', ['src/alpha'], now=1000.0)
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)
        allowed = assert_writable(self.store, lease['lease_id'], ['src/alpha'], now=1000.0)
        self.assertEqual(allowed['stream_id'], stream['stream_id'])
        with self.assertRaises(PolicyError):
            assert_writable(self.store, lease['lease_id'], ['src/beta'], now=1000.0)
        with self.assertRaises(PolicyError):
            assert_writable(self.store, lease['lease_id'], ['src/alpha/../beta'], now=1000.0)

    def test_unknown_stream_cannot_lease(self):
        with self.assertRaises(PolicyError):
            acquire_lease(self.store, stream_id='str_missing', owner='w', now=1000.0)

    def test_one_live_lease_per_stream(self):
        stream = self.open()
        acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)
        with self.assertRaises(PolicyError):
            acquire_lease(self.store, stream_id=stream['stream_id'], owner='w2', now=1001.0)

    def test_an_overlapping_lease_is_refused(self):
        alpha = self.open('alpha', ('src/alpha',))
        beta = self.open('beta', ('src/alpha/nested',))
        acquire_lease(self.store, stream_id=alpha['stream_id'], owner='w1', now=1000.0)
        with self.assertRaises(PolicyError):
            acquire_lease(self.store, stream_id=beta['stream_id'], owner='w2', now=1001.0)

    def test_heartbeat_extends_the_lease(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', ttl=10,
                              now=1000.0)
        self.assertEqual(lease['expires'], 1010.0)
        heartbeat(self.store, lease['lease_id'], now=1005.0, ttl=10)
        assert_writable(self.store, lease['lease_id'], ['src/alpha'], now=1014.0)
        with self.assertRaises(PolicyError):
            assert_writable(self.store, lease['lease_id'], ['src/alpha'], now=1016.0)

    def test_reclaim_retires_stale_leases_without_a_heartbeat(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', ttl=10,
                              now=1000.0)
        self.assertEqual(reclaim_stale_leases(self.store, now=1011.0), [lease['lease_id']])
        self.assertEqual(leases(self.store, state='EXPIRED')[0]['lease_id'], lease['lease_id'])
        again = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w2', now=1012.0)
        self.assertEqual(again['state'], 'ACTIVE')

    def test_a_retired_lease_can_never_be_revived(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)
        release_lease(self.store, lease['lease_id'], now=1001.0)
        with self.assertRaises(PolicyError):
            heartbeat(self.store, lease['lease_id'], now=1002.0)
        with self.assertRaises(PolicyError):
            assert_writable(self.store, lease['lease_id'], ['src/alpha'], now=1002.0)

    def test_a_revocation_records_its_reason(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)
        release_lease(self.store, lease['lease_id'], state='REVOKED', note='aborted', now=1001.0)
        row = leases(self.store, stream_id=stream['stream_id'])[0]
        self.assertEqual(row['state'], 'REVOKED')
        self.assertEqual(row['note'], 'aborted')


class RunTests(Base):
    def test_run_stream_requires_a_live_lease(self):
        stream = self.open()
        with self.assertRaises(PolicyError):
            run_stream(self.store, stream['stream_id'], self.worker(),
                       lease_id='lse_missing', paths=['src/alpha'])
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)
        release_lease(self.store, lease['lease_id'], now=1001.0)
        with self.assertRaises(PolicyError):
            run_stream(self.store, stream['stream_id'], self.worker(),
                       lease_id=lease['lease_id'], paths=['src/alpha'])

    def test_run_stream_refuses_paths_outside_the_lease(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)
        with self.assertRaises(PolicyError):
            run_stream(self.store, stream['stream_id'], self.worker(),
                       lease_id=lease['lease_id'], paths=['src/beta'], now=1000.0)

    def test_run_stream_refuses_a_foreign_lease(self):
        alpha = self.open('alpha', ('src/alpha',))
        beta = self.open('beta', ('src/beta',))
        lease = acquire_lease(self.store, stream_id=alpha['stream_id'], owner='w1', now=1000.0)
        with self.assertRaises(PolicyError):
            run_stream(self.store, beta['stream_id'], self.worker(),
                       lease_id=lease['lease_id'], paths=['src/beta'], now=1000.0)

    def test_run_stream_runs_the_worker_inside_the_stream(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)
        ran = run_stream(self.store, stream['stream_id'], self.worker('done\n'),
                         lease_id=lease['lease_id'], paths=['src/alpha'], now=1001.0)
        self.assertEqual(ran['result']['wrote'], 'src/alpha/work.txt')
        self.assertEqual((Path(stream['workspace']) / 'src' / 'alpha' / 'work.txt').read_text(),
                         'done\n')
        self.assertEqual([row['state'] for row in streams(self.store, mission_id=MISSION)],
                         ['RUN'])

    def test_a_stream_closes_once(self):
        stream = self.open()
        close_stream(self.store, stream['stream_id'], now=1000.0)
        with self.assertRaises(PolicyError):
            close_stream(self.store, stream['stream_id'], now=1001.0)


class AnnounceTests(Base):
    def _finished(self, name, paths, now=1000.0):
        stream = self.open(name, paths)
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner=name, now=now)
        run_stream(self.store, stream['stream_id'], self.worker(), lease_id=lease['lease_id'],
                   paths=list(paths), now=now)
        close_stream(self.store, stream['stream_id'], now=now)
        return stream, lease

    def test_only_a_finished_stream_announces(self):
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w', now=1000.0)
        with self.assertRaises(PolicyError):
            announce(self.store, stream_id=stream['stream_id'], lease_id=lease['lease_id'],
                     summary='too early', write_paths=['src/alpha'], now=1001.0)

    def test_the_chain_is_ordered_and_linked(self):
        alpha, lease_a = self._finished('alpha', ('src/alpha',))
        first = announce(self.store, stream_id=alpha['stream_id'], lease_id=lease_a['lease_id'],
                         summary='alpha done', write_paths=['src/alpha'], now=1002.0)
        self.assertEqual(first['seq'], 1)
        self.assertIsNone(first['previous'])
        self.assertTrue(first['digest'].startswith('sha256:'))
        beta, lease_b = self._finished('beta', ('src/beta',), now=1010.0)
        second = announce(self.store, stream_id=beta['stream_id'], lease_id=lease_b['lease_id'],
                          summary='beta done', write_paths=['src/beta'], now=1012.0)
        self.assertEqual(second['seq'], 2)
        self.assertEqual(second['previous'], first['announce_id'])
        chain = announce_chain(self.store, MISSION)
        self.assertEqual([row['seq'] for row in chain['announces']], [1, 2])
        self.assertTrue(chain['chain_ok'])
        self.assertEqual(chain['streams_announced'], 2)

    def test_an_announce_needs_a_live_lease_for_its_paths(self):
        alpha, lease_a = self._finished('alpha', ('src/alpha',))
        with self.assertRaises(PolicyError):
            announce(self.store, stream_id=alpha['stream_id'], lease_id=lease_a['lease_id'],
                     summary='wrong paths', write_paths=['src/beta'], now=1002.0)

    def test_synthesis_merges_the_chain(self):
        alpha, lease_a = self._finished('alpha', ('src/alpha',))
        announce(self.store, stream_id=alpha['stream_id'], lease_id=lease_a['lease_id'],
                 summary='alpha done', write_paths=['src/alpha'], now=1002.0)
        report = synthesize(self.store, MISSION)
        self.assertEqual(report['paths'], ['src/alpha'])
        self.assertEqual(report['announced'], 1)
        self.assertIn('alpha done', report['narrative'])
        self.assertTrue(report['merged_digest'].startswith('sha256:'))


class IntegrationTests(Base):
    def _stream(self, name, paths, shared=None, now=1000.0):
        stream = self.open(name, paths)
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner=name, now=now)

        def worker(inner, allowed, info):
            write(Path(inner['workspace']) / (allowed[0] + '/work.txt'), name + '\n')
            if shared:
                write(Path(inner['workspace']) / shared, 'shared\n')
            return {'wrote': allowed[0]}

        run_stream(self.store, stream['stream_id'], worker, lease_id=lease['lease_id'],
                   paths=list(paths), now=now)
        close_stream(self.store, stream['stream_id'], now=now)
        announce(self.store, stream_id=stream['stream_id'], lease_id=lease['lease_id'],
                 summary='%s done' % name, write_paths=list(paths), now=now + 1)
        release_lease(self.store, lease['lease_id'], now=now + 1)
        return stream

    def test_disjoint_streams_integrate_cleanly(self):
        self._stream('alpha', ('src/alpha',))
        self._stream('beta', ('src/beta',), now=1010.0)
        metrics = conflict_metrics(self.store, MISSION)
        self.assertEqual(metrics['conflict_count'], 0)
        self.assertEqual(metrics['conflict_rate'], 0.0)
        self.assertEqual(metrics['actual_overlaps'], [])
        result = integrate(self.store, MISSION, integrator=None,
                           target_root=self.root / 'integration')
        self.assertTrue(result['integration_ok'])
        self.assertEqual(result['conflicts'], [])
        self.assertEqual(result['integrated'], 2)
        self.assertTrue((self.root / 'integration' / 'src' / 'alpha' / 'work.txt').is_file())
        self.assertTrue((self.root / 'integration' / 'src' / 'beta' / 'work.txt').is_file())

    def test_a_stream_writing_outside_its_paths_is_a_real_conflict(self):
        self._stream('alpha', ('src/alpha',), shared='src/shared.txt')
        self._stream('beta', ('src/beta',), shared='src/shared.txt', now=1010.0)
        metrics = conflict_metrics(self.store, MISSION)
        self.assertEqual(metrics['conflict_count'], 1)
        self.assertEqual(metrics['actual_overlaps'][0]['paths'], ['src/shared.txt'])
        self.assertGreater(metrics['conflict_rate'], 0.0)
        result = integrate(self.store, MISSION, integrator=None,
                           target_root=self.root / 'conflict-integration')
        self.assertFalse(result['integration_ok'])
        self.assertTrue(result['conflicts'])

    def test_integration_needs_streams(self):
        with self.assertRaises(PolicyError):
            integrate(self.store, MISSION, integrator=None, target_root=self.root / 'empty')


class ParallelTests(Base):
    def _workers(self, shared=None):
        def make(name):
            def worker(stream, allowed, lease):
                write(Path(stream['workspace']) / (allowed[0] + '/work.txt'), name + '\n')
                if shared:
                    write(Path(stream['workspace']) / shared, 'shared\n')
                return {'wrote': allowed[0]}
            return worker
        return {'alpha': make('alpha'), 'beta': make('beta')}

    def _run(self, tier='D3', workers=None):
        return run_parallel(self.store, mission_id=MISSION, decomposition=decomposition(),
                            workers=workers or self._workers(), source_root=str(self.source),
                            task_id=TASK, streams_root=self.root / 'streams', tier=tier,
                            now=1000.0)

    def test_parallel_streams_need_a_d3_or_d4_decision(self):
        with self.assertRaises(PolicyError):
            self._run(tier='D2')

    def test_run_parallel_end_to_end(self):
        result = self._run()
        self.assertEqual(len(result['streams']), 2)
        self.assertEqual(result['synthesis']['announced'], 2)
        self.assertTrue(result['synthesis']['chain_ok'])
        self.assertTrue(result['integration']['integration_ok'])
        self.assertEqual(result['conflict_metrics']['conflict_count'], 0)
        self.assertEqual([row['state'] for row in streams(self.store, mission_id=MISSION)],
                         ['DONE', 'DONE'])
        self.assertEqual(sorted(row['state'] for row in leases(self.store, mission_id=MISSION)),
                         ['RELEASED', 'RELEASED'])

    def test_every_planned_stream_needs_a_worker(self):
        workers = self._workers()
        del workers['beta']
        with self.assertRaises(PolicyError):
            self._run(workers=workers)
        extra = self._workers()
        extra['gamma'] = extra['alpha']
        with self.assertRaises(PolicyError):
            self._run(workers=extra)

    def test_a_failing_worker_abandons_its_stream_and_revokes_the_lease(self):
        workers = self._workers()

        def boom(stream, allowed, lease):
            raise PolicyError('worker exploded')

        workers['beta'] = boom
        with self.assertRaises(PolicyError):
            self._run(workers=workers)
        states = {row['name']: row['state'] for row in streams(self.store, mission_id=MISSION)}
        self.assertEqual(states, {'alpha': 'DONE', 'beta': 'ABANDONED'})
        self.assertEqual(sorted(row['state'] for row in leases(self.store, mission_id=MISSION)),
                         ['RELEASED', 'REVOKED'])


class PilotClass3Tests(Base):
    def test_class3_pilot_meets_its_gates(self):
        # doc 13 class 3 readiness: the D3 parallel mission runs end to end and its integration
        # check catches the seeded seam that the single agent walks past.
        from kel.evaluation import run_pilot
        report = run_pilot(classes=('3',), workdir=self.root / 'pilot', now=1000.0)
        self.assertTrue(report['gates_ok'])
        per_class = report['per_class']['3']
        self.assertEqual(per_class['escaped_A'], 1)
        self.assertEqual(per_class['escaped_C'], 0)
        self.assertTrue(per_class['escaped_below_A'])
        self.assertTrue(per_class['interruptions_ok'])
        config_c = next(run for run in report['runs'] if run['config'] == 'C')
        self.assertGreaterEqual(config_c['result']['conflicts'], 1)
        self.assertFalse(config_c['result']['integration_ok'])
        self.assertEqual(config_c['result']['streams'], 2)


class Reaudit20Tests(Base):
    """Audit 20 findings (F20-1 … F20-10) — regressions for the 5.5 follow-up patch."""

    def _done_stream(self, name, paths, now=1000.0):
        stream = self.open(name, paths)
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner=name, now=now)

        def worker(inner, allowed, info):
            write(Path(inner['workspace']) / (allowed[0] + '/work.txt'), name + '\n')
            return {'wrote': allowed[0]}

        run_stream(self.store, stream['stream_id'], worker, lease_id=lease['lease_id'],
                   paths=list(paths), now=now)
        close_stream(self.store, stream['stream_id'], now=now)
        announce(self.store, stream_id=stream['stream_id'], lease_id=lease['lease_id'],
                 summary='%s done' % name, write_paths=list(paths), now=now + 1)
        release_lease(self.store, lease['lease_id'], now=now + 1)
        return stream

    def test_a_stream_cannot_announce_what_it_did_not_change(self):
        # F20-2: the announce attests the stream's real output, not its intention.
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w', now=1000.0)
        close_stream(self.store, stream['stream_id'], now=1001.0)
        with self.assertRaises(PolicyError):
            announce(self.store, stream_id=stream['stream_id'], lease_id=lease['lease_id'],
                     summary='nothing done', write_paths=['src/alpha'], now=1002.0)

    def test_the_digest_attests_the_change_set_not_the_summary(self):
        stream = self._done_stream('alpha', ('src/alpha',))
        chain = announce_chain(self.store, MISSION)
        old_scheme = 'sha256:' + digest('%s|%s' % (stream['stream_id'], 'alpha done'))
        self.assertNotEqual(chain['announces'][0]['digest'], old_scheme)

    def test_a_lone_out_of_bounds_write_is_reported(self):
        # F20-3: detection must not need a second stream to collide with.
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w1', now=1000.0)

        def stray(inner, allowed, info):
            write(Path(inner['workspace']) / 'elsewhere' / 'stray.txt', 'stray\n')
            return {'wrote': 'elsewhere/stray.txt'}

        run_stream(self.store, stream['stream_id'], stray, lease_id=lease['lease_id'],
                   paths=['src/alpha'], now=1000.0)
        close_stream(self.store, stream['stream_id'], now=1001.0)
        metrics = conflict_metrics(self.store, MISSION)
        self.assertEqual(metrics['undeclared_writes'][stream['stream_id']],
                         ['elsewhere/stray.txt'])
        self.assertEqual(metrics['undeclared_count'], 1)

    def test_case_differing_paths_are_not_disjoint(self):
        # F20-4: `Src/alpha` and `src/alpha` are one directory on a case-insensitive host.
        body = decomposition()
        body['streams'][1]['write_paths'] = ['Src/alpha']
        with self.assertRaises(PolicyError):
            plan_streams(body)
        alpha = self.open('alpha', ('src/alpha',))
        beta = self.open('beta', ('Src/alpha',))
        acquire_lease(self.store, stream_id=alpha['stream_id'], owner='w1', now=1000.0)
        with self.assertRaises(PolicyError):
            acquire_lease(self.store, stream_id=beta['stream_id'], owner='w2', now=1001.0)

    def test_a_lapsed_lease_cannot_be_revived_or_overlapped_live(self):
        # F20-5: two unexpired overlapping leases must be unreachable.
        alpha = self.open('alpha', ('src/alpha',))
        beta = self.open('beta', ('src/alpha/nested',))
        first = acquire_lease(self.store, stream_id=alpha['stream_id'], owner='w1', ttl=10,
                              now=1000.0)
        with self.assertRaises(PolicyError):
            heartbeat(self.store, first['lease_id'], now=1011.0)
        second = acquire_lease(self.store, stream_id=beta['stream_id'], owner='w2', ttl=10,
                               now=1011.0)
        self.assertEqual(second['state'], 'ACTIVE')
        self.assertEqual(leases(self.store, stream_id=alpha['stream_id'])[0]['state'], 'EXPIRED')
        with self.assertRaises(PolicyError):
            assert_writable(self.store, first['lease_id'], ['src/alpha'], now=1011.0)
        assert_writable(self.store, second['lease_id'], ['src/alpha/nested'], now=1011.0)

    def test_the_integrator_hook_is_used_and_a_refusal_is_a_conflict(self):
        # F20-1: the documented merge hook must be called, and a falsy return is a conflict.
        self._done_stream('alpha', ('src/alpha',))
        calls = []
        accepted = integrate(self.store, MISSION,
                             integrator=lambda item: calls.append(item) or True,
                             target_root=self.root / 'hook-ok')
        self.assertEqual(len(calls), 1)
        self.assertIn('patch', calls[0])
        self.assertTrue(accepted['integration_ok'])
        refused = integrate(self.store, MISSION, integrator=lambda item: False,
                            target_root=self.root / 'hook-refused')
        self.assertFalse(refused['integration_ok'])
        self.assertTrue(refused['conflicts'])

    def test_integration_with_no_finished_stream_is_refused(self):
        # F20-7: PolicyError, never IndexError.
        self.open()
        with self.assertRaises(PolicyError):
            integrate(self.store, MISSION, integrator=None, target_root=self.root / 'none-done')

    def test_extra_path_forms_are_refused_or_normalised(self):
        # F20-10: the forms the record claims are refused, and duplicate separators normalise.
        for bad in ('~/x', 'C:/x', 'C:\\x', '\\\\server\\share'):
            body = decomposition()
            body['streams'][0]['write_paths'] = [bad]
            with self.assertRaises(PolicyError):
                plan_streams(body)
        duplicate = decomposition()
        duplicate['streams'][1]['write_paths'] = ['src//alpha']
        with self.assertRaises(PolicyError):
            plan_streams(duplicate)  # normalises to the same path as stream one

    def test_a_refused_stream_with_no_worker_leaves_nothing_live(self):
        # F20-9: a non-PolicyError worker failure must still abandon and revoke.
        workers = {'alpha': lambda stream, allowed, lease: (_ for _ in ()).throw(
            RuntimeError('worker crashed')), 'beta': lambda stream, allowed, lease: {}}
        with self.assertRaises(RuntimeError):
            run_parallel(self.store, mission_id=MISSION, decomposition=decomposition(),
                         workers=workers, source_root=str(self.source), task_id=TASK,
                         streams_root=self.root / 'streams', tier='D3', now=1000.0)
        states = {row['name']: row['state'] for row in streams(self.store, mission_id=MISSION)}
        self.assertEqual(states['alpha'], 'ABANDONED')
        self.assertEqual(sorted(row['state'] for row in leases(self.store, mission_id=MISSION)),
                         ['REVOKED'])


class Reaudit21Tests(Base):
    """Audit 21 (N21-1..N21-5) — the cleanup-masking and digest-override regressions."""

    def test_announce_failure_keeps_the_causal_error_and_revokes_the_lease(self):
        # N21-1/N21-3: a worker that changes nothing under its declared paths makes announce
        # refuse *after* the stream reached DONE. Cleanup must not mask that error with an invalid
        # DONE -> ABANDONED transition, and must not leave a live lease behind.
        workers = {'alpha': lambda stream, allowed, lease: {'wrote': 'nothing'},
                   'beta': lambda stream, allowed, lease: {'wrote': 'nothing'}}
        with self.assertRaises(PolicyError) as caught:
            run_parallel(self.store, mission_id=MISSION, decomposition=decomposition(),
                         workers=workers, source_root=str(self.source), task_id=TASK,
                         streams_root=self.root / 'streams', tier='D3', now=1000.0)
        self.assertIn('did not change', str(caught.exception))
        self.assertNotIn('closed twice', str(caught.exception))
        self.assertEqual(leases(self.store, mission_id=MISSION, state='ACTIVE'), [])
        states = {row['name']: row['state'] for row in streams(self.store, mission_id=MISSION)}
        self.assertEqual(states, {'alpha': 'DONE'})

    def test_the_announce_digest_has_no_caller_override(self):
        # N21-2: the digest attests the staged change set; no parameter can replace it.
        stream = self.open()
        lease = acquire_lease(self.store, stream_id=stream['stream_id'], owner='w', now=1000.0)
        run_stream(self.store, stream['stream_id'], self.worker(), lease_id=lease['lease_id'],
                   paths=['src/alpha'], now=1000.5)
        close_stream(self.store, stream['stream_id'], now=1001.0)
        with self.assertRaises(TypeError):
            announce(self.store, stream_id=stream['stream_id'], lease_id=lease['lease_id'],
                     summary='done', write_paths=['src/alpha'], digest_value='sha256:forged',
                     now=1002.0)
        row = announce(self.store, stream_id=stream['stream_id'], lease_id=lease['lease_id'],
                       summary='done', write_paths=['src/alpha'], now=1003.0)
        old_scheme = 'sha256:' + digest('%s|%s' % (stream['stream_id'], 'done'))
        self.assertNotEqual(row['digest'], old_scheme)


if __name__ == '__main__':
    unittest.main()
