"""The state of each chat, kept by the engine (CP-10a stage 3, D-77), and the one-time switch to the one
chat store with a fresh start (D-80).

`chat_state` holds, per app chat (keyed by its donor id, the handle the shell and aioncore use):
the title, archived / pinned / deleted times, and `legacy` — the time the chat was frozen at the
switch (a chat from before the one store). The shell writes it first on rename, pin, archive,
unarchive and delete, then mirrors the change to aioncore (`common/adapter/kelChatState.ts`), so the
engine knows what the person did even when aioncore's copy is not read (the Memory mirror, search).

The switch (`/api/chat-store`, main process only):
- `backup`   copies the databases and link files the switch touches into
             `<engine>/chat-store-migration/<stamp>/` (SQLite's backup API, so a live database copies
             safely) before anything changes;
- `freeze`   marks the chats that exist now as legacy and archived (nothing is deleted);
- `complete` sets `chat_store = engine` and records when;
- `status`   the migration record.
The desktop drives these in order (`chatStoreMigration.ts`); each step is idempotent, so a switch
cut short is finished on the next launch.
"""
import contextlib
import json
from pathlib import Path
import shutil
import sqlite3
import threading
import time

from .chat_links import LEGACY_MAP, SESSION_MAP, ChatLinks


DDL = """
CREATE TABLE IF NOT EXISTS chat_state(
  donor_id TEXT PRIMARY KEY, conversation_id TEXT, title TEXT, archived_at REAL, pinned_at REAL,
  deleted_at REAL, legacy REAL, updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS chat_state_conversation ON chat_state(conversation_id);
"""

MIGRATION_KEY = 'migration'
BACKUP_DIR = 'chat-store-migration'
HISTORY_FILE = 'aion-history.json'
FIELDS = ('donor_id', 'conversation_id', 'title', 'archived_at', 'pinned_at', 'deleted_at', 'legacy', 'updated')

_ready = set()
_lock = threading.Lock()


