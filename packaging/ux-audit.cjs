// Kel V1.5 user-journey audit harness.
//
// Drives the packaged Kel application (frozen release or a rebuilt candidate) with Playwright,
// behaving like a user: fresh first launch, onboarding walk, primary-navigation click-through,
// settings tour, command palette, keyboard tab order, and readability probes. Everything is
// recorded as JSON + screenshots so findings can be compared across builds.
//
// Usage:
//   NODE_PATH=<node_modules-with-playwright> node packaging/ux-audit.cjs <appDir> <rootDir> <outDir> <scenario>
//
//   <appDir>   directory containing Kel.exe (packaged) or a dev build root
//   <rootDir>  isolated user profile root: <rootDir>/appdata (APPDATA), <rootDir>/kelwork (KEL_DATA_DIR)
//   <outDir>   where JSON + screenshots are written
//   <scenario> first-run | tour | settings | palette | keyboard | readability | compose | all
//
// The harness never writes inside <appDir>; the frozen release stays byte-identical.
const fs = require('fs');
const path = require('path');

function resolvePlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return process.env.PLAYWRIGHT_MODULE;
  try {
    return require.resolve('playwright');
  } catch (e) {}
  try {
    return require.resolve('@playwright/test');
  } catch (e) {}
  console.error('playwright not found; set PLAYWRIGHT_MODULE to a playwright install.');
  process.exit(2);
}
const { _electron: electron } = require(resolvePlaywright());

const appDir = path.resolve(process.argv[2] || '.');
const rootDir = path.resolve(process.argv[3] || '');
const outDir = path.resolve(process.argv[4] || '.');
const scenario = (process.argv[5] || 'all').toLowerCase();
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(rootDir, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const JARGON =
  /\b(worker|workers|agent|agents|provider|providers|model|models|lease|leases|scope|scopes|guardrail|guardrails|routing|milestone|milestones|verdict|continuation|artifact|artifacts|acceptance|claim|claims|engine|checkpoint|digest|snapshot|role snapshot|orchestrat\w*|delegat\w*|escalat\w*|quota|token|ACP|schema|sandbox|credential|credentials|autonomy|lease\b|fencing|broker|adopt\w*|projection|envelope|packet)\b/gi;

async function launchApp({ fresh = false } = {}) {
  const appdata = path.join(rootDir, 'appdata');
  const kelwork = path.join(rootDir, 'kelwork');
  if (fresh) {
    fs.rmSync(rootDir, { recursive: true, force: true });
  }
  fs.mkdirSync(appdata, { recursive: true });
  fs.mkdirSync(kelwork, { recursive: true });
  const packaged = fs.existsSync(path.join(appDir, 'Kel.exe'));
  const app = await electron.launch({
    executablePath: packaged
      ? path.join(appDir, 'Kel.exe')
      : path.join(path.resolve(__dirname, '..'), 'desktop', 'node_modules', 'electron', 'dist', 'electron.exe'),
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
    args: packaged
      ? ['--no-sandbox', '--window-position=-32000,-32000', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream']
      : [appDir, '--no-sandbox', '--window-position=-32000,-32000', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
  });
  const page = await app.firstWindow({ timeout: 120000 });
  const consoleErrors = [];
  page.on('pageerror', (e) => consoleErrors.push(String(e).slice(0, 300)));
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300));
  });
  try {
    await app.evaluate(async ({ BrowserWindow }) => {
      for (const win of BrowserWindow.getAllWindows()) {
        win.setPosition(-32000, -32000);
        win.setSkipTaskbar(true);
      }
    });
  } catch {}
  await page.setViewportSize({ width: 1440, height: 900 });
  return { app, page, kelwork, consoleErrors };
}

async function closeApp(app, kelwork, results) {
  try {
    await Promise.race([app.close(), sleep(20000)]);
    results.closeOutcome = 'closed';
  } catch {
    results.closeOutcome = 'close-timeout';
  }
  try {
    const session = JSON.parse(fs.readFileSync(path.join(kelwork, 'desktop-session.json'), 'utf8').replace(/^\uFEFF/, ''));
    if (session.pid) {
      process.kill(session.pid);
      results.engineKilled = true;
    }
  } catch {
    results.engineKilled = false;
  }
}

function save(name, results) {
  const file = path.join(outDir, `${name}.json`);
  fs.writeFileSync(file, JSON.stringify(results, null, 2));
  console.log(`[ux-audit] wrote ${file}`);
}

async function hash(page) {
  return page.evaluate(() => location.hash).catch(() => null);
}

async function bodyText(page, limit = 4000) {
  const text = await page.evaluate(() => (document.body ? document.body.innerText : '')).catch(() => '');
  return text.slice(0, limit);
}

async function shot(page, name) {
  try {
    await page.screenshot({ path: path.join(outDir, `${name}.png`) });
  } catch {}
}

// ---- generic page probes -------------------------------------------------------------

async function probeInteractives(page) {
  return page.evaluate(() => {
    const els = Array.from(
      document.querySelectorAll(
        'button,a[href],[role="button"],[role="tab"],[role="menuitem"],[role="option"],[role="switch"],[role="checkbox"],input,select,textarea,[tabindex]:not([tabindex="-1"])'
      )
    );
    const visible = els.filter((el) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return r.width > 1 && r.height > 1 && cs.visibility !== 'hidden' && cs.display !== 'none';
    });
    return visible.slice(0, 260).map((el) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        tag: el.tagName.toLowerCase(),
        role: el.getAttribute('role') || '',
        type: el.getAttribute('type') || '',
        name: (el.getAttribute('aria-label') || el.innerText || el.value || el.placeholder || '')
          .replace(/\s+/g, ' ')
          .trim()
          .slice(0, 90),
        disabled: Boolean(el.disabled) || el.getAttribute('aria-disabled') === 'true',
        checked: el.getAttribute('aria-checked') ?? null,
        tabIndex: el.tabIndex,
        fontSize: cs.fontSize,
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        cls: String(el.className || '').slice(0, 80),
      };
    });
  });
}

async function probeHeadings(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,[role="heading"]')).map((el) => ({
      tag: el.tagName.toLowerCase(),
      text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 120),
    }))
  );
}

async function probeTabs(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll('[role="tab"]')).map((el) => ({
      text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80),
      selected: el.getAttribute('aria-selected'),
    }))
  );
}

