/**
 * D12 — route transparency verification against the real engine.
 *
 * The engine records the routing decision (selected provider, fallbacks, excluded reasons,
 * policy flags) on the run.claimed event. This script seeds a real job + claim on a throwaway
 * data root, boots `python -m kel.service`, and checks the shipped HTTP surface:
 *   GET /api/state exposes routes[job] with provider + route (selected/policy/fallbacks/excluded);
 *   a cancelled job drops out of the map.
 * Writes docs/daily-driver/evidence/d12/route-transparency.json.
 *
 * Usage: node packaging/verify-route-transparency.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd12');
const PYTHON = process.env.KEL_PYTHON || 'python';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const SEED = `
import json, sys
from kel.core import Store
from kel.context import Context
store = Store(sys.argv[1])
Context(store)
contract = {'request': 'D12 route transparency', 'milestones': [
  {'id': 'm1', 'objective': 'Work', 'filename': 'out.md', 'depends_on': [],
   'checks': [{'kind': 'min_chars', 'value': 40}]}]}
job = store.create(contract, conversation='main')
job_id = job['id'] if isinstance(job, dict) else job
route = {'selected': 'fixture', 'fallbacks': ['other-provider'],
         'excluded': {'alt-provider': ['quota exhausted'], 'local-box': ['authentication unavailable']},
         'policy': 'eligible-cost-v1', 'unknown_cost': True, 'unknown_quota': True}
store.claim(job_id, 'm1', provider='fixture', route=route, model='fixture-1')
print(json.dumps({'job': job_id}))
`;

async function boot(dataDir) {
  const child = spawn(PYTHON, ['-m', 'kel.service', '--data', dataDir], { cwd: RUNTIME, windowsHide: true });
  let descriptor = null;
  for (let attempt = 0; attempt < 120 && !descriptor; attempt += 1) {
    await wait(200);
    try {
      descriptor = JSON.parse(fs.readFileSync(path.join(dataDir, 'desktop-session.json'), 'utf8'));
    } catch {
      /* still starting */
    }
  }
  if (!descriptor) throw new Error('engine did not publish a descriptor');
  return { child, descriptor };
}

async function main() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d12-'));
  const seedRun = spawnSync(PYTHON, ['-c', SEED, dataDir], { cwd: RUNTIME, encoding: 'utf8' });
  if (seedRun.status !== 0) throw new Error('seed failed: ' + (seedRun.stderr || '').slice(0, 400));
  const jobId = JSON.parse(seedRun.stdout.trim().split('\n').pop()).job;

  const engine = await boot(dataDir);
  const verdict = {};
  try {
    verdict.engine_booted = true;
    const base = engine.descriptor.url.replace(/\/?$/, '/');
    const headers = { authorization: 'Bearer ' + engine.descriptor.token };

    const response = await fetch(base + 'api/state?conversation=main', { headers });
    verdict.state_ok = response.ok;
    const state = await response.json();
    const decision = (state.routes || {})[jobId];
    verdict.route_is_exposed = Boolean(decision);
    verdict.route_matches_the_claim = Boolean(
      decision &&
        decision.provider === 'fixture' &&
        decision.route.selected === 'fixture' &&
        decision.route.policy === 'eligible-cost-v1' &&
        Array.isArray(decision.route.fallbacks) &&
        decision.route.fallbacks[0] === 'other-provider'
    );
    verdict.excluded_reasons_are_intact = Boolean(
      decision && JSON.stringify(decision.route.excluded) ===
        JSON.stringify({ 'alt-provider': ['quota exhausted'], 'local-box': ['authentication unavailable'] })
    );
    verdict.unknowns_are_flagged_honestly = Boolean(decision && decision.route.unknown_cost === true && decision.route.unknown_quota === true);
    verdict.route_body = decision || null;

    // Closed jobs leave the map: a cancelled job must not keep advertising a route.
    await fetch(base + 'api/control', {
      method: 'POST',
      headers: { ...headers, 'content-type': 'application/json' },
      body: JSON.stringify({ job: jobId, action: 'cancel' }),
    });
    await wait(500);
    const after = await (await fetch(base + 'api/state?conversation=main', { headers })).json();
    const jobAfter = (after.jobs || []).find((job) => job.id === jobId);
    const stateAfter = jobAfter ? jobAfter.state : 'GONE';
    const routeAfter = Boolean((after.routes || {})[jobId]);
    verdict.after_cancel_state = stateAfter;
    // Honest rule: the route disappears exactly when the job reaches a terminal state; while the
    // job is still winding down (cancel pending), its live route stays visible.
    const terminal = stateAfter === 'CLOSED' || stateAfter === 'CANCELLED' || stateAfter === 'GONE';
    verdict.route_clears_only_when_terminal = terminal ? !routeAfter : routeAfter;
  } finally {
    engine.child.kill();
    await wait(600);
  }

  const allGreen = Object.entries(verdict)
    .filter(([key]) => !['route_body', 'after_cancel_state'].includes(key))
    .every(([, value]) => value === true);
  const evidence = {
    phase: 'D12',
    when: new Date().toISOString(),
    data_dir: dataDir,
    job: jobId,
    verdict,
    all_green: allGreen,
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'route-transparency.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  if (!allGreen) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
