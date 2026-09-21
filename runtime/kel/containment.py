"""Practical containment for worker execution (V2-13): sensitive folders, session temp, env.

No VM, no container platform, no rewritten sandbox — the directive's §18 list, done on the paths
Kel already has:

* `assert_usable_root` — Kel refuses to snapshot or modify sensitive locations: Windows and Program
  Files, the user's credential folders, anything inside Kel's own data root, and any extra paths the
  environment protects through `KEL_PROTECTED_PATHS` (the desktop sets its stable-app folders there).
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
    for root in _protected_roots():
        if _inside(target, root):
            return 'a protected app folder'
    if store is not None and _inside(target, store.root):
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