async function probeScroll(page) {
  return page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('div,main,section,ul')) {
      const cs = getComputedStyle(el);
      if (!/(auto|scroll)/.test(cs.overflowY)) continue;
      if (el.scrollHeight > el.clientHeight + 4 && el.clientHeight > 100) {
        out.push({
          cls: String(el.className || '').slice(0, 70),
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          delta: el.scrollHeight - el.clientHeight,
        });
      }
      if (out.length >= 12) break;
    }
    return out;
  });
}

async function probeTerms(page) {
  const text = await bodyText(page, 12000);
  const found = {};
  let m;
  JARGON.lastIndex = 0;
  while ((m = JARGON.exec(text)) !== null) {
    const key = m[1].toLowerCase();
    if (!found[key]) {
      const start = Math.max(0, m.index - 40);
      found[key] = { count: 0, sample: text.slice(start, m.index + key.length + 45).replace(/\s+/g, ' ').trim() };
    }
    found[key].count += 1;
    if (Object.keys(found).length > 60) break;
  }
  return found;
}

async function probeComposer(page) {
  return page.evaluate(() => {
    const cands = Array.from(
      document.querySelectorAll(
        '[data-testid="sendbox-input"],[data-testid="guid-input"],textarea,[contenteditable="true"],[role="textbox"]'
      )
    );
    const visible = cands.filter((el) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return r.width > 80 && r.height > 12 && cs.visibility !== 'hidden' && cs.display !== 'none';
    });
    return visible.map((el) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        tag: el.tagName.toLowerCase(),
        testid: el.getAttribute('data-testid') || '',
        placeholder: el.getAttribute('placeholder') || '',
        ariaLabel: el.getAttribute('aria-label') || '',
        fontSize: cs.fontSize,
        valueLength: (el.value || '').length,
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        outer: el.outerHTML.slice(0, 160),
      };
    });
  });
}

async function probeSider(page) {
  return page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll('button,[role="button"],a[href]'));
    return buttons
      .filter((el) => {
        const r = el.getBoundingClientRect();
        return r.width > 4 && r.height > 4 && r.x < 320;
      })
      .map((el) => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return {
          name: (el.getAttribute('aria-label') || el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 80),
          tag: el.tagName.toLowerCase(),
          current: el.getAttribute('aria-current') || '',
          fontSize: cs.fontSize,
          color: cs.color,
          rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        };
      });
  });
}

// Readability: font-size histogram of visible text + contrast offenders (WCAG AA).
async function probeReadability(page) {
  return page.evaluate(() => {
    const parse = (c) => {
      const m = c && c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
      return m ? { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] } : null;
    };
    const lum = ({ r, g, b }) => {
      const f = (v) => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const ratio = (fg, bg) => {
      const L1 = lum(fg);
      const L2 = lum(bg);
      const [a, b] = L1 > L2 ? [L1, L2] : [L2, L1];
      return Math.round(((a + 0.05) / (b + 0.05)) * 100) / 100;
    };
    const bgOf = (el) => {
      let e = el;
      while (e) {
        const cs = getComputedStyle(e);
        const c = parse(cs.backgroundColor);
        if (c && c.a > 0.6) return c;
        e = e.parentElement;
      }
      return { r: 255, g: 255, b: 255, a: 1 };
    };
    const histogram = {};
    const offenders = [];
    const tiny = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    let guard = 0;
    while ((node = walker.nextNode()) && guard < 2500) {
      guard += 1;
      const text = (node.textContent || '').replace(/\s+/g, ' ').trim();
      if (!text) continue;
      const el = node.parentElement;
      if (!el) continue;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      if (r.width < 2 || r.height < 2 || cs.visibility === 'hidden' || cs.display === 'none') continue;
      const px = Math.round(parseFloat(cs.fontSize));
      // SVG text paints with `fill`, not `color`; measuring color here produced false positives
      // (e.g. the white-on-black Kel logo counted as black-on-black). Use fill when present.
      const isSvg = (el.namespaceURI || '').indexOf('svg') >= 0;
      const paint = isSvg ? cs.fill : cs.color;
      histogram[px] = (histogram[px] || 0) + text.length;
      const fg = parse(paint);
      if (!fg) continue;
      const cr = ratio(fg, bgOf(el));
      const bold = parseInt(cs.fontWeight, 10) >= 600;
      const large = px >= 24 || (px >= 18.66 && bold);
      const need = large ? 3 : 4.5;
      const entry = {
        text: text.slice(0, 70), px, contrast: cr, need, color: paint,
        cls: String(typeof el.className === 'string' ? el.className : el.getAttribute('class') || '').slice(0, 400),
        trail: (() => {
          const parts = [];
          let walk = el;
          for (let i = 0; i < 4 && walk; i += 1) {
            parts.push(String(walk.tagName || '').toLowerCase() + '.' + String(walk.className || '').slice(0, 400));
            walk = walk.parentElement;
          }
          return parts;
        })(),
        bg: (() => { const c = bgOf(el); return 'rgb(' + c.r + ', ' + c.g + ', ' + c.b + ')'; })(),
      };
      if (cr < need && offenders.length < 40) offenders.push(entry);
      if (px < 13 && tiny.length < 40) tiny.push(entry);
    }
    return { histogram, offenders, tiny };
  });
}

