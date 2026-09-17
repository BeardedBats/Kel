"""Backup and restore tests (docs/basic-ux-sweep/09_PERSISTENCE_AND_BACKUP.md).

Backups are local folders with a description file; credentials are excluded; restore is staged and
applied at the next engine start, keeping the previous data beside it.
"""
import contextlib
import json
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path

from kel.backup import INFO, MARKER, STAGING, Backup, apply_pending_restore
from kel import backup as backup_module
from kel.core import PolicyError, Store
from kel.transcription import Transcription


class BackupBase(unittest.TestCase):
    def setUp(self):
        sys.stdout.reconfigure(errors='replace') if hasattr(sys.stdout, 'reconfigure') else None
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.store = Store(base / 'data' / 'kel.sqlite3')
        self.store.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup = Backup(self.store)
        self.target = base / 'backups'
        self.target.mkdir()
        self.transcripts = Transcription(self.store)

    def tearDown(self):
        self.tmp.cleanup()


class CreateAndInspectTests(BackupBase):
    def test_create_then_inspect_reports_content(self):
        self.transcripts.save_recording('alpha note', 500, None) if False else None
        created = self.backup.create(str(self.target))
        self.assertTrue(Path(created['folder']).is_dir())
        self.assertTrue((Path(created['folder']) / INFO).exists())
        details = self.backup.inspect(created['folder'])
        self.assertEqual(details['format'], 1)
        self.assertIn('summary', details)

    def test_invalid_target_and_source_are_plain_errors(self):
        with self.assertRaises(PolicyError):
            self.backup.create(str(self.target / 'missing'))
        with self.assertRaises(PolicyError):
            self.backup.inspect(str(self.target))


class LiveWriteTests(BackupBase):
    def test_backup_works_while_another_connection_is_writing(self):
        with self.store.transaction() as db:
            db.execute("INSERT INTO transcripts(id, name, text, duration_ms, source_type, status, created, updated) "
                       "VALUES('live1','Live one','content',100,'recording','complete',1,1)")
        writer = self.store.connect()
        try:
            writer.execute('BEGIN IMMEDIATE')
            writer.execute("INSERT INTO transcripts(id, name, text, duration_ms, source_type, status, created, updated) "
                           "VALUES('live2','Live two','content',100,'recording','complete',2,2)")
            created = self.backup.create(str(self.target))
            writer.execute('COMMIT')
        finally:
            writer.close()
        copied = Path(created['folder']) / self.backup.db_name
        con = sqlite3.connect(str(copied))
        names = sorted(row[0] for row in con.execute('SELECT name FROM transcripts'))
        con.close()
        self.assertIn('Live one', names)


class SecretExclusionTests(BackupBase):
    def test_transcription_key_never_lands_in_the_backup(self):
        self.transcripts._set_setting('meta_api_key', 'secret-value-123')
        created = self.backup.create(str(self.target))
        copied = Path(created['folder']) / self.backup.db_name
        con = sqlite3.connect(str(copied))
        row = con.execute("SELECT value FROM transcription_settings WHERE name='meta_api_key'").fetchone()
        con.close()
        self.assertIsNone(row)
        notes = json.loads((Path(created['folder']) / INFO).read_text(encoding='utf-8'))
        self.assertIn('excluded', notes['notes'])


class RestoreTests(BackupBase):
    def test_stage_then_apply_restores_previous_content(self):
        self.transcripts.save_recording('keep me', 400, None) if False else None
        # Seed one real transcript row through the store so counts are meaningful.
        with self.store.transaction() as db:
            db.execute("INSERT INTO transcripts(id, name, text, duration_ms, source_type, status, created, updated) "
                       "VALUES('t1','Keep me','hello world',400,'recording','complete',1,1)")
        created = self.backup.create(str(self.target))
        with self.store.transaction() as db:
            db.execute('DELETE FROM transcripts')
        staged = self.backup.stage_restore(created['folder'])
        self.assertTrue(staged['restart_required'])
        self.assertTrue((Path(self.store.root) / MARKER).exists())
        self.assertTrue(apply_pending_restore(self.store))
        with contextlib.closing(self.store.connect()) as db:
            names = [row['name'] for row in db.execute('SELECT name FROM transcripts')]
        self.assertEqual(names, ['Keep me'])
        self.assertFalse((Path(self.store.root) / MARKER).exists())
        self.assertFalse((Path(self.store.root) / STAGING).exists())


