"""D-81: the Memory folder is the agents' world.

The intended agent boundary is Memory plus each run's assigned working copy and temporary folder.
Claude uses a tool guard. Codex confines writes, and its stronger Windows mode adds partial read
denials. Neither implementation establishes complete OS read confinement to Memory.

Layout:
- `Memory\\Projects\\` — where Kel creates every NEW project (existing projects stay where they are).
- `Memory\\Kel\\`      — a read-only mirror Kel keeps current for the agents (`kel.memory_mirror`):
  settings without secrets, every chat as a markdown file, and project knowledge.

Where it is: `KEL_MEMORY_ROOT` when set (tests and audits point it at scratch; the desktop passes the
installed location), else `<the folder holding the installed App>\\Memory` (for Nick:
`Desktop\\Kel\\Memory`), else beside Kel's Data folder. Created on demand.

What a worker may still READ outside Memory (tools must run): see `system_readable_roots`.
"""
import os
from pathlib import Path

REFUSAL = "That's outside Kel's Memory folder, so I can't touch it."
MIRROR_REFUSAL = ("Memory\\Kel is Kel's own read-only copy of its settings, chats and notes, "
                  "so I can't change it.")
ENV = 'KEL_MEMORY_ROOT'
PROJECTS = 'Projects'
MIRROR = 'Kel'


def _expand(value):
    return Path(os.path.expandvars(os.path.expanduser(value.strip())))


def _data_dir(engine_root=None):
    """Kel's Data folder (the one holding engine/store/host), when it can be told."""
    candidates = []
    if engine_root:
        candidates.append(Path(engine_root))
    if os.environ.get('KEL_DATA_DIR'):
        candidates.append(Path(os.environ['KEL_DATA_DIR']))
    for engine in candidates:
        engine = Path(os.path.abspath(engine))
        if engine.name.lower() == 'engine':
            return engine.parent
        if (engine / 'engine').is_dir():
            return engine
    return None


def memory_root(engine_root=None):
    """The Memory folder (not created here; see `ensure`)."""
    override = (os.environ.get(ENV) or '').strip()
    if override:
        return Path(os.path.abspath(_expand(override)))
    from .containment import app_roots
    for app in app_roots():
        return Path(app).parent / 'Memory'
    data = _data_dir(engine_root)
    if data is not None:
        return data.parent / 'Memory'
    if engine_root:
        return Path(os.path.abspath(engine_root)).parent / 'Memory'
    return Path(os.environ.get('USERPROFILE') or Path.home()) / 'Kel' / 'Memory'


def projects_dir(engine_root=None):
    return memory_root(engine_root) / PROJECTS


def mirror_dir(engine_root=None):
    return memory_root(engine_root) / MIRROR


def ensure(engine_root=None):
    """Create Memory, Memory\\Projects and Memory\\Kel on demand; return the Memory folder."""
    root = memory_root(engine_root)
    for path in (root, root / PROJECTS, root / MIRROR):
        path.mkdir(parents=True, exist_ok=True)
    return root


def _norm(path):
    try:
        return Path(path).resolve()
    except OSError:
        return Path(os.path.abspath(path))


def inside(target, root):
    if not root:
        return False
    target, root = _norm(target), _norm(root)
    return target == root or target.is_relative_to(root)


def in_memory(path, engine_root=None):
    return inside(path, memory_root(engine_root))


def in_mirror(path, engine_root=None):
    return inside(path, mirror_dir(engine_root))


def neighbours(engine_root=None):
    """Kel's own folders next to Memory (App, Data, Kel source, Tools, ...): every existing sibling of
    the Memory folder. Off-limits; named in Claude Code's deny rules."""
    root = _norm(memory_root(engine_root))
    parent = root.parent
    out = []
    if parent == root or not parent.is_dir():
        return out
    # Only when Memory sits in a Kel folder (it has Kel's App or Data beside it) — never a whole
    # Desktop or home folder that happens to hold a Memory folder.
    names = {p.name.lower() for p in parent.iterdir() if p.is_dir()}
    if not ({'app', 'data'} & names):
        return out
    for child in parent.iterdir():
        if child.is_dir() and _norm(child) != root:
            out.append(_norm(child))
    return out


# Git for Windows mounts these POSIX paths inside its own install folder (read-only for work).
POSIX_SYSTEM = ('/usr', '/bin', '/etc', '/mingw64', '/mingw32', '/dev', '/proc', '/tmp', '/opt', '/lib')


