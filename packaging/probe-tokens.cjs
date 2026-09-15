// Prints the resolved theme custom properties in light and dark, plus the computed colour of the
// elements the dark audit flagged — so a token fix can be aimed instead of guessed.
// Usage: node probe-tokens.cjs <appDir> <dataDir> [hash]
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
const hash = process.argv[4] || '/guid';

const PROBE = () => {
  const cs = getComputedStyle(document.documentElement);
  const names = [
    '--bg-5',
    '--bg-6',
    '--color-bg-6',
    '--color-text-1',
    '--color-text-2',
    '--color-text-3',
    '--kel-text-2',
    '--kel-text-3',
    '--kel-surface-1',
  ];
  const tokens = {};
  for (const name of names) tokens[name] = cs.getPropertyValue(name).trim();
  const bodyStyle = getComputedStyle(document.body);
  tokens['body.background'] = bodyStyle.backgroundColor;
  tokens['body.color'] = bodyStyle.color;
  tokens['html.data-theme'] = document.documentElement.getAttribute('data-theme');
  tokens['body.arco-theme'] = document.body.getAttribute('arco-theme');
  const probes = [];
  for (const label of ['Work & context', 'Project conversations', 'Work in a project']) {
    const el = Array.from(document.querySelectorAll('span, div, button')).find(
      (node) => (node.textContent || '').trim() === label
    );
    if (!el) continue;
    const style = getComputedStyle(el);
    probes.push({ label, tag: el.tagName, class: String(el.className).slice(0, 60), color: style.color, font: style.fontSize });
  }
  return { tokens, probes };
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
    await page.waitForTimeout(2000);
    out.light = await page.evaluate(PROBE);
    await page.evaluate(() => {
      const root = document.documentElement;
      root.setAttribute('data-color-scheme', 'default');
      root.setAttribute('data-theme', 'dark');
    });
    await page.waitForTimeout(900);
    out.dark = await page.evaluate(PROBE);
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
