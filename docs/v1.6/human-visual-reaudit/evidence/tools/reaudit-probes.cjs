#!/usr/bin/env node
/**
 * Kel V1.6 human-visual delta re-audit — INDEPENDENT probes (audit-owned).
 *
 * This script was written by the re-audit, not by the repair campaign. It is run against the
 * freshly built package and against the dedicated audit install. It performs objective checks
 * for the 14 human findings: scroll behaviour at 5 sizes, work->chat identity, sidebar mark and
 * badge bounds, permissions language (with raw-id observation), model page clarity, system
 * disclosure, appearance branding/typography floors, tools labels, desktop-pet truthfulness,
 * hidden-route redirects, donor-text sweep, narrow/zoom overflow, about logo, console errors.
 *
 * Usage:
 *   NODE_PATH=<desktop node_modules> node reaudit-probes.cjs <appDir> <rootDir> <outDir>
 *
 * Records JSON + screenshots; never throws on a failed probe (records the failure).
 */
'use strict';
const fs = require('fs');
const path = require('path');

function resolvePlaywright() {
  for (const m of ['playwright', '@playwright/test']) {
    try { return require.resolve(m); } catch (e) {}
  }
  if (process.env.PLAYWRIGHT_MODULE) return process.env.PLAYWRIGHT_MODULE;
  throw new Error('playwright not found; set NODE_PATH');
}
const { _electron: electron } = require(resolvePlaywright());

const appDir = path.resolve(process.argv[2]);
const rootDir = path.resolve(process.argv[3]);
const outDir = path.resolve(process.argv[4]);
fs.mkdirSync(outDir, { recursive: true });

const R = { startedAt: new Date().toISOString(), appDir, rootDir, probes: {}, shots: [], consoleErrors: [], pageErrors: [], notes: [] };
const V = (name, detail) => { R.probes[name] = detail; console.log('[probe] ' + name + ' :: ' + JSON.stringify(detail).slice(0, 600)); };

const DONOR = /aionui|aion core|aioncore|butler/i;

