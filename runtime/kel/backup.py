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

Never included, on purpose: credentials (JR-45) — the engine's credentials file, the transcription
key, provider API keys, sign-in tokens and the local account's password and secrets are left out or
blanked in the copied databases, and a restore keeps the live ones; the app's runtime state —
Chromium caches and storage under ``host`` (Cache, Code Cache, GPUCache, Dawn*…), logs, lock and
session files, downloaded runtimes (``store\\runtime``); and earlier backups/restore snapshots.
Anything that cannot be read while the app runs is listed in the backup description instead of
failing the whole copy (the two databases are the exception: without them there is no backup).

Restore validates the backup (its description and both databases open as SQLite) and stages it.
The desktop applies it on the next start, before anything opens the data, all or nothing: every
entry is swapped by renames recorded in a journal, and any failure undoes the swaps already made
(FN-02). The previous data is kept in one ``Kel data before restore <date>`` folder beside the data.
Backups made before format 2 (engine folder only) still inspect and restore.
"""
import json
import os
import shutil
import sqlite3
import stat
import sys
import time
import uuid
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
SKIP_ENTRIES = (STAGING, MARKER, OUTCOME, 'restore-journal.json')
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
EXCLUDES = ('Not included, on purpose: saved keys and sign-ins - model provider keys, the '
            'transcription key, connection credentials and sign-in tokens - and the app\'s caches '
            'and logs. A restore on this PC keeps the keys and sign-ins you have now; on a different '
            'PC, add them again there.')


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
        out['projects'] = _project_count(con)
        out['jobs'] = _count(con, 'SELECT COUNT(*) FROM jobs')
        con.close()
    except Exception:
        pass
    if chats_db:
        out.update(_chat_summary(chats_db))
    return {key: value for key, value in out.items() if value is not None}


def _project_count(con):
    """The projects a person sees under All projects: not archived, not Kel's plumbing (FN-15)."""
    visible = _count(con, "SELECT COUNT(*) FROM projects p LEFT JOIN project_meta m ON m.project_id=p.id "
                          "WHERE COALESCE(m.kind,'user')!='system' AND m.archived IS NULL")
    return visible if visible is not None else _count(con, 'SELECT COUNT(*) FROM projects')


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
        return  # credentials are left out on purpose (FN-15), never reported as "in use"
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


