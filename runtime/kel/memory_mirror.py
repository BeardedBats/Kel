"""D-81: `Memory\\Kel`, the read-only mirror Kel keeps current for the agents.

    Memory\\Kel\\settings.json                          Kel's settings, with every key, password and token removed
    Memory\\Kel\\chats\\<project or "No project">\\<date> <title>.md   one file per chat, ALL chats (archived too)
    Memory\\Kel\\knowledge\\<project>\\notes.md | memory.md          project notes and remembered facts

Kel writes it (on change, debounced: `Keeper`) and nobody else: the Claude Code guard refuses file
edits there, and every sync compares the mirror with what Kel last wrote (a manifest kept in Kel's own
engine folder, out of the agents' reach) and puts it back — a changed file is rewritten, a file an
agent added is moved out to `<engine>\\memory-mirror\\reverted`. Mirror files are also marked read-only.

Never credentials: settings are stripped by key name AND by value shape, chat and note text has
secret-shaped strings replaced, and `assert_clean` checks the settings before they are written.
"""
import contextlib
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import threading
import time

from . import memory_folder

STATE_DIR = memory_folder.STATE_DIR  # in the engine root (listed in runtime_guard._ENGINE_DIRS)
MANIFEST = 'manifest.json'
REVERTED = 'reverted'
REMOVED = '[secret removed]'
NO_PROJECT = 'No project'

# Settings tables worth mirroring (each is small). Credentials tables are never read.
SETTINGS_TABLES = ('authority_prefs', 'network_policy', 'network_tool_rules', 'model_prefs', 'role_models',
                   'role_overrides', 'project_prefs', 'project_tests', 'retention_settings',
                   'transcription_settings', 'transcription_folders', 'scoping_prefs', 'chat_store_settings',
                   'capability_global', 'staff_model_status')
NEVER_TABLES = ('provider_credentials', 'providers', 'connections', 'oauth_flows')

# Field names that hold credentials: api_key/apiKey/private_key, *token*, *secret*, password, credential,
# authorization, auth_token, cookie, bearer, signature. A bare "key" column (key/value tables) is a name.
SECRET_KEY = re.compile(r'([a-z0-9][_\-.]?key$|apikey|token|secret|passw|pwd|credential|authoriz|^auth$|'
                        r'auth[_\-.]?(token|header|code|data)|cookie|bearer|signature|^salt$)', re.I)


# Value shapes that are credentials whatever their key: provider keys, JWTs, long opaque strings.
_VALUE_SHAPES = (
    re.compile(r'sk-[A-Za-z0-9_\-]{16,}'),
    re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}'),
    re.compile(r'AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,}'),
    re.compile(r'eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    re.compile(r'(?i)authorization\s*:\s*bearer\s+\S{8,}'),
    re.compile(r'(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd|pwd)\b\s*[:=]\s*\S{6,}'),
)
_OPAQUE = re.compile(r'^[A-Za-z0-9+/=_\-]{32,}$')


# ---- secrets --------------------------------------------------------------------------------------

def redact(text):
    """Text with every secret-shaped string replaced."""
    out = str(text or '')
    for pattern in _VALUE_SHAPES:
        out = pattern.sub(REMOVED, out)
    return out


def _secret_value(value):
    if not isinstance(value, str):
        return False
    if any(p.search(value) for p in _VALUE_SHAPES):
        return True
    return bool(_OPAQUE.match(value)) and not re.match(r'^[0-9a-f\-]{32,36}$', value)  # ids stay


