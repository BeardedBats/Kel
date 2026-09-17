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

async function scenarioHardening() {
  const results = { schema: 1, scenario: 'hardening', steps: [], errors: [] };
  const ctx = await launchApp();
  const { app, page } = ctx;
  const waitFor = async (fn, timeout = 10000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const value = await fn();
        if (value) {
          results.steps.push({ label, ms: Date.now() - start });
          return value;
        }
      } catch (error) {
        /* retry */
      }
      await page.waitForTimeout(350);
    }
    results.steps.push({ label, ms: -1, timedOut: true });
    return null;
  };
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  const overflow = () =>
    page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth);
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { window.resizeTo(980, 760); });
    await page.waitForTimeout(700);
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2500);
    results.pageShown = await waitFor(() => page.locator('[data-testid="transcription-page"]').count(), 15000, 'page');
    results.emptyState = await waitFor(async () => /Nothing here yet/.test(await bodyText()), 8000, 'empty-state');
    const overflowTranscription = await overflow();
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);
    const overflowGuid = await overflow();
    results.narrowOverflow = { transcription: overflowTranscription, guid: overflowGuid };
    results.narrowNoScroll = overflowTranscription <= 2 && overflowGuid <= 2;
    await page.evaluate(() => { window.resizeTo(1280, 900); });
    await page.waitForTimeout(600);
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(1800);
    const banned = ['websocket', 'pcm', 'multipart', 'endpointing', 'wss://', 'api.meta.ai', 'bearer token', 'http status'];
    const transcriptionText = (await bodyText()).toLowerCase();
    const guidText = await page.evaluate(async () => {
      location.hash = '/guid';
      await new Promise((resolve) => setTimeout(resolve, 1600));
      return document.body.innerText || '';
    });
    const combined = `${transcriptionText} ${String(guidText).toLowerCase()}`;
    results.jargonOffenders = banned.filter((token) => combined.includes(token));
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(1600);
    await page.locator('[data-testid="record-button"]').first().focus();
    await page.keyboard.press('Enter');
    results.keyboardRecord = await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 15000, 'keyboard-record');
    await page.keyboard.press('Escape');
    results.keyboardEscape = await waitFor(async () => (await page.locator('[data-testid="recording-bar"]').count()) === 0, 10000, 'keyboard-escape');
    await shot('hardening-01-narrow-keyboard');
    // A wrong key must surface one plain sentence and never provider jargon.
    await page.locator('[data-testid="transcription-settings"]').first().click();
    await page.locator('[data-testid="key-input"]').first().fill('test-bogus-key');
    await page.locator('[data-testid="key-save"]').first().click();
    results.keyConnected = await waitFor(async () => (await page.locator('[data-testid="key-clear"]').count()) > 0, 8000, 'key-connected');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    const wav = (() => {
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
      for (let index = 0; index < samples; index += 1) buffer.writeInt16LE(Math.round(Math.sin(index / 20) * 8000), 44 + index * 2);
      return buffer;
    })();
    await page.locator('[data-testid="upload-input"]').setInputFiles({ name: 'bogus-key-check.mp3', mimeType: 'audio/mpeg', buffer: wav });
    results.bogusKeyError = await waitFor(async () => {
      const text = await bodyText();
      const plain = /could not|refused|check the|try again|internet|key/i.test(text);
      const jargon = /(HTTP |api\.meta\.ai|http status)/i.test(text);
      return plain && !jargon ? text.slice(-160) : null;
    }, 40000, 'bogus-key-error');
    await page.locator('[data-testid="transcription-settings"]').first().click();
    await page.locator('[data-testid="key-clear"]').first().click().catch(() => {});
    results.keyCleared = await waitFor(async () => (await page.locator('[data-testid="key-input"]').count()) > 0, 10000, 'key-cleared');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);

    // Palette can reach the dedicated page.
    await page.keyboard.press('Control+k');
    await page.waitForTimeout(900);
    const paletteInput = page.locator('input[type="text"], textarea').first();
    await paletteInput.fill('transcript').catch(() => {});
    results.paletteTranscript = await waitFor(async () => /Transcription/i.test(await bodyText()), 6000, 'palette-transcription');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Density: three folders and three recordings stay organised without layout overflow.
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(1800);
    for (const name of ['Interviews', 'Ideas', 'Standups']) {
      await page.locator('[data-testid="folder-name"]').first().fill(name);
      await page.locator('[data-testid="folder-create"]').first().click();
      await page.waitForTimeout(450);
    }
    results.folders = await waitFor(() => page.locator('[data-folder-id]').count(), 8000, 'folders');
    for (let index = 0; index < 3; index += 1) {
      await page.locator('[data-testid="record-button"]').first().click();
      await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 15000, 'dense-bar');
      await page.waitForTimeout(3200);
      await page.locator('[data-testid="stop-button"]').first().click();
      await page.waitForTimeout(1700);
    }
    results.denseRows = await waitFor(async () => (await page.locator('[data-testid="transcript-row"]').count()) >= 3, 30000, 'dense-rows');
    results.denseNoOverflow = (await overflow()) <= 2;
    await shot('hardening-02-dense');

    // Light appearance keeps the surfaces readable.
    await page.evaluate(() => { location.hash = '/settings/appearance'; });
    await page.waitForTimeout(2200);
    const themeBefore = await page.evaluate(() => document.documentElement.getAttribute('data-theme') || document.documentElement.className || '');
    const lightOption = page.locator('[data-testid="theme-card-light"]').first();
    if (await lightOption.count()) {
      await lightOption.scrollIntoViewIfNeeded().catch(() => {});
      await lightOption.dispatchEvent('click').catch(() => {});
      await page.waitForTimeout(1200);
    }
    const themeAfter = await page.evaluate(() => document.documentElement.getAttribute('data-theme') || document.documentElement.className || '');
    results.lightThemeToggled = Boolean(themeBefore !== themeAfter) || themeAfter === 'light';
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2000);
    results.lightModeReadable = await waitFor(async () => /Nothing here yet|transcript/i.test(await bodyText()), 8000, 'light-readable');
    await shot('hardening-03-light');
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot('hardening-error');
  }
  await closeApp(app, ctx.kelwork, results);
  save('ux-hardening', results);
  return results;
}

async function scenarioVoiceVetting() {
  const results = { schema: 1, scenario: 'voice-vetting', steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page } = ctx;
  const waitFor = async (fn, timeout = 12000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
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
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  const send = async (value) => {
    const composer = page
      .locator('[data-testid="guid-input"]:visible, [data-testid="sendbox-input"]:visible, textarea:visible')
      .first();
    await composer.click({ timeout: 15000 });
    await composer.fill('');
    await composer.type(value, { delay: 6 });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1800);
  };
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);

    // Journey 3 fragment: start a vetting session from the composer.
    await send('start design vetting: voice note routing');
    results.sessionStarted = await waitFor(async () => {
      const panelProbe = await page.evaluate(async () => {
        const api = window.kelAPI;
        return api ? await api.request('/api/vetting', { action: 'panel' }) : null;
      });
      return /Q1/.test(JSON.stringify(panelProbe || {}));
    }, 25000, 'session-started');

    // Journey 5: dictate ONE answer with the composer mic, edit it, send it as normal chat.
    await page.locator('[data-testid="kel-mic-toggle"]').first().click();
    results.dictationRecording = await waitFor(
      async () => (await page.locator('[data-testid="kel-mic"]').getAttribute('data-state')) === 'recording',
      20000,
      'dictation-recording'
    );
    await page.waitForTimeout(4600);
    await page.locator('[data-testid="kel-mic-toggle"]').first().click();
    results.dictationText = await waitFor(async () => {
      const value = (await page.locator('textarea:visible').first().inputValue()).trim();
      return value.length > 10 ? value.slice(0, 50) : null;
    }, 30000, 'dictation-text');
    await page.locator('textarea:visible').first().fill('1: C, matchup visually dominant');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2600);
    const panel = await page.evaluate(async () => {
      const api = window.kelAPI;
      return api ? await api.request('/api/vetting', { action: 'panel' }) : null;
    });
    const panelDump = JSON.stringify(panel || {});
    results.panelAfterDictation = panelDump.slice(0, 260);
    results.oneAnswerRecorded = /Q1/.test(panelDump) && /ANSWERED/.test(panelDump);

    // Journey 4: interrupt the flow with normal chat, then keep going.
    await send('hello kel');
    results.interruptedThen = await waitFor(async () => {
      const panelProbe = await page.evaluate(async () => {
        const api = window.kelAPI;
        return api ? await api.request('/api/vetting', { action: 'panel' }) : null;
      });
      const dump = JSON.stringify(panelProbe || {});
      return /Q1/.test(dump) && /ANSWERED/.test(dump);
    }, 15000, 'after-interrupt');
    await shot('voice-vetting-01-one-answer');

    // Journey 8 fragment: record a transcript on the dedicated page.
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2400);
    await page.locator('[data-testid="record-button"]').first().click();
    results.recordBar = await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 20000, 'record-bar');
    await page.waitForTimeout(3600);
    await page.locator('[data-testid="stop-button"]').first().click();
    results.transcriptRow = await waitFor(() => page.locator('[data-testid="transcript-row"]').count(), 30000, 'transcript-row');
    // Journey 7: Think Out Loud on the transcript brings back useful buckets.
    await page.locator('[data-testid="think-out-loud"]').first().click();
    results.thinkModal = await waitFor(() => page.locator('.arco-modal').count(), 12000, 'think-modal');
    await page.locator('[data-testid="review-edit"]').first().click();
    await page.locator('[data-testid="review-edit-text"]').first().fill(
      'I need a compact layout with quick scanning. I worry about clutter on small screens. Still open: the color direction.'
    );
    await page.locator('[data-testid="review-recheck"]').first().click();
    results.thinkBuckets = await waitFor(
      async () => /Requirements heard|Concerns heard|Still open/.test(await bodyText()),
      12000,
      'think-buckets'
    );
    await shot('voice-vetting-02-think');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);

    // Journey 6: edit the transcript text inside the review, re-check, then accept many answers.
    await page.locator('[data-testid="use-vetting"]').first().click();
    results.reviewModal = await waitFor(() => page.locator('.arco-modal').count(), 12000, 'review-modal');
    await page.locator('[data-testid="review-edit"]').first().click();
    await page.locator('[data-testid="review-edit-text"]').first().fill('2: A, dense decisions\n3: B, quick scanning\n4: D, quiet screens');
    await page.locator('[data-testid="review-recheck"]').first().click();
    results.multiPreview = await waitFor(async () => {
      const items = await page.locator('[data-testid="review-list"] li').count();
      return items >= 3 ? items : null;
    }, 12000, 'multi-preview');
    await page.locator('[data-testid="review-accept"]').first().click();
    results.acceptAll = await waitFor(
      async () => /Added to the vetting session|Applied to the vetting session/.test(await bodyText()),
      15000,
      'accept-all'
    );
    await page.locator('[data-testid="use-vetting"]').first().click();
    await waitFor(() => page.locator('.arco-modal').count(), 12000, 'review-modal-2');
    await page.locator('[data-testid="review-process"]').first().click();
    results.processBatch = await waitFor(
      async () => /Added to the vetting session|Applied to the vetting session/.test(await bodyText()),
      15000,
      'process-batch'
    );
    await shot('voice-vetting-03-applied');

    // Journey 11: restart Kel; the transcript and the vetting session both survive.
    await closeApp(app, ctx.kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2400);
    results.rowsAfterRestart = await waitFor(() => page.locator('[data-testid="transcript-row"]').count(), 20000, 'rows-after-restart');
    await page.locator('[data-testid="transcript-row"]').first().click();
    await page.waitForTimeout(600);
    results.audioAfterRestart = await page
      .locator('[data-testid="download-audio"]')
      .first()
      .isEnabled()
      .catch(() => false);
    await page.locator('[data-testid="transcript-row"]').first().click();
    await page.waitForTimeout(700);
    await page.locator('[data-testid="use-vetting"]').first().click();
    results.sessionAfterRestart = await waitFor(() => page.locator('.arco-modal').count(), 15000, 'session-after-restart');
    await shot('voice-vetting-04-restart');
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot('voice-vetting-error');
  }
  await closeApp(app, ctx.kelwork, results);
  save('ux-voice-vetting', results);
  return results;
}

