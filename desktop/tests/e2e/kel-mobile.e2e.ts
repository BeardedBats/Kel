/**
 * V2-05 — Kel on a phone, driven in a real browser engine.
 *
 * Not a CSS reasoning exercise: the built renderer is served through the real gateway
 * (`bun run webui` + aioncore + the Kel engine), signed in against the real backend, and walked at a
 * current-generation iPhone viewport. Screenshots and findings land in `docs/v2/evidence/v2-05/`.
 *
 * The dev password comes from the environment (the standalone webui prints it on first start); it is
 * never written into the repository.
 */
import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const BASE = process.env.KEL_WEBUI_URL || 'http://127.0.0.1:25809';
const USER = process.env.KEL_DEV_USER || 'admin';
const PASSWORD = process.env.KEL_DEV_PASSWORD || '';
const EVIDENCE = process.env.KEL_EVIDENCE_DIR
  || path.resolve(__dirname, '..', '..', '..', 'docs', 'v2', 'evidence', 'v2-05');

fs.mkdirSync(EVIDENCE, { recursive: true });

const findings: Array<Record<string, unknown>> = [];
function note(entry: Record<string, unknown>): void {
  findings.push(entry);
  console.log(`[v2-05] ${JSON.stringify(entry).slice(0, 700)}`);
}
function save(name: string): void {
  fs.writeFileSync(path.join(EVIDENCE, name), JSON.stringify(findings, null, 2), 'utf8');
}

interface Watch {
  wsFailures: string[];
  failedResponses: string[];
  consoleErrors: string[];
}

/** Watch the phone the way a person would: dead sockets, failed reads, shouted errors. */
function watch(page: Page): Watch {
  const state: Watch = { wsFailures: [], failedResponses: [], consoleErrors: [] };
  page.on('console', (message) => {
    const line = message.text();
    if (message.type() !== 'error') return;
    if (/WebSocket connection .*failed|\[ensureWs\] ERROR/.test(line)) {
      state.wsFailures.push(line.slice(0, 120));
      return;
    }
    state.consoleErrors.push(line.slice(0, 200));
  });
  page.on('pageerror', (error) => state.consoleErrors.push(`pageerror: ${String(error).slice(0, 200)}`));
  page.on('response', (response) => {
    if (response.status() < 400) return;
    state.failedResponses.push(`${response.status()} ${new URL(response.url()).pathname}`);
  });
  return state;
}

/** Horizontal overflow, naming the element that pokes out so a fix is obvious. */
async function overflow(page: Page): Promise<{ ok: boolean; scrollWidth: number; clientWidth: number; worst: string }> {
  return page.evaluate(() => {
    const root = document.documentElement;
    let worst = '';
    let worstRight = 0;
    for (const element of Array.from(document.querySelectorAll('body *'))) {
      const box = (element as HTMLElement).getBoundingClientRect();
      if (box.width === 0 && box.height === 0) continue;
      if (box.right > worstRight) {
        worstRight = box.right;
        const html = element as HTMLElement;
        worst = `${html.tagName.toLowerCase()} class="${html.className?.toString().slice(0, 70)}" right=${Math.round(box.right)}`;
      }
    }
    return {
      ok: root.scrollWidth <= root.clientWidth + 1,
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      worst,
    };
  });
}

const text = async (page: Page, limit = 900): Promise<string> => (await page.locator('body').innerText()).slice(0, limit);

/** Sign in when Kel asks. The sign-in view is rendered without changing the path, so the form itself is
 * the signal — never the URL. Wait for Kel to decide either way. */
async function signIn(page: Page): Promise<void> {
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  const username = page.locator('input[name="username"]');
  const shell = page.getByText('Work & context');
  const deadline = Date.now() + 25_000;
  while (Date.now() < deadline) {
    if (await username.count()) break;
    if (await shell.count()) return;
    await page.waitForTimeout(400);
  }
  if (!(await username.count())) throw new Error('Kel neither asked for a sign-in nor showed the app shell');
  await username.fill(USER);
  await page.fill('input[name="password"]', PASSWORD);
  await page.click('button[type="submit"], button:has-text("Sign In"), button:has-text("Sign in")');
  await username.waitFor({ state: 'detached', timeout: 30_000 });
}

/**
 * Walk Kel's first run the way a person holding the phone would: read each step, take the offered
 * "next" control, stop when the wizard is done. Recorded, not assumed — the labels are Kel's.
 */
async function leaveFirstRun(page: Page, journey: string): Promise<void> {
  for (let step = 0; step < 8; step += 1) {
    const body = await text(page, 400);
    if (!/Set up Kel/i.test(body)) return;
    note({ journey, step: `first-run-${step + 1}`, text: body });
    const next = page.getByRole('button', { name: /^(Next|Continue|Finish|Done|Skip setup)$/ }).first();
    if (!(await next.count())) return;
    await next.click();
    await page.waitForTimeout(900);
  }
}