def strip(value):
    """A copy of `value` without secret-named keys or secret-shaped values."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if SECRET_KEY.search(str(key)):
                continue
            if isinstance(item, str) and _secret_value(item):
                continue
            out[key] = strip(item)
        return out
    if isinstance(value, list):
        return [strip(v) for v in value if not (isinstance(v, str) and _secret_value(v))]
    if isinstance(value, str):
        return redact(value)
    return value


def assert_clean(value, where='settings'):
    """Raise ValueError if anything credential-like is left (checked before the mirror is written)."""
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.search(str(key)):
                raise ValueError('%s: a secret-named field (%s) reached the mirror' % (where, key))
            assert_clean(item, '%s.%s' % (where, key))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            assert_clean(item, '%s[%d]' % (where, i))
    elif isinstance(value, str) and _secret_value(value):
        raise ValueError('%s: a secret-shaped value reached the mirror' % where)


# ---- reading Kel's data (read-only) ---------------------------------------------------------------

def _connect(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    return db


def _table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _when(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value > 10 ** 11:
        value /= 1000
    try:
        return datetime.fromtimestamp(value)
    except (OverflowError, OSError, ValueError):
        return None


def _data_paths(engine_root):
    """(engine database, donor database or None, desktop config file or None)."""
    engine = Path(engine_root)
    data = engine.parent if engine.name.lower() == 'engine' else None
    donor = None
    for base in ([Path(os.environ['AIONUI_DATA_DIR'])] if os.environ.get('AIONUI_DATA_DIR') else []) + (
            [data / 'store'] if data else []):
        if (base / 'aionui-backend.db').exists():
            donor = base / 'aionui-backend.db'
            break
    config = None
    for base in ([Path(os.environ['KEL_HOST_DATA_DIR'])] if os.environ.get('KEL_HOST_DATA_DIR') else []) + (
            [data / 'host'] if data else []):
        for name in ('config/aionui-config.txt', 'config/configionui-config.txt', 'configionui-config.txt',
                     'aionui-config.txt'):
            if (base / name).exists():
                config = base / name
                break
        if config:
            break
    return engine / 'kel.sqlite3', donor, config


def _projects(db):
    projects = {}
    if _table(db, 'projects'):
        meta = {}
        if _table(db, 'project_meta'):
            meta = {r['project_id']: dict(r) for r in db.execute('SELECT * FROM project_meta')}
        for row in db.execute('SELECT id,name,root,context FROM projects'):
            m = meta.get(row['id']) or {}
            projects[row['id']] = {'id': row['id'], 'name': row['name'], 'folder': row['root'],
                                   'kind': m.get('kind') or ('general' if row['id'] == 'default' else 'user'),
                                   'archived': bool(m.get('archived')), 'notes': row['context'] or ''}
    return projects


def _desktop_config(path):
    if not path:
        return {}
    try:
        import base64
        import urllib.parse
        raw = Path(path).read_text(encoding='utf-8').strip()
        return json.loads(urllib.parse.unquote(base64.b64decode(raw).decode('latin-1')))
    except (OSError, ValueError):
        return {}


def settings(engine_root):
    """Kel's settings for the agents, without a single key, password or token."""
    engine_db, _donor, config = _data_paths(engine_root)
    out = {'about': ("Kel's settings, copied by Kel for reading. Keys, passwords and tokens are never "
                     'included. Agents never change these; ask Kel (the person) instead.'),
           'memory_folder': str(memory_folder.memory_root(engine_root)),
           'new_projects_folder': str(memory_folder.projects_dir(engine_root))}
    if engine_db.exists():
        with contextlib.closing(_connect(engine_db)) as db:
            out['projects'] = [{k: v for k, v in p.items() if k != 'notes'} for p in _projects(db).values()]
            engine = {}
            for table in SETTINGS_TABLES:
                if table in NEVER_TABLES or not _table(db, table):
                    continue
                engine[table] = [dict(r) for r in db.execute('SELECT * FROM %s' % table)]
            out['engine'] = engine
    desktop = _desktop_config(config)
    if desktop:
        out['desktop'] = desktop
    clean = strip(out)
    assert_clean(clean)
    return clean