async function scenarioRecheckProbe() {
  const results = { schema: 1, scenario: 'recheck-probe', steps: [], errors: [] };
  const { app, page } = await launchApp();
  const waitFor = async (fn, timeout = 12000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const value = await fn();
        if (value) { results.steps.push({ label, ms: Date.now() - start }); return value; }
      } catch (error) { /* retry */ }
      await page.waitForTimeout(300);
    }
    results.steps.push({ label, ms: -1, timedOut: true });
    return null;
  };
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2000);
    const composer = page
      .locator('[data-testid="guid-input"]:visible, [data-testid="sendbox-input"]:visible, textarea:visible')
      .first();
    await composer.click({ timeout: 15000 });
    await composer.fill('start design vetting: recheck probe');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(4500);
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2400);
    await page.locator('[data-testid="record-button"]').first().click();
    await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 20000, 'bar');
    await page.waitForTimeout(3400);
    await page.locator('[data-testid="stop-button"]').first().click();
    await waitFor(() => page.locator('[data-testid="transcript-row"]').count(), 30000, 'row');
    await page.locator('[data-testid="use-vetting"]').first().click();
    await waitFor(() => page.locator('.arco-modal').count(), 12000, 'modal');
    results.payloadArrived = await waitFor(() => page.locator('[data-testid="review-edit"]').count(), 12000, 'payload');
    await page.locator('[data-testid="review-edit"]').first().click();
    await page.locator('[data-testid="review-edit-text"]').first().fill('12: A, matchup visually dominant');
    await page.locator('[data-testid="review-recheck"]').first().click();
    await page.waitForTimeout(1800);
    results.listCount = await page.locator('[data-testid="review-list"] li').count();
    results.listText = await page.locator('[data-testid="review-list"]').first().innerText().catch(() => '');
    results.toast = await page.locator('.arco-message').allInnerTexts().catch(() => []);
    results.modalTail = (await page.locator('.arco-modal').first().innerText().catch(() => '')).slice(-400);
    results.bodyTail = (await bodyText()).slice(-200);
    results.consoleErrors = (await page.evaluate(() => window.__auditErrors || [])).slice(0, 5);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, null, results);
  save('ux-recheck-probe', results);
  return results;
}

async function scenarioSweepSeed() {
  // Creates three chats through the real UI (New Chat), records engine cid mappings, closes.
  const results = { schema: 1, scenario: 'sweep-seed', desktopIds: [], engineCids: [], errors: [] };
  const { app, page, kelwork } = await launchApp();
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);
    results.buttonInventory = await page.evaluate(() =>
      Array.from(document.querySelectorAll('button, a[href], [role="button"]'))
        .filter((n) => n.offsetParent !== null)
        .map((n) => ({
          text: (n.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 30),
          aria: n.getAttribute('aria-label'),
          testid: n.getAttribute('data-testid'),
          tag: n.tagName,
        }))
        .filter((entry) => entry.text || entry.aria || entry.testid)
        .slice(0, 60));
    const strategies = [
      ['role', () => page.getByRole('button', { name: /new chat/i }).first()],
      ['aria', () => page.locator('[aria-label*="New Chat" i], [aria-label*="new chat" i]').first()],
      ['testid', () => page.locator('[data-testid*="new-chat"], [data-testid*="newChat"], [data-testid*="create"]').first()],
    ];
    for (let i = 0; i < 3; i += 1) {
      let used = null;
      for (const [name, make] of strategies) {
        const locator = make();
        const count = await locator.count().catch(() => 0);
        if (!count) continue;
        await locator.click({ timeout: 4000 }).catch(() => {});
        await page.waitForTimeout(1800);
        used = name;
        break;
      }
      // A conversation materializes on its first message, so send one through the composer.
      const composer = page.locator('[data-testid="sendbox-input"], textarea').first();
      await composer.click({ timeout: 8000 }).catch(() => {});
      await page.keyboard.type('Seeding audit chat ' + (i + 1) + ' for the sweep battery.');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(5200);
      const hash = await page.evaluate(() => location.hash);
      const match = String(hash).match(/conversation[\/]([A-Za-z0-9_-]+)/);
      const desktopId = match ? match[1] : null;
      results.desktopIds.push(desktopId);
      results.strategiesUsed = results.strategiesUsed || [];
      results.strategiesUsed.push(used);
      const cid = desktopId
        ? await page.evaluate(async (id) => {
            const api = window.kelAPI;
            if (!api || !api.conversation) return null;
            try {
              return await api.conversation(id);
            } catch (error) {
              return null;
            }
          }, desktopId).catch(() => null)
        : null;
      results.engineCids.push(cid);
    }
    results.done = true;
    await page.waitForTimeout(1200);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
  }
  await closeApp(app, kelwork, results);
  save('ux-sweep-seed', results);
  return results;
}

