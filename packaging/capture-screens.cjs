// Repeatable packaged-UI screenshot harness for Kel (V1.3 baseline + V1.4 regression).
//
// Usage:
//   node capture-screens.cjs <appDir> <dataDir> <outDir> [--tag v13] [--widths 1440x900,...] [--views work:/work,team-office:/team/office] [--explore]
//
// Requirements: Playwright resolvable (`PLAYWRIGHT_MODULE` env, or `playwright` on NODE_PATH).
//
// Isolation guarantees:
//   - KEL_DATA_DIR / KEL_HOST_DATA_DIR / AIONUI_E2E_* are redirected into <dataDir>.
//   - Windows are moved offscreen, removed from the taskbar, and never focused.
//   - No synthetic input is sent to the desktop; all interaction goes through CDP.
//   - On exit the engine pid from desktop-session.json is awaited; task-owned leftovers are killed.
//
// Output: PNGs + manifest.json in <outDir> (view, size, inner size, route hash, errors).
const path = require('path');
const fs = require('fs');
const http = require('http');

let playwright;
try {
  playwright = require('playwright');
} catch (error) {
  playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
}
const { _electron: electron } = playwright;

const argv = process.argv.slice(2);
const appDir = path.resolve(argv[0] || '.');
const dataDir = path.resolve(argv[1] || '');
const outDir = path.resolve(argv[2] || '');
const flag = (name, dflt) => {
  const i = argv.indexOf('--' + name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
};
const hasFlag = (name) => argv.includes('--' + name);
const tag = flag('tag', 'v13');
const theme = flag('theme', 'light');
const explore = hasFlag('explore');
const widths = String(flag('widths', '1440x900,1280x720,1920x1080,2560x1440,1024x768'))
  .split(',')
  .map((s) => s.split('x').map(Number))
  .filter((p) => p.length === 2 && p[0] > 0 && p[1] > 0);
// Optional route views (V1.4 surfaces): --views "work:/work,team-office:/team/office" — captured at
// every width alongside the core view set.
const routeViews = String(flag('views', ''))
  .split(',')
  .map((entry) => entry.trim())
  .filter(Boolean)
  .map((entry) => {
    const at = entry.indexOf(':');
    const id = at >= 0 ? entry.slice(0, at) : entry;
    const hash = at >= 0 ? entry.slice(at + 1) : '/guid';
    return { id: (id || 'route').replace(/[^a-z0-9-]/gi, '-'), hash: hash || '/guid' };
  });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const manifest = { schema: 1, tag, appDir, dataDir, startedAt: new Date().toISOString(), entries: [], errors: [], shutdown: {} };
let APP = null;
let appProc = null;
let ENGINE_PID = null;
fs.mkdirSync(outDir, { recursive: true });

function httpRequest(descriptor, route) {
  return new Promise((resolve, reject) => {
    const url = new URL(route, descriptor.url);
    const req = http.request(url, {
      method: 'GET',
      headers: { Authorization: 'Bearer ' + descriptor.token },
      timeout: 10000,
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
    req.end();
  });
}

async function readDescriptor(dir, timeoutMs) {
  const file = path.join(dir, 'desktop-session.json');
  const deadline = Date.now() + (timeoutMs || 90000);
  while (Date.now() < deadline) {
    try {
      const parsed = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
      if (parsed && parsed.url && parsed.token) {
        const probe = await httpRequest(parsed, '/api/state?conversation=main').catch(() => null);
        if (probe && probe.status === 200) return parsed;
      }
    } catch (e) { /* not ready yet */ }
    await sleep(500);
  }
  throw new Error('engine descriptor not ready: ' + file);
}

async function main() {
  // Packaged mode: <appDir>/Kel.exe. Dev mode (no Kel.exe): Electron from
  // desktop/node_modules with the app directory as the first argument — used to verify V1.4 UI
  // before a candidate package exists. Isolation env + parking are identical in both modes.
  const packagedExe = path.join(appDir, 'Kel.exe');
  const packaged = fs.existsSync(packagedExe);
  const launchTarget = packaged
    ? { executablePath: packagedExe, args: ['--no-sandbox', '--window-position=-32000,-32000'] }
    : {
        executablePath: path.join(path.resolve(__dirname, '..'), 'desktop', 'node_modules', 'electron', 'dist', 'electron.exe'),
        args: [appDir, '--no-sandbox', '--window-position=-32000,-32000'],
      };
  manifest.launchMode = packaged ? 'packaged' : 'dev';
  const app = await electron.launch({
    executablePath: launchTarget.executablePath,
    cwd: appDir,
    timeout: 120000,
    env: {
      ...process.env,
      KEL_DATA_DIR: dataDir,
      KEL_HOST_DATA_DIR: path.join(dataDir, 'host'),
      AIONUI_E2E_TEST: '1',
      AIONUI_E2E_USER_DATA_DIR: path.join(dataDir, 'e2e-user-data'),
      KEL_SKIP_TELEMETRY: '1',
    },
    args: launchTarget.args,
  });
  manifest.launchedAt = new Date().toISOString();
  APP = app;
  appProc = app.process();

  const page = await app.firstWindow({ timeout: 120000 });
  page.on('pageerror', (e) => manifest.errors.push('pageerror: ' + String(e)));
  page.on('console', (m) => { if (m.type() === 'error') manifest.errors.push('console: ' + m.text()); });

  // Park every window offscreen + out of the taskbar; keep future windows parked too.
  await app.evaluate(({ app, BrowserWindow }) => {
    const stash = (w) => { try { w.setSkipTaskbar(true); w.setPosition(-32000, -32000); } catch (e) {} };
    BrowserWindow.getAllWindows().forEach(stash);
    app.on('browser-window-created', (_e, w) => stash(w));
  });

  const desc = await readDescriptor(dataDir, 120000);
  manifest.engine = { pid: desc.pid, version: desc.engine_version || null };
  ENGINE_PID = desc.pid;

  await page.waitForLoadState('domcontentloaded').catch(() => {});
  // UI ready gate: the Kel work-context trigger renders once the chat shell is live.
  await page.locator('text=Work & context').first().waitFor({ timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(2500);
  // A freshly seeded capture root has no onboarding flag, so the shell offers first-run setup. Dismiss
  // it through the product's own affordance ("Skip setup") so captures show the app itself.
  const skipSetup = page.getByRole('button', { name: /Skip setup|Skip for now/i }).first();
  if (await skipSetup.count()) {
    await skipSetup.click({ timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(2500);
  }
  // Dark mode is switched through the app's OWN Appearance setting. The donor applies a theme by
  // injecting `style#theme-tokens` plus Arco's variables; switching attributes alone leaves Arco
  // components on their light fallbacks (measured: three labels kept light colours).
  if (theme === 'dark') {
    await page.evaluate(() => { location.hash = '/settings/appearance'; }).catch(() => {});
    await page.waitForTimeout(2200);
    await page.getByText('Dark', { exact: true }).first().click({ timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1800);
    manifest.themeSwitch = await page.evaluate(() => ({
      dataTheme: document.documentElement.getAttribute('data-theme'),
      arcoTheme: document.body.getAttribute('arco-theme'),
      injectedTokens: Boolean(document.getElementById('theme-tokens')),
    }));
    await page.evaluate(() => { location.hash = '/guid'; }).catch(() => {});
    await page.waitForTimeout(1800);
  }

  const windowHandle = await app.browserWindow(page);
  const setSize = async (w, h) => {
    await windowHandle.evaluate((win, [width, height]) => win.setContentSize(width, height), [w, h]);
    await page.waitForTimeout(900);
  };
  const innerSize = async () => page.evaluate(() => [window.innerWidth, window.innerHeight]);

  let index = 0;
  const fullTexts = [];
  const shot = async (name, extra) => {
    index += 1;
    const label = String(index).padStart(2, '0');
    const file = path.join(outDir, `${tag}-${label}-${name}.png`);
    // Dark mode is the donor's root-attribute switch; re-apply it before every capture so a re-render
    // during the run cannot silently drop back to the light token set.
    if (theme === 'dark') {
      await page
        .evaluate(() => {
          // Both halves of the donor's theme switch: the root attribute for the CSS-file tokens and
          // body[arco-theme] for Arco's component styles.
          document.documentElement.setAttribute('data-color-scheme', 'default');
          document.documentElement.setAttribute('data-theme', 'dark');
          document.body.setAttribute('arco-theme', 'dark');
        })
        .catch(() => {});
    }
    await page.screenshot({ path: file });
    const stat = fs.statSync(file);
    const fullText = String(await page.locator('body').innerText().catch(() => ''));
    const textSample = fullText.replace(/\s+/g, ' ').trim().slice(0, 300);
    fullTexts.push({ view: name, file: path.basename(file), text: fullText.slice(0, 12000) });
    manifest.entries.push({
      view: name,
      file: path.basename(file),
      inner: await innerSize().catch(() => null),
      hash: await page.evaluate(() => location.hash).catch(() => null),
      title: await page.title().catch(() => null),
      bytes: stat.size,
      blankSuspect: stat.size < 20000,
      textSample,
      ...(extra || {}),
    });
  };

  const clickIf = async (selector, settleMs) => {
    const loc = page.locator(selector).first();
    if (await loc.count()) {
      await loc.click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(settleMs || 900);
      return true;
    }
    return false;
  };

  // --- discovery (explore mode only) -------------------------------------
  if (explore) {
    const discovery = await page.evaluate(() => {
      const pick = (sel) => Array.from(document.querySelectorAll(sel)).slice(0, 250).map((el) => ({
        tag: el.tagName,
        text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80),
        aria: el.getAttribute('aria-label'),
        title: el.getAttribute('title'),
        cls: String(el.className || '').slice(0, 100),
      }));
      return { buttons: pick('button, [role="button"]'), links: pick('a'), labels: pick('[aria-label]') };
    });
    fs.writeFileSync(path.join(outDir, `${tag}-discovery.json`), JSON.stringify(discovery, null, 2));
    await shot('00-explore-boot');
  }

  // --- capture set at the first width ------------------------------------
  const [primaryW, primaryH] = widths[0];
  await setSize(primaryW, primaryH);
  await shot('01-boot-chat');

  const drawerOpened = await clickIf('text=Work & context', 1600);
  if (drawerOpened) {
    await shot('02-work-drawer');
    await shot('02b-work-tab-default');
    const tabs = [
      ['03-continue', 'Continue work'],
      ['04-knowledge', 'Project knowledge'],
      ['05-map', 'Project map'],
      ['06-recipes', 'Recipes'],
    ];
    for (const [name, label] of tabs) {
      if (await clickIf(`text=${label}`, 1000)) await shot(name);
    }
    if (await clickIf('button:has-text("Preview")', 1400)) {
      await shot('07-recipe-preview');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }
    if (await clickIf('text=Project map', 900)) {
      if (await clickIf('button:has-text("Refresh map")', 2800)) {
        await shot('07b-map-after-refresh');
      }
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(700);
    await shot('08-after-drawer-close');
  }

  // --- settings (open via the sidebar entry, then sweep settings routes) --
  const settingsCandidates = [
    '[aria-label*="settings" i]',
    'text=Settings',
    '[class*="setting" i]',
  ];
  let settingsOpened = false;
  for (const sel of settingsCandidates) {
    if (await clickIf(sel, 1400)) { settingsOpened = true; break; }
  }
  if (settingsOpened) {
    await shot('09-settings-open');
    const settingsPages = ['appearance', 'system', 'pet', 'webui', 'archived', 'about',
      'model', 'agent', 'skills', 'tools'];
    for (const pageName of settingsPages) {
      await page.evaluate((p) => { location.hash = '#/settings/' + p; }, pageName).catch(() => {});
      await page.waitForTimeout(1600);
      await shot(`09-settings-${pageName}`);
    }
  }

  // --- V1.4 route views (--views id:hash) --------------------------------
  for (const view of routeViews) {
    await page.evaluate((hash) => { location.hash = hash; }, view.hash).catch(() => {});
    await page.waitForTimeout(1800);
    await shot(`12-${view.id}`);
  }
  for (const [rw, rh] of widths.slice(1)) {
    await setSize(rw, rh);
    for (const view of routeViews) {
      await page.evaluate((hash) => { location.hash = hash; }, view.hash).catch(() => {});
      await page.waitForTimeout(1200);
      await shot(`13-${view.id}-at-${rw}x${rh}`);
    }
  }

  // --- pet windows (--pets): enable the desktop pet through its own settings switch, then capture
  //     every window whose URL is a pet document. Zero pets are recorded explicitly, so the gap is
  //     visible in the manifest instead of being silently absent.
  if (hasFlag('pets')) {
    manifest.pets = [];
    await page.evaluate(() => { location.hash = '/settings/pet'; }).catch(() => {});
    await page.waitForTimeout(2200);
    const toggle = page.locator('.arco-switch').first();
    if (await toggle.count()) {
      await toggle.click({ timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2600);
    }
    const mainUrl = page.url();
    for (const win of app.windows()) {
      const url = win.url();
      // Identify pet windows by exclusion (never the main window) plus a pet-ish URL or title, rather
      // than by an exact filename — the pet documents load with their own URL shape.
      if (url === mainUrl) continue;
      const title = await win.title().catch(() => '');
      if (!/pet/i.test(url) && !/pet/i.test(title)) continue;
      const label = (url.split('/').pop() || 'pet').replace(/[^a-z0-9.]/gi, '-');
      const file = path.join(outDir, `${tag}-pet-${label}.png`);
      await win.screenshot({ path: file }).catch(() => {});
      const size = await win
        .evaluate(() => ({ w: window.innerWidth, h: window.innerHeight }))
        .catch(() => null);
      manifest.pets.push({ url, file: path.basename(file), size });
    }
    manifest.petWindowCount = manifest.pets.length;
    await page.evaluate(() => { location.hash = '/guid'; }).catch(() => {});
    await page.waitForTimeout(1500);
  }

  // --- resize passes: core views at the remaining widths ------------------
  for (const [w, h] of widths.slice(1)) {
    await setSize(w, h);
    await page.evaluate(() => { location.hash = '#/guid'; }).catch(() => {});
    await page.waitForTimeout(900);
    await shot(`10-boot-chat-at-${w}x${h}`);
    if (drawerOpened) {
      if (await clickIf('text=Work & context', 1600)) {
        await shot(`11-work-drawer-at-${w}x${h}`);
        await page.keyboard.press('Escape');
        await page.waitForTimeout(700);
      }
    }
  }

  // --- artifacts checkpoint (texts + manifest) before shutdown ------------
  const manifestPath = path.join(outDir, `${tag}-manifest.json`);
  fs.writeFileSync(path.join(outDir, `${tag}-texts.jsonl`),
    fullTexts.map((r) => JSON.stringify(r)).join('\n') + '\n');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));

  // --- shutdown / orphan check (bounded; must never fail the run) --------
  manifest.finishedAt = new Date().toISOString();
  const closeOutcome = await Promise.race([
    app.close().then(() => 'closed').catch(() => 'close-error'),
    sleep(20000).then(() => 'close-timeout'),
  ]);
  manifest.closeOutcome = closeOutcome;
  if (closeOutcome !== 'closed') {
    await app.evaluate(({ app }) => app.quit()).catch(() => {});
    await sleep(3000);
  }
  let engineStopped = false;
  for (let i = 0; i < 15; i++) {
    let alive = false;
    try { process.kill(ENGINE_PID, 0); alive = true; } catch { alive = false; }
    if (!alive) { engineStopped = true; break; }
    await sleep(1000);
  }
  let engineKilled = false;
  if (!engineStopped) {
    try { process.kill(ENGINE_PID); engineKilled = true; } catch (e) {}
    await sleep(1500);
    let alive = false;
    try { process.kill(ENGINE_PID, 0); alive = true; } catch { alive = false; }
    if (!alive) engineStopped = true;
  }
  try { if (appProc && appProc.exitCode === null) appProc.kill(); } catch (e) {}
  manifest.shutdown = {
    engineStopped: engineStopped && !engineKilled,
    engineKilled,
    appExitCode: appProc ? appProc.exitCode : null,
  };

  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(JSON.stringify({
    ok: true,
    shots: manifest.entries.length,
    errors: manifest.errors.slice(0, 5),
    blankSuspect: manifest.entries.filter((e) => e.blankSuspect).map((e) => e.file),
    shutdown: manifest.shutdown,
  }, null, 2));
  process.exit(0);
}

const watchdog = setTimeout(async () => {
  manifest.watchdog = true;
  try { if (APP) await APP.close().catch(() => {}); } catch (e) { /* ignore */ }
  if (ENGINE_PID) { try { process.kill(ENGINE_PID); } catch (e) { /* gone */ } }
  try { fs.writeFileSync(path.join(outDir, `${tag}-manifest.json`), JSON.stringify(manifest, null, 2)); } catch (e) {}
  console.error('WATCHDOG-EXIT');
  process.exit(3);
}, 720000);
watchdog.unref();
main().catch(async (error) => {
  manifest.fatal = String(error).slice(0, 800);
  manifest.fatalStack = String((error && error.stack) || '').slice(0, 2000);
  try {
    if (APP) await APP.close().catch(() => {});
  } catch (e) { /* ignore */ }
  if (ENGINE_PID) {
    try { process.kill(ENGINE_PID); } catch (e) { /* already gone */ }
  }
  try { fs.writeFileSync(path.join(outDir, `${tag}-manifest.json`), JSON.stringify(manifest, null, 2)); } catch (e) {}
  console.error('CAPTURE-FAILED', manifest.fatal);
  process.exit(1);
});
