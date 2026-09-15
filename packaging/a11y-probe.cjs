// Automated accessibility + keyboard evidence probe for the packaged Kel app.
//
// Usage: node a11y-probe.cjs <appDir> <dataDir> <outDir>
// Requires Playwright (PLAYWRIGHT_MODULE or resolvable `playwright`).
//
// Isolation matches capture-screens.cjs: package copy only, env redirected into the run data dir,
// windows parked offscreen, bounded shutdown, task-owned leftovers killed.
//
// Output (JSON, in <outDir>):
//   v13-a11y.json  — contrast samples, font-size histogram, focus order, palette, emoji count
//   v13-a11y-focus-N.png — first three tab stops (focus visibility evidence)
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

const appDir = path.resolve(process.argv[2] || '.');
const dataDir = path.resolve(process.argv[3] || '');
const outDir = path.resolve(process.argv[4] || '');
// --theme dark renders the dark token set (the donor switches on the root attributes) so the audit can
// measure contrast in dark mode as well as light.
const themeIndex = process.argv.indexOf('--theme');
const theme = themeIndex >= 0 ? process.argv[themeIndex + 1] : 'light';
let themeSwitched = false;
const applyTheme = async (target) => {
  if (theme !== 'dark') return;
  // Switch through the app's own Appearance setting once (the donor injects `style#theme-tokens` and
  // Arco's variables; attributes alone leave components on light fallbacks), then re-assert the
  // attributes before each audit so a re-render cannot drift back.
  if (!themeSwitched) {
    themeSwitched = true;
    await target.evaluate(() => { location.hash = '/settings/appearance'; }).catch(() => undefined);
    await target.waitForTimeout(2200);
    await target.getByText('Dark', { exact: true }).first().click({ timeout: 15000 }).catch(() => undefined);
    await target.waitForTimeout(1800);
    await target.evaluate(() => { location.hash = '/guid'; }).catch(() => undefined);
    await target.waitForTimeout(1800);
    return;
  }
  await target
    .evaluate(() => {
      document.documentElement.setAttribute('data-color-scheme', 'default');
      document.documentElement.setAttribute('data-theme', 'dark');
      document.body.setAttribute('arco-theme', 'dark');
    })
    .catch(() => undefined);
};
// Optional V1.4 surface sampling: --routes "work:/work,team-office:/team/office" (same shape as
// capture-screens.cjs --views).
const routeArgIndex = process.argv.indexOf('--routes');
const viewArgIndex = process.argv.indexOf('--views');
const routeSpec = routeArgIndex >= 0 ? process.argv[routeArgIndex + 1]
  : (viewArgIndex >= 0 ? process.argv[viewArgIndex + 1] : '');
const routeList = String(routeSpec || '')
  .split(',')
  .map((entry) => entry.trim())
  .filter(Boolean)
  .map((entry) => {
    const at = entry.indexOf(':');
    const id = at >= 0 ? entry.slice(0, at) : entry;
    const hash = at >= 0 ? entry.slice(at + 1) : '/guid';
    return { id: (id || 'route').replace(/[^a-z0-9-]/gi, '-'), hash: hash || '/guid' };
  });
fs.mkdirSync(outDir, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { schema: 1, startedAt: new Date().toISOString(), errors: [] };
let APP = null;
let ENGINE_PID = null;

function httpGet(descriptor, route) {
  return new Promise((resolve, reject) => {
    const req = http.request(new URL(route, descriptor.url), {
      method: 'GET', headers: { Authorization: 'Bearer ' + descriptor.token }, timeout: 10000,
    }, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => { try { resolve({ status: res.statusCode, body: JSON.parse(data) }); } catch (e) { resolve({ status: res.statusCode }); } });
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
        const probe = await httpGet(parsed, '/api/state?conversation=main').catch(() => null);
        if (probe && probe.status === 200) return parsed;
      }
    } catch (e) { /* not ready */ }
    await sleep(500);
  }
  throw new Error('engine descriptor not ready');
}