/**
 * Reach a surface the way a thumb does. A full-page load of a Kel route lands back on the home — the
 * phone moves through its own drawer — so the journey opens the drawer and taps the entry, exactly like
 * a person. Every step is bounded and recorded: a control that cannot be tapped is a finding, not a
 * sixty-second hang.
 */
async function openFromDrawer(page: Page, name: string, journey: string): Promise<void> {
  const visible = (label: string) =>
    page.getByRole('button', { name: new RegExp(`^${label}$`) }).filter({ visible: true });
  const onScreen = async (locator: ReturnType<typeof visible>): Promise<boolean> => {
    const box = await locator.first().boundingBox().catch(() => null);
    const viewport = page.viewportSize();
    if (!box || !viewport) return false;
    return box.x >= 0 && box.y >= 0 && box.x + box.width <= viewport.width + 1 && box.y < viewport.height;
  };
  // A drawer entry that is merely "visible" may sit off-canvas: the phone opens the drawer first.
  if (!(await onScreen(visible(name)))) {
    const toggle = page.getByRole('button', { name: /Work & context/ }).filter({ visible: true }).first();
    note({ journey, step: 'drawer-toggle', count: await toggle.count() });
    await toggle
      .click({ timeout: 8000 })
      .catch((error) => note({ journey, step: 'drawer-toggle-failed', error: String(error).slice(0, 160) }));
    await page.waitForTimeout(900);
    await page.screenshot({ path: path.join(EVIDENCE, `${journey}-drawer.png`) });
  }
  const target = visible(name).first();
  note({ journey, step: `drawer-${name}`, count: await visible(name).count(), onScreen: await onScreen(visible(name)) });
  await target
    .click({ timeout: 10_000 })
    .catch((error) => note({ journey, step: `drawer-${name}-failed`, error: String(error).slice(0, 160) }));
  await page.waitForTimeout(2500);
}

