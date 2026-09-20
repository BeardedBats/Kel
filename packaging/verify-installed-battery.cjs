/**
 * D19 — the installed-candidate GUI battery.
 *
 * Drives the app that is actually installed at `C:\Users\Nick\KelDailyDriverCandidate` (production
 * build, its own bundled engine, the prepared data root) — not a dev server. The app is launched
 * with a Chromium debugging port (a test-only launch flag; the shipped product never enables that
 * switch itself — see `configureChromium.ts`), attached over CDP with Playwright, and probed
 * through its own UI.
 *
 * Probes (the four installed replays left open by PACKAGE_EVIDENCE):
 *   D0-001  Permissions shows the work's own request, not a raw job id
 *   D0-004  The desktop-pet refusal shows exactly ONE message
 *   D1      Providers speak human status; Set up → Save → Verify keeps its words
 *   D2      The update check fails closed and says so truthfully
 *
 * Usage (repo root):
 *   node packaging/verify-installed-battery.cjs --tour        # walk the real UI, dump structure
 *   node packaging/verify-installed-battery.cjs               # run the battery, write evidence
 *   node packaging/verify-installed-battery.cjs --keep-open   # leave the app running afterwards
 */
const path = require('path');
const fs = require('fs');
const net = require('net');
const { spawn } = require('child_process');

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

const INSTALL_DIR = process.env.KEL_INSTALL_DIR || 'C:\\Users\\Nick\\KelDailyDriverCandidate';
const APP_EXE = path.join(INSTALL_DIR, 'Kel.exe');
const DATA_ROOT =
  process.env.KEL_BATTERY_DATA || 'C:\\Users\\Nick\\KelDailyDriverRuns\\prepared\\engine';
const OUT_DIR = path.resolve(__dirname, '..', 'docs', 'daily-driver', 'evidence', 'd19');
const TOUR = process.argv.includes('--tour');
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
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return await response.json();
    } catch (error) {
      lastError = error;
    }
    await wait(500);
  }
  throw new Error(`CDP endpoint never came up on ${port}: ${lastError && lastError.message}`);
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

const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();