def _valid_id(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= 200


def _title(value):
    if not isinstance(value, str):
        return None
    value = ' '.join(value.split())
    return value[:200] or None


def _hot_copy(source, destination):
    """A SQLite-safe copy of a database another process may hold open (WAL included)."""
    src = sqlite3.connect(Path(source).resolve().as_uri() + '?mode=ro', uri=True, timeout=10)
    dst = sqlite3.connect(str(destination), timeout=10)
    try:
        src.execute('PRAGMA busy_timeout=8000')
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()


class ChatState:
    def __init__(self, store):
        self.store = store
        self.root = Path(store.root)
        key = str(store.db_path)
        if key not in _ready:
            ChatLinks(store)  # the settings table lives with the links
            with contextlib.closing(store.connect()) as db:
                db.executescript(DDL)
            _ready.add(key)

    # -- per chat -------------------------------------------------------------------------------
    def get(self, donor_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM chat_state WHERE donor_id=?', (str(donor_id),)).fetchone()
        return dict(row) if row else None

    def rows(self):
        with contextlib.closing(self.store.connect()) as db:
            return [dict(r) for r in db.execute('SELECT * FROM chat_state ORDER BY updated')]

    def set(self, data):
        """One change the person made to a chat: any of title, archived, pinned, deleted (booleans)."""
        donor = data.get('donor')
        if not _valid_id(donor):
            raise ValueError('Pick a chat first.')
        donor = donor.strip()
        now = time.time()
        with _lock, self.store.transaction() as db:
            db.execute('INSERT OR IGNORE INTO chat_state(donor_id,updated) VALUES(?,?)', (donor, now))
            changes, values = ['updated=?'], [now]
            conversation = data.get('conversation')
            if not _valid_id(conversation):
                row = db.execute('SELECT conversation_id FROM chat_links WHERE donor_id=? AND retired IS NULL',
                                 (donor,)).fetchone()
                conversation = row['conversation_id'] if row else None
            if _valid_id(conversation):
                changes.append('conversation_id=?')
                values.append(conversation.strip())
            if 'title' in data and _title(data.get('title')):
                changes.append('title=?')
                values.append(_title(data['title']))
            for field, column in (('archived', 'archived_at'), ('pinned', 'pinned_at'), ('deleted', 'deleted_at')):
                if field in data:
                    # A time is kept when the flag is set again (the first archive stays the archive time).
                    changes.append('%s=%s' % (column, 'COALESCE(%s,?)' % column if data[field] else '?'))
                    values.append(now if data[field] else None)
            if data.get('archived'):
                changes.append('pinned_at=NULL')  # archiving unpins, as it does in the shell
            db.execute('UPDATE chat_state SET %s WHERE donor_id=?' % ','.join(changes), (*values, donor))
        return self.get(donor)

    def delete_archived(self):
        """"Empty the archive": every archived chat that is not deleted yet is now deleted."""
        now = time.time()
        with _lock, self.store.transaction() as db:
            count = db.execute('UPDATE chat_state SET deleted_at=?, updated=? WHERE archived_at IS NOT NULL '
                               'AND deleted_at IS NULL', (now, now)).rowcount
        return {'deleted': count}

    def apply(self, data):
        """`/api/chat-state` — what the renderer may do."""
        action = data.get('action') or 'set'
        if action == 'set':
            return self.set(data)
        if action == 'get':
            return {'chat': self.get(data.get('donor'))} if data.get('donor') else {'chats': self.rows()}
        if action == 'delete-archived':
            return self.delete_archived()
        raise ValueError('Unknown chat state action')

    # -- the switch (D-80) ----------------------------------------------------------------------
    def _setting(self, key):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT value FROM chat_store_settings WHERE key=?', (key,)).fetchone()
        if not row or not row['value']:
            return None
        try:
            return json.loads(row['value'])
        except ValueError:
            return None

    def _put_setting(self, db, key, value):
        db.execute('INSERT INTO chat_store_settings VALUES(?,?,?) ON CONFLICT(key) DO UPDATE '
                   'SET value=excluded.value, at=excluded.at', (key, json.dumps(value), time.time()))

    def migration(self):
        return self._setting(MIGRATION_KEY) or {'state': 'none'}

    def backup(self, data):
        """Copy what the switch changes. Reused, never retaken, once a switch has started: a second copy
        would hold chats the first attempt already archived."""
        record = self.migration()
        if record.get('backup') and Path(record['backup']).is_dir():
            return record
        stamp = time.strftime('%Y%m%d-%H%M%S')
        folder = self.root / BACKUP_DIR / stamp
        n = 2
        while folder.exists():
            folder, n = self.root / BACKUP_DIR / ('%s-%d' % (stamp, n)), n + 1
        folder.mkdir(parents=True)
        copied, skipped = [], []
        _hot_copy(self.store.db_path, folder / self.store.db_path.name)
        copied.append(self.store.db_path.name)
        donor = data.get('donor_db')
        if isinstance(donor, str) and donor and Path(donor).is_file():
            _hot_copy(donor, folder / Path(donor).name)
            copied.append(Path(donor).name)
        elif donor:
            skipped.append(str(donor))
        for name in (LEGACY_MAP, HISTORY_FILE):
            source = self.root / name
            if source.is_file():
                shutil.copy2(source, folder / name)
                copied.append(name)
        if (self.root / SESSION_MAP).is_dir():
            shutil.copytree(self.root / SESSION_MAP, folder / SESSION_MAP)
            copied.append(SESSION_MAP)
        (folder / 'README.txt').write_text(
            'Copied by Kel before it moved to one chat store (D-80), %s.\n'
            'To go back: close Kel, put these files back where they came from (the engine folder, and\n'
            'aionui-backend.db into the store folder), and set KEL_CHAT_STORE=legacy.\n' % time.strftime('%Y-%m-%d %H:%M'),
            encoding='utf-8')
        record = dict(record, state='started', backup=str(folder), copied=copied, skipped=skipped,
                      started=record.get('started') or time.time())
        with _lock, self.store.transaction() as db:
            self._put_setting(db, MIGRATION_KEY, record)
        return record

    def freeze(self, data):
        """Every chat given (the app's chats that exist now) becomes legacy and archived. Chats
        frozen before keep their first times. Returns how many rows changed."""
        chats = data.get('chats') if isinstance(data.get('chats'), list) else []
        now = time.time()
        frozen = 0
        record = self.migration()
        with _lock, self.store.transaction() as db:
            for chat in chats:
                donor = chat.get('donor') if isinstance(chat, dict) else None
                if not _valid_id(donor):
                    continue
                donor = donor.strip()
                db.execute('INSERT OR IGNORE INTO chat_state(donor_id,updated) VALUES(?,?)', (donor, now))
                conversation = chat.get('conversation') if _valid_id(chat.get('conversation')) else None
                live = db.execute('SELECT conversation_id FROM chat_links WHERE donor_id=? AND retired IS NULL',
                                  (donor,)).fetchone()
                if live:
                    conversation = live['conversation_id']  # the one link wins over the app's own field
                frozen +=db.execute(
                    'UPDATE chat_state SET legacy=COALESCE(legacy,?), archived_at=COALESCE(archived_at,?), '
                    'pinned_at=NULL, conversation_id=COALESCE(conversation_id,?), title=COALESCE(title,?), updated=? '
                    'WHERE donor_id=? AND (legacy IS NULL OR archived_at IS NULL)',
                    (now, now, conversation, _title(chat.get('title')), now, donor)).rowcount
            record = dict(record, frozen=(record.get('frozen') or 0) + frozen)
            self._put_setting(db, MIGRATION_KEY, record)
        return {'frozen': frozen}

    def complete(self, data):
        record = self.migration()
        if record.get('state') == 'done':
            return record
        record = dict(record, state='done', finished=time.time(),
                      archived=int(data.get('archived') or 0) + int(record.get('archived') or 0))
        with _lock, self.store.transaction() as db:
            self._put_setting(db, MIGRATION_KEY, record)
            db.execute("INSERT INTO chat_store_settings VALUES('chat_store','engine',?) ON CONFLICT(key) DO UPDATE "
                       "SET value='engine', at=excluded.at", (time.time(),))
        return record

    def store_action(self, data):
        """`/api/chat-store` — the switch; the main process only (not in the renderer's allowlist)."""
        action = data.get('action') or 'status'
        if action == 'status':
            return self.migration()
        if action == 'backup':
            return self.backup(data)
        if action == 'freeze':
            return self.freeze(data)
        if action == 'complete':
            return self.complete(data)
        raise ValueError('Unknown chat store action')


# ---- read-only helpers for the Memory mirror --------------------------------------------------

def read_states(db):
    """{donor id: row} from an open (read-only) connection, or {} before the table exists."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chat_state'").fetchone():
        return {}
    return {r['donor_id']: dict(r) for r in db.execute('SELECT * FROM chat_state')}
