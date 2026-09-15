// Asserts the shell skip-link contract on a packaged/unpacked Kel candidate:
//   exists  ->  is focusable  ->  is the FIRST tab stop from a fresh focus state  ->  targets existing content.
// Usage: node probe-skip-link.cjs <appDir> <dataDir> <outDir> [hash]
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
const rawHash = process.argv[5] || '/guid';
// Git-Bash rewrites a bare "/work" argument into a Windows path; recover the route.
const hash =
  rawHash.includes('\\') || rawHash.includes(':')
    ? '/' + rawHash.split(/[\\/]/).filter(Boolean).pop()
    : rawHash;
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const results = { schema: 1, hash, checks: {}, errors: [] };
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
    await page.evaluate((route) => {
      location.hash = route;
    }, hash);
    await page.waitForTimeout(2500);

    results.checks = await page.evaluate(() => {
      const link = document.querySelector('.kel-skip');
      const describe = (el) => {
        if (!el) return null;
        const cs = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName,
          text: (el.textContent || '').trim().slice(0, 40),
          href: el.getAttribute('href'),
          display: cs.display,
          visibility: cs.visibility,
          position: cs.position,
          left: cs.left,
          top: cs.top,
          opacity: cs.opacity,
          pointerEvents: cs.pointerEvents,
          tabIndex: el.tabIndex,
          rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
          offsetParent: Boolean(el.offsetParent),
          hiddenAncestor: (() => {
            let node = el.parentElement;
            while (node) {
              const style = getComputedStyle(node);
              if (style.display === 'none' || style.visibility === 'hidden') return node.tagName;
              node = node.parentElement;
            }
            return null;
          })(),
        };
      };
      const focusables = Array.from(
        document.querySelectorAll(
          "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])"
        )
      ).filter((el) => {
        const rect = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
      });
      const first = focusables[0];
      return {
        link: describe(link),
        linkCount: document.querySelectorAll('.kel-skip').length,
        firstFocusable: first
          ? {
              tag: first.tagName,
              isSkipLink: first.classList.contains('kel-skip'),
              text: (first.textContent || '').trim().slice(0, 40),
            }
          : null,
        targetExists: Boolean(document.querySelector('#kel-shell-content')),
      };
    });

    await page.evaluate(() => {
      const active = document.activeElement;
      if (active && typeof active.blur === 'function') active.blur();
    });
    await page.keyboard.press('Tab');
    await page.waitForTimeout(300);
    results.checks.firstTabStop = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      return {
        tag: el.tagName,
        isSkipLink: el.classList.contains('kel-skip'),
        text: (el.textContent || '').trim().slice(0, 40),
      };
    });
    await page.screenshot({ path: path.join(outDir, 'skip-link-focus.png') });
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

  fs.writeFileSync(path.join(outDir, 'skip-link-evidence.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
})();
