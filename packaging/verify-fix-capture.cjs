/**
 * V2.0 preflight — the installed Fix Capture journeys.
 *
 * Drives the app that is actually installed (its own bundled engine, its own data root) over CDP and
 * runs the five journeys Nick asked for, plus the honesty checks: no console errors, no orphaned
 * engine process, no raw internal ids on the surface, no donor terms, no horizontal overflow.
 *
 * The machine this runs on has no microphone, so the app is launched with Chromium's synthetic audio
 * device (`--use-fake-device-for-media-stream`). That is a *test-only* launch flag: the recording
 * path, the transcription family and the store are the shipped ones; only the audio source is fake.
 * With no transcription key the engine answers from its own practice provider, so the transcript text
 * is deterministic — the journeys verify the flow and the storage, not transcription accuracy.
 *
 * Usage: node packaging/verify-fix-capture.cjs [--keep-open]
 */
const path = require('path');
const fs = require('fs');
const net = require('net');
const { spawn, execFileSync } = require('child_process');

function loadPlaywright() {
  const candidates = [
    path.join(__dirname, '..', 'desktop', 'node_modules', 'playwright'),
    path.join(__dirname, '..', '..', 'desktop', 'node_modules', 'playwright'),
  ];
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch {
      /* try next */
    }
  }
  throw new Error('playwright not found under desktop/node_modules');
}

const INSTALL_DIR = process.env.KEL_FC_INSTALL_DIR || 'C:\\Users\\Nick\\KelDogfoodCandidate';
const APP_EXE = path.join(INSTALL_DIR, 'Kel.exe');
const DATA_ROOT = process.env.KEL_FC_DATA_ROOT || 'C:\\Users\\Nick\\KelDogfoodRuns\\prepared\\engine';
const OUT_DIR = path.resolve(__dirname, '..', 'docs', 'daily-driver', 'evidence', 'fix-capture');
const KEEP_OPEN = process.argv.includes('--keep-open');

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

async function waitForCdp(port, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return await response.json();
    } catch {
      /* not up yet */
    }
    await wait(500);
  }
  throw new Error(`CDP endpoint never came up on ${port}`);
}

async function findMainWindow(browser, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const context of browser.contexts()) {
      for (const page of context.pages()) {
        const url = page.url();
        if (url.startsWith('devtools://') || url === 'about:blank') continue;
        return page;
      }
    }
    await wait(500);
  }
  throw new Error('the app window never appeared');
}

/** Start the installed app with the synthetic microphone and one debugging port. */
async function launchApp(port, logName) {
  const log = fs.createWriteStream(path.join(OUT_DIR, logName));
  const child = spawn(
    APP_EXE,
    [
      `--remote-debugging-port=${port}`,
      '--use-fake-device-for-media-stream',
      '--use-fake-ui-for-media-stream',
    ],
    { env: { ...process.env, KEL_DATA_DIR: DATA_ROOT }, stdio: ['ignore', 'pipe', 'pipe'] }
  );
  child.stdout.pipe(log);
  child.stderr.pipe(log);
  return child;
}

async function attach(port, consoleErrors) {
  const { chromium } = loadPlaywright();
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const page = await findMainWindow(browser);
  page.setDefaultTimeout(20000);
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text().slice(0, 300));
  });
  page.on('pageerror', (error) => consoleErrors.push(('pageerror: ' + (error.message || error)).slice(0, 300)));
  await page.waitForLoadState('domcontentloaded');
  await wait(2500);
  return { browser, page };
}

async function stopApp(child, browser) {
  if (browser) await browser.close().catch(() => {});
  if (child) {
    spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
    await wait(2500);
  }
}