def system_readable_roots(engine_root=None, extra=()):
    """What a worker may read (never write) outside Memory and its working copy, so the CLIs and the
    tools they call can run. Returned as [(path, why)]:

    - `%SystemRoot%` (C:\\Windows): the shells (cmd, Windows PowerShell) and system libraries;
    - `%ProgramFiles%`, `%ProgramFiles(x86)%`, `%ProgramW6432%`: installed tools (Git and its bash,
      Node.js, PowerShell 7, ...);
    - every folder on PATH (the tools a command names: python, node, npm, git, the CLIs themselves),
      except a PATH folder inside a place that is off-limits (Kel's Data, App, source, Tools, a
      credential folder);
    - the CLI executables' own install folders (`extra`, e.g. Claude Code's and Codex's folders).

    Writes outside Memory, the working copy and the run's own temp folder are refused everywhere.
    """
    roots, seen = [], set()

    def add(path, why):
        if not path:
            return
        p = _norm(path)
        key = str(p).lower()
        if key in seen or not p.is_absolute():
            return
        seen.add(key)
        roots.append((p, why))

    for key in ('SystemRoot', 'WINDIR'):
        add(os.environ.get(key), 'Windows system folder')
    for key in ('ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432'):
        add(os.environ.get(key), 'installed programs')
    blocked = [_norm(p) for p in neighbours(engine_root)]
    from .containment import _credential_roots, _protected_roots, app_roots, data_roots
    blocked += [_norm(p) for p in _credential_roots() + _protected_roots() + app_roots() + data_roots()]
    home = _norm(os.environ.get('USERPROFILE') or Path.home())
    for part in (os.environ.get('PATH') or '').split(os.pathsep):
        part = part.strip().strip('"')
        if not part or not os.path.isabs(part):
            continue
        p = _norm(part)
        # Never the home folder, a folder above it or a drive root (that would open everything), nor a
        # folder inside an off-limits place.
        if home.is_relative_to(p) or p.parent == p or any(p == b or p.is_relative_to(b) for b in blocked):
            continue
        add(p, 'a tool folder on PATH')
    for path in extra:
        add(path, "the AI tool's own install folder")
    return roots


# ---- Codex's stronger Windows sandbox (one Windows admin approval) ---------------------------------
#
# Codex 0.157.1 has two Windows sandboxes. Kel starts in the restricted-token one ("unelevated", no
# admin): writes are confined to the working copy and Memory, reads are not. The "elevated" one runs
# commands as Codex's own sandbox users (CodexSandboxOffline/Online), so Windows itself refuses reads
# Kel denies (`runtime_guard.codex_deny_paths`). It needs a one-time setup that Windows asks an
# administrator to approve (a UAC prompt for OpenAI's codex-windows-sandbox-setup.exe). Kel switches
# to it only after `codex_sandbox_setup` succeeds, and checks Codex's readiness before every elevated
# run (a Codex update can require the setup again): if it is not ready, that run stops without
# downgrading or surprising the person with an admin prompt. Read denials remain partial.

STATE_DIR = 'memory-mirror'  # in the engine root; listed in runtime_guard._ENGINE_DIRS
CODEX_STATE = 'codex-sandbox.json'
SETUP_TIMEOUT = 600  # seconds: the person may take a while to answer Windows' prompt


def _codex_state_file(engine_root):
    return Path(engine_root) / STATE_DIR / CODEX_STATE


