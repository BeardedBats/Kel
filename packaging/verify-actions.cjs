// Drives the packaged Kel candidate through text-based interactions and records before/after
// evidence: rendered text, a screenshot, and the engine state read straight from the loopback API.
//
// Usage: node verify-actions.cjs <appDir> <dataDir> <outDir>
// Requires PLAYWRIGHT_MODULE (or a resolvable `playwright`) and PLAYWRIGHT_BROWSERS_PATH.
// Isolated like capture-screens.cjs: redirected data dirs, offscreen windows, bounded shutdown.
const path = require('path');
const fs = require('fs');

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

const STEPS = [
  {
    name: 'knowledge-confirm',
    hash: '/projects/knowledge',
    click: 'Confirm',
    expect: 'Confirm',
    probe: (session) =>
      apiGet(session, '/api/work?conversation=main').then((work) =>
        (work.memory.records || []).map((record) => ({
          topic: record.topic,
          status: record.status,
          user_confirmed: record.user_confirmed,
          trust: record.trust,
        }))
      ),
  },
  {
    name: 'recipe-preview',
    hash: '/projects/recipes',
    click: 'Preview (dry run)',
    expect: 'Dry run',
    probe: (session) =>
      apiGet(session, '/api/recipes', { action: 'list' }).then((payload) => ({
        keys: Object.keys(payload || {}),
      })),
  },
  {
    name: 'work-resume',
    hash: '/work',
    click: 'Resume',
    expect: 'Resume',
    probe: (session) =>
      apiGet(session, '/api/state?conversation=main').then((state) =>
        (state.jobs || []).map((job) => ({ state: job.state, verdict: job.verdict }))
      ),
  },
];

function descriptor() {
  return JSON.parse(fs.readFileSync(path.join(dataDir, 'desktop-session.json'), 'utf8'));
}

async function apiGet(session, route, body) {
  const url = `${session.url}${route}`;
  if (!body) {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${session.token}` } });
    return res.json();
  }
  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

function pageText(page) {
  return page.evaluate(() => (document.body ? document.body.innerText : ''));
}

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

  const results = { schema: 1, launchMode: packaged ? 'packaged' : 'dev', steps: [], errors: [] };
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
    await page.waitForTimeout(6000);

    const session = descriptor();
    results.engineVersion = session.version || null;

    for (const step of STEPS) {
      const entry = { name: step.name, hash: step.hash, click: step.click };
      try {
        entry.before = await step.probe(session);
        await page.evaluate((hash) => {
          location.hash = hash;
        }, step.hash);
        await page.waitForTimeout(2200);
        entry.textBefore = (await pageText(page)).slice(0, 600);
        await page.screenshot({ path: path.join(outDir, `actions-${step.name}-before.png`) });

        const target = page.getByRole('button', { name: step.click }).first();
        await target.click({ timeout: 20000 });
        entry.clicked = true;
        await page.waitForTimeout(2600);
        entry.textAfter = (await pageText(page)).slice(0, 900);
        entry.sawExpectedText = entry.textAfter.includes(step.expect);
        await page.screenshot({ path: path.join(outDir, `actions-${step.name}-after.png`) });
        entry.after = await step.probe(session);
        entry.changed = JSON.stringify(entry.before) !== JSON.stringify(entry.after);
      } catch (error) {
        entry.error = String(error).slice(0, 300);
        results.errors.push(`${step.name}: ${entry.error}`);
      }
      results.steps.push(entry);
    }
  } catch (error) {
    results.errors.push(`fatal: ${String(error).slice(0, 400)}`);
  }

  try {
    await Promise.race([app.close(), new Promise((resolve) => setTimeout(resolve, 20000))]);
    results.closeOutcome = 'closed';
  } catch (error) {
    results.closeOutcome = 'close-timeout';
  }

  try {
    const session = descriptor();
    if (session.pid) {
      process.kill(session.pid);
      results.engineKilled = true;
    }
  } catch {
    results.engineKilled = false;
  }

  fs.writeFileSync(path.join(outDir, 'actions-evidence.json'), JSON.stringify(results, null, 2));
  console.log(
    JSON.stringify(
      {
        ok: results.errors.length === 0,
        steps: results.steps.map((step) => ({
          name: step.name,
          clicked: Boolean(step.clicked),
          changed: Boolean(step.changed),
          sawExpectedText: Boolean(step.sawExpectedText),
          error: step.error || null,
        })),
        closeOutcome: results.closeOutcome,
      },
      null,
      2
    )
  );
  if (results.errors.length) process.exitCode = 1;
})();
