/**
 * D11 — cross-device continuity verification against the real stack.
 *
 * The promise: work created on the desktop is visible away from it, through the session-gated
 * Kel gateway, with no device-local divergence and no credential in the browser.
 *
 * This script boots the real stack — a Kel engine on a throwaway data root, the real `bun run webui`
 * (aioncore + web-host + built renderer) pointed at that root via KEL_DATA_DIR — seeds one real job
 * in the engine store, then drives the shipped HTTP surface:
 *   - anonymous /kel/api/state is refused (401) and the engine is never contacted;
 *   - the first-boot admin login yields a session; the same cookie reaches the engine state;
 *   - the desktop-created job is visible remotely (same durable state, no second store);
 *   - the response body never carries the engine bearer token.
 * Writes docs/daily-driver/evidence/d11/remote-kel.json.
 *
 * Usage: node packaging/verify-remote-kel.cjs
 */
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd11');
const PYTHON = process.env.KEL_PYTHON || 'python';
const BUN =
  [
    process.env.KEL_BUN,
    path.join(os.homedir(), 'AppData', 'Roaming', 'npm', 'node_modules', 'bun', 'bin', 'bun.exe'),
    path.join(os.homedir(), '.bun', 'bin', 'bun.exe'),
  ].find((candidate) => candidate && fs.existsSync(candidate)) || 'bun';
const PORT = Number(process.env.KEL_D11_PORT || 25913);
const AIONCORE =
  process.env.KEL_AIONCORE ||
  'C:/Users/Nick/KelVisualFixInstall/resources/bundled-aioncore/win32-x64/aioncore.exe';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const SEED = `
import json, sys
from kel.core import Store
from kel.context import Context
store = Store(sys.argv[1])
Context(store)
contract = {'request': 'D11 continuity job', 'milestones': [
  {'id': 'm1', 'objective': 'Prove cross-device state', 'filename': 'out.md', 'depends_on': [],
   'checks': [{'kind': 'min_chars', 'value': 40}]}]}
job = store.create(contract, conversation='main')
print(json.dumps({'job': job['id'] if isinstance(job, dict) else job}))
`;

function killTree(pid) {
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/F', '/T', '/PID', String(pid)], { stdio: 'ignore' });
  } else {
    try {
      process.kill(pid);
    } catch {
      /* already gone */
    }
  }
}