def chats(engine_root):
    """Every chat: [{project, title, created (datetime|None), archived, messages: [{role, text}]}].

    Both chat stores are read (D-77): the app's chats (with their titles and archived flag) with the
    words Kel's engine holds for them (and the app's own rows for words only it has), then every Kel
    conversation no app chat points at. With the one chat store (`chat_store = engine`, D-80) a chat's
    conversation is its `chat_links` row, a chat archived at the switch (or since) is archived, and a
    chat deleted in the app (its link names a chat that is gone, or `chat_state` says deleted) is
    left out."""
    from . import chat_links, chat_state
    engine_db, donor, _config = _data_paths(engine_root)
    if not engine_db.exists():
        return []
    with contextlib.closing(_connect(engine_db)) as db:
        projects = _projects(db)
        conversations = {r['id']: dict(r) for r in db.execute('SELECT id,project_id,title,created FROM conversations')}
        visible = 'seq NOT IN (SELECT seq FROM rewound_messages)' if _table(db, 'rewound_messages') else '1=1'
        messages = {}
        for row in db.execute('SELECT conversation_id,role,text,at FROM messages WHERE ' + visible + ' ORDER BY seq'):
            messages.setdefault(row['conversation_id'], []).append({'role': row['role'], 'text': row['text'] or ''})
        one_store = chat_links.mode_of(engine_db.parent, db) == 'engine'
        links = chat_links.live_links(db) if one_store else None
        ever_linked = chat_links.linked_conversations(db) if one_store else set()
        states = chat_state.read_states(db)

    def project_name(pid):
        if not pid:
            return NO_PROJECT
        project = projects.get(pid)
        return project['name'] if project else NO_PROJECT

    out, linked = [], set()
    deleted = {s['conversation_id'] for s in states.values() if s.get('deleted_at') and s.get('conversation_id')}
    if donor is not None:
        from .chatstore import inventory
        try:
            report = inventory(engine_db.parent, donor, show_text=True, effective_links=links)
        except (SystemExit, sqlite3.Error):
            report = {'chats': []}
        for chat in report['chats']:
            effective = chat.get('effective') or {}
            cid = effective.get('conversation')
            if cid:
                linked.add(cid)
            state = states.get(chat.get('donor_id')) or {}
            if state.get('deleted_at'):
                continue
            pid = chat['links'].get('project_binding') or (conversations.get(cid) or {}).get('project_id')
            words = [{'role': item['role'], 'text': item['text']} for item in chat['plan']
                     if 'text' in item and item.get('role') in ('user', 'assistant')]
            out.append({'project': project_name(pid), 'title': chat.get('title') or state.get('title') or 'Untitled chat',
                        'created': _parse(chat.get('created')),
                        'archived': bool(chat.get('archived')) or bool(state.get('archived_at')),
                        'messages': words})
    for cid, conv in conversations.items():
        if cid in linked or cid in deleted or not messages.get(cid):
            continue  # an empty Kel conversation no chat points at is not a chat anyone sees
        if donor is not None and cid in ever_linked:
            continue  # its app chat was deleted: not a chat any more
        out.append({'project': project_name(conv.get('project_id')), 'title': conv.get('title') or 'Untitled chat',
                    'created': _when(conv.get('created')), 'archived': False, 'messages': messages[cid]})
    return out


def _parse(text):
    try:
        return datetime.strptime(text, '%Y-%m-%d %H:%M') if text else None
    except ValueError:
        return None


def knowledge(engine_root):
    """{project name: {'notes': text, 'memory': [(topic, text)]}} — project notes and remembered facts."""
    engine_db, _donor, _config = _data_paths(engine_root)
    if not engine_db.exists():
        return {}
    out = {}
    with contextlib.closing(_connect(engine_db)) as db:
        projects = _projects(db)
        facts = {}
        if _table(db, 'memories'):
            for row in db.execute("SELECT project_id,type,topic,value,summary FROM memories WHERE status='active' "
                                  'ORDER BY project_id,type,topic'):
                facts.setdefault(row['project_id'], []).append(
                    ('%s — %s' % (row['type'], row['topic']), row['value'] or row['summary'] or ''))
    for pid, project in projects.items():
        notes, memory = project['notes'].strip(), facts.get(pid) or []
        if notes or memory:
            out[project['name']] = {'notes': notes, 'memory': memory}
    return out


