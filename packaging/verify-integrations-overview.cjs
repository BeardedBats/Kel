/**
 * D17 — integrations overview verification against the real engine.
 *
 * The overview reads `/api/capabilities`; this script proves the shipped HTTP surface returns the
 * inventory with honest states, both globally and per conversation, with stable ids.
 * Writes docs/daily-driver/evidence/d17/integrations-overview.json.
 *
 * Usage: node packaging/verify-integrations-overview.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd17');
const PYTHON = process.env.KEL_PYTHON || 'python';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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

const SEED = `
import sys
sys.path.insert(0, sys.argv[2])
from kel.core import Store
from kel.context import Context
Context(Store(sys.argv[1]))
print('ok')
`;

async function main() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d17-'));
  const seedRun = spawnSync(PYTHON, ['-c', SEED, dataDir, RUNTIME], { cwd: RUNTIME, encoding: 'utf8' });
  if (seedRun.status !== 0) throw new Error('seed failed: ' + (seedRun.stderr || '').slice(0, 400));

  const engine = await boot(dataDir);
  const verdict = {};
  try {
    const base = engine.descriptor.url.replace(/\/?$/, '/');
    const headers = { authorization: 'Bearer ' + engine.descriptor.token, 'content-type': 'application/json' };
    const capabilities = async (conversation) => {
      const response = await fetch(base + 'api/capabilities', {
        method: 'POST',
        headers,
        body: JSON.stringify({ action: 'get', conversation }),
      });
      return { ok: response.ok, status: response.status, body: await response.json().catch(() => []) };
    };

    const global = await capabilities(undefined);
    verdict.inventory_returns_rows = Boolean(global.ok && Array.isArray(global.body) && global.body.length >= 1);
    const rows = Array.isArray(global.body) ? global.body : [];
    verdict.every_row_has_honest_state = rows.every(
      (row) =>
        typeof row.id === 'string' &&
        typeof row.label === 'string' &&
        ['available', 'needs_setup', 'unavailable'].includes(row.availability) &&
        typeof row.availability_reason === 'string' &&
        ['on', 'off'].includes(row.effective) &&
        typeof row.usable === 'boolean'
    );

    const scoped = await capabilities('main');
    const globalIds = rows.map((row) => row.id).sort();
    const scopedIds = (Array.isArray(scoped.body) ? scoped.body : []).map((row) => row.id).sort();
    verdict.ids_are_stable_per_conversation = JSON.stringify(globalIds) === JSON.stringify(scopedIds);

    verdict.rows = rows.map((row) => ({
      id: row.id,
      availability: row.availability,
      effective: row.effective,
      reason: row.availability_reason,
    }));
  } finally {
    engine.child.kill();
    await wait(600);
  }

  const allGreen = Object.entries(verdict)
    .filter(([key]) => key !== 'rows')
    .every(([, value]) => value === true);
  const evidence = {
    phase: 'D17',
    when: new Date().toISOString(),
    data_dir: dataDir,
    verdict,
    all_green: allGreen,
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'integrations-overview.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  if (!allGreen) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
