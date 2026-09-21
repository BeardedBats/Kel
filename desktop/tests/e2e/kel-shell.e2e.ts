/** Built shell verification. Run against an isolated, authenticated WebUI with no provider secrets. */
import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const BASE = process.env.KEL_WEBUI_URL || 'http://127.0.0.1:25819';
const EVIDENCE = process.env.KEL_SHELL_EVIDENCE || path.resolve(__dirname, '../../../docs/v2/evidence/shell');
const state = process.env.KEL_SHELL_STORAGE;
if (state) test.use({ storageState: state });
fs.mkdirSync(EVIDENCE, { recursive: true });
test.beforeEach(async ({ context }) => { await context.clearCookies(); });

async function open(page: Page, route: string) {
  if (!page.url().startsWith(BASE) || !(await page.locator('.kel-v2-shell').count())) {
    await page.goto(`${BASE}/#/guid`);
    await expect(page.locator('.kel-v2-shell, input[name="username"]').first()).toBeVisible();
    if (await page.locator('input[name="username"]').count()) {
      if (!process.env.KEL_DEV_PASSWORD) throw new Error('Supply the isolated WebUI KEL_DEV_PASSWORD.');
      await page.locator('input[name="username"]').fill(process.env.KEL_DEV_USER || 'admin');
      await page.locator('input[name="password"]').fill(process.env.KEL_DEV_PASSWORD);
      await page.getByRole('button', { name: 'Sign In', exact: true }).click();
      await expect(page.locator('.kel-v2-shell')).toBeVisible();
    }
    await page.waitForTimeout(700);
    if (await page.getByRole('button', { name: 'Skip setup', exact: true }).count()) {
      await page.getByRole('button', { name: 'Skip setup', exact: true }).click();
      await expect(page.getByTestId('guid-input')).toBeVisible();
    }
    await page.evaluate(() => { location.hash = '/settings/appearance'; });
    await page.getByTestId('theme-card-dark').click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.waitForTimeout(3500);
  }
  await page.evaluate(route => { location.hash = route; }, route);
  await expect(page.locator('.kel-v2-shell')).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(600);
}

async function record(page: Page, name: string) {
  const geometry = await page.evaluate(() => {
    const root = document.documentElement;
    const boxes = Object.fromEntries(['.layout-sider', '.kel-shell-home-header', '.chat-layout-header', '.sendbox-panel', '.kel-shell-composer', '.kel-page', '.settings-page-content', '.kel-shell-model-modal', '.kel-shell-ramble > aside', '.kel-shell-ramble > main'].map(selector => {
      const el = document.querySelector(selector);
      if (!el) return [selector, null];
      const rect = el.getBoundingClientRect(); const css = getComputedStyle(el);
      return [selector, { x: rect.x, y: rect.y, width: rect.width, height: rect.height, font: css.font, borderRadius: css.borderRadius }];
    }));
    return { width: innerWidth, height: innerHeight, scrollWidth: root.scrollWidth, clientWidth: root.clientWidth, boxes };
  });
  await page.screenshot({ path: path.join(EVIDENCE, `${name}.png`) });
  fs.writeFileSync(path.join(EVIDENCE, `${name}.json`), JSON.stringify(geometry, null, 2));
  expect(geometry.scrollWidth, `${name}: no page overflow`).toBeLessThanOrEqual(geometry.clientWidth + 1);
}