// In-page: WCAG contrast of visible text, font-size histogram, palette, emoji count.
const PAGE_AUDIT = () => {
  const parse = (c) => {
    const m = String(c).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map((s) => parseFloat(s));
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => {
    const L1 = lum(a); const L2 = lum(b);
    return Math.round(((Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05)) * 100) / 100;
  };
  const bgOf = (el) => {
    let n = el;
    while (n && n !== document.documentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0.6) return c;
      n = n.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  };
  const samples = [];
  const sizes = {};
  const palette = { text: {}, bg: {} };
  const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (samples.length >= 220) break;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.5) continue;
    const hasDirectText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (!hasDirectText) continue;
    const text = el.textContent.replace(/\s+/g, ' ').trim().slice(0, 60);
    if (!text || seen.has(text)) continue;
    seen.add(text);
    const fg = parse(cs.color);
    const bg = bgOf(el);
    if (!fg) continue;
    const size = Math.round(parseFloat(cs.fontSize) * 10) / 10;
    sizes[size] = (sizes[size] || 0) + 1;
    const rgb = (c) => `rgb(${Math.round(c.r)},${Math.round(c.g)},${Math.round(c.b)})`;
    palette.text[rgb(fg)] = (palette.text[rgb(fg)] || 0) + 1;
    palette.bg[rgb(bg)] = (palette.bg[rgb(bg)] || 0) + 1;
    const large = size >= 24 || (size >= 18.66 && parseInt(cs.fontWeight, 10) >= 700);
    const classes = typeof el.className === 'string' && el.className ? '.' + el.className.split(/\s+/).slice(0, 3).join('.') : '';
    samples.push({ element: el.tagName.toLowerCase() + classes, text, size, weight: cs.fontWeight, fg: rgb(fg), bg: rgb(bg), ratio: ratio(fg, bg), need: large ? 3 : 4.5 });
  }
  const emoji = (document.body.innerText.match(/\p{Extended_Pictographic}/gu) || []).length;
  const failures = samples.filter((s) => s.ratio < s.need);
  const top = (obj, n) => Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => ({ value: k, count: v }));
  return {
    textSamples: samples.length,
    contrastFailures: failures.slice(0, 40),
    contrastFailureCount: failures.length,
    smallestText: Math.min(...Object.keys(sizes).map(Number)),
    largestText: Math.max(...Object.keys(sizes).map(Number)),
    fontSizeHistogram: Object.fromEntries(Object.entries(sizes).sort((a, b) => Number(a[0]) - Number(b[0]))),
    paletteText: top(palette.text, 10),
    paletteBg: top(palette.bg, 10),
    emojiCharacters: emoji,
  };
};

