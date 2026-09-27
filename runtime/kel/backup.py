"""Local backup and restore for everything Kel keeps (ST-01).

The installed app keeps one data tree beside App: ``Data\\{engine,store,host}``. A backup (format 2)
carries all three parts, each in its own folder inside the backup:

- ``engine`` — Kel's engine database (projects, work, memories, Knowledge, Recipes, transcripts,
  Vetting, connections' settings), transcript audio, attachments, Kibble (dogfood) screenshots and
  prompts, work evidence and project copies;
- ``store`` — the chat database the sidebar shows (``aionui-backend.db``, copied through SQLite's
  backup API so its live WAL is included) and the chat store's own files (conversation folders,
  built-in skills, extension state);
- ``host`` — only ``config`` (Kel's settings, skills and assistants).

Never included: credentials (JR-45) — the engine's credentials file, the transcription key,
provider API keys, sign-in tokens and the local account's password and secrets are left out or
blanked in the copied databases, and a restore keeps the live ones; the app's runtime state —
Chromium caches and storage under ``host`` (Cache, Code Cache, GPUCache, Dawn*…), logs, lock and
session files, downloaded runtimes (``store\\runtime``); and earlier backups/restore snapshots.
Anything that cannot be read while the app runs is listed in the backup description instead of
failing the whole copy (the two databases are the exception: without them there is no backup).

Restore validates the backup (its description and both databases open as SQLite), stages it, and
applies it on the next engine start, so a failed copy can never leave a half-restored database.
The previous data of each part is kept beside it as ``<part>.pre-restore-*``. Backups made before
format 2 (engine folder only) still inspect and restore exactly as before.
"""
import json
import os
import shutil
import sqlite3
import time
from pathlib import Path

from .core import PolicyError

MARKER = 'restore-pending.json'
STAGING = '.restore-staging'
INFO = 'BACKUP-INFO.json'
OUTCOME = 'restore-outcome.json'  # last restore attempt, recorded beside the data (PER-02)
SNAPSHOT_KEEP = 2  # pre-restore snapshots retained; older ones are pruned (PER-03)
FORMAT = 2
PARTS = ('engine', 'store', 'host')
CHATS_DB = 'aionui-backend.db'
SECRET_TABLE = 'transcription_settings'
SECRET_KEYS = ('meta_api_key',)
# The chat store's credential columns (JR-45). Blanked in the backup copy; a restore puts the live
# values back so the running app keeps its sign-in and keys. NULL where the column allows it.
STORE_SECRET_COLUMNS = {
    'users': (('password_hash', ''), ('jwt_secret', None), ('encryption_secret', None)),
    'providers': (('api_key_encrypted', ''),),
    'remote_agents': (('auth_token', None), ('device_private_key', None), ('device_token', None)),
}
STORE_SECRET_TABLES = ('oauth_tokens',)  # rows that are nothing but credentials
SKIP_ENTRIES = (STAGING, MARKER, OUTCOME)
# Credential custody lives in the OS keychain/app-data, but `KEL_DATA_DIR` can place the encrypted
# credentials file inside the data root; a backup must never capture it (audit PER-04).
NEVER_BACKUP = ('kel-credentials.json',)
# Runtime state the app keeps open while it runs, lock/scratch folders and earlier safety copies:
# never part of a backup.
VOLATILE_ENTRIES = ('logs', 'desktop.log', 'desktop-link.log', 'desktop-session.json',
                    'controller.lock', 'broker-locks', 'transport-locks', 'broker-logs',
                    'native-logs', 'sessions', 'backups')
STORE_VOLATILE = ('runtime',)  # downloaded runtimes the app provisions again by itself
# Everything under `host` is Chromium's user-data tree - caches, storage and locks the running
# app holds open - except Kel's own settings/skills/assistants in `config` (and the desktop
# database under `aionui` in the layout before the chat store moved to `store`).
HOST_ENTRY = 'host'
HOST_KEEP = ('config', 'aionui')
# Live SQLite sidecar files and process locks are never copied.
SKIP_SUFFIXES = ('-wal', '-shm', '-journal', '.wal', '.shm', '.journal', '.lock', '.log')
DB_SUFFIXES = ('.sqlite3', '.db', '.sqlite')