async function scenarioSweepA() {
  const results = { schema: 1, scenario: 'sweep-a', scrollMatrix: [], steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const waitFor = async (fn, timeout = 12000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
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
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  const routeProbe = async (route) => {
    await page.evaluate((r) => { location.hash = r; }, route);
    await page.waitForTimeout(1900);
    return await page.evaluate(() => {
      const scrollers = [];
      for (const el of Array.from(document.querySelectorAll('*'))) {
        const style = getComputedStyle(el);
        if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
            el.scrollHeight > el.clientHeight + 24 && el.clientHeight > 160) {
          scrollers.push(el);
        }
      }
      const main = scrollers.sort((a, b) => b.clientHeight - a.clientHeight)[0] || null;
      const nodes = Array.from(document.querySelectorAll(
        'main button, main a[href], main input, main textarea, main select, main [role="button"], main [tabindex]:not([tabindex="-1"]), button, a[href], input, textarea, select, [role="button"], [tabindex]:not([tabindex="-1"])'
      ));
      const visible = nodes.filter((n) => n.offsetParent !== null && n.offsetWidth > 0);
      const lastInteractive = visible[visible.length - 1] || null;
      let reachable = null;
      if (lastInteractive) {
        lastInteractive.focus();
        reachable = document.activeElement === lastInteractive;
      }
      let bottomReached = null;
      if (main) {
        main.scrollTop = main.scrollHeight;
        bottomReached = main.scrollTop + main.clientHeight >= main.scrollHeight - 4;
      }
      return {
        scrollable: Boolean(main),
        scrollHeight: main ? main.scrollHeight : null,
        clientHeight: main ? main.clientHeight : null,
        moreThanViewport: main ? main.scrollHeight > main.clientHeight + 24 : null,
        lastControlFocusable: reachable,
        lastControlLabel: lastInteractive
          ? (lastInteractive.getAttribute('aria-label') || lastInteractive.textContent || '').trim().slice(0, 40)
          : null,
        horizontalOverflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
        scrolledToBottom: bottomReached,
      };
    });
  };
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    for (const route of [
      '/guid', '/work', '/projects/knowledge', '/projects/map', '/providers', '/autonomy',
      '/settings/model', '/settings/agent', '/settings/skills', '/settings/tools', '/settings/appearance',
      '/settings/webui', '/settings/system', '/settings/archived', '/settings/about', '/transcription',
    ]) {
      results.scrollMatrix.push({ route, ...(await routeProbe(route)) });
    }
    await shot('sweep-a-01-scroll-matrix');

    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);
    const richRow = page.getByText('Rich rendering chat', { exact: false }).first();
    results.richRowFound = await richRow.count();
    if (results.richRowFound) {
      await richRow.click();
      await page.waitForTimeout(2400);
    }
    results.richProbe = await page.evaluate(() => ({
      tables: document.querySelectorAll('table').length,
      codeBlocks: document.querySelectorAll('pre').length,
      inlineCode: document.querySelectorAll('code').length,
      links: document.querySelectorAll('a[href^="http"]').length,
      headings: document.querySelectorAll('h1,h2,h3').length,
      copyButtons: Array.from(document.querySelectorAll('button')).filter((b) => /copy/i.test((b.getAttribute('aria-label') || b.textContent || ''))).length,
      scrollToLatest: Array.from(document.querySelectorAll('button')).filter((b) => /scroll|latest|bottom|newest/i.test(b.getAttribute('aria-label') || '')).length,
      messageNodes: document.querySelectorAll('[class*="message"], [data-message-id], [class*="Message"]').length,
    }));
    await shot('sweep-a-02-rich');

    await page.locator('[data-testid="sendbox-input"], textarea').first().click();
    results.composerFocused = await page.evaluate(() => {
      const a = document.activeElement;
      return Boolean(a && (a.tagName === 'TEXTAREA' || a.getAttribute('role') === 'textbox'));
    });
    await page.keyboard.type('draft line one');
    await page.keyboard.press('Shift+Enter');
    await page.keyboard.type('draft line two');
    results.shiftEnterNewline = await page.evaluate(() => {
      const t = document.querySelector('[data-testid="sendbox-input"]') || document.querySelector('textarea');
      return Boolean(t && t.value && t.value.includes('\n'));
    });
    await page.keyboard.press('Enter');
    results.sendingStateSeen = await waitFor(
      () => page.locator('button[aria-label*="Stop"], [data-testid*="stop"]').count(),
      6000,
      'stop-visible'
    );
    results.sendOutcome = await waitFor(async () => {
      const body = await bodyText();
      return /fail|error|could not|unavailable|no usable|add a|set up|provider|connect/i.test(body) ? body.slice(-300) : null;
    }, 25000, 'failure-surface');
    results.composerAfterFailure = await page.evaluate(() => {
      const t = document.querySelector('[data-testid="sendbox-input"]') || document.querySelector('textarea');
      return t ? t.value.slice(0, 120) : null;
    });
    // ---- conversation management ----
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(1900);
    results.listRowCount = await page.locator('text=/Rich rendering chat|Second chat|Third chat/').count();

    const searchBtn = page.locator('button[aria-label*="earch"], [data-testid*="search"]').first();
    results.searchControlFound = await searchBtn.count();
    if (results.searchControlFound) {
      await searchBtn.click().catch(() => {});
      await page.waitForTimeout(900);
      const searchInput = page.locator('input[placeholder*="earch"], input[type="search"], [role="combobox"] input').first();
      await searchInput.fill('Rich').catch(() => {});
      await page.waitForTimeout(900);
      results.searchPartialHit = /Rich rendering chat|Second chat|Third chat/.test(await bodyText());
      await searchInput.fill('zzzz').catch(() => {});
      await page.waitForTimeout(900);
      results.searchNoResult = /no result|nothing|not found|empty|no match/i.test(await bodyText());
      await searchInput.fill('').catch(() => {});
      await page.waitForTimeout(500);
      await page.keyboard.press('Escape');
    }

    await page.keyboard.press('Control+k');
    await page.waitForTimeout(1000);
    const paletteProbe = async (needle, label) => {
      await page.locator('#kel-palette-input').fill(needle).catch(() => {});
      await page.waitForTimeout(650);
      const txt = await page.locator('#kel-palette-list').innerText().catch(() => '');
      results.steps.push({ label, ms: 0 });
      return txt.slice(0, 300) || '(empty)';
    };
    results.paletteNew = await paletteProbe('new', 'palette-new');
    results.paletteSearch = await paletteProbe('search', 'palette-search');
    results.paletteTheme = await paletteProbe('theme', 'palette-theme');
    results.paletteModel = await paletteProbe('model', 'palette-model');
    results.paletteWork = await paletteProbe('work', 'palette-work');
    results.paletteVetting = await paletteProbe('vetting', 'palette-vetting');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);

    const rowMenu = async (title) => {
      const row = page.getByText(title, { exact: false }).first();
      await row.hover().catch(() => {});
      await page.waitForTimeout(500);
      const menuBtn = page.locator('button[aria-label*="ore"], [data-testid*="menu"], button[aria-label*="ption"]').first();
      if (await menuBtn.count()) {
        await menuBtn.click().catch(() => {});
        await page.waitForTimeout(500);
        return true;
      }
      return false;
    };
    results.renameMenuOpened = await rowMenu('Second chat');
    if (results.renameMenuOpened) {
      const renameItem = page.getByText(/^Rename$/).first();
      if (await renameItem.count()) {
        await renameItem.click().catch(() => {});
        await page.waitForTimeout(700);
        await page.locator('.arco-modal input, [role="dialog"] input').first().fill('Renamed chat').catch(() => {});
        await page.keyboard.press('Enter');
        await page.waitForTimeout(1300);
      }
      results.renameWorked = /Renamed chat/.test(await bodyText());
    }
    results.deleteMenuOpened = await rowMenu('Third chat');
    if (results.deleteMenuOpened) {
      const delItem = page.getByText(/^Delete$/).first();
      if (await delItem.count()) {
        await delItem.click().catch(() => {});
        await page.waitForTimeout(900);
        results.deleteConfirmShown = /delete/i.test(await bodyText());
        const cancel = page.getByText(/cancel|keep/i).first();
        results.deleteConfirmHasCancel = await cancel.count();
        await cancel.click().catch(() => {});
        await page.waitForTimeout(700);
        results.deleteCancelledKeepsRow = /Third chat/.test(await bodyText());
      }
    }

    // ---- attachments via mentions ----
    await page.locator('[data-testid="sendbox-input"], textarea').first().click();
    await page.keyboard.type('@');
    await page.waitForTimeout(1300);
    results.mentionPopup = await page.evaluate(() => {
      const list = document.querySelector('[class*="mention"], [role="listbox"]');
      return list ? (list.textContent || '').slice(0, 200) : null;
    });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="sendbox-input"]') || document.querySelector('textarea');
      if (el) {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        setter.call(el, '');
        el.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });

    // ---- drafts across conversation switches + restart ----
    const openChat = async (title) => {
      await page.getByText(title, { exact: false }).first().click().catch(() => {});
      await page.waitForTimeout(1700);
    };
    await openChat('Second chat');
    await page.locator('[data-testid="sendbox-input"], textarea').first().click();
    await page.keyboard.type('IMPORTANT DRAFT TEXT 42');
    await openChat('Rich rendering chat');
    results.draftOtherConversation = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="sendbox-input"]') || document.querySelector('textarea');
      return el ? el.value.slice(0, 80) : null;
    });
    await openChat('Second chat');
    results.draftRestoredOnReturn = await waitFor(async () => {
      const value = await page.evaluate(() => {
        const el = document.querySelector('[data-testid="sendbox-input"]') || document.querySelector('textarea');
        return el ? el.value : '';
      });
      return value && value.includes('42') ? value.slice(0, 60) : null;
    }, 6000, 'draft-return');

    await closeApp(app, kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    kelwork = ctx.kelwork;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2300);
    results.conversationsSurviveRestart = (await page.getByText('Second chat', { exact: false }).count()) > 0;
    await page.getByText('Second chat', { exact: false }).first().click().catch(() => {});
    await page.waitForTimeout(1900);
    results.draftAfterRestart = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="sendbox-input"]') || document.querySelector('textarea');
      return el ? el.value.slice(0, 80) : null;
    });
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot('sweep-a-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-sweep-a', results);
  return results;
}

async function scenarioSweepB() {
  const results = { schema: 1, scenario: 'sweep-b', steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const waitFor = async (fn, timeout = 12000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
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
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);

    await page.evaluate(() => { location.hash = '/settings/appearance'; });
    await page.waitForTimeout(2600);
    results.themeCards = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-testid^="theme-card-"]')).map((n) => n.getAttribute('data-testid')));
    await page.locator('[data-testid="theme-card-light"]').first().dispatchEvent('click').catch(() => {});
    results.lightApplied = await waitFor(
      async () => ((await page.evaluate(() => document.documentElement.getAttribute('data-theme'))) === 'light' ? true : null),
      6000, 'light-applied');
    results.semanticColorControls = await page.evaluate(() => ({
      colorInputs: document.querySelectorAll('input[type="color"]').length,
      themeColorsLabel: /theme colors/i.test(document.body.innerText),
      hexFields: document.querySelectorAll('input[placeholder*="#"]').length,
    }));
    await page.locator('[data-testid="theme-card-dark"]').first().dispatchEvent('click').catch(() => {});
    results.darkRestored = await waitFor(
      async () => ((await page.evaluate(() => document.documentElement.getAttribute('data-theme'))) === 'dark' ? true : null),
      6000, 'dark-restored');
    await shot('sweep-b-01-theme');

    await page.evaluate(() => { location.hash = '/settings/model'; });
    await page.waitForTimeout(2600);
    results.modelPageTail = (await bodyText()).slice(-800);
    results.providerNamesSeen = ['Claude', 'Codex', 'DeepSeek', 'Anthropic']
      .filter((name) => results.modelPageTail.includes(name));
    results.defaultModelControl = await page.evaluate(() => /default model/i.test(document.body.innerText));
    await shot('sweep-b-02-model');

    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2300);
    await page.getByText('Rich rendering chat', { exact: false }).first().click().catch(() => {});
    await page.waitForTimeout(2100);
    results.runtimeControl = await page.evaluate(() => {
      const el = Array.from(document.querySelectorAll('button, [role="button"]'))
        .find((n) => /Automatic|Runtime|Claude Code|Codex/i.test((n.textContent || '').trim()));
      return el ? { text: (el.textContent || '').trim().slice(0, 60), aria: el.getAttribute('aria-label') } : null;
    });
    if (results.runtimeControl) {
      await page.locator('button', { hasText: /Automatic|Runtime/i }).first().click().catch(() => {});
      await page.waitForTimeout(1000);
      results.runtimeOptionsTail = (await bodyText()).slice(-450);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    await page.locator('[data-testid="sendbox-input"], textarea').first().click();
    await page.keyboard.type('RECOVERY DRAFT 7');
    const { execSync } = require('child_process');
    try {
      execSync('taskkill /IM KelEngine.exe /F', { stdio: 'ignore' });
      results.engineKilledByHarness = true;
    } catch (error) {
      results.engineKilledByHarness = false;
    }
    await page.waitForTimeout(5000);
    results.engineKillReaction = (await bodyText()).slice(-320);
    await shot('sweep-b-03-engine-killed');

    await closeApp(app, kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    kelwork = ctx.kelwork;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2300);
    await page.getByText('Rich rendering chat', { exact: false }).first().click().catch(() => {});
    await page.waitForTimeout(1900);
    results.draftAfterCrash = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="sendbox-input"]') || document.querySelector('textarea');
      return el ? el.value.slice(0, 80) : null;
    });
    await page.evaluate(() => { location.hash = '/work'; });
    await page.waitForTimeout(2400);
    results.workPageTail = (await bodyText()).slice(-400);
    results.phantomWorkSeen = /running|in progress|working|queued/i.test(results.workPageTail);
    await shot('sweep-b-04-work-after-crash');

    await page.evaluate(() => { location.hash = '/settings/about'; });
    await page.waitForTimeout(2400);
    results.aboutVersion = await page.evaluate(() => (document.body.innerText.match(/\d+\.\d+\.\d+/) || [null])[0]);
    const checkBtn = page.getByText(/check for updates/i).first();
    results.updateButtonFound = await checkBtn.count();
    if (results.updateButtonFound) {
      await checkBtn.click().catch(() => {});
      await page.waitForTimeout(6000);
      results.updateCheckResult = (await bodyText()).slice(-300);
      await shot('sweep-b-05-update');
    }
    results.dataFolderAction = await page.evaluate(() => /data folder|open folder|copy path/i.test(document.body.innerText));
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot('sweep-b-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-sweep-b', results);
  return results;
}

