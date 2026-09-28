"""Projects as the one context boundary (D-54).

The engine is the single source of truth for which project is active. A project is `general` (the
built-in `default` row, shown as General), `user` (made or chosen by the person), or `system`
(plumbing the donor shell once created from temp/install folders). Side tables only — the
`projects`/`conversations` tables keep their positional inserts and are never altered.

Every decision about "which project does this belong to" lives here, so `service.py` and
`acp_host.py` only call in:

- `resolve_new(project, donor)` — where a new chat is created: explicit → donor binding → active
  project → General.
- `of(conversation, donor)` — which project a chat belongs to (or will, before its first message).
- `job_projects(job, conv_map)` — a job belongs to its conversation's project and to the project its
  contract names (a greenfield job shows in both).
- `scope(data, write)` — the project a Knowledge/Map/Recipes/brief/Activity call acts in.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

from .core import PolicyError, encode, uid


MIGRATION_VERSION = 32
MIGRATION_NAME = 'v2-projects'
# D-62: General gets a default folder (migration 35; 33 is schedules, 34 is Full access).
GENERAL_FOLDER_VERSION = 35
GENERAL_FOLDER_NAME = 'v2-general-folder'

GENERAL = 'default'
ALL = '*'
KINDS = ('general', 'user', 'system')
UTILITY_TITLE = 'Recipe runs'
HIDDEN_CONVERSATIONS = ('main',)
OPEN_EXCLUDED = ('CLOSED', 'CANCELLED')

DDL = """
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,root TEXT,context TEXT,updated REAL);
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,project_id TEXT,title TEXT,created REAL);
CREATE TABLE IF NOT EXISTS project_tests(project_id TEXT PRIMARY KEY,command TEXT);
CREATE TABLE IF NOT EXISTS project_meta(project_id TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'user',
    archived REAL, created REAL, utility_conversation TEXT);
