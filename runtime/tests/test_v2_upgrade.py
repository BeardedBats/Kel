"""V2-17 — manual upgrade reliability: the V2 state survives backup, restore and a re-open.

The directive's §22, practically: no updater infrastructure, but a safe manual upgrade, safe
migrations, failure without data loss and a practical developer rollback. The legacy migration and
the backup machinery already exist; these pins prove the NEW V2 state (V2-01…V2-14 tables) survives:

- an inventory that covers every table with counts and the migration ledger (the before/after tool);
- a backup that carries every V2 row and still never travels the credentials file;
- a restore that brings the V2 rows back exactly, leaving nothing from the post-backup mutations;
- a staged restore that touches nothing live until it is applied, and an apply that is a no-op the
  second time;
- a stray live credentials file that survives the restore (merge never deletes) while backups keep
  excluding it;
- a re-open (all V2 modules ensuring their schemas again) that changes no count and no ledger row.
"""
import contextlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from kel import network_policy
from kel.assignment import ensure_schema as ensure_assignment_schema
from kel.backup import Backup, apply_pending_restore, table_inventory
from kel.connections import ensure_schema as ensure_connections_schema
from kel.context import Context
from kel.core import Store
from kel.learning import queue_promotion
from kel.memory import Memory, ensure_proposals
from kel.memory import ensure_schema as ensure_memory_schema
from kel.model_prefs import ModelPrefs
from kel.team import ensure_schema as ensure_team_schema
from kel.workforce import ensure_schema as ensure_workforce_schema

SHADOW_ON = {'workforce.enabled': True, 'workforce.learning.shadow': True}
PROJECT = 'proj-upgrade'
V2_TABLES = ('connections', 'oauth_flows', 'connection_events', 'routing_outcomes',
             'model_prefs', 'network_policy', 'network_events', 'memories', 'memory_proposals',
             'team_events', 'projects', 'conversations', 'schema_migrations')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.data = Path(self.tmp.name) / 'data'
        self.store = Store(self.data)
        ensure_connections_schema(self.store)
        ensure_memory_schema(self.store)
        ensure_proposals(self.store)
        ensure_workforce_schema(self.store)
        ensure_assignment_schema(self.store)
        ensure_team_schema(self.store)
        self.context = Context(self.store)
        self.context.project('Upgrade Project', project_id=PROJECT)
        # A representative spread of V2 state.
        with self.store.transaction() as db:
            db.execute("INSERT INTO connections(id,name,kind,created,updated)"
                       " VALUES('con-1','Probe','api_key',?,?)", (time.time(), time.time()))
            db.execute('INSERT INTO connection_events(at,connection_id,action,domain,status,state,'
                       'attempts,ms) VALUES(?,?,?,?,?,?,?,?)',
                       (time.time(), 'con-1', 'read', 'api.example.com', 200, 'ok', 1, 5))
            db.execute('INSERT INTO routing_outcomes(run_id,provider,verdict,job_kind,at)'
                       ' VALUES(?,?,?,?,?)', ('run-1', 'codex', 'VERIFIED', 'coding', time.time()))
        ModelPrefs(self.store).set_default('codex', 'codex-native')
        network_policy.set_mode(self.store, 'approved', scope='default', domains=['example.com'])
        network_policy.decide(self.store, 'example.com')
        self.memory = Memory(self.store)
        self.memory.record(PROJECT, 'convention', 'style.terse', {'statement': 'Keep it short.'},
                           'Keep it short.', source_type='repo_inspection')
        queue_promotion(self.store, project_id=PROJECT, proposal_kind='learning.promotion',
                        subject='style.terse', requested={'confidence': 8}, flags=SHADOW_ON)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def inventory(self):
        return table_inventory(self.store.db_path)

    def create_backup(self):
        target = Path(self.tmp.name) / 'target'
        target.mkdir()
        return Backup(self.store).create(str(target))['folder']


