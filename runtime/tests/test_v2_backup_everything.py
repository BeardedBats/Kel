"""ST-01 — "Back up now" saves everything: the whole Data tree (engine, chat store, host config).

A fixture laid out exactly like the installed app (``Data\\{engine,store,host}``) proves: both
databases are copied through SQLite (the chat store's WAL included), the store's files, host config,
Kibble assets and transcripts travel; caches, logs, locks, downloaded runtimes and credentials do
not; the summary counts the sidebar's chats; and a restore validates, keeps the live data beside it,
brings every part back and keeps the live credentials.
"""
import contextlib
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from kel.backup import INFO, MARKER, STAGING, Backup, apply_pending_restore
from kel.core import PolicyError, Store
from kel.transcription import Transcription


def _store_db(path):
    con = sqlite3.connect(str(path))
    con.execute('PRAGMA journal_mode=WAL')
    con.executescript('''
        CREATE TABLE users(id TEXT PRIMARY KEY, username TEXT, password_hash TEXT NOT NULL,
                           jwt_secret TEXT, encryption_secret TEXT);
        CREATE TABLE providers(id TEXT PRIMARY KEY, name TEXT, api_key_encrypted TEXT NOT NULL);
        CREATE TABLE oauth_tokens(user_id TEXT, server_url TEXT, access_token TEXT NOT NULL,
                                  PRIMARY KEY(user_id, server_url));
        CREATE TABLE conversations(id TEXT PRIMARY KEY, name TEXT, archived_at INTEGER);
        CREATE TABLE messages(id TEXT PRIMARY KEY, conversation_id TEXT, content TEXT);
    ''')
    con.execute("INSERT INTO users VALUES('u1','nick','HASH','JWT','ENC')")
    con.execute("INSERT INTO providers VALUES('p1','OpenAI','sk-live-key')")
    con.execute("INSERT INTO oauth_tokens VALUES('u1','https://mcp.example','tok-123')")
    for cid, archived in (('c1', None), ('c2', None), ('c3', 99)):
        con.execute('INSERT INTO conversations VALUES(?,?,?)', (cid, 'Chat ' + cid, archived))
    con.execute("INSERT INTO messages VALUES('m1','c1','hello')")
    con.commit()
    return con


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._cleanup)
        base = Path(self.tmp.name)
        self.data = base / 'Data'
        self.engine = self.data / 'engine'
        self.chats = self.data / 'store'
        self.host = self.data / 'host'
        for folder in (self.engine, self.chats, self.host):
            folder.mkdir(parents=True)
        self.store = Store(self.engine)
        Transcription(self.store)  # the transcripts table, as the service creates it
        with self.store.transaction() as db:
            db.execute("INSERT INTO transcripts(id, name, text, duration_ms, source_type, status, created,"
                       " updated) VALUES('t1','Keep me','hello',400,'recording','complete',1,1)")
        self.write(self.engine / 'kel-credentials.json', '{"openai": "secret"}')
        self.write(self.engine / 'dogfood' / 'screenshots' / 'FIX-0001.png', 'png')
        self.write(self.engine / 'transcription' / 'audio' / 't1.webm', 'audio')
        self.write(self.engine / 'logs' / 'engine.stdout', 'noise')
        self.write(self.engine / 'desktop.log', 'noise')
        self.write(self.engine / 'controller.lock', '1')
        self.write(self.engine / 'broker-locks' / 'x.lock', '1')
        self.live = _store_db(self.chats / 'aionui-backend.db')
        self.addCleanup(self.live.close)
        # A write that sits only in the WAL (the app holds the database open).
        self.live.execute("INSERT INTO messages VALUES('m2','c2','only in the wal')")
        self.live.commit()
        self.write(self.chats / 'aionui-backend.db.instance.lock', '')
        self.write(self.chats / '.builtin-skills.lock', '')
        self.write(self.chats / 'extension-states.json', '{}')
        self.write(self.chats / 'conversations' / 'users' / 'u1' / 'c1.json', '{"c": 1}')
        self.write(self.chats / 'builtin-skills' / 'mermaid' / 'SKILL.md', '# mermaid')
        self.write(self.chats / 'runtime' / 'node' / 'node.exe', 'binary')
        self.write(self.host / 'config' / 'aionui-config.txt', 'zoom=1')
        self.write(self.host / 'config' / 'skills' / 'mine' / 'SKILL.md', '# mine')
        for cache in ('Cache', 'Code Cache', 'GPUCache', 'DawnWebGPUCache', 'Local Storage'):
            self.write(self.host / cache / 'data', 'cache')
        self.write(self.host / 'logs' / 'main.log', 'noise')
        self.target = base / 'backups'
        self.target.mkdir()
        self.backup = Backup(self.store)

    def _cleanup(self):
        try:
            self.tmp.cleanup()
        except PermissionError:
            pass

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def query(self, db_path, sql):
        with contextlib.closing(sqlite3.connect(str(db_path))) as con:
            return con.execute(sql).fetchall()


