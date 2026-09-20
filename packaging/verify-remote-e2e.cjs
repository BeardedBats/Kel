/**
 * D3 — real browser verification of the Remote/WebUI surface (aioncore + web-host + built renderer).
 *
 * Proves the actual browser path end to end: login/session lifecycle against the shipped web auth,
 * authenticated API access, logout invalidation, LAN exposure behavior, and phone-width layout.
 *
 * Usage (from the repo root, while `bun run webui --remote --data-dir <fresh>` is running):
 *   KEL_E2E_PORT=25901 KEL_E2E_PASSWORD=<admin pw> [KEL_E2E_LAN_IP=a.b.c.d] \
 *   node packaging/verify-remote-e2e.cjs
 */
const path = require('path');
const fs = require('fs');

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

const PORT = Number(process.env.KEL_E2E_PORT || 25901);
const PASSWORD = process.env.KEL_E2E_PASSWORD || '';
const LAN_IP = process.env.KEL_E2E_LAN_IP || '';
const OUT_DIR = path.resolve(__dirname, '..', 'docs', 'daily-driver', 'evidence', 'd3');
const BASE = `http://127.0.0.1:${PORT}`;

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function launchBrowser(chromium) {
  const attempts = [{ channel: 'msedge' }, { channel: 'chrome' }, {}];
  let lastError;
  for (const options of attempts) {
    try {
      return await chromium.launch({ headless: true, ...options });
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

async function main() {
  const { chromium } = loadPlaywright();
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const results = { base: BASE, startedAt: new Date().toISOString(), checks: {}, consoleErrors: [] };
  const browser = await launchBrowser(chromium);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.on('console', (message) => {
    if (message.type() === 'error') results.consoleErrors.push(message.text().slice(0, 300));
  });
  page.on('pageerror', (error) => results.consoleErrors.push(('pageerror: ' + (error.message || error)).slice(0, 300)));

  // 1) Entry
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await wait(3000);
  results.checks.entryUrl = page.url();
  results.checks.anonymousAuthUser = await page.evaluate(async () => {
    const response = await fetch('/api/auth/user', { credentials: 'include' });
    let body = null;
    try {
      body = await response.json();
    } catch {
      /* non-JSON */
    }
    return { status: response.status, body };
  });
  await page.screenshot({ path: path.join(OUT_DIR, '01-entry.png') });

  // 2) Login (if the page presents the login form)
  const passwordInput = page.locator('input[type="password"]');
  const loginVisible = (await passwordInput.count()) > 0;
  results.checks.loginFormVisible = loginVisible;
  if (loginVisible) {
    if (!PASSWORD) throw new Error('Login required but KEL_E2E_PASSWORD is not set');
    const usernameInput = page.locator('input:not([type="password"])').first();
    await usernameInput.fill('admin');
    await passwordInput.fill(PASSWORD);
    await page.screenshot({ path: path.join(OUT_DIR, '02-login-filled.png') });
    await Promise.all([
      page.waitForFunction(
        () => !window.location.hash.includes('/login') && !window.location.pathname.includes('/login'),
        { timeout: 20000 }
      ),
      passwordInput.press('Enter'),
    ]).catch(() => {});
    await wait(2500);
    results.checks.postLoginUrl = page.url();
    results.checks.loginSucceeded = !/\/login/.test(page.url());
  } else {
    results.checks.postLoginUrl = page.url();
    results.checks.loginSucceeded = true;
    results.checks.noteLoginAutoTrusted = 'No login form shown for this client';
  }
  await page.screenshot({ path: path.join(OUT_DIR, '03-after-login.png'), fullPage: false });

  // 3) Authenticated API access
  const apiProbe = (url, init) =>
    page.evaluate(
      async ([probeUrl, probeInit]) => {
        const response = await fetch(probeUrl, { credentials: 'include', ...(probeInit || {}) });
        let body = null;
        try {
          body = await response.json();
        } catch {
          /* non-JSON */
        }
        return { status: response.status, body };
      },
      [url, init]
    );

  const conversations = await apiProbe('/api/conversations?page_size=5');
  results.checks.conversations = {
    status: conversations.status,
    itemCount: Array.isArray(conversations.body?.items) ? conversations.body.items.length : null,
  };
  const assistants = await apiProbe('/api/assistants');
  results.checks.assistants = {
    status: assistants.status,
    count: Array.isArray(assistants.body) ? assistants.body.length : Array.isArray(assistants.body?.data) ? assistants.body.data.length : null,
  };
  const refresh = await apiProbe('/api/auth/refresh', { method: 'POST' });
  results.checks.refresh = { status: refresh.status };

  // 4) Logout invalidates the session
  const logout = await apiProbe('/logout', { method: 'POST' });
  const afterLogout = await apiProbe('/api/conversations?page_size=1');
  results.checks.logout = { logoutStatus: logout.status, afterLogoutStatus: afterLogout.status };
  if (PASSWORD && loginVisible) {
    // Re-login to leave the session healthy for follow-up checks.
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    await wait(2500);
    const pw2 = page.locator('input[type="password"]');
    if ((await pw2.count()) > 0) {
      await page.locator('input:not([type="password"])').first().fill('admin');
      await pw2.fill(PASSWORD);
      await pw2.press('Enter');
      await wait(2500);
    }
    results.checks.reloginSucceeded = !/\/login/.test(page.url());
  }

  // 5) Phone-width layout
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await wait(3000);
  results.checks.phone = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  await page.screenshot({ path: path.join(OUT_DIR, '04-phone.png') });

  // 6) LAN exposure from a raw client (no cookies)
  if (LAN_IP) {
    try {
      const lanHome = await fetch(`http://${LAN_IP}:${PORT}/`, { signal: AbortSignal.timeout(8000) });
      const lanApi = await fetch(`http://${LAN_IP}:${PORT}/api/conversations?page_size=1`, {
        signal: AbortSignal.timeout(8000),
      });
      results.checks.lan = { homeStatus: lanHome.status, anonymousApiStatus: lanApi.status };
    } catch (error) {
      results.checks.lan = { error: String(error && error.message ? error.message : error) };
    }
  }

  results.finishedAt = new Date().toISOString();
  results.consoleErrorCount = results.consoleErrors.length;
  fs.writeFileSync(path.join(OUT_DIR, 'remote-e2e.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
  await browser.close();
}

main().catch((error) => {
  console.error('D3 REMOTE E2E FAILED:', error && error.stack ? error.stack : error);
  process.exit(1);
});
