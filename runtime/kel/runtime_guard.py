"""FN-01: protected places stay out of reach of what the model runtimes do directly.

The protected-path rule (`containment.sensitive_reason`, `authority.protected_hit`) used to run only
on permission requests and on apply. A native host run under Full access (D-64) never asks, so a
runtime could write straight into Kel's own Data folder (found live: "save a copy of calc.py as
<Data>\\engine\\calc-copy.py" did exactly that). Full access means "no approval prompts", not "no
boundaries" (handoff §21, §12, D-64). This module holds the three layers:

1. **Prevent** — each runtime is started with its own real boundary (D-81: an allow-list, the working
   copy and Kel's Memory folder; see docs/v2/design/MEMORY_FOLDER.md):
   * Claude Code (2.1.283): `--settings` carrying a PreToolUse hook (`guard_hook.mjs`) plus
     `permissions.deny` rules. bypassPermissions "auto-approves every tool call (except explicit deny
     rules)"; a PreToolUse hook gates every call in every mode. Tools may read and write only the
     working copy, Memory and the run's temp folder, and read the system and tool folders.
   * Codex (0.157.1): the permission profile `kel` (`codex_config`): write only the working copy,
     Memory and the run's temp folder, at the OS level. Reads are confined by Windows only in Codex's
     elevated sandbox (after the person's one-time admin approval), through `deny` entries.
2. **Detect** — `Watch` snapshots metadata (names, sizes, mtimes; never contents) of the protected
   places before a run and compares after it. Anything new or changed there fails the step with a
   plain sentence, one Activity line, and the new entries are moved out (restored) where possible.
3. **Refuse clearly** — `request_refusal` reads a request before any work starts (D-55) and answers
   in plain words when it asks to touch a protected place.
"""
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time

from .containment import _credential_roots, _protected_roots as _env_roots, app_roots, data_roots

DATA_LABEL = "Kel's own data folder"
APP_LABEL = "Kel's installed app folder"
CREDENTIALS_LABEL = 'your credentials folder'
PROTECTED_LABEL = 'a protected folder'
NEIGHBOUR_LABEL = "one of Kel's own folders"
OUTSIDE_LABEL = "a place outside Kel's Memory folder"
MIRROR_LABEL = "Kel's read-only copy in the Memory folder"

HOOK = Path(__file__).with_name('guard_hook.mjs')
DENIALS = 'guard-denials.jsonl'
QUARANTINE = 'protected-quarantine'

# Files Kel itself (or the desktop shell) rewrites while work runs; never evidence of a worker write.
_CHURN = re.compile(r'(\.(sqlite3?|db)(-wal|-shm|-journal)?|-(wal|shm|journal)|\.log|\.lock|\.tmp|\.pid)$', re.I)
_ENGINE_BUSY = {'desktop-session.json', 'controller.lock', 'aion-history.json', 'aion-conversations.json'}
# Folders Kel creates in its engine root on demand.
_ENGINE_DIRS = {'sessions', 'native-logs', 'repositories', 'transport-locks', 'broker-locks', 'broker-logs',
                'logs', 'telemetry', 'artifacts', 'backups', 'application-backups', 'attachments',
                'migration-backups', 'missions', 'workspaces', 'dogfood', 'transcription',
                'aion-session-map', 'aion-workspaces', 'modules', 'recovery', 'memory-mirror'}


class _Root:
    """Just enough of a Store for `containment.data_roots` when only the engine folder is known."""
    def __init__(self, root):
        self.root = Path(root)


def _norm(path):
    try:
        return Path(path).resolve()
    except OSError:
        return Path(os.path.abspath(path))


def _inside(target, root):
    target, root = _norm(target), _norm(root)
    return target == root or target.is_relative_to(root)


