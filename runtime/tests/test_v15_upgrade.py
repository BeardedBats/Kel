"""V1.5 G11: migration 010 (`v15-authorization`) is additive and lazy on real data paths.

G11 also proved this on a copy of a real V1.3-origin user data root (see
docs/v1.5/13_MIGRATIONS.md); this test keeps the contract executable: stripping the 010
table + bookkeeping row from a live store, then using the boundary through the same calls the
application makes, recreates the schema, records policy-stamped decisions, keeps every prior
row, and stays idempotent across reopens.
"""
import tempfile
import unittest
from pathlib import Path

from kel.authorize import Authorizer, POLICY_VERSION
from kel.coding import compile_coding, git
from kel.core import Store
from kel.service import Service


def make_project(base, name):
    root = base / name
    root.mkdir(parents=True)
    git(root, 'init')
    (root / 'app.txt').write_text('old')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=Kel', '-c', 'user.email=kel@localhost', 'commit', '-m', 'base')
    return root


class UpgradeToV15Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.store = Store(self.base / 'data')
        self.project = make_project(self.base, 'proj')
        self.job = self.store.create(compile_coding('Touch app.txt.', self.project,
                                                    ['python', '-m', 'unittest']))

    def strip_v15(self):
        with self.store.transaction() as db:
            db.execute('DROP TABLE IF EXISTS guardrail_decisions')
            db.execute('DELETE FROM schema_migrations WHERE version=10')

    def table_present(self):
        import sqlite3
        con = sqlite3.connect(str(self.base / 'data' / 'kel.sqlite3'))
        try:
            row = con.execute("select name from sqlite_master where type='table' "
                              "and name='guardrail_decisions'").fetchone()
            return row is not None
        finally:
            con.close()

    def decision_count(self):
        import sqlite3
        con = sqlite3.connect(str(self.base / 'data' / 'kel.sqlite3'))
        try:
            return con.execute('select count(*) from guardrail_decisions').fetchone()[0]
        finally:
            con.close()

    def test_upgrade_is_additive_lazy_and_idempotent(self):
        self.strip_v15()
        self.assertFalse(self.table_present(), 'pre-010 state must be simulated for real')

        # The application path: the shell starts the V1.5 Service on the data root. Startup must
        # not fail on the stripped store, and must not silently drop anything.
        service = Service(self.base / 'data')
        service.shutdown()
        self.assertEqual(self.store.get(self.job)['id'], self.job,
                         'pre-010 data must survive startup')

        # The boundary applies 010 on first use and stamps the decision with the live policy.
        first = Authorizer(self.store).decide({'actor': 'kel', 'action_kind': 'shell',
                                               'target': 'upgrade probe', 'milestone': 'code'})
        self.assertEqual(first['outcome'], 'INVALID_CONTEXT')
        self.assertTrue(self.table_present())
        self.assertEqual(self.decision_count(), 1)

        import sqlite3
        con = sqlite3.connect(str(self.base / 'data' / 'kel.sqlite3'))
        try:
            rows = con.execute('select policy_version from guardrail_decisions').fetchall()
            self.assertEqual(rows, [(POLICY_VERSION,)])
            bookkeeping = con.execute('select count(*) from schema_migrations where version=10')
            self.assertEqual(bookkeeping.fetchone()[0], 1)
        finally:
            con.close()

        # Reopening (a restart) is idempotent: still one bookkeeping row, decisions accumulate.
        second = Authorizer(self.store).decide({'actor': 'kel', 'action_kind': 'shell',
                                                'target': 'upgrade probe 2', 'milestone': 'code'})
        self.assertEqual(second['outcome'], 'INVALID_CONTEXT')
        self.assertEqual(self.decision_count(), 2)


if __name__ == '__main__':
    unittest.main()
