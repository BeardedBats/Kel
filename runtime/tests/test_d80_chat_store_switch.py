"""D-80 and CP-10a stage 3 (D-77): the switch to the one chat store with a fresh start, and chat state
kept by the engine.

The desktop drives the switch (`chatStoreMigration.ts`): backup, freeze every existing chat as legacy
and archived, archive them in aioncore, complete. These tests cover the engine's half: the backup is
made once and reused by a resumed switch, freezing is idempotent, completing sets `chat_store =
engine`; the renderer's rename/pin/archive/delete land in `chat_state`; the Memory mirror still holds
every chat (the frozen, archived ones too) and leaves deleted ones out; engine search skips deleted
chats. Synthetic data only; no model is called.
"""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest import mock
import uuid

from kel import chat_links as links_module
from kel import chat_state as state_module
from kel import memory_mirror
from kel.chat_links import ChatLinks
from kel.chat_state import ChatState
from kel.core import Store


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        self.data = Path(self.tmp.name) / 'Data'
        self.engine = self.data / 'engine'
        (self.data / 'store').mkdir(parents=True)
        self.memory = Path(self.tmp.name) / 'Memory'
        env = mock.patch.dict(os.environ, {'KEL_MEMORY_ROOT': str(self.memory), 'KEL_MEMORY_MIRROR': '0'})
        env.start()
        self.addCleanup(env.stop)
        for key in ('KEL_CHAT_STORE', 'AIONUI_DATA_DIR', 'KEL_HOST_DATA_DIR'):
            os.environ.pop(key, None)
        self.store = Store(self.engine)
        from kel.context import Context
        from kel.projects import Projects
        Context(self.store)
        Projects(self.store)
        self.donor_path = self.data / 'store' / 'aionui-backend.db'
        donor = sqlite3.connect(self.donor_path)
        donor.executescript('''
            CREATE TABLE conversations(id TEXT PRIMARY KEY, name TEXT, extra TEXT, pinned INTEGER, created_at INTEGER,
                                       updated_at INTEGER, archived_at INTEGER);
            CREATE TABLE messages(id TEXT PRIMARY KEY, conversation_id TEXT, msg_id TEXT, type TEXT, content TEXT,
                                  position TEXT, status TEXT, hidden INTEGER, created_at INTEGER);''')
        donor.commit()
        donor.close()

    def _cleanup(self):
        links_module._overrides.pop(str(self.engine.resolve()), None)
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    def engine_chat(self, words=(), title='t'):
        cid = str(uuid.uuid4())
        with self.store.transaction() as db:
            db.execute('INSERT INTO conversations(id,project_id,title,created) VALUES(?,?,?,?)',
                       (cid, 'default', title, time.time()))
            for index, text in enumerate(words):
                db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                           (cid, 'user' if index % 2 == 0 else 'assistant', text, time.time()))
        return cid

    def donor_chat(self, donor, name, rows=(), archived=None, extra=None):
        db = sqlite3.connect(self.donor_path)
        db.execute('INSERT INTO conversations VALUES(?,?,?,?,?,?,?)',
                   (donor, name, json.dumps(extra or {}), 0, 1789357421822, 1789357421822, archived))
        for index, (position, text) in enumerate(rows):
            db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)',
                       ('%s-%d' % (donor, index), donor, 'm', 'text', json.dumps({'content': text}), position,
                        'finish', 0, 1789357421822 + index))
        db.commit()
        db.close()

    def archive_in_donor(self, donor):
        db = sqlite3.connect(self.donor_path)
        db.execute('UPDATE conversations SET archived_at=? WHERE id=?', (1789357500000, donor))
        db.commit()
        db.close()

    def delete_in_donor(self, donor):
        db = sqlite3.connect(self.donor_path)
        db.execute('DELETE FROM conversations WHERE id=?', (donor,))
        db.execute('DELETE FROM messages WHERE conversation_id=?', (donor,))
        db.commit()
        db.close()