def protected_places(engine_root=None):
    """Every protected place as (path, label, kind); kind 'data' | 'shell' | 'app' | 'credentials' |
    'protected'. The engine root and the whole installed Data tree are 'data'; the desktop shell's
    own folders (store/host) are 'shell' (it rewrites them all the time, so only new entries count)."""
    places, seen = [], set()

    def add(path, label, kind):
        key = str(_norm(path)).lower()
        if key not in seen:
            seen.add(key)
            places.append((_norm(path), label, kind))

    store = _Root(engine_root) if engine_root else None
    for root in data_roots(store):
        shell = os.environ.get('AIONUI_DATA_DIR'), os.environ.get('KEL_HOST_DATA_DIR')
        kind = 'shell' if any(v and _norm(v) == _norm(root) for v in shell) else 'data'
        add(root, DATA_LABEL, kind)
        for name in ('store', 'host'):
            if (Path(root) / name).is_dir():
                add(Path(root) / name, DATA_LABEL, 'shell')
    for root in app_roots():
        add(root, APP_LABEL, 'app')
    for root in _env_roots():
        add(root, PROTECTED_LABEL, 'protected')
    for root in _credential_roots():
        add(root, CREDENTIALS_LABEL, 'credentials')
    return places


def place_of(path, engine_root=None, workspace=None):
    """(label, root) when `path` is inside a protected place (and not inside the working copy)."""
    if workspace and _inside(path, workspace):
        return None
    best = None
    for root, label, _kind in protected_places(engine_root):
        if _inside(path, root) and (best is None or len(str(root)) > len(str(best[1]))):
            best = (label, root)
    return best


# ---- 1. prevent -----------------------------------------------------------------------------------

def policy(engine_root, workspace, logs, temp=None, tools=()):
    """The hook's policy for one run (D-81, an allow-list): the working copy, the Memory folder and the
    run's own temp folder are readable and writable; Memory\\Kel (Kel's mirror) and a few named files
    are readable; the system and tool folders the CLIs need are readable (`memory_folder.
    system_readable_roots`, plus `tools`: the CLIs' own install folders); everything else is refused.
    The protected places are listed so a refusal can say what the place is."""
    from . import memory_folder
    memory = memory_folder.memory_root(engine_root)
    places = [{'path': str(root), 'label': label} for root, label, _kind in protected_places(engine_root)]
    places += [{'path': str(root), 'label': NEIGHBOUR_LABEL} for root in memory_folder.neighbours(engine_root)
               if not any(_norm(root) == _norm(p['path']) for p in places)]
    return {'workspace': str(_norm(workspace)),
            'memory': str(_norm(memory)),
            'mirror': str(_norm(memory / memory_folder.MIRROR)),
            'writable': [str(_norm(temp))] if temp else [],
            # kel.conn (the Connections bridge) reads the engine's session file to reach Kel.
            'readable': [str(_norm(Path(engine_root) / 'desktop-session.json'))] if engine_root else [],
            'system': [str(path) for path, _why in memory_folder.system_readable_roots(engine_root, tools)],
            'protected': places,
            'log': str(Path(logs) / DENIALS)}


def write_policy(engine_root, workspace, logs, temp=None, tools=()):
    Path(logs).mkdir(parents=True, exist_ok=True)
    target = Path(logs) / 'guard-policy.json'
    target.write_text(json.dumps(policy(engine_root, workspace, logs, temp, tools), indent=1), encoding='utf-8')
    return target


def _rule_path(path):
    """Claude Code's absolute-path rule form: `//c/Users/...` (POSIX spelling of a Windows path)."""
    text = str(path).replace('\\', '/')
    if re.match(r'^[A-Za-z]:/', text):
        text = '/' + text[0].lower() + text[2:]
    return '//' + text.lstrip('/')


