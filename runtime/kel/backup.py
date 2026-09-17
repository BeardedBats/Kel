"""Local backup and restore for Kel's engine data.

What is backed up: chats, projects, work state, Vetting sessions, transcripts, transcript audio,
attachments, engine settings and the host's own settings, skills and assistants. What is never
included: provider credentials and the transcription key (they are stripped from the copied
database and the reason is recorded in BACKUP-INFO.json), nor the runtime state the app holds open
while it runs (Chromium's user-data caches and storage, logs, session markers); anything that still
cannot be read is listed in the backup description instead of failing the whole copy. Restore is
staged and applied on the next engine start, so a failed copy can never leave a half-restored
database; the previous data is kept beside it as `.pre-restore-*`.
"""
import json
import shutil
import sqlite3
import time
from pathlib import Path

from .core import PolicyError

MARKER = 'restore-pending.json'
STAGING = '.restore-staging'
INFO = 'BACKUP-INFO.json'
SECRET_TABLE = 'transcription_settings'
SECRET_KEYS = ('meta_api_key',)
SKIP_ENTRIES = (STAGING, MARKER)
# Runtime state the app keeps open while it runs: never part of a backup.
VOLATILE_ENTRIES = ('logs', 'desktop.log', 'desktop-session.json', 'controller.lock')
# Everything under `host` is Chromium's user-data tree - caches, storage and locks the running
# app holds open - except these two: Kel's own settings/skills/assistants live in `config`, and the
# chats live in the desktop database under `aionui`.
HOST_ENTRY = 'host'
HOST_KEEP = ('config', 'aionui')
# Live SQLite sidecar files and process locks are never copied.
SKIP_SUFFIXES = ('-wal', '-shm', '-journal', '.wal', '.shm', '.journal', '.lock')
DB_SUFFIXES = ('.sqlite3', '.db', '.sqlite')


def _strip_secrets(db_path):
    try:
        con = sqlite3.connect(str(db_path))
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if SECRET_TABLE in tables:
            for key in SECRET_KEYS:
                con.execute('DELETE FROM %s WHERE name=?' % SECRET_TABLE, (key,))
        con.commit()
        con.close()
    except Exception:
        pass  # a backup without our schema simply has nothing to strip


def _summary(db_path):
    out = {}
    try:
        con = sqlite3.connect(str(db_path))

        def count(table):
            try:
                return con.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
            except Exception:
                return None

        out['conversations'] = count('conversations')
        out['messages'] = count('messages')
        out['transcripts'] = count('transcripts')
        out['vetting_sessions'] = count('vetting_sessions')
        con.close()
    except Exception:
        pass
    return {key: value for key, value in out.items() if value is not None}


def _hot_copy_database(source, destination):
    """SQLite-safe copy of a live database (works while the engine holds it open)."""
    src = sqlite3.connect(str(source), timeout=10)
    dst = sqlite3.connect(str(destination))
    try:
        src.execute('PRAGMA busy_timeout=8000')
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()


def _copy_with_retries(source, destination):
    for attempt in range(4):
        try:
            shutil.copy2(source, destination)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(0.15 * (attempt + 1))


def _copy_entry(source, destination, skipped):
    """Copy one entry of the data tree.

    Runtime files the running app holds open (sidecars, locks) are skipped by name, databases are
    copied through SQLite so a live handle in another process cannot block the backup, and anything
    else that cannot be read is recorded in ``skipped`` instead of failing the whole copy.
    """
    lowered = source.name.lower()
    if lowered.endswith(SKIP_SUFFIXES):
        return
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            _copy_entry(child, destination / child.name, skipped)
        return
    if lowered.endswith(DB_SUFFIXES):
        try:
            _hot_copy_database(source, destination)
        except Exception:
            skipped.append(source.name)
        return
    try:
        _copy_with_retries(source, destination)
    except Exception:
        skipped.append(source.name)