/** The engine's own record: every fix, and the files its screenshots point at. */
function engineFacts() {
  const script = [
    'import json, pathlib, sqlite3, struct, sys',
    "root = pathlib.Path(sys.argv[1])",
    "con = sqlite3.connect(f'file:{(root / 'kel.sqlite3').as_posix()}?mode=ro', uri=True)",
    'con.row_factory = sqlite3.Row',
    "rows = [dict(r) for r in con.execute('SELECT * FROM dogfood_fixes ORDER BY id')]",
    'out = []',
    'for row in rows:',
    "    shot = row.get('screenshot') or ''",
    "    file = (root / shot) if shot else None",
    "    info = {'exists': bool(file and file.is_file())}",
    '    if info[\'exists\']:',
    "        raw = file.read_bytes()[:24]",
    "        width, height = struct.unpack('>II', raw[16:24])",
    "        info.update(width=width, height=height, bytes=len(file.read_bytes()))",
    '    out.append({**row, \'shot_file\': info})',
    "print(json.dumps({'fixes': out}))",
  ].join('\n');
  try {
    return JSON.parse(execFileSync('python', ['-c', script, DATA_ROOT], { encoding: 'utf8' }));
  } catch (error) {
    // A data root that has never seen a fix has no table yet — that is not a failure.
    const message = String((error && error.message) || error);
    return { error: message.includes('no such table') ? null : message, fixes: [] };
  }
}

/** Press the hotkey until the overlay appears (the shell mounts the layer asynchronously). */
async function openCapture(page, attempts = 6) {
  for (let index = 0; index < attempts; index += 1) {
    await page.keyboard.press('Control+Shift+F');
    try {
      await page.waitForSelector('[data-testid="fix-capture-overlay"]', { timeout: 2500 });
      return true;
    } catch {
      await wait(1200);
    }
  }
  throw new Error('Ctrl+Shift+F never opened the capture overlay');
}

/** One full capture through the UI, exactly as Nick would do it. */
async function captureFix(page, targetSelector, options = {}) {
  const { again = false, cancel = false } = options;
  await openCapture(page);
  await page.click(targetSelector);
  await page.waitForSelector('[data-testid="fix-capture-panel"][data-phase="recording"]', { timeout: 20000 });
  await wait(2200);
  if (cancel) {
    // Far from the selected target: a deliberate cancel, never a save.
    await page.mouse.click(3, 3);
    await page.waitForSelector('[data-testid="fix-capture-panel"]', { state: 'detached', timeout: 15000 });
    return null;
  }
  await page.keyboard.press('Control+Shift+F');
  await page.waitForSelector('[data-testid="fix-capture-panel"][data-phase="review"]', { timeout: 25000 });
  if (again) {
    await page.click('[data-testid="fix-capture-again"]');
    await page.waitForSelector('[data-testid="fix-capture-panel"][data-phase="recording"]', { timeout: 20000 });
    await wait(2200);
    await page.click('[data-testid="fix-capture-stop"]');
    await page.waitForSelector('[data-testid="fix-capture-panel"][data-phase="review"]', { timeout: 25000 });
  }
  const transcript = await page.inputValue('[data-testid="fix-capture-transcript"]');
  if (options.screenshotName) await page.screenshot({ path: path.join(OUT_DIR, options.screenshotName) });
  await page.click('[data-testid="fix-capture-save"]');
  const panel = page.locator('[data-testid="fix-capture-panel"]');
  await panel.locator('text=/Saved as FIX-/').first().waitFor({ timeout: 25000 });
  const savedText = (await panel.innerText()).replace(/\s+/g, ' ').trim();
  const id = (savedText.match(/FIX-\d+/) || [null])[0];
  return { id, transcript, savedText };
}

async function goto(page, hash) {
  await page.evaluate((target) => {
    location.hash = target;
  }, hash);
  await wait(1800);
}