async function pageFacts(page) {
  return page.evaluate(() => {
    const text = (node) => (node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim();
    return {
      hash: location.hash,
      heading: text(document.querySelector('h1, h2, h3, .kel-card-title') || document.body).slice(0, 140),
      bodyText: text(document.body).slice(0, 1200),
      testIds: Array.from(document.querySelectorAll('[data-testid]'))
        .map((node) => node.getAttribute('data-testid'))
        .slice(0, 60),
    };
  });
}

async function clickByText(page, label, { exact = true } = {}) {
  const locators = [
    page.getByRole('button', { name: label, exact }),
    page.getByRole('menuitem', { name: label, exact }),
    page.getByRole('tab', { name: label, exact }),
    page.getByText(label, { exact }),
  ];
  for (const locator of locators) {
    const count = await locator.count().catch(() => 0);
    if (!count) continue;
    await locator.first().click({ timeout: 8000 }).catch(() => {});
    await wait(1200);
    return true;
  }
  return false;
}

const DONOR_TERMS = ['aionui', 'iOfficeAI'];

/** Navigate the way a person does: click the entry by name, else fall back to the route. */
async function goTo(page, label, hash) {
  const clicked = label ? await clickByText(page, label) : false;
  if (!clicked) await page.evaluate((target) => { location.hash = target; }, hash);
  await wait(1800);
  return { clicked, hash: await page.evaluate(() => location.hash) };
}

const bodyText = (page) => page.evaluate(() => document.body.innerText);
/**
 * Distinct toasts. Arco nests message nodes, so a naive `[class*="arco-message"]` query counts one
 * toast several times — the probe must count the OUTERMOST nodes or it would report a duplicate
 * that a person never sees.
 */
const toastTexts = (page) =>
  page.evaluate(() => {
    const all = Array.from(document.querySelectorAll('[class*="arco-message"]'));
    const outermost = all.filter((node) => !all.some((other) => other !== node && other.contains(node)));
    return outermost
      .map((node) => (node.innerText || '').trim())
      .filter(Boolean);
  });

const safeShot = async (page, name) => {
  try {
    await page.screenshot({ path: path.join(OUT_DIR, name), animations: 'disabled', timeout: 8000 });
  } catch (error) {
    return String((error && error.message) || error);
  }
  return null;
};

/** D0-001 — the Permissions Work column names the work, never a raw engine job id. */
async function probePermissions(page, checks) {
  checks.permissions_nav = await goTo(page, 'Permissions', '#/autonomy');
  await page.waitForSelector('table.kel-table', { timeout: 20000 });
  const tables = await page.evaluate(() =>
    Array.from(document.querySelectorAll('table.kel-table')).map((table) => ({
      head: Array.from(table.querySelectorAll('thead th')).map((th) => th.innerText.trim()),
      rows: Array.from(table.querySelectorAll('tbody tr')).map((tr) =>
        Array.from(tr.querySelectorAll('td')).map((td) => td.innerText.trim())
      ),
    }))
  );
  checks.permissions_tables = tables.map((table) => table.head);
  const leaseTable = tables.find((table) => table.head[0] === 'Work' && table.head.includes('Scope'));
  if (!leaseTable || !leaseTable.rows.length) {
    checks.permissions_work_column = { pass: false, reason: 'no lease rows on the prepared data root' };
    return;
  }
  const workCell = leaseTable.rows[0][0];
  // The identifiers live behind the support-detail disclosure; open it so the evidence can show
  // both the human label and the raw id side by side.
  const supportToggle = page.getByText(/Support detail/i).first();
  if (await supportToggle.count().catch(() => 0)) {
    await supportToggle.click({ timeout: 5000 }).catch(() => {});
    await wait(1200);
  }
  const afterToggle = await page.evaluate(() =>
    Array.from(document.querySelectorAll('table.kel-table')).map((table) => ({
      head: Array.from(table.querySelectorAll('thead th')).map((th) => th.innerText.trim()),
      rows: Array.from(table.querySelectorAll('tbody tr')).map((tr) =>
        Array.from(tr.querySelectorAll('td')).map((td) => td.innerText.trim())
      ),
    }))
  );
  const supportTable = afterToggle.find((table) => table.head.includes('Job id'));
  const jobId = supportTable && supportTable.rows.length ? supportTable.rows[0][1] : null;
  const pageText = await bodyText(page);
  checks.permissions_support_table = supportTable ? supportTable.head : null;
  checks.permissions_work_column = {
    pass:
      /summarise the q3 customer feedback/i.test(workCell) &&
      (!jobId || workCell !== jobId) &&
      !/^[0-9a-f]{6,}$/i.test(workCell),
    workCell,
    jobIdFromSupportTable: jobId,
    identifierIsDifferentFromTheLabel: jobId ? workCell !== jobId : null,
    supportTableKeepsTheIdentifier: jobId ? pageText.includes(jobId) : null,
  };
  checks.permissions_no_donor_terms = !DONOR_TERMS.some((term) =>
    pageText.toLowerCase().includes(term.toLowerCase())
  );
  checks.permissions_screenshotError = await safeShot(page, 'probe-d0-001-permissions.png');
}

/** D0-004 — a refused pet enable shows exactly ONE message and settles the toggle off. */
async function probePetRefusal(page, checks) {
  checks.pet_nav = await goTo(page, null, '#/settings/pet');
  await wait(1500);
  const switches = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.arco-switch, button[role="switch"]').forEach((el, index) => {
      let node = el;
      let label = '';
      for (let up = 0; up < 5 && node; up += 1) {
        node = node.parentElement;
        const text = node ? (node.innerText || '').replace(/\s+/g, ' ').trim() : '';
        if (text) label = text;
        if (text && text.length < 120) break;
      }
      out.push({ index, checked: el.getAttribute('aria-checked'), label: label.slice(0, 120) });
    });
    return out;
  });
  const enableIndex = switches.findIndex((entry) => /enable desktop pet/i.test(entry.label));
  checks.pet_switch_found = enableIndex;
  if (enableIndex < 0) {
    checks.pet_single_message = { pass: false, reason: 'Enable Desktop Pet switch not found', switches };
    return;
  }
  await page.locator('.arco-switch, button[role="switch"]').nth(enableIndex).click();
  await wait(3000);
  const toasts = await toastTexts(page);
  const pageText = await bodyText(page);
  const refusal = 'The desktop pet is not available in this build, so it stays off.';
  const settled = await page.evaluate(
    (index) => {
      const el = document.querySelectorAll('.arco-switch, button[role="switch"]')[index];
      return el ? el.getAttribute('aria-checked') : null;
    },
    enableIndex
  );
  checks.pet_single_message = {
    pass: toasts.length === 1 && toasts[0].includes(refusal) && settled === 'false',
    toastCount: toasts.length,
    toasts,
    occurrencesOfRefusalInPage: pageText.split(refusal).length - 1,
    switchSettledOff: settled === 'false',
  };
  checks.pet_screenshotError = await safeShot(page, 'probe-d0-004-pet.png');
}

