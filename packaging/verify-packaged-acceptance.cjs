// Packaged acceptance run (PKG-02..09 + continuation-through-UI + memory survival).
// Usage: NODE_PATH=<playwright node_modules> node verify-packaged-acceptance.cjs <appDir> <dataDir>
const path = require('path');
const fs = require('fs');
const http = require('http');
const { _electron: electron } = require('playwright');
const watchdog = setTimeout(() => { console.log('WATCHDOG'); process.exit(3); }, 420000);
watchdog.unref();

function request(descriptor, route, payload) {
  return new Promise((resolve, reject) => {
    const url = new URL(route, descriptor.url);
    const body = payload === undefined ? undefined : JSON.stringify(payload);
    const req = http.request(url, {
      method: payload === undefined ? 'GET' : 'POST',
      headers: { Authorization: 'Bearer ' + descriptor.token,
                 'Content-Type': 'application/json',
                 ...(body ? { 'Content-Length': Buffer.byteLength(body) } : {}) },
      timeout: 15000,
    }, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch (e) { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('timeout')));
    if (body) req.write(body);
    req.end();
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function readDescriptor(dataDir) {
  const file = path.join(dataDir, 'desktop-session.json');
  for (let i = 0; i < 60; i++) {
    try {
      const raw = fs.readFileSync(file, 'utf8');
      const parsed = JSON.parse(raw);
      const probe = await request(parsed, '/api/state?conversation=main');
      if (probe.status === 200) return parsed;
    } catch (e) { /* not ready yet */ }
    await sleep(500);
  }
  throw new Error('engine descriptor not ready');
}

async function launch(appDir, dataDir) {
  const app = await electron.launch({
    executablePath: path.join(appDir, 'Kel.exe'), cwd: appDir,
    env: { ...process.env, KEL_DATA_DIR: dataDir, KEL_SKIP_TELEMETRY: '1' },
  });
  const page = await app.firstWindow();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(9000);
  return { app, page, errors };
}

(async () => {
  const appDir = path.resolve(process.argv[2]);
  const dataDir = path.resolve(process.argv[3]);
  const results = {};
  let { app, page, errors } = await launch(appDir, dataDir);
  results.pkg01_exe_opens = true;                       // PKG-01
  results.pkg02_shell_window = await page.title();      // PKG-02
  const desc = await readDescriptor(dataDir);
  const state0 = await request(desc, '/api/state?conversation=main');
  results.pkg03_engine_version = state0.body.engine_version;   // PKG-03
  results.continuation_field = 'continuation' in state0.body;
  const work0 = await request(desc, '/api/work?conversation=main');
  results.pkg05_records_before_restart = work0.body.memory.records.length;
  results.recipes_listed = work0.body.recipes.entries.length;
  // PKG-06: continuation through the packaged UI.
  await page.locator('text=Work & context').first().click({ timeout: 8000 });
  await page.waitForTimeout(1600);
  await page.locator('text=Continue work').first().click({ timeout: 8000 });
  await page.waitForTimeout(1400);
  results.continue_buttons = await page.locator('button:has-text("Continue")').count();
  const button = page.locator('button:has-text("Continue")').first();
  if (results.continue_buttons > 0) {
    await button.click({ timeout: 8000 });
    let resumed = false;
    for (let i = 0; i < 40; i++) {
      await page.waitForTimeout(500);
      const s = await request(desc, '/api/state?conversation=main');
      if (s.body.jobs.every((j) => j.state !== 'PAUSED')) { resumed = true; break; }
    }
    results.pkg06_continuation_resumed = resumed;
    const s = await request(desc, '/api/state?conversation=main');
    results.pkg06_continuation_message = s.body.messages.some(
      (m) => m.role === 'assistant' && /Continuing/.test(m.text));
  }
  results.pkg07_page_errors_run1 = errors.slice(0, 5);
  // PKG-08: graceful shutdown run 1.
  await app.close();
  await sleep(2500);
  // PKG-09 + PKG-05: relaunch, memory survives.
  ({ app, page, errors } = await launch(appDir, dataDir));
  results.pkg09_relaunch = true;
  const desc2 = await readDescriptor(dataDir);
  const work1 = await request(desc2, '/api/work?conversation=main');
  results.pkg05_records_after_restart = work1.body.memory.records.length;
  results.pkg05_memory_survived =
    work1.body.memory.records.length === results.pkg05_records_before_restart
    && results.pkg05_records_before_restart > 0;
  results.pkg07_page_errors_run2 = errors.slice(0, 5);
  await app.close();
  console.log(JSON.stringify({ schema: 1, results }, null, 2));
  process.exit(0);
})().catch((e) => { console.log('ACCEPTANCE-FAIL ' + String(e)); process.exit(1); });