# ---- writing the mirror ---------------------------------------------------------------------------

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(text, limit=80):
    name = _BAD.sub(' ', str(text or '')).strip().rstrip('. ')
    name = re.sub(r'\s+', ' ', name)[:limit].rstrip('. ') or 'Untitled'
    if name.upper().split('.')[0] in {'CON', 'PRN', 'AUX', 'NUL', *('COM%d' % i for i in range(10)),
                                      *('LPT%d' % i for i in range(10))}:
        name = '_' + name
    return name


def chat_markdown(chat):
    lines = ['# ' + redact(chat['title']), '']
    facts = ['Project: ' + chat['project']]
    if chat.get('created'):
        facts.append('Started: ' + chat['created'].strftime('%Y-%m-%d %H:%M'))
    if chat.get('archived'):
        facts.append('Archived')
    lines += [' · '.join(facts), '']
    if not chat['messages']:
        lines.append('_No messages._')
    for message in chat['messages']:
        who = 'You' if message['role'] == 'user' else 'Kel'
        lines += ['## ' + who, '', redact(message['text']).strip() or '_(empty)_', '']
    return '\n'.join(lines).rstrip() + '\n'


def files(engine_root):
    """{relative path: text} — the whole mirror as Kel would write it now."""
    out = {'settings.json': json.dumps(settings(engine_root), indent=2, ensure_ascii=False, default=str) + '\n',
           'README.md': ("# Kel's mirror\n\nKel keeps this folder current so its agents can read Kel's settings, "
                         'every chat and each project\'s notes. It is read-only: Kel puts back anything '
                         "changed here. It never holds keys, passwords or tokens.\n")}
    taken = set()
    for chat in chats(engine_root):
        date = chat['created'].strftime('%Y-%m-%d') if chat.get('created') else 'undated'
        base = 'chats/%s/%s %s' % (safe_name(chat['project']), date, safe_name(redact(chat['title'])))
        rel, n = base + '.md', 2
        while rel.lower() in taken:
            rel, n = '%s (%d).md' % (base, n), n + 1
        taken.add(rel.lower())
        out[rel] = chat_markdown(chat)
    for name, item in knowledge(engine_root).items():
        folder = 'knowledge/' + safe_name(name)
        if item['notes']:
            out[folder + '/notes.md'] = '# %s — notes\n\n%s\n' % (name, redact(item['notes']))
        if item['memory']:
            body = '\n'.join('- **%s**: %s' % (redact(topic), redact(text).replace('\n', ' ')) for topic, text in item['memory'])
            out[folder + '/memory.md'] = '# %s — what Kel remembers\n\n%s\n' % (name, body)
    return out


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _state(engine_root):
    return Path(engine_root) / STATE_DIR


