// Asserts the first-run onboarding rule with two launches:
//   1. a genuinely fresh data root  -> the shell lands on /onboarding
//   2. the same root after finishing -> the shell does NOT land on /onboarding again (flag persisted)
//   3. the migrated fixture root (already has conversations) -> never interrupted
// Usage: node verify-onboarding.cjs <appDir> <freshDataDir> <migratedDataDir> <outDir>
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
const freshDir = path.resolve(process.argv[3] || '');
const migratedDir = path.resolve(process.argv[4] || '');
const outDir = path.resolve(process.argv[5] || '.');
fs.mkdirSync(outDir, { recursive: true });

async function launchAndRead(dataDir, { finish = false } = {}) {
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
  const result = { hash: null, onboardingRendered: false, clicked: false, text: null, errors: [] };
  try {
    const page = await app.firstWindow({ timeout: 120000 });
    page.on('pageerror', (error) => result.errors.push(String(error).slice(0, 250)));
    await page.setViewportSize({ width: 1440, height: 900 });
    // The first-run gate polls the engine for up to ~6s while it starts, so sample the route over time
    // instead of judging at a fixed instant — the timeline is the evidence.
    result.timeline = [];
    for (let tick = 0; tick < 40; tick += 1) {
      const hash = await page.evaluate(() => location.hash);
      if (result.timeline[result.timeline.length - 1] !== hash) result.timeline.push(hash);
      if (tick >= 8 && hash.includes('/onboarding')) break;
      await page.waitForTimeout(500);
    }
    result.hash = result.timeline[result.timeline.length - 1] || null;
    result.onboardingRendered = await page.evaluate(
      () =>
        Boolean(document.querySelector('#kel-onboarding-main')) ||
        Boolean(document.body.innerText.includes('Step 1') || document.body.innerText.includes('Set up Kel'))
    );
    result.text = (await page.evaluate(() => document.body.innerText)).slice(0, 400);
    if (finish && result.onboardingRendered) {
      // Click through whatever the flow offers (Next → … → Start using Kel) and judge success by the
      // route leaving /onboarding, so the assertion does not depend on step wording.
      for (let i = 0; i < 8; i += 1) {
        const next = page
          .getByRole('button', { name: /Next|Continue|Start using Kel|Skip for now/i })
          .first();
        if (!(await next.count())) break;
        await next.click({ timeout: 10000 });
        await page.waitForTimeout(900);
        const hash = await page.evaluate(() => location.hash);
        if (!hash.includes('/onboarding')) break;
      }
      result.clicked = true;
      await page.waitForTimeout(2500);
      result.hashAfterFinish = await page.evaluate(() => location.hash);
    }
    await page.screenshot({ path: path.join(outDir, `onboarding-${path.basename(dataDir)}.png`) });
  } catch (error) {
    result.errors.push(`fatal: ${String(error).slice(0, 300)}`);
  }
  try {
    await Promise.race([app.close(), new Promise((resolve) => setTimeout(resolve, 20000))]);
    result.closeOutcome = 'closed';
  } catch {
    result.closeOutcome = 'close-timeout';
  }
  try {
    const session = JSON.parse(fs.readFileSync(path.join(dataDir, 'desktop-session.json'), 'utf8'));
    if (session.pid) {
      process.kill(session.pid);
      result.engineKilled = true;
    }
  } catch {
    result.engineKilled = false;
  }
  return result;
}

(async () => {
  fs.rmSync(path.join(freshDir), { recursive: true, force: true });
  fs.mkdirSync(freshDir, { recursive: true });

  const results = { schema: 1, checks: {}, errors: [] };
  results.checks.freshFirstLaunch = await launchAndRead(freshDir, { finish: true });
  results.checks.freshSecondLaunch = await launchAndRead(freshDir);
  results.checks.migratedLaunch = await launchAndRead(migratedDir);

  fs.writeFileSync(path.join(outDir, 'onboarding-evidence.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));

  const ok =
    String(results.checks.freshFirstLaunch.hash || '').includes('/onboarding') &&
    results.checks.freshFirstLaunch.clicked === true &&
    !String(results.checks.freshSecondLaunch.hash || '').includes('/onboarding') &&
    !String(results.checks.migratedLaunch.hash || '').includes('/onboarding') &&
    results.checks.migratedLaunch.errors.length === 0;
  if (!ok) process.exitCode = 1;
})();