def claude_settings(policy_file, node, workspace):
    """The `--settings` JSON for Kel's Claude Code host: the guard hook (the allow-list), and deny rules
    for every off-limits place that does not hold the working copy (Kel's Data folder holds it by
    design, so that one is left to the hook, which carves the working copy out), plus no edits in
    Memory\\Kel. Deny rules cannot express "everything but Memory"; the hook does."""
    command = '"%s" "%s"' % (str(node).replace('\\', '/'), str(HOOK).replace('\\', '/'))
    deny = []
    data = json.loads(Path(policy_file).read_text(encoding='utf-8'))
    for item in data['protected']:
        if _inside(workspace, item['path']) or (data.get('memory') and _inside(data['memory'], item['path'])):
            continue
        rule = _rule_path(item['path'])
        deny += ['Read(%s/**)' % rule, 'Edit(%s/**)' % rule]
    if data.get('mirror'):
        deny.append('Edit(%s/**)' % _rule_path(data['mirror']))
    return {'permissions': {'deny': deny},
            'hooks': {'PreToolUse': [{'matcher': '*', 'hooks': [
                {'type': 'command', 'command': command, 'timeout': 30}]}]}}


def network_allowed(engine_root):
    """False only when the person turned network off for Kel (V2-14 mode `none`); the default is on."""
    try:
        with contextlib.closing(sqlite3.connect('file:%s?mode=ro' % (Path(engine_root) / 'kel.sqlite3').as_posix(),
                                                uri=True, timeout=2)) as db:
            row = db.execute("SELECT mode FROM network_policy WHERE scope='default'").fetchone()
        return not (row and row[0] == 'none')
    except sqlite3.Error:
        return True


# Codex features that act outside the shell sandbox (their own processes, the person's browser or
# desktop, or user hooks). A Kel worker needs none of them.
CODEX_OUTSIDE_FEATURES = ('apps', 'plugins', 'hooks', 'browser_use', 'browser_use_external', 'computer_use',
                          'in_app_browser')
_MCP_NAME = re.compile(r'^[A-Za-z0-9_-]+$')


def codex_mcp_servers(codex, cwd):
    """Names of the MCP servers Codex would load here (the person's own config included).

    Found live: Nick's Codex config carries a `node_repl` MCP server, and a Kel run used its
    `fs.writeFile` — an MCP server is its own process, outside the workspace sandbox. Raises
    PolicyError when the list cannot be read, so a run never starts with servers Kel cannot see.
    """
    from .core import PolicyError
    argv = list(codex) + ['mcp', 'list', '--json']
    for feature in CODEX_OUTSIDE_FEATURES:
        argv += ['--disable', feature]
    try:
        out = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, encoding='utf-8',
                             errors='replace', timeout=60,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        servers = json.loads(out.stdout or 'null')
        if out.returncode != 0 or not isinstance(servers, list):
            raise ValueError(out.stderr[-300:])
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise PolicyError("Kel could not check which tool servers Codex would load, so it did not start "
                          'this run (%s).' % str(exc)[:160])
    names = [str(s.get('name') or '') for s in servers if isinstance(s, dict)]
    bad = [n for n in names if not _MCP_NAME.match(n)]
    if bad:
        raise PolicyError('Kel cannot switch off the Codex tool server "%s", so it did not start this run.'
                          % bad[0][:60])
    return names


CODEX_PROFILE = 'kel'


def _toml_str(text):
    text = str(text)
    if "'" not in text and '\n' not in text:
        return "'%s'" % text  # a TOML literal string: backslashes stay as they are
    return json.dumps(text)


