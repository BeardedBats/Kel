// Playwright-driven UI verification for the packaged Kel application.
// Usage: NODE_PATH=<node_modules-with-playwright> node verify-packaged-ui.cjs <app-dir> <data-dir>
// Opens the real Kel.exe, drives the Work & context drawer, and reports the five
// sections, empty states, recipe preview, and renderer console errors as JSON.
const path = require('path');
const fs = require('fs');
let playwright;
try {
  playwright = require('playwright');
} catch (error) {
  playwright = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
}
const { _electron: electron } = playwright;

(async () => {
  const appDir = path.resolve(process.argv[2]);
  const dataDir = path.resolve(process.argv[3]);
  fs.mkdirSync(dataDir, { recursive: true });
  const exe = path.join(appDir, 'Kel.exe');
  const errors = [];
  const app = await electron.launch({
    executablePath: exe,
    cwd: appDir,
    env: {
      ...process.env,
      KEL_DATA_DIR: dataDir,
      KEL_SKIP_TELEMETRY: '1',
      ELECTRON_ENABLE_LOGGING: '1',
    },
  });
  const page = await app.firstWindow();
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('pageerror', (error) => errors.push(String(error)));
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(8000);

  const checks = {};
  checks.title = await page.title();
  const trigger = page.locator('text=Work & context').first();
  checks.workButton = await trigger.count();
  if (checks.workButton > 0) {
    await trigger.click();
    await page.waitForTimeout(1500);
    for (const label of ['Work', 'Continue work', 'Project knowledge', 'Project map', 'Recipes', 'Saved context', 'Saved history']) {
      checks['tab:' + label] = await page.locator(`text=${label}`).count();
    }
    await page.locator('text=Continue work').first().click();
    await page.waitForTimeout(900);
    checks.continueEmpty = await page.locator('text=No unfinished work in this project.').count();
    await page.locator('text=Project knowledge').first().click();
    await page.waitForTimeout(900);
    checks.knowledgeEmpty = await page.locator('text=No saved project knowledge yet.').count();
    await page.locator('text=Project map').first().click();
    await page.waitForTimeout(900);
    checks.mapEmpty = await page.locator('text=No project map yet. Refresh to build one.').count();
    const refresh = page.locator('button:has-text("Refresh map")').first();
    if (await refresh.count()) {
      await refresh.click();
      await page.waitForTimeout(1800);
      checks.mapRefreshMessage = await page.locator('text=no root').count()
        + await page.locator('text=Project has no root').count();
    }
    await page.locator('text=Recipes').first().click();
    await page.waitForTimeout(900);
    checks.recipeFixBug = await page.locator('text=Fix Bug').count();
    checks.recipeContinueWork = await page.locator('text=Continue Work').count();
    const preview = page.locator('button:has-text("Preview")').first();
    if (await preview.count()) {
      await preview.click();
      await page.waitForTimeout(1500);
      checks.previewShown = await page.locator('pre').count();
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }
  checks.consoleErrors = errors.slice(0, 6);
  console.log(JSON.stringify({ schema: 1, checks }, null, 2));
  await app.close();
  process.exit(0);
})().catch((error) => {
  console.error('UI-CHECK-FAILED', String(error));
  process.exit(1);
});
