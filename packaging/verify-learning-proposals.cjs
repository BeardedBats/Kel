/**
 * D9 — controlled learning promotion verification against the real engine.
 *
 * Seeds (in Python, in the same store) one durable record plus two pending proposals, boots
 * `python -m kel.service` on that data dir, then drives the shipped HTTP surface the desktop uses:
 *   - /api/work exposes the open queue — nothing has been applied by itself;
 *   - a person defers one (it stays queued), accepts it (applied through the trust model, the old
 *     value preserved as superseded history), and rejects the other (gone from the queue);
 *   - after every decision the queue and the records are read back from the engine, not assumed.
 * Writes docs/daily-driver/evidence/d9/learning-proposals.json.
 *
 * Usage: node packaging/verify-learning-proposals.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd9');
const PYTHON = process.env.KEL_PYTHON || 'python';
const DESCRIPTOR = 'desktop-session.json';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const SEED = `
import json, sys
from kel.core import Store
from kel.context import Context
from kel.memory import Memory
store = Store(sys.argv[1])
Context(store)  # ensures project 'default' + conversation 'main'
m = Memory(store)
rec = m.record('default', 'fact', 'deploy target', {'host': 'staging-1'},
               'Deploys go to staging-1.', source_type='user_instruction')
a = m.propose_change('default', kind='user_change', type='fact', topic='deploy target',
                     value={'host': 'staging-2'}, summary='Deploys move to staging-2',
                     why='You used staging-2 in the last two runs.', current_id=rec)
b = m.propose_change('default', kind='repo_state', type='fact', topic='last run',
                     value={'result': 'clean'}, summary='The last run finished cleanly',
                     why='The engine observed a clean finish.')
print(json.dumps({'record': rec, 'a': a, 'b': b}))
`;

async function boot(dataDir) {
  fs.rmSync(path.join(dataDir, DESCRIPTOR), { force: true });
  const child = spawn(PYTHON, ['-m', 'kel.service', '--data', dataDir], { cwd: RUNTIME, windowsHide: true });
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
      if (candidate && candidate.pid === child.pid) descriptor = candidate;
    } catch {
      /* still starting */
    }
    if (exited) break;
  }
  if (!descriptor) throw new Error('engine did not publish a descriptor: ' + logs.join('').slice(0, 400));
  return { child, descriptor, logs, waitForExit: async (budgetMs) => {
    const deadline = Date.now() + budgetMs;
    while (!exited && Date.now() < deadline) await wait(200);
    return exited;
  } };
}

async function stop(handle) {
  const { child } = handle;
  child.kill();
  if (!(await handle.waitForExit(5000)) && process.platform === 'win32') {
    spawnSync('taskkill', ['/F', '/PID', String(child.pid)], { stdio: 'ignore' });
    if (!(await handle.waitForExit(5000))) throw new Error(`engine pid ${child.pid} refused to stop`);
  }
  await wait(600);
}

const headersOf = (descriptor) => ({
  'content-type': 'application/json',
  authorization: 'Bearer ' + descriptor.token,
});
const baseOf = (descriptor) => descriptor.url.replace(/\/?$/, '/');
const workOf = async (descriptor) => {
  const response = await fetch(baseOf(descriptor) + 'api/work?conversation=main', {
    headers: headersOf(descriptor),
  });
  if (!response.ok) throw new Error(`work -> ${response.status}`);
  return response.json();
};
const memoryAction = async (descriptor, payload) => {
  const response = await fetch(baseOf(descriptor) + 'api/memory', {
    method: 'POST',
    headers: headersOf(descriptor),
    body: JSON.stringify({ ...payload, conversation: 'main' }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`${payload.action} -> ${response.status}: ${JSON.stringify(body)}`);
  return body;
};
const valueOf = (record) => {
  const raw = record && record.value;
  if (raw && typeof raw === 'object') return raw;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
  return null;
};
const activeHost = (work, host) =>
  work.memory.records.filter(
    (record) => record.status === 'active' && (valueOf(record) || {}).host === host
  );

async function main() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d9-'));
  const seedRun = spawnSync(PYTHON, ['-c', SEED, dataDir], { cwd: RUNTIME, encoding: 'utf8' });
  if (seedRun.status !== 0) throw new Error('seed failed: ' + (seedRun.stderr || '').slice(0, 400));
  const seed = JSON.parse(seedRun.stdout.trim().split('\n').pop());
  const proposalA = seed.a.id;
  const proposalB = seed.b.id;

  const handle = await boot(dataDir);
  const verdict = {};
  try {
    const initial = await workOf(handle.descriptor);
    verdict.engine_booted = true;
    verdict.project_is_default = initial.project_id === 'default';
    verdict.queue_has_two_pending =
      initial.memory.proposals.length === 2 &&
      initial.memory.proposals.every((proposal) => proposal.state === 'pending');
    verdict.nothing_applied_before_a_decision =
      activeHost(initial, 'staging-1').length === 1 && activeHost(initial, 'staging-2').length === 0;

    await memoryAction(handle.descriptor, { action: 'defer_proposal', id: proposalA });
    const afterDefer = await workOf(handle.descriptor);
    const deferred = afterDefer.memory.proposals.find((proposal) => proposal.id === proposalA);
    verdict.defer_keeps_it_queued =
      Boolean(deferred) && deferred.state === 'deferred' && afterDefer.memory.proposals.length === 2;

    await memoryAction(handle.descriptor, { action: 'accept_proposal', id: proposalA });
    const afterAccept = await workOf(handle.descriptor);
    const openIds = afterAccept.memory.proposals.map((proposal) => proposal.id);
    verdict.accept_applies_the_change =
      activeHost(afterAccept, 'staging-2').length === 1 && activeHost(afterAccept, 'staging-1').length === 0;
    verdict.accept_preserves_history = afterAccept.memory.records.some(
      (record) => (valueOf(record) || {}).host === 'staging-1' && record.status !== 'active'
    );
    verdict.accept_leaves_only_the_other = openIds.length === 1 && openIds[0] === proposalB;

    await memoryAction(handle.descriptor, { action: 'reject_proposal', id: proposalB, reason: 'not right' });
    const afterReject = await workOf(handle.descriptor);
    const rejected = afterReject.memory.records;
    verdict.reject_empties_the_queue = afterReject.memory.proposals.length === 0;
    verdict.rejected_change_never_applied = !rejected.some(
      (record) => (valueOf(record) || {}).result === 'clean'
    );
    verdict.records_after = afterReject.memory.records.map((record) => ({
      topic: record.topic,
      status: record.status,
      trust: record.trust,
      value: record.value,
    }));
  } finally {
    await stop(handle);
    verdict.engine_stopped = true;
  }

  const allGreen = Object.entries(verdict)
    .filter(([key]) => !['records_after'].includes(key))
    .every(([, value]) => value === true);
  const evidence = {
    phase: 'D9',
    when: new Date().toISOString(),
    data_dir: dataDir,
    proposals: { a: proposalA, b: proposalB },
    verdict,
    all_green: allGreen,
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'learning-proposals.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  if (!allGreen) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