async function probeFocusRing(page) {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!el) return null;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      name: (el.getAttribute('aria-label') || el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70),
      outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}`,
      boxShadow: cs.boxShadow.slice(0, 80),
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
    };
  });
}

// ---- scenarios -----------------------------------------------------------------------

// Returning-but-unflagged profiles (pre-onboarding installs) are offered the flow once.
// Walk it to the end, or Skip, so the rest of the tour runs like a normal session.
async function dismissOnboarding(page) {
  const info = { present: false, steps: 0, method: null };
  if (!String(await hash(page)).includes('/onboarding')) return info;
  info.present = true;
  const FORWARD = [/^Start using Kel$/, /^Finish$/, /^Continue$/, /^Next$/, /^Get started$/];
  for (let i = 0; i < 10; i += 1) {
    let advanced = false;
    for (const re of FORWARD) {
      const btn = page.getByRole('button', { name: re }).first();
      if (await btn.count()) {
        await btn.click({ timeout: 8000 }).catch(() => {});
        advanced = true;
        info.steps += 1;
        await sleep(800);
        break;
      }
    }
    const h = await hash(page);
    if (!String(h).includes('/onboarding')) {
      info.method = info.steps > 0 ? 'completed' : 'left';
      break;
    }
    if (!advanced) {
      const skip = page.getByRole('button', { name: /^Skip setup$/i }).first();
      if (await skip.count()) {
        await skip.click({ timeout: 8000 }).catch(() => {});
        info.method = 'skipped';
        await sleep(1200);
      }
      break;
    }
  }
  info.finalHash = await hash(page);
  return info;
}

// The composer placeholder is a typewriter animation; sample it over time and keep the
// longest text actually rendered, which is what a user ends up reading.
async function probeComposerPlaceholder(page) {
  const seen = new Set();
  for (let i = 0; i < 8; i += 1) {
    const list = await probeComposer(page);
    if (list[0]) seen.add(list[0].placeholder || '');
    await sleep(500);
  }
  const arr = [...seen];
  arr.sort((a, b) => b.length - a.length);
  return arr.slice(0, 3);
}

async function scenarioFirstRun() {
  const results = { schema: 1, scenario: 'first-run', steps: [], errors: [] };
  const t0 = Date.now();
  const { app, page, kelwork, consoleErrors } = await launchApp({ fresh: true });
  try {
    // hash timeline until stable
    const timeline = [];
    let composerAt = null;
    for (let tick = 0; tick < 24; tick += 1) {
      const h = await hash(page);
      if (timeline[timeline.length - 1]?.hash !== h) timeline.push({ ms: Date.now() - t0, hash: h });
      if (!composerAt) {
        const composer = await probeComposer(page);
        if (composer.length) composerAt = Date.now() - t0;
      }
      if (tick >= 6 && composerAt) break;
      await sleep(500);
    }
    results.timeline = timeline;
    results.timeToComposerBeforeOnboardingMs = composerAt;
    results.hashAtBoot = await hash(page);
    results.title = await page.title();
    results.bodyText = await bodyText(page, 2500);
    results.sider = await probeSider(page);
    results.composer = await probeComposer(page);
    await shot(page, 'first-run-01-boot');

    if (String(results.hashAtBoot || '').includes('/onboarding')) {
      results.onboarding = { steps: [] };
      let clicks = 0;
      for (let i = 0; i < 9; i += 1) {
        const step = await page.evaluate(() => ({
          heading: Array.from(document.querySelectorAll('h1,h2,h3,[role="heading"]'))
            .map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim())
            .filter(Boolean)
            .slice(0, 4),
          text: (document.body.innerText || '').slice(0, 1600),
          buttons: Array.from(document.querySelectorAll('button,[role="button"],a[href]'))
            .filter((el) => {
              const r = el.getBoundingClientRect();
              return r.width > 4 && r.height > 4;
            })
            .map((el) => ({
              name: (el.getAttribute('aria-label') || el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70),
              disabled: Boolean(el.disabled),
            }))
            .filter((b) => b.name),
        }));
        step.hash = await hash(page);
        step.atMs = Date.now() - t0;
        step.skipOffered = (await page.getByRole('button', { name: /^Skip setup$/i }).count()) > 0;
        results.onboarding.steps.push(step);
        await shot(page, `first-run-onboarding-${i + 1}`);
        const FORWARD = [/^Start using Kel$/, /^Finish$/, /^Continue$/, /^Next$/, /^Get started$/];
        let advanced = false;
        for (const re of FORWARD) {
          const btn = page.getByRole('button', { name: re }).first();
          if (await btn.count()) {
            await btn.click({ timeout: 10000 }).catch((e) => results.errors.push(`click: ${String(e).slice(0, 200)}`));
            advanced = true;
            clicks += 1;
            await sleep(900);
            break;
          }
        }
        if (!advanced) break;
        const h = await hash(page);
        if (!String(h).includes('/onboarding')) break;
      }
      results.onboarding.forwardClicks = clicks;
      results.onboarding.finishedHash = await hash(page);
      results.onboarding.totalMs = Date.now() - t0;
    }
    // "Useful work within moments": how long until the composer is actually on screen.
    let landingComposerAt = null;
    for (let tick = 0; tick < 60; tick += 1) {
      const composer = await probeComposer(page);
      if (composer.length) {
        landingComposerAt = Date.now() - t0;
        break;
      }
      await sleep(500);
    }
    results.timeToComposerMs = landingComposerAt;
    results.hashAfterOnboarding = await hash(page);
    results.landingBody = await bodyText(page, 2000);
    results.landingComposer = await probeComposer(page);
    results.landingPlaceholderSamples = await probeComposerPlaceholder(page);
    results.landingInteractives = await probeInteractives(page);
    results.landingSider = await probeSider(page);
    // A normal user next looks for somewhere to type: measure the New Chat hop.
    results.newChat = { clicked: false, msToComposer: null };
    if (!results.landingComposer.length) {
      const tHop = Date.now();
      const newChat = page.getByRole('button', { name: /^New Chat$/ }).first();
      if (await newChat.count()) {
        await newChat
          .click({ timeout: 10000 })
          .catch((e) => results.errors.push(`newchat: ${String(e).slice(0, 200)}`));
        results.newChat.clicked = true;
        for (let tick = 0; tick < 40; tick += 1) {
          const composer = await probeComposer(page);
          if (composer.length) {
            results.newChat.msToComposer = Date.now() - tHop;
            break;
          }
          await sleep(400);
        }
        results.newChat.hashAfter = await hash(page);
        results.newChat.composer = await probeComposer(page);
        results.newChat.placeholderSamples = await probeComposerPlaceholder(page);
        await shot(page, 'first-run-04-newchat-composer');
      }
    }
    await shot(page, 'first-run-02-landing');
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-first-run', results);
  return results;
}

const TOUR_ROUTES = [
  ['guid', '/guid'],
  ['work', '/work'],
  ['team-office', '/team/office'],
  ['team-roster', '/team/roster'],
  ['team-studio', '/team/studio'],
  ['projects-knowledge', '/projects/knowledge'],
  ['projects-map', '/projects/map'],
  ['projects-recipes', '/projects/recipes'],
  ['providers', '/providers'],
  ['autonomy', '/autonomy'],
  ['diagnostics', '/diagnostics'],
];

async function scenarioTour({ clickNav = true } = {}) {
  const results = { schema: 1, scenario: 'tour', pages: {}, navClicks: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(9000);
    results.onboardingAtBoot = await dismissOnboarding(page);
    await page.waitForTimeout(800);
    if (clickNav) {
      // Click every primary sider entry like a user would; record where it lands.
      for (const label of ['Work', 'Team', 'Projects', 'Providers', 'Autonomy', 'Diagnostics']) {
        const btn = page.locator(`button[aria-label="${label}"]`).first();
        const entry = { label, exists: await btn.count() };
        if (entry.exists) {
          const before = await hash(page);
          await btn.click({ timeout: 8000 }).catch((e) => (entry.error = String(e).slice(0, 160)));
          await page.waitForTimeout(1400);
          entry.before = before;
          entry.after = await hash(page);
        }
        results.navClicks.push(entry);
      }
      // New Chat from a non-guid page.
      const newChat = page.getByRole('button', { name: /New Chat/i }).first();
      if (await newChat.count()) {
        await newChat.click().catch(() => {});
        await page.waitForTimeout(1200);
        results.navClicks.push({ label: 'New Chat', after: await hash(page) });
      }
    }
    for (const [name, route] of TOUR_ROUTES) {
      const pageResult = {};
      try {
        await page.evaluate((r) => {
          location.hash = r;
        }, route);
        await page.waitForTimeout(2400);
        pageResult.finalHash = await hash(page);
        pageResult.headings = await probeHeadings(page);
        pageResult.text = await bodyText(page, 3000);
        pageResult.interactives = await probeInteractives(page);
        pageResult.tabs = await probeTabs(page);
        pageResult.scroll = await probeScroll(page);
        pageResult.terms = await probeTerms(page);
        await shot(page, `tour-${name}`);
      } catch (error) {
        pageResult.error = String(error).slice(0, 300);
      }
      results.pages[name] = pageResult;
    }
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-tour', results);
  return results;
}

const SETTINGS_ROUTES = [
  '/settings/appearance',
  '/settings/archived',
  '/settings/system',
  '/settings/webui',
  '/settings/pet',
  '/settings/about',
  '/settings/model',
  '/settings/agent',
  '/settings/skills',
  '/settings/tools',
  '/settings',
];

async function scenarioSettings() {
  const results = { schema: 1, scenario: 'settings', siderItems: [], pages: {}, errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(9000);
    results.onboardingAtBoot = await dismissOnboarding(page);
    await page.waitForTimeout(600);
    // Click the Settings gear the way a user does.
    const gear = page.getByRole('button', { name: /^Settings$/i }).first();
    results.gearExists = await gear.count();
    if (results.gearExists) {
      await gear.click().catch((e) => results.errors.push(`gear: ${String(e).slice(0, 160)}`));
      await page.waitForTimeout(1800);
    }
    results.hashAfterGear = await hash(page);
    results.siderItems = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-settings-id]')).map((el) => ({
        id: el.getAttribute('data-settings-id'),
        path: el.getAttribute('data-settings-path'),
        label: (el.innerText || '').replace(/\s+/g, ' ').trim(),
      }))
    );
    await shot(page, 'settings-00-sider');
    for (const route of SETTINGS_ROUTES) {
      const key = route.replace(/\//g, '_') || 'root';
      const entry = {};
      try {
        await page.evaluate((r) => {
          location.hash = r;
        }, route);
        await page.waitForTimeout(2200);
        entry.finalHash = await hash(page);
        entry.headings = await probeHeadings(page);
        entry.text = await bodyText(page, 2200);
        entry.interactives = await probeInteractives(page);
        entry.tabs = await probeTabs(page);
        entry.scroll = await probeScroll(page);
        await shot(page, `settings-${key}`);
      } catch (error) {
        entry.error = String(error).slice(0, 300);
      }
      results.pages[route] = entry;
    }
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-settings', results);
  return results;
}

async function scenarioPalette() {
  const results = { schema: 1, scenario: 'palette', steps: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  const state = () =>
    page.evaluate(() => ({
      open: Boolean(document.querySelector('#kel-palette-input')),
      label: (document.querySelector('label[for="kel-palette-input"]')?.textContent || '').trim(),
      options: Array.from(document.querySelectorAll('[role="option"]')).map((el) =>
        (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 100)
      ),
      active: (() => {
        const el = document.querySelector('[role="option"][aria-selected="true"]');
        return el ? (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 100) : null;
      })(),
      hash: location.hash,
      emptyText: (document.querySelector('#kel-palette-list')?.innerText || '').slice(0, 200),
    }));
  const push = async (name) => {
    const entry = { name, at: Date.now() };
    entry.state = await state();
    results.steps.push(entry);
  };
  try {
    await page.waitForTimeout(9000);
    await push('initial');
    await page.keyboard.press('Control+k');
    await page.waitForTimeout(1400);
    await push('ctrl-k-open');
    await shot(page, 'palette-01-open');
    await page.locator('#kel-palette-input').fill('knowledge');
    await page.waitForTimeout(700);
    await push('filter-knowledge');
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(300);
    await push('arrow-down');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1600);
    await push('enter-nav');
    await page.keyboard.press('/');
    await page.waitForTimeout(1000);
    await push('slash-open');
    await shot(page, 'palette-02-search');
    await page.locator('#kel-palette-input').fill('zzzz');
    await page.waitForTimeout(600);
    await push('no-match');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    await push('escape-close');
    // "/" inside the composer must not hijack typing.
    const composer = page.locator('textarea,[contenteditable="true"],[role="textbox"]').first();
    if (await composer.count()) {
      await composer.click().catch(() => {});
      await page.keyboard.type('/');
      await page.waitForTimeout(700);
      await push('slash-in-composer');
      await page.keyboard.press('Escape');
    }
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-palette', results);
  return results;
}

async function scenarioKeyboard() {
  const results = { schema: 1, scenario: 'keyboard', stops: [], workStops: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(9000);
    await page.evaluate(() => {
      const a = document.activeElement;
      if (a && a.blur) a.blur();
    });
    for (let i = 0; i < 24; i += 1) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(140);
      const focus = await probeFocusRing(page);
      results.stops.push(focus);
    }
    await shot(page, 'keyboard-01-tab-stops');
    // Enter on first stop (skip link) should move focus into main content.
    await page.evaluate(() => {
      const a = document.activeElement;
      if (a && a.blur) a.blur();
    });
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    results.afterSkipEnter = await page.evaluate(() => ({
      active: (document.activeElement && (document.activeElement.id || document.activeElement.tagName)) || null,
      hash: location.hash,
    }));
    await page.evaluate(() => {
      location.hash = '/work';
    });
    await page.waitForTimeout(2200);
    for (let i = 0; i < 16; i += 1) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(120);
      results.workStops.push(await probeFocusRing(page));
    }
    await shot(page, 'keyboard-02-work-tabs');
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-keyboard', results);
  return results;
}

async function scenarioReadability() {
  const results = { schema: 1, scenario: 'readability', pages: {}, errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(9000);
    for (const [name, route] of [
      ['guid', '/guid'],
      ['work', '/work'],
      ['projects-knowledge', '/projects/knowledge'],
      ['providers', '/providers'],
      ['settings-appearance', '/settings/appearance'],
    ]) {
      await page.evaluate((r) => {
        location.hash = r;
      }, route);
      await page.waitForTimeout(2200);
      results.pages[name] = await probeReadability(page);
    }
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-readability', results);
  return results;
}

async function scenarioCompose() {
  // Interactive: type a real message and send it. Requires a configured provider.
  const message = process.env.UX_MESSAGE || 'In one short sentence, explain what you can help me with.';
  const results = { schema: 1, scenario: 'compose', message, timeline: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(9000);
    await page.evaluate(() => {
      location.hash = '/guid';
    });
    await page.waitForTimeout(2000);
    results.composer = await probeComposer(page);
    const composer = page.locator('textarea,[contenteditable="true"],[role="textbox"]').first();
    await composer.click({ timeout: 15000 });
    await composer.type(message, { delay: 12 }).catch(async () => {
      await page.keyboard.type(message, { delay: 12 });
    });
    await page.waitForTimeout(600);
    await shot(page, 'compose-01-typed');
    results.typedText = await page.evaluate(() => {
      const el = document.activeElement;
      return el ? (el.value || el.innerText || '').slice(0, 200) : null;
    });
    const send = page.getByRole('button', { name: /Send|send/i }).first();
    if (await send.count()) {
      await send.click();
    } else {
      await page.keyboard.press('Enter');
    }
    const t0 = Date.now();
    let last = '';
    let stable = 0;
    const sendBaseline = await page.evaluate(() => (document.body.innerText || '').length);
    results.sendBaseline = sendBaseline;
    const MAX_MS = Number(process.env.UX_WAIT_MS || 300000);
    while (Date.now() - t0 < MAX_MS) {
      await page.waitForTimeout(4000);
      const snap = await page.evaluate(() => {
        const text = document.body.innerText || '';
        const activityRows = Array.from(
          document.querySelectorAll('[class*="tool"], [class*="activity"], [class*="progress"], [class*="step"]')
        )
          .map((el) => (el.innerText || '').replace(/\s+/g, ' ').trim())
          .filter((t) => /Kel work:|VIEW STEPS|WAITING|VERIFIED|UNCERTAIN|FAILED|CLOSED/i.test(t))
          .slice(0, 6);
        const approvalVisible = /Allow once|Allow for this project|\bDeny\b|needs access|Waiting on you|waiting on you|Approve\b/i.test(
          text
        );
        return {
          bodyLength: text.length,
          tail: text.slice(-700),
          busy: Boolean(
            document.querySelector('[class*="stop"], [class*="loading"], [class*="spinner"], [aria-busy="true"]')
          ),
          stopButtons: Array.from(document.querySelectorAll('button'))
            .map((b) => (b.innerText || '').trim())
            .filter((t) => /stop|cancel/i.test(t))
            .slice(0, 4),
          activityRows,
          approvalVisible,
        };
      });
      if (snap.tail !== last) {
        results.timeline.push({
          ms: Date.now() - t0,
          bodyLength: snap.bodyLength,
          tail: snap.tail,
          busy: snap.busy,
          stopButtons: snap.stopButtons,
          activityRows: snap.activityRows,
          approvalVisible: snap.approvalVisible,
        });
        last = snap.tail;
        stable = 0;
      } else {
        stable += 1;
      }
      if (snap.approvalVisible && !results.approvalDetected) {
        results.approvalDetected = true;
        await shot(page, 'compose-approval-visible');
      }
      if (snap.bodyLength > sendBaseline + 80 && stable >= 3) break;
    }
    // Engine-side truth (authoritative), read before the app closes the engine.
    try {
      const session = JSON.parse(
        fs.readFileSync(path.join(kelwork, 'desktop-session.json'), 'utf8').replace(/^\uFEFF/, '')
      );
      const base = session.url.replace(/\/$/, '');
      const api = async (route) => {
        const res = await fetch(base + route, { headers: { Authorization: 'Bearer ' + session.token } });
        return res.json();
      };
      const state = await api('/api/state');
      results.engine = {
        jobs: (state.jobs || []).map((job) => ({
          id: job.id,
          state: job.state,
          verdict: job.verdict,
          routeBlock: job.route_block || null,
        })),
      };
    } catch (error) {
      results.engineError = String(error).slice(0, 200);
    }
    results.finalHash = await hash(page);
    results.finalText = await bodyText(page, 3000);
    results.terms = await probeTerms(page);
    await shot(page, 'compose-03-final');
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
    await shot(page, 'compose-error').catch(() => {});
  }
  await closeApp(app, kelwork, results);
  save('ux-compose', results);
  return results;
}

async function scenarioVetting() {
  // Design Vetting Sessions, driven like a user: start from the composer, answer rapidly with no
  // assistant turn between answers, process, answer more, finish the spec, then use the panel.
  const results = { schema: 1, scenario: 'vetting', steps: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  const send = async (text, label) => {
    const composer = page.locator('[data-testid="guid-input"], [data-testid="sendbox-input"], textarea').first();
    await composer.click({ timeout: 15000 });
    await composer.fill('');
    await composer.type(text, { delay: 8 });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1600);
    const body = await page.evaluate(() => document.body.innerText || '');
    const step = { label, text, tail: body.slice(-500) };
    results.steps.push(step);
    return body;
  };
  const waitFor = async (needle, timeoutMs, label) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const body = await page.evaluate(() => document.body.innerText || '');
      if (body.includes(needle)) {
        results.steps.push({ label, found: needle, ms: Date.now() - start });
        return true;
      }
      await page.waitForTimeout(500);
    }
    results.steps.push({ label, found: needle, ms: -1, timedOut: true });
    return false;
  };
  try {
    await page.waitForTimeout(9000);
    results.onboardingAtBoot = await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2000);

    await send('start design vetting: Basketball matchup dashboard', 'start');
    results.batchShown = await waitFor('Design vetting', 25000, 'batch-1-visible');
    await shot(page, 'vetting-01-batch');

    const answers = ['1: C', '2: A', '3: B', '4: D', '5: B', '6: A', '7: A', '8: C', '9: D', '10: B'];
    for (const answer of answers) {
      const body = await send(answer, 'answer-' + answer);
      results.lastAnswerSawProgress = /Recorded: \d+ of \d+ recorded/.test(body);
    }
    results.allAnswersRecorded = await waitFor('Recorded: 10 of 12 recorded', 25000, 'all-answers-recorded');
    results.answerProgressCount = await page.evaluate(
      () => ((document.body.innerText || '').match(/Recorded: \d+ of \d+ recorded/g) || []).length
    );
    await shot(page, 'vetting-02-rapid-answers');

    await send('process answers', 'process');
    results.batch2Shown = await waitFor('Batch 2', 30000, 'batch-2-visible');
    await shot(page, 'vetting-03-batch-2');

    await send('19: B', 'answer-19');
    let body = await send('view decisions', 'view-decisions');
    results.decisionsSeen = body.includes('Decisions so far:');
    await send('show greyboxes 19', 'greyboxes');
    results.greyboxesSeen = await waitFor('greybox direction', 20000, 'greyboxes-generated');
    await shot(page, 'vetting-04-greyboxes');

    await send('finish spec now', 'finish');
    results.specSaved = await waitFor('Spec snapshot saved', 25000, 'spec-saved');
    await shot(page, 'vetting-05-spec-saved');

    // The panel mirrors the same state.
    const trigger = page.locator('text=Work & context').first();
    if (await trigger.count()) {
      await trigger.click();
      await page.waitForTimeout(1200);
      const vettingTab = page.locator('[role="tab"]:has-text("Vetting")').first();
      results.panelTab = await vettingTab.count();
      if (results.panelTab) {
        await vettingTab.click();
        await page.waitForTimeout(1500);
        const panelText = await page.evaluate(() => document.body.innerText || '');
        results.panelShowsTopic = panelText.includes('Basketball matchup dashboard');
        results.panelShowsProgress = /recorded/.test(panelText);
        results.panelShowsDecisions = panelText.includes('Decisions');
        await shot(page, 'vetting-06-panel');
        const preview = page.locator('button:has-text("Preview spec")').first();
        if (await preview.count()) {
          await preview.click();
          await page.waitForTimeout(2000);
          const afterPreview = await page.evaluate(() => document.body.innerText || '');
          results.panelSpecPreview = afterPreview.includes('Design specification');
          await shot(page, 'vetting-07-panel-spec');
        }
      }
    }
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot(page, 'vetting-error').catch(() => {});
  }
  await closeApp(app, kelwork, results);
  save('ux-vetting', results);
  return results;
}

async function scenarioVettingLive() {
  // Live vetting: the donor transcript streams, while the Vetting panel is Kel's own surface and
  // reads engine state directly. The transcript is re-read after a reload to prove durability.
  const results = { schema: 1, scenario: 'vetting-live', steps: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  const send = async (text, label) => {
    const composer = page.locator('[data-testid="guid-input"], [data-testid="sendbox-input"], textarea').first();
    await composer.click({ timeout: 15000 });
    await composer.fill('');
    await composer.type(text, { delay: 6 });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1400);
    const body = await page.evaluate(() => document.body.innerText || '');
    results.steps.push({ label, tail: body.slice(-400) });
    return body;
  };
  const panelText = () => page.evaluate(() => document.body.innerText || '');
  try {
    await page.waitForTimeout(9000);
    results.onboardingAtBoot = await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2000);

    await send('start design vetting: Matchup center', 'start');
    for (const answer of ['1: C', '2: A', '3: B', '4: D', '5: B', '6: A', '7: A', '8: C', '9: D', '10: B']) {
      await send(answer, 'answer-' + answer);
    }
    await send('process answers', 'process');
    await send('19: B', 'answer-19');
    await send('finish spec now', 'finish');

    const trigger = page.locator('text=Work & context').first();
    if (await trigger.count()) {
      await trigger.click();
      await page.waitForTimeout(1200);
      const vettingTab = page.locator('[role="tab"]:has-text("Vetting")').first();
      results.panelTab = await vettingTab.count();
      if (results.panelTab) {
        await vettingTab.click();
        await page.waitForTimeout(1800);
        const panel = await panelText();
        results.panelTopic = panel.includes('Matchup center');
        results.panelState = /FINISHED/i.test(panel);
        results.panelProgress = /recorded/i.test(panel);
        results.panelDecisions = panel.includes('Decisions');
        await shot(page, 'vetting-live-01-panel');
        const preview = page.locator('button:has-text("Preview spec")').first();
        if (await preview.count()) {
          await preview.click();
          await page.waitForTimeout(2500);
          const after = await panelText();
          results.panelSpec = after.includes('Design specification');
          await shot(page, 'vetting-live-02-spec');
        }
      }
    }
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(700);
    await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => {});
    await page.waitForTimeout(9000);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(3000);
    const body = await page.evaluate(() => document.body.innerText || '');
    results.transcriptRecordedLines = (body.match(/Recorded: \d+ of \d+ recorded/g) || []).length;
    results.transcriptBatchShown = body.includes('Design vetting');
    results.transcriptSpecSaved = body.includes('Spec snapshot saved');
    results.transcriptSynthesis = body.includes('Synthesis');
    await shot(page, 'vetting-live-03-transcript');
    const frameTexts = [];
    for (const frame of page.frames()) {
      try {
        const t = await frame.evaluate(() => (document.body ? document.body.innerText : ''));
        if (t && t.length > 30) frameTexts.push(t);
      } catch (e) { /* cross-frame reads can fail; skip */ }
    }
    const frameText = frameTexts.sort((a, b) => b.length - a.length)[0] || '';
    results.frameCount = page.frames().length;
    results.frameTextLength = frameText.length;
    results.frameHasRecorded = frameText.includes('Recorded:');
    results.frameHasBatch = frameText.includes('Design vetting');
    results.frameHasSpec = frameText.includes('Spec snapshot');
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot(page, 'vetting-live-error').catch(() => {});
  }
  await closeApp(app, kelwork, results);
  save('ux-vetting-live', results);
  return results;
}

async function scenarioPeek() {
  const results = { schema: 1, scenario: 'peek', probes: {}, errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(10000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(3000);
    results.probes = await page.evaluate(() => {
      const body = document.body.innerText || '';
      const containers = Array.from(document.querySelectorAll('main, section, div'))
        .map((el) => ({ cls: String(el.className || '').slice(0, 60), len: (el.innerText || '').length }))
        .filter((entry) => entry.len > 200)
        .sort((a, b) => b.len - a.len)
        .slice(0, 12);
      return {
        bodyLength: body.length,
        hasRecorded: body.includes('Recorded:'),
        hasDesignVetting: body.includes('Design vetting'),
        hasSpecSnapshot: body.includes('Spec snapshot'),
        hasSynthesis: body.includes('Synthesis'),
        markers: ['Recorded:', 'Design vetting', 'Spec snapshot', 'Synthesis', 'Matchup center']
          .filter((needle) => body.includes(needle)),
        containers
      };
    });
    await shot(page, 'peek-01-guid');
    const html = await page.content();
    results.htmlLength = html.length;
    results.htmlHasRecorded = html.includes('Recorded:');
    results.htmlHasVetting = html.includes('Design vetting');
    results.consoleErrors = consoleErrors.slice(0, 10);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-peek', results);
  return results;
}

async function scenarioPaneldump() {
  const results = { schema: 1, scenario: 'paneldump', apiResponses: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  page.on('response', async (response) => {
    if (response.url().includes('/api/vetting')) {
      try {
        results.apiResponses.push({ url: response.url(), body: (await response.text()).slice(0, 500) });
      } catch (e) { /* body may be unavailable */ }
    }
  });
  try {
    await page.waitForTimeout(10000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2500);
    const triggers = ['text=Work & context', '[title="Work & context"]', 'text=Work'];
    for (const selector of triggers) {
      const el = page.locator(selector).first();
      if (await el.count()) {
        try { await el.click({ timeout: 4000 }); results.trigger = selector; break; } catch (e) { /* try next */ }
      }
    }
    await page.waitForTimeout(2500);
    const tab = page.locator('[role="tab"]:has-text("Vetting")').first();
    results.tabCount = await tab.count();
    if (results.tabCount) {
      await tab.click().catch((e) => { results.tabClickError = String(e).slice(0, 120); });
      await page.waitForTimeout(2500);
    }
    results.dom = await page.evaluate(() => {
      const drawer = document.querySelector('.arco-drawer');
      const text = drawer ? drawer.innerText : '(no drawer)';
      return {
        drawerFound: !!drawer,
        drawerText: text.slice(0, 700),
        hasFinished: text.includes('FINISHED'),
        hasTopic: text.includes('Matchup'),
        hasRecorded: /recorded/.test(text),
        hasDecisions: text.includes('Decisions'),
        startForm: text.includes('Start vetting session')
      };
    });
    await shot(page, 'paneldump-01');
    results.consoleErrors = consoleErrors.slice(0, 10);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
    await shot(page, 'paneldump-error').catch(() => {});
  }
  await closeApp(app, kelwork, results);
  save('ux-paneldump', results);
  return results;
}

async function scenarioTranscription() {
  // Transcription, driven like a user: record with the microphone, upload files, organize, hand a
  // transcript to chat and to a Vetting Session, then restart and find everything still there.
  const results = { schema: 1, scenario: 'transcription', steps: [], errors: [] };
  let ctx = await launchApp();
  let app = ctx.app;
  let page = ctx.page;
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const boxValue = () => page.evaluate(() => (document.querySelector('textarea') || {}).value || '');
  const waitFor = async (fn, timeoutMs, label) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        const value = await fn();
        if (value) {
          results.steps.push({ label, ms: Date.now() - start });
          return value;
        }
      } catch (error) {
        /* retry */
      }
      await page.waitForTimeout(400);
    }
    results.steps.push({ label, ms: -1, timedOut: true });
    return null;
  };
  const wavFixture = () => {
    const rate = 24000;
    const samples = rate;
    const buffer = Buffer.alloc(44 + samples * 2);
    buffer.write('RIFF', 0);
    buffer.writeUInt32LE(36 + samples * 2, 4);
    buffer.write('WAVE', 8);
    buffer.write('fmt ', 12);
    buffer.writeUInt32LE(16, 16);
    buffer.writeUInt16LE(1, 20);
    buffer.writeUInt16LE(1, 22);
    buffer.writeUInt32LE(rate, 24);
    buffer.writeUInt32LE(rate * 2, 28);
    buffer.writeUInt16LE(2, 32);
    buffer.writeUInt16LE(16, 34);
    buffer.write('data', 36);
    buffer.writeUInt32LE(samples * 2, 40);
    for (let index = 0; index < samples; index += 1) {
      buffer.writeInt16LE(Math.round(Math.sin(index / 20) * 8000), 44 + index * 2);
    }
    return buffer;
  };
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2500);
    results.pageShown = await waitFor(() => page.locator('[data-testid="transcription-page"]').count(), 15000, 'page-visible');
    await shot(page, 'transcription-01-page');

    await page.locator('[data-testid="record-button"]').first().click();
    results.recording = await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 20000, 'recording-bar');
    await page.waitForTimeout(5200);
    await shot(page, 'transcription-02-recording');
    await page.locator('[data-testid="stop-button"]').first().click();
    results.firstRow = await waitFor(() => page.locator('[data-testid="transcript-row"]').count(), 30000, 'transcript-saved');
    results.firstText = ((await bodyText()).match(/This is a local practice transcript[^\n]{0,40}/) || [''])[0];
    await shot(page, 'transcription-03-saved');

    await page.locator('[data-testid="rename-button"]').first().click();
    await page.locator('[data-testid="transcript-rename"]').first().fill('Morning note');
    await page.keyboard.press('Enter');
    results.renamed = await waitFor(async () => (await bodyText()).includes('Morning note'), 8000, 'renamed');
    await page.locator('[data-testid="folder-name"]').first().fill('Interviews');
    await page.locator('[data-testid="folder-create"]').first().click();
    results.folder = await waitFor(async () => (await bodyText()).includes('Interviews'), 8000, 'folder-created');
    try {
      await page
        .locator('[data-testid="transcript-row"]')
        .first()
        .dragTo(page.locator('[data-folder-id]').first(), { timeout: 6000 });
      results.dragWorked = await waitFor(() => page.locator('[data-testid="folder-transcript"]').count(), 8000, 'dragged-into-folder');
    } catch (error) {
      results.dragWorked = false;
      results.dragError = String(error).slice(0, 140);
    }
    if (!results.dragWorked) {
      await page.locator('[data-testid="move-select"]').first().click().catch(() => {});
      await page.locator('.arco-select-option:has-text("Interviews")').first().click().catch(() => {});
      results.movedViaSelect = await waitFor(() => page.locator('[data-testid="folder-transcript"]').count(), 8000, 'moved-via-select');
    }

    await page.locator('[data-testid="upload-input"]').setInputFiles({ name: 'meeting.mp3', mimeType: 'audio/mpeg', buffer: wavFixture() });
    results.uploadRow = await waitFor(async () => (await page.locator('[data-testid="transcript-row"]').count()) >= 2, 30000, 'upload-transcribed');
    await shot(page, 'transcription-04-upload');
    await page.locator('[data-testid="upload-input"]').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('not audio') });
    results.invalidMessage = await waitFor(async () => /could not be read/.test(await bodyText()), 10000, 'invalid-copy');

    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);
    await page.locator('[data-testid="kel-mic-toggle"]').first().click();
    results.composerRecording = await waitFor(
      async () => (await page.locator('[data-testid="kel-mic"]').getAttribute('data-state')) === 'recording',
      20000,
      'composer-recording'
    );
    await page.waitForTimeout(4600);
    await page.locator('[data-testid="kel-mic-toggle"]').first().click();
    results.composerText = await waitFor(async () => {
      const value = (await boxValue()).trim();
      return value.length > 10 ? value.slice(0, 60) : null;
    }, 30000, 'composer-text');
    await page.locator('textarea').first().fill('');
    results.composerCleared = true;
    await shot(page, 'transcription-05-composer');

    await page.locator('textarea').first().fill('start design vetting: voice routing');
    await page.keyboard.press('Enter');
    // The chat transcript renders outside the audited document (same shell limit as the vetting
    // evidence), so the session is proven by the review step below, not by reading the chat body.
    await page.waitForTimeout(2500);
    results.sessionStarted = 'proven-by-review-below';
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2200);
    await page.locator('[data-testid="transcript-row"]').first().click();
    await page.waitForTimeout(600);
    await page.locator('[data-testid="use-vetting"]').first().click();
    results.reviewModal = await waitFor(async () => (await page.locator('.arco-modal').count()) > 0, 12000, 'review-open');
    await shot(page, 'transcription-06-review');
    const processButton = page.locator('[data-testid="review-process"]').first();
    if (await processButton.count()) {
      await processButton.click().catch(() => {});
    }
    results.reviewApplied = await waitFor(
      async () => /Applied to the vetting session|Added to the vetting session/.test(await bodyText()),
      15000,
      'review-applied'
    );
    results.sessionProvenByReview = Boolean(results.reviewModal && results.reviewApplied);

    await closeApp(app, ctx.kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2500);
    results.rowsAfterRestart = await waitFor(
      async () => (await page.locator('[data-testid="transcript-row"]').count()) >= 2,
      20000,
      'rows-after-restart'
    );
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
    await shot(page, 'transcription-07-restart');
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot(page, 'transcription-error').catch(() => {});
  }
  await closeApp(app, ctx.kelwork, results);
  save('ux-transcription', results);
  return results;
}

async function scenarioSider() {





  const results = { schema: 1, scenario: 'sider', probes: [], errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(12000);
    results.hash = await hash(page);
    results.siderText = await page.evaluate(() => {
      const el = document.querySelector('[class*="history"], [class*="sider"], [class*="Sider"]');
      return el ? el.innerText.slice(0, 1200) : null;
    });
    results.rows = await page.evaluate(() => {
      const nodes = Array.from(
        document.querySelectorAll('[class*="conversation"], [data-testid*="conversation"]')
      );
      return nodes.slice(0, 30).map((el) => ({
        cls: String(el.className).slice(0, 90),
        text: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70),
      }));
    });
    results.bodyText = await bodyText(page, 2000);
    await page.keyboard.press('Control+k');
    await page.waitForTimeout(1600);
    results.palette = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[role="option"]')).map((el) =>
        (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 90)
      )
    );
    await shot(page, 'sider-01-palette');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    await shot(page, 'sider-00-base');
    results.consoleErrors = consoleErrors.slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-sider', results);
  return results;
}

async function scenarioMaintext() {
  const results = { schema: 1, scenario: 'maintext', pages: {}, errors: [] };
  const { app, page, kelwork, consoleErrors } = await launchApp();
  try {
    await page.waitForTimeout(9000);
    results.onboardingAtBoot = await dismissOnboarding(page);
    const routes = (
      process.env.UX_ROUTES ||
      '/guid,/work,/providers,/autonomy,/diagnostics,/projects/knowledge,/projects/map,/projects/recipes,/team/office,/team/roster,/team/studio,/settings/appearance,/settings/system,/settings/webui,/settings/about,/settings/archived'
    ).split(',');
    for (const route of routes) {
      await page.evaluate((h) => {
        location.hash = h;
      }, route);
      await page.waitForTimeout(2600);
      const info = await page.evaluate(() => {
        const main = document.querySelector('#kel-shell-content') || document.body;
        return { hash: location.hash, mainText: (main.innerText || '').slice(0, 2600) };
      });
      results.pages[route] = info;
      await shot(page, 'maintext' + route.replace(/\//g, '_'));
    }
    results.consoleErrors = consoleErrors.slice(0, 8);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-maintext', results);
  return results;
}

(async () => {
  const run = {
    'first-run': scenarioFirstRun,
    tour: scenarioTour,
    settings: scenarioSettings,
    palette: scenarioPalette,
    keyboard: scenarioKeyboard,
    readability: scenarioReadability,
    compose: scenarioCompose,
    vetting: scenarioVetting,
    'vetting-live': scenarioVettingLive,
    peek: scenarioPeek,
    paneldump: scenarioPaneldump,
    transcription: scenarioTranscription,
    sider: scenarioSider,
    maintext: scenarioMaintext,
  };
  if (scenario === 'all') {
    await scenarioFirstRun();
    await scenarioTour();
    await scenarioSettings();
    await scenarioPalette();
    await scenarioKeyboard();
    await scenarioReadability();
  } else if (run[scenario]) {
    await run[scenario]();
  } else {
    console.error(`unknown scenario '${scenario}'`);
    process.exit(2);
  }
  process.exit(0);
})().catch((e) => {
  console.error('HARNESS ERROR', String(e));
  process.exit(1);
});
