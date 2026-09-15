"""Real native CLI adapters. No shell invocation; native tools disabled.

This first compatibility slice accepts text output only. It does not claim native
edit, ACP permission streaming, cost metering or arbitrary tool isolation.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from .core import uid


def executable(provider):
    if provider == 'codex':
        return [shutil.which('codex') or 'codex']
    if provider == 'claude':
        candidate = Path(os.environ.get('APPDATA', '')) / 'npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe'
        if candidate.is_file():
            return [str(candidate)]
        path = shutil.which('claude')
        if path and Path(path).suffix.lower() not in ('.cmd', '.ps1', '.bat'):
            return [path]
        raise RuntimeError('Native Claude executable unavailable; shell wrappers are not used')
    raise ValueError('Unknown native provider')


class NativeAdapter:
    def __init__(self, provider, workspace, logs, timeout=100):
        self.provider = provider
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logs = Path(logs).resolve()
        self.logs.mkdir(parents=True, exist_ok=True)
        self.timeout = min(max(timeout, 1), 180)
        self.processes = {}
        self.lock = threading.Lock()

    def probe(self):
        try:
            result = subprocess.run(executable(self.provider)+['--version'], capture_output=True, text=True,
                                    encoding='utf-8', timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            return dict(provider=self.provider, installed=result.returncode == 0, version=result.stdout.strip(),
                        capabilities=['text', 'native_session'], tool_access=False, native_approval_stream=False,
                        quality=None, quota=None, incremental_cost=None)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            return dict(provider=self.provider, installed=False, error=str(exc))

    def argv(self, session_id=None):
        if self.provider == 'codex':
            args = executable('codex') + ['exec', '--ignore-user-config', '--skip-git-repo-check', '--json',
                    '-c', 'approval_policy="never"', '-c', 'web_search="disabled"', '-c', 'model_reasoning_effort="low"',
                    '-c', 'sandbox_mode="read-only"']
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
        if session_id:
            args += ['--resume', session_id]
        return args

    def execute(self, prompt, run_id=None, session_id=None, cancel=None, process_observer=None):
        run_id = run_id or uid()
        stdout_path, stderr_path = self.logs/(run_id+'.stdout'), self.logs/(run_id+'.stderr')
        started = time.monotonic()
        env = os.environ.copy()
        env.pop('CLAUDECODE', None)
        # Do not forward unrelated provider keys into a native worker.
        if self.provider == 'codex':
            env.pop('ANTHROPIC_API_KEY', None)
        else:
            env.pop('OPENAI_API_KEY', None)
        try:
            with stdout_path.open('wb') as out, stderr_path.open('wb') as err:
                process = subprocess.Popen(self.argv(session_id), cwd=self.workspace, stdin=subprocess.PIPE,
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
                    time.sleep(.1)
            output = stdout_path.read_text(encoding='utf-8', errors='replace')
            # Logs stay local. Return only bounded diagnostics; never inspect credential files.
            if stopped:
                return dict(outcome='CANCELLED' if stopped == 'CANCELLED' else 'FAILED', error=stopped,
                            session_id=session_id, duration=time.monotonic()-started)
            result = self.parse(output, session_id)
            if process.returncode != 0:
                result.update(outcome='FAILED', error=f'Native CLI exited {process.returncode}; inspect local log {stderr_path.name}')
            result.update(duration=round(time.monotonic()-started, 3), logs=str(stdout_path), provider=self.provider)
            return result
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            return dict(outcome='FAILED', error=str(exc), provider=self.provider)
        finally:
            with self.lock:
                self.processes.pop(run_id, None)

    def parse(self, output, session_id=None):
        if self.provider == 'claude':
            try:
                record = json.loads(output)
            except json.JSONDecodeError:
                return dict(outcome='FAILED', error='Malformed native JSON')
            return dict(outcome='FAILED' if record.get('is_error') else 'SUCCESS',
                        text=record.get('result', ''), session_id=record.get('session_id', session_id),
                        usage=record.get('usage'), cost_usd=record.get('total_cost_usd'),
                        native_subtype=record.get('subtype'))
        text, events, errors = [], [], []
        for line in output.splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(record.get('type'))
            if record.get('type') == 'thread.started':
                session_id = record.get('thread_id')
            item = record.get('item', {})
            if record.get('type') == 'item.completed' and item.get('type') == 'agent_message':
                text.append(item.get('text', ''))
            if record.get('type') in ('error', 'turn.failed'):
                errors.append(record.get('message', 'Native turn failed'))
        return dict(outcome='SUCCESS' if text and not errors else 'FAILED', text='\n'.join(text),
                    session_id=session_id, native_events=events, error='; '.join(errors) or None)


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
