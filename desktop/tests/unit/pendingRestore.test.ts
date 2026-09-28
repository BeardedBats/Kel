/**
 * FN-02 — the main process applies a staged restore first thing at start, before initStorage,
 * aioncore, the engine or the window open the data, and never leaves a restore to loop.
 */
import { spawnSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  RESTORE_JOURNAL,
  RESTORE_MARKER,
  RESTORE_OUTCOME,
  RESTORE_OWNER_ENV,
  RESTORE_STAGING,
  applyPendingRestoreAtStartup,
  restoreEngineRoot,
} from '@process/startup/pendingRestore';

const repoRuntime = path.resolve(__dirname, '../../../runtime');
let tmp: string;
let engineRoot: string;
let resources: string;

const outcome = () => JSON.parse(fs.readFileSync(path.join(engineRoot, RESTORE_OUTCOME), 'utf8'));
const stage = () => {
  fs.mkdirSync(path.join(engineRoot, RESTORE_STAGING, 'engine'), { recursive: true });
  fs.writeFileSync(path.join(engineRoot, RESTORE_MARKER), JSON.stringify({ id: 'x', format: 2, staged: 1 }));
};

beforeEach(() => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-restore-'));
  engineRoot = path.join(tmp, 'Data', 'engine');
  resources = path.join(tmp, 'resources');
  fs.mkdirSync(engineRoot, { recursive: true });
  fs.mkdirSync(resources, { recursive: true });
});
afterEach(() => {
  fs.rmSync(tmp, { recursive: true, force: true });
});

describe('applyPendingRestoreAtStartup', () => {
  it('does nothing when no restore is staged, but still claims restores for the shell', () => {
    const env: NodeJS.ProcessEnv = {};
    const run = vi.fn();
    expect(applyPendingRestoreAtStartup({ engineRoot, resourcesPath: resources, env, run, log: () => {} })).toEqual({
      ran: false,
    });
    expect(run).not.toHaveBeenCalled();
    expect(env[RESTORE_OWNER_ENV]).toBe('shell'); // the engine, spawned later, never applies one
  });

  it('runs the packed engine applier on the engine folder and reports what it did', () => {
    stage();
    const exe = path.join(resources, 'kel-engine', 'KelEngine.exe');
    fs.mkdirSync(path.dirname(exe), { recursive: true });
    fs.writeFileSync(exe, '');
    const env: NodeJS.ProcessEnv = {};
    const run = vi.fn(() => ({
      status: 0,
      stdout: 'noise\n{"ran": true, "ok": true, "status": "restored"}\n',
      stderr: '',
      error: undefined,
    }));
    const result = applyPendingRestoreAtStartup({ engineRoot, resourcesPath: resources, env, run, log: () => {} });
    expect(result).toEqual({ ran: true, ok: true, status: 'restored', part: undefined });
    expect(run).toHaveBeenCalledWith(exe, ['--apply-restore', '--data', engineRoot], {
      cwd: path.dirname(exe),
      env: expect.objectContaining({ [RESTORE_OWNER_ENV]: 'shell' }),
    });
  });

  it('ends the attempt itself when the applier cannot run: nothing moved, never retried', () => {
    stage();
    const run = vi.fn(() => {
      throw new Error('ENOENT python');
    });
    const result = applyPendingRestoreAtStartup({ engineRoot, resourcesPath: resources, env: {}, run, log: () => {} });
    expect(result.status).toBe('not_started');
    expect(fs.existsSync(path.join(engineRoot, RESTORE_MARKER))).toBe(false);
    expect(fs.existsSync(path.join(engineRoot, RESTORE_STAGING))).toBe(false);
    const recorded = outcome();
    expect(recorded).toMatchObject({ ok: false, status: 'not_started', notice: true });
    expect(recorded.detail).toContain('nothing was replaced');
    expect(recorded.detail).not.toContain('ENOENT');
    expect(recorded.technical).toContain('ENOENT');
  });

  it('never re-applies after a crash mid-swap: the marker goes, the journal stays for the undo', () => {
    stage();
    fs.writeFileSync(path.join(engineRoot, RESTORE_JOURNAL), JSON.stringify({ state: 'swapping', moves: [] }));
    const run = vi.fn(() => ({ status: 3221225477, stdout: '', stderr: 'crash', error: undefined }));
    const result = applyPendingRestoreAtStartup({ engineRoot, resourcesPath: resources, env: {}, run, log: () => {} });
    expect(result.status).toBe('rollback_incomplete');
    expect(fs.existsSync(path.join(engineRoot, RESTORE_MARKER))).toBe(false);
    expect(fs.existsSync(path.join(engineRoot, RESTORE_JOURNAL))).toBe(true);
    expect(outcome().title).toBe('A restore stopped partway');
  });

  it('drives the real engine applier from source (python -m kel.backup)', () => {
    const probe = spawnSync(process.env.KEL_PYTHON || 'python', ['--version'], { encoding: 'utf8' });
    if (probe.status !== 0 || !fs.existsSync(path.join(repoRuntime, 'kel', 'backup.py'))) return;
    // A marker whose staged copy is gone: the applier ends the attempt and says so.
    fs.writeFileSync(path.join(engineRoot, RESTORE_MARKER), JSON.stringify({ id: 'x', format: 2, staged: 1 }));
    const env: NodeJS.ProcessEnv = { ...process.env };
    const result = applyPendingRestoreAtStartup({
      engineRoot,
      resourcesPath: resources,
      sourceRoot: repoRuntime,
      env,
      log: () => {},
    });
    expect(result).toMatchObject({ ran: true, ok: false, status: 'not_started' });
    expect(fs.existsSync(path.join(engineRoot, RESTORE_MARKER))).toBe(false);
    expect(outcome().detail).toContain('your data is unchanged');
  }, 60000);

  it('uses the same engine folder as KelService', () => {
    expect(restoreEngineRoot({ KEL_DATA_DIR: 'D:\\Data\\engine' }, 'C:\\AppData')).toBe('D:\\Data\\engine');
    expect(restoreEngineRoot({}, 'C:\\AppData')).toBe(path.join('C:\\AppData', 'kel-desktop', 'work'));
  });
});

describe('startup ordering (FN-02)', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../../packages/desktop/src/index.ts'), 'utf8');
  const ready = source.slice(source.indexOf('const handleAppReady = async'));
  const body = ready.slice(0, ready.indexOf('\n};\n'));
  const at = (needle: string) => {
    const index = body.indexOf(needle);
    expect(index, needle).toBeGreaterThan(-1);
    return index;
  };

  it('applies the restore before initStorage, aioncore, the engine and the window', () => {
    const restore = at('applyPendingRestoreAtStartup(');
    expect(restore).toBeLessThan(at('await initializeProcess()'));
    expect(restore).toBeLessThan(at('startBackendOrExit('));
    expect(restore).toBeLessThan(at('initializeKel('));
    expect(restore).toBeLessThan(at('createWindow('));
  });

  it('runs only in the instance that holds the single-instance lock', () => {
    expect(source).toMatch(/if \(shouldRegisterBackendStartup\(gotTheLock\)\) \{[\s\S]*?handleAppReady\(\)/);
    expect(source.indexOf('applyPendingRestoreAtStartup(')).toBeGreaterThan(source.indexOf('const handleAppReady'));
  });
});