class InventoryTests(Base):
    def test_the_inventory_covers_the_v2_surfaces(self):
        inventory = self.inventory()
        for table in V2_TABLES:
            self.assertIn(table, inventory['tables'], table)
        self.assertGreaterEqual(inventory['tables']['connections'], 1)
        self.assertEqual(inventory['tables']['connection_events'], 1)
        self.assertEqual(inventory['tables']['routing_outcomes'], 1)
        self.assertEqual(inventory['tables']['network_policy'], 1)
        self.assertGreaterEqual(len(inventory['migrations']), 1, 'the ledger is readable')
        self.assertTrue(all('version' in row for row in inventory['migrations']))

    def test_reopening_the_same_store_twice_changes_no_counts(self):
        before = self.inventory()
        reopened = Store(self.data)
        ensure_connections_schema(reopened)
        ensure_memory_schema(reopened)
        ensure_proposals(reopened)
        ensure_workforce_schema(reopened)
        ensure_assignment_schema(reopened)
        ensure_team_schema(reopened)
        ModelPrefs(reopened)
        network_policy.ensure_schema(reopened)
        after = table_inventory(reopened.db_path)
        self.assertEqual(after, before, 'an additive re-open keeps every row and the ledger')


class BackupSurvivalTests(Base):
    def test_a_backup_carries_every_v2_row_and_never_the_credentials(self):
        credentials = self.data / 'kel-credentials.json'
        credentials.write_text(json.dumps({'OPENAI_API_KEY': 'probe'}), encoding='utf-8')
        folder = Path(self.create_backup())
        self.assertFalse((folder / 'kel-credentials.json').exists(),
                         'credentials never travel in a backup')
        Backup(self.store).inspect(str(folder))  # the description is readable
        with contextlib.closing(__import__('sqlite3').connect(str(folder / 'kel.sqlite3'))) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM connections').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memories').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM network_policy').fetchone()[0], 1)

    def test_a_restore_brings_every_v2_row_back_and_drops_post_backup_mutations(self):
        folder = self.create_backup()
        before = self.inventory()
        with self.store.transaction() as db:
            db.execute("INSERT INTO connections(id,name,kind,created,updated)"
                       " VALUES('con-2','Later','api_key',?,?)", (time.time(), time.time()))
        self.memory.record(PROJECT, 'convention', 'style.later', {'statement': 'Later.'}, 'Later.',
                           source_type='repo_inspection')
        self.assertGreater(self.inventory()['tables']['connections'], before['tables']['connections'])
        Backup(self.store).stage_restore(folder)
        self.assertTrue(apply_pending_restore(Store(self.data)))
        restored = table_inventory(self.store.db_path)
        self.assertEqual(restored, before, 'every table and the ledger come back exactly')
        self.assertEqual(restored['tables']['connections'], 1, 'the later row is gone')

    def test_a_staged_restore_touches_nothing_until_it_is_applied(self):
        folder = self.create_backup()
        Backup(self.store).stage_restore(folder)
        staged = self.inventory()
        with self.store.transaction() as db:
            db.execute("INSERT INTO connections(id,name,kind,created,updated)"
                       " VALUES('con-3','After-stage','api_key',?,?)", (time.time(), time.time()))
        live = self.inventory()
        self.assertEqual(live['tables']['connections'], staged['tables']['connections'] + 1,
                         'the live data kept its rows while the restore is staged')
        self.assertTrue(apply_pending_restore(Store(self.data)))
        self.assertFalse(apply_pending_restore(Store(self.data)), 'the second apply is a no-op')
        self.assertEqual(self.inventory()['tables']['connections'], 1, 'applying replaces with the backup')

    def test_the_live_credentials_file_survives_the_restore(self):
        credentials = self.data / 'kel-credentials.json'
        credentials.write_text(json.dumps({'OPENAI_API_KEY': 'probe'}), encoding='utf-8')
        folder = self.create_backup()
        Backup(self.store).stage_restore(folder)
        apply_pending_restore(Store(self.data))
        self.assertTrue(credentials.exists(),
                        'restoring never deletes the live credentials file (backups exclude it)')


if __name__ == '__main__':
    unittest.main()
