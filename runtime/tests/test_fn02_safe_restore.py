"""FN-02 — a restore is applied once, all or nothing, and never re-applied on a later start.

The finding (installed 5294c27, on a copy of the data): back up → rename a project → restore →
restart. The restore ran inside the engine after the window and the chat store already held their
files, so it failed partway (`PermissionError`), yet the engine part was already replaced and the
pending marker was kept on purpose — every later start re-applied it: a rename made after the
restore reverted again, a stopped job came back, and each start added another set of
`*.pre-restore-*` folders.

These tests pin the replacement: the desktop applies the staged restore before anything opens the
data (`apply_restore`), every entry is swapped by renames recorded in a journal, a failure in any
part undoes the parts already swapped, the attempt always ends (marker cleared, outcome in plain
words), a crash mid-swap is undone on the next start, and the credentials stay in custody.
"""
import contextlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kel import backup
from kel.backup import (BEFORE_PREFIX, JOURNAL, MARKER, OUTCOME, STAGING, Backup, apply_pending_restore,
                        apply_restore, read_outcome)
from kel.core import Store
from kel.instance_lock import InstanceLock
from kel.transcription import Transcription

RUNTIME = Path(__file__).resolve().parents[1]


def _chats(path):
    con = sqlite3.connect(str(path))
    con.execute('PRAGMA journal_mode=WAL')
    con.executescript('''
        CREATE TABLE users(id TEXT PRIMARY KEY, password_hash TEXT NOT NULL, jwt_secret TEXT,
                           encryption_secret TEXT);
        CREATE TABLE providers(id TEXT PRIMARY KEY, api_key_encrypted TEXT NOT NULL);
        CREATE TABLE conversations(id TEXT PRIMARY KEY, name TEXT, archived_at INTEGER);
        CREATE TABLE messages(id TEXT PRIMARY KEY, conversation_id TEXT, content TEXT);
    ''')
    con.execute("INSERT INTO users VALUES('u1','HASH','JWT','ENC')")
    con.execute("INSERT INTO providers VALUES('p1','sk-then')")
    con.execute("INSERT INTO conversations VALUES('c1','First chat',NULL)")
    con.commit()
    con.close()