class CreateTests(Fixture):
    def test_every_part_is_backed_up_and_runtime_state_is_not(self):
        created = self.backup.create(str(self.target))
        folder = Path(created['folder'])
        self.assertEqual(created['parts'], ['engine', 'store', 'host'])
        for kept in ('engine/kel.sqlite3', 'engine/dogfood/screenshots/FIX-0001.png',
                     'engine/transcription/audio/t1.webm', 'store/aionui-backend.db',
                     'store/extension-states.json', 'store/conversations/users/u1/c1.json',
                     'store/builtin-skills/mermaid/SKILL.md', 'host/config/aionui-config.txt',
                     'host/config/skills/mine/SKILL.md'):
            self.assertTrue((folder / kept).exists(), kept)
        for left_out in ('engine/kel-credentials.json', 'engine/logs', 'engine/desktop.log',
                         'engine/controller.lock', 'engine/broker-locks',
                         'store/aionui-backend.db-wal', 'store/aionui-backend.db-shm',
                         'store/aionui-backend.db.instance.lock', 'store/.builtin-skills.lock',
                         'store/runtime', 'host/Cache', 'host/Code Cache', 'host/GPUCache',
                         'host/DawnWebGPUCache', 'host/Local Storage', 'host/logs'):
            self.assertFalse((folder / left_out).exists(), left_out)

    def test_the_chat_database_is_complete_and_carries_no_credentials(self):
        folder = Path(self.backup.create(str(self.target))['folder'])
        chats = folder / 'store' / 'aionui-backend.db'
        self.assertEqual(sorted(r[0] for r in self.query(chats, 'SELECT id FROM messages')), ['m1', 'm2'],
                         'the write that was only in the WAL is in the backup')
        self.assertEqual(self.query(chats, 'SELECT password_hash, jwt_secret, encryption_secret FROM users'),
                         [('', None, None)])
        self.assertEqual(self.query(chats, 'SELECT api_key_encrypted FROM providers'), [('',)])
        self.assertEqual(self.query(chats, 'SELECT COUNT(*) FROM oauth_tokens'), [(0,)])
        # The live database is untouched by the stripping.
        self.assertEqual(self.live.execute('SELECT jwt_secret FROM users').fetchone()[0], 'JWT')
        info = json.loads((folder / INFO).read_text(encoding='utf-8'))
        self.assertEqual(info['format'], 2)
        self.assertIn('Credentials are excluded', info['notes'])
        self.assertIn('kel-credentials.json', info['skipped'])

    def test_the_summary_counts_the_sidebar_chats(self):
        created = self.backup.create(str(self.target))
        summary = created['summary']
        self.assertEqual(summary['conversations'], 2, 'the store\'s chats, not engine records (one archived)')
        self.assertEqual(summary['messages'], 2)
        self.assertEqual(summary['transcripts'], 1)
        self.assertEqual(self.backup.inventory()['summary']['conversations'], 2)

    def test_inspect_describes_and_validates(self):
        folder = self.backup.create(str(self.target))['folder']
        details = self.backup.inspect(folder)
        self.assertEqual((details['format'], details['parts']), (2, ['engine', 'store', 'host']))
        self.assertEqual(details['summary']['conversations'], 2)
        self.assertIn('your chats', details['restores'])
        self.assertIn('credentials', details['excludes'])
        (Path(folder) / 'store' / 'aionui-backend.db').write_bytes(b'not a database at all' * 100)
        with self.assertRaises(PolicyError):
            self.backup.inspect(folder)
        (Path(folder) / 'store' / 'aionui-backend.db').unlink()
        with self.assertRaises(PolicyError):
            self.backup.inspect(folder)


