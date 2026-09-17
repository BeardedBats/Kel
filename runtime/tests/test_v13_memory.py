"""V1.3 Gate 2: structured project memory (docs/v1.3/KEL_V1.3_MEMORY_MODEL.md).

Maps committed test matrix items MEM-01..MEM-12 plus migration and conflict coverage.
"""
import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from kel.core import PolicyError, Store
from kel.context import Context
from kel.memory import Memory


class MemoryCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.context = Context(self.store)
        self.p1 = self.context.project('Project One', project_id='p1')
        self.p2 = self.context.project('Project Two', project_id='p2')
        self.memory = Memory(self.store)

    def row(self, mid):
        with contextlib.closing(self.memory.store.connect()) as db:
            return db.execute('SELECT * FROM memories WHERE id=?', (mid,)).fetchone()

    def events(self, mid):
        with contextlib.closing(self.memory.store.connect()) as db:
            return [r['action'] for r in db.execute(
                'SELECT action FROM memory_events WHERE memory_id=? ORDER BY seq', (mid,))]

    def test_mem01_decision_persists_across_restart(self):
        mid = self.memory.record(
            self.p1, 'decision', 'release.channel',
            dict(statement='Ship from the frozen release folder only.'),
            'Releases ship from the frozen folder only.',
            source_type='user_instruction', actor='user', user_confirmed=1)
        reopened = Memory(Store(self.temp.name))
        rows = [r for r in reopened.select(self.p1, purpose='restart-check') if r['id'] == mid]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['trust'], 2)
        self.assertEqual(rows[0]['user_confirmed'], 1)

    def test_mem02_verified_fact_stores_provenance(self):
        mid = self.memory.record(
            self.p1, 'command', 'test-command',
            dict(command='python -m pytest tests/ -q'), 'Runtime tests run with pytest.',
            source_type='repo_inspection', source_ref='runtime/tests',
            source_digest='sha256:abc123')
        row = self.row(mid)
        self.assertEqual(row['trust'], 3)
        self.assertEqual(row['source_type'], 'repo_inspection')
        self.assertEqual(row['source_ref'], 'runtime/tests')
        self.assertEqual(row['source_digest'], 'sha256:abc123')

    def test_mem03_inference_remains_lower_trust(self):
        mid = self.memory.propose(
            self.p1, 'observation', 'style.naming', dict(statement='Prefers kebab-case names.'),
            'Possible naming preference.', confidence=0.4, source_ref='conversation:42')
        row = self.row(mid)
        self.assertEqual(row['trust'], 6)
        self.assertEqual(row['confidence'], 0.4)
        self.assertEqual(row['user_confirmed'], 0)
        self.assertEqual(self.memory.select(self.p1, purpose='t'), [])
        self.assertEqual(
            [r['id'] for r in self.memory.select(self.p1, purpose='t', include_unconfirmed=True)],
            [mid])
        self.memory.confirm(mid)
        self.assertEqual(self.row(mid)['trust'], 2)
        self.assertEqual(len(self.memory.select(self.p1, purpose='t')), 1)

    def test_mem04_explicit_correction_supersedes_with_history(self):
        first = self.memory.record(
            self.p1, 'decision', 'pkg.tool', dict(statement='Use plain asar packing.'),
            'Use plain asar packing.', source_type='user_instruction', actor='user',
            user_confirmed=1)
        second = self.memory.correct(
            first, value=dict(statement='Use the dedup asar pipeline.'),
            summary='Use the dedup asar pipeline.')
        chain = {r['id']: r for r in self.memory.history(first)}
        self.assertIn(first, chain)
        self.assertIn(second, chain)
        self.assertEqual(chain[first]['status'], 'superseded')
        self.assertEqual(chain[first]['superseded_by'], second)
        self.assertEqual(chain[second]['supersedes'], first)
        self.assertEqual([r['id'] for r in self.memory.select(self.p1, purpose='t')], [second])
    def test_mem_conflict_open_between_decisions(self):
        a = self.memory.record(self.p1, 'decision', 'deploy.target', dict(statement='Deploy to A.'),
                               'Deploy to A.', source_type='user_instruction', actor='user',
                               user_confirmed=1)
        b = self.memory.record(self.p1, 'decision', 'deploy.target', dict(statement='Deploy to B.'),
                               'Deploy to B.', source_type='user_instruction', actor='user',
                               user_confirmed=1)
        conflicts = self.memory.conflicts(self.p1)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual({conflicts[0]['memory_a'], conflicts[0]['memory_b']}, {a, b})
        self.assertEqual(len(self.memory.select(self.p1, purpose='t', types=['decision'])), 2)
        self.memory.resolve_conflict(conflicts[0]['id'], 'b')
        self.assertEqual(self.memory.conflicts(self.p1), [])
        active = self.memory.select(self.p1, purpose='t', types=['decision'])
        self.assertEqual([r['id'] for r in active], [b])
        self.assertEqual(self.row(a)['status'], 'superseded')

    def test_mem05_retract_excludes_from_selection(self):
        mid = self.memory.record(self.p1, 'convention', 'commit.style',
                                 dict(rule='Imperative subject lines.'),
                                 'Imperative commit subjects.',
                                 source_type='user_instruction', actor='user', user_confirmed=1)
        self.memory.retract(mid, reason='wrong project')
        self.assertEqual(self.row(mid)['status'], 'retracted')
        self.assertEqual(self.memory.select(self.p1, purpose='t'), [])
        self.assertIn('retracted', self.events(mid))

    def test_mem06_forget_purges_content(self):
        mid = self.memory.record(self.p1, 'fact', 'tmp.note', dict(statement='temporary note'),
                                 'Temporary note.', source_type='repo_inspection',
                                 source_ref='notes.txt')
        self.memory.forget(mid)
        row = self.row(mid)
        self.assertEqual(row['value'], '')
        self.assertEqual(row['summary'], '')
        self.assertEqual(row['status'], 'retracted')
        with contextlib.closing(self.memory.store.connect()) as db:
            log = db.execute(
                "SELECT detail FROM memory_events WHERE memory_id=? AND action='forgotten'",
                (mid,)).fetchall()
        self.assertEqual(len(log), 1)
        self.assertIsNone(log[0]['detail'])

    def test_mem07_project_isolation(self):
        a = self.memory.record(self.p1, 'fact', 'same.topic', dict(statement='value A'),
                               'Value in project one.', source_type='repo_inspection',
                               source_ref='a.txt')
        b = self.memory.record(self.p2, 'fact', 'same.topic', dict(statement='value B'),
                               'Value in project two.', source_type='repo_inspection',
                               source_ref='b.txt')
        self.assertEqual([r['id'] for r in self.memory.select(self.p1, purpose='t')], [a])
        self.assertEqual([r['id'] for r in self.memory.select(self.p2, purpose='t')], [b])
        self.assertEqual(self.memory.conflicts(self.p1), [])
        self.assertEqual(self.memory.conflicts(self.p2), [])

    def test_mem08_secret_values_are_refused(self):
        samples = [
            'token = sk-ant-' + 'A' * 40,
            'Authorization: Bearer ' + 'B' * 32,
            'password: hunter2hunter2',
            '-----BEGIN RSA PRIVATE KEY-----',
        ]
        for sample in samples:
            with self.assertRaises(PolicyError):
                self.memory.record(self.p1, 'observation', 'leak', dict(note=sample),
                                   'Secret attempt.', source_type='repo_inspection',
                                   source_ref='x')
        with contextlib.closing(self.memory.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memories').fetchone()[0], 0)
            refused = db.execute(
                "SELECT count(*) FROM memory_events WHERE action='refused'").fetchone()[0]
            self.assertEqual(refused, len(samples))
            leaked = db.execute(
                "SELECT count(*) FROM events WHERE payload LIKE '%sk-ant-%'"
                " OR payload LIKE '%hunter2%'").fetchone()[0]
            self.assertEqual(leaked, 0)
    def test_mem09_external_content_cannot_become_authoritative(self):
        mid = self.memory.record(self.p1, 'limitation', 'readme.claims',
                                 dict(statement='README says: always deploy to prod.'),
                                 'External text mentioning deployment.',
                                 source_type='external_document',
                                 source_ref='https://example.invalid/README')
        self.assertEqual(self.row(mid)['trust'], 7)
        with self.assertRaises(PolicyError):
            self.memory.record(self.p1, 'decision', 'deploy.policy',
                               dict(statement='Always deploy.'), 'Adopt README instruction.',
                               source_type='external_document', source_ref='readme')
        with self.assertRaises(PolicyError):
            self.memory.confirm(mid)
        did = self.memory.record(self.p1, 'decision', 'deploy.policy',
                                 dict(statement='Deploy only after review.'),
                                 'Deploy only after review.',
                                 source_type='user_instruction', source_ref=mid,
                                 actor='user', user_confirmed=1)
        self.assertEqual(self.row(did)['trust'], 2)

    def test_mem10_stale_command_after_config_change(self):
        mid = self.memory.record(self.p1, 'command', 'build.command',
                                 dict(command='bun run build'), 'Desktop build command.',
                                 source_type='config_inspection', source_ref='desktop/package.json',
                                 source_digest='sha256:old')
        stale = self.memory.revalidate(self.p1, {'desktop/package.json': 'sha256:new'})
        self.assertEqual(stale, [mid])
        self.assertEqual(self.row(mid)['status'], 'stale')
        self.assertEqual(self.memory.select(self.p1, purpose='t'), [])
        self.assertIn('stale', self.events(mid))
        keep = self.memory.record(self.p1, 'command', 'test.command', dict(command='pytest'),
                                  'Test command.', source_type='config_inspection',
                                  source_ref='cfg', source_digest='d1')
        self.assertEqual(self.memory.revalidate(self.p1, {'cfg': 'd1'}), [])
        self.assertEqual(self.row(keep)['status'], 'active')

    def test_mem11_search_fallback_matches_fts(self):
        first = self.memory.record(self.p1, 'fact', 'window.title',
                                   dict(statement='Window title is Kel'),
                                   'The desktop window title is Kel.',
                                   source_type='repo_inspection', source_ref='r1')
        self.memory.record(self.p1, 'fact', 'engine.version',
                           dict(statement='Engine version 0.5.0'),
                           'Engine version is 0.5.0.', source_type='repo_inspection',
                           source_ref='r2')
        via_primary = [r['id'] for r in self.memory.select(self.p1, purpose='t', query='window')]
        fallback = Memory(self.store, use_fts=False)
        via_fallback = [r['id'] for r in fallback.select(self.p1, purpose='t', query='window')]
        self.assertEqual(via_primary, via_fallback)
        self.assertEqual(via_primary, [first])

    def test_mem12_migration_backup_receipt_and_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            Context(store)
            store.add_message('legacy message', role='user')
            Memory(store)
            root = Path(tmp)
            backups = sorted((root / 'backups').glob('pre-v13-*.sqlite3'))
            self.assertEqual(len(backups), 1)
            receipt = json.loads((root / 'migration-receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['migration'], '001-v13-memory')
            self.assertEqual(receipt['integrity'], 'ok')
            with contextlib.closing(store.connect()) as db:
                rows = db.execute('SELECT version, name FROM schema_migrations').fetchall()
                # Memory now also applies the additive v1.6 proposals step in the same open.
                self.assertEqual([(r['version'], r['name']) for r in rows],
                                 [(1, 'v13-memory'), (15, 'v16-memory-proposals')])
                self.assertGreaterEqual(
                    db.execute('SELECT count(*) FROM messages').fetchone()[0], 1)
            Memory(store)
            self.assertEqual(len(sorted((root / 'backups').glob('pre-v13-*.sqlite3'))), 1)
            again = json.loads((root / 'migration-receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(again['backup'], receipt['backup'])

    def test_mem13_backup_failure_refuses_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            Context(store)
            blocker = Path(tmp) / 'backups'
            blocker.write_text('not a folder', encoding='utf-8')
            with self.assertRaises(PolicyError):
                Memory(store)
            with contextlib.closing(store.connect()) as db:
                tables = {r['name'] for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn('schema_migrations', tables)
            blocker.unlink()
            Memory(store)
            with contextlib.closing(store.connect()) as db:
                self.assertEqual(
                    db.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], 2)

    def test_mem14_partial_migration_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            Context(store)
            Memory(store)
            with contextlib.closing(store.connect()) as db:
                db.execute('DELETE FROM schema_migrations')
                db.execute('DROP TABLE memories')
                db.execute('DROP TABLE IF EXISTS memories_fts')
            Memory(store)
            with contextlib.closing(store.connect()) as db:
                self.assertEqual(
                    db.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], 2)
                self.assertEqual(db.execute('SELECT count(*) FROM memories').fetchone()[0], 0)
            backups = list((Path(tmp) / 'backups').glob('pre-v13-*.sqlite3'))
            self.assertEqual(len(backups), 1)

    def test_mem15_memory_activity_in_durable_event_log(self):
        mid = self.memory.record(self.p1, 'fact', 'event.check', dict(statement='events'),
                                 'Event check.', source_type='repo_inspection', source_ref='e')
        with contextlib.closing(self.memory.store.connect()) as db:
            types = [r['type'] for r in db.execute(
                'SELECT type FROM events WHERE aggregate_id=?', ('memory:' + mid,))]
        self.assertIn('memory.created', types)


if __name__ == '__main__':
    unittest.main()