def codex_deny_paths(engine_root, workspace=None, temp=None):
    """What Codex's elevated Windows sandbox is told it may NOT read (D-81).

    Codex 0.157.1 cannot express "read only these folders": both Windows sandbox modes refuse a
    permission profile without `:root` read (windows-sandbox-rs lib.rs / resolved_permissions.rs), and
    only the elevated mode enforces `deny` entries (as deny ACEs for its CodexSandboxUsers group). So
    the allow-list is approximated by denying, around the Memory folder and the run's own folders:
    - Kel's own folders beside Memory (App, Kel source, Tools, ...) and the parts of Data that hold
      no run folder (everything in Data but the engine; in the engine everything but `repositories`
      and `sessions`, the working copies and run temp folders);
    - the credential folders and KEL_PROTECTED_PATHS;
    - the person's own folders in the home folder (Documents, Downloads, Pictures, Music, Videos,
      OneDrive, Favorites, ...), the Desktop apart from the Kel folder, and the home's `.claude`,
      `.ssh`-style dot folders.
    Only existing paths are listed (Codex would create a missing one), and never a folder that holds
    Memory, the working copy or the run's temp folder (a deny there would reach them).
    Not denied (still readable by Codex even when elevated): Windows, Program Files, ProgramData,
    AppData (tool installs live there) and other drives. See docs/v2/design/MEMORY_FOLDER.md."""
    from . import memory_folder
    memory = _norm(memory_folder.memory_root(engine_root))
    keep = [memory] + [_norm(p) for p in (workspace, temp) if p]

    def holds_kept(path):
        p = _norm(path)
        return any(k == p or k.is_relative_to(p) for k in keep)

    out, seen = [], set()

    def deny(path):
        p = _norm(path)
        key = str(p).lower()
        if key in seen or not p.exists() or holds_kept(p):
            return
        seen.add(key)
        out.append(p)

    def deny_around(folder, depth=3):
        """Deny every child of `folder` except the ones on the way to a kept folder (recursively)."""
        try:
            children = list(Path(folder).iterdir())
        except OSError:
            return
        for child in children:
            if holds_kept(child):
                if depth > 1 and child.is_dir() and not any(_norm(child) == k for k in keep):
                    deny_around(child, depth - 1)
            else:
                deny(child)

    kel_root = memory.parent
    if memory_folder.neighbours(engine_root):
        deny_around(kel_root, depth=3)  # App, Kel, Tools; Data -> engine -> all but repositories/sessions
    from .containment import _credential_roots, _protected_roots
    for path in _credential_roots() + _protected_roots():
        deny(path)
    home = Path(os.environ.get('USERPROFILE') or Path.home())
    for name in ('Documents', 'Downloads', 'Pictures', 'Music', 'Videos', 'Favorites', 'Contacts', 'Links',
                 'Saved Games', 'Searches', '3D Objects', '.claude', '.claude.json', '.codex/auth.json', '.gnupg',
                 '.config', '.git-credentials', '.npmrc', '.pypirc', '.netrc'):
        deny(home / name)
    try:
        for child in home.iterdir():
            if child.name.lower().startswith('onedrive'):
                deny(child)
    except OSError:
        pass
    desktop = home / 'Desktop'
    if desktop.is_dir():
        if holds_kept(desktop):
            deny_around(desktop, depth=1)
        else:
            deny(desktop)
    return out


def codex_config(network=True, codex=None, cwd=None, engine_root=None, temp=None, elevated=False):
    """Codex app-server overrides (D-81): a permission profile `kel` — read the machine (Codex 0.157.1
    requires `:root` read in both Windows sandbox modes), write only the working copy (`:workspace_roots`),
    the Memory folder and the run's temp folder — network per the person's setting, and nothing that
    runs outside it (the outside-acting features off, every MCP server switched off by name).

    `elevated` (after the one-time Windows admin approval, `codex_sandbox_setup`) runs the commands as
    Codex's own sandbox users and adds `deny` entries (`codex_deny_paths`) so reads outside the Memory
    folder are blocked by Windows too. Without it (the restricted-token sandbox, no admin) writes are
    confined but reads are not; Kel's instructions and request check are the only read limit then.

    Kel sends no per-thread `sandbox` and no per-turn `sandboxPolicy`: either replaces the profile
    with the legacy policy (which also makes the whole machine temp folder writable)."""
    from . import memory_folder
    memory = memory_folder.memory_root(engine_root)
    entries = {':root': 'read', ':workspace_roots': 'write', str(memory): 'write'}
    if temp:
        entries[str(temp)] = 'write'
    if elevated:
        for path in codex_deny_paths(engine_root, cwd, temp):
            entries[str(path)] = 'deny'
    table = '{%s}' % ', '.join('%s="%s"' % (_toml_str(k), v) for k, v in entries.items())
    args = ['-c', 'sandbox_mode="workspace-write"',  # the fallback if the profile were ever ignored
            '-c', 'default_permissions="%s"' % CODEX_PROFILE,
            '-c', 'permissions.%s.filesystem=%s' % (CODEX_PROFILE, table),
            '-c', 'permissions.%s.network.enabled=%s' % (CODEX_PROFILE, 'true' if network else 'false'),
            '-c', 'sandbox_workspace_write.network_access=%s' % ('true' if network else 'false')]
    if os.name == 'nt':
        args += ['-c', 'windows.sandbox="%s"' % ('elevated' if elevated else 'unelevated')]
    for feature in CODEX_OUTSIDE_FEATURES:
        args += ['--disable', feature]
    if codex is not None:
        for name in codex_mcp_servers(codex, cwd or os.getcwd()):
            args += ['-c', 'mcp_servers.%s.enabled=false' % name]
    return args