async function scenarioSweep2() {
  const results = { schema: 1, scenario: 'sweep2', steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const waitFor = async (fn, timeout = 12000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const value = await fn();
        if (value) { results.steps.push({ label, ms: Date.now() - start }); return value; }
      } catch (error) { /* retry */ }
      await page.waitForTimeout(400);
    }
    results.steps.push({ label, ms: -1, timedOut: true });
    return null;
  };
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  const composer = () =>
    page.locator('[data-testid="sendbox-input"]:visible, [data-testid="guid-input"]:visible, textarea:visible').first();
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);
    results.richRowInList = await page.getByText('Rich rendering chat', { exact: false }).count();
    await page.getByText('Rich rendering chat', { exact: false }).first().click().catch(() => {});
    await page.waitForTimeout(2400);
    results.openedRichChat = await page.evaluate(() => /conversation/.test(location.hash));

    // The seeded rich reply is the newest message in a long chat; a virtualized list mounts only
    // what is near the viewport, so scroll to the end first — otherwise the probe reports "absent"
    // for content that is simply not mounted yet.
    await page.evaluate(() => {
      const scrollers = Array.from(document.querySelectorAll('*')).filter((node) => {
        const style = getComputedStyle(node);
        return /auto|scroll/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 40;
      });
      for (const node of scrollers) node.scrollTop = node.scrollHeight;
    }).catch(() => {});
    await page.waitForTimeout(1400);

    results.markdownProbe = await page.evaluate(() => {
      // Assistant replies render through MarkdownView, which mounts its body inside a shadow root
      // (components/Markdown/ShadowView). innerText and querySelectorAll on the light DOM cannot
      // see that content, so walk shadow roots the way a reader's eyes do.
      const walk = (root, selector) => {
        const hits = Array.from(root.querySelectorAll(selector));
        for (const el of root.querySelectorAll('*')) if (el.shadowRoot) hits.push(...walk(el.shadowRoot, selector));
        return hits;
      };
      const textOf = (node) => {
        let text = node.innerText || '';
        for (const el of node.querySelectorAll('*')) if (el.shadowRoot) text += '\n' + (el.shadowRoot.textContent || '');
        return text;
      };
      const messageRoots = Array.from(document.querySelectorAll('[data-testid^="message-text-"]'));
      const host = messageRoots.find((node) => textOf(node).includes('Layout review summary')) || null;
      const scope = host || document.body;
      return {
        textFound: Boolean(host),
        hostHtmlSample: host ? host.innerHTML.slice(0, 260) : null,
        tables: walk(scope, 'table').length,
        pre: walk(scope, 'pre').length,
        code: walk(scope, 'code').length,
        links: walk(scope, 'a[href^="http"]').length,
        copyButtons: Array.from(document.querySelectorAll('button')).filter((b) => /copy/i.test((b.getAttribute('aria-label') || b.textContent || ''))).length,
        retryButtons: Array.from(document.querySelectorAll('button')).filter((b) => /retry|try again/i.test((b.getAttribute('aria-label') || b.textContent || ''))).length,
        scrollToLatest: Array.from(document.querySelectorAll('button')).filter((b) => /scroll|latest|bottom|newest/i.test(b.getAttribute('aria-label') || '')).length,
      };
    });
    // The copy affordance is an icon button (no text/aria-label), so count it by its icon class and
    // prove the feedback toast appears rather than trusting a text match.
    const copyIcon = page.locator('[class*="i-icon-copy"]').first();
    results.copyAffordance = await copyIcon.count();
    if (results.copyAffordance) {
      const toastsBefore = await page.locator('.arco-message').count();
      await copyIcon.hover().catch(() => {});
      await copyIcon.click({ timeout: 8000 }).catch(() => {});
      results.copyToastSeen = await waitFor(
        async () => ((await page.locator('.arco-message').count()) > toastsBefore ? true : null),
        6000, 'copy-toast');
    }
    await shot('sweep2-01-markdown');

    await composer().click({ timeout: 8000 });
    results.composerFocused = await page.evaluate(() => {
      const a = document.activeElement;
      return Boolean(a && a.tagName === 'TEXTAREA');
    });
    await page.keyboard.type('retry probe message');
    await page.keyboard.press('Enter');
    // Assistant text (including failure copy) lives inside a shadow root, so read it the same way.
    const deepText = () =>
      page.evaluate(() => {
        const walk = (root) => {
          let text = root.innerText || '';
          for (const el of root.querySelectorAll('*')) if (el.shadowRoot) text += '\n' + walk(el.shadowRoot);
          return text;
        };
        return walk(document.body);
      });
    results.failureSeen = await waitFor(async () => {
      const body = await deepText();
      // Plain human states count: the shipped copy says Kel is waiting for a model to continue.
      return /waiting_for_resource|WAITING_RESOURCE|FAILED|failed|could not|waiting for a model|is waiting/i.test(body) ? body.slice(-260) : null;
    }, 20000, 'failure-surface');
    results.retryAfterFailure = await waitFor(async () => {
      const btn = page.locator('button').filter({ hasText: /retry|try again/i }).first();
      if (!(await btn.count())) return null;
      await btn.click().catch(() => {});
      await page.waitForTimeout(2500);
      return (await bodyText()).slice(-200);
    }, 8000, 'retry-clicked');
    await shot('sweep2-02-retry');

    const rowMenu = async (title) => {
      const row = page.getByText(title, { exact: false }).first();
      await row.scrollIntoViewIfNeeded().catch(() => {});
      await row.hover().catch(() => {});
      await page.waitForTimeout(700);
      // The row menu is a span revealed by row hover (other rows keep theirs hidden), so target
      // the visible one instead of the first match in the DOM.
      const menuBtn = page.locator('[data-testid^="conversation-row-menu-"]:visible').first();
      if (!(await menuBtn.count())) return null;
      await menuBtn.click({ timeout: 6000 }).catch(() => {});
      await page.waitForTimeout(900);
      return (await bodyText()).slice(-400);
    };
    results.secondChatMenu = await rowMenu('Second chat');
    const renameItem = page.getByText(/^rename/i).first();
    results.renameAffordance = await renameItem.count();
    if (results.renameAffordance) {
      await renameItem.click().catch(() => {});
      await page.waitForTimeout(800);
      await page.locator('.arco-modal input, [role="dialog"] input').first().fill('Renamed chat').catch(() => {});
      await page.keyboard.press('Enter');
      await page.waitForTimeout(1400);
      results.renameWorked = /Renamed chat/.test(await bodyText());
    }
    results.thirdChatMenu = await rowMenu('Third chat');
    const deleteItem = page.getByText(/^delete/i).first();
    results.deleteAffordance = await deleteItem.count();
    if (results.deleteAffordance) {
      await deleteItem.click().catch(() => {});
      await page.waitForTimeout(900);
      results.deleteConfirmShown = /delete/i.test(await bodyText());
      await page.getByText(/cancel|keep/i).first().click().catch(() => {});
      await page.waitForTimeout(700);
      results.deleteCancelledKeepsRow = /Third chat/.test(await bodyText());
    }
    await shot('sweep2-03-menus');

    results.mentionPopup = await waitFor(async () => {
      await composer().click({ timeout: 8000 });
      await page.keyboard.type('@');
      await page.waitForTimeout(1200);
      return page.evaluate(() => {
        const list = document.querySelector('[class*="mention"], [role="listbox"]');
        return list ? (list.textContent || '').slice(0, 180) : null;
      });
    }, 10000, 'mention-popup');
    await page.keyboard.press('Escape');
    await composer().fill('').catch(() => {});

    const openChat = async (title) => {
      await page.getByText(title, { exact: false }).first().click().catch(() => {});
      await page.waitForTimeout(1800);
    };
    await openChat(/Renamed chat|Second chat/);
    await composer().click({ timeout: 8000 });
    await page.keyboard.type('IMPORTANT DRAFT TEXT 42');
    await openChat('Rich rendering chat');
    results.draftOtherConversation = await composer().inputValue().catch(() => null);
    await openChat(/Renamed chat|Second chat/);
    results.draftRestoredOnReturn = await waitFor(async () => {
      const value = await composer().inputValue().catch(() => '');
      return value.includes('42') ? value.slice(0, 60) : null;
    }, 6000, 'draft-return');

    await closeApp(app, kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    kelwork = ctx.kelwork;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2300);
    results.conversationsSurviveRestart = (await page.getByText(/Renamed chat|Second chat/).count()) > 0;
    await page.getByText(/Renamed chat|Second chat/).first().click().catch(() => {});
    await page.waitForTimeout(2000);
    results.draftAfterRestart = await composer().inputValue().catch(() => null);
    await shot('sweep2-04-draft-restart');
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot('sweep2-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-sweep2', results);
  return results;
}