class RuntimeTreeTests(BackupBase):
    """A backup carries user data, not the app's own runtime state.

    The host keeps Chromium's user-data tree (caches, storage, locks) and the app holds log files
    and session markers open while it runs; copying them fails on Windows and is what made
    `backup-now` answer "Kel could not finish the backup" in the packaged app.
    """

    def test_runtime_trees_are_left_out_and_host_keeps_config(self):
        (self.store.root / 'logs').mkdir(exist_ok=True)
        (self.store.root / 'logs' / 'engine.stdout').write_text('noise', encoding='utf-8')
        (self.store.root / 'desktop.log').write_text('noise', encoding='utf-8')
        host = self.store.root / 'host'
        (host / 'Cache').mkdir(parents=True, exist_ok=True)
        (host / 'Cache' / 'data.bin').write_bytes(b'cache')
        (host / 'config').mkdir(parents=True, exist_ok=True)
        (host / 'config' / 'aionui-config.txt').write_text('{"ui.zoomFactor": 1}', encoding='utf-8')

        created = self.backup.create(str(self.target))
        folder = Path(created['folder'])

        self.assertFalse((folder / 'logs').exists())
        self.assertFalse((folder / 'desktop.log').exists())
        self.assertFalse((folder / 'host' / 'Cache').exists())
        self.assertTrue((folder / 'host' / 'config' / 'aionui-config.txt').exists())
        self.assertTrue((folder / self.backup.db_name).exists())

    def test_backup_carries_the_desktop_chat_database(self):
        """The chats live in the desktop database inside `host`; a backup without it is empty."""
        desktop = self.store.root / 'host' / 'aionui'
        desktop.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(str(desktop / 'aionui-backend.db'))
        source.execute('CREATE TABLE conversations (id TEXT PRIMARY KEY, name TEXT)')
        source.execute("INSERT INTO conversations VALUES('c1', 'Rich rendering chat')")
        source.commit()
        source.close()

        created = self.backup.create(str(self.target))
        copied = Path(created['folder']) / 'host' / 'aionui' / 'aionui-backend.db'
        self.assertTrue(copied.exists())
        con = sqlite3.connect(str(copied))
        self.assertEqual(con.execute('SELECT name FROM conversations').fetchone()[0], 'Rich rendering chat')
        con.close()
        self.assertFalse((Path(created['folder']) / 'host' / 'aionui' / 'aionui-backend.db-wal').exists())

    def test_staged_restore_applies_while_kel_is_running(self):
        """The app is already up when the engine starts, so the restore must merge, not delete."""
        with self.store.transaction() as db:
            db.execute("INSERT INTO transcripts(id, name, text, duration_ms, source_type, status, created, updated) "
                       "VALUES('t1','Keep me','hello world',400,'recording','complete',1,1)")
        created = self.backup.create(str(self.target))
        with self.store.transaction() as db:
            db.execute('DELETE FROM transcripts')
        (self.store.root / 'host' / 'Cache').mkdir(parents=True, exist_ok=True)
        (self.store.root / 'host' / 'Cache' / 'data.bin').write_bytes(b'cache')
        (self.store.root / 'logs').mkdir(exist_ok=True)
        (self.store.root / 'logs' / 'engine.stdout').write_text('noise', encoding='utf-8')
        self.backup.stage_restore(created['folder'])

        holder = sqlite3.connect(str(self.store.db_path))
        try:
            self.assertTrue(apply_pending_restore(self.store))
        finally:
            holder.close()

        with contextlib.closing(self.store.connect()) as db:
            names = [row['name'] for row in db.execute('SELECT name FROM transcripts')]
        self.assertEqual(names, ['Keep me'])
        self.assertTrue((self.store.root / 'host' / 'Cache' / 'data.bin').exists())
        self.assertTrue((self.store.root / 'logs' / 'engine.stdout').exists())
        self.assertFalse((self.store.root / STAGING).exists())
        self.assertFalse((self.store.root / MARKER).exists())

    def test_a_file_the_app_holds_open_is_recorded_not_fatal(self):
        (self.store.root / 'aion-history.json').write_text('{"x": 1}', encoding='utf-8')
        original = backup_module._copy_with_retries

        def locked(source, destination):
            if Path(source).name == 'aion-history.json':
                raise PermissionError('[WinError 32] The process cannot access the file')
            return original(source, destination)

        backup_module._copy_with_retries = locked
        try:
            created = self.backup.create(str(self.target))
        finally:
            backup_module._copy_with_retries = original

        folder = Path(created['folder'])
        self.assertTrue((folder / self.backup.db_name).exists())
        self.assertIn('aion-history.json', created['skipped'])
        stored = json.loads((folder / INFO).read_text(encoding='utf-8'))
        self.assertIn('in use', stored['notes'])
        self.assertEqual(self.backup.inspect(created['folder'])['format'], 1)


if __name__ == '__main__':
    unittest.main()
