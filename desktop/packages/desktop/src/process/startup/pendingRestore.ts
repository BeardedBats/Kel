/**
 * FN-02 — apply a staged restore at the one safe moment: first thing at start, before initStorage,
 * aioncore (the chat store), the Kel engine or any window opens the data.
 *
 * The restore used to be applied inside the engine, after Kel.exe and aioncore already held the chat
 * store and host files open. It failed partway, kept its pending marker on purpose, and re-applied
 * the engine part on every later start (a rename made after it reverted, a stopped job came back,
 * and each start added another set of `*.pre-restore-*` folders).
 *
 * Now the main process runs the engine's all-or-nothing applier (`KelEngine.exe --apply-restore`, or
 * `python -m kel.backup --apply-restore` from source) synchronously before anything else, and sets
 * `KEL_RESTORE_OWNER=shell` so the engine itself never applies a restore. The applier swaps every
 * part by renames, undoes them all if one fails, and always ends the attempt: the marker is cleared
 * and `restore-outcome.json` says in plain words what happened. If the applier cannot run at all,
 * this module ends the attempt itself — a staged restore is never left to loop.
 */
import { spawnSync, type SpawnSyncReturns } from 'child_process';
import fs from 'fs';
import path from 'path';

export const RESTORE_MARKER = 'restore-pending.json';
export const RESTORE_STAGING = '.restore-staging';
export const RESTORE_JOURNAL = 'restore-journal.json';
export const RESTORE_OUTCOME = 'restore-outcome.json';
export const RESTORE_OWNER_ENV = 'KEL_RESTORE_OWNER';
const APPLY_TIMEOUT_MS = 5 * 60 * 1000;

export type RestoreStartupResult = {
  ran: boolean;
  ok?: boolean;
  status?: string;
  part?: string;
};

type Runner = (
  command: string,
  args: string[],
  options: { cwd: string; env: NodeJS.ProcessEnv }
) => Pick<SpawnSyncReturns<string>, 'status' | 'stdout' | 'stderr' | 'error'>;

export interface PendingRestoreOptions {
  /** The engine's data root (KEL_DATA_DIR): where the marker, staging and outcome live. */
  engineRoot: string;
  resourcesPath: string;
  /** Source checkout's runtime folder, used when there is no packed engine (development). */
  sourceRoot?: string;
  env?: NodeJS.ProcessEnv;
  run?: Runner;
  log?: (message: string) => void;
}

/** The engine root the main process and the engine agree on (KelService's `kelDataRoot`). */
export function restoreEngineRoot(env: NodeJS.ProcessEnv, appDataPath: string): string {
  return env.KEL_DATA_DIR || path.join(appDataPath, 'kel-desktop', 'work');
}

/** A restore is waiting to be applied, or an interrupted one still has moves to undo. */
export function restoreIsPending(engineRoot: string): boolean {
  return fs.existsSync(path.join(engineRoot, RESTORE_MARKER)) || fs.existsSync(path.join(engineRoot, RESTORE_JOURNAL));
}

function applierCommand(options: PendingRestoreOptions, env: NodeJS.ProcessEnv) {
  const packed = path.join(options.resourcesPath, 'kel-engine', 'KelEngine.exe');
  const args = ['--apply-restore', '--data', options.engineRoot];
  if (fs.existsSync(packed)) return { command: packed, args, cwd: path.dirname(packed), env };
  const source = options.sourceRoot || env.KEL_SOURCE_ROOT || path.resolve(process.cwd(), '../runtime');
  return {
    command: env.KEL_PYTHON || 'python',
    args: ['-X', 'utf8', '-m', 'kel.backup', ...args],
    cwd: source,
    env: { ...env, PYTHONPATH: source },
  };
}

const defaultRun: Runner = (command, args, options) =>
  spawnSync(command, args, {
    cwd: options.cwd,
    env: options.env,
    encoding: 'utf8',
    windowsHide: true,
    timeout: APPLY_TIMEOUT_MS,
  });

function lastJson(stdout: string | null | undefined): Record<string, unknown> | null {
  const lines = String(stdout || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      const parsed = JSON.parse(lines[index]);
      if (parsed && typeof parsed === 'object') return parsed as Record<string, unknown>;
    } catch {
      // not the applier's report line
    }
  }
  return null;
}