def _rmtree(path):
    """Remove a folder completely, read-only files included (a repository's .git objects are)."""
    def writable(func, target, _info):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except Exception:
            pass
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=writable)
        else:
            shutil.rmtree(path, onerror=writable)
    except Exception:
        pass


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
        stamp = 'Kel-Backup-' + time.strftime('%Y%m%d-%H%M%S')
        folder, suffix = destination_root / stamp, 2
        while folder.exists():  # two backups in the same second each get their own folder
            folder, suffix = destination_root / ('%s-%d' % (stamp, suffix)), suffix + 1
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
            _rmtree(folder)
            raise
        except Exception:
            _rmtree(folder)
            raise PolicyError('Kel could not finish the backup. Close any other Kel window '
                              'and try again.') from None
        copied_db = folder / 'engine' / self.db_name
        if copied_db.exists():
            _strip_secrets(copied_db)
        chats = folder / 'store' / CHATS_DB
        if chats.exists():
            _strip_store_secrets(chats)
        notes = ('Credentials are excluded on purpose: provider keys, the transcription key, '
                 'connection credentials and sign-in tokens stay on this PC and are never copied. '
                 'Restoring on this PC keeps them; on a different PC, add them again there.')
        if skipped:
            notes += (' Some files were in use and are not in this backup: '
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
            'left_out': list(NEVER_BACKUP),
            'summary': _summary(copied_db, chats if chats.exists() else None) if copied_db.exists() else {},
        }
        (folder / INFO).write_text(json.dumps(info, indent=2), encoding='utf-8')
        return {'folder': str(folder), 'summary': info['summary'], 'notes': notes,
                'skipped': info['skipped'], 'left_out': info['left_out'], 'parts': parts, 'includes': INCLUDES,
                'excludes': EXCLUDES}

    def _copy_engine(self, destination, skipped, folder):
        destination.mkdir()
        for entry in self.root.iterdir():
            if entry.name in SKIP_ENTRIES or entry.name in VOLATILE_ENTRIES:
                continue
            if entry.name.startswith('.pre-restore') or entry.name.endswith('.log'):
                continue
            if entry.name in NEVER_BACKUP:
                continue  # credentials never travel in a backup (PER-04), on purpose (FN-15)
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
        return ('Restoring replaces %s with the backup\'s copy. Kel finishes the restore the next time it '
                'starts, before it opens your data; if any part cannot be replaced, Kel puts everything '
                'back as it was. Your current data is kept beside the data folder, and the keys and '
                'sign-ins saved on this PC stay as they are.' % ', '.join(named))

    def inventory(self):
        """The engine's table inventory plus a summary in the backup's words (chats from the store)."""
        out = table_inventory(self.store.db_path)
        chats = self.layout()['store']
        chats_db = chats / CHATS_DB if chats is not None and (chats / CHATS_DB).exists() else None
        out['summary'] = _summary(self.store.db_path, chats_db)
        return out

    def stage_restore(self, source):
        if (self.root / JOURNAL).exists():
            raise PolicyError('Kel is still putting back data from an earlier restore. Quit Kel and reopen '
                              'it first, then choose Restore again.')
        details = self.inspect(source)
        src = Path(details['folder'])
        staging = self.root / STAGING
        if staging.exists():
            _rmtree(staging)
            if staging.exists():
                raise PolicyError('Kel could not clear an earlier restore copy. Quit Kel and reopen it, then '
                                  'choose Restore again.')
        staging.mkdir()
        for entry in src.iterdir():
            if entry.name in (INFO, MARKER):
                continue
            if entry.is_dir():
                shutil.copytree(entry, staging / entry.name, dirs_exist_ok=True)
            else:
                shutil.copy2(entry, staging / entry.name)
        (self.root / MARKER).write_text(
            json.dumps({'id': uuid.uuid4().hex, 'source': str(src), 'staged': time.time(),
                        'format': details['format'], 'parts': details['parts'],
                        'created': details.get('created')}), encoding='utf-8')
        return {'restart_required': True, **details}


def _record_outcome(root, ok, detail='', **fields):
    """Durable, database-independent record of the last restore attempt (audit PER-02, FN-02).

    A restore is what replaces the database, so its outcome cannot live inside it: the record is a
    sidecar next to the data, read by `Service.state()` and by Settings → System. `detail` is the
    plain-words message (JR-8); `technical` keeps the raw reason for Details. `notice` is true until
    the one-time notice has been shown. Called with only an exception name (the engine's own guard
    when a restore cannot even start), it still says what happened in plain words. Recording never
    raises — a failed restore must still return its verdict.
    """
    record = {'version': 2, 'ok': bool(ok), 'at': time.time(), 'notice': True}
    if 'title' not in fields:
        # The engine's guard: only an exception name is known, and nothing was replaced.
        fields = {'title': 'Your backup was restored' if ok else 'Kel could not restore your backup',
                  'status': 'restored' if ok else 'not_started', 'technical': str(detail)[:200],
                  **fields}
        detail = '' if ok else ('Kel could not start the restore, so nothing was replaced — your data '
                                'is unchanged. ' + NEXT_STEP['other'])
    record.update(fields)
    record['detail'] = str(detail)
    record['technical'] = str(record.get('technical') or '')[:400]
    try:
        (Path(root) / OUTCOME).write_text(json.dumps(record), encoding='utf-8')
    except Exception:
        pass
    return record