class SwitchTests(_Base):
    def test_backup_copies_both_databases_and_the_link_files_once(self):
        (self.engine / 'aion-conversations.json').write_text('{"a": "b"}')
        (self.engine / 'aion-history.json').write_text('{}')
        (self.engine / 'aion-session-map').mkdir()
        (self.engine / 'aion-session-map' / 'x.json').write_text('{"a": "b"}')
        self.donor_chat('old', 'Old chat', [('right', 'hello')])
        state = ChatState(self.store)
        self.assertEqual(state.store_action({'action': 'status'}), {'state': 'none'})
        first = state.store_action({'action': 'backup', 'donor_db': str(self.donor_path)})
        folder = Path(first['backup'])
        self.assertEqual(first['state'], 'started')
        self.assertTrue(folder.is_relative_to(self.engine / 'chat-store-migration'))
        for name in ('kel.sqlite3', 'aionui-backend.db', 'aion-conversations.json', 'aion-history.json',
                     'aion-session-map/x.json', 'README.txt'):
            self.assertTrue((folder / name).is_file(), name)
        copy = sqlite3.connect(folder / 'aionui-backend.db')
        self.assertEqual(copy.execute('SELECT name FROM conversations').fetchall(), [('Old chat',)])
        copy.close()
        # A resumed switch reuses the first copy: a second one would hold chats already archived.
        again = state.store_action({'action': 'backup', 'donor_db': str(self.donor_path)})
        self.assertEqual(again['backup'], first['backup'])
        self.assertEqual(len(list((self.engine / 'chat-store-migration').iterdir())), 1)
        from kel import backup
        self.assertIn('chat-store-migration', backup.VOLATILE_ENTRIES, "the safety copy keeps the app's keys: never in a backup")

    def test_freeze_marks_every_chat_legacy_and_archived_and_is_idempotent(self):
        linked = self.engine_chat(['hi'])
        ChatLinks(self.store).import_links({'a': linked})
        state = ChatState(self.store)
        state.store_action({'action': 'backup', 'donor_db': str(self.donor_path)})
        chats = [{'donor': 'a', 'title': 'First'}, {'donor': 'b', 'conversation': 'c-b', 'title': 'Second'}]
        self.assertEqual(state.store_action({'action': 'freeze', 'chats': chats})['frozen'], 2)
        a = state.get('a')
        self.assertIsNotNone(a['legacy'])
        self.assertIsNotNone(a['archived_at'])
        self.assertEqual(a['conversation_id'], linked, 'the live link fills a chat that did not name one')
        self.assertEqual(a['title'], 'First')
        self.assertEqual(state.get('b')['conversation_id'], 'c-b')
        first_times = (a['legacy'], a['archived_at'])
        self.assertEqual(state.store_action({'action': 'freeze', 'chats': chats})['frozen'], 0, 'nothing changes twice')
        again = state.get('a')
        self.assertEqual((again['legacy'], again['archived_at']), first_times)

    def test_complete_records_the_switch_and_sets_the_one_store(self):
        links = ChatLinks(self.store)
        links.set_mode('legacy')  # an install that had rolled back, say
        state = ChatState(self.store)
        state.store_action({'action': 'backup', 'donor_db': str(self.donor_path)})
        done = state.store_action({'action': 'complete', 'archived': 3})
        self.assertEqual(done['state'], 'done')
        self.assertEqual(done['archived'], 3)
        self.assertTrue(done['finished'])
        self.assertEqual(links.mode(), 'engine')
        self.assertEqual(state.store_action({'action': 'complete', 'archived': 9})['archived'], 3, 'once only')
        self.assertEqual(state.store_action({'action': 'status'})['state'], 'done')
        with mock.patch.dict(os.environ, {'KEL_CHAT_STORE': 'legacy'}):
            self.assertEqual(links.mode(), 'legacy', 'the rollback switch still wins')

    def test_the_backup_can_be_made_without_an_app_database(self):
        state = ChatState(self.store)
        record = state.store_action({'action': 'backup', 'donor_db': str(self.data / 'missing.db')})
        self.assertIn('kel.sqlite3', record['copied'])
        self.assertEqual(record['skipped'], [str(self.data / 'missing.db')])

    def test_unknown_actions_are_refused(self):
        with self.assertRaises(ValueError):
            ChatState(self.store).store_action({'action': 'erase'})
        with self.assertRaises(ValueError):
            ChatState(self.store).apply({'action': 'freeze'})


