// RA final-audit stunts on the INSTALLED product (first-party, read/scoped-write only).
//
//   node ra-stunt.cjs isolation        <appDir> <rootDir> <outDir>
//   node ra-stunt.cjs continuity-check <appDir> <rootDir> <outDir>
//
// isolation: live cross-scope battery (approvals via the service routes, capability state,
// conversation state) + the Pet-settings dead-control observation, on a booted installed app.
// continuity-check: existing conversations + a seeded marker message survive a reinstall-over.
const fs = require('fs');
const path = require('path');

function resolvePlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return process.env.PLAYWRIGHT_MODULE;
  try { return require.resolve('playwright'); } catch (e) {}
  console.error('playwright not found; set PLAYWRIGHT_MODULE');
  process.exit(2);
}
const { _electron: electron } = require(resolvePlaywright());

const mode = process.argv[2];
const appDir = path.resolve(process.argv[3]);
const rootDir = path.resolve(process.argv[4]);
const outDir = path.resolve(process.argv[5]);
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(rootDir, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const kelwork = path.join(rootDir, 'kelwork');
const results = [];
const check = (name, ok, note) => { results.push({ name, ok: !!ok, note: note || '' });
  console.log((ok ? 'PASS' : 'FAIL') + ' | ' + name + ' | ' + (note || '')); };

const descriptor = () => {
  try { return JSON.parse(fs.readFileSync(path.join(kelwork, 'desktop-session.json'), 'utf8')); }
  catch { return null; }
};

async function engineGet(d, route, conversation) {
  const url = new URL('/api/' + route + (conversation ? '?conversation=' + encodeURIComponent(conversation) : ''), d.url);
  const res = await fetch(url, { headers: { Authorization: 'Bearer ' + d.token }, signal: AbortSignal.timeout(8000) });
  let body = null; try { body = await res.json(); } catch {}
  return { status: res.status, body };
}
async function enginePost(d, route, payload) {
  const url = new URL('/api/' + route, d.url);
  const res = await fetch(url, { method: 'POST',
    headers: { Authorization: 'Bearer ' + d.token, 'content-type': 'application/json' },
    body: JSON.stringify(payload), signal: AbortSignal.timeout(8000) });
  let body = null; try { body = await res.json(); } catch {}
  return { status: res.status, body };
}
async function waitHealthy(d, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try { const s = await engineGet(d, 'state', 'main'); if (s.status === 200) return s.body; } catch {}
    await sleep(1200);
  }
  return null;
}

async function launchApp() {
  const appdata = path.join(rootDir, 'appdata');
  const app = await electron.launch({
    executablePath: path.join(appDir, 'Kel.exe'),
    cwd: appDir,
    timeout: 120000,
    env: {
      ...process.env,
      APPDATA: appdata,
      KEL_DATA_DIR: kelwork,
      KEL_HOST_DATA_DIR: path.join(kelwork, 'host'),
      AIONUI_DISABLE_AUTO_UPDATE: '1',
      KEL_SKIP_TELEMETRY: '1',
    },
  });
  const page = await app.firstWindow({ timeout: 120000 });
  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e).slice(0, 200)));
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(String(m.text()).slice(0, 200)); });
  return { app, page, pageErrors, consoleErrors };
}

