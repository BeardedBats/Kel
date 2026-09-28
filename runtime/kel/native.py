"""Real native CLI adapters. No shell invocation; native tools disabled.

This first compatibility slice accepts text output only. It does not claim native
edit, ACP permission streaming, cost metering or arbitrary tool isolation.
"""
from __future__ import annotations
import json
import os
import re
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


class NativeAdapter:
    def __init__(self, provider, workspace, logs, timeout=100, model=None, effort=DEFAULT_EFFORT,
                 fallback_model=None):
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
        # Called with (error, runtime version) when a run on an explicit model fails, so a refused
        # model is remembered at its first refusal from any call site (turn, plan, review, Oracle).
        self.on_refusal = None
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
            args = executable('codex') + ['exec', '--ignore-user-config', '--skip-git-repo-check', '--json',
                    '-c', 'approval_policy="never"', '-c', 'web_search="disabled"']
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
            if session_id:
                args += ['resume', session_id, '-']
            else:
                args += ['-s', 'read-only', '-']
            return args
        args = executable('claude') + ['-p', '--safe-mode', '--tools', '', '--disable-slash-commands',
                '--permission-mode', 'dontAsk', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                '--output-format', 'json', '--max-budget-usd', '0.50']
        if stream:
            # D-75.1: the reply's words as they are written (the last line is the same result record).
            args[args.index('--output-format') + 1] = 'stream-json'
            args += ['--verbose', '--include-partial-messages']
        if self.model:
            args += ['--model', self.model]
            if self.fallback_model and self.fallback_model != self.model:
                args += ['--fallback-model', self.fallback_model]
        if self.effort is not DEFAULT_EFFORT and self.effort:
            args += ['--effort', self.effort]
        if session_id:
            args += ['--resume', session_id]
        return args

    def execute(self, prompt, run_id=None, session_id=None, cancel=None, process_observer=None, on_text=None):
        """`on_text(answer so far)` (D-75.1): Claude Code streams its words; Codex exec reports a
        message only once it is complete, so its answer arrives whole."""
        run_id = run_id or uid()
        stream = on_text is not None and self.provider == 'claude'
        streamed = {'offset': 0, 'text': '', 'rest': b''}
        stdout_path, stderr_path = self.logs/(run_id+'.stdout'), self.logs/(run_id+'.stderr')
        started = time.monotonic()
        session = session_dir(self.logs.parent, run_id)
        env = child_env(self.provider, session=session)
        try:
            with stdout_path.open('wb') as out, stderr_path.open('wb') as err:
                process = subprocess.Popen(self.argv(session_id, stream=stream), cwd=self.workspace, stdin=subprocess.PIPE,
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
                return dict(outcome='CANCELLED' if stopped == 'CANCELLED' else 'FAILED', error=stopped,
                            session_id=session_id, duration=time.monotonic()-started)
            result = self.parse(output, session_id)
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
            result.setdefault('runtime_version', runtime_version(self.provider))
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
            cleanup_session(session)

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
            usage_by_model = record.get('modelUsage') if isinstance(record.get('modelUsage'), dict) else {}
            used = None
            if usage_by_model:
                # The model that did the work: the one with the most output (Claude Code may also
                # call a small helper model).
                used = max(usage_by_model, key=lambda name: (usage_by_model[name] or {}).get('outputTokens') or 0)
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
            return out
        text, events, errors = [], [], []
        usage = None
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
