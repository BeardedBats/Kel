"""FN-08: search finds words anywhere in a message, says which chat a vetting hit lives in, and
leaves out messages an edit or a regenerate rewound (D-75.2)."""
import contextlib
import tempfile
import unittest
from pathlib import Path

from kel.context import Context
from kel.core import Store
from kel.search import Search


class FN08SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'kel.sqlite3')
        self.context = Context(self.store)  # the real schema, including rewound_messages
        with contextlib.closing(self.store.connect()) as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS vetting_sessions(id TEXT PRIMARY KEY, project_id TEXT,
                conversation_id TEXT, template TEXT, topic TEXT, state TEXT, current_batch INTEGER,
                created REAL, updated REAL);
            ''')
        self.cid = self.context.conversation('default', title='Garden')
        with self.store.transaction() as db:
            db.execute("INSERT INTO vetting_sessions VALUES('s1','default',?,'product-ui','Trellis layout','ACTIVE',1,1,2)",
                       (self.cid,))

    def add(self, text):
        return self.store.add_message(text, 'user', self.cid)

    def test_a_word_far_into_a_long_message_is_found(self):
        self.add('x' * 300 + ' the word periwinkle sits here')
        hit = Search(self.store).run('periwinkle')['conversations'][0]
        self.assertEqual(hit['id'], self.cid)
        self.assertIn('periwinkle', hit['snippet'])

    def test_vetting_hits_name_their_chat(self):
        hit = Search(self.store).run('trellis')['vetting'][0]
        self.assertEqual(hit['conversation_id'], self.cid)

    def test_rewound_messages_are_not_found(self):
        seq = self.add('a note about marigolds')
        with self.store.transaction() as db:
            db.execute('INSERT INTO rewound_messages VALUES(?,?,?,?)', (seq, self.cid, 'edit', 1))
        self.assertEqual(Search(self.store).run('marigolds')['conversations'], [])


if __name__ == '__main__':
    unittest.main()
