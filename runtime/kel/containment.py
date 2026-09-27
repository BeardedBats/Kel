"""Practical containment for worker execution (V2-13): sensitive folders, session temp, env.

No VM, no container platform, no rewritten sandbox — the directive's §18 list, done on the paths
Kel already has:

* `assert_usable_root` — Kel refuses to snapshot or modify sensitive locations: Windows and Program
  Files, the user's credential folders, anything inside Kel's own data (the engine root and, in the
  installed layout, the whole `Data` tree), the installed app it runs from, and any extra paths the
  environment protects through `KEL_PROTECTED_PATHS`. `kel.authorize` applies the same check to
  every write, so Full access (D-64) can never reach them either.
* `session_dir` / `cleanup_session` — one disposable temp directory per run, pointed at by
  TMP/TEMP/TMPDIR for the child and removed when the run's transport returns.
* `scrub_secrets` — the child environment keeps the credentials it needs and loses every
  secret-shaped variable (the Round 2.5 R7 rule, widened from a fixed three-name list to the shape
  of the name, so a provider child never carries an unrelated service's token).
"""
import os
import re
import shutil
from pathlib import Path

from .core import PolicyError

SECRET_SHAPE = re.compile(r'(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)[A-Z0-9_]*$',
                          re.IGNORECASE)
# Kel's own helper variables are configuration, not another service's secret.
SECRET_KEEP_PREFIXES = ('KEL_',)

_CREDENTIAL_FOLDERS = ('.ssh', '.aws', '.gnupg', '.azure', '.kube', '.docker', '.config/gcloud')


def scrub_secrets(env, keep=()):
    """Return the environment minus every secret-shaped name that is not explicitly kept."""
    kept = set(keep)
    for name in sorted(env):
        if name in kept or name.startswith(SECRET_KEEP_PREFIXES):
            continue
        if SECRET_SHAPE.search(name):
            env.pop(name, None)
    return env


def _system_roots():
    roots = []
    for key in ('WINDIR', 'SystemRoot', 'ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432'):
        value = os.environ.get(key)
        if value:
            roots.append(Path(value))
    return roots


def _credential_roots():
    home = Path(os.environ.get('USERPROFILE') or Path.home())
    return [home / name for name in _CREDENTIAL_FOLDERS]


def _protected_roots():
    raw = os.environ.get('KEL_PROTECTED_PATHS') or ''
    return [Path(part.strip()) for part in raw.split(';') if part.strip()]


def data_roots(store=None):
    """Kel's own durable data: the engine root and, in the installed layout, the whole Data tree.

    The installed app keeps one tree beside App — `Data\\{engine,store,host}` — with the engine at
    `Data\\engine`. The shell also names its folders through AIONUI_DATA_DIR / KEL_HOST_DATA_DIR.
    Every one of them is Kel's own state, never a work target (D-64 keeps handoff §21 intact).
    """
    roots = []
    if store is not None:
        engine = Path(store.root)
        roots.append(engine)
        parent = engine.parent
        if engine.name.lower() == 'engine' and any((parent / name).is_dir() for name in ('store', 'host')):
            roots.append(parent)
    for key in ('KEL_DATA_DIR', 'AIONUI_DATA_DIR', 'KEL_HOST_DATA_DIR'):
        value = os.environ.get(key)
        if value:
            roots.append(Path(value))
    return roots


def app_roots():
    """The installed Kel app: when the engine runs frozen inside it, the folder holding Kel.exe."""
    import sys
    roots = []
    if getattr(sys, 'frozen', False):
        here = Path(sys.executable).resolve().parent
        for candidate in (here, *here.parents):
            if (candidate / 'Kel.exe').exists():
                roots.append(candidate)
                break
    return roots


def _inside(target, root):
    try:
        resolved = Path(root).resolve()
    except OSError:
        return False
    try:
        return target == resolved or target.is_relative_to(resolved)
    except OSError:
        return False


def sensitive_reason(path, store=None):
    """None when the path is fine; a short plain label when it is not."""
    try:
        target = Path(path).resolve()
    except OSError:
        return 'an unreadable location'
    for root in _system_roots():
        if _inside(target, root):
            return 'a Windows system folder'
    for root in _credential_roots():
        if _inside(target, root):
            return 'your credentials folder'
    for root in _protected_roots() + app_roots():
        if _inside(target, root):
            return 'a protected app folder'
    for root in data_roots(store):
        if _inside(target, root):
            return "Kel's own data folder"
    return None


def assert_usable_root(path, purpose='work', store=None):
    """Refuse a sensitive root for work Kel would perform autonomously; return the path otherwise."""
    reason = sensitive_reason(path, store=store)
    if reason:
        raise PolicyError('Kel will not use %s for %s: it is %s.'
                          % (path, purpose, reason))
    return Path(path)


def session_dir(root, run_id):
    """The disposable temp directory for one run (created on first use)."""
    path = Path(root) / 'sessions' / str(run_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_session(path):
    """Best-effort removal; a locked leftover file never fails the run."""
    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass
    return not Path(path).exists()