# ---- 2. detect ------------------------------------------------------------------------------------

def _stat(path):
    try:
        st = path.lstat()
    except OSError:
        return None
    if path.is_dir() and not path.is_symlink():
        return ('dir', 0, 0)
    return ('file', st.st_size, st.st_mtime_ns)


def _scan(root, depth):
    out = {}
    try:
        children = list(Path(root).iterdir())
    except OSError:
        return out
    for child in children:
        info = _stat(child)
        if info is None:
            continue
        out[str(child)] = info
        if depth > 1 and info[0] == 'dir':
            out.update(_scan(child, depth - 1))
    return out


class Watch:
    """Metadata of the protected places around one run (names, sizes, mtimes — never contents)."""

    def __init__(self, engine_root, workspace, run_id=None):
        self.engine_root = Path(engine_root)
        self.workspace = _norm(workspace)
        self.run_id = run_id
        self.places = [p for p in protected_places(engine_root) if p[0].exists()]
        self.before = self._snapshot()

    def _depth(self, kind):
        return 1 if kind in ('data', 'shell', 'app') else 2

    def _snapshot(self):
        snap = {}
        for root, label, kind in self.places:
            for key, info in _scan(root, self._depth(kind)).items():
                snap.setdefault(key, (info, label, kind, str(root)))
        return snap

    def _ignored(self, path, kind, root, new):
        p = Path(path)
        if _inside(p, self.workspace) or self.workspace.is_relative_to(_norm(p)):
            return True
        if kind in ('data', 'shell'):
            if _CHURN.search(p.name):
                return True
            if kind == 'shell' and not new:
                return True  # the desktop shell rewrites its own files constantly
            if _norm(p.parent) == _norm(self.engine_root):
                if p.name in _ENGINE_BUSY or (new and p.name in _ENGINE_DIRS and p.is_dir()):
                    return True
            if _norm(p.parent) == _norm(root) and p.name in ('engine', 'store', 'host', 'workspaces',
                                                              'backups', 'recovery'):
                return True
        return False

    def changes(self):
        """[{path, label, change: 'new'|'changed'|'removed'}] outside the working copy."""
        after = self._snapshot()
        found = []
        for key, (info, label, kind, root) in after.items():
            old = self.before.get(key)
            if old is None:
                if not self._ignored(key, kind, root, True):
                    found.append({'path': key, 'label': label, 'change': 'new', 'kind': info[0]})
            elif info[0] == 'file' and old[0][0] == 'file' and info[1:] != old[0][1:]:
                if not self._ignored(key, kind, root, False):
                    found.append({'path': key, 'label': label, 'change': 'changed', 'kind': 'file'})
        for key, (info, label, kind, root) in self.before.items():
            if key not in after and not self._ignored(key, kind, root, False):
                found.append({'path': key, 'label': label, 'change': 'removed', 'kind': info[0]})
        # A new folder already explains the files inside it.
        news = [Path(c['path']) for c in found if c['change'] == 'new' and c['kind'] == 'dir']
        return [c for c in found if not any(Path(c['path']) != d and Path(c['path']).is_relative_to(d) for d in news)]

    def restore(self, change, logs):
        """Move a new entry out of the protected place (kept beside the run's logs). True if done."""
        if change['change'] != 'new':
            return False
        source = Path(change['path'])
        target = Path(logs) / QUARANTINE / ('%d-%s' % (int(time.time() * 1000), source.name))
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            return not source.exists()
        except OSError:
            return False


