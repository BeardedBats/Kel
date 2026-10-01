"""Real native CLI adapters. No shell invocation; native tools disabled.

This first compatibility slice accepts text output only. It does not claim native
edit, ACP permission streaming, cost metering or arbitrary tool isolation.
"""
from __future__ import annotations
import json
import os
import re
import stat
import base64
import hashlib
from pathlib import Path
import shutil
import subprocess
import threading
import time
from .core import uid
from .containment import cleanup_session, scrub_secrets, session_dir
from .internal import SECRET_ENV_KEYS


_VERSION_RE = re.compile(r'(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.-]+)?')
_VERSIONS = {}
_VERSIONS_LOCK = threading.Lock()


def parse_version(text):
    """(major, minor, patch, release flag) from a CLI's `--version` text; a pre-release (`-alpha.5`)
    sorts below its release. None when the text carries no version."""
    match = _VERSION_RE.search(str(text or ''))
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)), 0 if match.group(4) else 1)


def version_of(path):
    """The `--version` line of one executable (asked once per process), or None."""
    key = str(path)
    with _VERSIONS_LOCK:
        if key in _VERSIONS:
            return _VERSIONS[key]
    text = None
    try:
        result = subprocess.run([key, '--version'], capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=15,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                                env=child_env('codex'))
        if result.returncode == 0:
            text = (result.stdout or '').strip().splitlines()[0].strip() if (result.stdout or '').strip() else None
    except (OSError, subprocess.SubprocessError, ValueError):
        text = None
    with _VERSIONS_LOCK:
        _VERSIONS[key] = text
    return text


def codex_candidates(env=None):
    """Every Codex CLI binary Kel can see: `KEL_CODEX_PATH` alone when it is set (Nick's config);
    otherwise each `codex.exe` on PATH (the Codex desktop app ships one), the npm-global package's
    native binary (never its .cmd wrapper) and the desktop app's own bin folder."""
    env = os.environ if env is None else env
    configured = str(env.get('KEL_CODEX_PATH') or '').strip()
    if configured:
        return [configured] if Path(configured).is_file() else []
    names = ('codex.exe',) if os.name == 'nt' else ('codex',)
    found = []
    for folder in str(env.get('PATH') or '').split(os.pathsep):
        for name in names:
            candidate = Path(folder.strip('"')) / name if folder else None
            if candidate is not None and candidate.is_file():
                found.append(str(candidate))
    appdata = env.get('APPDATA')
    if appdata:
        package = Path(appdata) / 'npm' / 'node_modules' / '@openai' / 'codex'
        for arch, triple in (('x64', 'x86_64-pc-windows-msvc'), ('arm64', 'aarch64-pc-windows-msvc')):
            for base in (package / 'node_modules' / '@openai' / ('codex-win32-' + arch),
                         Path(appdata) / 'npm' / 'node_modules' / '@openai' / ('codex-win32-' + arch),
                         package):
                candidate = base / 'vendor' / triple / 'bin' / 'codex.exe'
                if candidate.is_file():
                    found.append(str(candidate))
                candidate = base / 'vendor' / triple / 'codex' / 'codex.exe'
                if candidate.is_file():
                    found.append(str(candidate))
    local = env.get('LOCALAPPDATA')
    if local:
        candidate = Path(local) / 'Programs' / 'OpenAI' / 'Codex' / 'bin' / 'codex.exe'
        if candidate.is_file():
            found.append(str(candidate))
    unique = []
    for item in found:
        try:
            resolved = str(Path(item).resolve())
        except OSError:
            resolved = item
        if resolved.lower() not in {u.lower() for u in unique}:
            unique.append(resolved)
    return unique


_CODEX_CHOICE = {}


def codex_executable(refresh=False, env=None):
    """{'path', 'version'} of the Codex CLI Kel runs: the configured one, else the newest installed
    (the first on PATH can be an old bundled copy — the live check found 0.142.5 ahead of 0.144.5).
    `path` is None when no Codex CLI is installed."""
    key = 'default' if env is None else id(env)
    if not refresh and key in _CODEX_CHOICE:
        return dict(_CODEX_CHOICE[key])
    best, best_version, best_text = None, None, None
    for candidate in codex_candidates(env):
        text = version_of(candidate)
        parsed = parse_version(text) or (0, 0, 0, 0)
        if best is None or parsed > best_version:
            best, best_version, best_text = candidate, parsed, text
    choice = {'path': best, 'version': best_text}
    _CODEX_CHOICE[key] = choice
    return dict(choice)