class ChatStateRouteTests(_Base):
    def setUp(self):
        super().setUp()
        os.environ['KEL_REVIEWER'] = 'none'
        os.environ['KEL_SKIP_TELEMETRY'] = '1'
        from kel.service import Service
        self.service = Service(self.data / 'svc')
        self.service.engine.adapters = {}
        self.service.stop.set()
        self.addCleanup(self.service.shutdown)

    def test_rename_pin_archive_unarchive_and_delete_are_kept(self):
        act = self.service.action
        act('/api/chat-state', {'donor': 'chat', 'title': '  Plans   for Friday '})
        act('/api/chat-state', {'donor': 'chat', 'pinned': True})
        row = act('/api/chat-state', {'action': 'get', 'donor': 'chat'})['chat']
        self.assertEqual(row['title'], 'Plans for Friday')
        self.assertIsNotNone(row['pinned_at'])
        row = act('/api/chat-state', {'donor': 'chat', 'archived': True})
        self.assertIsNotNone(row['archived_at'])
        self.assertIsNone(row['pinned_at'], 'archiving unpins, as in the sidebar')
        self.assertIsNone(act('/api/chat-state', {'donor': 'chat', 'archived': False})['archived_at'])
        act('/api/chat-state', {'donor': 'chat', 'archived': True})
        act('/api/chat-state', {'donor': 'other', 'archived': True})
        act('/api/chat-state', {'donor': 'kept'})
        self.assertEqual(act('/api/chat-state', {'action': 'delete-archived'}), {'deleted': 2})
        rows = {r['donor_id']: r for r in act('/api/chat-state', {'action': 'get'})['chats']}
        self.assertIsNotNone(rows['chat']['deleted_at'])
        self.assertIsNone(rows['kept']['deleted_at'])
        with self.assertRaises(ValueError):
            act('/api/chat-state', {'title': 'no chat'})

    def test_the_switch_route_runs_the_steps(self):
        act = self.service.action
        self.assertEqual(act('/api/chat-store', {'action': 'status'})['state'], 'none')
        self.assertEqual(act('/api/chat-store', {'action': 'backup'})['state'], 'started')
        act('/api/chat-store', {'action': 'freeze', 'chats': [{'donor': 'x'}]})
        self.assertEqual(act('/api/chat-store', {'action': 'complete'})['state'], 'done')
        self.assertEqual(act('/api/chat-link', {'action': 'mode'})['mode'], 'engine')

    def test_search_leaves_a_deleted_chat_out(self):
        store = self.service.store
        cid = str(uuid.uuid4())
        with store.transaction() as db:
            db.execute('INSERT INTO conversations(id,project_id,title,created) VALUES(?,?,?,?)',
                       (cid, 'default', 'Chat', time.time()))
            db.execute('INSERT INTO messages(conversation_id,role,text,at) VALUES(?,?,?,?)',
                       (cid, 'user', 'find the zebra', time.time()))
        ChatLinks(store).link('chat', cid, 'acp')
        from kel.search import Search
        self.assertEqual([c['id'] for c in Search(store).run('zebra')['conversations']], [cid])
        self.service.action('/api/chat-state', {'donor': 'chat', 'deleted': True})
        self.assertEqual(Search(store).run('zebra')['conversations'], [])


class MirrorTests(_Base):
    """The Memory mirror on the one store: every chat, the ones archived at the switch too."""

    def files(self):
        root = self.memory / 'Kel' / 'chats'
        return {p.relative_to(root).as_posix(): p.read_text(encoding='utf-8') for p in root.rglob('*.md')}

    def test_archived_old_chats_new_chats_and_deleted_ones(self):
        old_engine = self.engine_chat(['old question', 'old answer'])
        self.donor_chat('old', 'Before the switch', [('right', 'old question'), ('left', 'old answer'),
                                                     ('left', 'only the app kept this')],
                        extra={'kel_conversation_id': old_engine})
        self.donor_chat('older', 'Already archived', [('right', 'archived long ago')], archived=1789357421822)
        state = ChatState(self.store)
        state.store_action({'action': 'backup', 'donor_db': str(self.donor_path)})
        ChatLinks(self.store).import_links({'old': old_engine})
        state.store_action({'action': 'freeze', 'chats': [{'donor': 'old'}, {'donor': 'older'}]})
        self.archive_in_donor('old')
        state.store_action({'action': 'complete', 'archived': 1})
        # After the switch: a new chat, linked by the ACP host; its words live in the engine only.
        new_engine = self.engine_chat(['new question', 'new answer'])
        ChatLinks(self.store).link('new', new_engine, 'acp')
        self.donor_chat('new', 'After the switch', [('right', 'new question')])
        # A chat made and then deleted after the switch.
        gone_engine = self.engine_chat(['deleted words'])
        ChatLinks(self.store).link('gone', gone_engine, 'acp')
        self.donor_chat('gone', 'Deleted chat')
        state.set({'donor': 'gone', 'deleted': True})
        self.delete_in_donor('gone')

        memory_mirror.sync(self.engine)
        files = self.files()
        before = next(text for name, text in files.items() if name.endswith('Before the switch.md'))
        self.assertIn('Archived', before)
        self.assertIn('old answer', before)
        self.assertIn('only the app kept this', before, 'words only the app held stay readable')
        older = next(text for name, text in files.items() if name.endswith('Already archived.md'))
        self.assertIn('Archived', older)
        after = next(text for name, text in files.items() if name.endswith('After the switch.md'))
        self.assertNotIn('Archived', after)
        self.assertIn('new answer', after, "the one store's words")
        joined = '\n'.join(files.values())
        self.assertNotIn('deleted words', joined)
        self.assertNotIn('Deleted chat', '\n'.join(files))

    def test_legacy_mode_mirror_is_unchanged(self):
        cid = self.engine_chat(['q', 'a'])
        self.donor_chat('chat', 'Legacy chat', [('right', 'q')], extra={'kel_conversation_id': cid})
        ChatLinks(self.store).set_mode('legacy')
        memory_mirror.sync(self.engine)
        text = next(t for n, t in self.files().items() if n.endswith('Legacy chat.md'))
        self.assertIn('## Kel\n\na', text)


if __name__ == '__main__':
    unittest.main()
