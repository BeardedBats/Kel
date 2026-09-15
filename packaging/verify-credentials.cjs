// Proves OS-backed credential custody end to end, from the outside:
//   store a value through the Providers UI  ->  the engine holds metadata only
//   the on-disk store holds ciphertext, never the plaintext  ->  delete removes both.
//
// Usage: node verify-credentials.cjs <appDir> <dataDir> <outDir> [plaintext]
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
const plaintext = process.argv[5] || 'sk-kel-fixture-1a2b3c4d5e6f-not-a-real-key';
const provider = 'deepseek';
fs.mkdirSync(outDir, { recursive: true });

const storeFile = () => path.join(dataDir, 'kel-credentials.json');
const readStore = () => {
  try {
    return fs.readFileSync(storeFile(), 'utf8');
  } catch {
    return '';
  }
};

function descriptor() {
  return JSON.parse(fs.readFileSync(path.join(dataDir, 'desktop-session.json'), 'utf8'));
}

async function apiPost(session, route, body) {
  const response = await fetch(`${session.url}${route}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
}

(async () => {
  const results = { schema: 1, provider, checks: {}, errors: [] };
  const packaged = fs.existsSync(path.join(appDir, 'Kel.exe'));
  results.launchMode = packaged ? 'packaged' : 'dev';
  fs.rmSync(storeFile(), { force: true });

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

    await page.evaluate(() => {
      location.hash = '/providers';
    });
    await page.waitForTimeout(2500);

    results.checks.storageAvailable = await page.evaluate(async () => {
      const status = await window.kelAPI?.credentials?.status();
      return Boolean(status?.available);
    });

    await page.getByLabel('Credential value').fill(plaintext);
    await page.screenshot({ path: path.join(outDir, 'credentials-before-store.png') });
    await page.getByRole('button', { name: 'Store credential' }).click({ timeout: 20000 });
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(outDir, 'credentials-after-store.png') });

    results.checks.rendererStatus = await page.evaluate(async () => {
      const status = await window.kelAPI?.credentials?.status();
      return status?.providers ?? null;
    });
    results.checks.valueGetterAbsent = await page.evaluate(() => {
      const api = window.kelAPI?.credentials;
      return !api || typeof api !== 'object' ? null : !('get' in api);
    });

    const session = descriptor();
    const metadata = await apiPost(session, '/api/providers', {
      action: 'credentials',
      provider,
    });
    results.checks.engineMetadata = metadata.credentials ?? null;

    const storedFile = readStore();
    results.checks.fileExists = fs.existsSync(storeFile());
    results.checks.fileHasPlaintext = storedFile.includes(plaintext);
    const parsedStore = (() => {
      try {
        return JSON.parse(storedFile);
      } catch {
        return {};
      }
    })();
    const storedValues = Object.values(parsedStore);
    results.checks.storedKeys = Object.keys(parsedStore);
    results.checks.fileBlobLooksEncrypted =
      storedValues.length > 0 &&
      storedValues.every(
        (value) => typeof value === 'string' && value.length >= 24 && !value.includes(plaintext)
      );
    results.checks.fileSize = storedFile.length;

    const remainingText = await page.evaluate(() => document.body.innerText);
    results.checks.plaintextNotRendered = !remainingText.includes(plaintext);

    results.checks.deleted = await page.evaluate(async (providerId) => {
      const result = await window.kelAPI?.credentials?.remove(providerId);
      return result ?? null;
    }, provider);
    await page.waitForTimeout(1500);
    results.checks.fileAfterDeleteHasProvider = readStore().includes(provider);
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
    const session = descriptor();
    if (session.pid) {
      process.kill(session.pid);
      results.engineKilled = true;
    }
  } catch {
    results.engineKilled = false;
  }

  fs.writeFileSync(
    path.join(outDir, 'credentials-evidence.json'),
    JSON.stringify(results, null, 2)
  );
  console.log(JSON.stringify(results, null, 2));
  const ok =
    results.checks.storageAvailable === true &&
    results.checks.fileExists === true &&
    results.checks.fileHasPlaintext === false &&
    results.checks.fileBlobLooksEncrypted === true &&
    results.checks.plaintextNotRendered === true &&
    results.checks.valueGetterAbsent === true &&
    Array.isArray(results.checks.engineMetadata) &&
    results.checks.engineMetadata.length >= 1 &&
    results.checks.fileAfterDeleteHasProvider === false &&
    results.errors.length === 0;
  if (!ok) process.exitCode = 1;
})();