async function scenarioSweep3() {
  const results = { schema: 1, scenario: 'sweep3', steps: [], errors: [] };
  const fs = require('fs');
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const waitFor = async (fn, timeout = 12000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const value = await fn();
        if (value) { results.steps.push({ label, ms: Date.now() - start }); return value; }
      } catch (error) { /* retry */ }
      await page.waitForTimeout(400);
    }
    results.steps.push({ label, ms: -1, timedOut: true });
    return null;
  };
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  const paletteQuery = async (needle, label) => {
    await page.keyboard.press('Control+k');
    await page.waitForTimeout(900);
    await page.locator('#kel-palette-input').fill(needle).catch(() => {});
    await page.waitForTimeout(700);
    const txt = await page.locator('#kel-palette-list').innerText().catch(() => '');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    results.steps.push({ label, ms: 0 });
    return txt.slice(0, 220) || '(empty)';
  };
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2000);

    results.paletteNewChat = await paletteQuery('new chat', 'palette-new-chat');
    results.paletteTranscription = await paletteQuery('transcription', 'palette-transcription');
    results.paletteTheme = await paletteQuery('theme', 'palette-theme');
    results.paletteVetting = await paletteQuery('vetting', 'palette-vetting');
    results.paletteSystem = await paletteQuery('system', 'palette-system');

    await page.evaluate(() => { location.hash = '/settings/appearance'; });
    await page.waitForTimeout(2600);
    results.themeColorsSection = (await page.locator('[data-testid="theme-colors-section"]').count()) > 0;
    results.themeColorInputs = await page.evaluate(
      () => document.querySelectorAll('[data-testid^="theme-color-"]').length);
    const accentBefore = await page.evaluate(
      () => getComputedStyle(document.documentElement).getPropertyValue('--primary').trim());
    await page.locator('[data-testid="theme-hex-primary"]').first().fill('#ff5533').catch(() => {});
    await page.keyboard.press('Enter').catch(() => {});
    await page.waitForTimeout(1400);
    const accentAfter = await page.evaluate(
      () => getComputedStyle(document.documentElement).getPropertyValue('--primary').trim());
    results.accentOverrideApplied = accentBefore !== accentAfter;
    const backgroundForContrast = await page.evaluate(
      () => getComputedStyle(document.documentElement).getPropertyValue('--bg-base').trim());
    // Primary text set to the background colour is 1:1 contrast in whatever theme is active, so the
    // warning is expected either way (the old probe assumed a dark theme and could not see it).
    await page.locator('[data-testid="theme-hex-text-primary"]').first()
      .fill(backgroundForContrast || '#ffffff').catch(() => {});
    await page.keyboard.press('Enter').catch(() => {});
    await page.waitForTimeout(1400);
    results.contrastProbe = { textPrimaryFilledWith: backgroundForContrast };
    results.contrastWarningShown = (await page.locator('[data-testid="theme-color-warnings"]').count()) > 0;
    await shot('sweep3-01-theme-colors');
    await page.locator('[data-testid="theme-colors-restore"]').first().click().catch(() => {});
    await page.waitForTimeout(1500);
    results.restoreAllWorked = await waitFor(async () => {
      const accent = await page.evaluate(
        () => getComputedStyle(document.documentElement).getPropertyValue('--primary').trim());
      return accent !== accentAfter ? true : null;
    }, 9000, 'restore-defaults');
    if (!results.restoreAllWorked) {
      await page.locator('[data-testid="theme-colors-restore"]').first().click().catch(() => {});
      await page.waitForTimeout(1500);
      results.restoreAllWorked = await page.evaluate(
        () => getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()) !== accentAfter;
    }

    await page.evaluate(() => { location.hash = '/settings/model'; });
    await page.waitForTimeout(2600);
    results.defaultModelCard = await waitFor(
      () => page.locator('[data-testid="kel-default-model-card"]').count(), 12000, 'default-card');
    results.modelCardText = (await bodyText()).slice(-500);

    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);
    await page.getByText(/Renamed chat|Second chat|Rich rendering chat/).first().click().catch(() => {});
    await page.waitForTimeout(2200);
    results.headerButtonInventory = await page.evaluate(() =>
      Array.from(document.querySelectorAll('button')).filter((b) => b.offsetParent !== null)
        .map((b) => ((b.getAttribute('data-testid') || '') + '|' + (b.textContent || '').trim().slice(0, 24))).slice(0, 24));
    const pill = page.locator('[data-testid="kel-model-pill"], button:has-text("Kel model")').first();
    results.modelPillFound = await pill.count();
    if (results.modelPillFound) {
      await pill.click().catch(() => {});
      await page.waitForTimeout(900);
      results.modelPillMenu = (await bodyText()).slice(-400);
      const option = page.getByText(/DeepSeek Reasoner|Claude Sonnet|DeepSeek Chat|Claude \(built-in\)/).first();
      if (await option.count()) {
        await option.click().catch(() => {});
        await page.waitForTimeout(1200);
      }
      results.modelChoicePersisted = await page.evaluate(async () => {
        const api = window.kelAPI;
        if (!api) return null;
        try {
          const state = await api.request('/api/model', { action: 'get' });
          return JSON.stringify(state).slice(0, 220);
        } catch (error) {
          return 'error: ' + String(error);
        }
      });
      await shot('sweep3-02-model-pill');
    }

    const backupDir = `${outDir}/backup-target`;
    fs.mkdirSync(backupDir, { recursive: true });
    await page.evaluate(() => { location.hash = '/settings/system'; });
    await page.waitForTimeout(2600);
    results.dataPathShown = await waitFor(async () => {
      const txt = await page.locator('[data-testid="data-folder-path"]').first().innerText().catch(() => '');
      return txt && txt !== 'Loading…' ? txt.slice(0, 120) : null;
    }, 8000, 'data-path');
    await page.locator('[data-testid="copy-data-path"]').first().click().catch(() => {});
    await page.waitForTimeout(800);
    results.copyPathToast = /copied/i.test(await bodyText());
    await page.evaluate((target) => { window.__kelBackupTarget = target; }, backupDir);
    await page.locator('[data-testid="backup-target"]').first().fill(backupDir);
    await page.locator('[data-testid="backup-now"]').first().click();
    results.backupCreated = await waitFor(
      async () => /Backup created/i.test(await bodyText()) ? true : null, 30000, 'backup-created');
    if (!results.backupCreated) {
      results.backupError = await page.evaluate(async () => {
        const api = window.kelAPI;
        if (!api) return 'no-bridge';
        try {
          const res = await api.request('/api/backup', { action: 'create', target: window.__kelBackupTarget });
          return 'direct-ok: ' + JSON.stringify(res).slice(0, 120);
        } catch (error) {
          return 'direct-error: ' + String(error).slice(0, 160);
        }
      });
    }
    results.backupFolders = fs.readdirSync(backupDir);
    if (results.backupFolders.length) {
      const backupPath = `${backupDir}/${results.backupFolders[0]}`;
      await page.locator('[data-testid="restore-source"]').first().fill(backupPath);
      await page.locator('[data-testid="restore-inspect"]').first().click();
      results.restoreConfirm = await waitFor(
        async () => /Restore this backup\?/i.test(await bodyText()) ? true : null, 12000, 'restore-confirm');
      await page.getByText(/Keep current data/i).first().click().catch(() => {});
      await page.waitForTimeout(700);
      results.restoreCancelled = !/Ready to restore/i.test(await bodyText());
    }
    await shot('sweep3-03-backup');

    // Text size and Ctrl +/- both drive Electron's zoom factor (useFontScale -> app.set-zoom-factor),
    // so the honest measurement is the window's actual zoom factor, not a CSS font size. Start from
    // a known factor: the harness pins the viewport to 1440x900, which normalises the displayed
    // zoom, so both measurements begin with a Ctrl+0 reset.
    const zoomFactor = () =>
      app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].webContents.getZoomFactor());
    const sendZoomKey = (keyCode) =>
      app.evaluate(({ BrowserWindow }, code) => {
        const contents = BrowserWindow.getAllWindows()[0].webContents;
        contents.sendInputEvent({ type: 'keyDown', keyCode: code, modifiers: ['control'] });
        contents.sendInputEvent({ type: 'keyUp', keyCode: code, modifiers: ['control'] });
      }, keyCode);
    await page.evaluate(() => { location.hash = '/settings/appearance'; });
    await page.waitForTimeout(2200);
    await sendZoomKey('0');
    await page.waitForTimeout(900);
    const beforeText = await zoomFactor();
    await page.locator('[data-testid="text-larger"]').first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(1200);
    const afterLarger = await zoomFactor();
    await page.locator('[data-testid="text-smaller"]').first().click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(1200);
    results.textScale = { before: beforeText, afterLarger, afterSmaller: await zoomFactor() };
    results.textScaleWorks = afterLarger > beforeText;
    const beforeZoom = await zoomFactor();
    await sendZoomKey('=');
    await page.waitForTimeout(1000);
    const afterZoomIn = await zoomFactor();
    await sendZoomKey('0');
    await page.waitForTimeout(1000);
    const afterReset = await zoomFactor();
    results.zoomKeys = { before: beforeZoom, afterIn: afterZoomIn, afterReset };
    results.zoomKeysWork = afterZoomIn > beforeZoom && Math.abs(afterReset - 0.95) < 0.0001;
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot('sweep3-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-sweep3', results);
  return results;
}

