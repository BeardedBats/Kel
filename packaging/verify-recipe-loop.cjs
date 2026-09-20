/**
 * D10 — recipe loop verification against the real engine.
 *
 * The engine ships the whole loop but nothing called it: a draft built from a settled job
 * (`propose_from_job`), a save that refuses without explicit confirmation, and a run that compiles
 * into the existing execution. This script boots `python -m kel.service` on a throwaway data dir,
 * creates one real job in the same store, then drives that loop over the shipped HTTP surface:
 *   - draft from the job (preview only, nothing saved);
 *   - save without confirmation is refused (fail-closed);
 *   - save with confirmation persists; saving the same version again is idempotent;
 *   - run submits a real job; running again submits a second one (run → again).
 * Writes docs/daily-driver/evidence/d10/recipe-loop.json.
 *
 * Usage: node packaging/verify-recipe-loop.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd10');
const PYTHON = process.env.KEL_PYTHON || 'python';
const DESCRIPTOR = 'desktop-session.json';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const SEED = `
import json, sys
from kel.core import Store
from kel.context import Context
store = Store(sys.argv[1])
Context(store)  # ensures project 'default' + conversation 'main'
contract = {'request': 'Do the work', 'milestones': [
  {'id': 'm1', 'objective': 'Draft the thing', 'filename': 'out.md', 'depends_on': [],
   'checks': [{'kind': 'min_chars', 'value': 40}]},
  {'id': 'm2', 'objective': 'Second step', 'filename': 'two.md', 'depends_on': ['m1'],
   'checks': [{'kind': 'min_chars', 'value': 40}]}]}
job = store.create(contract, conversation='main')
print(json.dumps({'job': job['id'] if isinstance(job, dict) else job}))
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

async function recipes(descriptor, payload) {
  const response = await fetch(baseOf(descriptor) + 'api/recipes', {
    method: 'POST',
    headers: headersOf(descriptor),
    body: JSON.stringify({ ...payload, conversation: 'main' }),
  });
  const body = await response.json().catch(() => ({}));
  return { ok: response.ok, status: response.status, body };
}

async function stateOf(descriptor) {
  const response = await fetch(baseOf(descriptor) + 'api/state?conversation=main', {
    headers: headersOf(descriptor),
  });
  if (!response.ok) throw new Error(`state -> ${response.status}`);
  return response.json();
}

async function main() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d10-'));
  const seedRun = spawnSync(PYTHON, ['-c', SEED, dataDir], { cwd: RUNTIME, encoding: 'utf8' });
  if (seedRun.status !== 0) throw new Error('seed failed: ' + (seedRun.stderr || '').slice(0, 400));
  const jobId = JSON.parse(seedRun.stdout.trim().split('\n').pop()).job;

  const handle = await boot(dataDir);
  const verdict = {};
  try {
    verdict.engine_booted = true;

    const draft = await recipes(handle.descriptor, { action: 'propose_from_job', job_id: jobId });
    const recipe = draft.body && draft.body.recipe;
    verdict.draft_from_job = Boolean(
      draft.ok && recipe && recipe.source === 'from_job:' + jobId && draft.body.preview.milestones === 2
    );
    const listAfterDraft = await recipes(handle.descriptor, { action: 'list' });
    verdict.draft_is_not_stored = Boolean(
      listAfterDraft.ok &&
        !(listAfterDraft.body.entries || []).some((entry) => entry.recipe_id === recipe.recipe_id)
    );

    const refused = await recipes(handle.descriptor, { action: 'save', recipe });
    verdict.save_without_confirmation_is_refused =
      !refused.ok && String(refused.body.error || '').toLowerCase().includes('explicit user confirmation');

    const saved = await recipes(handle.descriptor, { action: 'save', recipe, confirm: true });
    verdict.save_with_confirmation_persists = Boolean(saved.ok && saved.body.saved === true);

    const listAfterSave = await recipes(handle.descriptor, { action: 'list' });
    verdict.saved_recipe_is_listed = Boolean(
      listAfterSave.ok &&
        (listAfterSave.body.entries || []).some((entry) => entry.recipe_id === recipe.recipe_id)
    );

    const again = await recipes(handle.descriptor, { action: 'save', recipe, confirm: true });
    verdict.saving_the_same_version_is_idempotent = Boolean(
      again.ok && again.body.saved === false && again.body.reason === 'already saved'
    );

    const runOne = await recipes(handle.descriptor, { action: 'run', recipe_id: recipe.recipe_id, inputs: {} });
    const runTwo = await recipes(handle.descriptor, { action: 'run', recipe_id: recipe.recipe_id, inputs: {} });
    verdict.run_submits_a_job = Boolean(runOne.ok && runOne.body.submission);
    verdict.run_again_submits_another = Boolean(
      runTwo.ok && runTwo.body.submission && runTwo.body.submission !== runOne.body.submission
    );

    const state = await stateOf(handle.descriptor);
    const runJobs = (state.jobs || []).filter((job) =>
      String((job.contract && job.contract.request) || '').startsWith('Run recipe')
    );
    // The submission queue is durable and drains one job at a time: both runs are accepted (distinct
    // submission ids above); the first materializes as a real job, the second waits its turn.
    verdict.first_run_is_a_real_job = runJobs.length >= 1;
    verdict.run_jobs_states = runJobs.map((job) => ({ state: job.state, request: job.contract.request }));
  } finally {
    await stop(handle);
    verdict.engine_stopped = true;
  }

  const allGreen = Object.entries(verdict)
    .filter(([key]) => !['run_jobs_states'].includes(key))
    .every(([, value]) => value === true);
  const evidence = {
    phase: 'D10',
    when: new Date().toISOString(),
    data_dir: dataDir,
    job: jobId,
    verdict,
    all_green: allGreen,
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'recipe-loop.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  if (!allGreen) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