def runtime_version(provider):
    """Plain runtime name and version ("Codex CLI 0.144.5", "Claude Code 2.1.283"), or None."""
    try:
        if provider in ('codex', 'codex-code'):
            text = codex_executable().get('version')
            parsed = parse_version(text)
            return ('Codex CLI %s' % _VERSION_RE.search(text).group(0)) if parsed else None
        if provider in ('claude', 'claude-code'):
            text = version_of(executable('claude')[0])
            parsed = parse_version(text)
            return ('Claude Code %s' % _VERSION_RE.search(text).group(0)) if parsed else None
    except Exception:
        return None
    return None


def executable(provider):
    if provider == 'codex':
        chosen = codex_executable().get('path')
        return [chosen or shutil.which('codex') or 'codex']
    if provider == 'claude':
        candidate = Path(os.environ.get('APPDATA', '')) / 'npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe'
        if candidate.is_file():
            return [str(candidate)]
        path = shutil.which('claude')
        if path and Path(path).suffix.lower() not in ('.cmd', '.ps1', '.bat'):
            return [path]
        raise RuntimeError('Native Claude executable unavailable; shell wrappers are not used')
    raise ValueError('Unknown native provider')


def require_ephemeral_codex(command=None):
    """Non-model compatibility check before app-server can create a thread."""
    command = command or executable('codex')
    observed = version_of(command[0]) if command else None
    if not isinstance(observed,str) or not re.match(r'^codex(?:-cli)?\s',observed) or not parse_version(observed) or parse_version(observed) < (0,159,2,1):
        raise RuntimeError('This Codex runtime cannot confirm private temporary sessions. Update Codex before using it in Kel.')


def local_session_id(provider, session_id):
    """Internal callers replay their durable prompt; old Codex IDs remain local receipts only."""
    return None if provider in ('codex','codex-web','codex-code') else session_id


_NATIVE_PROVIDER_CREDENTIALS = {
    'codex': ('OPENAI_API_KEY',),
    'claude': ('ANTHROPIC_API_KEY',),
}


def child_env(provider, base=None, session=None):
    """Environment for a native CLI child: never CLAUDECODE, never another provider's key.

    A native child receives at most its own provider's credentials; every other provider key is
    removed, and V2-13 widens the rule from a fixed three-name list to the **shape** of the name:
    anything ending in KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH is dropped unless it is this
    provider's own credential (Kel's own KEL_* helpers are configuration, not a service secret).
    When `session` is given, TMP/TEMP/TMPDIR point at the run's disposable directory.
    """
    env = dict(os.environ if base is None else base)
    env.pop('CLAUDECODE', None)
    allowed = set(_NATIVE_PROVIDER_CREDENTIALS.get(provider, ()))
    scrub_secrets(env, keep=allowed)
    for name in SECRET_ENV_KEYS:
        if name not in allowed:
            env.pop(name, None)
    if session is not None:
        for name in ('TMP', 'TEMP', 'TMPDIR'):
            env[name] = str(session)
    return env


DEFAULT_EFFORT = object()  # "as before": Codex text runs at low effort, Claude uses its own default


def _plain_schema_path(path, directory=False):
    """Refuse redirection at every existing ancestor and at the final leaf."""
    path = Path(path).absolute()
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise RuntimeError('Structured correction path is linked.')
    info = path.stat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError('Structured correction folder is invalid.')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RuntimeError('Structured correction leaf is not a private plain file.')
    return path


