"""One link table between the shell's chats and Kel's conversations (CP-10a stage 1, D-77).

Before this, three files and a JSON field said which Kel conversation an app chat (a "donor" chat,
owned by the bundled aioncore host) belongs to:

- D  `aion-session-map/<sha256(donor)>.json` — written by the ACP host when a chat is first opened;
- C  `aion-conversations.json` — the desktop's own map (older chats, and chats it adopted);
- E  `conversations.extra.kel_conversation_id` in the donor database — written on adoption.

The ACP host let D win, the desktop let E win (B-9), so one chat could answer in one conversation and
show the history of another. `chat_links` is the one answer, written only by the engine.

The switch: the engine setting `chat_store` (`legacy` | `engine`, default `legacy`), overridden by
the env `KEL_CHAT_STORE` or, for this engine process only, by the desktop (`override`). In `legacy`
every reader uses the files exactly as before. In `engine` every reader uses the table. The files
are never rewritten or deleted here: switching back to `legacy` gives today's behaviour.

Import (idempotent, safe to run on every start): candidates come from D, then C, then E. A donor
whose candidates all name one conversation gets that link. When they disagree, the side whose
engine conversation exists and has messages wins; when none does, every side is kept as a retired
row and the chat is treated as unlinked (a fresh link is made the next time it is opened). Every
conflict is written into the losing rows' `note`, so the report can show it. A donor is resolved
again only when a candidate it has never seen appears.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import threading
import time


MODES = ('legacy', 'engine')
DEFAULT_MODE = 'legacy'
ENV = 'KEL_CHAT_STORE'
SESSION_MAP = 'aion-session-map'
LEGACY_MAP = 'aion-conversations.json'

# Import precedence: where Kel answers (D), the desktop's own map (C), the donor row (E).
SOURCES = ('session-map', 'legacy-map', 'donor-extra')
# Links written live by the new path (the ACP host's session/new, the desktop's adoption).
LIVE_SOURCES = ('acp', 'adopt')

DDL = """
CREATE TABLE IF NOT EXISTS chat_links(
  donor_id TEXT NOT NULL, conversation_id TEXT NOT NULL, source TEXT NOT NULL, created REAL NOT NULL,
  retired REAL, note TEXT, PRIMARY KEY(donor_id, conversation_id));