// The phone fixture is top-level: `launchOptions` also has to be, because it forces a worker.
test.use({
  viewport: { width: 393, height: 852 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
  permissions: ['microphone'],
  launchOptions: {
    args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
  },
  userAgent:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
});

test.describe('Kel on a phone (V2-05)', () => {

  test('A — the phone answers "what is happening with Kel?"', async ({ page }) => {
    await signIn(page);
    // The normal phone case: the device already carries a session, so the shell boots WITH it — that is
    // when live updates and every Kel read must work.
    const seen = watch(page);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3500);
    await leaveFirstRun(page, 'A');
    await page.waitForTimeout(1500);

    await page.screenshot({ path: path.join(EVIDENCE, 'A1-home.png') });
    const home = await overflow(page);
    const homeText = await text(page, 1200);
    note({ journey: 'A', step: 'home', path: new URL(page.url()).pathname, overflow: home, text: homeText });

    // Does the opening surface answer the question? Running / recent / failed work + what needs Nick.
    note({
      journey: 'A',
      step: 'home-answer',
      needsAttention: /need you|Needs your attention/i.test(homeText),
      status: /waiting|working|finished|failed|running/i.test(homeText),
      honestHold: /not answering|no.*model|wait instead/i.test(homeText),
    });

    await openFromDrawer(page, 'Work', 'A');
    await page.screenshot({ path: path.join(EVIDENCE, 'A2-work.png') });
    const work = await overflow(page);
    const workText = await text(page, 1500);
    note({ journey: 'A', step: 'work', overflow: work, text: workText });

    note({
      journey: 'A',
      step: 'post-signin-failures',
      wsFailures: [...new Set(seen.wsFailures)].slice(0, 4),
      failedResponses: [...new Set(seen.failedResponses)].slice(0, 12),
      consoleErrors: [...new Set(seen.consoleErrors)].slice(0, 8),
    });
    save('findings-A.json');

    expect(seen.failedResponses, 'no failed reads once the phone is signed in').toEqual([]);
    expect(seen.wsFailures, 'live updates connect once the phone is signed in').toEqual([]);
    expect(home.ok, `no horizontal overflow on the home surface: ${home.worst}`).toBe(true);
    expect(work.ok, `no horizontal overflow on the work surface: ${work.worst}`).toBe(true);
  });

  test('B — a conversation works from the thumb', async ({ page }) => {
    await signIn(page);
    await leaveFirstRun(page, 'B');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(EVIDENCE, 'B1-home.png') });

    const composer = page.locator('textarea, [contenteditable="true"]').first();
    note({ journey: 'B', step: 'composer', count: await composer.count() });
    await composer.click();
    // Paste-shaped input, the way a phone clipboard arrives.
    await page.keyboard.insertText('Phone journey paste check: 3 lines\nsecond line\nthird line');
    await page.waitForTimeout(700);
    const typed = await page.evaluate(() => {
      const element = document.querySelector('textarea, [contenteditable="true"]') as HTMLTextAreaElement | HTMLElement | null;
      return element ? ((element as HTMLTextAreaElement).value || element.innerText || '').slice(0, 120) : '';
    });
    await page.screenshot({ path: path.join(EVIDENCE, 'B2-pasted.png') });

    const send = page.locator('button.send-button-custom').first();
    const box = await send.boundingBox().catch(() => null);
    const before = { count: await send.count(), box, disabled: await send.isDisabled().catch(() => null) };
    // A real key press separates "React never saw the paste" from "Kel is holding the send back".
    await page.keyboard.press('Space');
    await page.waitForTimeout(500);
    const afterKey = { disabled: await send.isDisabled().catch(() => null) };
    note({ journey: 'B', step: 'send-control', typed, before, afterKey });

    const layout = await overflow(page);
    note({ journey: 'B', step: 'composer-layout', overflow: layout, text: await text(page, 700) });
    note({ journey: 'B', step: 'composer-reachable', box, viewport: page.viewportSize() });

    // The conversation that already exists must open from the phone, with its context intact.
    const drawerToggle = page.getByRole('button', { name: /Work & context/ }).filter({ visible: true }).first();
    if (await drawerToggle.count()) {
      await drawerToggle.click({ timeout: 8000 }).catch(() => undefined);
      await page.waitForTimeout(1200);
      await page.screenshot({ path: path.join(EVIDENCE, 'B3-history.png') });
    }
    const entry = page.getByText(/Phone journey seed/i).first();
    note({ journey: 'B', step: 'history-entry', count: await entry.count() });
    if (await entry.count()) {
      await entry
        .click({ timeout: 8000 })
        .catch((error) => note({ journey: 'B', step: 'history-open-failed', error: String(error).slice(0, 200) }));
      await page.waitForTimeout(2500);
      await page.screenshot({ path: path.join(EVIDENCE, 'B4-conversation.png') });
      const opened = await text(page, 1200);
      note({
        journey: 'B',
        step: 'conversation',
        text: opened,
        hasSeed: /Phone journey seed/i.test(opened),
        hasAnswer: /Kel here/i.test(opened),
        overflow: await overflow(page),
      });
    }
    save('findings-B.json');

    expect(layout.ok, `no horizontal overflow at the composer: ${layout.worst}`).toBe(true);
    expect(box, 'the send control has a real box on the phone').not.toBeNull();
    expect(box!.x + box!.width, 'the send control is inside the phone width').toBeLessThanOrEqual(393);
  });

  test('C — what needs Nick can be answered from the phone', async ({ page }) => {
    await signIn(page);
    await leaveFirstRun(page, 'C');
    await page.waitForTimeout(1500);
    const before = await text(page, 900);
    note({ journey: 'C', step: 'attention', text: before });

    const action = page.getByRole('button', { name: /^(Set it up|Open Providers|Review|Answer|Approve|Deny)$/ }).first();
    note({ journey: 'C', step: 'action-control', count: await action.count(), name: await action.textContent().catch(() => null) });
    if (await action.count()) {
      await action.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: path.join(EVIDENCE, 'C1-after-action.png') });
      const after = await text(page, 1200);
      note({ journey: 'C', step: 'after-action', path: new URL(page.url()).pathname, text: after, changed: after !== before });
      note({ journey: 'C', step: 'after-action-layout', overflow: await overflow(page) });
    }
    save('findings-C.json');
  });

  test('D — project context follows the thumb', async ({ page }) => {
    await signIn(page);
    await leaveFirstRun(page, 'D');
    await openFromDrawer(page, 'Projects', 'D');
    await page.screenshot({ path: path.join(EVIDENCE, 'D1-projects.png') });
    const layout = await overflow(page);
    note({ journey: 'D', step: 'projects', text: await text(page, 1000), overflow: layout });
    const controls = await page.evaluate(() =>
      Array.from(document.querySelectorAll('button, [role="button"], a[href]'))
        .map((element) => (element.getAttribute('aria-label') || element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40))
        .filter(Boolean)
        .slice(0, 40)
    );
    note({ journey: 'D', step: 'controls', controls });

    // Why a rail entry resists a tap decides whether this is a spec artifact or a real phone defect:
    // ask the browser what a thumb would actually hit at that point.
    const hitTest = await page.evaluate(() => {
      const target = Array.from(document.querySelectorAll('button')).find(
        (element) => (element.getAttribute('aria-label') || element.textContent || '').trim() === 'Projects'
      );
      if (!target) return null;
      const box = target.getBoundingClientRect();
      const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2) as HTMLElement | null;
      const style = getComputedStyle(target);
      return {
        box: { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) },
        pointerEvents: style.pointerEvents,
        visibility: style.visibility,
        opacity: style.opacity,
        topElement: top ? `${top.tagName.toLowerCase()}.${(top.className || '').toString().slice(0, 50)}` : null,
        topIsTarget: top === target || (top ? target.contains(top) : false),
      };
    });
    note({ journey: 'D', step: 'rail-hit-test', hitTest });
    save('findings-D.json');
    expect(layout.ok, `no horizontal overflow on the project surface: ${layout.worst}`).toBe(true);
  });

  test('E — voice goes through the phone microphone', async ({ page }) => {
    const seen = watch(page);
    await signIn(page);
    await leaveFirstRun(page, 'E');
    await page.waitForTimeout(1500);

    const mic = page.getByRole('button', { name: /Record a message/i }).filter({ visible: true }).first();
    note({ journey: 'E', step: 'mic-control', count: await mic.count(), box: await mic.boundingBox().catch(() => null) });
    if (await mic.count()) {
      await mic
        .click({ timeout: 10_000 })
        .catch((error) => note({ journey: 'E', step: 'mic-click-failed', error: String(error).slice(0, 160) }));
      await page.waitForTimeout(3000);
      await page.screenshot({ path: path.join(EVIDENCE, 'E1-recording.png') });
      note({ journey: 'E', step: 'recording', text: await text(page, 700) });
      const stop = page.locator('[data-testid="kel-mic-stop"]').first();
      note({ journey: 'E', step: 'stop-control', count: await stop.count() });
      await stop
        .click({ timeout: 10_000 })
        .catch((error) => note({ journey: 'E', step: 'stop-click-failed', error: String(error).slice(0, 160) }));
      // Give the real transcription path time to answer: a transcript arrives, or Kel says why not.
      await page.waitForTimeout(12_000);
      await page.screenshot({ path: path.join(EVIDENCE, 'E2-after-stop.png') });
      const composer = await page.evaluate(() => {
        const element = document.querySelector('textarea, [contenteditable="true"]') as HTMLTextAreaElement | HTMLElement | null;
        return element ? ((element as HTMLTextAreaElement).value || element.innerText || '').slice(0, 300) : '';
      });
      note({
        journey: 'E',
        step: 'after-stop',
        text: await text(page, 900),
        composer,
        consoleErrors: [...new Set(seen.consoleErrors)].slice(0, 6),
      });
    }
    save('findings-E.json');
  });

  test('F — the PWA contract holds on the phone', async ({ page }) => {
    await signIn(page);
    const seen = watch(page);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3500);

    const manifest = await page.evaluate(async () => {
      const href = document.querySelector('link[rel="manifest"]')?.getAttribute('href') ?? '';
      const response = await fetch(href, { cache: 'no-store' });
      const body = await response.json();
      return {
        ok: response.ok,
        href,
        name: body.name,
        shortName: body.short_name,
        display: body.display,
        icons: (body.icons ?? []).length,
        donorWords: /aionui|aion\b|gemini/i.test(JSON.stringify(body)) ? JSON.stringify(body).slice(0, 200) : null,
      };
    });
    const pwa = await page.evaluate(async () => {
      const registration = await navigator.serviceWorker.getRegistration();
      return {
        registered: Boolean(registration),
        controller: Boolean(navigator.serviceWorker.controller),
        scope: registration?.scope ?? null,
        caches: await caches.keys(),
      };
    });
    // `/api/` must never be served stale from a cache: count cached API entries.
    const apiCacheHitCount = await page.evaluate(async () => {
      let cached = 0;
      for (const name of await caches.keys()) {
        for (const key of await (await caches.open(name)).keys()) {
          if (new URL(key.url).pathname.startsWith('/api/')) cached += 1;
        }
      }
      return cached;
    });
    const layout = await overflow(page);
    note({ journey: 'F', manifest, serviceWorker: pwa, apiCacheHitCount, overflow: layout });
    note({
      journey: 'F',
      step: 'post-signin-failures',
      failedResponses: [...new Set(seen.failedResponses)].slice(0, 10),
      consoleErrors: [...new Set(seen.consoleErrors)].slice(0, 6),
      wsFailures: seen.wsFailures.length,
    });
    save('findings-F.json');

    expect(manifest.name, 'the manifest is Kel').toBe('Kel');
    expect(manifest.donorWords, 'no donor identity in the manifest').toBeNull();
    expect(pwa.registered, 'a service worker registers').toBe(true);
    expect(apiCacheHitCount, '/api/ is never cached').toBe(0);
    expect(layout.ok, `no horizontal overflow on the phone shell: ${layout.worst}`).toBe(true);
  });
});
