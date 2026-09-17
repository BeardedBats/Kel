"""Global search tests (docs/basic-ux-sweep/11_SEARCH_AND_DISCOVERABILITY.md)."""
import contextlib
import sys
import tempfile
import unittest
from pathlib import Path

from kel.core import Store
from kel.search import Search


class SearchBase(unittest.TestCase):
    def setUp(self):
        sys.stdout.reconfigure(errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.search = Search(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def _table(self, script):
        # executescript performs an implicit COMMIT: keep it on a plain autocommit connection.
        with contextlib.closing(self.store.connect()) as db:
            db.executescript(script)

    def _seed(self):
        self._table("""
        CREATE TABLE IF NOT EXISTS transcripts(id TEXT PRIMARY KEY, name TEXT, text TEXT,
            duration_ms INTEGER, source_type TEXT, status TEXT, created REAL, updated REAL);
        CREATE TABLE IF NOT EXISTS vetting_sessions(id TEXT PRIMARY KEY, project_id TEXT,
            conversation_id TEXT, template TEXT, topic TEXT, state TEXT, current_batch INTEGER,
            created REAL, updated REAL);
        CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, project_id TEXT, title TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS messages(seq INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT, role TEXT, text TEXT, job_id TEXT, at REAL);
        """)
        with self.store.transaction() as db:
            db.execute("INSERT INTO transcripts VALUES('t1','Morning interview','the dashboard feels cramped on small screens',1200,'recording','complete',1,2)")
            db.execute("INSERT INTO vetting_sessions VALUES('s1','default','main','product-ui','Basketball matchup dashboard','ACTIVE',1,1,2)")
            db.execute("INSERT INTO conversations VALUES('c1','default','Voice note routing',1)")
            db.execute("INSERT INTO messages(conversation_id, role, text, at) VALUES('c1','user','tighten the matchup table spacing',1)")


class SearchTests(SearchBase):
    def test_short_query_returns_nothing(self):
        out = self.search.run('a')
        self.assertEqual(out['transcripts'], [])
        self.assertEqual(out['vetting'], [])

    def test_partial_matches_with_snippets(self):
        self._seed()
        out = self.search.run('cramped')
        self.assertEqual(len(out['transcripts']), 1)
        self.assertIn('cramped', out['transcripts'][0]['snippet'])
        self.assertEqual(out['transcripts'][0]['title'], 'Morning interview')

    def test_vetting_and_chats_are_found(self):
        self._seed()
        out = self.search.run('matchup')
        self.assertTrue(out['vetting'])
        self.assertTrue(out['conversations'])
        chats = self.search.run('routing')
        self.assertTrue(chats['conversations'])

    def test_like_metacharacters_are_escaped(self):
        self._seed()
        out = self.search.run('%_%')
        self.assertEqual(out['transcripts'], [])
        self.assertEqual(out['conversations'], [])


if __name__ == '__main__':
    unittest.main()