INCLUDES = ('Includes your chats, projects, work, memories, transcripts and their audio, '
            'attachments, Kibble screenshots, skills and settings.')
EXCLUDES = ('Not included: saved credentials - model provider keys, the transcription key, '
            'connection credentials and sign-in tokens - and the app\'s caches and logs. '
            'Add the credentials again after a restore.')


def data_layout(store):
    """{part: folder or None} for this engine's data tree.

    The installed layout is ``Data\\engine`` with ``store`` and ``host`` beside it; the shell also
    names them through AIONUI_DATA_DIR / KEL_HOST_DATA_DIR. A development engine without them backs
    up its engine folder only.
    """
    engine = Path(store.root)
    parent = engine.parent
    canonical = engine.name.lower() == 'engine'
    out = {'engine': engine, 'store': None, 'host': None}
    for part, env in (('store', 'AIONUI_DATA_DIR'), ('host', 'KEL_HOST_DATA_DIR')):
        candidate = parent / part if canonical and (parent / part).is_dir() else None
        if candidate is None and canonical and os.environ.get(env):
            named = Path(os.environ[env])
            try:
                if named.is_dir() and named.resolve() != engine.resolve() \
                        and not named.resolve().is_relative_to(engine.resolve()):
                    candidate = named
            except OSError:
                candidate = None
        out[part] = candidate
    return out


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


def _columns(con, table):
    return {row[1] for row in con.execute('PRAGMA table_info("%s")' % table)}


def _strip_store_secrets(db_path):
    """Blank the chat store's credential columns in the backup copy (JR-45)."""
    con = sqlite3.connect(str(db_path))
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, columns in STORE_SECRET_COLUMNS.items():
            if table not in tables:
                continue
            present = _columns(con, table)
            for column, blank in columns:
                if column in present:
                    con.execute('UPDATE "%s" SET "%s"=?' % (table, column), (blank,))
        for table in STORE_SECRET_TABLES:
            if table in tables:
                con.execute('DELETE FROM "%s"' % table)
        con.commit()
    finally:
        con.close()


def _capture_store_secrets(db_path):
    """The live credential values, keyed by row id, read before a restore replaces the database."""
    captured = {'columns': {}, 'rows': {}}
    if not Path(db_path).exists():
        return captured
    con = sqlite3.connect(str(db_path), timeout=10)
    try:
        con.row_factory = sqlite3.Row
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, columns in STORE_SECRET_COLUMNS.items():
            if table not in tables or 'id' not in _columns(con, table):
                continue
            names = [c for c, _ in columns if c in _columns(con, table)]
            if not names:
                continue
            captured['columns'][table] = [dict(row) for row in con.execute(
                'SELECT id, %s FROM "%s"' % (', '.join('"%s"' % n for n in names), table))]
        for table in STORE_SECRET_TABLES:
            if table in tables:
                captured['rows'][table] = [dict(row) for row in con.execute('SELECT * FROM "%s"' % table)]
    finally:
        con.close()
    return captured


def _reapply_store_secrets(db_path, captured):
    """Put the live credentials back into the restored chat database (custody never changes)."""
    if not captured['columns'] and not captured['rows']:
        return
    con = sqlite3.connect(str(db_path), timeout=10)
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, rows in captured['columns'].items():
            if table not in tables:
                continue
            present = _columns(con, table)
            for row in rows:
                names = [k for k in row if k != 'id' and k in present]
                if names:
                    con.execute('UPDATE "%s" SET %s WHERE id=?' % (table, ', '.join('"%s"=?' % n for n in names)),
                                (*[row[n] for n in names], row['id']))
        for table, rows in captured['rows'].items():
            if table not in tables:
                continue
            present = _columns(con, table)
            for row in rows:
                names = [k for k in row if k in present]
                con.execute('INSERT OR REPLACE INTO "%s"(%s) VALUES(%s)' % (
                    table, ', '.join('"%s"' % n for n in names), ', '.join('?' * len(names))),
                    [row[n] for n in names])
        con.commit()
    finally:
        con.close()