def _manifest(engine_root):
    try:
        return json.loads((_state(engine_root) / MANIFEST).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _writable(path):
    with contextlib.suppress(OSError):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def _readonly(path):
    with contextlib.suppress(OSError):
        os.chmod(path, stat.S_IREAD)


_lock = threading.Lock()


def sync(engine_root):
    """Bring Memory\\Kel exactly to what Kel would write now. Returns {'written': [...], 'reverted': [...],
    'removed': [...]} (relative paths). `reverted` lists files someone else changed or added."""
    with _lock:
        root = memory_folder.ensure(engine_root) / memory_folder.MIRROR
        wanted = {rel: text.encode('utf-8') for rel, text in files(engine_root).items()}
        manifest = _manifest(engine_root)
        written, reverted, removed = [], [], []
        seen = set()
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            seen.add(rel)
            try:
                current = _digest(path.read_bytes())
            except OSError:
                current = None
            if rel not in wanted:
                if manifest.get(rel) != current:
                    reverted.append(rel)  # an agent's file: moved out, never deleted
                    target = _state(engine_root) / REVERTED / ('%d-%s' % (int(time.time() * 1000), path.name))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    _writable(path)
                    with contextlib.suppress(OSError):
                        shutil.move(str(path), str(target))
                else:
                    removed.append(rel)  # Kel's own file that is no longer wanted (a renamed chat)
                    _writable(path)
                    with contextlib.suppress(OSError):
                        path.unlink()
                continue
            if current != _digest(wanted[rel]):
                if rel in manifest and manifest[rel] != current:
                    reverted.append(rel)
                _write(path, wanted[rel])
                written.append(rel)
            else:
                _readonly(path)
        for rel, data in wanted.items():
            if rel not in seen:
                if rel in manifest:
                    reverted.append(rel)  # deleted by someone else
                _write(root / rel, data)
                written.append(rel)
        # Empty folders left by renamed or removed chats.
        for folder in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            with contextlib.suppress(OSError):
                folder.rmdir()
        state = _state(engine_root)
        state.mkdir(parents=True, exist_ok=True)
        (state / MANIFEST).write_text(json.dumps({rel: _digest(d) for rel, d in wanted.items()}, indent=0),
                                      encoding='utf-8')
        return {'written': written, 'reverted': sorted(set(reverted)), 'removed': removed}


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _writable(path)
    tmp = path.with_name(path.name + '.kel-tmp')
    tmp.write_bytes(data)
    os.replace(tmp, path)
    _readonly(path)


def tampered(engine_root):
    """Relative paths in Memory\\Kel that differ from what Kel last wrote (changed, added or removed)."""
    root = memory_folder.mirror_dir(engine_root)
    manifest = _manifest(engine_root)
    found = []
    present = set()
    if root.is_dir():
        for path in root.rglob('*'):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                present.add(rel)
                try:
                    if manifest.get(rel) != _digest(path.read_bytes()):
                        found.append(rel)
                except OSError:
                    found.append(rel)
    found += [rel for rel in manifest if rel not in present]
    return sorted(found)


# ---- keeping it current ---------------------------------------------------------------------------

def fingerprint(engine_root):
    """Cheap change signal: sizes and mtimes of the files the mirror is made from."""
    engine_db, donor, config = _data_paths(engine_root)
    parts = []
    for path in (engine_db, Path(str(engine_db) + '-wal'), donor, Path(str(donor) + '-wal') if donor else None, config):
        if path is None:
            continue
        try:
            st = path.stat()
            parts.append((str(path), st.st_size, st.st_mtime_ns))
        except OSError:
            parts.append((str(path), None, None))
    return tuple(parts)


def enabled():
    return (os.environ.get('KEL_MEMORY_MIRROR') or '1').strip().lower() not in ('0', 'off', 'false', 'no')


class Keeper:
    """Keeps Memory\\Kel current: a sync once the source files have been still for `quiet` seconds after
    a change (debounced), and a tamper check every `check` seconds that puts back anything changed."""

    def __init__(self, engine_root, stop, poll=2.0, quiet=2.0, check=15.0):
        self.engine_root = Path(engine_root)
        self.stop = stop
        self.poll, self.quiet, self.check = poll, quiet, check
        self.last = None
        self.error = None
        self.thread = threading.Thread(target=self._loop, daemon=True, name='kel-memory-mirror')

    def start(self):
        self.thread.start()
        return self

    def _loop(self):
        synced, pending, checked = None, None, 0.0
        while not self.stop.is_set():
            try:
                now = time.monotonic()
                mark = fingerprint(self.engine_root)
                if mark != synced:
                    if pending is None or pending[0] != mark:
                        pending = (mark, now)
                    elif now - pending[1] >= self.quiet:
                        self.last = sync(self.engine_root)
                        synced, pending, checked = mark, None, now
                elif now - checked >= self.check:
                    checked = now
                    if tampered(self.engine_root):
                        self.last = sync(self.engine_root)
                self.error = None
            except Exception as exc:  # a mirror that cannot be written never stops Kel
                self.error = type(exc).__name__ + ': ' + str(exc)[:200]
            self.stop.wait(self.poll)