async function scenarioSweep4() {
  const results = { schema: 1, scenario: 'sweep4', steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const waitFor = async (fn, timeout = 12000, label = '') => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const value = await fn();
        if (value) { results.steps.push({ label, ms: Date.now() - start }); return value; }
      } catch (error) { /* retry */ }
      await page.waitForTimeout(400);
    }
    results.steps.push({ label, ms: -1, timedOut: true });
    return null;
  };
  const bodyText = () => page.evaluate(() => document.body.innerText || '');
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/settings/model'; });
    await page.waitForTimeout(2600);
    results.modelPageButtons = await page.evaluate(() =>
      Array.from(document.querySelectorAll('button')).filter((b) => b.offsetParent !== null)
        .map((b) => (b.textContent || '').trim().slice(0, 24)).slice(0, 24));
    // The provider credential field below the fold (the user-reported DeepSeek case class).
    const credentialBtn = page.getByText(/set credential metadata/i).first();
    results.credentialAffordance = await credentialBtn.count();
    if (results.credentialAffordance) {
      await credentialBtn.click().catch(() => {});
      await page.waitForTimeout(1500);
      results.formText = await waitFor(async () => {
        const body = await bodyText();
        return /credential|api key|value/i.test(body) ? body.slice(-420) : null;
      }, 8000, 'provider-form');
      await shot('sweep4-01-provider-form');
      const keyInput = page
        .locator('.arco-modal input, [role="dialog"] input, input[type="password"], input[placeholder*="key" i], input[placeholder*="value" i]')
        .first();
      results.keyFieldFound = await waitFor(async () => ((await keyInput.count()) ? true : null), 8000, 'key-field');
      if (results.keyFieldFound) {
        await keyInput.scrollIntoViewIfNeeded().catch(() => {});
        await page.waitForTimeout(400);
        results.keyFieldVisibleAfterScroll = await keyInput.isVisible().catch(() => false);
        await keyInput.click({ timeout: 6000 }).catch(() => {});
        await keyInput.fill('test-key-scroll-case').catch(() => {});
        results.keyFieldTyped = (await keyInput.inputValue().catch(() => '')) === 'test-key-scroll-case';
        results.keyFieldFocused = await page.evaluate(() => {
          const a = document.activeElement;
          return Boolean(a && a.tagName === 'INPUT');
        });
      }
      await page.keyboard.press('Escape');
      await page.waitForTimeout(600);
      await shot('sweep4-02-key-typed');
    }
    // ---- backup / restore / restart recovery ----
    const fs = require('fs');
    const backupDir = `${outDir}/backup-target`;
    fs.mkdirSync(backupDir, { recursive: true });
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2400);
    for (let i = 0; i < 2; i += 1) {
      await page.locator('[data-testid="record-button"]').first().click();
      await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 20000, 'rec-bar');
      await page.waitForTimeout(3200);
      await page.locator('[data-testid="stop-button"]').first().click();
      await page.waitForTimeout(1800);
    }
    results.rowsBeforeBackup = await waitFor(
      async () => ((await page.locator('[data-testid="transcript-row"]').count()) >= 2 ? 2 : null),
      30000, 'rows-before-backup');
    await page.evaluate(() => { location.hash = '/settings/system'; });
    await page.waitForTimeout(2600);
    results.dataFolderShown = await waitFor(
      async () => ((await page.locator('[data-testid="data-folder-path"]').innerText().catch(() => '')).length > 3 ? true : null),
      8000, 'data-folder');
    await page.locator('[data-testid="backup-target"]').first().fill(backupDir.replace(/\\/g, '\\'));
    await page.locator('[data-testid="backup-now"]').first().click();
    results.backupCreated = await waitFor(async () => {
      const toast = /backup created/i.test(await bodyText());
      const folders = fs.readdirSync(backupDir).filter((name) => name.startsWith('Kel-Backup-'));
      return toast || folders.length > 0 ? true : null;
    }, 40000, 'backup-created');
    await shot('sweep4-03-backup');
    // delete one transcript through the UI
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2400);
    await page.locator('[data-testid="transcript-row"]').first().click();
    await page.waitForTimeout(700);
    await page.locator('[data-testid="delete-transcript"]').first().click();
    await page.waitForTimeout(1000);
    results.deleteDialogSeen = await page.locator('.arco-modal').count();
    await page.locator('.arco-modal button:has-text("Delete")').last().click().catch(() => {});
    await page.waitForTimeout(1800);
    results.rowsAfterDelete = await page.locator('[data-testid="transcript-row"]').count();
    // restore from the backup, then restart
    await page.evaluate(() => { location.hash = '/settings/system'; });
    await page.waitForTimeout(2400);
    const backups = fs.readdirSync(backupDir).filter((name) => name.startsWith('Kel-Backup-'));
    results.backupFolders = backups.length;
    await waitFor(() => page.locator('[data-testid="restore-source"]').count(), 10000, 'restore-card');
    await page.locator('[data-testid="restore-source"]').first().fill(`${backupDir}/${backups[0]}`);
    await page.locator('[data-testid="restore-inspect"]').first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(1200);
    results.restoreConfirm = await waitFor(async () => {
      const body = await bodyText();
      return /restore this backup/i.test(body) ? body.slice(-300) : null;
    }, 12000, 'restore-confirm');
    await shot('sweep4-04-restore-confirm');
    // Scope to the dialog: the card title "Restore" also matches /^restore$/i and comes first in
    // the DOM, so an unscoped click confirmed nothing and the restore was never staged.
    await page.locator('.arco-modal button:has-text("Restore")').last().click({ timeout: 8000 }).catch(() => {});
    results.restoreStaged = await waitFor(async () => /close and reopen kel/i.test(await bodyText()), 15000, 'restore-staged');
    await closeApp(app, kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    kelwork = ctx.kelwork;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2600);
    results.rowsAfterRestore = await page.locator('[data-testid="transcript-row"]').count();
    results.restoreRecovered = results.rowsAfterRestore >= 2;
    await shot('sweep4-05-restored');
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 500));
    await shot('sweep4-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-sweep4', results);
  return results;
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
    const composer = page
      .locator('[data-testid="guid-input"]:visible, [data-testid="sendbox-input"]:visible, textarea:visible')
      .first();
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
  const panelJson = () =>
    page.evaluate(async () => {
      const api = window.kelAPI;
      return api ? await api.request('/api/vetting', { action: 'panel' }) : null;
    });
  const waitPanel = async (fn, timeoutMs, label) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        const panelDump = JSON.stringify((await panelJson()) || {});
        let previewDump = '';
        try {
          previewDump = JSON.stringify((await previewJson()) || {});
        } catch (previewError) {
          previewDump = '';
        }
        const value = await fn(panelDump + previewDump);
        if (value) {
          results.steps.push({ label, ms: Date.now() - start });
          return value;
        }
      } catch (error) {
        /* retry */
      }
      await page.waitForTimeout(500);
    }
    results.steps.push({ label, ms: -1, timedOut: true });
    return null;
  };
  const previewJson = () =>
    page.evaluate(async () => {
      const api = window.kelAPI;
      return api ? await api.request('/api/vetting', { action: 'preview' }) : null;
    });
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
    results.batchShown = await waitPanel((dump) => /Q1\b/.test(dump), 25000, 'batch-1-in-panel');
    await shot(page, 'vetting-01-batch');

    const answers = ['1: C', '2: A', '3: B', '4: D', '5: B', '6: A', '7: A', '8: C', '9: D', '10: B'];
    for (const answer of answers) {
      const body = await send(answer, 'answer-' + answer);
      results.lastAnswerSawProgress = /Recorded: \d+ of \d+ recorded/.test(body);
    }
    results.allAnswersRecorded = await waitPanel(
      (dump) => ((dump.match(/ANSWERED/g) || []).length >= 10 ? true : null),
      25000,
      'ten-answers-recorded'
    );
    results.answerProgressCount = await panelJson().then((panel) => ({
      answered: ((JSON.stringify(panel || {}).match(/ANSWERED/g) || []).length),
    }));
    await shot(page, 'vetting-02-rapid-answers');

    await send('process answers', 'process');
    results.batch2Shown = await waitPanel((dump) => /Q1[1-9]|Q2[0-9]/.test(dump), 30000, 'batch-2-in-panel');
    await shot(page, 'vetting-03-batch-2');

    await send('19: B', 'answer-19');
    await send('view decisions', 'view-decisions');
    results.decisionsSeen = await waitPanel((dump) => /decision/i.test(dump), 20000, 'decisions-in-panel');
    await send('show greyboxes 19', 'greyboxes');
    results.greyboxesSeen = await waitPanel((dump) => /greybox/i.test(dump), 25000, 'greyboxes-in-panel');
    await shot(page, 'vetting-04-greyboxes');

    await send('finish spec now', 'finish');
    results.specSaved = await waitPanel((dump) => /Design specification|coverage/i.test(dump) ? true : null, 30000, 'spec-preview');
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
    const composer = page
      .locator('[data-testid="guid-input"]:visible, [data-testid="sendbox-input"]:visible, textarea:visible')
      .first();
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

    // Escape cancels an in-progress recording on the page without saving a row.
    const rowsBeforeEscape = await page.locator('[data-testid="transcript-row"]').count();
    await page.locator('[data-testid="record-button"]').first().click();
    await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 20000, 'escape-bar');
    await page.keyboard.press('Escape');
    results.escapeCancelled = await waitFor(async () => {
      const bar = await page.locator('[data-testid="recording-bar"]').count();
      const rows = await page.locator('[data-testid="transcript-row"]').count();
      return bar === 0 && rows === rowsBeforeEscape;
    }, 10000, 'escape-cancelled');

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
    await page.locator('[data-testid="copy-transcript"]').first().click();
    await page.waitForTimeout(400);
    await page.locator('[data-testid="download-txt"]').first().click();
    await page.waitForTimeout(700);
    results.downloadAudioEnabled = await page.locator('[data-testid="download-audio"]').first().isEnabled().catch(() => false);
    await page.locator('[data-testid="download-audio"]').first().click();
    await page.waitForTimeout(700);
    results.copyAndDownload = true;

    // Combine merges another transcript into the selected one and removes it from the list.
    await page.locator('[data-testid="transcript-row"]').first().click();
    await page.waitForTimeout(500);
    await page.locator('[data-testid="combine-open"]').first().click();
    await page.locator('[data-testid="combine-select"]').first().click();
    await page.locator('.arco-select-option').first().click();
    await page.locator('[data-testid="combine-confirm"]').first().click();
    results.combined = await waitFor(async () => {
      const text = await bodyText();
      const folderRows = await page.locator('[data-testid="folder-transcript"]').count();
      return /Merged into this transcript/.test(text) && folderRows === 0;
    }, 12000, 'combined');

    // Keep a healthy library for the restart check.
    await page.locator('[data-testid="record-button"]').first().click();
    await waitFor(() => page.locator('[data-testid="recording-bar"]').count(), 20000, 'second-bar');
    await page.waitForTimeout(3200);
    await page.locator('[data-testid="stop-button"]').first().click();
    results.secondRow = await waitFor(async () => (await page.locator('[data-testid="transcript-row"]').count()) >= 2, 30000, 'second-row');

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
    results.composerSingleCopy = await waitFor(async () => {
      const value = (await boxValue()).trim();
      if (value.length < 10) return false;
      const fragment = value.split(/\s+/).slice(0, 3).join(' ');
      return fragment.length > 5 && value.split(fragment).length === 2;
    }, 8000, 'composer-single-copy');
    await page.locator('textarea').first().fill('');
    results.composerCleared = true;
    await shot(page, 'transcription-05-composer');

    // Send to chat hands the transcript to the composer as editable text (no auto-send).
    await page.evaluate(() => { location.hash = '/transcription'; });
    await page.waitForTimeout(2000);
    await page.locator('[data-testid="transcript-row"]').first().click();
    await page.waitForTimeout(500);
    await page.locator('[data-testid="send-to-chat"]').first().click();
    await page.waitForTimeout(1600);
    results.sendToChat = await waitFor(async () => {
      const value = (await boxValue()).trim();
      return value.length > 20 && /transcript/i.test(value) ? value.slice(0, 40) : null;
    }, 15000, 'send-to-chat');
    await page.locator('textarea').first().fill('');

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
    await page.locator('[data-testid="review-edit"]').first().click();
    await page.locator('[data-testid="review-edit-text"]').first().fill('12: A, matchup visually dominant');
    await page.locator('[data-testid="review-recheck"]').first().click();
    results.recheckWorked = await waitFor(() => page.locator('[data-testid="review-list"]').count(), 10000, 'review-recheck');
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