def _event(store, job_id, event_type, payload):
    if not job_id:
        return
    with store.transaction() as db:
        try:
            job = store._get(db, str(job_id))
        except KeyError:
            return
        store._save(db, job, event_type, payload)


def denials(logs):
    """What the guard hook refused during a run (read once: the log is renamed when read)."""
    path = Path(logs) / DENIALS
    if not path.exists():
        return []
    done = path.with_suffix('.recorded')
    try:
        path.replace(done)
        lines = done.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _attempt(item):
    """What the worker tried, in a few plain words (a file's name, never a long path or a command)."""
    data = item.get('input') or {}
    tool = str(item.get('tool') or '')
    target = data.get('file_path') or data.get('notebook_path') or data.get('path') or ''
    name = Path(str(target)).name if target else ''
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        return 'let the worker write %s' % (name or 'a file')
    if tool in ('Read', 'NotebookRead', 'Glob', 'Grep', 'LS'):
        return 'let the worker read %s' % (name or 'that folder')
    return 'let the worker run a command that reached it'


def _refusal_label(reason):
    if 'Memory\\Kel' in reason:
        return MIRROR_LABEL
    return next((l for l in (DATA_LABEL, APP_LABEL, CREDENTIALS_LABEL, PROTECTED_LABEL, NEIGHBOUR_LABEL)
                 if l in reason), OUTSIDE_LABEL)


def _restore_mirror(store, job_id, run_id, result):
    """D-81: Memory\\Kel is Kel's read-only mirror. Anything a run changed there is put back at once
    (one Activity line, one sentence in the result); the step itself stands."""
    from . import memory_mirror
    try:
        if not (Path(store.root) / memory_mirror.STATE_DIR / memory_mirror.MANIFEST).exists():
            return
        if not memory_mirror.tampered(store.root):
            return
        reverted = memory_mirror.sync(store.root)['reverted']
    except Exception:
        return  # the mirror keeper retries; a run's result never depends on it
    if not reverted:
        return
    _event(store, job_id, 'approval.refused',
           {'summary': 'keep the change the worker made to %s' % reverted[0], 'reason': MIRROR_LABEL,
            'source': 'runtime-guard', 'run_id': run_id, 'changes': len(reverted), 'restored': len(reverted)})
    if isinstance(result, dict) and isinstance(result.get('text'), str):
        result['text'] += ("\n\nKel put back Memory\\Kel (%s): it is Kel's read-only copy, and agents never change "
                           "Kel's settings." % reverted[0])
    if isinstance(result, dict):
        result['mirror_reverted'] = reverted[:10]