class Fixture(unittest.TestCase):
    """A data tree laid out like the installed app: Data\\{engine,store,host}."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.data = base / 'Data'
        self.engine = self.data / 'engine'
        self.chats = self.data / 'store'
        self.host = self.data / 'host'
        for folder in (self.engine, self.chats, self.host):
            folder.mkdir(parents=True)
        self.store = Store(self.engine)
        Transcription(self.store)
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,root TEXT,'
                       'context TEXT,updated REAL)')
            db.execute("INSERT INTO projects VALUES('p1','Alpha',NULL,'',1)")
            db.execute("INSERT INTO jobs VALUES('j1',1,?)", (json.dumps({'state': 'RUNNING'}),))
            db.execute("INSERT OR REPLACE INTO transcription_settings(name,value) VALUES('meta_api_key','key-then')")
        (self.engine / 'kel-credentials.json').write_text('{"anthropic:api_key": "cipher"}', encoding='utf-8')
        (self.engine / 'attachments').mkdir()
        (self.engine / 'attachments' / 'a.txt').write_text('then', encoding='utf-8')
        # A project copy's git objects are read-only: clearing the staged copy must still remove them
        # (found live — the staged copy stayed behind after a rolled-back restore).
        objects = self.engine / 'repositories' / 'r1' / '.git' / 'objects'
        objects.mkdir(parents=True)
        (objects / 'ab12').write_text('blob', encoding='utf-8')
        os.chmod(objects / 'ab12', stat.S_IREAD)
        _chats(self.chats / 'aionui-backend.db')
        (self.chats / 'extension-states.json').write_text('{"then": true}', encoding='utf-8')
        (self.chats / 'runtime').mkdir()
        (self.chats / 'runtime' / 'node.exe').write_text('binary', encoding='utf-8')
        (self.host / 'config').mkdir()
        (self.host / 'config' / 'aionui-config.txt').write_text('zoom=1', encoding='utf-8')
        (self.host / 'Cache').mkdir()
        (self.host / 'Cache' / 'data').write_text('cache', encoding='utf-8')
        self.target = base / 'backups'
        self.target.mkdir()
        env = {'AIONUI_DATA_DIR': str(self.chats), 'KEL_HOST_DATA_DIR': str(self.host)}
        self._env = {key: os.environ.get(key) for key in (*env, backup.OWNER_ENV)}
        os.environ.update(env)
        os.environ.pop(backup.OWNER_ENV, None)
        self.addCleanup(self._restore_env)
        self.addCleanup(setattr, backup, '_RENAME_ATTEMPTS', backup._RENAME_ATTEMPTS)
        backup._RENAME_ATTEMPTS = 1
        self.folder = Backup(self.store).create(str(self.target))['folder']

    def _restore_env(self):
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    # ---- changes Nick makes after the backup ----
    def change_after_backup(self, name='Beta'):
        with self.store.transaction() as db:
            db.execute('UPDATE projects SET name=? WHERE id=?', (name, 'p1'))
            db.execute('UPDATE jobs SET data=? WHERE id=?', (json.dumps({'state': 'CANCELLED'}), 'j1'))
            db.execute("UPDATE transcription_settings SET value='key-now' WHERE name='meta_api_key'")
        (self.engine / 'attachments' / 'a.txt').write_text('now', encoding='utf-8')
        con = sqlite3.connect(str(self.chats / 'aionui-backend.db'))
        con.execute("INSERT INTO conversations VALUES('c2','Later chat',NULL)")
        con.execute("UPDATE providers SET api_key_encrypted='sk-now'")
        con.commit()
        con.close()
        (self.host / 'config' / 'aionui-config.txt').write_text('zoom=2', encoding='utf-8')

    def project_name(self):
        with contextlib.closing(sqlite3.connect(str(self.store.db_path))) as con:
            return con.execute("SELECT name FROM projects WHERE id='p1'").fetchone()[0]

    def job_state(self):
        with contextlib.closing(sqlite3.connect(str(self.store.db_path))) as con:
            return json.loads(con.execute("SELECT data FROM jobs WHERE id='j1'").fetchone()[0])['state']

    def chat_ids(self):
        with contextlib.closing(sqlite3.connect(str(self.chats / 'aionui-backend.db'))) as con:
            return sorted(r[0] for r in con.execute('SELECT id FROM conversations'))

    def query(self, path, sql):
        with contextlib.closing(sqlite3.connect(str(path))) as con:
            return con.execute(sql).fetchall()

    def kept_folders(self):
        return sorted(self.data.glob(BEFORE_PREFIX + '*'))

    def legacy_piles(self):
        return sorted(self.data.glob('*.pre-restore-*'))

    def fail_on(self, part_folder):
        """Make any move into or out of one live part fail, as a held-open file does on Windows."""
        original = backup._rename

        def refuse(source, destination):
            if Path(destination).parent == part_folder or Path(source).parent == part_folder:
                raise PermissionError(13, 'The process cannot access the file because it is being used')
            return original(source, destination)

        backup._rename = refuse
        self.addCleanup(setattr, backup, '_rename', original)
        return lambda: setattr(backup, '_rename', original)


class AtomicSwapTests(Fixture):
    def test_every_part_is_swapped_the_old_data_is_kept_once_and_credentials_stay(self):
        self.change_after_backup()
        Backup(self.store).stage_restore(self.folder)
        result = apply_restore(self.engine)
        self.assertEqual(result['status'], 'restored')
        self.assertEqual(self.project_name(), 'Alpha')
        self.assertEqual(self.chat_ids(), ['c1'])
        self.assertEqual((self.engine / 'attachments' / 'a.txt').read_text(encoding='utf-8'), 'then')
        self.assertEqual((self.host / 'config' / 'aionui-config.txt').read_text(encoding='utf-8'), 'zoom=1')
        # Credentials never change custody: the live values are the ones after the restore.
        self.assertEqual(self.query(self.chats / 'aionui-backend.db', 'SELECT api_key_encrypted FROM providers'),
                         [('sk-now',)])
        self.assertEqual(self.query(self.store.db_path,
                                    "SELECT value FROM transcription_settings WHERE name='meta_api_key'"),
                         [('key-now',)])
        self.assertTrue((self.engine / 'kel-credentials.json').exists())
        # Runtime state the backup leaves out is untouched.
        self.assertTrue((self.host / 'Cache' / 'data').exists())
        self.assertTrue((self.chats / 'runtime' / 'node.exe').exists())
        # One dated folder holds the data from just before the restore.
        kept = self.kept_folders()
        self.assertEqual(len(kept), 1)
        self.assertEqual(self.query(kept[0] / 'engine' / 'kel.sqlite3', "SELECT name FROM projects"), [('Beta',)])
        self.assertEqual(sorted(r[0] for r in self.query(kept[0] / 'store' / 'aionui-backend.db',
                                                         'SELECT id FROM conversations')), ['c1', 'c2'])
        outcome = read_outcome(self.engine)
        self.assertEqual((outcome['ok'], outcome['title'], outcome['notice']), (True, 'Your backup was restored', True))
        self.assertIn(kept[0].name, outcome['detail'])
        self.assertIn('stayed as they were', outcome['detail'])
        for leftover in (MARKER, STAGING, JOURNAL):
            self.assertFalse((self.engine / leftover).exists(), leftover)
        self.assertIsNone(apply_restore(self.engine), 'nothing is pending any more')

    def test_a_failure_in_a_later_part_rolls_back_the_parts_already_swapped(self):
        self.change_after_backup()
        Backup(self.store).stage_restore(self.folder)
        self.fail_on(self.host)  # engine and store swap first, then host fails
        result = apply_restore(self.engine)
        self.assertEqual((result['status'], result['part']), ('rolled_back', 'host'))
        # Everything is exactly as it was before the attempt.
        self.assertEqual(self.project_name(), 'Beta')
        self.assertEqual(self.job_state(), 'CANCELLED')
        self.assertEqual(self.chat_ids(), ['c1', 'c2'])
        self.assertEqual((self.engine / 'attachments' / 'a.txt').read_text(encoding='utf-8'), 'now')
        self.assertEqual((self.host / 'config' / 'aionui-config.txt').read_text(encoding='utf-8'), 'zoom=2')
        self.assertEqual(self.kept_folders(), [], 'a rolled-back attempt leaves no folder behind')
        for leftover in (MARKER, STAGING, JOURNAL):
            self.assertFalse((self.engine / leftover).exists(), leftover)
        outcome = read_outcome(self.engine)
        self.assertEqual((outcome['ok'], outcome['status'], outcome['part']), (False, 'rolled_back', 'host'))
        # JR-8: what happened, which part and why, what Kel did, what to do next — no bare exception.
        self.assertIn('your settings, skills and assistants', outcome['detail'])
        self.assertIn('another program still had some of those files open', outcome['detail'])
        self.assertIn('put back everything it had changed', outcome['detail'])
        self.assertIn('choose Restore in Settings', outcome['detail'])
        self.assertNotIn('PermissionError', outcome['detail'])
        self.assertIn('PermissionError', outcome['technical'])

    def test_a_crash_mid_swap_is_undone_on_the_next_start(self):
        self.change_after_backup()
        Backup(self.store).stage_restore(self.folder)
        original = backup._rename
        moves = []

        def crash(source, destination):
            moves.append(source)
            if len(moves) == 5:
                raise KeyboardInterrupt  # the process dies: no except clause runs
            return original(source, destination)

        backup._rename = crash
        try:
            with self.assertRaises(KeyboardInterrupt):
                apply_restore(self.engine)
        finally:
            backup._rename = original
        self.assertTrue((self.engine / JOURNAL).exists())
        result = apply_restore(self.engine)  # the next start
        self.assertEqual(result['status'], 'rolled_back')
        self.assertEqual(self.project_name(), 'Beta')
        self.assertEqual((self.engine / 'attachments' / 'a.txt').read_text(encoding='utf-8'), 'now')
        self.assertFalse((self.engine / JOURNAL).exists())
        self.assertFalse((self.engine / MARKER).exists())
        self.assertIn('interrupted', read_outcome(self.engine)['detail'])
        self.assertIsNone(apply_restore(self.engine))

    def test_a_crash_after_every_move_finishes_the_restore_instead_of_undoing_it(self):
        Backup(self.store).stage_restore(self.folder)
        original = backup._record_outcome

        def die(*args, **kwargs):
            raise KeyboardInterrupt

        backup._record_outcome = die
        try:
            with self.assertRaises(KeyboardInterrupt):
                apply_restore(self.engine)
        finally:
            backup._record_outcome = original
        self.assertEqual(json.loads((self.engine / JOURNAL).read_text(encoding='utf-8'))['state'], 'done')
        self.assertEqual(apply_restore(self.engine)['status'], 'restored')
        self.assertTrue(read_outcome(self.engine)['ok'])
        self.assertFalse((self.engine / JOURNAL).exists())

    def test_moves_that_cannot_be_undone_yet_are_finished_on_a_later_start_never_reapplied(self):
        self.change_after_backup()
        Backup(self.store).stage_restore(self.folder)
        original = backup._rename
        state = {'failing': False}
        host = self.host

        def flaky(source, destination):
            if Path(source).parent == host or Path(destination).parent == host:
                state['failing'] = True  # the host part is held open
                raise PermissionError(13, 'in use')
            if state['failing'] and Path(source).name == 'aionui-backend.db':
                raise PermissionError(13, 'still in use')  # and putting the chats back fails too
            return original(source, destination)

        backup._rename = flaky
        try:
            result = apply_restore(self.engine)
        finally:
            backup._rename = original
        self.assertEqual(result['status'], 'rollback_incomplete')
        outcome = read_outcome(self.engine)
        self.assertEqual(outcome['title'], 'A restore stopped partway')
        self.assertIn('Nothing was deleted', outcome['detail'])
        self.assertFalse((self.engine / MARKER).exists(), 'never re-applied')
        self.assertTrue((self.engine / JOURNAL).exists(), 'the undo is finished on the next start')
        result = apply_restore(self.engine)
        self.assertEqual(result['status'], 'rolled_back')
        self.assertEqual(self.chat_ids(), ['c1', 'c2'])
        self.assertEqual(self.project_name(), 'Beta')
        self.assertEqual(self.kept_folders(), [])
        self.assertIn('finished putting back', read_outcome(self.engine)['detail'])

    def test_an_engine_still_running_means_nothing_is_touched(self):
        self.change_after_backup()
        Backup(self.store).stage_restore(self.folder)
        running = InstanceLock(self.engine)
        try:
            result = apply_restore(self.engine)
        finally:
            running.close()
        self.assertEqual(result['status'], 'not_started')
        self.assertEqual(self.project_name(), 'Beta')
        self.assertEqual(self.kept_folders(), [])
        self.assertFalse((self.engine / MARKER).exists())
        self.assertIn('engine was still running', read_outcome(self.engine)['detail'])

    def test_the_desktop_owns_restores_so_the_engine_never_applies_one(self):
        Backup(self.store).stage_restore(self.folder)
        os.environ[backup.OWNER_ENV] = 'shell'
        self.assertFalse(apply_pending_restore(self.store))
        self.assertTrue((self.engine / MARKER).exists(), 'left for the desktop to apply at its safe moment')

    def test_the_command_line_the_desktop_runs_applies_and_reports(self):
        Backup(self.store).stage_restore(self.folder)
        env = {**os.environ, 'PYTHONPATH': str(RUNTIME), backup.OWNER_ENV: 'shell'}
        done = subprocess.run([sys.executable, '-m', 'kel.backup', '--apply-restore', '--data', str(self.engine)],
                              capture_output=True, text=True, env=env, cwd=str(RUNTIME), timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])['status'], 'restored')
        again = subprocess.run([sys.executable, '-m', 'kel.backup', '--apply-restore', '--data', str(self.engine)],
                               capture_output=True, text=True, env=env, cwd=str(RUNTIME), timeout=120)
        self.assertEqual(json.loads(again.stdout.strip().splitlines()[-1]), {'ran': False})


class Fn02ReproTests(Fixture):
    """Back up → rename the project → restore → restart (twice), with one part held open."""

    def test_after_a_failed_restore_a_later_rename_survives_restarts_and_nothing_resurrects(self):
        self.change_after_backup('Beta')  # the rename, and the job is stopped
        Backup(self.store).stage_restore(self.folder)
        release = self.fail_on(self.chats)  # the chat store is held open, as in FN-02
        first = apply_restore(self.engine)  # the restart
        release()
        self.assertEqual(first['status'], 'rolled_back')
        self.assertEqual(self.project_name(), 'Beta', 'the engine part was not applied on its own')
        self.assertEqual(self.job_state(), 'CANCELLED', 'the stopped job did not come back')
        # Nick keeps working: a rename made after the failed restore.
        with self.store.transaction() as db:
            db.execute("UPDATE projects SET name='Gamma' WHERE id='p1'")
        for _ in range(2):  # restart twice: the desktop's safe moment, then the engine's own start
            self.assertIsNone(apply_restore(self.engine))
            self.assertFalse(apply_pending_restore(Store(self.engine)))
        self.assertEqual(self.project_name(), 'Gamma')
        self.assertEqual(self.job_state(), 'CANCELLED')
        self.assertEqual(self.kept_folders(), [], 'no folder pile-up')
        self.assertEqual(self.legacy_piles(), [])
        outcome = read_outcome(self.engine)
        self.assertEqual((outcome['status'], outcome['part']), ('rolled_back', 'store'))
        self.assertIn('your chats', outcome['detail'])

    def test_a_looping_restore_left_by_an_earlier_kel_is_stopped_not_applied(self):
        # The state FN-02 left behind: an old-format marker, its staging, the recorded failure and a
        # pile of snapshots from every start that re-applied it.
        self.change_after_backup('Beta')
        Backup(self.store).stage_restore(self.folder)
        marker = json.loads((self.engine / MARKER).read_text(encoding='utf-8'))
        marker.pop('id')
        (self.engine / MARKER).write_text(json.dumps(marker), encoding='utf-8')
        (self.engine / OUTCOME).write_text(json.dumps({'ok': False, 'detail': 'PermissionError',
                                                       'at': marker['staged'] + 60}), encoding='utf-8')
        for stamp in ('20260927-100000', '20260927-110000', '20260927-120000', '20260927-130000'):
            (self.data / ('engine.pre-restore-' + stamp)).mkdir()
        self.assertEqual(read_outcome(self.engine)['title'], 'An earlier restore did not finish')
        self.assertNotEqual(read_outcome(self.engine)['detail'], 'PermissionError')
        result = apply_restore(self.engine)
        self.assertEqual(result['status'], 'abandoned')
        self.assertEqual(self.project_name(), 'Beta', 'the old restore is not applied over newer work')
        self.assertFalse((self.engine / MARKER).exists())
        self.assertFalse((self.engine / STAGING).exists())
        self.assertEqual(len(self.legacy_piles()), 2, 'the pile shrinks to the newest two')
        self.assertIn('stopped retrying', read_outcome(self.engine)['detail'])
        self.assertIsNone(apply_restore(self.engine))


class OutcomeAndWordingTests(Fixture):
    def test_the_notice_is_shown_once_and_settings_can_dismiss_it(self):
        Backup(self.store).stage_restore(self.folder)
        apply_restore(self.engine)
        self.assertTrue(read_outcome(self.engine)['notice'])
        self.assertFalse(backup.mark_outcome(self.engine, notice=False)['notice'])
        dismissed = backup.mark_outcome(self.engine, notice=False, dismissed=True)
        self.assertTrue(dismissed['dismissed'])
        self.assertEqual(dismissed['title'], 'Your backup was restored')

    def test_the_backup_counts_the_projects_nick_sees(self):
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS project_meta(project_id TEXT PRIMARY KEY, kind TEXT NOT NULL '
                       "DEFAULT 'user', archived REAL, created REAL, utility_conversation TEXT)")
            db.execute("INSERT INTO projects VALUES('tmp1','tmpabc',NULL,'',1)")
            db.execute("INSERT INTO projects VALUES('old','Old one',NULL,'',1)")
            db.execute("INSERT INTO project_meta(project_id,kind,archived) VALUES('tmp1','system',5)")
            db.execute("INSERT INTO project_meta(project_id,kind,archived) VALUES('old','user',7)")
            db.execute("INSERT INTO project_meta(project_id,kind) VALUES('p1','user')")
        created = Backup(self.store).create(str(self.target))
        self.assertEqual(created['summary']['projects'], 1, 'only Alpha: not the archived one, not plumbing')

    def test_credentials_are_left_out_on_purpose_and_the_restore_says_they_stay_on_this_pc(self):
        created = Backup(self.store).create(str(self.target))
        self.assertNotIn('kel-credentials.json', created['skipped'])
        self.assertNotIn('in use', created['notes'])
        self.assertIn('on purpose', created['notes'])
        details = Backup(self.store).inspect(created['folder'])
        self.assertIn('on purpose', details['excludes'])
        self.assertIn('on this PC keeps', details['excludes'])
        self.assertIn('stay as they are', details['restores'])


if __name__ == '__main__':
    unittest.main()
