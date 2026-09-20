/**
 * D6 — restart/resume verification against the real engine.
 *
 * Boots `python -m kel.service` on a throwaway data dir, records the durable state surface,
 * stops the engine HARD (and verifies it is gone — the engine has a single-instance guard),
 * plants the engine's own restore-outcome record (the same file the backup module writes after a
 * restore attempt), boots AGAIN on the same data dir and asserts:
 *   - the same durable state comes back (a restart does not reset truth),
 *   - the recorded restore outcome survives and is surfaced on /api/state.restore,
 *   - continuation is derived from durable state (empty on a fresh, work-free store).
 * Writes docs/daily-driver/evidence/d6/continuation-restart.json.
 *
 * Usage: node packaging/verify-continuation-restart.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd6');
const PYTHON = process.env.KEL_PYTHON || 'python';
const DESCRIPTOR = 'desktop-session.json';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function boot(dataDir) {
  // A stale descriptor from a prior run must never be mistaken for a live engine.
  fs.rmSync(path.join(dataDir, DESCRIPTOR), { force: true });
  const child = spawn(PYTHON, ['-m', 'kel.service', '--data', dataDir], { cwd: RUNTIME, windowsHide: true });
  // exitCode stays null when a process is signal-killed (Windows taskkill /F), so liveness must be
  // tracked with the exit event, not with exitCode.
  let exited = false;
  child.once('exit', () => {
    exited = true;
  });
  const logs = [];
  child.stdout.on('data', (data) => logs.push(data.toString('utf8')));
  child.stderr.on('data', (data) => logs.push(data.toString('utf8')));
  let descriptor = null;
  for (let attempt = 0; attempt < 120 && !descriptor; attempt += 1) {
    await wait(200);
    try {
      const candidate = JSON.parse(fs.readFileSync(path.join(dataDir, DESCRIPTOR), 'utf8'));
      // Only trust a descriptor this very process wrote.
      if (candidate && candidate.pid === child.pid) descriptor = candidate;
    } catch {
      /* still starting */
    }
    if (exited) break;
  }
  if (!descriptor) {
    throw new Error('engine did not publish a descriptor: ' + logs.join('').slice(0, 400));
  }
  return { child, descriptor, logs, isAlive: () => !exited, waitForExit: async (budgetMs) => {
    const deadline = Date.now() + budgetMs;
    while (!exited && Date.now() < deadline) await wait(200);
    return exited;
  } };
}

async function stateOf(descriptor) {
  const response = await fetch(descriptor.url.replace(/\/?$/, '/') + 'api/state', {
    headers: { authorization: 'Bearer ' + descriptor.token },
  });
  if (!response.ok) throw new Error(`state -> ${response.status}`);
  return response.json();
}

async function stop(handle) {
  const { child } = handle;
  child.kill();
  if (!(await handle.waitForExit(5000)) && process.platform === 'win32') {
    spawnSync('taskkill', ['/F', '/PID', String(child.pid)], { stdio: 'ignore' });
    if (!(await handle.waitForExit(5000))) throw new Error(`engine pid ${child.pid} refused to stop`);
  }
  // Give the single-instance guard a beat to observe the process is gone.
  await wait(600);
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d6-'));
  const results = { dataDir, checks: {}, startedAt: new Date().toISOString() };

  // Boot 1: fresh store — durable truth is empty and untouched.
  const first = await boot(dataDir);
  results.checks.firstBootPid = first.descriptor.pid;
  const before = await stateOf(first.descriptor);
  results.checks.firstBoot = {
    connected: before.connected,
    engine_version: before.engine_version,
    restore: before.restore,
    continuation: before.continuation,
    jobs: (before.jobs ?? []).length,
    conversations: (before.conversations ?? []).length,
  };
  await stop(first);

  // Plant the engine's own restore-outcome record (exactly the file the backup module writes).
  const record = {
    ok: false,
    detail: 'fixture: a restore attempt was interrupted before it finished',
    at: Math.floor(Date.now() / 1000),
  };
  fs.writeFileSync(path.join(dataDir, 'restore-outcome.json'), JSON.stringify(record));

  // Boot 2: the same data dir — truth survives, and the recorded outcome is surfaced.
  const second = await boot(dataDir);
  results.checks.secondBootPid = second.descriptor.pid;
  const after = await stateOf(second.descriptor);
  results.checks.secondBoot = {
    connected: after.connected,
    engine_version: after.engine_version,
    restore: after.restore,
    continuation: after.continuation,
    jobs: (after.jobs ?? []).length,
    conversations: (after.conversations ?? []).length,
  };
  await stop(second);

  results.checks.verdict = {
    fresh_process: first.descriptor.pid !== second.descriptor.pid,
    engine_version_stable: before.engine_version === after.engine_version,
    connection_restored: after.connected === true,
    restore_absent_before: before.restore === null,
    restore_record_survives:
      after.restore !== null &&
      after.restore.ok === false &&
      String(after.restore.detail).includes('interrupted'),
    continuation_derived_cleanly: Array.isArray(after.continuation) && after.continuation.length === 0,
    durable_counts_stable:
      (before.jobs ?? []).length === (after.jobs ?? []).length &&
      (before.conversations ?? []).length === (after.conversations ?? []).length,
  };

  results.finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(OUT, 'continuation-restart.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));

  const failed = Object.entries(results.checks.verdict).filter(([, ok]) => !ok);
  if (failed.length) {
    console.error('D6 RESTART CHECKS FAILED:', failed.map(([key]) => key).join(', '));
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('D6 RESTART VERIFICATION FAILED:', error && error.stack ? error.stack : error);
  process.exit(1);
});
