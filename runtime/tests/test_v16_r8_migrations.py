"""Round 2.5 R8.A — migration assertions.

Every module owns a numbered marker in `schema_migrations`; the set must be unique, idempotent and
reach the intended maximum on a fresh database while preserving an existing one. The inventory and
the R8.B/R8.C package work are recorded in
`docs/v1.6/pre-audit/increments/R8-PACKAGE-ASSERTIONS.md`.
"""
import importlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kel.core import Store  # noqa: E402

MODULES = ('memory', 'projectmap', 'continuation', 'recipes', 'solution', 'team', 'providers',
           'autonomy', 'diagnostics', 'authorize', 'vetting', 'transcription', 'model_prefs',
           'capabilities', 'workforce', 'delegation', 'parallel', 'chat_approvals', 'assignment',
           'dogfood', 'connections')
EXPECTED_MAX = 27


def run_all(store):
    for name in MODULES:
        module = importlib.import_module('kel.' + name)
        module.ensure_schema(store)


def markers(store):
    with store.connect() as db:
        return [dict(row) for row in
                db.execute('SELECT version, name FROM schema_migrations ORDER BY version').fetchall()]


class MigrationSetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup_tmp)
        self.path = Path(self.tmp.name) / 'kel.sqlite3'

    def _cleanup_tmp(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def test_a_fresh_database_reaches_the_intended_maximum_exactly_once(self):
        store = Store(self.path)
        run_all(store)
        rows = markers(store)
        versions = [row['version'] for row in rows]
        self.assertEqual(len(versions), len(set(versions)), 'duplicate migration markers: %r' % versions)
        self.assertEqual(max(versions), EXPECTED_MAX)
        names = {row['version']: row['name'] for row in rows}
        self.assertEqual(names[EXPECTED_MAX], 'v20-connection-sources')
        self.assertEqual(names[25], 'v20-connection-prefix')
        self.assertEqual(names[24], 'v20-connection-tests')
        self.assertEqual(names[23], 'v20-connections')
        self.assertEqual(names[22], 'v20-fix-capture')
        self.assertEqual(names[20], 'chat_approval_announcements')
        for required in (1, 14, 17, 18, 19, 21):
            self.assertIn(required, versions)

    def test_the_migration_set_is_idempotent(self):
        store = Store(self.path)
        run_all(store)
        first = markers(store)
        run_all(store)
        self.assertEqual(markers(store), first)

    def test_an_existing_database_keeps_its_state_and_is_stamped(self):
        store = Store(self.path)
        run_all(store)
        store.add_message('hello migration', 'user', conversation='main')
        with store.transaction() as db:
            db.execute('DELETE FROM schema_migrations WHERE version=?', (EXPECTED_MAX,))
        store2 = Store(self.path)
        run_all(store2)
        self.assertEqual(markers(store2)[-1]['version'], EXPECTED_MAX)
        with store2.connect() as db:
            kept = db.execute("SELECT text FROM messages WHERE text='hello migration'").fetchone()
        self.assertIsNotNone(kept, 'existing state was lost by the migration set')

    def test_module_migration_constants_are_unique(self):
        # The direct guard for the R8.A finding: two modules once claimed version 17, so the
        # schema_migrations row could not say which migration was applied.
        claimed = {}
        for name in MODULES:
            module = importlib.import_module('kel.' + name)
            version = getattr(module, 'MIGRATION_VERSION', None)
            if version is None:
                continue
            self.assertNotIn(version, claimed,
                             '%s and %s both claim migration %s' % (name, claimed.get(version), version))
            claimed[version] = name
        self.assertEqual(max(claimed), EXPECTED_MAX)
        self.assertEqual(claimed[EXPECTED_MAX], 'connections')