def _input_session(root, run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', str(run_id)):
        raise RuntimeError('Invalid internal private input request.')
    base = _plain_schema_path(root, directory=True)
    parent = base / 'sessions'
    if not parent.exists():
        parent.mkdir()
    _plain_schema_path(parent, directory=True)
    session = parent / str(run_id)
    session.mkdir()  # An existing run is never reused for schema or final output.
    _plain_schema_path(session, directory=True)
    return session


def _schema_session(root, run_id, schema):
    if not isinstance(schema, dict):
        raise RuntimeError('Invalid internal structured correction request.')
    raw = json.dumps(schema, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(raw) > 32000:
        raise RuntimeError('Structured correction schema is too large.')
    session = _input_session(root, run_id)
    schema_path, final_path = session / 'correction-schema.json', session / 'correction-final.json'
    with schema_path.open('xb') as handle:
        handle.write(raw)
    with final_path.open('xb'):
        pass
    _plain_schema_path(schema_path)
    _plain_schema_path(final_path)
    return session, schema_path, final_path


def _stage_image_inputs(session, images):
    from .context import image_mime
    if not isinstance(images,list) or not 1<=len(images)<=10:
        raise RuntimeError('Use one to ten verified image inputs.')
    decoded=[]
    for image in images:
        if not isinstance(image,dict) or set(image)!={'mime','data','sha256'} or not isinstance(image['data'],str) or len(image['data'])>6_666_668:
            raise RuntimeError('Invalid verified image input.')
        raw=base64.b64decode(image['data'],validate=True)
        media=image_mime(raw)
        if not 0<len(raw)<=5_000_000 or media is None or media!=image['mime'] or hashlib.sha256(raw).hexdigest()!=image['sha256']:
            raise RuntimeError('Image input bytes or type do not match selection.')
        decoded.append((raw,media,image['sha256']))
    paths=[]
    for index,(raw,media,sha) in enumerate(decoded,1):
        _plain_schema_path(session,directory=True)
        path=session/('image-%d.%s' % (index,{'image/png':'png','image/jpeg':'jpg','image/gif':'gif','image/webp':'webp'}[media]))
        with path.open('xb') as handle:
            handle.write(raw)
        _plain_schema_path(path)
        _verify_image_leaf(path,sha,len(raw))
        paths.append(path)
    return paths


def _verify_image_leaf(path, sha, size):
    path=_plain_schema_path(path)
    before=path.stat()
    if before.st_size!=size or not 0<size<=5_000_000:
        raise RuntimeError('Staged image input changed.')
    descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0))
    with os.fdopen(descriptor,'rb') as source:
        opened=os.fstat(source.fileno())
        if opened.st_nlink!=1 or (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):
            raise RuntimeError('Staged image input changed.')
        raw=source.read(5_000_001)
    _plain_schema_path(path)
    after=path.stat()
    if ((after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)!=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
            or len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha):
        raise RuntimeError('Staged image input changed.')


def _schema_final(path):
    path = _plain_schema_path(path)
    before = path.stat()
    if not 0 < before.st_size <= 256000:
        raise RuntimeError('Structured correction final output is missing or too large.')
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(descriptor, 'rb') as handle:
        opened = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise RuntimeError('Structured correction final output changed.')
        raw = handle.read(256001)
    _plain_schema_path(path)
    after = path.stat()
    if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
        raise RuntimeError('Structured correction final output changed.')
    if len(raw) > 256000:
        raise RuntimeError('Structured correction final output is too large.')
    text = raw.decode('utf-8', errors='strict')
    if not text.strip():
        raise RuntimeError('Structured correction final output is empty.')
    return text


