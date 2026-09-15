// Verifies the Kel command palette contract in a packaged candidate:
//   Ctrl+K opens it, `/` opens it in search mode, typing filters engine-derived results,
//   Enter navigates, Escape closes.
// Usage: node verify-palette.cjs <appDir> <dataDir> <outDir>
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
const outDir = path.resolve(process.argv[4] || '.');
fs.mkdirSync(outDir, { recursive: true });

const paletteState = () => ({
  open: Boolean(document.querySelector('#kel-palette-input')),
  options: Array.from(document.querySelectorAll('[role="option"]')).map((el) =>
    (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60)
  ),
  activeOption: (() => {
    const el = document.querySelector('[role="option"][aria-selected="true"]');
    return el ? (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60) : null;
  })(),
  hash: location.hash,
});

(async () => {
  const results = { schema: 1, checks: {}, errors: [] };
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

  try {
    const page = await app.firstWindow({ timeout: 120000 });
    page.on('pageerror', (error) => results.errors.push(String(error).slice(0, 300)));
    await app.evaluate(async ({ BrowserWindow }) => {
      for (const win of BrowserWindow.getAllWindows()) {
        win.setPosition(-32000, -32000);
        win.setSkipTaskbar(true);
      }
    });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(7000);

    results.checks.closedInitially = await page.evaluate(paletteState);

    await page.keyboard.press('Control+k');
    await page.waitForTimeout(1200);
    results.checks.afterCtrlK = await page.evaluate(paletteState);
    await page.screenshot({ path: path.join(outDir, 'palette-open.png') });

    await page.locator('#kel-palette-input').fill('providers');
    await page.waitForTimeout(600);
    results.checks.filtered = await page.evaluate(paletteState);

    await page.keyboard.press('Enter');
    await page.waitForTimeout(1200);
    results.checks.afterEnter = await page.evaluate(paletteState);

    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    await page.keyboard.press('/');
    await page.waitForTimeout(900);
    results.checks.afterSlash = await page.evaluate(paletteState);
    await page.screenshot({ path: path.join(outDir, 'palette-search-mode.png') });

    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    results.checks.afterEscape = await page.evaluate(paletteState);
  } catch (error) {
    results.errors.push(`fatal: ${String(error).slice(0, 400)}`);
  }

  try {
    await Promise.race([app.close(), new Promise((resolve) => setTimeout(resolve, 20000))]);
    results.closeOutcome = 'closed';
  } catch {
    results.closeOutcome = 'close-timeout';
  }
  try {
    const session = JSON.parse(fs.readFileSync(path.join(dataDir, 'desktop-session.json'), 'utf8'));
    if (session.pid) {
      process.kill(session.pid);
      results.engineKilled = true;
    }
  } catch {
    results.engineKilled = false;
  }

  fs.writeFileSync(path.join(outDir, 'palette-evidence.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
  const ok =
    results.checks.closedInitially?.open === false &&
    results.checks.afterCtrlK?.open === true &&
    results.checks.filtered?.options?.some((label) => /Providers/i.test(label)) &&
    String(results.checks.afterEnter?.hash || '').includes('/providers') &&
    results.checks.afterSlash?.open === true &&
    results.checks.afterEscape?.open === false &&
    results.errors.length === 0;
  if (!ok) process.exitCode = 1;
})();