def settle(store, job_id, run_id, watch, logs, result, actor='The worker'):
    """After a runtime turn: record what the guard refused, and fail the step on any protected write.

    Returns a replacement result when a protected place changed (the step fails with a plain
    explanation), else None (the caller's result stands; a note on refused steps is added to it).
    """
    refused = denials(logs)
    for item in refused[:5]:
        reason = str(item.get('reason') or '')
        label = _refusal_label(reason)
        _event(store, job_id, 'approval.refused',
               {'summary': _attempt(item), 'reason': label, 'source': 'runtime-guard', 'run_id': run_id})
    if refused and isinstance(result, dict) and isinstance(result.get('text'), str):
        places = sorted({_refusal_label(str(i.get('reason'))) for i in refused})
        result['text'] += ('\n\nKel stopped the worker from touching %s; that part of the request was not done.'
                           % ' or '.join(places))
        result['protected_refusals'] = len(refused)
    _restore_mirror(store, job_id, run_id, result)
    if watch is None:
        return None
    changes = watch.changes()
    if not changes:
        return None
    restored, kept = [], []
    for change in changes:
        (restored if watch.restore(change, logs) else kept).append(change)
    first = changes[0]
    name = Path(first['path']).name
    what = {'new': 'wrote %s into' % name, 'changed': 'changed %s in' % name,
            'removed': 'removed %s from' % name}[first['change']]
    more = ' (and %d more)' % (len(changes) - 1) if len(changes) > 1 else ''
    tail = ('Kel moved it back out.' if not kept else
            'Kel could not undo that on its own: check %s.' % kept[0]['path'])
    error = ("%s %s %s%s, which Kel never allows, so Kel stopped this step. %s"
             % (actor, what, first['label'], more, tail))
    _event(store, job_id, 'approval.refused',
           {'summary': 'keep the %s %s %s there' % (name, actor[0].lower() + actor[1:], {'new': 'wrote', 'changed': 'changed',
                                                                  'removed': 'removed'}[first['change']]),
            'reason': first['label'],
            'source': 'runtime-guard', 'run_id': run_id, 'changes': len(changes), 'restored': len(restored)})
    failed = {'outcome': 'FAILED', 'error': error, 'protected_breach': changes[:10]}
    for key in ('session_id', 'model_used', 'reasoning_used', 'usage', 'cost_usd'):
        if isinstance(result, dict) and key in result:
            failed[key] = result[key]
    return failed


# ---- 3. refuse clearly ----------------------------------------------------------------------------

_QUOTED = re.compile(r'[`"“”\']([^`"“”\'\n]{3,400})[`"“”\']')
# A path a request names: a drive path (not the "s://" of a URL), ~, %VAR%, $env:VAR, or Git Bash /c/...
_BARE = re.compile(r'(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]|(?<![\w/.~-])~[\\/]|%[A-Za-z_]+%[\\/]?|\$(?:env:)?[A-Za-z_]+[\\/]'
                   r'|(?<![\w/.:~-])/[a-zA-Z]/)[^\s`"\'<>|,;]*')
_WRITE = re.compile(r'\b(save|saving|write|writing|copy|copying|move|put|create|add|edit|change|modify|delete|'
                    r'remove|overwrite|store|place|drop|append|replace|install|patch|update)\b', re.I)
_PHRASES = (
    (re.compile(r"\bkel'?s\s+(own\s+)?data\s+(folder|directory|root)\b", re.I), DATA_LABEL),
    (re.compile(r"\bkel'?s\s+(own\s+)?(installed\s+)?(app|install(ation)?)\s+(folder|directory|files)\b", re.I), APP_LABEL),
    (re.compile(r"(?:~[\\/]|\b(?:my|your|the user'?s|home|user)\s+)\.(ssh|aws|gnupg|azure|kube|docker)(?=$|[\s\\/\"`'.,])",
                re.I), CREDENTIALS_LABEL),
    (re.compile(r'\b(?:credentials?|ssh keys?)\s+(?:folder|directory)\b', re.I), CREDENTIALS_LABEL),
    (re.compile(r"\bkel'?s\s+(own\s+)?settings\b", re.I), MIRROR_LABEL),
)


def _expand(text):
    home = os.environ.get('USERPROFILE') or str(Path.home())
    t = text.strip().rstrip('.,;:)')
    t = re.sub(r'\$env:([A-Za-z_]\w*)', lambda m: os.environ.get(m.group(1), m.group(0)), t, flags=re.I)
    t = re.sub(r'%([A-Za-z_]\w*)%', lambda m: os.environ.get(m.group(1), m.group(0)), t)
    t = re.sub(r'\$\{?([A-Za-z_]\w*)\}?', lambda m: (home if m.group(1).upper() == 'HOME'
                                                     else os.environ.get(m.group(1), m.group(0))), t)
    if t == '~' or t.startswith(('~/', '~\\')):
        t = home + t[1:]
    bash = re.match(r'^/([a-zA-Z])(/|$)(.*)$', t)
    if bash and os.name == 'nt':
        t = bash.group(1) + ':/' + bash.group(3)
    return t


