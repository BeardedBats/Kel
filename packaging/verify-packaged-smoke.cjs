// V1.2 final packaged smoke: fresh data dir, normal quit path, clean shutdown.
// Usage: node verify-packaged-smoke.cjs <Kel.exe> <fresh-data-dir>   (SMOKE_OUT optional)
function resolvePlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return process.env.PLAYWRIGHT_MODULE;
  try { return require.resolve('playwright'); } catch (e) {}
  try { return require.resolve('@playwright/test'); } catch (e) {}
  console.error('playwright not found; set PLAYWRIGHT_MODULE to a playwright install.');
  process.exit(2);
}
const { _electron: electron } = require(resolvePlaywright());
const fs = require('fs'), path = require('path');
const OUT = process.env.SMOKE_OUT || path.dirname(path.resolve(process.argv[3]));
const EXE = path.resolve(process.argv[2]);
const DATA = path.resolve(process.argv[3]);
const RESULT = path.join(OUT, 'smoke-result.json');
const out = { steps: [], errors: [] };
const save = () => fs.writeFileSync(RESULT, JSON.stringify(out, null, 2));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
(async () => {
  const app = await electron.launch({
    executablePath: EXE,
    env: { ...process.env, AIONUI_E2E_TEST: '1', KEL_DATA_DIR: DATA },
    timeout: 90000,
    args: ['--no-sandbox'],
  });
  out.steps.push('launched'); save();
  const win = await app.firstWindow({ timeout: 90000 });
  out.steps.push('window'); save();
  win.on('pageerror', (e) => out.errors.push(String(e)));
  await win.waitForTimeout(15000);
  out.title = await win.title();
  out.hash = await win.evaluate(() => location.hash);
  out.bodyPreview = (await win.locator('body').innerText().catch(() => '')).slice(0, 200);
  const desc = JSON.parse(fs.readFileSync(path.join(DATA, 'desktop-session.json'), 'utf8').replace(/^\uFEFF/, ''));
  out.enginePid = desc.pid;
  out.engineVersion = desc.engine_version || null;
  await win.screenshot({ path: path.join(OUT, 'smoke-final.png') });
  out.steps.push('checks-done'); save();
  // Normal quit path: app.quit() -> before-quit drain (shutdown-idle) -> engine stops.
  await app.evaluate(({ app }) => app.quit());
  let engineStopped = false;
  for (let i = 0; i < 40; i++) {
    try { process.kill(out.enginePid, 0); } catch { engineStopped = true; break; }
    await sleep(1000);
  }
  out.engineStopped = engineStopped;
  const proc = app.process();
  let appExited = false;
  for (let i = 0; i < 40; i++) {
    if (proc.exitCode !== null) { appExited = true; break; }
    await sleep(1000);
  }
  out.appExited = appExited;
  out.steps.push('quit-observed'); save();
  console.log(JSON.stringify(out, null, 2));
  process.exit(0);
})().catch((e) => {
  out.error = String(e).slice(0, 500);
  save();
  console.error('HARNESS ERROR', out.error);
  process.exit(1);
});