def read_outcome(root):
    """The last restore attempt in plain words, or None when no restore was ever attempted.

    Records written before FN-02 held only an exception name; they are translated here so nobody is
    ever shown "PermissionError" on its own.
    """
    try:
        data = json.loads((Path(root) / OUTCOME).read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    ok = bool(data.get('ok'))
    if int(data.get('version') or 1) < 2:
        raw = str(data.get('detail') or '')
        data = {'ok': ok, 'at': data.get('at'), 'status': 'restored' if ok else 'unknown',
                'title': 'Your backup was restored' if ok else 'An earlier restore did not finish',
                'detail': '' if ok else ('An earlier version of Kel could not finish a restore. '
                                         'If your data looks wrong, choose Restore again in '
                                         'Settings → System.'),
                'technical': raw, 'notice': False}
    keys = ('ok', 'at', 'status', 'title', 'detail', 'part', 'kept', 'technical', 'notice',
            'dismissed', 'backup_created')
    out = {key: data.get(key) for key in keys if key in data}
    out['ok'] = ok
    out['detail'] = str(out.get('detail') or '')
    out['notice'] = bool(out.get('notice'))
    out['dismissed'] = bool(out.get('dismissed'))
    return out


def mark_outcome(root, **changes):
    """Mark the record seen (`notice=False`) or dismissed in Settings (`dismissed=True`)."""
    path = Path(root) / OUTCOME
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    allowed = {key: bool(value) for key, value in changes.items() if key in ('notice', 'dismissed')}
    data.update(allowed)
    try:
        path.write_text(json.dumps(data), encoding='utf-8')
    except Exception:
        pass
    return read_outcome(root)


def _prune_snapshots(root, keep=SNAPSHOT_KEEP):
    """Keep only the newest `keep` legacy pre-restore snapshots (audit PER-03).

    Kel before FN-02 left `root.name + '.pre-restore-<stamp>'` beside the data on every attempt, and
    a failed restore re-ran on every start, piling them up. Only directories matching that exact
    prefix are touched, the newest `keep` always survive, and pruning never fails a restore.
    """
    prefix = root.name + '.pre-restore-'
    try:
        snapshots = sorted((entry for entry in root.parent.iterdir()
                            if entry.is_dir() and entry.name.startswith(prefix)),
                           key=lambda entry: entry.name, reverse=True)
        for stale in snapshots[keep:]:
            _rmtree(stale)
    except Exception:
        pass


def _prune_before_folders(parent, keep=SNAPSHOT_KEEP):
    """One "Kel data before restore <date>" folder per applied restore; the newest `keep` stay."""
    try:
        folders = sorted((entry for entry in Path(parent).iterdir()
                          if entry.is_dir() and entry.name.startswith(BEFORE_PREFIX)),
                         key=lambda entry: entry.name, reverse=True)
        for stale in folders[keep:]:
            _rmtree(stale)
    except Exception:
        pass


def _read_marker(marker):
    try:
        data = json.loads(marker.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ---- applying a staged restore (FN-02) ------------------------------------------------------------
#
# A staged restore is applied at a safe moment — the desktop's main process runs it before the chat
# store, the engine or any window opens the data (`python -m kel.backup --apply-restore`, or the
# packed engine's `--apply-restore`) — and it is all or nothing:
#
# 1. the engine's instance lock is taken, so no engine can open the data while the swap runs (an
#    engine still running from before means nothing is touched at all);
# 2. the live credentials are copied into the *staged* databases, so custody never changes;
# 3. every entry the backup carries is swapped by renames: the live entry (and its SQLite sidecars)
#    moves into one "Kel data before restore <date>" folder, the staged entry moves into place.
#    Each move is written to a journal on disk before it happens;
# 4. if any move fails, every move already made is undone in reverse order, so the data is exactly
#    as it was. A restore interrupted by a crash is undone the same way on the next start.
#
# A staged restore is attempted exactly once: success, failure and rollback all clear the pending
# marker and leave a plain-words outcome. Nothing ever re-applies a restore on a later start.

BEFORE_PREFIX = 'Kel data before restore '
JOURNAL = 'restore-journal.json'
OWNER_ENV = 'KEL_RESTORE_OWNER'  # 'shell': the desktop applies restores; the engine never does
PART_WORDS = {'engine': 'your projects, work, memories and transcripts',
              'store': 'your chats', 'host': 'your settings, skills and assistants'}
REASON_WORDS = {
    'in_use': 'another program still had some of those files open',
    'no_space': 'the disk is full',
    'missing': 'part of the copy Kel prepared for the restore was missing',
    'other': 'of an unexpected error',
}
NEXT_STEP = {
    'in_use': 'To try again, quit Kel completely, reopen it, and choose Restore in Settings → System.',
    'no_space': 'Free up some disk space, then choose Restore again in Settings → System.',
    'missing': 'Choose Restore again in Settings → System to prepare a fresh copy.',
    'other': 'Choose Restore again in Settings → System. If it fails again, the details help Kel\'s '
             'team.',
}
_RENAME_ATTEMPTS = 8
_RENAME_PAUSE = 0.25


def _rename(source, destination):
    """One atomic move on the same volume, retried briefly (virus scanners hold files for a moment)."""
    for attempt in range(_RENAME_ATTEMPTS):
        try:
            os.rename(source, destination)
            return
        except PermissionError:
            if attempt == _RENAME_ATTEMPTS - 1:
                raise
            time.sleep(_RENAME_PAUSE)


def _reason(exc):
    if isinstance(exc, FileNotFoundError):
        return 'missing'
    if isinstance(exc, PermissionError) or getattr(exc, 'winerror', None) in (5, 32, 33):
        return 'in_use'
    if getattr(exc, 'errno', None) == 28 or getattr(exc, 'winerror', None) in (39, 112):
        return 'no_space'
    return 'other'


def _technical(exc):
    text = type(exc).__name__
    code = getattr(exc, 'winerror', None) or getattr(exc, 'errno', None)
    return '%s%s' % (text, ' (%s)' % code if code else '')


def _when(created):
    try:
        stamp = float(created)
    except (TypeError, ValueError):
        return ''
    if stamp > 1e12:
        stamp /= 1000
    moment = time.localtime(stamp)
    return ' from %s %d, %d' % (time.strftime('%b', moment), moment.tm_mday, moment.tm_year)


def _words(parts):
    named = [PART_WORDS[p] for p in PARTS if p in parts]
    if len(named) <= 1:
        return ''.join(named) or 'your data'
    return ', '.join(named[:-1]) + ' and ' + named[-1]


def _read_journal(root):
    try:
        data = json.loads((Path(root) / JOURNAL).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_journal(root, journal):
    path = Path(root) / JOURNAL
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(journal), encoding='utf-8')
    os.replace(temporary, path)


def _undo(journal):
    """Reverse the recorded moves strictly newest first, stopping at the first that cannot be undone.

    Returns the moves still to undo, oldest first (empty when everything is back). Stopping keeps the
    data consistent — a database is never put back without its sidecar files, or the other way round —
    and the remaining moves stay in the journal for the next start.
    """
    moves = [list(pair) for pair in journal.get('moves') or []]
    for index in range(len(moves) - 1, -1, -1):
        source, destination = Path(moves[index][0]), Path(moves[index][1])
        if not (destination.exists() or destination.is_symlink()):
            continue  # only intended (recorded, never made), or already undone: nothing to do
        if source.exists():
            return moves[:index + 1]
        try:
            source.parent.mkdir(parents=True, exist_ok=True)
            _rename(destination, source)
        except Exception:
            return moves[:index + 1]
    return []


def _remove_if_empty(folder):
    """Remove a before-restore folder that holds nothing (only empty sub-folders)."""
    folder = Path(folder)
    if not folder.is_dir():
        return
    for path in sorted(folder.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if path.is_file() or path.is_symlink():
            return
    _rmtree(folder)


def _clear_pending(root, staging=True):
    root = Path(root)
    (root / MARKER).unlink(missing_ok=True)
    if staging:
        _rmtree(root / STAGING)


def _units(part, staged, live):
    """(staged entry, live entry) pairs the restore swaps for one part of the data tree."""
    out = []
    for entry in sorted(staged.iterdir(), key=lambda e: e.name):
        name = entry.name
        if name in (INFO, MARKER, OUTCOME, STAGING, JOURNAL) or name in NEVER_BACKUP \
                or name in VOLATILE_ENTRIES or name.lower().endswith(SKIP_SUFFIXES):
            continue
        if part == 'store' and name in STORE_VOLATILE:
            continue
        if part == 'host' and name not in HOST_KEEP:
            continue
        if part == 'engine' and name == HOST_ENTRY and entry.is_dir():
            # The layout before the chat store moved out: only Kel's own parts of `host`.
            for child in sorted(entry.iterdir(), key=lambda e: e.name):
                if child.name in HOST_KEEP:
                    out.append((child, live / HOST_ENTRY / child.name))
            continue
        out.append((entry, live / name))
    return out


def _carry_engine_secrets(live_db, staged_db):
    """The transcription key lives in the engine database: keep the live one (never in backups)."""
    if not Path(live_db).exists() or not Path(staged_db).exists():
        return
    live = sqlite3.connect(str(live_db), timeout=10)
    try:
        tables = {row[0] for row in live.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        rows = [] if SECRET_TABLE not in tables else live.execute(
            'SELECT name, value FROM %s WHERE name IN (%s)' % (SECRET_TABLE, ','.join('?' * len(SECRET_KEYS))),
            SECRET_KEYS).fetchall()
    finally:
        live.close()
    if not rows:
        return
    staged = sqlite3.connect(str(staged_db), timeout=10)
    try:
        tables = {row[0] for row in staged.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if SECRET_TABLE in tables:
            staged.executemany('INSERT OR REPLACE INTO %s(name, value) VALUES(?, ?)' % SECRET_TABLE, rows)
            staged.commit()
    finally:
        staged.close()


def _outcome_for_failure(root, part, exc, kept, stuck, created, touched_any):
    reason = _reason(exc)
    what = PART_WORDS.get(part, 'your data')
    if stuck:
        return _record_outcome(
            root, False,
            'Kel could not replace %s because %s, and could not put everything back yet. Nothing was '
            'deleted: your data from before the restore is in the folder "%s" beside your data folder. '
            'Kel will finish putting it back the next time it starts. Keep that folder until this '
            'message is gone.' % (what, REASON_WORDS[reason], Path(kept).name),
            title='A restore stopped partway', status='rollback_incomplete', part=part,
            kept=str(kept), technical=_technical(exc), backup_created=created)
    did = ('Kel put back everything it had changed, so your data is exactly as it was before the '
           'restore.' if touched_any else 'Nothing was replaced, so your data is unchanged.')
    return _record_outcome(
        root, False,
        'Kel could not replace %s because %s. %s %s' % (what, REASON_WORDS[reason], did, NEXT_STEP[reason]),
        title='Kel could not restore your backup', status='rolled_back', part=part,
        technical=_technical(exc), backup_created=created)


def _recover(root, journal):
    """A journal at start: a restore was interrupted (crash, power loss) or could not be undone."""
    if journal.get('state') == 'done':
        # Every move was made; only the tidy-up was cut short.
        _clear_pending(root)
        (Path(root) / JOURNAL).unlink(missing_ok=True)
        previous = read_outcome(root) or {}
        if previous.get('status') != 'restored':
            _record_outcome(root, True, 'Kel finished restoring your backup.', title='Your backup was restored',
                            status='restored', kept=journal.get('kept') or '')
        return {'ran': True, 'ok': True, 'status': 'restored'}
    stuck = _undo(journal)
    part = journal.get('part') or ''
    if stuck:
        journal['moves'] = stuck
        _write_journal(root, journal)
        _record_outcome(
            root, False,
            'Kel is still putting back your data from before an unfinished restore: another program '
            'has some of those files open. Nothing was deleted: your data from before the restore is in '
            'the folder "%s" beside your data folder. Quit Kel completely and reopen it to finish; keep '
            'that folder until this message is gone.' % Path(journal.get('kept') or '').name,
            title='A restore stopped partway', status='rollback_incomplete', part=part,
            kept=journal.get('kept') or '', technical='undo pending: %d' % len(stuck))
        _clear_pending(root, staging=False)
        return {'ran': True, 'ok': False, 'status': 'rollback_incomplete'}
    (Path(root) / JOURNAL).unlink(missing_ok=True)
    if journal.get('kept'):
        _remove_if_empty(journal['kept'])
    _clear_pending(root)
    previous = read_outcome(root) or {}
    if previous.get('status') == 'rollback_incomplete':
        message = ('Kel finished putting back your data from before the restore, so it is exactly as it '
                   'was. ' + NEXT_STEP['in_use'])
    else:
        message = ('The restore was interrupted before it finished (Kel closed or the PC restarted). Kel '
                   'put back everything it had changed, so your data is exactly as it was before the '
                   'restore. ' + NEXT_STEP['in_use'])
    _record_outcome(root, False, message, title='Kel could not restore your backup', status='rolled_back',
                    part=part, technical='interrupted')
    return {'ran': True, 'ok': False, 'status': 'rolled_back'}


class _Root:
    def __init__(self, root):
        self.root = Path(root)


def apply_restore(root, store=None):
    """Apply a staged restore now, all or nothing. Returns None when nothing was pending.

    Must run before anything opens the data (the desktop calls it first thing at start); a file
    another program holds open makes the swap fail and roll back rather than half-apply.
    """
    root = Path(root)
    journal = _read_journal(root)
    if journal is not None:
        return _recover(root, journal)
    marker = root / MARKER
    if not marker.exists():
        return None
    info = _read_marker(marker)
    created = info.get('created')
    staging = root / STAGING
    if not staging.is_dir():
        _clear_pending(root)
        _record_outcome(root, False, 'Kel could not restore your backup because the copy it prepared was '
                        'missing. Nothing was replaced, so your data is unchanged. ' + NEXT_STEP['missing'],
                        title='Kel could not restore your backup', status='not_started',
                        technical='staging missing', backup_created=created)
        return {'ran': True, 'ok': False, 'status': 'not_started'}
    previous = read_outcome(root)
    if not info.get('id') and previous is not None and float(previous.get('at') or 0) >= float(info.get('staged') or 0):
        # FN-02: a restore staged by an earlier Kel that already tried (and failed) to apply it, then
        # retried on every start. Applying it now would undo everything done since; stop instead.
        _clear_pending(root)
        for live in data_layout(store or _Root(root)).values():
            if live is not None:
                _prune_snapshots(Path(live))
        _record_outcome(root, False, 'An earlier restore could not finish, and the previous version of Kel '
                        'kept retrying it each time it started. Kel has stopped retrying, so it no longer '
                        'changes your data: what you have now stays as it is. To restore that backup, '
                        'choose Restore again in Settings → System.',
                        title='Kel stopped an unfinished restore', status='abandoned',
                        technical=str((previous or {}).get('technical') or 'legacy marker'),
                        backup_created=created)
        return {'ran': True, 'ok': False, 'status': 'abandoned'}
    from .core import Conflict
    from .instance_lock import InstanceLock
    try:
        lock = InstanceLock(root)
    except (Conflict, OSError):
        _clear_pending(root)
        _record_outcome(root, False, 'Kel did not restore your backup because its engine was still running '
                        'work in the background, so nothing was replaced — your data is unchanged. Let that '
                        'work finish or stop it, quit Kel, reopen it, and choose Restore again in Settings → '
                        'System.', title='Kel could not restore your backup', status='not_started',
                        part='engine', technical='engine running', backup_created=created)
        return {'ran': True, 'ok': False, 'status': 'not_started'}
    try:
        return _apply_locked(root, store or _Root(root), info, staging, created)
    finally:
        lock.close()


def _apply_locked(root, store, info, staging, created):
    plan = []  # (part, staged folder, live folder)
    if int(info.get('format') or 1) >= 2:
        layout = data_layout(store)
        for part in PARTS:
            if (staging / part).is_dir() and layout.get(part) is not None:
                plan.append((part, staging / part, Path(layout[part])))
    else:
        plan.append(('engine', staging, root))
    parts = [part for part, _, _ in plan]
    if not plan:
        _clear_pending(root)
        _record_outcome(root, False, 'Kel could not restore your backup because the copy it prepared was '
                        'missing. Nothing was replaced, so your data is unchanged. ' + NEXT_STEP['missing'],
                        title='Kel could not restore your backup', status='not_started',
                        technical='nothing staged', backup_created=created)
        return {'ran': True, 'ok': False, 'status': 'not_started'}
    stamp = time.strftime('%Y-%m-%d %H%M%S')
    part = parts[0] if parts else ''
    kept = None
    journal = {'state': 'swapping', 'moves': [], 'kept': '', 'part': part}
    try:
        # Credentials stay in custody: the live values go into the staged copies before any swap.
        for part, staged, live in plan:
            if part == 'engine':
                _carry_engine_secrets(root / 'kel.sqlite3', staged / 'kel.sqlite3')
            if (staged / CHATS_DB).exists():
                _reapply_store_secrets(staged / CHATS_DB, _capture_store_secrets(live / CHATS_DB))
        for part, staged, live in plan:
            journal['part'] = part
            if kept is None:
                kept = live.parent / (BEFORE_PREFIX + stamp)
                suffix = 2
                while kept.exists():
                    kept = live.parent / ('%s%s (%d)' % (BEFORE_PREFIX, stamp, suffix))
                    suffix += 1
                journal['kept'] = str(kept)
            aside_root = (kept if kept.parent == live.parent else live.parent / kept.name) / part
            for source, target in _units(part, staged, live):
                aside = aside_root / target.relative_to(live)
                companions = [target]
                if target.name.lower().endswith(DB_SUFFIXES):
                    companions += [target.with_name(target.name + s) for s in ('-wal', '-shm', '-journal')]
                for current in companions:
                    if current.exists() or current.is_symlink():
                        moved = aside.with_name(current.name)
                        moved.parent.mkdir(parents=True, exist_ok=True)
                        journal['moves'].append([str(current), str(moved)])
                        _write_journal(root, journal)
                        _rename(current, moved)
                target.parent.mkdir(parents=True, exist_ok=True)
                journal['moves'].append([str(source), str(target)])
                _write_journal(root, journal)
                _rename(source, target)
        journal['state'] = 'done'
        _write_journal(root, journal)
    except Exception as exc:
        failed = journal.get('part') or part
        touched = bool(journal['moves'])
        stuck = _undo(journal) if touched else []
        if stuck:
            journal['moves'] = stuck
            try:
                _write_journal(root, journal)
            except Exception:
                pass
            _clear_pending(root, staging=False)
        else:
            (root / JOURNAL).unlink(missing_ok=True)
            if kept is not None:
                for folder in {Path(live.parent / kept.name) for _, _, live in plan}:
                    _remove_if_empty(folder)
            _clear_pending(root)
        _outcome_for_failure(root, failed, exc, kept or '', stuck, created, touched)
        return {'ran': True, 'ok': False, 'status': 'rollback_incomplete' if stuck else 'rolled_back',
                'part': failed}
    # Done: the marker goes first, so a crash from here on can only finish the tidy-up.
    _clear_pending(root, staging=False)
    for folder in {Path(live.parent / kept.name) for _, _, live in plan} if kept is not None else ():
        _remove_if_empty(folder)
    _record_outcome(
        root, True,
        'Kel restored %s from your backup%s. Your data from just before the restore is kept in the folder '
        '"%s" beside your data folder. Saved keys and sign-ins on this PC stayed as they were.'
        % (_words(parts), _when(created), kept.name if kept is not None else ''),
        title='Your backup was restored', status='restored', kept=str(kept or ''),
        backup_created=created)
    (root / JOURNAL).unlink(missing_ok=True)
    _rmtree(staging)
    for _, _, live in plan:
        _prune_snapshots(live)
        _prune_before_folders(live.parent)
    return {'ran': True, 'ok': True, 'status': 'restored'}


def apply_pending_restore(store):
    """The engine's own start-up path (a standalone engine, tests): apply a staged restore.

    Inside the desktop the main process applies restores before anything opens the data and sets
    ``KEL_RESTORE_OWNER=shell``; the engine then never touches a staged restore, because by the time
    it starts the chat store and the window may already hold their files. Returns True only when a
    restore was applied.
    """
    if os.environ.get(OWNER_ENV) == 'shell':
        return False
    result = apply_restore(Path(store.root), store)
    return bool(result and result.get('ok'))


def main(argv=None):
    """``python -m kel.backup --apply-restore --data <engine folder>``: the desktop's safe moment."""
    import argparse
    parser = argparse.ArgumentParser(description='Apply a staged Kel restore (all or nothing).')
    parser.add_argument('--data', required=True)
    parser.add_argument('--apply-restore', action='store_true')
    args = parser.parse_args(argv)
    if not args.apply_restore:
        parser.error('nothing to do')
    try:
        result = apply_restore(Path(args.data)) or {'ran': False}
    except Exception as exc:  # the caller records a failure itself when nothing was recorded
        result = {'ran': True, 'ok': False, 'status': 'crashed', 'technical': _technical(exc)}
    print(json.dumps(result), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