def _project_roots(engine_root):
    """The folders of Kel's saved projects (existing projects stay where they are, D-81)."""
    if not engine_root:
        return []
    try:
        with contextlib.closing(sqlite3.connect('file:%s?mode=ro' % (Path(engine_root) / 'kel.sqlite3').as_posix(),
                                                uri=True, timeout=2)) as db:
            query = 'SELECT root FROM projects WHERE root IS NOT NULL AND root<>""'
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='project_meta'").fetchone():
                # Only the person's live projects: never archived or plumbing ("system") ones.
                query = ('SELECT p.root FROM projects p LEFT JOIN project_meta m ON m.project_id=p.id WHERE p.root IS NOT '
                         "NULL AND p.root<>'' AND m.archived IS NULL AND COALESCE(m.kind,'user')<>'system'")
            rows = db.execute(query).fetchall()
    except sqlite3.Error:
        return []
    roots = []
    for (root,) in rows:
        # Never a project whose folder is Kel's own (old plumbing projects pointed into Data or temp).
        if root and os.path.isabs(root) and not place_of(root, engine_root):
            roots.append(root)
    return roots


def _where(path, engine_root=None, project_root=None, write=False):
    """None when a worker may use `path` (D-81); else the label of the place it is in."""
    from . import memory_folder
    if memory_folder.in_mirror(path, engine_root):
        return MIRROR_LABEL if write else None
    if memory_folder.in_memory(path, engine_root):
        return None
    if project_root and _inside(path, project_root):
        return None  # the project's own folder: the worker has its working copy
    if any(_inside(path, root) for root in _project_roots(engine_root)):
        return None  # another saved project: Kel routes the work there, on a working copy
    hit = place_of(path, engine_root)
    if hit:
        return hit[0]
    if not write and any(_inside(path, root) for root, _why in memory_folder.system_readable_roots(engine_root)):
        return None
    return OUTSIDE_LABEL


def mentions(text, engine_root=None, project_root=None):
    """Places outside Kel's Memory folder that a request names: [(label, path-or-None)]."""
    found = []
    write = bool(_WRITE.search(text or ''))
    text = text or ''
    # A bare path stops at a space; "C:\...\Kel Projects\calc" is also tried up to the line's end or
    # the next punctuation (without ".." hops), and counts as fine when either form is.
    candidates = [(m.group(1), None) for m in _QUOTED.finditer(text)]
    candidates += [(m.group(0), re.match(r'[^\n`"\'<>|,;]*', text[m.start():]).group(0).rstrip(' .:)'))
                   for m in _BARE.finditer(text)]
    for raw, longer in candidates:
        path = _expand(raw)
        if not (os.path.isabs(path) or re.match(r'^[A-Za-z]:[\\/]', path)):
            continue
        label = _where(path, engine_root, project_root, write)
        if label and longer and longer != raw and not re.search(r'(^|[\\/])\.\.([\\/]|$)', longer):
            # Try each space-separated extension: "…\Kel" → "…\Kel Projects" → "…\Kel Projects\calc\calc.py".
            pieces = longer[len(raw):].split(' ')
            for n in range(1, len(pieces) + 1):
                if not _where(_expand(raw + ' '.join(pieces[:n])), engine_root, project_root, write):
                    label = None
                    break
        if label:
            found.append((label, path))
    for pattern, label in _PHRASES:
        if pattern.search(text or '') and (label != MIRROR_LABEL or write):
            found.append((label, None))
    return found


def request_refusal(text, engine_root=None, project_root=None):
    """One plain sentence when a request asks to touch a place outside Kel's Memory folder (D-81), or
    to change Kel's own mirror in it (D-55: said before any work starts, never promised and failed
    later); None when it does not."""
    from .memory_folder import MIRROR_REFUSAL, REFUSAL
    found = mentions(text, engine_root, project_root)
    if not found:
        return None
    if all(label == MIRROR_LABEL for label, _path in found):
        return MIRROR_REFUSAL
    return REFUSAL