(async () => {
  const convMapPath = path.join(rootDir, 'kelwork', 'aion-conversations.json');
  const convMap = JSON.parse(fs.readFileSync(convMapPath, 'utf8'));
  const donorIds = Object.values(convMap);
  const expectedMain = convMap['main'];

  const app = await electron.launch({
    executablePath: path.join(appDir, 'Kel.exe'),
    timeout: 60000,
    env: {
      ...process.env,
      APPDATA: path.join(rootDir, 'appdata'),
      KEL_DATA_DIR: path.join(rootDir, 'kelwork'),
      KEL_HOST_DATA_DIR: path.join(rootDir, 'kelwork', 'host'),
      AIONUI_DISABLE_AUTO_UPDATE: '1',
      KEL_SKIP_TELEMETRY: '1',
    },
  });
  const page = await app.firstWindow({ timeout: 60000 });
  page.on('console', (m) => { if (m.type() === 'error') R.consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => R.pageErrors.push(String((e && e.message) || e)));
  await page.waitForLoadState('domcontentloaded');

  const hash = () => page.evaluate(() => window.location.hash);
  const settle = (ms) => page.waitForTimeout(ms || 700);
  const nav = async (h, ms) => { await page.evaluate((x) => { window.location.hash = x; }, h); await settle(ms || 1100); };
  const waitFor = async (fnBody, timeout, every) => {
    const t0 = Date.now();
    while (Date.now() - t0 < (timeout || 15000)) {
      try { if (await page.evaluate(fnBody)) return true; } catch (e) {}
      await page.waitForTimeout(every || 350);
    }
    return false;
  };
  const shot = async (name) => {
    const p = path.join(outDir, name + '.png');
    try { await page.screenshot({ path: p }); R.shots.push(name); } catch (e) { R.shots.push(name + ' (FAILED: ' + String(e && e.message) + ')'); }
  };
  const setSize = async (w, h) => {
    await app.evaluate(async ({ BrowserWindow }, size) => {
      const win = BrowserWindow.getAllWindows()[0];
      if (win) win.setBounds({ x: 60, y: 40, width: size.w, height: size.h });
    }, { w, h });
    await settle(500);
  };
  const setZoom = async (z) => {
    await app.evaluate(async ({ BrowserWindow }, zf) => {
      const win = BrowserWindow.getAllWindows()[0];
      if (win) win.webContents.setZoomFactor(zf);
    }, z);
    await settle(400);
  };
  const domClick = async (predicate) => page.evaluate((body) => {
    const fn = new Function('return (' + body + ')')();
    const el = fn();
    if (!el) return false;
    el.click();
    return true;
  }, predicate);

  try {
    /* ---------------- P1 boot ---------------- */
    let bootHash = '';
    for (let i = 0; i < 80; i++) {
      bootHash = await hash();
      if (bootHash && bootHash.length > 1 && !/login/i.test(bootHash)) break;
      await settle(500);
    }
    await settle(2500);
    bootHash = await hash();
    const title = await page.title();
    const windows = await app.evaluate(async ({ BrowserWindow }) => BrowserWindow.getAllWindows().length);
    V('boot', { hash: bootHash, title, windows });

    /* ---------------- P2 sidebar (canonical K + badge + footer) ---------------- */
    const sidebarInfo = async () => page.evaluate(() => {
      const sider = document.querySelector('.layout-sider');
      if (!sider) return { error: 'no .layout-sider' };
      const rect = (el) => { const r = el.getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height }; };
      const img = sider.querySelector('img');
      const badges = Array.from(sider.querySelectorAll('.arco-badge-text, .arco-badge-number')).map((b) => ({ text: b.textContent, ...rect(b) }));
      const svgText = sider.querySelector('svg text');
      return {
        sider: rect(sider),
        img: img ? { src: img.getAttribute('src'), naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight } : null,
        badges,
        hasSvgTextNode: !!svgText,
        siderTextSample: (sider.innerText || '').slice(0, 400),
      };
    });
    await setSize(1440, 960);
    await nav('#/guid', 1200);
    const sbWide = await sidebarInfo();
    await shot('sidebar-1440');
    await setSize(1000, 720);
    await settle(600);
    const sbNarrow = await sidebarInfo();
    await shot('sidebar-1000');
    await setSize(1440, 960);
    await settle(400);
    const badge = sbWide && sbWide.badges && sbWide.badges[0];
    V('sidebar', {
      img: sbWide && sbWide.img,
      badge,
      badgeInsideSider: !!(badge && sbWide && badge.right <= sbWide.sider.right + 1 && badge.left >= -1),
      noSvgText: !(sbWide && sbWide.hasSvgTextNode),
      narrowBadgeInside: !!(sbNarrow && sbNarrow.badges && sbNarrow.badges[0] && sbNarrow.badges[0].right <= sbNarrow.sider.right + 1),
      plainKTextPresent: /(^|\s)K(\s|$)/.test((sbWide && sbWide.siderTextSample || '').replace(/[^\x20-\x7E]/g, ' ')),
    });

    /* ---------------- P3 permissions scrolling at 5 sizes ---------------- */
    const sizes = [[1366, 768], [1440, 900], [1440, 960], [1920, 1080], [1100, 800]];
    const scrollMatrix = [];
    for (const [w, h] of sizes) {
      await setSize(w, h);
      await nav('#/autonomy', 600);
      await waitFor(() => !!document.querySelector('.kel-scope'), 12000);
      await settle(900);
      const info = await page.evaluate(() => {
        const sc = document.querySelector('.kel-scope');
        const de = document.documentElement;
        const rect = sc ? sc.getBoundingClientRect() : null;
        return {
          canScroll: sc ? sc.scrollHeight > sc.clientHeight + 8 : false,
          scrollTop: sc ? sc.scrollTop : -1,
          max: sc ? sc.scrollHeight - sc.clientHeight : -1,
          clientHeight: sc ? sc.clientHeight : -1,
          rect,
          docOverflowX: de.scrollWidth - de.clientWidth,
        };
      });
      let wheelDelta = 0, endTop = -1, homeTop = -1, pageUpDelta = 0, pageDownDelta = 0;
      if (info.rect) {
        await page.mouse.move(info.rect.left + info.rect.width / 2, info.rect.top + info.rect.height / 2);
        await page.mouse.wheel(0, 420);
        await settle(400);
        wheelDelta = (await page.evaluate(() => document.querySelector('.kel-scope').scrollTop)) - info.scrollTop;
      }
      await page.evaluate(() => { const el = document.getElementById('kel-autonomy-main'); if (el) el.focus(); });
      await page.keyboard.press('End'); await settle(450);
      endTop = await page.evaluate(() => document.querySelector('.kel-scope').scrollTop);
      const pageDownBefore = endTop;
      await page.keyboard.press('PageUp'); await settle(450);
      pageUpDelta = pageDownBefore - (await page.evaluate(() => document.querySelector('.kel-scope').scrollTop));
      await page.keyboard.press('PageDown'); await settle(450);
      pageDownDelta = (await page.evaluate(() => document.querySelector('.kel-scope').scrollTop)) - (pageDownBefore - pageUpDelta);
      // bottom visibility: last content row inside viewport when at end
      await page.keyboard.press('End'); await settle(450);
      endTop = await page.evaluate(() => document.querySelector('.kel-scope').scrollTop);
      const bottomReach = await page.evaluate(() => {
        const sc = document.querySelector('.kel-scope');
        const rows = document.querySelectorAll('.kel-table tr, .kel-card');
        const last = rows[rows.length - 1];
        if (!sc || !last) return null;
        const r = last.getBoundingClientRect();
        return { lastBottom: r.bottom, viewportH: window.innerHeight, visible: r.top < window.innerHeight && r.bottom > 0 && r.bottom <= window.innerHeight + 40 };
      });
      await page.keyboard.press('Home'); await settle(450);
      homeTop = await page.evaluate(() => document.querySelector('.kel-scope').scrollTop);
      const dualScroll = await page.evaluate(() => {
        const de = document.documentElement;
        return { htmlScrollTop: de.scrollTop, bodyOverflow: de.scrollHeight - de.clientHeight };
      });
      scrollMatrix.push({ size: w + 'x' + h, canScroll: info.canScroll, initial: info.scrollTop, wheelDelta, endTop, max: info.max, homeTop, pageUpDelta, pageDownDelta, bottomReach, dualScroll, docOverflowX: info.docOverflowX, clientHeight: info.clientHeight });
      if (w === 1366) { await shot('permissions-' + w + 'x' + h + '-top'); }
    }
    V('permissionsScroll', scrollMatrix);
    await shot('permissions-matrix-end');
    // back to 1366x768 for the remaining checks
    await setSize(1366, 768);
    await nav('#/autonomy', 700);

    /* ---------------- P4 permissions language + advanced gating ---------------- */
    await waitFor(() => /Active permissions/.test(document.body.innerText), 12000);
    const permLang = await page.evaluate(() => {
      const t = document.body.innerText || '';
      return {
        text: t.slice(0, 4000),
        hasActive: /Active permissions/.test(t),
        hasRequests: /Access requests/.test(t),
        hasLeaseWord: /\bleases?\b/i.test(t),
        hasSnapshot: /\bsnapshots?\b/i.test(t),
        hasWorker: /\bworkers?\b/i.test(t),
        hasReviewSample: /prepared review sample/i.test(t),
        hasZeroAgo: /0s ago/i.test(t),
        jobIdMatches: (t.match(/job_[a-z0-9_]+/gi) || []).slice(0, 10),
        leaseIdMatches: (t.match(/lease_[a-z0-9_]+/gi) || []).slice(0, 5),
        advBtnPresent: /Advanced details/.test(t),
        permCheckHidden: !/Permission check/.test(t),
        guardrailsHidden: !/Locked guardrails/.test(t),
        emergency: /Emergency stop/.test(t),
      };
    });
    await shot('permissions-language-top');
    const advClicked = await domClick("() => Array.from(document.querySelectorAll('button')).find(b => (b.textContent||'').trim() === 'Advanced details')");
    await settle(800);
    const permAdv = await page.evaluate(() => {
      const t = document.body.innerText || '';
      return { permCheckVisible: /Permission check/.test(t), guardrailsVisible: /Locked guardrails/.test(t), hideBtn: /Hide advanced details/.test(t) };
    });
    await shot('permissions-advanced');
    V('permissionsLanguage', Object.assign(permLang, { advClicked, afterAdvanced: permAdv }));
    // extra observations: expiry correctness on the active row + revoke button states
    const permRow = await page.evaluate(() => {
      const rows = Array.from(document.querySelectorAll('.kel-table tbody tr, .kel-table tr'));
      return rows.slice(0, 4).map((r) => (r.innerText || '').replace(/\s+/g, ' ').slice(0, 180));
    });
    V('permissionsRows', permRow);
    if (advClicked) { await domClick("() => Array.from(document.querySelectorAll('button')).find(b => (b.textContent||'').trim() === 'Hide advanced details')"); await settle(400); }

    /* ---------------- P5 work -> open the chat ---------------- */
    await nav('#/work', 1200);
    await waitFor(() => !!document.querySelector('.kel-attention__row'), 15000);
    await settle(600);
    const attentionRows = await page.evaluate(() => Array.from(document.querySelectorAll('.kel-attention__row')).map((r) => (r.innerText || '').replace(/\s+/g, ' ').slice(0, 220)));
    const openChatCount = await page.evaluate(() => Array.from(document.querySelectorAll('button')).filter((b) => (b.textContent || '').trim() === 'Open the chat').length);
    const opened = [];
    for (let i = 0; i < Math.min(openChatCount, 3); i++) {
      await nav('#/work', 700);
      await waitFor(() => !!document.querySelector('.kel-attention__row'), 12000);
      const clicked = await page.evaluate((idx) => {
        const btns = Array.from(document.querySelectorAll('button')).filter((b) => (b.textContent || '').trim() === 'Open the chat');
        if (!btns[idx]) return false;
        btns[idx].click();
        return true;
      }, i);
      if (!clicked) { opened.push({ index: i, clicked: false }); continue; }
      let h2 = '';
      for (let k = 0; k < 40; k++) { h2 = await hash(); if (h2.startsWith('#/conversation/')) break; await settle(250); }
      await settle(1200);
      const convText = await page.evaluate(() => (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 300));
      const convId = h2.replace('#/conversation/', '');
      opened.push({ index: i, hash: h2, convId, idIsKnownDonor: donorIds.includes(convId), textSample: convText });
      await shot('conversation-' + i + '-' + convId);
      // back/forward sanity
      await page.goBack(); await settle(900);
      const backHash = await hash();
      await page.goForward(); await settle(900);
      const fwdHash = await hash();
      opened[opened.length - 1].backHash = backHash;
      opened[opened.length - 1].forwardHash = fwdHash;
      if (fwdHash.startsWith('#/conversation/')) { await page.goBack(); await settle(500); }
    }
    V('workToChat', { attentionRows: attentionRows.slice(0, 4), openChatCount, opened, expectedMain });
    // manual second conversation render (independence check for conversation routing)
    const secondDonor = convMap['demo-quick'];
    await nav('#/conversation/' + secondDonor, 1500);
    await shot('conversation-manual-' + secondDonor);
    const manualConv = await page.evaluate(() => (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 240));
    V('conversationManual', { donor: secondDonor, hash: await hash(), textSample: manualConv });

    /* markdown / code font floor measurement (rendered) */
    const fonts = await page.evaluate(() => {
      const probe = (v, fallback) => {
        const d = document.createElement('span');
        d.style.fontSize = 'var(' + v + ', ' + fallback + ')';
        document.body.appendChild(d);
        const px = getComputedStyle(d).fontSize;
        d.remove();
        return px;
      };
      return { mdVar: probe('--md-font-size', '16px'), codeVar: probe('--code-font-size', '14px') };
    });
    V('fontFloors', fonts);

    /* ---------------- P6 model page ---------------- */
    await nav('#/settings/model', 1400);
    await waitFor(() => /model/i.test(document.body.innerText), 12000);
    await settle(800);
    const modelInfo = await page.evaluate(() => {
      const t = document.body.innerText || '';
      return {
        textSample: t.slice(0, 1200),
        hasNoConfigured: /No configured models/.test(t),
        hasNoCustomConfigured: /No custom models configured/.test(t),
        hasDefaultCard: /Default Kel model/.test(t),
        hasAvailable: /Available/.test(t),
        hasNeedsSetup: /Needs setup/.test(t),
        hasCurrent: /Current/.test(t),
        availableCount: (t.match(/Available/g) || []).length,
        needsSetupCount: (t.match(/Needs setup/g) || []).length,
        hasAutomatic: /Automatic/.test(t),
      };
    });
    await shot('model');
    V('modelPage', modelInfo);

    /* ---------------- P7 system page ---------------- */
    await nav('#/settings/system', 1400);
    await settle(800);
    const sysBefore = await page.evaluate(() => {
      const t = document.body.innerText || '';
      return { hasAdvancedFolders: /Advanced — folders/.test(t), hasShow: /\bShow\b/.test(t), hasWorkDir: /Work Directory/i.test(t), hasDonorPath: /aionui|kelwork/i.test(t), textSample: t.slice(0, 600) };
    });
    const sysClicked = await domClick("() => Array.from(document.querySelectorAll('button')).find(b => (b.textContent||'').trim() === 'Show')");
    await settle(700);
    const sysAfter = await page.evaluate(() => {
      const t = document.body.innerText || '';
      return { foldersOpenText: /kelwork|Folders|folders/i.test(t), hasHide: /\bHide\b/.test(t), donorPathVisibleNow: /aionui/i.test(t) };
    });
    await shot('system');
    V('systemPage', { before: sysBefore, sysClicked, after: sysAfter });
    if (sysClicked) { await domClick("() => Array.from(document.querySelectorAll('button')).find(b => (b.textContent||'').trim() === 'Hide')"); await settle(400); }

    /* ---------------- P8 appearance ---------------- */
    await nav('#/settings/appearance', 1400);
    await settle(800);
    const appBefore = await page.evaluate(() => {
      const t = document.body.innerText || '';
      return { hasLight: /\bLight\b/.test(t), hasDark: /\bDark\b/.test(t), hasFollow: /Follow System/.test(t), donorText: DONOR_TEST(t), textSample: t.slice(0, 800) };
    }, );
    await shot('appearance');
    // theme switching: click Dark then Light then Follow System (record theme attributes)
    const themeTry = async (label) => {
      const clicked = await domClick("() => { const els = Array.from(document.querySelectorAll('div,span,[role],button')); const cand = els.find(e => (e.textContent||'').trim() === '" + label + "' && e.closest('[class*=card],[class*=theme],[class*=cover]')); if (!cand) return false; cand.click(); return true; }");
      await settle(900);
      const state = await page.evaluate(() => ({
        bodyAttr: document.body.getAttribute('arco-theme'),
        htmlClass: document.documentElement.className.slice(0, 120),
        bg: getComputedStyle(document.body).backgroundColor,
      }));
      return { label, clicked, state };
    };
    const darkTry = await themeTry('Dark');
    const lightTry = await themeTry('Light');
    const followTry = await themeTry('Follow System');
    V('appearancePage', { before: appBefore, darkTry, lightTry, followTry });

    /* ---------------- P9 tools page ---------------- */
    await nav('#/settings/tools', 1400);
    await settle(800);
    const toolsInfo = await page.evaluate(() => {
      const t = document.body.innerText || '';
      return {
        textSample: t.slice(0, 1000),
        hasKelBrowser: /Kel Browser/.test(t),
        hasDonorBrowserId: /aionui-browser/i.test(t),
        hasChromeDevtools: /chrome-devtools/i.test(t),
        donorAny: DONOR_TEST(t),
      };
    });
    await shot('tools');
    V('toolsPage', toolsInfo);

    /* ---------------- P10 desktop pet truthfulness ---------------- */
    await nav('#/settings/pet', 1400);
    await waitFor(() => !!document.querySelector('.arco-switch:not(.arco-switch-disabled)'), 15000);
    await settle(1200);
    const petBefore = await page.evaluate(() => {
      const sw = Array.from(document.querySelectorAll('[role=switch], .arco-switch')).map((s) => ({ checked: s.getAttribute('aria-checked'), cls: s.className.slice(0, 60), disabled: s.className.includes('disabled') }));
      const t = document.body.innerText || '';
      return { switches: sw, textSample: t.slice(0, 500) };
    });
    const petClicked = await domClick("() => { const s = document.querySelector('.arco-switch'); if (s) { s.click(); return true; } return false; }");
    await settle(1800);
    const petAfter = await page.evaluate(() => {
      const s = document.querySelector('.arco-switch');
      const msgs = Array.from(document.querySelectorAll('.arco-message, .arco-message-content')).map((m) => (m.innerText || '').trim()).filter(Boolean);
      const others = Array.from(document.querySelectorAll('[role=switch], .arco-switch')).map((x) => ({ checked: x.getAttribute('aria-checked'), disabled: x.className.includes('disabled') }));
      const radios = Array.from(document.querySelectorAll('.arco-radio')).map((r) => ({ checked: r.className.includes('checked'), disabled: r.className.includes('disabled') }));
      return { firstChecked: s ? s.getAttribute('aria-checked') : null, msgs, switches: others, radios };
    });
    await shot('pet-after-refusal');
    await nav('#/guid', 800);
    await nav('#/settings/pet', 1400);
    await settle(1200);
    const petReload = await page.evaluate(() => {
      const s = document.querySelector('.arco-switch');
      return { firstChecked: s ? s.getAttribute('aria-checked') : null };
    });
    let petConfig = null;
    try {
      const raw = fs.readFileSync(path.join(rootDir, 'kelwork', 'host', 'config', 'aionui-config.txt'), 'utf8').trim();
      const decoded = Buffer.from(raw, 'base64').toString('utf8');
      const m = decoded.match(/"pet\.enabled":(true|false)/);
      petConfig = m ? m[1] : 'unparsed';
    } catch (e) { petConfig = 'unreadable: ' + String(e && e.message); }
    const winCount = await app.evaluate(async ({ BrowserWindow }) => BrowserWindow.getAllWindows().length);
    V('desktopPet', { before: petBefore, clicked: petClicked, after: petAfter, reloadChecked: petReload.firstChecked, persisted: petConfig, windowCount: winCount });

    /* ---------------- P11 hidden routes ---------------- */
    const routeResults = {};
    for (const r of ['#/team', '#/team/office', '#/team/roster', '#/team/studio', '#/settings/skills-hub', '#/settings/agent', '#/settings/assistants', '#/settings/capabilities']) {
      await nav(r, 900);
      routeResults[r] = await hash();
    }
    await settle(300);
    const siderText = await page.evaluate(() => (document.querySelector('.layout-sider') ? document.querySelector('.layout-sider').innerText : '').toLowerCase());
    const navWords = { team: /\bteam\b/.test(siderText), roster: /\broster\b/.test(siderText), office: /\boffice\b/.test(siderText), studio: /\bstudio\b/.test(siderText) };
    V('hiddenRoutes', { redirects: routeResults, sidebarWords: navWords });
    await nav('#/settings/appearance', 900);
    const settingsSider = await page.evaluate(() => {
      const el = document.querySelector('.settings-sider, [class*=settings] [class*=sider]');
      return el ? el.innerText.slice(0, 600) : null;
    });
    V('settingsSider', { text: settingsSider, hasAgents: /agents/i.test(settingsSider || ''), hasSkills: /skills/i.test(settingsSider || ''), hasTeam:/team/i.test(settingsSider || '') });

    /* ---------------- P12 about ---------------- */
    await nav('#/settings/about', 1400);
    await settle(900);
    const aboutInfo = await page.evaluate(() => {
      const imgs = Array.from(document.querySelectorAll('img')).map((i) => ({ src: (i.getAttribute('src') || '').slice(0, 120), w: i.naturalWidth, h: i.naturalHeight }));
      const t = document.body.innerText || '';
      return { imgs: imgs.filter((i) => i.w > 0).slice(0, 10), donorText: DONOR_TEST(t), hasVersion: /1\.6\.0/.test(t), textSample: t.slice(0, 600) };
    });
    await shot('about');
    V('aboutPage', aboutInfo);

    /* ---------------- P13 donor sweep on visited screens + titles ---------------- */
    const sweepScreens = ['#/guid', '#/work', '#/autonomy', '#/settings/model', '#/settings/system', '#/settings/appearance', '#/settings/tools', '#/settings/pet', '#/settings/webui', '#/settings/archived', '#/settings/about'];
    const sweep = {};
    for (const s of sweepScreens) {
      await nav(s, 900);
      sweep[s] = await page.evaluate(() => {
        const t = document.body.innerText || '';
        return { donor: DONOR_TEST(t), title: document.title };
      });
    }
    V('donorSweep', sweep);

    /* ---------------- P14 narrow + zoom overflow ---------------- */
    await setSize(1100, 800);
    const narrow = {};
    for (const s of ['#/work', '#/autonomy', '#/settings/model', '#/settings/system', '#/settings/appearance', '#/settings/tools', '#/settings/pet']) {
      await nav(s, 800);
      narrow[s] = await page.evaluate(() => window.document.documentElement.scrollWidth - window.document.documentElement.clientWidth);
    }
    V('narrowOverflow', narrow);
    await setSize(1366, 768);
    await setZoom(1.25);
    const zoom = {};
    for (const s of ['#/work', '#/autonomy', '#/settings/model']) {
      await nav(s, 800);
      zoom[s] = await page.evaluate(() => ({ ovx: window.document.documentElement.scrollWidth - window.document.documentElement.clientWidth, innerW: window.innerWidth }));
    }
    await setZoom(1.0);
    V('zoom125', zoom);

    /* ---------------- finalize ---------------- */
    R.finishedAt = new Date().toISOString();
    fs.writeFileSync(path.join(outDir, 'reaudit-probes.json'), JSON.stringify(R, null, 2));
    fs.writeFileSync(path.join(outDir, 'reaudit-probes-summary.txt'), buildSummary(R));
    console.log('=== REAUDIT PROBES DONE ===');
    console.log(buildSummary(R));
  } catch (fatal) {
    R.fatal = String((fatal && fatal.stack) || fatal);
    try { fs.writeFileSync(path.join(outDir, 'reaudit-probes.json'), JSON.stringify(R, null, 2)); } catch (e) {}
    console.log('=== REAUDIT PROBES FATAL ===');
    console.log(R.fatal);
  } finally {
    try { await app.close(); } catch (e) {}
  }
})().catch((e) => { console.error('probe crashed:', e); process.exit(1); });

