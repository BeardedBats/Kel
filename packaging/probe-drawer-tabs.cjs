// Resolves the drawer-tab semantics question by inspecting the real DOM: what are the focused tab
// elements, do they carry roles, and what do their parents look like?
// Usage: node probe-drawer-tabs.cjs <appDir> <dataDir> [hash]
const fs = require('fs');
const path = require('path');

let playwright;
try {
  playwright = require('playwright');
} catch (error) {
  playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
}
const { _electron: electron } = playwright;

const appDir = path.resolve(process.argv[2] || '.');
const dataDir = path.resolve(process.argv[3] || '');
const rawHash = process.argv[4] || '/work';
const hash =
  rawHash.includes('\\') || rawHash.includes(':')
    ? '/' + rawHash.split(/[\\/]/).filter(Boolean).pop()
    : rawHash;

const INSPECT = () => {
  const describe = (el) => ({
    tag: el.tagName,
    role: el.getAttribute('role'),
    tabindex: el.getAttribute('tabindex'),
    ariaSelected: el.getAttribute('aria-selected'),
    ariaControls: el.getAttribute('aria-controls'),
    className: String(el.className).slice(0, 90),
    text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 30),
  });
  const candidates = Array.from(
    document.querySelectorAll('[tabindex]:not([tabindex="-1"]), [role="tab"], [role="tablist"] button')
  );
  const tablish = candidates.filter((el) =>
    /work|saved|continue|knowledge|map|recipes/i.test((el.textContent || '').slice(0, 40))
  );
  return {
    tablistNodes: Array.from(document.querySelectorAll('[role="tablist"]')).map(describe),
    tabNodes: Array.from(document.querySelectorAll('[role="tab"]')).map(describe),
    focusedLikeTabs: tablish.slice(0, 8).map((el) => ({
      ...describe(el),
      parent: el.parentElement ? describe(el.parentElement) : null,
      grandparent: el.parentElement?.parentElement ? describe(el.parentElement.parentElement) : null,
    })),
    arcoTabCount: document.querySelectorAll('.arco-tabs-header-title').length,
  };
};

(async () => {
  const packaged = fs.existsSync(path.join(appDir, 'Kel.exe'));
  const app = await electron.launch({
    executablePath: packaged
      ? path.join(appDir, 'Kel.exe')
      : path.join(path.resolve(__dirname, '..'), 'desktop', 'node_modules', 'electron', 'dist', 'electron.exe'),
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
    args: packaged
      ? ['--no-sandbox', '--window-position=-32000,-32000']
      : [appDir, '--no-sandbox', '--window-position=-32000,-32000'],
  });
  const out = { schema: 1, hash };
  try {
    const page = await app.firstWindow({ timeout: 120000 });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(8000);
    await page.evaluate((route) => {
      location.hash = route;
    }, hash);
    await page.waitForTimeout(2200);
    // Open the work drawer the way the app does, so the tab strip is mounted.
    const trigger = page.getByText('Work & context', { exact: false }).first();
    if (await trigger.count()) {
      await trigger.click({ timeout: 10000 }).catch(() => undefined);
      await page.waitForTimeout(1800);
    }
    out.inspect = await page.evaluate(INSPECT);
  } catch (error) {
    out.error = String(error).slice(0, 300);
  }
  try {
    await Promise.race([app.close(), new Promise((resolve) => setTimeout(resolve, 15000))]);
  } catch {
    /* bounded */
  }
  try {
    const session = JSON.parse(fs.readFileSync(path.join(dataDir, 'desktop-session.json'), 'utf8'));
    if (session.pid) process.kill(session.pid);
  } catch {
    /* nothing to kill */
  }
  console.log(JSON.stringify(out, null, 2));
})();
