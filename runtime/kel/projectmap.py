"""Durable project map: deterministic inspection, bounded synthesis, versioned snapshots.

V1.3 migration 002 (docs/v1.3/KEL_V1.3_ARCHITECTURE.md 2-4): project_maps + context_packets.
Deterministic inspection runs first; optional bounded synthesis (a caller-provided
`synthesizer`) may add prose summaries that are always labeled `inferred`.
"""
import contextlib
import hashlib
import json
import subprocess
import time
from pathlib import Path

from .core import PolicyError
from .memory import _backup, _is_fresh_database, _table

MIGRATION_VERSION = 2
MIGRATION_NAME = 'v13-projectmap'

DDL = """
CREATE TABLE IF NOT EXISTS project_maps(
    project_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    fingerprint TEXT NOT NULL,
    data TEXT NOT NULL,
    updated REAL NOT NULL,
    note TEXT,
    PRIMARY KEY(project_id, version));
CREATE TABLE IF NOT EXISTS context_packets(
    packet_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    job_id TEXT,
    conversation_id TEXT,
    purpose TEXT NOT NULL,
    data TEXT NOT NULL,
    created REAL NOT NULL);
"""

KEY_FILES = ('package.json', 'bun.lock', 'bun.lockb', 'pnpm-lock.yaml', 'package-lock.json',
             'yarn.lock', 'pyproject.toml', 'setup.py', 'requirements.txt', 'Cargo.toml',
             'go.mod', 'Makefile', 'justfile', 'tsconfig.json')
SECTIONS = ('identity', 'execution', 'architecture', 'conventions', 'state')


def ensure_schema(store):
    """Create migration 002 tables (idempotent; a v1.2 database is backed up once)."""
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'schema_migrations') and db.execute(
                'SELECT 1 FROM schema_migrations WHERE version=?', (MIGRATION_VERSION,)).fetchone():
            return
        first = not _table(db, 'schema_migrations')
        if first:
            if not _is_fresh_database(db):
                _backup(store, db)  # one-time pre-V1.3 backup before the first V1.3 mutation
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations('
                       'version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied REAL NOT NULL,'
                       ' note TEXT)')
        db.executescript(DDL)
        db.execute('INSERT OR IGNORE INTO schema_migrations VALUES(?,?,?,?)',
                   (MIGRATION_VERSION, MIGRATION_NAME, time.time(), None))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(root, *args):
    try:
        out = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True,
                             timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _key_digests(root):
    digests = {}
    for name in KEY_FILES:
        path = root / name
        if path.is_file():
            digests[name] = _sha(path)
    return digests


def section_inputs(root, name):
    """Cheap change-detection inputs for one section (used before any content work)."""
    if name == 'identity':
        head = _git(root, 'rev-parse', '--short', 'HEAD')
        dirty = bool(_git(root, 'status', '--porcelain')) if head is not None else False
        return {'git': (head or 'none') + ('+dirty' if dirty else '')}
    if name == 'execution':
        inputs = {}
        for extra in ('package.json', 'bun.lock', 'bun.lockb', 'tsconfig.json', 'Makefile'):
            path = root / extra
            if path.is_file():
                inputs[extra] = _sha(path)
        return inputs
    if name == 'architecture':
        top = sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith('.'))
        inputs = {'listing': hashlib.sha256('|'.join(top).encode()).hexdigest()}
        package = root / 'package.json'
        if package.is_file():
            inputs['package.json'] = _sha(package)
        return inputs
    if name == 'conventions':
        listing = [x for x in ('src', 'kel', 'lib', 'runtime', 'tests', 'test', 'e2e')
                   if (root / x).is_dir()]
        return {'listing': hashlib.sha256('|'.join(listing).encode()).hexdigest()}
    return None  # 'state' has no cheap probe; recompute on every refresh that runs


def fingerprint(root):
    """Git tree digest plus key-file digests (or a key-file bundle for non-git trees)."""
    parts = []
    tree = _git(root, 'rev-parse', 'HEAD^{tree}')
    if tree:
        parts.append('git:' + tree)
    digests = _key_digests(root)
    if digests:
        bundle = json.dumps(digests, sort_keys=True).encode()
        parts.append('files:' + hashlib.sha256(bundle).hexdigest()[:32])
    return '|'.join(parts) if parts else 'empty'