CREATE UNIQUE INDEX IF NOT EXISTS chat_links_live ON chat_links(donor_id) WHERE retired IS NULL;
CREATE INDEX IF NOT EXISTS chat_links_conversation ON chat_links(conversation_id);
CREATE TABLE IF NOT EXISTS chat_store_settings(key TEXT PRIMARY KEY, value TEXT, at REAL NOT NULL);
"""

_ready = set()
_imported = set()  # engine databases whose D and C files were folded in by this process
_overrides = {}  # store root -> mode, set by the desktop for this engine process only
_lock = threading.Lock()


def _valid_id(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= 200


def record_path(root, donor_id):
    return Path(root) / SESSION_MAP / (hashlib.sha256(str(donor_id).encode()).hexdigest() + '.json')


def _read_json(path):
    try:
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8-sig'))
            return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        pass
    return {}


# -- the files, read exactly as before (legacy) ---------------------------------------------------
def legacy_map(root):
    """C: donor id -> conversation id."""
    return {k: v for k, v in _read_json(Path(root) / LEGACY_MAP).items() if _valid_id(k) and _valid_id(v)}


def session_records(root):
    """D: every per-chat record, merged (donor id -> conversation id)."""
    out = {}
    folder = Path(root) / SESSION_MAP
    if folder.is_dir():
        for record in sorted(folder.glob('*.json')):
            for k, v in _read_json(record).items():
                if _valid_id(k) and _valid_id(v):
                    out[k] = v
    return out


def legacy_conversation_for(root, donor_id):
    """The pre-table answer: the chat's own session record, else the desktop's map."""
    if not donor_id:
        return None
    found = _read_json(record_path(root, donor_id)).get(str(donor_id))
    if found:
        return found
    return legacy_map(root).get(str(donor_id))


def legacy_donor_for(root, cid):
    for donor, mapped in session_records(root).items():
        if mapped == cid:
            return donor
    return next((donor for donor, mapped in legacy_map(root).items() if mapped == cid), None)


def write_session_record(root, donor_id, cid, only_if_absent=False):
    """D, written atomically. `only_if_absent`: the engine mode never rewrites an existing record."""
    record = record_path(root, donor_id)
    if only_if_absent and record.exists():
        return False
    record.parent.mkdir(exist_ok=True)
    temporary = record.with_suffix('.' + os.urandom(8).hex() + '.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump({donor_id: cid}, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, record)
    return True


# -- the conflict rule ----------------------------------------------------------------------------
def conversation_weight(db, cid):
    """(exists, message count) for one engine conversation."""
    row = db.execute('SELECT 1 FROM conversations WHERE id=?', (cid,)).fetchone()
    if not row:
        return False, 0
    return True, db.execute('SELECT COUNT(*) FROM messages WHERE conversation_id=?', (cid,)).fetchone()[0]


def resolve(candidates, weigh):
    """The one conversation a chat links to, from `candidates` [(conversation id, source)] in
    precedence order, or None. `weigh(cid)` -> (exists, messages).

    One distinct conversation: it is the link (even if it has no row yet — a reserved chat).
    Several: the one whose conversation exists and has messages; if several do, the first in
    precedence order; if none does, no link."""
    distinct = []
    for cid, _source in candidates:
        if cid not in distinct:
            distinct.append(cid)
    if len(distinct) <= 1:
        return (distinct[0] if distinct else None), 'single'
    with_messages = [cid for cid in distinct if weigh(cid)[1] > 0]
    if len(with_messages) == 1:
        return with_messages[0], 'has-messages'
    if with_messages:
        return with_messages[0], 'has-messages-precedence'
    return None, 'none-has-messages'


class ChatLinks:
    def __init__(self, store):
        self.store = store
        self.root = Path(store.root)
        key = str(store.db_path)
        if key not in _ready:
            with contextlib.closing(store.connect()) as db:
                db.executescript(DDL)
            _ready.add(key)

    # -- the switch -------------------------------------------------------------------------------
    def setting(self):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT value FROM chat_store_settings WHERE key='chat_store'").fetchone()
        return row['value'] if row and row['value'] in MODES else None

    def mode(self):
        override = _overrides.get(str(self.root))
        if override in MODES:
            return override
        env = (os.environ.get(ENV) or '').strip().lower()
        if env in MODES:
            return env
        return self.setting() or DEFAULT_MODE

    def set_mode(self, mode):
        if mode not in MODES:
            raise ValueError('chat_store is legacy or engine')
        with self.store.transaction() as db:
            db.execute("INSERT INTO chat_store_settings VALUES('chat_store',?,?) ON CONFLICT(key) DO UPDATE "
                       'SET value=excluded.value, at=excluded.at', (mode, time.time()))
        return self.mode()

    def override(self, mode):
        """This engine process only (the desktop's `KEL_CHAT_STORE`); None clears it."""
        if mode in (None, ''):
            _overrides.pop(str(self.root), None)
        elif mode in MODES:
            _overrides[str(self.root)] = mode
        else:
            raise ValueError('chat_store is legacy or engine')
        return self.mode()

    # -- import -----------------------------------------------------------------------------------
    def import_links(self, extra=None):
        """Fold D, C and the given E links {donor: conversation} into the table (idempotent).
        Returns {'added', 'conflicts'}: each conflict names the chat, every side and the outcome."""
        per_donor = {}
        for source, links in (('session-map', session_records(self.root)),
                              ('legacy-map', legacy_map(self.root)),
                              ('donor-extra', {k: v for k, v in (extra or {}).items()
                                               if _valid_id(k) and _valid_id(v)})):
            for donor, cid in links.items():
                per_donor.setdefault(donor, []).append((cid, source))
        added, conflicts = 0, []
        with _lock, self.store.transaction() as db:
            for donor, candidates in per_donor.items():
                rows = db.execute('SELECT conversation_id,source,retired FROM chat_links WHERE donor_id=?',
                                  (donor,)).fetchall()
                known = {r['conversation_id'] for r in rows}
                fresh = [(cid, source) for cid, source in candidates if cid not in known]
                if not fresh:
                    continue
                live = [(r['conversation_id'], r['source']) for r in rows if r['retired'] is None]
                retired = [(r['conversation_id'], r['source']) for r in rows if r['retired'] is not None]
                ordered = live + fresh + retired
                outcome = self._settle(db, donor, ordered, rows)
                added += outcome['added']
                if outcome['conflict']:
                    conflicts.append(outcome['conflict'])
        return {'added': added, 'conflicts': conflicts}

    def _settle(self, db, donor, ordered, rows):
        weights = {}

        def weigh(cid):
            if cid not in weights:
                weights[cid] = conversation_weight(db, cid)
            return weights[cid]

        winner, rule = resolve(ordered, weigh)
        live_now = next((r['conversation_id'] for r in rows if r['retired'] is None), None)
        if winner is None and live_now is not None and any(
                r['conversation_id'] == live_now and r['source'] in LIVE_SOURCES for r in rows):
            # A link made by the new path (a chat opened after an earlier conflict) is kept: it is the
            # reserved conversation Kel will answer in.
            winner, rule = live_now, 'kept-live-link'
        now = time.time()
        conflict = None
        distinct = []
        for cid, source in ordered:
            if cid not in [d[0] for d in distinct]:
                distinct.append((cid, source))
        if len(distinct) > 1:
            conflict = {'donor': donor, 'rule': rule, 'winner': winner,
                        'sides': [{'conversation': cid, 'source': source, 'exists': weigh(cid)[0],
                                   'messages': weigh(cid)[1]} for cid, source in distinct]}
        note = json.dumps({'conflict': [c for c, _ in distinct], 'rule': rule, 'winner': winner}) if conflict else None
        existing = {r['conversation_id'] for r in rows}
        added = 0
        # Retire first so the one-live-link index never sees two live rows.
        for cid, _source in distinct:
            if cid != winner:
                if cid in existing:
                    db.execute('UPDATE chat_links SET retired=COALESCE(retired,?), note=COALESCE(?,note) '
                               'WHERE donor_id=? AND conversation_id=?', (now, note, donor, cid))
                else:
                    db.execute('INSERT INTO chat_links VALUES(?,?,?,?,?,?)', (donor, cid, _source, now, now, note))
                    added += 1
        if winner is not None:
            source = next(s for c, s in distinct if c == winner)
            if winner in existing:
                db.execute('UPDATE chat_links SET retired=NULL, note=COALESCE(?,note) '
                           'WHERE donor_id=? AND conversation_id=?', (note, donor, winner))
            else:
                db.execute('INSERT INTO chat_links VALUES(?,?,?,?,NULL,?)', (donor, winner, source, now, note))
                added += 1
        return {'added': added, 'conflict': conflict}

    # -- reads ------------------------------------------------------------------------------------
    def conversation_for(self, donor_id):
        if not donor_id:
            return None
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT conversation_id FROM chat_links WHERE donor_id=? AND retired IS NULL',
                             (str(donor_id),)).fetchone()
        return row['conversation_id'] if row else None

    def donor_for(self, cid):
        if not cid:
            return None
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT donor_id FROM chat_links WHERE conversation_id=? AND retired IS NULL '
                             'ORDER BY created LIMIT 1', (str(cid),)).fetchone()
        return row['donor_id'] if row else None

    def live(self):
        with contextlib.closing(self.store.connect()) as db:
            return {r['donor_id']: r['conversation_id']
                    for r in db.execute('SELECT donor_id,conversation_id FROM chat_links WHERE retired IS NULL')}

    def conflicts(self):
        with contextlib.closing(self.store.connect()) as db:
            rows = db.execute('SELECT donor_id,conversation_id,source,retired,note FROM chat_links '
                              'WHERE note IS NOT NULL ORDER BY donor_id,created').fetchall()
        out = {}
        for r in rows:
            item = out.setdefault(r['donor_id'], dict(json.loads(r['note']), donor=r['donor_id'], rows=[]))
            item['rows'].append({'conversation': r['conversation_id'], 'source': r['source'],
                                 'retired': r['retired'] is not None})
        return list(out.values())

    # -- writes (the new path) --------------------------------------------------------------------
    def link(self, donor_id, cid, source):
        """A link made live by the ACP host (`acp`) or the desktop's adoption (`adopt`). A chat that
        already links to a conversation with messages keeps it; the effective link is returned."""
        if not _valid_id(donor_id) or not _valid_id(cid):
            raise ValueError('Pick a chat first.')
        if source not in LIVE_SOURCES:
            raise ValueError('Unknown link source')
        donor_id, cid = donor_id.strip(), cid.strip()
        with _lock, self.store.transaction() as db:
            rows = db.execute('SELECT conversation_id,retired FROM chat_links WHERE donor_id=?', (donor_id,)).fetchall()
            live = next((r['conversation_id'] for r in rows if r['retired'] is None), None)
            if live == cid:
                return cid
            if live is not None:
                if conversation_weight(db, live)[1] > 0:
                    return live
                db.execute('UPDATE chat_links SET retired=?, note=COALESCE(note,?) WHERE donor_id=? AND conversation_id=?',
                           (time.time(), json.dumps({'replaced_by': cid, 'rule': 'empty-link-replaced'}), donor_id, live))
            if any(r['conversation_id'] == cid for r in rows):
                db.execute('UPDATE chat_links SET retired=NULL, source=? WHERE donor_id=? AND conversation_id=?',
                           (source, donor_id, cid))
            else:
                db.execute('INSERT INTO chat_links VALUES(?,?,?,?,NULL,NULL)', (donor_id, cid, source, time.time()))
        return cid

    def retire(self, donor_id, reason='gone'):
        """The chat is gone in the shell: its link stops being live. The row is kept."""
        with _lock, self.store.transaction() as db:
            db.execute('UPDATE chat_links SET retired=?, note=COALESCE(note,?) WHERE donor_id=? AND retired IS NULL',
                       (time.time(), json.dumps({'retired': str(reason)[:80]}), str(donor_id)))
        return {'ok': True}

    # -- the mode-aware answers every reader uses --------------------------------------------------
    def resolve_donor(self, donor_id):
        if self.mode() == 'engine':
            self.ensure_imported()
            return self.conversation_for(donor_id)
        return legacy_conversation_for(self.root, donor_id)

    def resolve_conversation(self, cid):
        if self.mode() == 'engine':
            self.ensure_imported()
            return self.donor_for(cid)
        return legacy_donor_for(self.root, cid)

    def ensure_imported(self):
        """D and C are folded in once per engine process (E arrives from the desktop's start-up)."""
        key = str(self.store.db_path)
        if key in _imported:
            return
        self.import_links()
        _imported.add(key)

    # -- `/api/chat-link` -------------------------------------------------------------------------
    def view(self, donor=None, conversation=None):
        mode = self.mode()
        if mode == 'engine':
            self.ensure_imported()
        out = {'mode': mode, 'setting': self.setting() or DEFAULT_MODE}
        if donor:
            out['conversation'] = self.conversation_for(donor)
        elif conversation:
            out['donor'] = self.donor_for(conversation)
        else:
            out['links'] = self.live()
        return out

    def apply(self, data):
        action = data.get('action')
        if action in (None, 'get'):
            return self.view(data.get('donor'), data.get('conversation'))
        if action == 'import':
            extra = data.get('links') if isinstance(data.get('links'), dict) else {}
            result = self.import_links(extra)
            _imported.add(str(self.store.db_path))
            return dict(result, mode=self.mode(), links=self.live())
        if action == 'link':
            return {'conversation': self.link(data.get('donor'), data.get('conversation'), data.get('source') or 'acp')}
        if action == 'retire':
            return self.retire(data.get('donor'), data.get('reason') or 'gone')
        if action == 'mode':
            if 'override' in data:
                self.override(data.get('override'))
            if data.get('set'):
                self.set_mode(data['set'])
            return {'mode': self.mode(), 'setting': self.setting() or DEFAULT_MODE}
        if action == 'conflicts':
            return {'conflicts': self.conflicts()}
        raise ValueError('Unknown chat link action')

