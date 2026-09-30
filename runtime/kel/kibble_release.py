"""Explicit Kibble candidate builds. Never launches an installer or changes App/Data.

SQLite owns stage facts; the candidate owns a bounded build log and manifest.
Builds serialize because the canonical checkout shares desktop/out and dist/runtime.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time

from .core import PolicyError

ACTIVE = ('QUEUED', 'BUILDING_ENGINE', 'BUILDING_DESKTOP', 'PACKAGING')
BUILD_TIMEOUT = 30 * 60
_build_lock = threading.Lock()
_LOADED_AT = time.time()


def ensure(store):
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS kibble_releases('
                   'fix_id TEXT PRIMARY KEY, release_id TEXT NOT NULL, data TEXT NOT NULL)')


def _get(store, fix_id):
    with contextlib.closing(store.connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='kibble_releases'").fetchone():
            return None
        row = db.execute('SELECT data FROM kibble_releases WHERE fix_id=?', (fix_id,)).fetchone()
    return json.loads(row['data']) if row else None


def _save(store, fix_id, release_id, **changes):
    with store.transaction() as db:
        row = db.execute('SELECT data,release_id FROM kibble_releases WHERE fix_id=?', (fix_id,)).fetchone()
        if not row or row['release_id'] != release_id:
            raise PolicyError('A newer build owns this finding.')
        data = json.loads(row['data'])
        data.update(changes, updated=time.time())
        db.execute('UPDATE kibble_releases SET data=? WHERE fix_id=?', (json.dumps(data), fix_id))
    return data


def _owner_alive(data):
    from .runner import process_identity
    identity = data.get('owner')
    return bool(identity and process_identity(data.get('pid')) == identity)


def status(store, fix_id):
    data = _get(store, fix_id)
    if not data:
        return None
    if data['state'] in ACTIVE and not _owner_alive(data):
        data.update(state='INTERRUPTED', stage='Build interrupted',
                    error='Kel closed before this build finished. Build it again.')
    path = Path(data['candidate_path']) / 'build.log'
    try:
        # Read only a bounded tail, even when a tool produced a large log.
        with path.open('rb') as log:
            log.seek(0, 2)
            log.seek(max(0, log.tell() - 16000))
            lines = log.read().decode('utf-8', errors='replace').splitlines()
        data['log'] = lines[-60:]
    except OSError:
        data['log'] = []
    # READY means packaged, never installed. Opening an installer is a separate user action.
    data['installed'] = _installed(data)
    return data


def _installed(data):
    """The active packaged engine must come from canonical App with this release marker."""
    app = Path(data['source_root']).parent / 'App'
    engine = app / 'resources/kel-engine/KelEngine.exe'
    if (not getattr(sys, 'frozen', False) or Path(sys.executable).resolve() != engine.resolve()
            or not _launched_after(data['created'])):
        return False
    try:
        marker = json.loads((app / 'resources/kibble-installed-update.json').read_text(encoding='utf-8'))
        return (data['state'] == 'READY' and marker.get('release_id') == data['release_id']
                and marker.get('source_fingerprint') == data['source_fingerprint'])
    except (OSError, ValueError):
        return False


def _launched_after(created):
    if os.name == 'nt':
        from .runner import process_identity
        identity = process_identity(os.getpid())
        return bool(identity and int(identity) / 10000000 - 11644473600 > created)
    return _LOADED_AT > created


def _git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                            timeout=30, check=False)
    if result.returncode:
        raise PolicyError('Kel could not read its source history. The build did not start.')
    return result.stdout


def fingerprint(root):
    """HEAD and all tracked/non-ignored files; catches edits, deletions, and new source files."""
    root = Path(root).resolve()
    sha = _git(root, 'rev-parse', 'HEAD').decode().strip()
    files = sorted(set(_git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')))
    digest = hashlib.sha256(sha.encode())
    for raw in files:
        if not raw:
            continue
        relative = os.fsdecode(raw)
        path = root / relative
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            raise PolicyError('A linked source file cannot own a Kel update.')
        digest.update(raw + b'\0')
        try:
            with path.open('rb') as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b''):
                    digest.update(block)
        except FileNotFoundError:
            digest.update(b'<deleted>')
        digest.update(b'\0')
    return sha, digest.hexdigest()


def _checked_root(service, fix_id):
    from .kibble_work import progress, source_root
    from .auto_apply import describe
    work = progress(service.store, fix_id)
    if not work or not work.get('job_id'):
        raise PolicyError('Kel has no checked source change for this finding yet.')
    job = service.store.get(work['job_id'])
    if (job.get('contract', {}).get('context', {}).get('kibble') or {}).get('fix_id') != fix_id:
        raise PolicyError('This source change does not belong to this finding.')
    app = describe(service.store, [job['id']]).get(job['id']) or {}
    if job.get('verdict') != 'VERIFIED' or app.get('state') != 'APPLIED' or app.get('auto'):
        raise PolicyError('Apply the verified source change before building the update.')
    root = source_root(service.store)
    if Path(job['contract']['root']).resolve() != root or Path(app.get('root') or '').resolve() != root:
        raise PolicyError('The checked change points to a different source folder.')
    # An applied finding cannot build after somebody changed its exact repaired files.
    from .apply_changes import application
    from .core import digest
    journal = application(service.store, job['id']) or {}
    for name, change in (journal.get('plan') or {}).get('changes', {}).items():
        target = root / name
        if not target.resolve().is_relative_to(root):
            raise PolicyError('A checked source path left Kel source.')
        actual = digest(target.read_bytes()) if target.is_file() else None
        if actual != change.get('after'):
            raise PolicyError('The repaired source changed after Apply. Check it again before building.')
    return root, job['id']


def start(service, fix_id):
    """Return persisted progress immediately; run build commands on a background thread."""
    ensure(service.store)
    with service.handoff_lock:
        previous = status(service.store, fix_id)
        if previous and previous['state'] in ACTIVE:
            return previous
        root, job_id = _checked_root(service, fix_id)
        sha, stamp = fingerprint(root)
        if previous and previous['state'] == 'READY' and previous['source_fingerprint'] == stamp:
            return previous
        # The explicit output root is beside canonical source, never in installed App or Data.
        parent = root.parent
        temp = parent / 'Temp'
        if temp.resolve() != temp.absolute():
            raise PolicyError('Kel cannot build into a linked temporary folder.')
        temp.mkdir(exist_ok=True)
        release_id = secrets.token_hex(6)
        candidate = temp / ('Candidate-' + release_id)
        candidate.mkdir()
        from .runner import process_identity
        data = {'release_id': release_id, 'fix_id': fix_id, 'job_id': job_id,
                'state': 'QUEUED', 'stage': 'Waiting to build', 'error': None,
                'candidate_path': str(candidate), 'installer_path': None,
                'source_root': str(root), 'source_sha': sha, 'source_fingerprint': stamp,
                'created': time.time(), 'updated': time.time(), 'pid': os.getpid(),
                'owner': process_identity(os.getpid()), 'installed': False}
        with service.store.transaction() as db:
            db.execute('INSERT OR REPLACE INTO kibble_releases VALUES(?,?,?)',
                       (fix_id, release_id, json.dumps(data)))
        _launch(service.store, fix_id, release_id)
        return status(service.store, fix_id)


def _launch(store, fix_id, release_id):
    threading.Thread(target=_build, args=(store, fix_id, release_id),
                     name='kel-kibble-release', daemon=True).start()


def _run(command, cwd, log):
    # Build tools do not need provider keys. Keep their stdout away from credential custody.
    env = {k: v for k, v in os.environ.items() if not
           any(token in k.upper() for token in ('API_KEY', 'ACCESS_TOKEN', 'CLIENT_SECRET', 'MUSE_KEY'))}
    from .containment import SECRET_SHAPE
    env = {k: v for k, v in env.items() if not SECRET_SHAPE.search(k)}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['CSC_IDENTITY_AUTO_DISCOVERY'] = 'false'
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    if os.name == 'nt':
        # A dedicated lifetime group kills only this build's descendants on timeout/engine exit.
        runtime = cwd if (cwd / 'kel/windows_job.py').is_file() else cwd.parent / 'runtime'
        env['PYTHONPATH'] = str(runtime)
        wrapper = ('from kel.windows_job import contain_current_process; import subprocess,sys; '
                   'group=contain_current_process(); process=subprocess.Popen(sys.argv[1:]); '
                   'sys.exit(process.wait())')
        command = ['python', '-c', wrapper, *command]
    with log.open('ab') as output:
        result = subprocess.run(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                timeout=BUILD_TIMEOUT, check=False, env=env, creationflags=flags)
    if result.returncode:
        raise PolicyError('The build tool stopped with code %d. Open the build log.' % result.returncode)


def _config(root, candidate):
    # Extending the canonical configuration preserves Kel identity and NSIS policy.
    # Explicit resources include the runtime pieces prior installs retained separately.
    resources = [{'from': str(candidate / 'kibble-installed-update.json'), 'to': 'kibble-installed-update.json'},
                 {'from': str(root / 'dist/runtime/KelEngine'), 'to': 'kel-engine'},
                 {'from': str(root / 'desktop/LICENSE'), 'to': 'AionUI-LICENSE.txt'},
                 {'from': str(root / 'desktop/resources/bundled-aioncore'), 'to': 'bundled-aioncore'},
                 {'from': str(root / 'desktop/resources/hub'), 'to': 'hub'},
                 {'from': str(root / 'desktop/public'), 'to': '.'},
                 {'from': str(root / 'desktop/resources/app.png'), 'to': 'app.png'}]
    config = {'extends': str(root / 'desktop/kel-builder.json'),
              'directories': {'output': str(candidate), 'app': str(root / 'desktop'),
                              'buildResources': str(root / 'desktop/resources')},
              'extraResources': resources, 'publish': None,
              'win': {'target': ['nsis'], 'signAndEditExecutable': False},
              'nsis': {'artifactName': 'Kel-Kibble-Update-${version}-${arch}.${ext}'}}
    path = candidate / 'builder-config.json'
    path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return path


def _build(store, fix_id, release_id):
    try:
        with _build_lock, contextlib.ExitStack() as cleanup:
            data = _get(store, fix_id)
            if not data or data['release_id'] != release_id:
                return
            root = Path(data['source_root'])
            candidate = Path(data['candidate_path'])
            log = candidate / 'build.log'
            from .instance_lock import InstanceLock
            from .core import Conflict
            lock_root = candidate.parent / '.kibble-build-lock'
            lock_root.mkdir(exist_ok=True)
            try:
                build_lock = InstanceLock(lock_root)
            except Conflict:
                raise PolicyError('Another Kel update is building. Wait for it to finish, then build again.') from None
            cleanup.callback(build_lock.close)
            if fingerprint(root)[1] != data['source_fingerprint']:
                raise PolicyError('Kel source changed while this build waited. Build it again.')
            _save(store, fix_id, release_id, state='BUILDING_ENGINE', stage='Building Kel engine')
            _run(['python', '-m', 'PyInstaller', '--noconfirm', '--clean',
                  '--distpath', str(root / 'dist/runtime'), '--workpath', str(root / 'dist/pyinstaller-work'),
                  'KelEngine.spec'], root / 'runtime', log)
            _save(store, fix_id, release_id, state='BUILDING_DESKTOP', stage='Building Kel interface')
            # --pack-only returns before the legacy packager's process cleanup/kill branches.
            _run(['node', 'scripts/build-with-builder.js', '--pack-only', '--force'], root / 'desktop', log)
            _save(store, fix_id, release_id, state='PACKAGING', stage='Preparing update installer')
            marker = {k: data[k] for k in ('release_id', 'source_fingerprint', 'fix_id', 'job_id')}
            (candidate / 'kibble-installed-update.json').write_text(json.dumps(marker, indent=2), encoding='utf-8')
            config = _config(root, candidate)
            # Direct CLI argument array avoids the wrapper's shell interpolation and process killing.
            _run(['node', 'node_modules/electron-builder/cli.js', '--config', str(config),
                  '--win', 'nsis', '--x64', '--publish', 'never'], root / 'desktop', log)
            if fingerprint(root)[1] != data['source_fingerprint']:
                raise PolicyError('Kel source changed during the build. This candidate is not ready.')
            installers = list(candidate.glob('Kel-Kibble-Update-*.exe'))
            required = [candidate / 'win-unpacked/Kel.exe',
                        candidate / 'win-unpacked/resources/app.asar',
                        candidate / 'win-unpacked/resources/kel-engine/KelEngine.exe']
            if len(installers) != 1 or not all(p.is_file() for p in required):
                raise PolicyError('The build did not produce a complete Kel candidate and installer.')
            installer = installers[0]
            with installer.open('rb') as artifact:
                digest = hashlib.file_digest(artifact, 'sha256').hexdigest()
            manifest = {k: data[k] for k in ('release_id', 'fix_id', 'job_id', 'source_sha', 'source_fingerprint')}
            manifest.update(installer_sha256=digest, installed=False, built_at=time.time())
            (candidate / 'kibble-candidate.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            _save(store, fix_id, release_id, state='READY', stage='Update installer ready',
                  installer_path=str(installer), installer_sha256=digest, error=None)
    except Exception as exc:
        note = str(exc) if isinstance(exc, PolicyError) else 'Kel could not finish this build (%s). Open the log.' % type(exc).__name__
        _save(store, fix_id, release_id, state='FAILED', stage='Build stopped', error=note)