async function bootEngine(dataDir) {
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

async function bootWebui(webDir, engineDir) {
  const staticDir = path.join(REPO, 'desktop', 'out', 'renderer');
  if (!fs.existsSync(path.join(staticDir, 'index.html'))) {
    throw new Error(`renderer build missing at ${staticDir} — run "bun run package" in desktop first`);
  }
  if (!fs.existsSync(AIONCORE)) throw new Error(`aioncore binary missing at ${AIONCORE}`);
  const child = spawn(
    BUN,
    ['run', 'webui', '--no-build', '--no-open', '--data-dir', webDir, '--port', String(PORT)],
    {
      cwd: path.join(REPO, 'desktop'),
      windowsHide: true,
      env: {
        ...process.env,
        AIONUI_BACKEND_BIN: AIONCORE,
        AIONUI_STATIC_DIR: staticDir,
        KEL_DATA_DIR: engineDir,
      },
    }
  );
  const logs = [];
  let password = null;
  const keep = (chunk) => {
    const text = chunk.toString('utf8');
    logs.push(text);
    const match = /Initial admin password:\s*(\S+)/.exec(text);
    if (match) password = match[1];
  };
  child.stdout.on('data', keep);
  child.stderr.on('data', keep);

  const base = `http://127.0.0.1:${PORT}`;
  let ready = false;
  for (let attempt = 0; attempt < 300 && !ready; attempt += 1) {
    await wait(300);
    try {
      const response = await fetch(base + '/', { redirect: 'manual' });
      ready = response.status < 500;
    } catch {
      /* not listening yet */
    }
  }
  if (!ready) throw new Error('webui did not become ready: ' + logs.join('').slice(-600));
  for (let attempt = 0; attempt < 100 && !password; attempt += 1) await wait(300);
  return { child, base, logs, password };
}

async function main() {
  const engineDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d11-engine-'));
  const webDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d11-web-'));
  const seedRun = spawnSync(PYTHON, ['-c', SEED, engineDir], { cwd: RUNTIME, encoding: 'utf8' });
  if (seedRun.status !== 0) throw new Error('seed failed: ' + (seedRun.stderr || '').slice(0, 400));
  const jobId = JSON.parse(seedRun.stdout.trim().split('\n').pop()).job;

  const engine = await bootEngine(engineDir);
  const verdict = {};
  let webui = null;
  try {
    webui = await bootWebui(webDir, engineDir);
    verdict.webui_ready = true;
    verdict.initial_password_published = Boolean(webui.password);

    const anon = await fetch(webui.base + '/kel/api/state?conversation=main');
    const anonBody = await anon.text();
    verdict.anonymous_is_refused = anon.status === 401;

    const login = await fetch(webui.base + '/login', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: webui.password, remember: false }),
    });
    const loginBody = await login.json().catch(() => ({}));
    const rawCookie = login.headers.get('set-cookie') || '';
    const cookie = rawCookie.split(';')[0];
    verdict.login_succeeds = Boolean(login.ok && cookie.includes('aionui-session'));

    // The engine serves these reads as GET with a query param — the same shape the renderer uses.
    const state = await fetch(webui.base + '/kel/api/state?conversation=main', {
      headers: { cookie },
    });
    const stateText = await state.text();
    let stateBody = {};
    try {
      stateBody = JSON.parse(stateText);
    } catch {
      /* non-JSON response */
    }
    verdict.state_status = state.status;
    verdict.state_body_head = stateText.slice(0, 200);
    verdict.authenticated_state_reachable = state.ok && typeof stateBody === 'object';
    const jobs = Array.isArray(stateBody.jobs) ? stateBody.jobs : [];
    verdict.desktop_job_visible_remotely = jobs.some(
      (job) => String((job.contract && job.contract.request) || '').includes('D11 continuity job')
    );

    const work = await fetch(webui.base + '/kel/api/work?conversation=main', {
      headers: { cookie },
    });
    const workText = await work.text();
    let workBody = {};
    try {
      workBody = JSON.parse(workText);
    } catch {
      /* non-JSON response */
    }
    verdict.work_status = work.status;
    verdict.work_body_head = workText.slice(0, 200);
    verdict.workspace_reachable_remotely = work.ok && Boolean(workBody.project_id || workBody.memory);

    const text = anonBody + JSON.stringify(stateBody);
    verdict.engine_token_never_reaches_the_browser =
      !text.includes(engine.descriptor.token || 'never-empty') && !text.includes('Bearer');

    // A dead engine must degrade honestly, not 200 with stale content.
    killTree(engine.child.pid);
    await wait(1200);
    const dead = await fetch(webui.base + '/kel/api/state?conversation=main', {
      headers: { cookie },
    });
    const deadBody = await dead.json().catch(() => ({}));
    verdict.dead_engine_fails_closed = dead.status === 502 || dead.status === 503;
    verdict.dead_engine_error = deadBody.error || null;
  } finally {
    if (webui) killTree(webui.child.pid);
    killTree(engine.child.pid);
    await wait(800);
  }

  const allGreen = Object.entries(verdict)
    .filter(([key]) => !['dead_engine_error', 'state_status', 'state_body_head', 'work_status', 'work_body_head'].includes(key))
    .every(([, value]) => value === true);
  const evidence = {
    phase: 'D11',
    when: new Date().toISOString(),
    port: PORT,
    engine_data: engineDir,
    web_data: webDir,
    seeded_job: jobId,
    verdict,
    all_green: allGreen,
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'remote-kel.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
  if (!allGreen) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