/** The same record the engine writes (backup._record_outcome), for when the applier never ran. */
function recordOutcome(engineRoot: string, fields: Record<string, unknown>): void {
  try {
    fs.writeFileSync(
      path.join(engineRoot, RESTORE_OUTCOME),
      JSON.stringify({ version: 2, ok: false, at: Date.now() / 1000, notice: true, ...fields }),
      'utf8'
    );
  } catch {
    // Recording must never stop Kel from starting.
  }
}

/**
 * End an attempt the applier could not finish: the restore is never re-applied. With no journal,
 * nothing was moved (the applier writes the journal before its first move), so the data is
 * unchanged; with a journal, the engine's applier undoes the recorded moves on the next start.
 */
function endAttempt(engineRoot: string, technical: string): RestoreStartupResult {
  const moved = fs.existsSync(path.join(engineRoot, RESTORE_JOURNAL));
  try {
    fs.rmSync(path.join(engineRoot, RESTORE_MARKER), { force: true });
    if (!moved) fs.rmSync(path.join(engineRoot, RESTORE_STAGING), { recursive: true, force: true });
  } catch {
    // Best effort: the outcome below still tells the truth.
  }
  if (moved) {
    recordOutcome(engineRoot, {
      status: 'rollback_incomplete',
      title: 'A restore stopped partway',
      detail:
        'Kel could not finish restoring your backup and has not put everything back yet. Nothing was deleted: ' +
        'your data from before the restore is in the "Kel data before restore" folder beside your data folder. ' +
        'Kel will put it back the next time it starts; keep that folder until this message is gone.',
      technical,
    });
    return { ran: true, ok: false, status: 'rollback_incomplete' };
  }
  recordOutcome(engineRoot, {
    status: 'not_started',
    title: 'Kel could not restore your backup',
    detail:
      'Kel could not start its restore step, so nothing was replaced — your data is unchanged. ' +
      "Choose Restore again in Settings → System. If it fails again, the details help Kel's team.",
    technical,
  });
  return { ran: true, ok: false, status: 'not_started' };
}

/**
 * Run before anything opens the data. Synchronous on purpose: nothing else may start until the
 * restore is applied or rolled back. Always leaves `KEL_RESTORE_OWNER=shell` in the environment so
 * the engine (spawned later, inheriting it) never applies a restore on its own.
 */
export function applyPendingRestoreAtStartup(options: PendingRestoreOptions): RestoreStartupResult {
  const env = options.env ?? process.env;
  env[RESTORE_OWNER_ENV] = 'shell';
  const log = options.log ?? ((message: string) => console.log(`[KEL-RESTORE] ${message}`));
  if (!restoreIsPending(options.engineRoot)) return { ran: false };
  const spec = applierCommand(options, env);
  log(`applying the staged restore before start (${path.basename(spec.command)})`);
  const run = options.run ?? defaultRun;
  let result: ReturnType<Runner>;
  try {
    result = run(spec.command, spec.args, { cwd: spec.cwd, env: spec.env });
  } catch (error) {
    log(`the restore step could not run: ${String(error)}`);
    return endAttempt(options.engineRoot, `spawn failed: ${String((error as Error)?.message || error)}`.slice(0, 300));
  }
  const report = lastJson(result.stdout);
  if (result.error || result.status !== 0 || !report || report.status === 'crashed') {
    const technical = String(
      result.error?.message || report?.technical || `exit ${result.status}: ${String(result.stderr || '').slice(-200)}`
    ).slice(0, 300);
    log(`the restore step did not finish: ${technical}`);
    // The applier may have recorded the attempt before failing; ending it again is harmless, and a
    // marker that is still there must not survive to the next start.
    if (!restoreIsPending(options.engineRoot)) return { ran: true, ok: false, status: 'unknown' };
    return endAttempt(options.engineRoot, technical);
  }
  log(`restore step finished: ${String(report.status)}`);
  return {
    ran: Boolean(report.ran),
    ok: report.ok === true,
    status: typeof report.status === 'string' ? report.status : undefined,
    part: typeof report.part === 'string' ? report.part : undefined,
  };
}