test('desktop surfaces use the built renderer and real state', async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const failures: string[] = [];
  page.on('pageerror', e => failures.push(e.message));
  for (const [name, route] of Object.entries({ home: '/guid', work: '/work', projects: '/projects', activity: '/activity', permissions: '/autonomy', appearance: '/settings/appearance', model: '/settings/model', connections: '/connections', providers: '/providers', tools: '/settings/tools', remote: '/settings/webui', system: '/settings/system', archived: '/settings/archived', about: '/settings/about', pet: '/settings/pet', diagnostics: '/diagnostics', scheduled: '/scheduled', onboarding: '/onboarding', ramble: '/transcription', kibble: '/dogfood' })) {
    await open(page, route);
    if (name === 'projects') await expect(page.locator('#project-knowledge')).toBeVisible({ timeout: 20000 });
    if (name === 'ramble') {
      await expect(page.getByTestId('record-button')).toHaveCSS('font-weight', '600');
      await expect(page.getByTestId('record-button')).toHaveCSS('color', 'rgb(255, 241, 240)');
      await expect(page.getByTestId('record-button')).toHaveCSS('background-image', 'linear-gradient(rgb(166, 68, 63), rgb(139, 49, 45))');
    }
    if (name === 'work') await expect(page.getByText('Loading…', { exact: true })).toHaveCount(0, { timeout: 20000 });
    await page.waitForTimeout(1500);
    await record(page, `1440-${name}`);
  }
  expect(failures).toEqual([]);
});
for (const width of [1920, 1024, 393, 360]) {
  test(`responsive shell at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width < 768 ? 852 : 1080 });
    await open(page, '/guid');
    await expect(page.getByTestId('guid-input')).toBeVisible();
    await record(page, `${width}-home`);
    if (width < 768) {
      await page.getByRole('button', { name: 'Expand More', exact: true }).click();
      await record(page, `${width}-drawer`);
      await page.getByRole('button', { name: 'Ramble', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Ramble', exact: true })).toBeVisible();
      await expect(page.locator('.layout-sider')).not.toBeVisible();
      const folderInput = page.getByPlaceholder('New folder', { exact: true });
      await folderInput.scrollIntoViewIfNeeded();
      await expect(folderInput).toBeVisible();
      await record(page, `${width}-ramble`);
      await open(page, '/guid');
      await page.getByRole('button', { name: 'Expand More', exact: true }).click();
      await page.getByRole('button', { name: 'Kibble', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Kibble', exact: true })).toBeVisible();
      await record(page, `${width}-kibble`);
      await open(page, '/guid');
      await page.getByRole('button', { name: 'Attach files and tools' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await record(page, `${width}-composer-sheet`);
    }
  });
}
test('Kibble shortcut and project deep links preserve their routes', async ({ page }) => {
  await open(page, '/guid');
  await page.keyboard.press('Control+Shift+F');
  await expect(page.getByText('Click the part of Kel that bothered you', { exact: false })).toBeVisible();
  await page.keyboard.press('Escape');
  await open(page, '/projects/recipes');
  await expect(page.locator('#project-recipes')).toBeVisible();
  await expect(page.locator('#project-knowledge')).toBeAttached();
  await expect(page.locator('#project-map')).toBeAttached();
});


test('appearance choices change live paint and restore cleanly', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, '/settings/appearance');
  await page.getByTestId('theme-card-dark').click();
  const canvas = page.getByTestId('theme-hex-bg-base');
  await canvas.fill('#123456');
  await expect(page.locator('.kel-v2-shell')).toHaveCSS('background-color', 'rgb(18, 52, 86)');
  await page.getByTestId('theme-hex-bg-1').fill('#234567');
  await expect(page.locator('.kel-shell-appearance > div').first()).toHaveCSS('background-color', 'rgb(35, 69, 103)');
  await record(page, '1440-custom-colors');
  await page.getByTestId('theme-reset-bg-base').click();
  await page.getByTestId('theme-reset-bg-1').click();
  await expect(page.locator('html')).not.toHaveAttribute('style', /--kel-shell-custom-(canvas|panel)/);
  await page.getByTestId('theme-card-light').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await record(page, '1440-light');
  await page.getByTestId('theme-card-dark').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});

test('source button states and keyboard focus remain visible', async ({ page }) => {
  await open(page, '/guid');
  const button = page.locator('.kel-shell-new-chat');
  await button.hover();
  await record(page, '1440-newchat-hover');
  await page.mouse.down();
  await record(page, '1440-newchat-pressed');
  await page.mouse.up();
  await button.focus();
  await expect(button).toBeFocused();
  await record(page, '1440-newchat-focus');
  await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeDisabled();
});


test('conversation rendering keeps real message components and touch actions', async ({ page, context }) => {
  const id = 'shell-visual-fixture';
  const at = Date.UTC(2026, 8, 21, 13, 32);
  const conversation = { id, name: 'Shell conversation fixture', type: 'aionrs', createTime: at, modifyTime: at, extra: {}, model: { provider_id: 'fixture', use_model: 'fixture' } };
  await page.route(/\/api\/conversations(?:\?.*)?$/, route => route.fulfill({ json: { success: true, data: {
    items: [{ ...conversation, extra: { pinned: true, pinned_at: at } }, { ...conversation, id: 'shell-recent-fixture', name: 'Recent conversation fixture' }], total: 2, has_more: false,
  } } }));
  const messages = [
    { id: 'fixture-user', conversation_id: id, type: 'text', position: 'right', status: 'finish', created_at: at, content: { content: 'Review the shell layout and preserve the working controls.' } },
    { id: 'fixture-kel', conversation_id: id, type: 'text', position: 'left', status: 'finish', created_at: at + 1000, content: { content: 'The shell uses the shared components.\n\n- Conversation controls remain connected.\n- Tools opens Ramble and Kibble.\n- Phone controls stay within the viewport.' } },
  ];
  // Fixtures are confined to this automated test. No database or production demo state is changed.
  await page.route(`**/api/conversations/${id}**`, async route => {
    const pathname = new URL(route.request().url()).pathname;
    let data: unknown = conversation;
    if (pathname.endsWith('/messages')) data = { items: messages, oldest_cursor: null, newest_cursor: null, has_more_before: false, has_more_after: false };
    else if (pathname.endsWith('/runtime/ensure')) data = { recovered: false, config_options: [], runtime: { is_processing: false, state: 'idle' } };
    else if (pathname !== `/api/conversations/${id}`) return route.continue();
    await route.fulfill({ json: { success: true, data } });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, `/conversation/${id}`);
  await expect(page.getByTestId('chat-title-editor-trigger')).toContainText('Shell conversation fixture');
  await expect(page.locator('.kel-shell-message-turn')).toHaveCount(2);
  await expect(page.locator('.conversation-item')).toHaveCount(2);
  await expect(page.getByText('Pinned', { exact: true })).toBeVisible();
  const body = page.locator('.markdown-shadow-body p').first();
  await expect(body).toHaveCSS('font-family', /SF Pro Text/);
  await expect(body).toHaveCSS('font-weight', '400');
  await expect(body).toHaveCSS('font-size', '16px');
  await expect(body).toHaveCSS('line-height', '25px');
  await record(page, '1440-chat-fixture');
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.getByRole('button', { name: 'Copy', exact: true }).last().click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('Tools opens Ramble and Kibble');
  await page.setViewportSize({ width: 393, height: 852 });
  await expect(page.getByRole('button', { name: 'Copy', exact: true }).last()).toBeVisible();
  await page.waitForTimeout(3500);
  await expect(body).toHaveCSS('font-size', '16px');
  await expect(body).toHaveCSS('line-height', '25px');
  await record(page, '393-chat-fixture');
});

test('model configuration modal keeps cancel and disabled validation', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, '/settings/model');
  await page.getByRole('button', { name: /Add Model|Add Provider/i }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.waitForTimeout(400);
  const modal = page.locator('.kel-shell-model-modal');
  const box = await modal.boundingBox();
  expect(box?.width).toBe(520);
  expect(box?.x).toBe(588);
  await expect(modal.locator('.arco-modal-content')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await record(page, '1440-model-dialog');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
});


test('provider rows reveal real controls and onboarding keeps five sections', async ({ page }) => {
  await open(page, '/providers');
  const provider = page.locator('.kel-shell-provider').filter({ hasText: 'DeepSeek' });
  await provider.locator('summary').click();
  await provider.getByRole('button', { name: 'Set up', exact: true }).click();
  await expect(provider.getByRole('textbox', { name: /API key/ })).toBeVisible();
  await expect(provider.getByRole('button', { name: 'Save + Verify' })).toBeDisabled();
  await provider.getByRole('button', { name: 'Cancel', exact: true }).click();
  await open(page, '/onboarding');
  for (const title of ['Kel runs on this machine', 'Connect a model', 'Where work happens', 'How much Kel does on its own', "You're set"]) {
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeAttached();
  }
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2');
});


test('Foundations typography loads the specified fonts and role metrics', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, '/projects');
  const title = page.getByRole('heading', { name: 'Projects', exact: true });
  const card = page.getByRole('heading', { name: 'Knowledge', exact: true });
  await expect(title).toHaveCSS('font-family', /Instrument Sans/);
  await expect(title).toHaveCSS('font-size', '26px');
  await expect(title).toHaveCSS('line-height', '32px');
  await expect(title).toHaveCSS('font-weight', '600');
  await expect(card).toHaveCSS('font-family', /Instrument Sans/);
  await expect(card).toHaveCSS('font-size', '15px');
  await expect(card).toHaveCSS('line-height', '20px');
  await expect(card).toHaveCSS('font-weight', '700');
  await expect(card).toHaveCSS('color', 'rgb(255, 196, 129)');
  await expect(page.locator('.kel-shell-workspace-link')).toHaveCSS('font-size', '13px');
  await expect(page.locator('.kel-shell-workspace-link')).toHaveCSS('line-height', '18px');
  await expect(page.locator('.kel-v2-shell')).toHaveCSS('font-family', /SF Pro Text/);
  expect(await page.evaluate(() => document.fonts.check('400 16px "SF Pro Text"'))).toBe(true);
  expect(await page.evaluate(() => [...document.fonts].some(font => font.family === 'Inter'))).toBe(false);
});