async function main() {
  // Packaged mode: <appDir>/Kel.exe. Dev mode: Electron from desktop/node_modules with the app
  // directory as the first argument (V1.4 UI verification before a candidate package exists).
  const packagedExe = path.join(appDir, 'Kel.exe');
  const packaged = fs.existsSync(packagedExe);
  const launchTarget = packaged
    ? { executablePath: packagedExe, args: ['--no-sandbox', '--window-position=-32000,-32000'] }
    : {
        executablePath: path.join(path.resolve(__dirname, '..'), 'desktop', 'node_modules', 'electron', 'dist', 'electron.exe'),
        args: [appDir, '--no-sandbox', '--window-position=-32000,-32000'],
      };
  out.launchMode = packaged ? 'packaged' : 'dev';
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
  APP = app;
  const page = await app.firstWindow({ timeout: 120000 });
  page.on('pageerror', (e) => out.errors.push('pageerror: ' + String(e)));
  page.on('console', (m) => { if (m.type() === 'error') out.errors.push('console: ' + m.text()); });

  await app.evaluate(({ app, BrowserWindow }) => {
    const stash = (w) => { try { w.setSkipTaskbar(true); w.setPosition(-32000, -32000); } catch (e) {} };
    BrowserWindow.getAllWindows().forEach(stash);
    app.on('browser-window-created', (_e, w) => stash(w));
  });

  const desc = await readDescriptor(dataDir, 120000);
  ENGINE_PID = desc.pid;
  out.engine = { pid: desc.pid, version: desc.engine_version || null };
  await page.locator('text=Work & context').first().waitFor({ timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(2200);

  const win = await app.browserWindow(page);
  await win.evaluate((w) => w.setContentSize(1440, 900));
  await page.waitForTimeout(900);

  await applyTheme(page);
  out.bootScreen = await page.evaluate(PAGE_AUDIT);

  // Fresh-load focus order: collected before any interaction so the sequence reflects what a keyboard
  // user meets on arrival (the shell's first stop is the skip link). The post-interaction order is
  // collected later as `focusOrder`.
  out.focusOrderBoot = [];
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press('Tab');
    await page.waitForTimeout(110);
    out.focusOrderBoot.push(await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return { tag: 'BODY' };
      const cs = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        name: el.getAttribute('aria-label') || el.getAttribute('title'),
        text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40),
        outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}`,
        rect: [Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height)],
        isSkipLink: el.classList.contains('kel-skip'),
      };
    }));
  }
  await page.evaluate(() => { const a = document.activeElement; if (a && a.blur) a.blur(); });

  // Open the work drawer for the second pass.
  const trigger = page.locator('text=Work & context').first();
  if (await trigger.count()) { await trigger.click({ timeout: 8000 }).catch(() => {}); await page.waitForTimeout(1500); }
  out.workDrawer = await page.evaluate(PAGE_AUDIT);

  // V1.4 surfaces: sample each route (--routes id:hash) after the drawer pass.
  out.routes = {};
  for (const route of routeList) {
    await page.evaluate((hash) => { location.hash = hash; }, route.hash).catch(() => {});
    await page.waitForTimeout(1800);
    await applyTheme(page);
    out.routes[route.id] = await page.evaluate(PAGE_AUDIT);
    if (routeList.indexOf(route) < 2) {
      await page.screenshot({
        path: path.join(outDir, `v14-a11y-${route.id}.png`),
      }).catch(() => {});
    }
  }

  // Keyboard order evidence (app-scoped Tab presses inside the test window only).
  // Reset focus first so the sequence starts like a fresh load — otherwise it continues from wherever
  // the previous interaction left it and the shell's first stop (the skip link) looks absent.
  await page.evaluate(() => {
    const active = document.activeElement;
    if (active && typeof active.blur === 'function') active.blur();
  });
  const stops = [];
  for (let i = 0; i < 30; i++) {
    await page.keyboard.press('Tab');
    await page.waitForTimeout(120);
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return { tag: 'BODY' };
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        name: el.getAttribute('aria-label') || el.getAttribute('title'),
        text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 50),
        rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}`,
        boxShadow: String(cs.boxShadow).slice(0, 90),
      };
    });
    stops.push(info);
    if (i < 3) await page.screenshot({ path: path.join(outDir, `v13-a11y-focus-${i + 1}.png`) });
  }
  out.focusOrder = stops;
  out.focusIndicatorMissing = stops.filter((s) => s.tag !== 'BODY' && /none/.test(String(s.outline)) && /none/.test(String(s.boxShadow))).length;

  fs.writeFileSync(path.join(outDir, 'v13-a11y.json'), JSON.stringify(out, null, 2));

  const closeOutcome = await Promise.race([
    app.close().then(() => 'closed').catch(() => 'close-error'),
    sleep(20000).then(() => 'close-timeout'),
  ]);
  out.closeOutcome = closeOutcome;
  if (closeOutcome !== 'closed') {
    await app.evaluate(({ app }) => app.quit()).catch(() => {});
    await sleep(3000);
  }
  for (let i = 0; i < 15; i++) {
    let alive = false;
    try { process.kill(ENGINE_PID, 0); alive = true; } catch { alive = false; }
    if (!alive) break;
    await sleep(1000);
  }
  try { process.kill(ENGINE_PID); } catch (e) { /* gone */ }
  fs.writeFileSync(path.join(outDir, 'v13-a11y.json'), JSON.stringify(out, null, 2));
  console.log(JSON.stringify({
    ok: true,
    launchMode: out.launchMode,
    contrastFailures: out.workDrawer.contrastFailureCount + out.bootScreen.contrastFailureCount,
    routeContrastFailures: Object.entries(out.routes || {}).map(([id, r]) => [id, r.contrastFailureCount]),
    smallestText: out.bootScreen.smallestText,
    emoji: out.bootScreen.emojiCharacters + out.workDrawer.emojiCharacters,
    focusStops: out.focusOrder.length,
    closeOutcome: out.closeOutcome,
  }, null, 2));
  process.exit(0);
}

main().catch((err) => {
  out.fatal = String(err).slice(0, 600);
  try { fs.writeFileSync(path.join(outDir, 'v13-a11y.json'), JSON.stringify(out, null, 2)); } catch (e) {}
  if (ENGINE_PID) { try { process.kill(ENGINE_PID); } catch (e) {} }
  console.error('A11Y-PROBE-FAILED', out.fatal);
  process.exit(1);
});