const bodyText = (page) => page.evaluate(() => document.body.innerText);

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.mkdirSync(DATA_ROOT, { recursive: true });
  if (!fs.existsSync(APP_EXE)) throw new Error(`installed app missing: ${APP_EXE}`);

  const results = {
    startedAt: new Date().toISOString(),
    installDir: INSTALL_DIR,
    appExe: APP_EXE,
    dataRoot: DATA_ROOT,
    fakeMicrophone: true,
    journeys: {},
    consoleErrors: [],
    checks: {},
  };

  let port = await freePort();
  let child = await launchApp(port, 'app-journeys.log');
  let session = null;
  try {
    await waitForCdp(port);
    session = await attach(port, results.consoleErrors);
    let { page } = session;

    const before = engineFacts();
    results.fixesBefore = before.fixes?.length ?? 0;

    // ---- Journey A: capture a Settings element, save, restart, still there -------------------
    await goto(page, '#/settings/about');
    const first = await captureFix(page, 'button:has-text("Check for updates")', {
      screenshotName: 'journey-a-review.png',
    });
    results.journeys.a = {
      saved: Boolean(first?.id),
      fixId: first?.id ?? null,
      transcriptPresent: Boolean(first?.transcript?.trim()),
      transcript: first?.transcript ?? '',
    };

    await stopApp(child, session.browser);
    session = null;
    port = await freePort();
    child = await launchApp(port, 'app-restart.log');
    await waitForCdp(port);
    session = await attach(port, results.consoleErrors);
    page = session.page;
    await goto(page, '#/dogfood');
    const afterRestart = await bodyText(page);
    results.journeys.a.survivedRestart = Boolean(first?.id) && afterRestart.includes(first.id);
    results.journeys.a.showsTranscript =
      Boolean(first?.transcript?.trim()) && afterRestart.includes(first.transcript.slice(0, 40));
    await page.screenshot({ path: path.join(OUT_DIR, 'journey-a-after-restart.png') });

    // ---- Journey B: Record Again replaces the words, keeps the target -----------------------
    await goto(page, '#/settings/about');
    const second = await captureFix(page, 'text=v1.7.0-dev', { again: true });
    const afterB = engineFacts().fixes ?? [];
    results.journeys.b = {
      saved: Boolean(second?.id),
      fixId: second?.id ?? null,
      transcriptPresent: Boolean(second?.transcript?.trim()),
      exactlyOneFixForTheCapture: afterB.length === results.fixesBefore + 2,
      transcript: second?.transcript ?? '',
    };

    // ---- Journey C: click outside cancels, nothing saved ------------------------------------
    const countBeforeC = (engineFacts().fixes ?? []).length;
    const tmpDirAfterC = path.join(DATA_ROOT, 'dogfood', 'tmp');
    await goto(page, '#/settings/about');
    const cancelled = await captureFix(page, 'button:has-text("Check for updates")', { cancel: true });
    await wait(1500);
    const countAfterC = (engineFacts().fixes ?? []).length;
    results.journeys.c = {
      cancelled: cancelled === null,
      nothingSaved: countAfterC === countBeforeC,
      panelGone: (await page.locator('[data-testid="fix-capture-panel"]').count()) === 0,
      tempFilesLeft: (fs.existsSync(tmpDirAfterC) ? fs.readdirSync(tmpDirAfterC) : []).length,
    };

    // ---- Journey D: fixes become one prompt, OPEN → BATCHED ---------------------------------
    await goto(page, '#/settings/about');
    const third = await captureFix(page, '[data-testid="kel-about-logo"]');
    const fourth = await captureFix(page, 'text=v1.7.0-dev');
    await goto(page, '#/dogfood');
    const openTabText = await bodyText(page);
    await page.locator('button', { hasText: 'Prepare Fix Prompt' }).first().click();
    await page.waitForSelector('[data-testid="fix-prompt"]', { timeout: 25000 });
    const promptText = await page.inputValue('[data-testid="fix-prompt"]');
    const ids = [third?.id, fourth?.id].filter(Boolean);
    const afterD = engineFacts();
    const batchedIds = (afterD.fixes ?? []).filter((fix) => fix.status === 'BATCHED').map((fix) => fix.id);
    results.journeys.d = {
      prepared: Boolean(promptText),
      newFixIdsInPrompt: ids.filter((id) => promptText.includes(id)).length,
      newFixIdsExpected: ids.length,
      allBatched: ids.every((id) => batchedIds.includes(id)),
      openTabShowedTheNewFixes:
        openTabText.includes(third?.id ?? 'FIX-none') && openTabText.includes(fourth?.id ?? 'FIX-none'),
      promptHasTenInstructions: ['1. ', '10. '].every((marker) => promptText.includes(marker)),
    };
    await page.screenshot({ path: path.join(OUT_DIR, 'journey-d-prompt.png') });

    // ---- Journey E: screenshot + target box describe the real element ------------------------
    const facts = engineFacts();
    const firstRow = (facts.fixes ?? []).find((fix) => fix.id === first?.id) ?? null;
    const element = firstRow?.element ? JSON.parse(firstRow.element) : null;
    const windowInfo = firstRow?.window ? JSON.parse(firstRow.window) : null;
    const scale =
      firstRow?.shot_file?.width && windowInfo?.width ? firstRow.shot_file.width / windowInfo.width : null;
    const boxInside =
      !!element?.rect &&
      !!scale &&
      element.rect.x * scale >= 0 &&
      element.rect.y * scale >= 0 &&
      (element.rect.x + element.rect.width) * scale <= (firstRow?.shot_file?.width ?? 0) + 2 &&
      (element.rect.y + element.rect.height) * scale <= (firstRow?.shot_file?.height ?? 0) + 2;
    results.journeys.e = {
      screenshotExists: Boolean(firstRow?.shot_file?.exists),
      screenshotBytes: firstRow?.shot_file?.bytes ?? 0,
      imageWidth: firstRow?.shot_file?.width ?? 0,
      imageHeight: firstRow?.shot_file?.height ?? 0,
      recordedRoute: firstRow?.route ?? null,
      recordedTag: element?.tag ?? null,
      recordedVersion: firstRow?.version ?? null,
      targetBoxInsideTheImage: boxInside,
      scale,
    };
    // The fixes are Batched now, so the detail lives under that tab.
    await page.locator('button, [role="tab"]', { hasText: 'Batched' }).first().click().catch(() => {});
    await wait(1200);
    const detailToggle = page.locator('button', { hasText: first?.id ?? 'FIX-none' }).first();
    results.journeys.e.detailFound = (await detailToggle.count()) > 0;
    if (results.journeys.e.detailFound) {
      await detailToggle.click();
      await wait(1800);
      const outline = page.locator('[data-testid="fix-shot-target"]').first();
      results.journeys.e.outlineRendered = (await outline.count()) > 0;
      if (results.journeys.e.outlineRendered) {
        const box = await outline.boundingBox();
        results.journeys.e.outlineBox = box ? { width: Math.round(box.width), height: Math.round(box.height) } : null;
        results.journeys.e.outlineHasArea = Boolean(box && box.width > 4 && box.height > 4);
      }
      await page.screenshot({ path: path.join(OUT_DIR, 'journey-e-detail.png') });
    }

    // ---- Surface honesty checks -------------------------------------------------------------
    const dogfoodText = await bodyText(page);
    const sample = (engineFacts().fixes ?? [])[0] ?? null;
    const rawIdsShown = [sample?.conversation, sample?.project_id]
      .filter(Boolean)
      .filter((value) => dogfoodText.includes(String(value)));
    results.checks.dogfoodPage = {
      noRawInternalIds: rawIdsShown.length === 0,
      offenderCount: rawIdsShown.length,
      donorTerms: ['aionui', 'iOfficeAI'].filter((term) =>
        dogfoodText.toLowerCase().includes(term.toLowerCase())
      ),
      horizontalOverflowPx: await page.evaluate(() =>
        Math.max(0, document.documentElement.scrollWidth - window.innerWidth)
      ),
    };
    const promptsDir = path.join(DATA_ROOT, 'dogfood', 'prompts');
    const shotsDir = path.join(DATA_ROOT, 'dogfood', 'screenshots');
    const tmpDir = path.join(DATA_ROOT, 'dogfood', 'tmp');
    results.checks.files = {
      prompts: fs.existsSync(promptsDir) ? fs.readdirSync(promptsDir) : [],
      screenshots: fs.existsSync(shotsDir) ? fs.readdirSync(shotsDir) : [],
      temporaryLeft: fs.existsSync(tmpDir) ? fs.readdirSync(tmpDir) : [],
    };
    const final = engineFacts();
    results.counts = (final.fixes ?? []).reduce((acc, fix) => {
      acc[fix.status] = (acc[fix.status] ?? 0) + 1;
      return acc;
    }, {});
  } finally {
    if (!KEEP_OPEN) await stopApp(child, session?.browser ?? null);
    await wait(1200);
    let processes = '';
    try {
      processes = execFileSync('tasklist', { encoding: 'utf8' });
    } catch {
      processes = '';
    }
    results.orphanEngineProcesses = (processes.match(/KelEngine\.exe/gi) ?? []).length;
    fs.writeFileSync(
      path.join(OUT_DIR, 'installed-journeys.json'),
      JSON.stringify(results, null, 2),
      'utf8'
    );
    console.log(
      JSON.stringify(
        {
          journeys: results.journeys,
          checks: results.checks,
          counts: results.counts,
          orphans: results.orphanEngineProcesses,
        },
        null,
        2
      )
    );
  }
}

main().catch((error) => {
  console.error('JOURNEYS FAILED:', error && error.stack ? error.stack : error);
  process.exit(1);
});