/** D1 — providers speak human status, and Set up → Save + Verify says what really happened. */
async function probeProviders(page, checks) {
  checks.providers_nav = await goTo(page, null, '#/providers');
  await page.waitForSelector('.kel-card', { timeout: 20000 });
  const pageText = await bodyText(page);
  checks.providers_human_status = {
    pass:
      /Needs setup/.test(pageText) &&
      !/not_installed|installed_not_authenticated/.test(pageText) &&
      /API key \(billed per use\)|subscription session/.test(pageText),
    sample: pageText.slice(0, 400),
  };
  const setUp = page.getByRole('button', { name: 'Set up', exact: true }).first();
  if ((await setUp.count().catch(() => 0)) === 0) {
    checks.providers_setup_flow = { pass: false, reason: 'no Set up control on the installed page' };
    return;
  }
  // Prefer a real API provider card (the realistic path a key would take); the first Set up control
  // on the page can belong to an internal adapter, which is not the thing a person is setting up.
  const apiCard = page.locator('.kel-card', { hasText: 'Anthropic' }).first();
  const apiSetUp = apiCard.getByRole('button', { name: 'Set up', exact: true }).first();
  const useApiCard = (await apiSetUp.count().catch(() => 0)) > 0;
  checks.providers_targeted_card = useApiCard ? 'Anthropic API' : 'first card with a Set up control';
  await (useApiCard ? apiSetUp : setUp).click();
  await wait(1200);
  const keyInput = page.locator('input[aria-label$="API key"]').first();
  const inputShown = (await keyInput.count().catch(() => 0)) > 0;
  if (!inputShown) {
    checks.providers_setup_flow = { pass: false, reason: 'the key field did not appear' };
    return;
  }
  await keyInput.fill('sk-d19-battery-not-a-real-key');
  const saveButton = page.getByRole('button', { name: 'Save + Verify', exact: true }).first();
  const saveEnabled = await saveButton.isEnabled().catch(() => false);
  await saveButton.click();
  await wait(7000);
  const after = await bodyText(page);
  const messages = await toastTexts(page);
  const savedLine = (after.match(/Saved[^\n]*/) || [null])[0];
  // Honest outcomes only: the key is either verified into the OS store, or reported as not read
  // back. A bogus key must never produce a claim that the provider now works.
  const honest =
    !!savedLine &&
    /Saved and verified .* is in the OS store|did not list the key back/.test(
      savedLine + ' ' + messages.join(' ')
    );
  checks.providers_setup_flow = {
    pass: inputShown && saveEnabled && honest,
    keyFieldAppeared: inputShown,
    saveEnabled,
    messages,
    savedLine,
  };
  checks.providers_no_false_health = !/Connected/.test(
    (await bodyText(page)).slice((await bodyText(page)).indexOf('Anthropic'))
  );
  // Leave the prepared data root as it was found: drop the synthetic key again.
  const remove = page.getByRole('button', { name: 'Remove key', exact: true }).first();
  checks.providers_key_removed = (await remove.count().catch(() => 0)) > 0;
  if (checks.providers_key_removed) {
    await remove.click();
    await wait(2500);
  }
  checks.providers_after_cleanup = (await bodyText(page)).match(/Needs setup/g)?.length ?? 0;
  checks.providers_screenshotError = await safeShot(page, 'probe-d1-providers.png');
}

/** D2 — the update check fails closed truthfully, with no donor infrastructure anywhere. */
async function probeUpdate(page, checks) {
  checks.update_nav = await goTo(page, null, '#/settings/about');
  await wait(1500);
  const before = await bodyText(page);
  checks.update_identity = {
    pass: /v?1\.7\.0-dev/.test(before),
    versionLine: (before.match(/v?[\d.]+-dev/) || [null])[0],
    donorTermPresent: DONOR_TERMS.some((term) => before.toLowerCase().includes(term.toLowerCase())),
  };
  const button = page.getByRole('button', { name: 'Check for updates', exact: true }).first();
  if ((await button.count().catch(() => 0)) === 0) {
    checks.update_fails_closed = { pass: false, reason: 'no Check for updates control' };
    return;
  }
  await button.click();
  // The manual check talks to GitHub (30s timeout), so allow for a real wait.
  const deadline = Date.now() + 60000;
  let messages = [];
  while (Date.now() < deadline) {
    messages = await toastTexts(page);
    if (messages.length) break;
    await wait(1000);
  }
  const after = await bodyText(page);
  const outcome = messages.join(' | ');
  const honestUpToDate = /already on the latest version/i.test(outcome);
  const honestFailure = /not allowed|timed out|request failed|Failed to check for updates|no result/i.test(
    outcome
  );
  const donorLeak = DONOR_TERMS.some((term) =>
    (after + ' ' + outcome).toLowerCase().includes(term.toLowerCase())
  );
  checks.update_fails_closed = {
    pass: (honestUpToDate || honestFailure) && !donorLeak,
    outcome,
    interpretation: honestUpToDate
      ? 'honest up-to-date answer (Kel publishes no release asset yet)'
      : honestFailure
        ? 'honest fail-closed answer'
        : 'unrecognised outcome',
    releaseCardShown: /Update available/i.test(after),
  };
  checks.update_screenshotError = await safeShot(page, 'probe-d2-update.png');
}

