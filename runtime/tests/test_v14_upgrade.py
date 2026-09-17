"""V1.4 Gate 10: the V1.3 -> V1.4 data upgrade path (UPG-*).

A "V1.3 store" is exactly what the V1.3 module set produces: `Store` + `Context` + `Memory` +
`ProjectMap` + `Recipes` + `Continuation`, i.e. schema_migrations 1-4 — plus, since the v1.6 memory
proposal surface shipped inside `Memory`, the additive proposals step (15). None of the V1.4 tables
exist. Opening that store with the V1.4 modules must add tables additively, keep every existing row,
and leave a backup + schema record behind — never rewrite or drop anything.
"""
import contextlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from kel.autonomy import Autonomy
from kel.context import Context
from kel.continuation import Continuation
from kel.core import Store
from kel.diagnostics import Diagnostics
from kel.memory import Memory
from kel.projectmap import ProjectMap
from kel.providers import Providers
from kel.recipes import RecipeLibrary
from kel.solution import SolutionBriefs
from kel.team import Team

V14_TABLES = (
    'solution_briefs', 'solution_options', 'option_comparisons', 'capability_opportunities',
    'solution_reviews', 'role_templates', 'role_versions', 'role_overrides', 'team_assignments',
    'team_events', 'assignment_artifacts', 'provider_credentials', 'provider_usage',
    'capability_leases', 'lease_scope', 'lease_events', 'boundary_expansion_requests',
    'startup_spans', 'performance_measurements', 'health_observations', 'process_observations',
    'retention_settings',
)


def contract():
    return {'request': 'Do the work', 'project_id': 'default',
            'milestones': [{'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md',
                            'depends_on': [], 'checks': [{'kind': 'min_chars', 'value': 4}]}]}


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # --- a V1.3 store: the V1.3 module set only ------------------------------------------------
        self.store = Store(self.root)
        self.context = Context(self.store)
        self.memory = Memory(self.store)
        # The rest of the V1.3 module set, so the fixture really is a V1.3 store (schema_migrations 1-4).
        ProjectMap(self.store)
        Continuation(self.store)
        RecipeLibrary(self.store)
        self.legacy_job = self.store.create(contract(), conversation='main')
        self.memory.record('default', 'observation', 'Drawer density',
                           {'value': 'pre-upgrade'},
                           'Seeded before the V1.4 upgrade.',
                           source_type='repo_inspection', source_ref='README.md')

    def tearDown(self):
        self.tmp.cleanup()

    def tables(self):
        with contextlib.closing(self.store.connect()) as db:
            return {row['name'] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}

    def versions(self):
        with contextlib.closing(self.store.connect()) as db:
            return [row['version'] for row in db.execute(
                'SELECT version FROM schema_migrations ORDER BY version')]

    def test_a_v13_store_has_only_the_v13_schema(self):
        tables = self.tables()
        self.assertNotIn('team_assignments', tables)
        self.assertNotIn('capability_leases', tables)
        self.assertNotIn('health_observations', tables)
        # The v1.6 proposals step rides with the memory module (additive table, own version row).
        self.assertIn('memory_proposals', tables)
        self.assertEqual(self.versions(), [1, 2, 3, 4, 15])

    def test_opening_it_with_v14_modules_upgrades_additively_and_keeps_the_data(self):
        before_job = self.store.get(self.legacy_job)
        before_memories = [record['summary'] for record in
                           self.memory.records('default', limit=20)]

        # First V1.4 open — every new module runs its own additive migration step.
        SolutionBriefs(self.store)
        Team(self.store)
        Providers(self.store)
        Autonomy(self.store)
        Diagnostics(self.store, engine_version='1.4.0-upgrade')

        tables = self.tables()
        missing = [table for table in V14_TABLES if table not in tables]
        self.assertEqual(missing, [])
        self.assertEqual(self.versions(), [1, 2, 3, 4, 5, 6, 7, 8, 9, 15])

        # Nothing pre-existing moved or disappeared.
        self.assertEqual(self.store.get(self.legacy_job)['id'], before_job['id'])
        self.assertEqual(self.store.get(self.legacy_job)['state'], before_job['state'])
        self.assertEqual([record['summary'] for record in
                          self.memory.records('default', limit=20)], before_memories)

    def test_reopening_is_idempotent(self):
        for factory in (lambda: SolutionBriefs(self.store), lambda: Team(self.store),
                        lambda: Providers(self.store), lambda: Autonomy(self.store),
                        lambda: Diagnostics(self.store)):
            factory()
        versions_first = self.versions()
        for factory in (lambda: SolutionBriefs(self.store), lambda: Team(self.store),
                        lambda: Providers(self.store), lambda: Autonomy(self.store),
                        lambda: Diagnostics(self.store)):
            factory()
        self.assertEqual(self.versions(), versions_first)
        self.assertEqual(len(self.versions()), len(set(self.versions())))

    def test_the_upgrade_leaves_a_backup_and_a_record(self):
        SolutionBriefs(self.store)
        Team(self.store)
        Providers(self.store)
        Autonomy(self.store)
        Diagnostics(self.store, engine_version='1.4.0-upgrade')
        backups = list((self.root / 'backups').glob('*')) if (self.root / 'backups').exists() else []
        self.assertTrue(backups, 'the additive upgrade should keep a pre-migration backup')
        with contextlib.closing(self.store.connect()) as db:
            rows = list(db.execute('SELECT version, name FROM schema_migrations ORDER BY version'))
        names = {row['name'] for row in rows if row['version'] >= 5}
        self.assertEqual(names, {'v14-solution', 'v14-team', 'v14-providers', 'v14-autonomy',
                                 'v14-diagnostics', 'v16-memory-proposals'})

    def test_v14_features_work_on_upgraded_data(self):
        team = Team(self.store)
        team.seed_defaults()
        briefs = SolutionBriefs(self.store)
        brief = briefs.open_brief('default', 'Upgraded project work', conversation_id='main')
        self.assertTrue(brief)
        lease = Autonomy(self.store).issue(self.legacy_job, review_ref='brief:' + brief,
                                          roots=[str(self.root)])
        self.assertTrue(lease['lease_id'])
        diagnostics = Diagnostics(self.store, engine_version='1.4.0-upgrade')
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot['database']['integrity'], 'ok')
        self.assertGreaterEqual(snapshot['counts']['jobs'], 1)
        _ = team.roster()