class NativeAdapter:
    def __init__(self, provider, workspace, logs, timeout=100, model=None, effort=DEFAULT_EFFORT,
                 fallback_model=None, web=False):
        """`model`/`fallback_model`/`effort` (D-67) are the runtime's own flags: Codex `-m` and
        `model_reasoning_effort`; Claude Code `--model`, `--fallback-model`, `--effort`. `effort=None`
        means "the model's own default level" (no override)."""
        self.provider = provider
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logs = Path(logs).resolve()
        self.logs.mkdir(parents=True, exist_ok=True)
        self.timeout = min(max(timeout, 1), 180)
        self.model = model or None
        self.fallback_model = fallback_model or None
        self.effort = effort
        # D-74.1: a research run gets the runtime's own web search and nothing else — Codex
        # `-c web_search="live"` (verified on codex-cli 0.142.5: `item.completed` events of type
        # `web_search`), Claude Code `--tools WebSearch,WebFetch` (verified on 2.1.283: the result's
        # `modelUsage[*].webSearchRequests`). No shell, no file tools, read-only sandbox as before.
        self.web = bool(web)
        # Called with (error, runtime version) when a run on an explicit model fails, so a refused
        # model is remembered at its first refusal from any call site (turn, plan, review, Oracle).
        self.on_refusal = None
        # Tests hand in a fake app-server connection for streamed Codex answers.
        self.connection_factory = None
        self.processes = {}
        self.lock = threading.Lock()

    def reasoning(self):
        """The reasoning level this adapter asks for ('auto' = the model's own default)."""
        if self.effort is DEFAULT_EFFORT:
            return 'low' if self.provider == 'codex' else 'auto'
        return self.effort or 'auto'

    def probe(self):
        try:
            result = subprocess.run(executable(self.provider)+['--version'], capture_output=True, text=True,
                                    encoding='utf-8', timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                                    env=child_env(self.provider))
            return dict(provider=self.provider, installed=result.returncode == 0, version=result.stdout.strip(),
                        capabilities=['text', 'native_session'], tool_access=False, native_approval_stream=False,
                        quality=None, quota=None, incremental_cost=None)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            return dict(provider=self.provider, installed=False, error=str(exc))

    def argv(self, session_id=None, stream=False):
        if self.provider == 'codex':
            if session_id:raise RuntimeError('Kel cannot resume a stored Codex session. Use the current Kel context in a new request.')
            args = executable('codex') + ['exec', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check', '--json',
                    '-c', 'approval_policy="never"', '-c', 'web_search="%s"' % ('live' if self.web else 'disabled')]
            effort = 'low' if self.effort is DEFAULT_EFFORT else self.effort
            if effort:
                args += ['-c', 'model_reasoning_effort="%s"' % effort]
            if self.model:
                args += ['-m', self.model]
            args += ['-c', 'sandbox_mode="read-only"']
            for feature in ('multi_agent', 'multi_agent_v2', 'shell_tool', 'unified_exec', 'apps', 'plugins',
                            'hooks', 'memories', 'browser_use', 'computer_use', 'image_generation',
                            'workspace_dependencies', 'goals', 'in_app_browser', 'browser_use_external'):
                args += ['--disable', feature]
            # Kel owns conversation history. Never reopen a user's persistent Codex thread.
            args += ['-s', 'read-only', '-']
            return args
        tools = ['--tools', 'WebSearch,WebFetch', '--allowedTools', 'WebSearch,WebFetch'] if self.web else ['--tools', '']
        # stream-json (one JSON record per line, the last is the same result record `json` gives) is
        # the only output format that carries Claude Code's `rate_limit_event` — how much of Nick's
        # plan is used (kel.quota). It needs --verbose in print mode.
        args = executable('claude') + ['-p', '--safe-mode'] + tools + ['--disable-slash-commands',
                '--permission-mode', 'dontAsk', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                '--output-format', 'stream-json', '--verbose', '--max-budget-usd', '0.50']
        if stream:
            # D-75.1: the reply's words as they are written.
            args += ['--include-partial-messages']
        if self.model:
            args += ['--model', self.model]
            if self.fallback_model and self.fallback_model != self.model:
                args += ['--fallback-model', self.fallback_model]
        if self.effort is not DEFAULT_EFFORT and self.effort:
            args += ['--effort', self.effort]
        if session_id:
            args += ['--resume', session_id]
        return args

    def execute(self, prompt, run_id=None, session_id=None, cancel=None, process_observer=None, on_text=None, output_schema=None, images=None):
        """Run one prompt. A per-model overlay (kel.overlays; none are registered today) is appended
        as a subordinate note and recorded on the result."""
        from .overlays import apply as apply_overlay
        prompt, overlay = apply_overlay(prompt, self.provider, self.model)
        result = self._execute(prompt, run_id, session_id, cancel, process_observer, on_text, output_schema, images)
        if overlay and isinstance(result, dict):
            result['overlay'] = overlay
        return result

    def _execute(self, prompt, run_id=None, session_id=None, cancel=None, process_observer=None, on_text=None, output_schema=None, images=None):
        """`on_text(answer so far)` (D-75.1): Claude Code streams its words through stream-json.
        `codex exec --json` reports a message only once it is complete (checked live on 0.157.1:
        thread.started, turn.started, item.completed, turn.completed — no partial events), so a
        streamed Codex answer runs through Codex's app-server instead, whose
        `item/agentMessage/delta` notifications carry the words as they are written; if the
        app-server cannot start, the answer arrives whole from exec as before."""
        if self.provider == 'codex' and session_id:
            return dict(outcome='FAILED',error='Kel cannot resume a stored Codex session. Use the current Kel context in a new request.')
        if output_schema is not None and (self.provider != 'codex' or on_text is not None):
            return dict(outcome='FAILED', error='Structured correction requires buffered Codex output.')
        if images is not None and (self.provider!='codex' or not images):
            return dict(outcome='FAILED',error='Selected native model does not support these image inputs.')
        if on_text is not None and self.provider == 'codex' and process_observer is None and images is None:
            streamed = self._codex_stream(prompt, run_id or uid(), session_id, cancel, on_text)
            if streamed is not None:
                return streamed
        run_id = run_id or uid()
        stream = on_text is not None and self.provider == 'claude'
        streamed = {'offset': 0, 'text': '', 'rest': b''}
        stdout_path, stderr_path = self.logs/(run_id+'.stdout'), self.logs/(run_id+'.stderr')
        started = time.monotonic()
        session = None
        try:
            if output_schema is not None:
                session, schema_path, final_path = _schema_session(self.logs.parent, run_id, output_schema)
            elif images is not None:
                session = _input_session(self.logs.parent,run_id)
            else:
                session = session_dir(self.logs.parent, run_id)
            image_paths = _stage_image_inputs(session,images) if images is not None else []
        except (OSError, ValueError, RuntimeError, TypeError):
            if session is not None:
                try:
                    _plain_schema_path(session,directory=True)
                    cleanup_session(session)
                except (OSError,RuntimeError):
                    pass
            return dict(outcome='FAILED', error='Private native inputs could not be verified or created.')
        env = child_env(self.provider, session=session)
        try:
            argv = self.argv(session_id, stream=stream)
            if image_paths:
                exec_index=argv.index('exec')+1
                for path,image in reversed(list(zip(image_paths,images))):
                    _verify_image_leaf(path,image['sha256'],len(base64.b64decode(image['data'],validate=True)))
                    argv[exec_index:exec_index]=['--image',str(path)]
            if output_schema is not None:
                _plain_schema_path(schema_path)
                _plain_schema_path(final_path)
                exec_index = argv.index('exec') + 1
                argv[exec_index:exec_index] = ['--output-schema', str(schema_path), '--output-last-message', str(final_path)]
            with stdout_path.open('wb') as out, stderr_path.open('wb') as err:
                process = subprocess.Popen(argv, cwd=self.workspace, stdin=subprocess.PIPE,
                    stdout=out, stderr=err, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if process_observer:
                    try:process_observer(process.pid,stdout_path,self.timeout)
                    except BaseException:
                        process.stdin.close();process.kill();process.wait(timeout=10)
                        raise
                with self.lock:
                    self.processes[run_id] = process
                process.stdin.write(prompt.encode('utf-8'))
                process.stdin.close()
                stopped = None
                while process.poll() is None:
                    if cancel and cancel.is_set():
                        stopped = 'CANCELLED'
                    elif time.monotonic()-started >= self.timeout:
                        stopped = 'TIMED_OUT'
                    elif stdout_path.stat().st_size + stderr_path.stat().st_size > 4_000_000:
                        stopped = 'OUTPUT_LIMIT'
                    if stopped:
                        process.kill()
                        process.wait(timeout=10)
                        break
                    if stream:
                        self._stream_words(stdout_path, streamed, on_text)
                    time.sleep(.1)
            output = stdout_path.read_text(encoding='utf-8', errors='replace')
            # Logs stay local. Return only bounded diagnostics; never inspect credential files.
            if stopped:
                out = dict(outcome='CANCELLED' if stopped == 'CANCELLED' else 'FAILED', error=stopped,
                           session_id=session_id, duration=time.monotonic()-started)
                try:
                    partial = self.parse(output, session_id)  # LIVE-13: tokens the run had already used
                    if partial.get('usage'):
                        out.update(usage=partial['usage'], partial=True)
                except Exception:
                    pass
                return out
            result = self.parse(output, session_id)
            if output_schema is not None and process.returncode == 0:
                if result.get('outcome') == 'SUCCESS' and 'turn.completed' in result.get('native_events', []):
                    try:
                        result['text'] = _schema_final(final_path)
                        result['structured_output'] = True
                    except (OSError, ValueError, RuntimeError, UnicodeError):
                        result.update(outcome='FAILED', text='', error='Structured correction final output is invalid.')
                else:
                    result.update(outcome='FAILED', text='', error='Structured correction native turn did not complete.')
            if process.returncode != 0:
                reported = result.get('error') if result.get('outcome') == 'FAILED' else None
                result.update(outcome='FAILED', error=f'Native CLI exited {process.returncode}; inspect local log {stderr_path.name}')
                if reported and reported not in ('Malformed native JSON', 'Native turn failed'):
                    result['error'] += ' — ' + str(reported)[:300]  # the runtime's own words
                result.pop('model_used', None)
                try:
                    # A model the runtime refused says so on stderr; keep one plain line for D-67's
                    # "record what was asked, what ran, and why".
                    tail = stderr_path.read_text(encoding='utf-8', errors='replace').strip().splitlines()
                    if tail and 'model' in tail[-1].lower() and tail[-1][:200] not in result['error']:
                        result['error'] += ' — ' + tail[-1][:200]
                except OSError:
                    pass
            elif result.get('outcome') == 'SUCCESS' and not result.get('model_used') and self.model \
                    and self.provider == 'codex':
                result['model_used'] = self.model  # Codex accepted `-m` and finished the turn with it
            if result.get('outcome') == 'SUCCESS':
                result.setdefault('reasoning_used', self.reasoning())
            result.update(duration=round(time.monotonic()-started, 3), logs=str(stdout_path), provider=self.provider)
            if image_paths:
                result['image_inputs']={'count':len(image_paths),'buffered':True}
            result.setdefault('runtime_version', runtime_version(self.provider))
            if self.provider == 'codex' and result.get('session_id') and 'rate_limits' not in result:
                try:
                    from .quota import codex_rollout_limits
                    limits = codex_rollout_limits(result['session_id'])
                    if limits:
                        result['rate_limits'] = limits  # exec's own session log (kel.quota)
                except Exception:
                    pass
            if result.get('outcome') == 'FAILED' and self.on_refusal is not None and self.model:
                try:
                    self.on_refusal(result.get('error'), result.get('runtime_version'))
                except Exception:
                    pass  # remembering a refusal is additive; the caller still sees the failure
            return result
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            return dict(outcome='FAILED', error=str(exc), provider=self.provider)
        finally:
            with self.lock:
                self.processes.pop(run_id, None)
            if session is not None:
                cleanup_session(session)

    def appserver_argv(self):
        """Codex's app-server with the same limits as `argv()`'s exec run: read-only sandbox, never
        asks for approval, no web search unless research, no shell or other tools. The app-server
        has no --ignore-user-config, so the user-config settings that would change the run (model,
        reasoning, sandbox, approvals, the turn-complete `notify` program, MCP servers) are
        overridden here and the feature switches match exec's."""
        effort = 'low' if self.effort is DEFAULT_EFFORT else self.effort
        args = executable('codex') + ['app-server', '--stdio', '-c', 'approval_policy="never"',
                '-c', 'sandbox_mode="read-only"', '-c', 'web_search="%s"' % ('live' if self.web else 'disabled'),
                '-c', 'notify=[]', '-c', 'mcp_servers={}', '-c', 'analytics.enabled=false']
        if effort:
            args += ['-c', 'model_reasoning_effort="%s"' % effort]
        for feature in ('multi_agent', 'multi_agent_v2', 'shell_tool', 'unified_exec', 'apps', 'plugins',
                        'hooks', 'memories', 'browser_use', 'computer_use', 'image_generation',
                        'workspace_dependencies', 'goals', 'in_app_browser', 'browser_use_external'):
            args += ['--disable', feature]
        return args

    def _codex_stream(self, prompt, run_id, session_id, cancel, on_text, connection_factory=None):
        """One Codex answer through the app-server, its words passed to `on_text` as they arrive
        (`item/agentMessage/delta`, protocol v2 of the installed 0.157.1). Returns the same result
        shape as `parse()`, or None when the app-server could not start (the caller then uses exec).
        Also keeps the turn's tokens (`thread/tokenUsage/updated`) and the plan's limits
        (`account/rateLimits/updated`)."""
        import queue as _queue
        if session_id:
            return self._stream_failed('Kel cannot resume a stored Codex session. Use the current Kel context in a new request.',None,time.monotonic())
        started = time.monotonic()
        factory = connection_factory or self.connection_factory
        try:require_ephemeral_codex()
        except RuntimeError as exc:return self._stream_failed(str(exc),None,started)
        try:
            if factory is not None:
                connection = factory(self)
            else:
                from .appserver import CodexConnection
                connection = CodexConnection(self.workspace, self.logs, process_argv=self.appserver_argv())
        except Exception:
            return None
        texts, order, errors = {}, [], []
        usage, limits, status, thread_id, interrupted = None, None, None, session_id, None
        shown = {'text': ''}

        def emit():
            joined = '\n'.join(texts[key] for key in order if texts.get(key))
            if joined and joined != shown['text']:
                shown['text'] = joined
                try:
                    on_text(joined)
                except Exception:
                    pass  # showing words early is additive; the run's result is unchanged

        try:
            thread = {'cwd': str(self.workspace), 'sandbox': 'read-only', 'approvalPolicy': 'never', 'ephemeral': True}
            if self.model:
                thread['model'] = self.model
            try:
                response = connection.call('thread/start', thread)
                if ((response or {}).get('thread') or {}).get('ephemeral') is not True:
                    raise RuntimeError('Codex did not confirm a private temporary session. No Kel prompt was sent.')
            except RuntimeError as exc:
                return self._stream_failed(str(exc), session_id, started)
            thread_id = ((response or {}).get('thread') or {}).get('id') or session_id
            turn = {'threadId': thread_id, 'input': [{'type': 'text', 'text': prompt}]}
            effort = 'low' if self.effort is DEFAULT_EFFORT else self.effort
            if effort:
                turn['effort'] = effort
            try:
                response = connection.call('turn/start', turn)
            except RuntimeError as exc:
                return self._stream_failed(str(exc), thread_id, started)
            turn_id = ((response or {}).get('turn') or {}).get('id')
            while True:
                if interrupted is None and ((cancel and cancel.is_set()) or time.monotonic() - started >= self.timeout):
                    interrupted = ('CANCELLED' if cancel and cancel.is_set() else 'TIMED_OUT', time.monotonic())
                    try:
                        connection.call('turn/interrupt', {'threadId': thread_id, 'turnId': turn_id}, timeout=10)
                    except Exception:
                        pass
                if interrupted and time.monotonic() - interrupted[1] > 20:
                    break
                try:
                    event = connection.events.get(timeout=.1)
                except _queue.Empty:
                    continue
                method = event.get('method', '')
                params = event.get('params') or {}
                if 'id' in event:
                    # A read-only, never-ask run has nothing to approve; anything asked is declined.
                    connection.send({'id': event['id'], 'error': {'code': -32601,
                                                                  'message': 'Unsupported Kel interaction'}})
                    continue
                if params.get('threadId', thread_id) != thread_id:
                    continue
                if method == 'item/agentMessage/delta' and isinstance(params.get('delta'), str):
                    key = params.get('itemId') or '-'
                    if key not in texts:
                        order.append(key)
                        texts[key] = ''
                    texts[key] += params['delta']
                    emit()
                elif method == 'item/completed' and (params.get('item') or {}).get('type') == 'agentMessage':
                    item = params['item']
                    key = item.get('id') or '-'
                    if key not in texts:
                        order.append(key)
                    texts[key] = item.get('text') or texts.get(key, '')
                    emit()
                elif method == 'thread/tokenUsage/updated':
                    info = params.get('tokenUsage') if isinstance(params.get('tokenUsage'), dict) else {}
                    if isinstance(info.get('last'), dict):
                        usage = dict(info['last'])  # this turn's share (inputTokens includes cached)
                elif method == 'account/rateLimits/updated':
                    from .quota import from_codex
                    limits = from_codex(params.get('rateLimits'), 'Codex account/rateLimits/updated') or limits
                elif method == 'error':
                    nested = params.get('error')
                    message = nested.get('message') if isinstance(nested, dict) else nested
                    if not params.get('willRetry'):
                        errors.append(str(message or 'Native turn failed'))
                elif method == 'turn/completed':
                    done = params.get('turn') or {}
                    status = done.get('status')
                    failure = done.get('error')
                    if isinstance(failure, dict):
                        failure = failure.get('message')
                    if failure:
                        errors.append(str(failure))
                    break
                elif method == 'kel/connectionClosed':
                    errors.append('Codex app-server closed')
                    status = 'failed'
                    break
        finally:
            try:
                connection.close()
            except Exception:
                pass
        text = '\n'.join(texts[key] for key in order if texts.get(key))
        if interrupted:
            out = dict(outcome='CANCELLED' if interrupted[0] == 'CANCELLED' else 'FAILED', error=interrupted[0],
                       session_id=thread_id, duration=round(time.monotonic() - started, 3))
        else:
            ok = bool(status == 'completed' and text and not errors)
            out = dict(outcome='SUCCESS' if ok else 'FAILED', text=text, session_id=thread_id,
                       native_status=status, duration=round(time.monotonic() - started, 3), streamed=True,
                       error=None if ok else ('; '.join(dict.fromkeys(errors)) or 'Native turn failed'))
            if ok:
                if self.model:
                    out['model_used'] = self.model
                out['reasoning_used'] = self.reasoning()
        if usage is not None:
            out['usage'] = usage
        if limits:
            out['rate_limits'] = limits
        out['provider'] = self.provider
        out.setdefault('runtime_version', runtime_version(self.provider))
        if out.get('outcome') == 'FAILED' and self.on_refusal is not None and self.model:
            try:
                self.on_refusal(out.get('error'), out.get('runtime_version'))
            except Exception:
                pass
        return out

    def _stream_failed(self, error, session_id, started):
        out = dict(outcome='FAILED', error=str(error)[:500], session_id=session_id, provider=self.provider,
                   duration=round(time.monotonic() - started, 3), runtime_version=runtime_version(self.provider))
        if self.on_refusal is not None and self.model:
            try:
                self.on_refusal(out['error'], out['runtime_version'])
            except Exception:
                pass
        return out

    @staticmethod
    def _stream_words(stdout_path, streamed, on_text):
        """Read Claude Code's new stream-json lines and pass the answer so far to `on_text`."""
        try:
            with stdout_path.open('rb') as handle:
                handle.seek(streamed['offset'])
                chunk = handle.read()
        except OSError:
            return
        if not chunk:
            return
        streamed['offset'] += len(chunk)
        lines = (streamed['rest'] + chunk).split(b'\n')
        streamed['rest'] = lines.pop()
        grew = False
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            event = record.get('event') if isinstance(record, dict) and record.get('type') == 'stream_event' else None
            delta = (event or {}).get('delta') if isinstance(event, dict) and event.get('type') == 'content_block_delta' else None
            if isinstance(delta, dict) and delta.get('type') == 'text_delta' and isinstance(delta.get('text'), str):
                streamed['text'] += delta['text']
                grew = True
        if grew:
            try:
                on_text(streamed['text'])
            except Exception:
                pass  # showing words early is additive; the run's result is unchanged

    def parse(self, output, session_id=None):
        if self.provider == 'claude':
            try:
                record = json.loads(output)
            except json.JSONDecodeError:
                # D-75.1: a streamed run ends with the same result record on its last line.
                record = None
                for line in reversed(output.splitlines()):
                    try:
                        candidate = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(candidate, dict) and candidate.get('type') == 'result':
                        record = candidate
                        break
                if record is None:
                    return dict(outcome='FAILED', error='Malformed native JSON')
            limits = None
            if '"rate_limit_event"' in output:
                from .quota import from_claude
                for line in output.splitlines():
                    if '"rate_limit_event"' not in line:
                        continue
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(event, dict) and event.get('type') == 'rate_limit_event':
                        limits = from_claude(event.get('rate_limit_info')) or limits
            usage_by_model = record.get('modelUsage') if isinstance(record.get('modelUsage'), dict) else {}
            used = None
            searches = sum(int((entry or {}).get('webSearchRequests') or 0) for entry in usage_by_model.values()
                           if isinstance(entry, dict))
            if usage_by_model:
                # The model that did the work: the one with the most output (Claude Code may also
                # call a small helper model — for web research that helper runs the searches, so a
                # model that only searched is not the one that wrote the answer).
                writers = [name for name in usage_by_model
                           if not ((usage_by_model[name] or {}).get('webSearchRequests') or 0)] or list(usage_by_model)
                used = max(writers, key=lambda name: (usage_by_model[name] or {}).get('outputTokens') or 0)
            out = dict(outcome='FAILED' if record.get('is_error') else 'SUCCESS',
                       text=record.get('result', ''), session_id=record.get('session_id', session_id),
                       usage=record.get('usage'), cost_usd=record.get('total_cost_usd'),
                       native_subtype=record.get('subtype'))
            if isinstance(record.get('duration_ms'), (int, float)):
                out['runtime_ms'] = int(record['duration_ms'])
            if record.get('is_error') and record.get('result'):
                out['error'] = str(record.get('result'))[:500]
            if used:
                out['model_used'] = used
            if self.web:
                out['searches'] = searches
            if limits:
                out['rate_limits'] = limits
            return out
        text, events, errors = [], [], []
        usage = None
        queries = []
        for line in output.splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            events.append(record.get('type'))
            if record.get('type') == 'thread.started':
                session_id = record.get('thread_id')
            item = record.get('item', {})
            if record.get('type') == 'item.completed' and item.get('type') == 'web_search':
                action = item.get('action') if isinstance(item.get('action'), dict) else {}
                queries.append(str(item.get('query') or action.get('query') or '')[:200])
            if record.get('type') == 'item.completed' and item.get('type') == 'agent_message':
                text.append(item.get('text', ''))
            if record.get('type') == 'turn.completed' and isinstance(record.get('usage'), dict):
                # Codex exec reports the turn's tokens here (input includes the cached part).
                usage = dict(record['usage'])
            if record.get('type') in ('error', 'turn.failed'):
                # The live check: a refused model arrives as {"type":"turn.failed","error":{"message":…}};
                # reading only a top-level message turned every refusal into "Native turn failed".
                nested = record.get('error')
                message = record.get('message') or (nested.get('message') if isinstance(nested, dict)
                                                    else nested if isinstance(nested, str) else None)
                errors.append(str(message or 'Native turn failed'))
        out = dict(outcome='SUCCESS' if text and not errors else 'FAILED', text='\n'.join(text),
                   session_id=session_id, native_events=events, error='; '.join(dict.fromkeys(errors)) or None)
        if usage is not None:
            out['usage'] = usage
        if self.web:
            out.update(searches=len(queries), queries=[q for q in queries if q])
        return out


class FixtureAdapter:
    """Deterministic fault injection only. Never represented as a real model."""
    provider = 'fixture'
    def __init__(self, output='## Result\nFixture evidence.', fail_first=False, delay=0):
        self.output, self.fail_first, self.delay = output, fail_first, delay
        self.calls = 0

    def execute(self, prompt, run_id=None, session_id=None, cancel=None):
        self.calls += 1
        if cancel and cancel.wait(self.delay):
            return dict(outcome='CANCELLED', error='Cancelled fixture')
        return dict(outcome='SUCCESS', text='wrong output' if self.fail_first and self.calls == 1 else self.output,
                    session_id=session_id or uid(), fixture=True)