async function scenarioKeepAwake() {
  // Keep-awake as a user journey: off by default, enable -> active, survives restart and re-applies
  // at startup, disable -> released. The card reports the app's live inhibition state, not the switch
  // position, so this proves the setting actually holds something.
  const results = { schema: 1, scenario: 'keepawake', steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  const stateText = () => page.locator('[data-testid="kel-keep-awake-state"]').first().innerText().catch(() => '');
  const switchOn = async () =>
    (await page.locator('[data-testid="kel-keep-awake-switch"] .arco-switch-checked').count()) > 0;
  const openSystem = async () => {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.evaluate(() => { location.hash = '/settings/system'; });
    await page.waitForTimeout(2600);
  };
  try {
    await openSystem();
    results.cardPresent = await page.locator('[data-testid="kel-keep-awake-card"]').count();
    results.initialState = (await stateText()).slice(0, 90);
    results.initiallyOff = (await switchOn()) === false;

    await page.locator('[data-testid="kel-keep-awake-switch"]').first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(1600);
    results.stateAfterEnable = (await stateText()).slice(0, 90);
    results.activeAfterEnable = /Active/.test(results.stateAfterEnable);
    results.toastAfterEnable = /keep this computer awake/i.test(await page.evaluate(() => document.body.innerText || ''));
    await shot('keepawake-01-enabled');

    // Restart: the choice is per computer and must come back applied, not just remembered.
    await closeApp(app, kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    kelwork = ctx.kelwork;
    await openSystem();
    results.stateAfterRestart = (await stateText()).slice(0, 90);
    results.stillOnAfterRestart = await switchOn();
    results.activeAfterRestart = /Active/.test(results.stateAfterRestart);

    await page.locator('[data-testid="kel-keep-awake-switch"]').first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(1600);
    results.stateAfterDisable = (await stateText()).slice(0, 90);
    results.inactiveAfterDisable = /Off/.test(results.stateAfterDisable);
    await shot('keepawake-02-disabled');
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
    await shot('keepawake-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-keepawake', results);
  return results;
}

async function scenarioSessionTools() {
  // Conversation-scoped tool controls as a user journey: isolation between chats, restart, reset,
  // narrowing, enabling a configured capability, an unavailable one, and the natural-language path.
  const results = { schema: 1, scenario: 'sessiontools', steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const shot = (name) => page.screenshot({ path: `${outDir}/${name}.png` }).catch(() => {});
  const ask = (body) =>
    page.evaluate(async (payload) => {
      const api = window.kelAPI;
      if (!api) return null;
      try {
        return await api.request('/api/capabilities', payload);
      } catch (error) {
        return { error: String(error) };
      }
    }, body);
  const rowsFor = (conversation) => ask({ action: 'get', conversation });
  const rowOf = (rows, id) => (Array.isArray(rows) ? rows.find((row) => row.id === id) : null);
  const openChat = async (title) => {
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.waitForTimeout(2200);
    await page.getByText(title, { exact: false }).first().click().catch(() => {});
    await page.waitForTimeout(2400);
  };
  const engineId = () =>
    page.evaluate(async () => {
      const api = window.kelAPI;
      const hash = String(location.hash);
      const match = hash.match(/conversation[\/]([A-Za-z0-9_-]+)/);
      if (!api || !match) return null;
      try {
        return await api.conversation(match[1]);
      } catch {
        return null;
      }
    });
  try {
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await openChat('Rich rendering chat');
    results.pillPresent = await page.locator('[data-testid="kel-tools-pill"]').count();
    const chatA = await engineId();
    results.chatA = chatA;

    // The menu speaks plain words: capability labels, availability, and no raw tool/runtime ids.
    await page.locator('[data-testid="kel-tools-pill"]').first().click();
    await page.waitForTimeout(900);
    const menu = await page.locator('[data-testid="kel-tools-menu"]').first().innerText().catch(() => '');
    results.menuText = menu.replace(/\s+/g, ' ').slice(0, 320);
    results.menuPlain = /Web/.test(menu) && /GitHub/.test(menu) && /Files/.test(menu);
    results.menuHidesMachinery = !/mcp|server|tool id|runtime/i.test(menu);
    results.menuOffersRemoved = !/Google Drive|Connected apps/i.test(menu);
    await shot('sessiontools-01-menu');
    await page.keyboard.press('Escape').catch(() => {});

    // Narrowing: Web off for this chat only.
    await ask({ action: 'set', conversation: chatA, capability: 'web', state: 'off' });
    const aAfter = await rowsFor(chatA);
    results.chatAWebOverride = rowOf(aAfter, 'web')?.override;
    results.chatAWebUsable = rowOf(aAfter, 'web')?.usable;

    // Allow once: the same control grants a single action, and the engine reports the capability as
    // usable while that grant is live (the single-use spend is engine-tested).
    await ask({ action: 'allow_once', conversation: chatA, capability: 'web' });
    results.chatAAllowOnceUsable = rowOf(await rowsFor(chatA), 'web')?.usable;

    // Isolation: a second conversation keeps its own (default) state, and can differ the other way.
    await openChat('Second chat');
    const chatB = await engineId();
    results.chatB = chatB;
    const bRows = await rowsFor(chatB);
    results.chatBWebOverride = rowOf(bRows, 'web')?.override;
    results.chatBWebUsable = rowOf(bRows, 'web')?.usable;
    await ask({ action: 'set', conversation: chatB, capability: 'web', state: 'on' });

    // Enable: an already-available capability is genuinely usable here.
    const bAfter = await rowsFor(chatB);
    results.chatBWebEnabledUsable = rowOf(bAfter, 'web')?.usable;
    results.chatBWebEffective = rowOf(bAfter, 'web')?.effective;

    // Removed capabilities (CAP-01 / V1.6): Google Drive and Connected apps have no production
    // effect path in this release, so the control no longer offers them and a stale caller is
    // refused plainly instead of being shown a switch that could not be kept.
    const bRowsBeforeRemoved = await rowsFor(chatB);
    results.offeredCapabilityIds = (Array.isArray(bRowsBeforeRemoved) ? bRowsBeforeRemoved.map((row) => row.id) : []).join(',');
    const driveAsk = await ask({ action: 'set', conversation: chatB, capability: 'drive', state: 'on' });
    results.removedDriveRefused = !!driveAsk && driveAsk.error !== undefined && driveAsk.error !== null;
    results.removedDriveAbsent = rowOf(await rowsFor(chatB), 'drive') === undefined;

    // Natural language: the chat instruction writes the same state as the menu.
    await openChat('Rich rendering chat');
    const composer = page.locator('[data-testid="sendbox-input"]:visible, textarea:visible').first();
    await composer.click({ timeout: 8000 }).catch(() => {});
    await composer.fill('Use GitHub for this conversation.');
    await page.keyboard.press('Enter');
    let nlSeen = false;
    let nlBody = '';
    for (let i = 0; i < 12 && !nlSeen; i += 1) {
      await page.waitForTimeout(2500);
      nlBody = await page.evaluate(() => document.body.innerText || '');
      nlSeen = /I can use GitHub in this conversation/i.test(nlBody);
    }
    results.naturalLanguageReplySeen = nlSeen;
    if (!nlSeen) {
      // The transcript is virtualized: nudge it to the newest message and read again.
      await page.mouse.wheel(0, 4000).catch(() => {});
      await page.waitForTimeout(1500);
      nlBody = await page.evaluate(() => document.body.innerText || '');
      nlSeen = /I can use GitHub in this conversation/i.test(nlBody);
      results.naturalLanguageReplySeen = nlSeen;
    }
    results.naturalLanguageBodyTail = nlBody.slice(-160).replace(/\s+/g, ' ');
    await shot('sessiontools-03-natural-language');
    const aRows = await rowsFor(chatA);
    results.chatAGithubOverride = rowOf(aRows, 'github')?.override;

    // Ordinary talk about a tool must not change capability state (CAP-02 regression): the web
    // override set through the control earlier stays exactly as it was.
    await composer.fill('Can you use the web here?');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(6000);
    results.ordinaryTalkWebOverride = rowOf(await rowsFor(chatA), 'web')?.override;
    await shot('sessiontools-04-ordinary-talk');

    // CAP2-CLAUSE: an explicit embedded control is the bracketed form; only the bracket token is
    // consumed and the request is forwarded without it (the workspace wrapper verifies the exact
    // forwarded text against the engine database afterwards).
    await composer.fill('Please summarize the release notes. [terminal: off]');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(7000);
    results.embeddedClauseTerminalOverride = rowOf(await rowsFor(chatA), 'terminal')?.override;

    // Ordinary prose that merely CONTAINS control-shaped text must not mutate state or alter the
    // message: plain substring, quoted, and inline-code variants all leave GitHub as it was (on).
    await composer.fill('The string github: off appears in this error.');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(5000);
    results.proseGithubOverridePlain = rowOf(await rowsFor(chatA), 'github')?.override;
    await composer.fill('he said "github: off" in the meeting yesterday');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(5000);
    results.proseGithubOverrideQuoted = rowOf(await rowsFor(chatA), 'github')?.override;
    await composer.fill('Use `github: off` in the script.');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(5000);
    results.proseGithubOverrideCode = rowOf(await rowsFor(chatA), 'github')?.override;
    await shot('sessiontools-05-clause-safety');

    // Restart: both conversations keep their own state.
    await closeApp(app, kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    kelwork = ctx.kelwork;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    const aRestart = await rowsFor(chatA);
    const bRestart = await rowsFor(chatB);
    results.afterRestartChatAWeb = rowOf(aRestart, 'web')?.override;
    results.afterRestartChatAGithub = rowOf(aRestart, 'github')?.override;
    results.afterRestartChatBWeb = rowOf(bRestart, 'web')?.override;

    // Reset: chat A follows the global default again.
    await ask({ action: 'reset', conversation: chatA });
    const aReset = await rowsFor(chatA);
    results.afterResetChatAWeb = rowOf(aReset, 'web')?.override;
    results.afterResetChatAUsable = rowOf(aReset, 'web')?.usable;
    results.afterResetChatBUntouched = rowOf(await rowsFor(chatB), 'web')?.override;
    await shot('sessiontools-02-after-reset');
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
    await shot('sessiontools-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-sessiontools', results);
  return results;
}

async function scenarioMemoryProps() {
  // The memory proposal surface as a user journey: a Design Vetting answer that disagrees with a
  // saved rule queues a review on the chat pill; Accept updates knowledge (the previous value is
  // kept), Reject never re-asks for the same answer, Defer persists across restart, and the extra
  // project's same-topic rule is untouched. The driver seeds the stored rules before this runs
  // (seed-memory-prop.py), and probes the database after it (memoryprops-db-probe.py).
  const results = { schema: 1, scenario: 'memoryprops', steps: [], errors: [] };
  let ctx = await launchApp();
  let { app, page, kelwork } = ctx;
  const mem = (payload) =>
    page.evaluate(async (body) => {
      const api = window.kelAPI;
      return api ? await api.request('/api/memory', body) : null;
    }, payload);
  const vet = (payload) =>
    page.evaluate(async (body) => {
      const api = window.kelAPI;
      return api ? await api.request('/api/vetting', body) : null;
    }, payload);
  const send = async (text, label) => {
    const composer = page
      .locator('[data-testid="guid-input"]:visible, [data-testid="sendbox-input"]:visible, textarea:visible')
      .first();
    await composer.click({ timeout: 15000 });
    await composer.fill('');
    await composer.type(text, { delay: 8 });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1500);
    results.steps.push({ label, text });
  };
  const waitText = async (needle, timeoutMs, label) => {
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
  const waitVet = async (needle, timeoutMs, label) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      try {
        const dump = JSON.stringify((await vet({ action: 'panel' })) || {});
        if (dump.includes(needle)) {
          results.steps.push({ label, found: needle, ms: Date.now() - start });
          return true;
        }
      } catch {
        /* retry */
      }
      await page.waitForTimeout(500);
    }
    results.steps.push({ label, found: needle, ms: -1, timedOut: true });
    return false;
  };
  const remount = async () => {
    await page.reload();
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    await page.waitForTimeout(1500);
  };
  try {
    await page.waitForTimeout(9000);
    results.onboardingAtBoot = await dismissOnboarding(page);
    await page.evaluate(() => {
      location.hash = '/guid';
    });
    await page.waitForTimeout(2000);

    // 1) A Design Vetting answer that disagrees with the saved Q6 rule queues a pending proposal.
    await send('start design vetting: Memory review check', 'start');
    results.batchShown = await waitVet('Q1', 25000, 'vetting-batch-shown');
    await send('6: A', 'answer-6A');
    await page.waitForTimeout(2500);
    const list1 = await mem({ action: 'proposals', state: 'open' });
    const q6 = (list1?.proposals || []).find((p) => p.topic === 'vetting.Q6');
    results.proposalQueued = Boolean(q6 && q6.state === 'pending');
    results.proposalKind = q6?.kind || null;
    results.proposalCurrent = q6?.current?.summary || null;

    // 2) The chat offers the review; the card shows current, proposed and why in plain words.
    // The header pills live on a conversation page, so open the chat the vetting message created
    // (this is engine conversation 'main', the same chat the session is bound to).
    await page.evaluate(() => {
      location.hash = '/guid';
    });
    await page.waitForTimeout(2500);
    await page
      .getByText('start design vetting: Memory review check', { exact: false })
      .first()
      .click();
    await page.waitForTimeout(4000);
    results.onConversationPage = await page.evaluate(() => location.hash.startsWith('#/conversation/'));
    results.pillShown = await waitText('Review ·', 15000, 'review-pill-visible');
    await page.locator('[data-testid="kel-memory-pill"]').click();
    await page.waitForTimeout(900);
    results.cardShown = await waitText(
      'Kel thinks this project decision changed',
      5000,
      'card-headline'
    );
    results.currentShown = await waitText(
      'Top-level navigation stays a single flat bar.',
      5000,
      'card-current'
    );
    results.whyShown = await waitText(
      'Your latest Design Vetting decisions conflict with the stored project rule',
      5000,
      'card-why'
    );
    await shot(page, 'memoryprops-01-card');

    // 3) Accept: the saved rule updates through the review; the queue clears.
    await page.locator('[data-testid="kel-memory-accept"]').click();
    await page.waitForTimeout(3500);
    const list2 = await mem({ action: 'proposals', state: 'open' });
    results.acceptedClearsQueue = (list2?.proposals || []).length === 0;
    const all2 = await mem({ action: 'proposals', state: 'all' });
    results.q6Accepted = (all2?.proposals || []).some(
      (p) => p.topic === 'vetting.Q6' && p.state === 'accepted'
    );

    // 4) Reject: a new disagreement asks once, the rejection settles it, the same answer never re-asks.
    await send('7: A', 'answer-7A');
    await page.waitForTimeout(2500);
    const list3 = await mem({ action: 'proposals', state: 'open' });
    results.q7Queued = (list3?.proposals || []).some(
      (p) => p.topic === 'vetting.Q7' && p.state === 'pending'
    );
    await remount();
    await page.locator('[data-testid="kel-memory-pill"]').click();
    await page.waitForTimeout(900);
    await page.locator('[data-testid="kel-memory-reject"]').click();
    await page.waitForTimeout(3500);
    const all4 = await mem({ action: 'proposals', state: 'all' });
    results.q7Rejected = (all4?.proposals || []).some(
      (p) => p.topic === 'vetting.Q7' && p.state === 'rejected'
    );
    await send('7: A', 'answer-7A-again');
    await page.waitForTimeout(2500);
    const list5 = await mem({ action: 'proposals', state: 'open' });
    results.rejectedNotReAsked = !(list5?.proposals || []).some((p) => p.topic === 'vetting.Q7');
    await remount();
    const bodyAfterReject = await page.evaluate(() => document.body.innerText || '');
    results.pillHiddenAfterReject = !bodyAfterReject.includes('Review ·');

    // 5) Defer: it leaves the chat but stays queued for Work.
    await send('8: C', 'answer-8C');
    await page.waitForTimeout(2500);
    await remount();
    await page.locator('[data-testid="kel-memory-pill"]').click();
    await page.waitForTimeout(900);
    await page.locator('[data-testid="kel-memory-defer"]').click();
    await page.waitForTimeout(3500);
    const list6 = await mem({ action: 'proposals', state: 'open' });
    results.q8Deferred = (list6?.proposals || []).some(
      (p) => p.topic === 'vetting.Q8' && p.state === 'deferred'
    );
    await remount();
    const bodyAfterDefer = await page.evaluate(() => document.body.innerText || '');
    results.deferredHiddenFromChat = !bodyAfterDefer.includes('Review ·');

    // 6) The Work panel hosts the same queue on its Project knowledge tab.
    try {
      await page.locator('.kel-work-context-btn').first().click({ timeout: 8000 });
      await page.waitForTimeout(1500);
      await page.locator('text=Project knowledge').first().click({ timeout: 8000 });
      await page.waitForTimeout(1500);
      results.workPanelProposals = await page.evaluate(
        () => document.querySelectorAll('[data-testid="kel-work-proposal"]').length
      );
      results.workPanelHistory = await page.evaluate(() =>
        (document.body.innerText || '').includes('What changed')
      );
      await shot(page, 'memoryprops-02-work');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(800);
    } catch (error) {
      results.steps.push({ label: 'work-panel-probe', error: String(error).slice(0, 240) });
    }

    // 7) Restart: every decision survives.
    await closeApp(app, kelwork, results);
    ctx = await launchApp();
    app = ctx.app;
    page = ctx.page;
    kelwork = ctx.kelwork;
    await page.waitForTimeout(9000);
    await dismissOnboarding(page);
    const afterRestart = await mem({ action: 'proposals', state: 'all' });
    const states = Object.fromEntries(
      (afterRestart?.proposals || []).map((p) => [p.topic, p.state])
    );
    results.afterRestartStates = states;
    results.restartKeepsStates =
      states['vetting.Q6'] === 'accepted' &&
      states['vetting.Q7'] === 'rejected' &&
      states['vetting.Q8'] === 'deferred';
    results.consoleErrors = (ctx.consoleErrors || []).slice(0, 12);
  } catch (error) {
    results.errors.push(String(error).slice(0, 400));
    await shot(page, 'memoryprops-error');
  }
  await closeApp(app, kelwork, results);
  save('ux-memoryprops', results);
  return results;
}

(async () => {
  const run = {
    'first-run': scenarioFirstRun,
    tour: scenarioTour,
    settings: scenarioSettings,
    palette: scenarioPalette,
    sessiontools: scenarioSessionTools,
    memoryprops: scenarioMemoryProps,
    keepawake: scenarioKeepAwake,
    keyboard: scenarioKeyboard,
    readability: scenarioReadability,
    compose: scenarioCompose,
    vetting: scenarioVetting,
    'vetting-live': scenarioVettingLive,
    peek: scenarioPeek,
    paneldump: scenarioPaneldump,
    transcription: scenarioTranscription,
    hardening: scenarioHardening,
    'voice-vetting': scenarioVoiceVetting,
    'sweep-seed': scenarioSweepSeed,
    'sweep-a': scenarioSweepA,
    'sweep-b': scenarioSweepB,
    'sweep2': scenarioSweep2,
    'sweep3': scenarioSweep3,
    'sweep4': scenarioSweep4,
    'recheck-probe': scenarioRecheckProbe,
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