def codex_state(engine_root):
    import json
    try:
        data = json.loads(_codex_state_file(engine_root).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_codex_state(engine_root, **changes):
    import json
    import time
    data = codex_state(engine_root)
    data.update(changes, at=time.time())
    path = _codex_state_file(engine_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding='utf-8')
    return data


def codex_elevated(engine_root):
    """True when Kel runs Codex in its elevated Windows sandbox (after the one-time approval)."""
    return os.name == 'nt' and codex_state(engine_root).get('mode') == 'elevated'


def _codex_readiness(status):
    if status == 'ready':
        return 'ready'
    if not isinstance(status, str) or not status or status in ('unknown', 'not_checked'):
        return 'unknown'
    return 'not_ready'


def codex_not_ready(engine_root, status):
    """Keep the stronger choice; failed readiness stops the run without a downgrade."""
    import time
    _save_codex_state(engine_root, readiness=_codex_readiness(status),
                      readiness_at=time.time(), setup='failed',
                      error='Codex could not confirm its stronger Windows sandbox. This run stopped.',
                      note='The stronger sandbox remains selected. Check its Windows setup before retrying.')


def codex_ready(engine_root):
    """Record the latest readiness observation, not a complete read-confinement claim."""
    import time
    _save_codex_state(engine_root, readiness='ready', readiness_at=time.time(), setup='done', error=None, note=None)


def codex_sandbox_setup(engine_root, network=True, timeout=SETUP_TIMEOUT):
    """Run Codex's one-time elevated sandbox setup (the ONE Windows admin prompt), then switch Kel's
    Codex runs to it. Blocks until Windows' prompt is answered (or `timeout`). Returns the new state.

    Codex's own app-server does the work (`windowsSandbox/setupStart {mode: 'elevated'}`, then its
    `windowsSandbox/setupCompleted` notification). If the setup is already complete (Codex's markers
    in CODEX_HOME/.sandbox are current) there is no prompt at all."""
    import queue
    import time
    from .appserver import CodexConnection
    from .native import executable
    from . import runtime_guard
    if os.name != 'nt':
        return _save_codex_state(engine_root, mode='unelevated', setup='not-windows')
    memory = ensure(engine_root)
    failure_mode = 'elevated' if codex_state(engine_root).get('mode') == 'elevated' else 'unelevated'
    _save_codex_state(engine_root, setup='running')
    codex = executable('codex')
    argv = codex + ['app-server', '--stdio', '-c', 'analytics.enabled=false',
                    *runtime_guard.codex_config(network, None, memory, engine_root), '-c', 'approval_policy="never"']
    logs = Path(engine_root) / STATE_DIR / 'codex-setup'
    try:
        connection = CodexConnection(memory, logs, process_argv=argv)
    except Exception:
        return _save_codex_state(engine_root, mode=failure_mode, setup='failed',
                                 error='Codex could not start its Windows sandbox setup.')
    try:
        ready = connection.call('windowsSandbox/readiness', {}, timeout=60).get('status')
        started = connection.call('windowsSandbox/setupStart', {'mode': 'elevated', 'cwd': str(memory)}, timeout=60)
        if not started.get('started'):
            return _save_codex_state(engine_root, setup='failed', error='Codex did not start its sandbox setup.')
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                event = connection.events.get(timeout=1)
            except queue.Empty:
                continue
            if event.get('method') == 'kel/connectionClosed':
                break
            if event.get('method') == 'windowsSandbox/setupCompleted':
                params = event.get('params') or {}
                if params.get('success'):
                    after = connection.call('windowsSandbox/readiness', {}, timeout=60).get('status')
                    observed = _codex_readiness(after)
                    return _save_codex_state(engine_root, mode='elevated',
                                             setup='done' if observed == 'ready' else 'failed', readiness=observed,
                                             readiness_at=time.time(), before=_codex_readiness(ready),
                                             error=None if observed == 'ready' else
                                                'Codex setup finished, but its stronger sandbox is not confirmed ready.', note=None)
                return _save_codex_state(engine_root, mode=failure_mode, setup='failed',
                                         error=str(params.get('error') or 'Windows did not allow the setup.')[:300])
        return _save_codex_state(engine_root, mode=failure_mode, setup='failed',
                                 error='No answer from the Windows prompt in time.')
    except Exception:
        return _save_codex_state(engine_root, mode=failure_mode, setup='failed',
                                 error='Codex could not complete its Windows sandbox setup.')
    finally:
        connection.close()


def status(engine_root):
    """What Settings says about the Memory folder and how each AI tool is held to it."""
    state = codex_state(engine_root)
    elevated = codex_elevated(engine_root)
    readiness = state.get('readiness')
    readiness = _codex_readiness(readiness) if readiness is not None else 'not_checked'
    if elevated:
        codex = ('The stronger Windows sandbox limits some reads outside Memory. '
                 'Each run checks readiness and stops if this protection is unavailable.')
    else:
        codex = ('Codex writes stay in its working folders. Reads outside Memory remain available. '
                 'Stronger protection limits some reads.')
    return {'folder': str(memory_root(engine_root)), 'projects': str(projects_dir(engine_root)),
            'mirror': str(mirror_dir(engine_root)),
            'claude': ('Kel checks Claude Code file and command tools with its guard. '
                       'This is tool-level protection, not complete Windows read confinement.'),
            'codex': codex, 'codex_reads_blocked': False,
            'codex_configured_mode': 'elevated' if elevated else 'unelevated',
            'codex_readiness': readiness, 'codex_readiness_at': state.get('readiness_at'),
            'codex_read_coverage': 'partial-deny-list' if elevated else 'unconfined',
            'codex_complete_read_confinement': False,
            'codex_setup': state.get('setup'), 'codex_error': state.get('error'),
            'codex_setup_available': os.name == 'nt' and (not elevated or readiness != 'ready')}