async function main() {
  const { app, page, pageErrors, consoleErrors } = await launchApp();
  try {
    let d = null;
    for (let i = 0; i < 60 && !d; i++) { d = descriptor(); if (!d) await sleep(1000); }
    const healthy = d ? await waitHealthy(d, 120000) : null;
    check('engine healthy on installed app', Boolean(healthy), healthy ? 'engine ' + healthy.engine_version : 'no state');
    if (!healthy) throw new Error('engine did not become healthy');

    const convs = (healthy.conversations || []).map((c) => c.id);
    let bId = process.env.RA_CONV_B || null;
    if (!bId) {
      for (const id of convs) {
        if (id === 'main') continue;
        const st = (await engineGet(d, 'state', id)).body || {};
        if ((st.messages || []).some((m) => m.text === 'RA-MARKER-CONTINUITY-B')) { bId = id; break; }
      }
      if (!bId) bId = convs.find((id) => id !== 'main');
    }
    check('two conversations present', convs.includes('main') && Boolean(bId), JSON.stringify(convs));

    if (mode === 'isolation') {
      const stateA = (await engineGet(d, 'state', 'main')).body;
      const stateB = (await engineGet(d, 'state', bId)).body;
      const textsA = (stateA.messages || []).map((m) => m.text);
      const textsB = (stateB.messages || []).map((m) => m.text);
      check('marker message visible in its own conversation', textsB.includes('RA-MARKER-CONTINUITY-B'),
        'B messages=' + JSON.stringify(textsB.slice(0, 5)));
      check('marker message absent from the other conversation', !textsA.includes('RA-MARKER-CONTINUITY-B'),
        'A messages=' + JSON.stringify(textsA.slice(0, 5)));
      check('submission scoped to its conversation',
        (stateB.submissions || []).some((s) => s.id === 'sub_ra_b')
        && !(stateA.submissions || []).some((s) => s.id === 'sub_ra_b'), '');

      const r1 = await enginePost(d, 'approvals', { kind: 'action', id: 'apr_ra_b', allow: true });
      check('live: foreign omission refused', r1.status >= 400 && /another conversation/.test(JSON.stringify(r1.body)), 'status=' + r1.status + ' ' + JSON.stringify(r1.body));
      const r2 = await enginePost(d, 'approvals', { kind: 'action', id: 'apr_ra_b', allow: true, conversation: 'main' });
      check('live: foreign declared-main refused', r2.status >= 400 && /another conversation/.test(JSON.stringify(r2.body)), 'status=' + r2.status + ' ' + JSON.stringify(r2.body));
      const r3 = await enginePost(d, 'approvals', { kind: 'action', id: 'apr_ra_b', allow: true, conversation: bId });
      check('live: owner settles its own approval', r3.status === 200 && String(r3.body.state) === 'approved', JSON.stringify(r3.body));
      const r4 = await enginePost(d, 'approvals', { kind: 'action', id: 'apr_ra_b', allow: true, conversation: bId });
      check('live: duplicate resolve refused', r4.status >= 400, 'status=' + r4.status + ' ' + JSON.stringify(r4.body));
      const r5 = await enginePost(d, 'approvals', { kind: 'action', id: 'apr_ra_a', allow: true });
      const r5ok = (r5.status === 200 && String(r5.body.state) === 'approved')
        || (r5.status >= 400 && /does not match/.test(JSON.stringify(r5.body))
            && !/another conversation/.test(JSON.stringify(r5.body)));
      check('live: main parity (omission on main-owned reaches resolve)', r5ok, JSON.stringify(r5.body));

      await enginePost(d, 'capabilities', { action: 'set', conversation: 'main', capability: 'web', state: 'off' });
      const capsA = (await enginePost(d, 'capabilities', { action: 'get', conversation: 'main' })).body || [];
      const capsB = (await enginePost(d, 'capabilities', { action: 'get', conversation: bId })).body || [];
      const webA = (capsA.find ? capsA.find((c) => c.id === 'web') : null) || {};
      const webB = (capsB.find ? capsB.find((c) => c.id === 'web') : null) || {};
      check('capability override scoped to its conversation',
        webA.effective === 'off' && webB.effective !== 'off',
        'A=' + webA.effective + ' B=' + webB.effective);
      await enginePost(d, 'capabilities', { action: 'set', conversation: 'main', capability: 'web', state: 'default' });

      // Pet settings dead-control observation (objective: does a visible control do anything?)
      await page.evaluate(() => { window.location.hash = '#/settings/pet'; });
      await sleep(2500);
      await page.screenshot({ path: path.join(outDir, 'ra-pet-before.png') });
      const petText = await page.evaluate(() => (document.querySelector('main') || document.body).innerText.replace(/\s+/g, ' ').slice(0, 300));
      let switches = await page.getByRole('switch').count();
      let before = null; let after = null; let clicked = false;
      if (switches > 0) {
        const first = page.getByRole('switch').first();
        before = await first.getAttribute('aria-checked');
        try { await first.click({ timeout: 3000 }); clicked = true; } catch {}
        await sleep(2000);
        after = await page.getByRole('switch').first().getAttribute('aria-checked');
      }
      await page.screenshot({ path: path.join(outDir, 'ra-pet-after.png') });
      let afterReload = null;
      try {
        await page.evaluate(() => { window.location.hash = '#/settings/about'; });
        await sleep(1500);
        await page.evaluate(() => { window.location.hash = '#/settings/pet'; });
        await sleep(2500);
        afterReload = await page.getByRole('switch').first().getAttribute('aria-checked');
        await page.screenshot({ path: path.join(outDir, 'ra-pet-reload.png') });
      } catch {}
      check('pet settings observation (recorded, not a pass/fail claim)', true,
        JSON.stringify({ route: '#/settings/pet', switches, clicked, before, after, afterReload, text: petText.slice(0, 160) }));
    }

    if (mode === 'continuity-check') {
      const stateB = (await engineGet(d, 'state', bId)).body;
      const textsB = (stateB.messages || []).map((m) => m.text);
      check('conversations preserved across reinstall-over', convs.includes('main') && Boolean(bId), JSON.stringify(convs));
      check('seeded message preserved across reinstall-over', textsB.includes('RA-MARKER-CONTINUITY-B'),
        JSON.stringify(textsB.slice(0, 6)));
      check('engine version still 1.6.0', healthy.engine_version === '1.6.0', String(healthy.engine_version));
    }

    fs.writeFileSync(path.join(outDir, 'ra-stunt-results.json'), JSON.stringify(
      { mode, appDir, rootDir, results, pageErrors, consoleErrors, at: new Date().toISOString() }, null, 2));
    const failed = results.filter((r) => !r.ok && !r.name.includes('observation'));
    console.log('SUMMARY: ' + results.length + ' checks, ' + failed.length + ' failed; pageErrors=' + pageErrors.length + ' consoleErrors=' + consoleErrors.length);
    await app.close().catch(() => {});
    process.exit(failed.length ? 1 : 0);
  } catch (err) {
    console.error('STUNT ERROR:', err && err.message);
    try { await app.close(); } catch {}
    process.exit(2);
  }
}

main();