def _count(con, sql):
    try:
        return con.execute(sql).fetchone()[0]
    except Exception:
        return None


def _summary(db_path, chats_db=None):
    """What a person would recognise: chats (the sidebar's), projects, work, transcripts, …"""
    out = {}
    try:
        con = sqlite3.connect(str(db_path))
        if not chats_db:
            # A backup from before the chat store was included: its engine records are all it has.
            out['conversations'] = _count(con, 'SELECT COUNT(*) FROM conversations')
            out['messages'] = _count(con, 'SELECT COUNT(*) FROM messages')
        out['transcripts'] = _count(con, 'SELECT COUNT(*) FROM transcripts')
        out['vetting_sessions'] = _count(con, 'SELECT COUNT(*) FROM vetting_sessions')
        # V2-17: the V2 surfaces a person would miss most, visible in the backup description too.
        out['connections'] = _count(con, 'SELECT COUNT(*) FROM connections')
        out['memories'] = _count(con, 'SELECT COUNT(*) FROM memories')
        out['projects'] = _count(con, 'SELECT COUNT(*) FROM projects')
        out['jobs'] = _count(con, 'SELECT COUNT(*) FROM jobs')
        con.close()
    except Exception:
        pass
    if chats_db:
        out.update(_chat_summary(chats_db))
    return {key: value for key, value in out.items() if value is not None}


def _chat_summary(chats_db):
    """The sidebar's chats and their messages, from the chat store (ST-01)."""
    out = {}
    try:
        con = sqlite3.connect(str(chats_db))
        try:
            archived = 'archived_at' in _columns(con, 'conversations')
            out['conversations'] = _count(con, 'SELECT COUNT(*) FROM conversations' +
                                          (' WHERE archived_at IS NULL' if archived else ''))
            out['messages'] = _count(con, 'SELECT COUNT(*) FROM messages')
        finally:
            con.close()
    except Exception:
        pass
    return {key: value for key, value in out.items() if value is not None}