class Backup:
    def __init__(self, store):
        self.store = store

    @property
    def root(self):
        return Path(self.store.root)

    @property
    def db_name(self):
        return Path(self.store.db_path).name

    def create(self, target):
        destination_root = Path(str(target or '')).expanduser()
        if not str(target or '').strip() or not destination_root.is_dir():
            raise PolicyError('Choose an existing folder for the backup.')
        folder = destination_root / ('Kel-Backup-' + time.strftime('%Y%m%d-%H%M%S'))
        folder.mkdir()
        skipped = []
        try:
            for entry in self.root.iterdir():
                if entry.name in SKIP_ENTRIES or entry.name in VOLATILE_ENTRIES:
                    continue
                if entry.name.lower().endswith(('-wal', '-shm', '-journal', '.wal', '.shm', '.journal')):
                    # Live SQLite sidecar files are locked and never copied; the hot database
                    # copy below carries a consistent snapshot of their contents.
                    continue
                if entry.name.lower().endswith(('.sqlite3', '.db', '.sqlite')):
                    try:
                        _hot_copy_database(entry, folder / entry.name)
                    except Exception:
                        shutil.rmtree(folder, ignore_errors=True)
                        raise PolicyError('Kel could not read its database for the backup. '
                                          'Close any other Kel window and try again.') from None
                elif entry.is_dir():
                    target_dir = folder / entry.name
                    target_dir.mkdir(exist_ok=True)
                    children = list(entry.iterdir()) if entry.name != HOST_ENTRY else [
                        child for child in entry.iterdir() if child.name in HOST_KEEP]
                    for child in children:
                        _copy_entry(child, target_dir / child.name, skipped)
                else:
                    try:
                        _copy_with_retries(entry, folder / entry.name)
                    except Exception:
                        skipped.append(entry.name)
        except PolicyError:
            raise
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise PolicyError('Kel could not finish the backup. Close any other Kel window '
                              'and try again.') from None
        copied_db = folder / self.db_name
        if copied_db.exists():
            _strip_secrets(copied_db)
        notes = ('Provider credentials and the transcription key are excluded from backups. '
                 'Reconnect them after restoring.')
        if skipped:
            notes += (' Some runtime files were in use and are not in this backup: '
                      + ', '.join(sorted(skipped)) + '.')
        info = {
            'format': 1,
            'app': 'Kel',
            'created': time.time(),
            'database': self.db_name,
            'notes': notes,
            'skipped': sorted(skipped),
            'summary': _summary(copied_db) if copied_db.exists() else {},
        }
        (folder / INFO).write_text(json.dumps(info, indent=2), encoding='utf-8')
        return {'folder': str(folder), 'summary': info['summary'], 'notes': notes,
                'skipped': info['skipped']}

    def inspect(self, source):
        src = Path(str(source or '')).expanduser()
        if not str(source or '').strip():
            raise PolicyError('Choose the backup folder to restore from.')
        if src.is_file():
            src = src.parent
        if not (src / INFO).exists():
            raise PolicyError('That folder is not a Kel backup (no backup description inside).')
        try:
            info = json.loads((src / INFO).read_text(encoding='utf-8'))
        except Exception:
            raise PolicyError('That backup description could not be read.') from None
        database = src / str(info.get('database') or self.db_name)
        if not database.exists():
            raise PolicyError('That backup is missing its database file.')
        return {
            'folder': str(src),
            'created': info.get('created'),
            'format': info.get('format'),
            'notes': info.get('notes') or '',
            'summary': _summary(database),
        }

    def stage_restore(self, source):
        details = self.inspect(source)
        src = Path(details['folder'])
        staging = self.root / STAGING
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir()
        for entry in src.iterdir():
            if entry.name in (INFO, MARKER):
                continue
            if entry.is_dir():
                shutil.copytree(entry, staging / entry.name, dirs_exist_ok=True)
            else:
                shutil.copy2(entry, staging / entry.name)
        (self.root / MARKER).write_text(
            json.dumps({'source': str(src), 'staged': time.time()}), encoding='utf-8')
        return {'restart_required': True, **details}


def _restore_entry(source, destination):
    """Write one staged entry back into the live data tree.

    Directories are merged (never deleted - the running app holds files inside them), databases go
    through SQLite so the copy works while another process has them open, and a failure raises: a
    half-applied restore must keep its pending marker instead of reporting success.
    """
    lowered = source.name.lower()
    if lowered.endswith(SKIP_SUFFIXES):
        return
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            if source.name == HOST_ENTRY and child.name not in HOST_KEEP:
                continue
            _restore_entry(child, destination / child.name)
        return
    if lowered.endswith(DB_SUFFIXES):
        _hot_copy_database(source, destination)
        return
    _copy_with_retries(source, destination)


def apply_pending_restore(store):
    """Called at engine start, before any connection touches the databases.

    Kel itself is already running at this point, so the app's live runtime state (Chromium's caches
    inside `host`, log files, locks) is never removed or overwritten: the previous version of what
    the restore replaces is kept as a best-effort safety net, directory entries are merged instead
    of deleted, and databases are written through SQLite.
    """
    root = Path(store.root)
    marker = root / MARKER
    staging = root / STAGING
    if not marker.exists() or not staging.exists():
        return False
    rollback = root.parent / (root.name + '.pre-restore-' + time.strftime('%Y%m%d-%H%M%S'))
    entries = [entry for entry in staging.iterdir() if entry.name not in (INFO, MARKER)]
    try:
        rollback.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            target = root / entry.name
            if not target.exists():
                continue
            try:
                if target.is_dir():
                    shutil.copytree(target, rollback / entry.name, dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns(*SKIP_SUFFIXES))
                else:
                    shutil.copy2(target, rollback / entry.name)
            except Exception:
                pass  # best-effort safety net; the restore itself still has to happen
        for entry in entries:
            _restore_entry(entry, root / entry.name)
        shutil.rmtree(staging, ignore_errors=True)
        marker.unlink(missing_ok=True)
        return True
    except Exception:
        return False