def _inspect_identity(root, project):
    head = _git(root, 'rev-parse', '--short', 'HEAD')
    repo = None
    if head is not None:
        repo = {'branch': _git(root, 'rev-parse', '--abbrev-ref', 'HEAD') or '',
                'head': head,
                'dirty': bool(_git(root, 'status', '--porcelain'))}
    languages = []
    if (root / 'package.json').is_file():
        languages.append('javascript/typescript')
    if (root / 'pyproject.toml').is_file() or (root / 'setup.py').is_file() or \
            (root / 'kel').is_dir():
        languages.append('python')
    content = {'name': project['name'], 'root': str(root), 'repo': repo, 'languages': languages}
    inputs = section_inputs(root, 'identity')
    sources = ['git'] if repo else []
    return content, inputs, sources


def _inspect_execution(root):
    commands = {}
    sources = []
    inputs = section_inputs(root, 'execution')
    package = root / 'package.json'
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding='utf-8-sig'))
        except ValueError:
            data = None
        if isinstance(data, dict):
            scripts = data.get('scripts') if isinstance(data.get('scripts'), dict) else {}
            runner = 'bun run'
            if not ((root / 'bun.lock').exists() or (root / 'bun.lockb').exists()):
                if (root / 'pnpm-lock.yaml').exists():
                    runner = 'pnpm run'
                elif (root / 'yarn.lock').exists():
                    runner = 'yarn'
                elif (root / 'package-lock.json').exists():
                    runner = 'npm run'
            for key in ('dev', 'start', 'build', 'test', 'lint', 'typecheck', 'type-check',
                        'package', 'dist'):
                if isinstance(scripts.get(key), str):
                    commands[key] = runner + ' ' + key
            sources.append('package.json')
    tests = root / 'tests'
    if tests.is_dir() and any(tests.glob('test_*.py')) and 'test' not in commands:
        commands['test'] = 'python -m pytest tests/ -q'
        sources.append('tests/')
    for extra in ('bun.lock', 'tsconfig.json', 'Makefile'):
        if (root / extra).is_file():
            sources.append(extra)
    return {'commands': commands}, inputs, sources
def _inspect_architecture(root):
    entries = [name for name in ('main.py', 'app.py', 'kel/__main__.py', 'src/index.ts',
                                 'src/main.ts', 'src/index.js', 'index.js')
               if (root / name).is_file()]
    top = sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith('.'))
    packages = [name for name in top if (root / name / '__init__.py').is_file()][:8]
    ui = [name for name in ('src/renderer', 'renderer', 'frontend', 'ui', 'app')
          if (root / name).is_dir()]
    services = [name for name in ('src/process/services', 'services', 'server', 'runtime')
                if (root / name).is_dir()]
    storage = [name for name in ('data', 'storage', 'db') if (root / name).is_dir()]
    dependencies = []
    inputs = section_inputs(root, 'architecture')
    package = root / 'package.json'
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding='utf-8-sig'))
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get('dependencies'), dict):
            dependencies = sorted(data['dependencies'].keys())[:10]
    content = {'entry_points': entries, 'packages': packages, 'top_level': top[:12],
               'ui': ui, 'services': services, 'storage': storage,
               'key_dependencies': dependencies}
    return content, inputs, ['directory listing']


def _inspect_conventions(root):
    source_dirs = [name for name in ('src', 'kel', 'lib', 'runtime') if (root / name).is_dir()]
    test_dirs = [name for name in ('tests', 'test', 'e2e') if (root / name).is_dir()]
    guardrails = [name for name in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md',
                                    'CONTRIBUTING.md', 'AGENTS.md') if (root / name).is_file()]
    listing = '|'.join(source_dirs + test_dirs)
    content = {'source_locations': source_dirs, 'test_locations': test_dirs,
               'guardrails': guardrails}
    return content, section_inputs(root, 'conventions'), ['directory listing']