def table_inventory(db_path):
    """Every real table with its row count, plus the migration ledger (V2-17).

    The manual-upgrade before/after: a developer can compare this against the same call on a
    restored copy or on a fresh upgrade and see that no table lost rows. Read-only.
    """
    out = {'tables': {}, 'migrations': []}
    try:
        con = sqlite3.connect(str(db_path))
        try:
            names = [row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                if not row[0].startswith('sqlite_')]
            for name in names:
                try:
                    out['tables'][name] = con.execute(
                        'SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
                except Exception:
                    out['tables'][name] = None
            try:
                out['migrations'] = [
                    {'version': row[0], 'name': row[1]} for row in
                    con.execute('SELECT version, name FROM schema_migrations ORDER BY version')]
            except Exception:
                out['migrations'] = []
        finally:
            con.close()
    except Exception:
        raise PolicyError('Kel could not read the database inventory.') from None
    return out


def _hot_copy_database(source, destination):
    """SQLite-safe copy of a live database (works while another process holds it open)."""
    src = sqlite3.connect(str(source), timeout=10)
    dst = sqlite3.connect(str(destination), timeout=10)
    try:
        src.execute('PRAGMA busy_timeout=8000')
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()


def _valid_database(path):
    try:
        from urllib.parse import quote
        con = sqlite3.connect('file:%s?mode=ro' % quote(Path(path).as_posix(), safe='/:'), uri=True)
        try:
            con.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
            return con.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        finally:
            con.close()
    except Exception:
        return False


def _copy_with_retries(source, destination):
    for attempt in range(4):
        try:
            shutil.copy2(source, destination)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(0.15 * (attempt + 1))


def _copy_entry(source, destination, skipped, exclude=()):
    """Copy one entry of the data tree.

    Runtime files the running app holds open (sidecars, locks, logs) are skipped by name, databases
    are copied through SQLite so a live handle in another process cannot block the backup, and
    anything else that cannot be read is recorded in ``skipped`` instead of failing the whole copy.
    """
    lowered = source.name.lower()
    if lowered.endswith(SKIP_SUFFIXES) or source.name in NEVER_BACKUP:
        if source.name in NEVER_BACKUP:
            skipped.append(source.name)
        return
    if any(_same(source, other) for other in exclude):
        return  # never copy a backup into itself
    if source.is_dir():
        if source.name == 'logs':
            return
        destination.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            _copy_entry(child, destination / child.name, skipped, exclude)
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


def _same(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


class Backup:
    def __init__(self, store):
        self.store = store

    @property
    def root(self):
        return Path(self.store.root)

    @property
    def db_name(self):
        return Path(self.store.db_path).name

    def layout(self):
        return data_layout(self.store)

    # ---- create ----------------------------------------------------------------------------------
    def create(self, target):
        destination_root = Path(str(target or '')).expanduser()
        if not str(target or '').strip() or not destination_root.is_dir():
            raise PolicyError('Choose an existing folder for the backup.')
        folder = destination_root / ('Kel-Backup-' + time.strftime('%Y%m%d-%H%M%S'))
        folder.mkdir()
        skipped = []
        layout = self.layout()
        parts = []
        try:
            self._copy_engine(folder / 'engine', skipped, folder)
            parts.append('engine')
            if layout['store'] is not None:
                self._copy_store(layout['store'], folder / 'store', skipped, folder)
                parts.append('store')
            if layout['host'] is not None:
                self._copy_host(layout['host'], folder / 'host', skipped, folder)
                parts.append('host')
        except PolicyError:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise PolicyError('Kel could not finish the backup. Close any other Kel window '
                              'and try again.') from None
        copied_db = folder / 'engine' / self.db_name
        if copied_db.exists():
            _strip_secrets(copied_db)
        chats = folder / 'store' / CHATS_DB
        if chats.exists():
            _strip_store_secrets(chats)
        notes = ('Credentials are excluded from backups: provider keys, the transcription key, '
                 'connection credentials and sign-in tokens. Reconnect them after restoring.')
        if skipped:
            notes += (' Some runtime files were in use and are not in this backup: '
                      + ', '.join(sorted(set(skipped))) + '.')
        info = {
            'format': FORMAT,
            'app': 'Kel',
            'created': time.time(),
            'database': 'engine/' + self.db_name,
            'chats_database': 'store/' + CHATS_DB if chats.exists() else None,
            'parts': parts,
            'notes': notes,
            'includes': INCLUDES,
            'excludes': EXCLUDES,
            'skipped': sorted(set(skipped)),
            'summary': _summary(copied_db, chats if chats.exists() else None) if copied_db.exists() else {},
        }
        (folder / INFO).write_text(json.dumps(info, indent=2), encoding='utf-8')
        return {'folder': str(folder), 'summary': info['summary'], 'notes': notes,
                'skipped': info['skipped'], 'parts': parts, 'includes': INCLUDES,
                'excludes': EXCLUDES}

    def _copy_engine(self, destination, skipped, folder):
        destination.mkdir()
        for entry in self.root.iterdir():
            if entry.name in SKIP_ENTRIES or entry.name in VOLATILE_ENTRIES:
                continue
            if entry.name.startswith('.pre-restore') or entry.name.endswith('.log'):
                continue
            if entry.name in NEVER_BACKUP:
                skipped.append(entry.name)  # credentials never travel in a backup (PER-04)
                continue
            if entry.name.lower().endswith(('-wal', '-shm', '-journal', '.wal', '.shm', '.journal')):
                # Live SQLite sidecar files are never copied; the hot copy carries their contents.
                continue
            if _same(entry, self.store.db_path):
                try:
                    _hot_copy_database(entry, destination / entry.name)
                except Exception:
                    raise PolicyError('Kel could not read its database for the backup. '
                                      'Close any other Kel window and try again.') from None
            elif entry.is_dir() and entry.name == HOST_ENTRY:
                # The layout before the chat store moved out: only Kel's own parts of `host`.
                for child in entry.iterdir():
                    if child.name in HOST_KEEP:
                        _copy_entry(child, destination / entry.name / child.name, skipped, (folder,))
            else:
                _copy_entry(entry, destination / entry.name, skipped, (folder,))

    def _copy_store(self, source, destination, skipped, folder):
        destination.mkdir()
        for entry in source.iterdir():
            if entry.name in STORE_VOLATILE or entry.name in VOLATILE_ENTRIES:
                continue
            if entry.name == CHATS_DB:
                try:
                    _hot_copy_database(entry, destination / entry.name)
                except Exception:
                    raise PolicyError('Kel could not read your chats for the backup. '
                                      'Close any other Kel window and try again.') from None
                continue
            _copy_entry(entry, destination / entry.name, skipped, (folder,))

    def _copy_host(self, source, destination, skipped, folder):
        destination.mkdir()
        for entry in source.iterdir():
            if entry.name == 'config':
                _copy_entry(entry, destination / entry.name, skipped, (folder,))

    # ---- inspect / restore -----------------------------------------------------------------------
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
        fmt = int(info.get('format') or 1)
        if fmt >= 2:
            database = src / str(info.get('database') or ('engine/' + self.db_name))
            chats = src / str(info['chats_database']) if info.get('chats_database') else None
        else:
            database = src / str(info.get('database') or self.db_name)
            chats = None
        if not database.exists():
            raise PolicyError('That backup is missing its database file.')
        if not _valid_database(database):
            raise PolicyError('That backup\'s database is damaged, so Kel will not restore it.')
        if chats is not None:
            if not chats.exists():
                raise PolicyError('That backup is missing its chats database.')
            if not _valid_database(chats):
                raise PolicyError('That backup\'s chats database is damaged, so Kel will not restore it.')
        parts = [p for p in (info.get('parts') or ['engine']) if p in PARTS] if fmt >= 2 else ['engine']
        return {
            'folder': str(src),
            'created': info.get('created'),
            'format': fmt,
            'parts': parts,
            'notes': info.get('notes') or '',
            'includes': INCLUDES if fmt >= 2 else 'Includes Kel\'s engine data (made by an earlier Kel).',
            'excludes': EXCLUDES,
            'restores': self._restore_description(parts),
            'summary': _summary(database, chats),
        }

    def _restore_description(self, parts):
        words = {'engine': 'projects, work, memories, transcripts, attachments and Kibble',
                 'store': 'your chats', 'host': 'settings, skills and assistants'}
        named = [words[p] for p in PARTS if p in parts]
        return ('Restoring replaces %s with the backup\'s copy. Your current data is kept beside the '
                'data folder first, saved credentials stay as they are, and Kel finishes the restore '
                'the next time it starts.' % ', '.join(named))

    def inventory(self):
        """The engine's table inventory plus a summary in the backup's words (chats from the store)."""
        out = table_inventory(self.store.db_path)
        chats = self.layout()['store']
        chats_db = chats / CHATS_DB if chats is not None and (chats / CHATS_DB).exists() else None
        out['summary'] = _summary(self.store.db_path, chats_db)
        return out

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
            json.dumps({'source': str(src), 'staged': time.time(), 'format': details['format'],
                        'parts': details['parts']}), encoding='utf-8')
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


def _snapshot_entry(source, destination):
    """Best-effort copy of the live data a restore replaces (databases through SQLite)."""
    lowered = source.name.lower()
    if lowered.endswith(SKIP_SUFFIXES):
        return
    try:
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            for child in source.iterdir():
                _snapshot_entry(child, destination / child.name)
        elif lowered.endswith(DB_SUFFIXES):
            _hot_copy_database(source, destination)
        else:
            shutil.copy2(source, destination)
    except Exception:
        pass  # a safety net only; the restore itself still has to happen


def _record_outcome(root, ok, detail=''):
    """Durable, database-independent record of the last restore attempt (audit PER-02).

    A restore is what replaces the database, so its outcome cannot live inside it: the record is a
    sidecar next to the data. `Service` reads it and surfaces a failure in `state()` instead of
    discarding it. Recording never raises — a failed restore must still return its verdict.
    """
    try:
        (Path(root) / OUTCOME).write_text(
            json.dumps({'ok': bool(ok), 'detail': str(detail)[:200], 'at': time.time()}),
            encoding='utf-8')
    except Exception:
        pass


def _prune_snapshots(root, keep=SNAPSHOT_KEEP):
    """Keep only the newest `keep` pre-restore snapshots (audit PER-03).

    Every applied *or attempted* restore leaves `root.name + '.pre-restore-<stamp>'` beside the
    data, and nothing ever removed them. Only directories matching that exact prefix are touched,
    the newest `keep` always survive (including the one this attempt just wrote), and pruning is
    best-effort so it can never fail a restore.
    """
    prefix = root.name + '.pre-restore-'
    try:
        snapshots = sorted((entry for entry in root.parent.iterdir()
                            if entry.is_dir() and entry.name.startswith(prefix)),
                           key=lambda entry: entry.name, reverse=True)
        for stale in snapshots[keep:]:
            shutil.rmtree(stale, ignore_errors=True)
    except Exception:
        pass


def _read_marker(marker):
    try:
        data = json.loads(marker.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def apply_pending_restore(store):
    """Called at engine start, before any connection touches the databases.

    Kel itself is already running at this point, so the app's live runtime state (Chromium's caches
    inside `host`, log files, locks) is never removed or overwritten: the previous version of what
    the restore replaces is kept as a best-effort safety net, directory entries are merged instead
    of deleted, and databases are written through SQLite. A format-2 backup restores each part
    (engine, store, host) into its live folder; the chat store's live credentials are kept.
    """
    root = Path(store.root)
    marker = root / MARKER
    staging = root / STAGING
    if not marker.exists() or not staging.exists():
        return False
    stamp = time.strftime('%Y%m%d-%H%M%S')
    plan = []  # (staged folder, live folder)
    if int(_read_marker(marker).get('format') or 1) >= 2:
        layout = data_layout(store)
        for part in PARTS:
            if (staging / part).is_dir() and layout.get(part) is not None:
                plan.append((staging / part, Path(layout[part])))
    else:
        plan.append((staging, root))
    touched = []
    try:
        for staged, live in plan:
            rollback = live.parent / (live.name + '.pre-restore-' + stamp)
            rollback.mkdir(parents=True, exist_ok=True)
            touched.append(live)
            for entry in staged.iterdir():
                if entry.name in (INFO, MARKER):
                    continue
                target = live / entry.name
                if target.exists():
                    _snapshot_entry(target, rollback / entry.name)
        for staged, live in plan:
            captured = None
            if (staged / CHATS_DB).exists():
                captured = _capture_store_secrets(live / CHATS_DB)
            for entry in staged.iterdir():
                if entry.name in (INFO, MARKER):
                    continue
                _restore_entry(entry, live / entry.name)
            if captured is not None:
                _reapply_store_secrets(live / CHATS_DB, captured)
        shutil.rmtree(staging, ignore_errors=True)
        marker.unlink(missing_ok=True)
        for live in touched or [root]:
            _prune_snapshots(live)
        _record_outcome(root, True)
        return True
    except Exception as exc:
        # Audit PER-02: a failed or partial restore used to vanish into `False` while the marker
        # stayed behind. The outcome is now recorded (and surfaced by the service) while the
        # marker keeps its meaning: the restore is still pending.
        for live in touched or [root]:
            _prune_snapshots(live)
        _record_outcome(root, False, type(exc).__name__)
        return False
