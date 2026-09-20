/**
 * D16 — live capability revision verification against the real engine.
 *
 * Proves both halves of the promise over the shipped HTTP surface:
 *   - narrowing is immediate: revoking a lease denies the very next check, mid-flight;
 *   - nothing widens silently: a pending boundary request changes nothing, a user grant widens
 *     deliberately for one use only, and the one-time grant does not stick.
 * Writes docs/daily-driver/evidence/d16/live-revision.json.
 *
 * Usage: node packaging/verify-live-revision.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd16');
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
inside = os.path.join(data, 'workspace')
outside = os.path.join(data, 'elsewhere')
os.makedirs(inside, exist_ok=True)
os.makedirs(outside, exist_ok=True)
contract = {'request': 'D16 live revision', 'milestones': [
  {'id': 'm1', 'objective': 'Work', 'filename': 'out.md', 'depends_on': [],
   'checks': [{'kind': 'min_chars', 'value': 40}]}]}
job = store.create(contract, conversation='main')
job_id = job['id'] if isinstance(job, dict) else job
lease = Autonomy(store).issue(job_id, review_ref='brief:approved', roots=[inside],
                              repositories=[inside], tools=['read', 'write'])
request = Autonomy(store).request_expansion(lease['lease_id'], 'root', outside,
                                            what='write in the neighbouring folder',
                                            why='the task needs one file there',
                                            benefit='finish the job without a detour',
                                            fallback='stop and ask you',
                                            risk='writes outside the approved folder')
print(json.dumps({'job': job_id, 'lease': lease['lease_id'],
                  'request': request.get('request_id'),
                  'inside': inside, 'outside': outside}))
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
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d16-'));
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
    const check = (target) => call({ action: 'check', lease_id: seeded.lease, kind: 'write', target });
    const insideFile = path.join(seeded.inside, 'out.md');
    const outsideFile = path.join(seeded.outside, 'other.md');

    const inScope = await check(insideFile);
    verdict.in_scope_write_is_allowed = Boolean(inScope.ok && inScope.body.allowed === true);

    const outScope = await check(outsideFile);
    verdict.out_of_scope_write_is_denied = Boolean(outScope.ok && outScope.body.allowed === false);

    const requests = await call({ action: 'requests' });
    const pending = (requests.body.requests || []).find((entry) => entry.request_id === seeded.request);
    verdict.request_is_pending = Boolean(pending && pending.status === 'PENDING');

    const afterRequest = await check(outsideFile);
    verdict.pending_request_does_not_widen = Boolean(afterRequest.ok && afterRequest.body.allowed === false);

    const granted = await call({ action: 'resolve', request_id: seeded.request, allow: true });
    verdict.user_grant_is_accepted = Boolean(granted.ok && granted.body.status === 'GRANTED');

    const afterGrant = await check(outsideFile);
    verdict.user_grant_widens_deliberately = Boolean(afterGrant.ok && afterGrant.body.allowed === true);

    const afterOnce = await check(outsideFile);
    verdict.one_time_grant_does_not_stick = Boolean(afterOnce.ok && afterOnce.body.allowed === false);

    const revoked = await call({ action: 'revoke', lease_id: seeded.lease, reason: 'live revision check' });
    verdict.revoke_is_accepted = Boolean(revoked.ok && revoked.body.state === 'REVOKED');

    const afterRevoke = await check(insideFile);
    verdict.revocation_narrows_immediately = Boolean(
      afterRevoke.ok && afterRevoke.body.allowed === false && afterRevoke.body.rule === 'lease-revoked'
    );
  } finally {
    engine.child.kill();
    await wait(600);
  }

  const allGreen = Object.entries(verdict).every(([, value]) => value === true);
  const evidence = {
    phase: 'D16',
    when: new Date().toISOString(),
    data_dir: dataDir,
    seeded: { job: seeded.job, lease: seeded.lease },
    verdict,
    all_green: allGreen,
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'live-revision.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  if (!allGreen) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