/* NOTE: DONOR_TEST is referenced inside page.evaluate bodies — define it as a global on the page
   side by injecting it before probes run. */
async function injectGlobals(page) {
  await page.evaluate(() => {
    window.DONOR_TEST = (t) => /aionui|aion core|aioncore|butler/i.test(t || '');
  });
}

function buildSummary(R) {
  const lines = [];
  lines.push('appDir: ' + R.appDir);
  lines.push('rootDir: ' + R.rootDir);
  const p = R.probes;
  if (p.boot) lines.push('boot: ' + JSON.stringify(p.boot));
  if (p.sidebar) lines.push('sidebar: badgeInside=' + p.sidebar.badgeInsideSider + ' noSvgText=' + p.sidebar.noSvgText + ' imgW=' + (p.sidebar.img && p.sidebar.img.naturalWidth));
  if (p.permissionsScroll) for (const row of p.permissionsScroll) lines.push('scroll ' + row.size + ': wheel=' + row.wheelDelta + ' end=' + row.endTop + '/' + row.max + ' home=' + row.homeTop + ' pgup=' + row.pageUpDelta + ' pgdn=' + row.pageDownDelta + ' bottomVisible=' + (row.bottomReach && row.bottomReach.visible) + ' ovx=' + row.docOverflowX);
  if (p.permissionsLanguage) lines.push('permLang: lease=' + p.permissionsLanguage.hasLeaseWord + ' worker=' + p.permissionsLanguage.hasWorker + ' jobIds=' + JSON.stringify(p.permissionsLanguage.jobIdMatches) + ' advAfter=' + JSON.stringify(p.permissionsLanguage.afterAdvanced));
  if (p.workToChat) lines.push('workToChat: buttons=' + p.workToChat.openChatCount + ' opened=' + JSON.stringify(p.workToChat.opened.map((o) => ({ h: o.hash, known: o.idIsKnownDonor, back: o.backHash, fwd: o.forwardHash }))));
  if (p.modelPage) lines.push('model: noConfigured=' + p.modelPage.hasNoConfigured + ' noCustom=' + p.modelPage.hasNoCustomConfigured + ' available=' + p.modelPage.availableCount + ' needsSetup=' + p.modelPage.needsSetupCount);
  if (p.systemPage) lines.push('system: before=' + JSON.stringify(p.systemPage.before && { adv: p.systemPage.before.hasAdvancedFolders, workDir: p.systemPage.before.hasWorkDir, donor: p.systemPage.before.hasDonorPath }) + ' after=' + JSON.stringify(p.systemPage.after));
  if (p.appearancePage) lines.push('appearance: dark=' + JSON.stringify(p.appearancePage.darkTry && p.appearancePage.darkTry.state) + ' light=' + JSON.stringify(p.appearancePage.lightTry && p.appearancePage.lightTry.state));
  if (p.toolsPage) lines.push('tools: kelBrowser=' + p.toolsPage.hasKelBrowser + ' donorId=' + p.toolsPage.hasDonorBrowserId + ' chromeDevtools=' + p.toolsPage.hasChromeDevtools);
  if (p.desktopPet) lines.push('pet: before=' + JSON.stringify(p.desktopPet.before.switches && p.desktopPet.before.switches[0]) + ' after=' + p.desktopPet.after.firstChecked + ' msgs=' + JSON.stringify(p.desktopPet.after.msgs) + ' reload=' + p.desktopPet.reloadChecked + ' persisted=' + p.desktopPet.persisted + ' windows=' + p.desktopPet.windowCount);
  if (p.hiddenRoutes) lines.push('hiddenRoutes: ' + JSON.stringify(p.hiddenRoutes.redirects) + ' siderWords=' + JSON.stringify(p.hiddenRoutes.sidebarWords));
  if (p.aboutPage) lines.push('about: imgs=' + JSON.stringify(p.aboutPage.imgs) + ' donor=' + JSON.stringify(p.aboutPage.donorText));
  if (p.donorSweep) { const bad = Object.entries(p.donorSweep).filter(([k, v]) => v.donor); lines.push('donorSweep hits: ' + JSON.stringify(bad)); }
  if (p.narrowOverflow) lines.push('narrowOverflow: ' + JSON.stringify(p.narrowOverflow));
  if (p.zoom125) lines.push('zoom125: ' + JSON.stringify(p.zoom125));
  lines.push('consoleErrors: ' + R.consoleErrors.length + ' → ' + JSON.stringify(R.consoleErrors.slice(0, 8)));
  lines.push('pageErrors: ' + R.pageErrors.length + ' → ' + JSON.stringify(R.pageErrors.slice(0, 5)));
  return lines.join('\n');
}