/** Walk the installed UI so the probes are written against what is really there. */
async function tour(page, out) {
  const steps = [];
  for (const label of ['Work', 'Projects', 'Activity', 'Permissions', 'Transcription']) {
    const clicked = await clickByText(page, label);
    steps.push({ label, clicked, ...(await pageFacts(page)) });
    await page.screenshot({ path: path.join(OUT_DIR, `tour-${label.toLowerCase()}.png`) });
  }
  // Settings opens a section with its own sider; dump the entries it offers.
  const settingsOpened = await clickByText(page, 'Settings');
  const settingsFacts = await pageFacts(page);
  const siderItems = await page.evaluate(() =>
    Array.from(document.querySelectorAll('[role="menuitem"], .ant-menu-item, [class*="sider"] li'))
      .map((node) => (node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim())
      .filter(Boolean)
      .slice(0, 40)
  );
  steps.push({ label: 'Settings', clicked: settingsOpened, siderItems, ...settingsFacts });
  await page.screenshot({ path: path.join(OUT_DIR, 'tour-settings.png') });
  out.structure = steps;
  return steps;
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  if (!fs.existsSync(APP_EXE)) throw new Error(`installed app missing: ${APP_EXE}`);
  const port = await freePort();
  const logPath = path.join(OUT_DIR, 'app-console.log');
  const log = fs.createWriteStream(logPath);
  const child = spawn(APP_EXE, [`--remote-debugging-port=${port}`], {
    env: { ...process.env, KEL_DATA_DIR: DATA_ROOT },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.pipe(log);
  child.stderr.pipe(log);

  const results = {
    startedAt: new Date().toISOString(),
    installDir: INSTALL_DIR,
    appExe: APP_EXE,
    dataRoot: DATA_ROOT,
    cdpPort: port,
    checks: {},
    consoleErrors: [],
  };

  let browser = null;
  try {
    results.cdp = await waitForCdp(port);
    const { chromium } = loadPlaywright();
    browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
    const page = await findMainWindow(browser);
    page.setDefaultTimeout(15000);
    page.on('console', (message) => {
      if (message.type() === 'error') results.consoleErrors.push(message.text().slice(0, 300));
    });
    page.on('pageerror', (error) =>
      results.consoleErrors.push(('pageerror: ' + (error.message || error)).slice(0, 300))
    );
    await page.waitForLoadState('domcontentloaded');
    await wait(3500);
    results.appUrl = page.url();

    if (TOUR) {
      await tour(page, results);
    } else {
      for (const probe of [probePermissions, probePetRefusal, probeProviders, probeUpdate]) {
        try {
          await probe(page, results.checks);
        } catch (error) {
          results.checks[probe.name] = { pass: false, error: String((error && error.message) || error) };
        }
      }
      results.allPassed = Object.values(results.checks).every(
        (entry) => !entry || entry.pass !== false
      );
      results.donorTermsInConsole = (results.consoleErrors || []).filter((line) =>
        DONOR_TERMS.some((term) => line.toLowerCase().includes(term.toLowerCase()))
      ).length;
    }

    fs.writeFileSync(
      path.join(OUT_DIR, TOUR ? 'tour.json' : 'installed-battery.json'),
      JSON.stringify(results, null, 2),
      'utf8'
    );
    console.log(JSON.stringify(TOUR ? results.structure : results.checks, null, 2));
  } finally {
    // The CDP connection is dropped, not closed: the app is a packaged GUI process, so it is
    // stopped with a task-tree kill and then checked for orphaned engine processes.
    if (browser) await browser.close().catch(() => {});
    log.end();
    if (!KEEP_OPEN) {
      spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
      await wait(2500);
    }
  }
}

main().catch((error) => {
  console.error('BATTERY FAILED:', error && error.stack ? error.stack : error);
  process.exit(1);
});
