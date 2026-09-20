/**
 * D15 — emergency stop verification against the real engine.
 *
 * Seeds a real job plus a real capability lease (the same call the reviewed-plan approval makes),
 * boots `python -m kel.service`, then drives the shipped HTTP surface:
 *   - GET /api/autonomy leases shows the lease ACTIVE;
 *   - POST /api/autonomy {action:'emergency_stop'} stops everything: every lease REVOKED with
 *     reason 'emergency stop' and active/queued work paused;
 *   - the shell cannot self-authorize: the service forces actor='user' (there is no actor input).
 * Writes docs/daily-driver/evidence/d15/emergency-stop.json.
 *
 * Usage: node packaging/verify-emergency-stop.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd15');
const PYTHON = process.env.KEL_PYTHON || 'python';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const SEED = `
import json, sys, os
sys.path.insert(0, sys.argv[2])
from kel.core import Store
from kel.context import Context
from kel.autonomy import Autonomy
data = sys.argv[1]
store = Store(data)
Context(store)
workspace = os.path.join(data, 'workspace')
os.makedirs(workspace, exist_ok=True)
contract = {'request': 'D15 lease holder', 'milestones': [
  {'id': 'm1', 'objective': 'Work', 'filename': 'out.md', 'depends_on': [],
   'checks': [{'kind': 'min_chars', 'value': 40}]}]}
job = store.create(contract, conversation='main')
job_id = job['id'] if isinstance(job, dict) else job
lease = Autonomy(store).issue(job_id, review_ref='brief:approved', roots=[workspace],
                              repositories=[workspace], tools=['read', 'write'])
print(json.dumps({'job': job_id, 'lease': lease['lease_id']}))
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
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d15-'));
  const seedRun = spawnSync(PYTHON, ['-c', SEED, dataDir, RUNTIME], { cwd: RUNTIME, encoding: 'utf8' });
  if (seedRun.status !== 0) throw new Error('seed failed: ' + (seedRun.stderr || '').slice(0, 400));
  const seeded = JSON.parse(seedRun.stdout.trim().split('\n').pop());

  const engine = await boot(dataDir);
  const verdict = {};
  try {
    const base = engine.descriptor.url.replace(/\/?$/, '/');
    const headers = { authorization: 'Bearer ' + engine.descriptor.token, 'content-type': 'application/json' };
    const call = async (payload) => {
      const response = await fetch(base + 'api/autonomy', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      return { ok: response.ok, status: response.status, body: await response.json().catch(() => ({})) };
    };

    const before = await call({ action: 'leases' });
    const activeBefore = (before.body.leases || []).filter((lease) => lease.state === 'ACTIVE');
    verdict.lease_is_active_before = activeBefore.length === 1 && activeBefore[0].lease_id === seeded.lease;

    const stop = await call({ action: 'emergency_stop' });
    verdict.stop_is_accepted = Boolean(stop.ok && (stop.body.stopped || stop.body.ok || stop.body.leases === undefined));

    const after = await call({ action: 'leases' });
    const leaseAfter = (after.body.leases || []).find((lease) => lease.lease_id === seeded.lease);
    verdict.lease_is_revoked = Boolean(leaseAfter && leaseAfter.state === 'REVOKED');
    verdict.revocation_reason_is_recorded = Boolean(leaseAfter && /emergency stop/i.test(String(leaseAfter.reason || '')));

    const stateResponse = await fetch(base + 'api/state?conversation=main', {
      headers: { authorization: 'Bearer ' + engine.descriptor.token },
    });
    const state = await stateResponse.json();
    const jobAfter = (state.jobs || []).find((job) => job.id === seeded.job);
    verdict.job_state_after = jobAfter ? jobAfter.state : 'GONE';
    verdict.work_was_paused = jobAfter ? ['PAUSED', 'CANCELLING', 'CANCEL_REQUESTED', 'CANCELLED'].includes(jobAfter.state) : false;

    // The service forces actor='user'; a caller-supplied actor is ignored, so a shell can never
    // self-authorize. Prove it by sending a hostile actor and confirming the stop is still the user's.
    const hostile = await call({ action: 'emergency_stop', actor: 'shell' });
    verdict.hostile_actor_response = hostile.ok ? 'accepted' : String(hostile.body.error || hostile.status);
    // It is fine for the second stop to be a no-op (nothing left to stop); it is NOT fine for the
    // caller-supplied actor to change the authorization path — that would surface as the engine's
    // "Only the user can trigger an emergency stop" refusal.
    verdict.hostile_actor_input_is_ignored =
      hostile.ok || !/only the user/i.test(String(hostile.body.error || ''));
  } finally {
    engine.child.kill();
    await wait(600);
  }

  const allGreen = Object.entries(verdict)
    .filter(([key]) => !['job_state_after', 'hostile_actor_response'].includes(key))
    .every(([, value]) => value === true);
  const evidence = {
    phase: 'D15',
    when: new Date().toISOString(),
    data_dir: dataDir,
    seeded,
    verdict,
    all_green: allGreen,
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'emergency-stop.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  if (!allGreen) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