CREATE TABLE IF NOT EXISTS project_prefs(scope TEXT PRIMARY KEY, value TEXT, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS project_bindings(donor_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS project_moves(conversation_id TEXT, from_project TEXT, to_project TEXT, at REAL, reason TEXT)
"""

# Tables whose rows belong to one project. A plumbing project that owns a row in any of these keeps
# it: it is only flagged and archived, never emptied (nothing is deleted by the migration).
OWNED = (
    ('memories', 'project_id=?'),
    ('memory_proposals', 'project_id=?'),
    ('memory_conflicts', 'project_id=?'),
    ('grants', 'project_id=? AND revoked=0'),
    ('project_tests', 'project_id=?'),
    ('recipes', "project_id=? AND scope='project'"),
    ('recipe_marks', 'project_id=?'),
    ('project_maps', 'project_id=?'),
    ('capability_leases', 'project_id=?'),
    ('solution_briefs', 'project_id=?'),
    ('vetting_sessions', 'project_id=?'),
    ('artifact_lineage', 'project_id=?'),
    ('context_packets', 'project_id=?'),
)

_TEMP_NAME = re.compile(r'-temp-[0-9a-z]+$', re.IGNORECASE)


def _temp_roots():
    """Folders that are never a person's project (the OS temp folder and /tmp)."""
    roots = []
    for value in (tempfile.gettempdir(), os.environ.get('TEMP'), os.environ.get('TMP'), '/tmp'):
        if value:
            try:
                roots.append(Path(value).resolve())
            except (OSError, RuntimeError, ValueError):
                continue
    return roots


def _inside(path, parent):
    return path == parent or parent in path.parents


def _table(db, name):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def plumbing_root(store, root):
    """True when `root` is a folder Kel or the shell created for itself, not a project folder."""
    if not root:
        return False
    text = str(root).replace('\\', '/').lower()
    if 'conversations/users' in text:
        return True
    try:
        path = Path(root).resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    engine = Path(store.root).resolve()
    candidates = [engine] + [engine.parent / name for name in ('engine', 'store', 'host')] + _temp_roots()
    return any(_inside(path, candidate) for candidate in candidates)


def classify(store, row):
    """general | user | system for one `projects` row (dict-like with id, name, root)."""
    if row['id'] == GENERAL:
        return 'general'
    if _TEMP_NAME.search(str(row['name'] or '')) or plumbing_root(store, row['root']):
        return 'system'
    return 'user'


def _owns(db, project_id):
    """(table, count) pairs for the project-scoped rows this project owns."""
    found = []
    for table, where in OWNED:
        if not _table(db, table):
            continue
        count = db.execute('SELECT COUNT(*) FROM %s WHERE %s' % (table, where), (project_id,)).fetchone()[0]
        if count:
            found.append((table, count))
    return found


def projects_root():
    """Where Kel creates new projects: `%USERPROFILE%/Documents/Kel Projects`, or `KEL_PROJECTS_ROOT`
    (the engine test suite and off-screen audits point it at a temporary folder)."""
    override = (os.environ.get('KEL_PROJECTS_ROOT') or '').strip()
    if override:
        return Path(os.path.expandvars(os.path.expanduser(override)))
    return Path(os.environ.get('USERPROFILE') or Path.home()) / 'Documents' / 'Kel Projects'


def default_general_root():
    """General's default folder (D-62): `%USERPROFILE%/Documents/Kel Projects/General`.

    `KEL_GENERAL_ROOT` overrides it (a path), or turns it off (`none`) — the engine test suite does
    that so no test ever creates a folder in the real Documents folder.
    """
    override = os.environ.get('KEL_GENERAL_ROOT')
    if override is not None:
        if override.strip().lower() in ('', 'none', 'off'):
            return None
        return Path(os.path.expandvars(os.path.expanduser(override.strip())))
    if (os.environ.get('KEL_PROJECTS_ROOT') or '').strip():
        return projects_root() / 'General'
    home = Path(os.environ.get('USERPROFILE') or Path.home())
    return home / 'Documents' / 'Kel Projects' / 'General'


def ensure_folder(store, root):
    """Create General's default folder the first time work needs it; return `root` unchanged.

    Only that one folder is ever created here, and only when it is still General's folder: a
    folder the person chose is theirs and is never created or touched.
    """
    default = default_general_root()
    if not root or default is None:
        return root
    try:
        if os.path.normcase(str(Path(root))) != os.path.normcase(str(default)) or Path(root).is_dir():
            return root
        with contextlib.closing(store.connect()) as db:
            row = db.execute('SELECT root FROM projects WHERE id=?', (GENERAL,)).fetchone()
        if row and row['root'] and os.path.normcase(row['root']) == os.path.normcase(str(default)):
            Path(root).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # the work that needs it says plainly that the folder cannot be used
    return root


def _general_folder(db, now):
    """Migration 35 body: give General its default folder when it has none (never replace one)."""
    default = default_general_root()
    note = {'set': False}
    if default is not None:
        row = db.execute('SELECT root FROM projects WHERE id=?', (GENERAL,)).fetchone()
        if row is None:
            db.execute('INSERT INTO projects VALUES(?,?,?,?,?)', (GENERAL, 'General', str(default), '', now))
            note['set'] = True
        elif not (row['root'] or '').strip():
            db.execute('UPDATE projects SET root=? WHERE id=?', (str(default), GENERAL))
            note['set'] = True
    db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
               (GENERAL_FOLDER_VERSION, GENERAL_FOLDER_NAME, now, json.dumps(note, sort_keys=True)))


def ensure_schema(store):
    """Migrations 32 and 35 through the ledger.

    32: side tables, then one pass over existing projects. Every project gets a meta row. A `system`
    (plumbing) project that owns nothing has its chats moved to General (each move logged in
    `project_moves`) and is archived; one that owns something is only flagged and archived. Nothing
    is deleted. The active project starts as All projects.
    35 (D-62): General gets its default folder when it has none.
    """
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                   'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL, note TEXT)')
        for statement in filter(None, (part.strip() for part in DDL.split(';'))):
            db.execute(statement)
        if not db.execute('SELECT 1 FROM schema_migrations WHERE version=?',
                          (GENERAL_FOLDER_VERSION,)).fetchone():
            _general_folder(db, time.time())
        if db.execute('SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return False
        now = time.time()
        counts = {'projects': 0, 'general': 0, 'user': 0, 'system': 0, 'archived': 0,
                  'flagged_only': 0, 'chats_moved': 0}
        general = bool(db.execute('SELECT 1 FROM projects WHERE id=?', (GENERAL,)).fetchone())
        for row in [dict(r) for r in db.execute('SELECT * FROM projects')]:
            counts['projects'] += 1
            existing = db.execute('SELECT kind FROM project_meta WHERE project_id=?', (row['id'],)).fetchone()
            kind = existing['kind'] if existing else classify(store, row)
            counts[kind] += 1
            archived = None
            if kind == 'system':
                archived = now
                counts['archived'] += 1
                if _owns(db, row['id']) or not general:
                    counts['flagged_only'] += 1
                else:
                    moved = [r['id'] for r in db.execute('SELECT id FROM conversations WHERE project_id=?',
                                                         (row['id'],))]
                    for cid in moved:
                        db.execute('INSERT INTO project_moves VALUES(?,?,?,?,?)',
                                   (cid, row['id'], GENERAL, now, 'v2-projects: plumbing project'))
                    db.execute('UPDATE conversations SET project_id=? WHERE project_id=?', (GENERAL, row['id']))
                    counts['chats_moved'] += len(moved)
            db.execute('INSERT INTO project_meta(project_id,kind,archived,created) VALUES(?,?,?,?) '
                       'ON CONFLICT(project_id) DO UPDATE SET kind=excluded.kind,'
                       'archived=COALESCE(project_meta.archived,excluded.archived)',
                       (row['id'], kind, archived, row['updated'] or now))
        db.execute('INSERT OR REPLACE INTO project_prefs VALUES(?,?,?)', ('active', ALL, now))
        db.execute('INSERT OR IGNORE INTO schema_migrations(version, name, applied, note) VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, now, json.dumps(counts, sort_keys=True)))
        return True


def job_projects(job, conv_map):
    """The projects one job belongs to: its conversation's project and its contract's project."""
    out = set()
    project = conv_map.get(job.get('conversation'))
    if project:
        out.add(project)
    named = (job.get('contract') or {}).get('project_id')
    if named:
        out.add(named)
    return out


def primary_project(job, conv_map):
    """The one project a job is shown under when a view needs a single answer."""
    return conv_map.get(job.get('conversation')) or (job.get('contract') or {}).get('project_id') or GENERAL


class Projects:
    def __init__(self, store):
        self.store = store
        # A plain read first: once migrated, constructing this per request takes no write lock.
        with contextlib.closing(store.connect()) as db:
            ready = _table(db, 'schema_migrations') and _table(db, 'project_meta') and db.execute(
                'SELECT COUNT(*) FROM schema_migrations WHERE version IN (?,?)',
                (MIGRATION_VERSION, GENERAL_FOLDER_VERSION)).fetchone()[0] == 2
        if not ready:
            ensure_schema(store)

    # -- reads ----------------------------------------------------------------------------------
    def _conv_map(self, db):
        return {r['id']: r['project_id'] for r in db.execute('SELECT id,project_id FROM conversations')}

    def _meta(self, db, rows):
        """project_id -> meta dict; rows with no meta are classified now and written (once)."""
        meta = {r['project_id']: dict(r) for r in db.execute('SELECT * FROM project_meta')}
        missing = [row for row in rows if row['id'] not in meta]
        if missing:
            # Inside a caller's transaction, write there (a second writer would wait on it).
            owner = contextlib.nullcontext(db) if db.in_transaction else self.store.transaction()
            with owner as tx:
                for row in missing:
                    kind = classify(self.store, row)
                    tx.execute('INSERT OR IGNORE INTO project_meta(project_id,kind,archived,created) VALUES(?,?,?,?)',
                               (row['id'], kind, None, row['updated'] or time.time()))
                    meta[row['id']] = {'project_id': row['id'], 'kind': kind, 'archived': None,
                                       'created': row['updated'], 'utility_conversation': None}
        return meta

    def utility_ids(self):
        with contextlib.closing(self.store.connect()) as db:
            return {r[0] for r in db.execute(
                'SELECT utility_conversation FROM project_meta WHERE utility_conversation IS NOT NULL')}

    def _rows(self, ids=None):
        with contextlib.closing(self.store.connect()) as db:
            projects = [dict(r) for r in db.execute('SELECT * FROM projects')]
            meta = self._meta(db, projects)
            tests = {r['project_id']: r['command'] for r in db.execute('SELECT project_id,command FROM project_tests')} \
                if _table(db, 'project_tests') else {}
            hidden = set(HIDDEN_CONVERSATIONS) | {m['utility_conversation'] for m in meta.values()
                                                  if m.get('utility_conversation')}
            chats = {}
            for r in db.execute('SELECT id,project_id FROM conversations'):
                if r['id'] not in hidden:
                    chats[r['project_id']] = chats.get(r['project_id'], 0) + 1
            last_message = {r['project_id']: r['at'] for r in db.execute(
                'SELECT c.project_id AS project_id, MAX(m.at) AS at FROM messages m '
                'JOIN conversations c ON c.id=m.conversation_id GROUP BY c.project_id')}
            last_created = {r['project_id']: r['at'] for r in db.execute(
                'SELECT project_id, MAX(created) AS at FROM conversations GROUP BY project_id')}
            conv_map = self._conv_map(db)
            pending = {r['job_id'] for r in db.execute("SELECT DISTINCT job_id FROM approvals WHERE status='PENDING'")}
            replaced = {r[0] for r in db.execute('SELECT replaced_job FROM handoff_restarts')} \
                if _table(db, 'handoff_restarts') else set()
        open_work, needs_you = {}, {}
        for job in self.store.list_jobs():
            if job.get('state') in OPEN_EXCLUDED or job['id'] in replaced:
                continue
            waiting = job['id'] in pending or job.get('state') == 'AWAITING_USER'
            for project in job_projects(job, conv_map):
                open_work[project] = open_work.get(project, 0) + 1
                if waiting:
                    needs_you[project] = needs_you.get(project, 0) + 1
        out = []
        for row in projects:
            if ids is not None and row['id'] not in ids:
                continue
            info = meta.get(row['id']) or {}
            try:
                command = json.loads(tests[row['id']]) if row['id'] in tests else None
            except (TypeError, ValueError):
                command = None
            root = row['root'] or None
            try:
                has_folder = bool(root) and Path(root).is_dir()
            except OSError:
                has_folder = False
            pid = row['id']
            out.append({'id': pid, 'name': row['name'], 'root': root, 'has_folder': has_folder,
                        'test_command': command, 'kind': info.get('kind') or 'user',
                        'archived': info.get('archived') or None, 'archived_at': info.get('archived') or None,
                        'conversations': chats.get(pid, 0), 'open_work': open_work.get(pid, 0),
                        'needs_you': needs_you.get(pid, 0), 'updated': row['updated'],
                        'last_active': max(v for v in (last_message.get(pid), last_created.get(pid),
                                                       row['updated'], 0) if v is not None),
                        'context': row['context'] or ''})
        return out

    def row(self, project_id):
        rows = self._rows({project_id})
        if not rows:
            raise PolicyError('That project no longer exists.')
        return rows[0]

    def list(self, include_archived=False, include_system=False):
        rows = [r for r in self._rows()
                if (include_archived or not r['archived']) and (include_system or r['kind'] != 'system')]
        rows.sort(key=lambda r: (r['kind'] != 'general', -(r['last_active'] or 0), r['name'].lower()))
        return rows

    def kinds(self):
        """project_id -> {kind, archived} for decorating other views (state)."""
        with contextlib.closing(self.store.connect()) as db:
            projects = [dict(r) for r in db.execute('SELECT * FROM projects')]
            meta = self._meta(db, projects)
        return {pid: {'kind': m.get('kind') or 'user', 'archived': m.get('archived') or None}
                for pid, m in meta.items()}

    def _info(self, db, project_id):
        """(projects row, meta row) or PolicyError when the project is gone."""
        row = db.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
        if not row:
            raise PolicyError('That project no longer exists.')
        meta = db.execute('SELECT * FROM project_meta WHERE project_id=?', (project_id,)).fetchone()
        if meta is None:
            self._meta(db, [dict(row)])
            meta = db.execute('SELECT * FROM project_meta WHERE project_id=?', (project_id,)).fetchone()
        return dict(row), dict(meta) if meta else {'kind': classify(self.store, row), 'archived': None}

    def live(self, project_id):
        """True when a project exists, is not archived and is not plumbing."""
        with contextlib.closing(self.store.connect()) as db:
            try:
                _, meta = self._info(db, project_id)
            except PolicyError:
                return False
        return not meta.get('archived') and meta.get('kind') != 'system'

    def _require_live(self, project_id, verb='use'):
        if not isinstance(project_id, str) or not project_id:
            raise PolicyError('Choose a project first.')
        with contextlib.closing(self.store.connect()) as db:
            _, meta = self._info(db, project_id)
        if meta.get('kind') == 'system':
            raise PolicyError("That folder is Kel's own working space, not a project.")
        if meta.get('archived'):
            raise PolicyError('That project is archived. Restore it in Projects to %s it.' % verb)
        return project_id

    # -- active project -------------------------------------------------------------------------
    def active(self):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute("SELECT value FROM project_prefs WHERE scope='active'").fetchone()
        value = row['value'] if row else None
        if not value or value == ALL:
            return ALL
        return value if self.live(value) else ALL

    def set_active(self, project_id):
        if project_id != ALL:
            self._require_live(project_id)
        with self.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO project_prefs VALUES(?,?,?)', ('active', project_id, time.time()))
        return {'active': project_id}

    def _drop_active(self, db, project_id):
        db.execute("UPDATE project_prefs SET value=?,updated=? WHERE scope='active' AND value=?",
                   (ALL, time.time(), project_id))

    # -- changes --------------------------------------------------------------------------------
    @staticmethod
    def _name(name):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
            raise PolicyError('A project name must be 1 to 120 characters.')
        return name.strip()

    @staticmethod
    def _root(root):
        if root in (None, ''):
            return None
        if not isinstance(root, str):
            raise PolicyError('Choose a folder for this project.')
        try:
            path = Path(os.path.expandvars(os.path.expanduser(root))).resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            raise PolicyError('That folder does not exist.') from None
        if not path.is_dir():
            raise PolicyError('Project folder is not a directory.')
        return str(path)

    @staticmethod
    def _context(context):
        if context is None:
            return ''
        if not isinstance(context, str) or len(context) > 12000:
            raise PolicyError('Project context exceeds 12000 characters.')
        return context

    @staticmethod
    def _command(command):
        if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
            raise PolicyError('Test command must be a list of arguments.')
        return command

    def create(self, name, root=None, test_command=None, context=None, project_id=None, kind='user'):
        name = self._name(name)
        root = self._root(root)
        context = self._context(context)
        command = self._command(test_command) if test_command else None
        pid = project_id or uid()
        now = time.time()
        with self.store.transaction() as db:
            if db.execute('SELECT 1 FROM projects WHERE id=?', (pid,)).fetchone():
                raise PolicyError('That project already exists.')
            db.execute('INSERT INTO projects VALUES(?,?,?,?,?)', (pid, name, root, context, now))
            db.execute('INSERT OR REPLACE INTO project_meta(project_id,kind,archived,created) VALUES(?,?,?,?)',
                       (pid, kind, None, now))
            if command:
                db.execute('INSERT OR REPLACE INTO project_tests VALUES(?,?)', (pid, encode(command)))
        return self.row(pid)

    def legacy_save(self, context, data):
        """`/api/project` without an action: the old create-or-overwrite, now recorded as a user
        project (the person chose it) when it has no meta yet."""
        pid = context.project(data['name'], data.get('root') or None, data.get('context', ''), data.get('id'))
        command = data.get('test_command')
        with self.store.transaction() as db:
            db.execute('INSERT OR IGNORE INTO project_meta(project_id,kind,archived,created) VALUES(?,?,?,?)',
                       (pid, 'general' if pid == GENERAL else 'user', None, time.time()))
            if command:
                db.execute('INSERT OR REPLACE INTO project_tests VALUES(?,?)', (pid, encode(self._command(command))))
        return {'id': pid}

    def update(self, project_id, changes):
        """Only the keys sent change. A new folder revokes remembered permissions; a null test command
        removes it. Plumbing and archived projects are not edited."""
        with contextlib.closing(self.store.connect()) as db:
            row, meta = self._info(db, project_id)
        if meta.get('kind') == 'system':
            raise PolicyError("That folder is Kel's own working space, not a project.")
        if meta.get('archived'):
            raise PolicyError('That project is archived. Restore it in Projects to change it.')
        sets, args = [], []
        if 'name' in changes:
            sets.append('name=?'); args.append(self._name(changes['name']))
        new_root = row['root']
        if 'root' in changes:
            new_root = self._root(changes['root'])
            sets.append('root=?'); args.append(new_root)
        if 'context' in changes:
            sets.append('context=?'); args.append(self._context(changes['context']))
        command = self._command(changes['test_command']) if changes.get('test_command') is not None else None
        with self.store.transaction() as db:
            if sets:
                db.execute('UPDATE projects SET %s,updated=? WHERE id=?' % ','.join(sets),
                           (*args, time.time(), project_id))
            if 'root' in changes and (new_root or None) != (row['root'] or None):
                db.execute('UPDATE grants SET revoked=1 WHERE project_id=?', (project_id,))
            if 'test_command' in changes:
                if command is None:
                    db.execute('DELETE FROM project_tests WHERE project_id=?', (project_id,))
                else:
                    db.execute('INSERT OR REPLACE INTO project_tests VALUES(?,?)', (project_id, encode(command)))
        return self.row(project_id)

    def for_folder(self, root):
        """The live project for this folder (the most recently updated one), else a new project
        named after the folder. Kel's own working folders are refused."""
        if not root:
            raise PolicyError('Choose a folder first.')
        path = self._root(root)
        if plumbing_root(self.store, path):
            raise PolicyError("That folder is Kel's own working space. Choose a folder of your own.")
        matches = [r for r in self._rows() if r['root'] and not r['archived'] and r['kind'] != 'system'
                   and os.path.normcase(r['root']) == os.path.normcase(path)]
        if matches:
            matches.sort(key=lambda r: -(r['updated'] or 0))
            return matches[0]
        return self.create(Path(path).name or path, root=path)

    def archive(self, project_id):
        if project_id == GENERAL:
            raise PolicyError('General is where chats go by default and cannot be archived.')
        with self.store.transaction() as db:
            self._info(db, project_id)
            db.execute('UPDATE project_meta SET archived=? WHERE project_id=? AND archived IS NULL',
                       (time.time(), project_id))
            db.execute('UPDATE grants SET revoked=1 WHERE project_id=?', (project_id,))
            self._drop_active(db, project_id)
        return self.row(project_id)

    def restore(self, project_id):
        with self.store.transaction() as db:
            _, meta = self._info(db, project_id)
            if meta.get('kind') == 'system':
                raise PolicyError("That folder is Kel's own working space, not a project.")
            db.execute('UPDATE project_meta SET archived=NULL WHERE project_id=?', (project_id,))
        return self.row(project_id)

    def delete(self, project_id):
        """Only an empty project can be deleted; anything with chats or saved work is archived."""
        if project_id == GENERAL:
            raise PolicyError('General cannot be deleted.')
        with self.store.transaction() as db:
            self._info(db, project_id)
            meta = db.execute('SELECT utility_conversation FROM project_meta WHERE project_id=?',
                              (project_id,)).fetchone()
            utility = meta['utility_conversation'] if meta else None
            chats = db.execute('SELECT COUNT(*) FROM conversations WHERE project_id=? AND id IS NOT ?',
                               (project_id, utility)).fetchone()[0]
            if chats:
                raise PolicyError('This project still has %d chat%s. Archive it instead.'
                                  % (chats, '' if chats == 1 else 's'))
            if utility and db.execute('SELECT 1 FROM messages WHERE conversation_id=? LIMIT 1', (utility,)).fetchone():
                raise PolicyError('This project still has Recipe runs. Archive it instead.')
            owned = [t for t, _ in _owns(db, project_id) if t not in ('project_tests', 'grants')]
            jobs = any((json.loads(r['data']).get('contract') or {}).get('project_id') == project_id
                       for r in db.execute('SELECT data FROM jobs'))
            if owned or jobs:
                raise PolicyError('This project still has saved knowledge or work. Archive it instead.')
            if utility:
                db.execute('DELETE FROM conversations WHERE id=?', (utility,))
            db.execute('DELETE FROM project_tests WHERE project_id=?', (project_id,))
            db.execute('DELETE FROM project_bindings WHERE project_id=?', (project_id,))
            db.execute('DELETE FROM project_meta WHERE project_id=?', (project_id,))
            db.execute('DELETE FROM projects WHERE id=?', (project_id,))
            self._drop_active(db, project_id)
        return {'ok': True, 'id': project_id}

    # -- chats ----------------------------------------------------------------------------------
    def bind(self, donor_id, project_id):
        """The shell's chat `donor_id` starts in `project_id` (written before it navigates, so a later
        switch of the active project cannot change where it lands). Idempotent; the last bind wins
        while the chat has no engine row. An existing chat is never moved."""
        if not isinstance(donor_id, str) or not donor_id.strip() or len(donor_id) > 200:
            raise PolicyError('Pick a chat first.')
        self._require_live(project_id)
        with self.store.transaction() as db:
            db.execute('INSERT INTO project_bindings VALUES(?,?,?) ON CONFLICT(donor_id) DO UPDATE SET '
                       'project_id=excluded.project_id', (donor_id.strip(), project_id, time.time()))
        return {'donor': donor_id.strip(), 'project_id': project_id}

    def binding(self, donor_id):
        if not donor_id:
            return None
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT project_id FROM project_bindings WHERE donor_id=?', (str(donor_id),)).fetchone()
        return row['project_id'] if row else None

    def resolve_new(self, project=None, donor=None):
        """Where a new chat is created: explicit → donor binding → active project → General."""
        if project not in (None, ''):
            return self._require_live(project, 'start a chat in')
        bound = self.binding(donor)
        if bound and self.live(bound):
            return bound
        active = self.active()
        if active != ALL:
            return active
        return GENERAL

    def _session_map(self):
        """donor id -> Kel conversation id, as the ACP host recorded it."""
        mapping = {}
        path = Path(self.store.root) / 'aion-conversations.json'
        try:
            if path.exists():
                mapping.update(json.loads(path.read_text(encoding='utf-8-sig')))
        except (OSError, ValueError):
            pass
        return mapping

    def conversation_for_donor(self, donor_id):
        if not donor_id:
            return None
        record = Path(self.store.root) / 'aion-session-map' / (hashlib.sha256(str(donor_id).encode()).hexdigest() + '.json')
        try:
            if record.exists():
                found = json.loads(record.read_text(encoding='utf-8-sig')).get(str(donor_id))
                if found:
                    return found
        except (OSError, ValueError, AttributeError):
            pass
        return self._session_map().get(str(donor_id))

    def donor_for_conversation(self, cid):
        folder = Path(self.store.root) / 'aion-session-map'
        if folder.is_dir():
            for record in folder.glob('*.json'):
                try:
                    for donor, mapped in json.loads(record.read_text(encoding='utf-8-sig')).items():
                        if mapped == cid:
                            return donor
                except (OSError, ValueError, AttributeError):
                    continue
        return next((donor for donor, mapped in self._session_map().items() if mapped == cid), None)

    def pending_project(self, cid):
        """Where a reserved (not yet created) chat will be created."""
        return self.resolve_new(None, self.donor_for_conversation(cid))

    def of(self, conversation=None, donor=None):
        cid = conversation or self.conversation_for_donor(donor)
        if cid:
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute('SELECT project_id FROM conversations WHERE id=?', (cid,)).fetchone()
            if row:
                try:
                    project = self.row(row['project_id'])
                except PolicyError:
                    project = None
                return {'project': project, 'pending': False, 'conversation': cid}
        pid = self.resolve_new(None, donor if donor else (self.donor_for_conversation(cid) if cid else None))
        return {'project': self.row(pid), 'pending': True, 'conversation': cid}

    def utility_conversation(self, project_id):
        """The hidden per-project chat Recipe runs started from the Projects page land in."""
        with self.store.transaction() as db:
            _, meta = self._info(db, project_id)
            cid = meta.get('utility_conversation')
            if cid and db.execute('SELECT 1 FROM conversations WHERE id=?', (cid,)).fetchone():
                return cid
            cid = str(uuid.uuid4())
            db.execute('INSERT INTO conversations VALUES(?,?,?,?)', (cid, project_id, UTILITY_TITLE, time.time()))
            db.execute('UPDATE project_meta SET utility_conversation=? WHERE project_id=?', (cid, project_id))
        return cid

    # -- scope ----------------------------------------------------------------------------------
    def scope(self, data, write, project_of):
        """The project one Knowledge/Map/Recipes/brief/Activity call acts in.

        `data.project`: that project (it must exist; a change needs it not archived). `'*'`: every
        project, for reads only. Otherwise the project of `data.conversation`."""
        project = data.get('project')
        if project in (None, ''):
            return project_of(data.get('conversation') or 'main')
        if project == ALL:
            if write:
                raise PolicyError('Choose a project first.')
            return ALL
        if not isinstance(project, str):
            raise PolicyError('Choose a project first.')
        with contextlib.closing(self.store.connect()) as db:
            _, meta = self._info(db, project)
        if write and meta.get('archived'):
            raise PolicyError('That project is archived. Restore it in Projects to change it.')
        return project

    def live_ids(self):
        return [r['id'] for r in self.list()]

    def names(self):
        with contextlib.closing(self.store.connect()) as db:
            return {r['id']: r['name'] for r in db.execute('SELECT id,name FROM projects')}

    # -- API ------------------------------------------------------------------------------------
    def apply(self, data):
        action = data.get('action')
        if action == 'list':
            return {'projects': self.list(include_archived=bool(data.get('include_archived')),
                                          include_system=bool(data.get('include_system'))),
                    'active': self.active()}
        if action == 'create':
            return self.create(data.get('name'), data.get('root'), data.get('test_command'), data.get('context'))
        if action == 'update':
            changes = {k: data[k] for k in ('name', 'root', 'context', 'test_command') if k in data}
            return self.update(self._id(data), changes)
        if action == 'for_folder':
            return self.for_folder(data.get('root'))
        if action == 'archive':
            return self.archive(self._id(data))
        if action == 'restore':
            return self.restore(self._id(data))
        if action == 'delete':
            return self.delete(self._id(data))
        if action == 'set_active':
            return self.set_active(data.get('id') or data.get('project') or ALL)
        if action == 'bind':
            return self.bind(data.get('donor'), data.get('project') or data.get('id'))
        if action == 'of':
            if not data.get('conversation') and not data.get('donor'):
                raise PolicyError('Pick a chat first.')
            return self.of(data.get('conversation'), data.get('donor'))
        raise PolicyError('Unknown project action')

    @staticmethod
    def _id(data):
        value = data.get('id') or data.get('project')
        if not isinstance(value, str) or not value:
            raise PolicyError('Choose a project first.')
        return value

    def create_conversation(self, context, data):
        """`/api/conversation`: `{id, project_id}` — created in `resolve_new(project, donor)`; an id
        the ACP host reserved that already has a row keeps the project it has."""
        cid = data.get('id')
        if cid is not None:
            with contextlib.closing(self.store.connect()) as db:
                row = db.execute('SELECT project_id FROM conversations WHERE id=?', (str(cid),)).fetchone()
            if row:
                return {'id': str(cid), 'project_id': row['project_id']}
        project = self.resolve_new(data.get('project'), data.get('donor'))
        created = context.conversation(project, conversation_id=cid)
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT project_id FROM conversations WHERE id=?', (created,)).fetchone()
        return {'id': created, 'project_id': row['project_id'] if row else project}


# -- '*' (All projects) reads ---------------------------------------------------------------------
MEMORY_READS = ('proposals', 'proposal', 'history', 'learnings', 'learning')
RECIPE_WRITES = ('run', 'save', 'duplicate')


def recipe_writes(data):
    """Whether a `/api/recipes` call changes something (a '*' scope refuses those)."""
    action = data.get('action')
    return action in RECIPE_WRITES or (action == 'favourites' and bool(data.get('recipe_id')))


def memory_everywhere(projects, action, data):
    """Knowledge reads across every live project; each item names its project."""
    from .memory import Memory
    memory = Memory(projects.store)
    ids = projects.live_ids()
    limit = data.get('limit')
    if action == 'proposals':
        wanted = data.get('state') or 'open'
        size = limit or 100
        items = [item for pid in ids
                 for item in memory.proposals(pid, state=None if wanted == 'all' else wanted, limit=size)]
        items.sort(key=lambda item: -(item.get('updated') or 0))
        return {'proposals': items[:size]}
    if action == 'proposal':
        return memory.proposal(data.get('id'))
    if action == 'history':
        size = limit or 50
        entries = [dict(entry, project_id=pid) for pid in ids for entry in memory.history_view(pid, limit=size)]
        entries.sort(key=lambda entry: -(entry.get('at') or 0))
        return {'entries': entries[:size]}
    if action == 'learnings':
        from .learning import learnings_view
        return {'learnings': [dict(item, project_id=pid) for pid in ids
                              for item in learnings_view(projects.store, project_id=pid,
                                                         include_stale=bool(data.get('include_stale')),
                                                         include_disabled=bool(data.get('include_disabled')))]}
    if action == 'learning':
        from .learning import explain_learning
        return explain_learning(projects.store, data.get('id'))
    raise PolicyError('Choose a project first.')


def recipes_everywhere(projects, query=None):
    """Built-in recipes plus each live project's own recipes, labelled with their project."""
    from .recipes import RecipeLibrary
    library = RecipeLibrary(projects.store)
    names = projects.names()
    if query is not None:
        items = library.search('', query)
    else:
        items = library.entries(project_id='')
    out = [item for item in items if item['scope'] == 'builtin']
    for pid in projects.live_ids():
        found = library.search(pid, query) if query is not None else library.entries(project_id=pid)
        out.extend(dict(item, project_id=pid, project_name=names.get(pid)) for item in found
                   if item['scope'] == 'project')
    return out
