/** Native desktop smoke; uses only the owned shell scratch data root. */
import { test, expect, _electron as electron } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

test('built Electron shell keeps native settings connected', async () => {
  test.skip(process.env.KEL_SHELL_NATIVE !== '1', 'Set KEL_SHELL_NATIVE=1 and KEL_SHELL_BACKEND for native verification.');
  test.setTimeout(180_000);
  const root = path.resolve(__dirname, '../../..');
  const scratch = path.join(root, '.shell-run/electron');
  const evidence = process.env.KEL_SHELL_EVIDENCE || path.join(root, 'docs/v2/evidence/shell');
  fs.mkdirSync(scratch, { recursive: true });
  const app = await electron.launch({
    executablePath: path.join(root, 'desktop/node_modules/electron/dist/electron.exe'),
    args: [path.join(root, 'desktop/out/main/index.js')],
    cwd: path.join(root, 'desktop'),
    env: { ...process.env, AIONUI_E2E_TEST: '1', AIONUI_E2E_USER_DATA_DIR: scratch,
      KEL_HOST_DATA_DIR: scratch, KEL_DATA_DIR: path.join(root, '.shell-run/engine'),
      KEL_SOURCE_ROOT: path.join(root, 'runtime'), AIONUI_BACKEND_BIN: process.env.KEL_SHELL_BACKEND!,
      KEL_SKIP_TELEMETRY: '1', AIONUI_DISABLE_AUTO_UPDATE: '1' },
  });
  try {
    const page = await app.firstWindow();
    await app.evaluate(({ BrowserWindow }) => { for (const win of BrowserWindow.getAllWindows()) { win.hide(); win.setContentSize(1440, 900); } });
    await expect(page.locator('.kel-v2-shell')).toBeVisible({ timeout: 90_000 });
    const skip = page.getByRole('button', { name: 'Skip setup', exact: true });
    await page.waitForTimeout(1000);
    if (await skip.count()) { await skip.click(); await expect(page.getByTestId('guid-input')).toBeVisible(); }
    await page.waitForTimeout(500);
    await page.evaluate(() => { location.hash = '/settings/appearance'; });
    await page.getByTestId('theme-card-dark').click();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(3500);
    for (const [name, route] of Object.entries({ home: '/guid', remote: '/settings/webui', system: '/settings/system', pet: '/settings/pet', about: '/settings/about' })) {
      await page.evaluate(route => { location.hash = route; }, route);
      await page.waitForTimeout(900);
      await page.screenshot({ path: path.join(evidence, `electron-${name}.png`) });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    }
    await expect(page.getByText(/Electron \d+ · React/)).toBeVisible();
    await page.evaluate(() => { location.hash = '/settings/system'; });
    await expect(page.getByTestId('data-folder-path')).toContainText('.shell-run');
    expect((await page.locator('.settings-page-content').boundingBox())?.x).toBe(388);
    await page.evaluate(() => { location.hash = '/guid'; });
    await page.keyboard.press('Control+Shift+F');
    await expect(page.getByText('Click the part of Kel that bothered you', { exact: false })).toBeVisible();
    await page.keyboard.press('Escape');
  } catch (error) {
    const page = app.windows()[0];
    if (page) { await page.screenshot({ path: path.join(evidence, 'electron-failure.png') }); fs.writeFileSync(path.join(root, '.shell-run/electron-failure.txt'), await page.locator('body').innerText()); }
    throw error;
  } finally { await app.close(); }
});