def _inspect_state(store, project_id):
    content = {'decisions': [], 'active_work': [], 'open_conflicts': 0, 'recent_changes': []}
    with contextlib.closing(store.connect()) as db:
        if _table(db, 'memories'):
            content['decisions'] = [dict(r) for r in db.execute(
                "SELECT id, topic, summary FROM memories WHERE project_id=? AND type='decision'"
                " AND status='active' ORDER BY trust ASC, updated DESC LIMIT 3", (project_id,))]
        if _table(db, 'memory_conflicts'):
            content['open_conflicts'] = db.execute(
                "SELECT count(*) FROM memory_conflicts WHERE project_id=? AND state='open'",
                (project_id,)).fetchone()[0]
        if _table(db, 'jobs'):
            conversations = {r['id'] for r in db.execute(
                'SELECT id FROM conversations WHERE project_id=?', (project_id,))} \
                if _table(db, 'conversations') else set()
            active = []
            for row in db.execute('SELECT data FROM jobs ORDER BY rowid DESC LIMIT 50'):
                job = json.loads(row['data'])
                if job.get('state') not in ('CLOSED', 'CANCELLED') and \
                        (not conversations or job.get('conversation') in conversations):
                    active.append({'id': job['id'], 'state': job.get('state')})
            content['active_work'] = active[:5]
    return content, {}, ['jobs', 'memories']


class ProjectMap:
    """Versioned project map store. Never rescans the whole repository unnecessarily."""

    def __init__(self, store, synthesizer=None):
        self.store = store
        self.synthesizer = synthesizer
        ensure_schema(store)

    def _project(self, project_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
        if not row:
            raise PolicyError('Project missing')
        return dict(row)

    def get(self, project_id):
        with contextlib.closing(self.store.connect()) as db:
            row = db.execute(
                'SELECT * FROM project_maps WHERE project_id=? ORDER BY version DESC LIMIT 1',
                (project_id,)).fetchone()
        if not row:
            return None
        data = json.loads(row['data'])
        return {'project_id': project_id, 'version': row['version'],
                'fingerprint': row['fingerprint'], 'updated': row['updated'],
                'note': row['note'], 'sections': data['sections']}

    def _compute(self, project, project_id, name):
        root = Path(project['root'])
        if name == 'identity':
            return _inspect_identity(root, project)
        if name == 'execution':
            return _inspect_execution(root)
        if name == 'architecture':
            return _inspect_architecture(root)
        if name == 'conventions':
            return _inspect_conventions(root)
        return _inspect_state(self.store, project_id)

    def refresh(self, project_id, *, force=False, reason='manual'):
        project = self._project(project_id)
        if not project.get('root'):
            raise PolicyError('Project has no root to inspect')
        root = Path(project['root'])
        if not root.is_dir():
            raise PolicyError('Project root is not readable')
        mark = fingerprint(root)
        latest = self.get(project_id)
        if latest and not force and latest['fingerprint'] == mark:
            unchanged = dict(latest)
            unchanged['note'] = 'unchanged (%s)' % reason
            return unchanged
        sections = {}
        changed = []
        for name in SECTIONS:
            previous = latest['sections'].get(name) if latest else None
            probe = section_inputs(root, name) if name != 'state' else None
            if previous and not force and probe is not None and previous.get('inputs') == probe:
                sections[name] = dict(previous)
                sections[name]['stale'] = False  # copied forward with its digests
                continue
            content, inputs, sources = self._compute(project, project_id, name)
            digest = hashlib.sha256(
                json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()[:32]
            section = {'content': content, 'inputs': inputs, 'sources': sources,
                       'digest': digest, 'updated': time.time(), 'trust': 'verified',
                       'stale': False}
            if name in ('architecture', 'conventions') and self.synthesizer:
                try:
                    summary = self.synthesizer(name, content)
                except Exception:
                    summary = None
                if isinstance(summary, str) and summary.strip():
                    section['summary'] = summary.strip()[:1200]
                    section['trust'] = 'inferred'
            sections[name] = section
            changed.append(name)
        version = (latest['version'] + 1) if latest else 1
        note = reason + ((' changed: ' + ','.join(changed)) if changed else ' copied forward')
        with self.store.transaction() as db:
            db.execute('INSERT INTO project_maps VALUES(?,?,?,?,?,?)',
                       (project_id, version, mark,
                        json.dumps({'sections': sections}, sort_keys=True, default=str),
                        time.time(), note))
        result = self.get(project_id)
        result['note'] = note
        return result

    def stale_sections(self, project_id, changed_paths):
        """Which sections a set of changed source paths would invalidate."""
        latest = self.get(project_id)
        if not latest:
            raise PolicyError('No project map yet')
        names = set(changed_paths)
        stale = []
        for name, section in latest['sections'].items():
            refs = set(section.get('inputs', {})) | set(section.get('sources', []))
            if refs & names:
                stale.append(name)
        return sorted(set(stale))