class RestoreTests(Fixture):
    def test_restore_brings_every_part_back_keeps_live_credentials_and_the_old_data_beside(self):
        folder = self.backup.create(str(self.target))['folder']
        # Changes after the backup.
        self.live.execute("DELETE FROM conversations WHERE id='c1'")
        self.live.execute("UPDATE users SET jwt_secret='JWT-NOW', password_hash='HASH-NOW'")
        self.live.execute("UPDATE providers SET api_key_encrypted='sk-now'")
        self.live.execute("INSERT INTO oauth_tokens VALUES('u1','https://other','tok-now')")
        self.live.commit()
        self.write(self.host / 'config' / 'aionui-config.txt', 'zoom=2')
        with self.store.transaction() as db:
            db.execute('DELETE FROM transcripts')
        staged = self.backup.stage_restore(folder)
        self.assertTrue(staged['restart_required'])
        self.assertTrue((self.engine / MARKER).exists())
        self.assertTrue(apply_pending_restore(self.store))
        chats = self.chats / 'aionui-backend.db'
        self.assertEqual(sorted(r[0] for r in self.query(chats, 'SELECT id FROM conversations')),
                         ['c1', 'c2', 'c3'])
        self.assertEqual(self.query(chats, 'SELECT password_hash, jwt_secret, encryption_secret FROM users'),
                         [('HASH-NOW', 'JWT-NOW', 'ENC')], 'live credentials stay in custody')
        self.assertEqual(self.query(chats, 'SELECT api_key_encrypted FROM providers'), [('sk-now',)])
        self.assertEqual(sorted(r[0] for r in self.query(chats, 'SELECT server_url FROM oauth_tokens')),
                         ['https://mcp.example', 'https://other'])
        self.assertEqual((self.host / 'config' / 'aionui-config.txt').read_text(encoding='utf-8'), 'zoom=1')
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual([r['name'] for r in db.execute('SELECT name FROM transcripts')], ['Keep me'])
        # Live runtime state and credentials are untouched; the previous data is kept beside.
        self.assertTrue((self.host / 'Cache' / 'data').exists())
        self.assertTrue((self.engine / 'kel-credentials.json').exists())
        for part in ('engine', 'store', 'host'):
            snapshots = list(self.data.glob(part + '.pre-restore-*'))
            self.assertEqual(len(snapshots), 1, part)
        before = next(self.data.glob('host.pre-restore-*'))
        self.assertEqual((before / 'config' / 'aionui-config.txt').read_text(encoding='utf-8'), 'zoom=2')
        store_before = next(self.data.glob('store.pre-restore-*')) / 'aionui-backend.db'
        self.assertEqual(sorted(r[0] for r in self.query(store_before, 'SELECT id FROM conversations')),
                         ['c2', 'c3'])
        self.assertFalse((self.engine / STAGING).exists())
        self.assertFalse((self.engine / MARKER).exists())
        self.assertFalse(apply_pending_restore(self.store), 'a second apply is a no-op')

    def test_an_engine_only_backup_from_an_earlier_kel_still_restores(self):
        legacy = self.target / 'Kel-Backup-legacy'
        legacy.mkdir()
        with contextlib.closing(sqlite3.connect(str(self.store.db_path))) as src, \
                contextlib.closing(sqlite3.connect(str(legacy / 'kel.sqlite3'))) as dst:
            src.backup(dst)
        (legacy / INFO).write_text(json.dumps({'format': 1, 'database': 'kel.sqlite3',
                                               'created': time.time()}), encoding='utf-8')
        details = self.backup.inspect(str(legacy))
        self.assertEqual((details['format'], details['parts']), (1, ['engine']))
        with self.store.transaction() as db:
            db.execute('DELETE FROM transcripts')
        self.backup.stage_restore(str(legacy))
        self.assertTrue(apply_pending_restore(self.store))
        with contextlib.closing(self.store.connect()) as db:
            self.assertEqual([r['name'] for r in db.execute('SELECT name FROM transcripts')], ['Keep me'])
        self.assertEqual(self.query(self.chats / 'aionui-backend.db', 'SELECT COUNT(*) FROM conversations'),
                         [(3,)], 'an engine-only backup leaves the chats alone')


if __name__ == '__main__':
    unittest.main()
