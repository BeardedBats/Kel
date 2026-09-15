"""PKG-04: frozen V1.2 data upgrades safely under the packaged V1.3 engine.

Creates a V1.2-era data directory with the FROZEN V1.2 KelEngine, copies it, opens the copy
with the packaged V1.3 KelEngine, and verifies: one-time backup + integrity receipt, applied
migration rows 1-4, and intact V1.2 conversations/messages/approvals.

Usage: python verify-v12-upgrade.py <frozen-tree> <v13-engine-exe> <work-dir>
"""
import contextlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def wait_descriptor(data_dir, timeout=60):
    path = Path(data_dir) / 'desktop-session.json'
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding='utf-8'))
            except ValueError:
                pass
        time.sleep(0.4)
    raise TimeoutError('descriptor not written: ' + str(data_dir))


def call(descriptor, route, payload=None):
    request = urllib.request.Request(
        descriptor['url'].rstrip('/') + route,
        data=json.dumps(payload).encode() if payload is not None else None,
        method='POST' if payload is not None else 'GET')
    request.add_header('Authorization', 'Bearer ' + descriptor['token'])
    if payload is not None:
        request.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def boot(engine_exe, data_dir):
    env = dict(os.environ)
    env['KEL_SKIP_TELEMETRY'] = '1'
    stale = Path(data_dir) / 'desktop-session.json'
    if stale.exists():
        stale.unlink()
    proc = subprocess.Popen([str(engine_exe), '--data', str(data_dir), '--port', '0'],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 60
    descriptor = None
    while time.time() < deadline:
        try:
            candidate = wait_descriptor(data_dir, timeout=5)
        except TimeoutError:
            continue
        if candidate.get('pid') == proc.pid:
            descriptor = candidate
            break
    if descriptor is None:
        raise TimeoutError('engine did not own the descriptor: ' + str(data_dir))
    time.sleep(1.0)
    return proc, descriptor


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main():
    frozen = Path(sys.argv[1])
    v13_engine = Path(sys.argv[2])
    work = Path(sys.argv[3])
    src = work / 'v12-src'
    dst = work / 'v12-upgraded'
    for target in (src, dst):
        if target.exists():
            shutil.rmtree(target)
    src.mkdir(parents=True)
    results = {}

    # 1. Build a V1.2-era data directory with the frozen engine.
    v12_proc, v12_desc = boot(frozen / 'resources' / 'kel-engine' / 'KelEngine.exe', src)
    try:
        call(v12_desc, '/api/conversation', {'project': 'default'})
        call(v12_desc, '/api/send', {'text': 'status', 'conversation': 'main'})
        time.sleep(1.0)
        with contextlib.closing(sqlite3.connect(str(src / 'kel.sqlite3'))) as db:
            cols = [c[1] for c in db.execute('PRAGMA table_info(approvals)')]
            values = {'id': 'v12-approval', 'status': 'CANCELLED',
                      'action_digest': 'legacy-digest'}
            use = {k: v for k, v in values.items() if k in cols}
            db.execute('INSERT OR IGNORE INTO approvals (%s) VALUES (%s)'
                       % (','.join(use), ','.join('?' * len(use))), list(use.values()))
            db.commit()
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        results['v12_schema_migrations_absent'] = 'schema_migrations' not in tables
    finally:
        stop(v12_proc)

    # 2. Upgrade a copy with the packaged V1.3 engine.
    shutil.copytree(src, dst)
    v13_proc, v13_desc = boot(v13_engine, dst)
    try:
        status, state = call(v13_desc, '/api/state?conversation=main')
        results['state_ok'] = status == 200
        results['conversations'] = len(state.get('conversations', []))
        results['messages'] = len(state.get('messages', []))
        results['engine_version'] = state.get('engine_version')
        with contextlib.closing(sqlite3.connect(str(dst / 'kel.sqlite3'))) as db:
            rows = [row[0] for row in db.execute(
                'SELECT version FROM schema_migrations ORDER BY version')]
            results['migrations'] = rows
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            results['memories_table'] = 'memories' in tables
            results['job_links_table'] = 'job_links' in tables
            results['recipes_table'] = 'recipes' in tables
            results['project_maps_table'] = 'project_maps' in tables
            legacy = db.execute("SELECT status FROM approvals WHERE id='v12-approval'").fetchone()
            results['legacy_approval_intact'] = bool(legacy) and legacy[0] == 'CANCELLED'
            old_messages = db.execute('SELECT count(*) FROM messages').fetchone()[0]
            results['legacy_messages_preserved'] = old_messages >= len(state.get('messages', [])) and old_messages > 0
        backups = sorted((dst / 'backups').glob('pre-v13-*.sqlite3'))
        results['backup_created'] = len(backups) == 1
        receipt_path = dst / 'migration-receipt.json'
        results['receipt_created'] = receipt_path.is_file()
        if receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            results['receipt_integrity'] = receipt.get('integrity')
    finally:
        stop(v13_proc)

    print(json.dumps({'schema': 1, 'results': results}, indent=2))


if __name__ == '__main__':
    main()
