/**
 * Kel — real Muse verification (installed app).
 *
 * Drives the installed Dogfood candidate through its own window over CDP and proves that transcription
 * is performed by the real Muse path with the credential the copied Transcriptions app already stored:
 *
 *   --mode transcriptions   the normal Transcriptions feature, one spoken phrase
 *   --mode fix-capture      Ctrl+Shift+F → select → record → stop → review → Save Fix → Dogfood Fixes
 *   --mode failure          the same capture with an unusable key: honest error, retry, nothing saved
 *   --mode device-check     no fake audio at all: does the app open the real microphone?
 *
 * Audio: the machine has a real microphone but nobody can speak into it during an automated run, so
 * the speech comes from a WAV rendered by Windows TTS and fed to the page as its media input
 * (`--use-file-for-fake-audio-capture`). The capture path, the engine, the credential lookup and the
 * network call to Muse are the shipped ones; only the source of the sound is synthetic. `device-check`
 * runs without that flag and reports what the real device does.
 */
const fs = require('fs');
const path = require('path');
const net = require('net');
const { spawn, execFileSync } = require('child_process');

const REPO = 'C:/Users/Nick/Desktop/Kel/kel-daily-driver';
const { chromium } = require(path.join(REPO, 'desktop', 'node_modules', 'playwright'));

const APP = process.env.KEL_MUSE_APP || 'C:/Users/Nick/KelDogfoodCandidate/Kel.exe';
const DATA_ROOT = process.env.KEL_MUSE_DATA || 'C:/Users/Nick/KelDogfoodRuns/prepared/engine';
const PHRASES = {
  a: { file: 'C:/Users/Nick/KelMuseVerify/phrase-a.wav', words: ['orange', 'forty'], label: 'Regular transcription Muse verification, orange baseball forty-seven.' },
  b: { file: 'C:/Users/Nick/KelMuseVerify/phrase-b.wav', words: ['blue', 'eighty'], label: 'Fix Capture Muse verification, blue baseball eighty-three.' },
};
const OUT_DIR = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'muse');

const argv = process.argv.slice(2);
const argValue = (name, fallback) => {
  const index = argv.indexOf(name);
  return index >= 0 && argv[index + 1] ? argv[index + 1] : fallback;
};
const MODE = argValue('--mode', 'device-check');
const PHRASE = argValue('--phrase', MODE === 'transcriptions' ? 'a' : 'b');
const RECORD_MS = Number(argValue('--record-ms', '9000'));
const STAMP = new Date().toISOString().replace(/[:.]/g, '-');
const OUT_FILE = path.join(OUT_DIR, `${MODE}-${STAMP}.json`);

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const freePort = () => new Promise((resolve, reject) => {
  const server = net.createServer();
  server.on('error', reject);
  server.listen(0, '127.0.0.1', () => {
    const { port } = server.address();
    server.close(() => resolve(port));
  });
});

async function waitForCdp(port, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return true;
    } catch {
      /* not up yet */
    }
    await wait(500);
  }
  throw new Error(`CDP endpoint never came up on ${port}`);
}

async function findMainWindow(browser, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const context of browser.contexts()) {
      for (const page of context.pages()) {
        const url = page.url();
        if (url.startsWith('devtools://') || url === 'about:blank') continue;
        return page;
      }
    }
    await wait(500);
  }
  throw new Error('the app window never appeared');
}

function launchApp(port, extraArgs, extraEnv, logName) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const log = fs.createWriteStream(path.join(OUT_DIR, logName));
  const child = spawn(APP, [`--remote-debugging-port=${port}`, ...extraArgs], {
    env: { ...process.env, KEL_DATA_DIR: DATA_ROOT, ...extraEnv },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.pipe(log);
  child.stderr.pipe(log);
  return child;
}

async function attach(port, consoleErrors) {
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const page = await findMainWindow(browser);
  page.setDefaultTimeout(30000);
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text().slice(0, 300));
  });
  page.on('pageerror', (error) => consoleErrors.push(('pageerror: ' + (error.message || error)).slice(0, 300)));
  await page.waitForLoadState('domcontentloaded');
  await wait(3000);
  return { browser, page };
}

async function stopApp(child, browser) {
  if (browser) await browser.close().catch(() => {});
  if (child) {
    spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore' });
    await wait(2500);
  }
}

const goto = async (page, hash) => {
  await page.evaluate((target) => {
    location.hash = target;
  }, hash);
  await wait(2200);
};

const bodyText = (page) => page.evaluate(() => document.body.innerText);

/** The engine's own record (counts + transcripts) so a verification can compare against it. */
function engineFacts() {
  const script = [
    'import json, pathlib, sqlite3, sys',
    'root = pathlib.Path(sys.argv[1])',
    "con = sqlite3.connect(f'file:{(root / 'kel.sqlite3').as_posix()}?mode=ro', uri=True)",
    'con.row_factory = sqlite3.Row',
    'out = {}',
    "try:",
    "    out['fixes'] = [dict(r) for r in con.execute('SELECT id, status, transcript FROM dogfood_fixes ORDER BY id')]",
    "except Exception as exc:",
    "    out['fixes'] = []",
    "    out['fixes_error'] = str(exc)",
    "try:",
    "    out['transcripts'] = [dict(r) for r in con.execute('SELECT id, name, text FROM transcripts ORDER BY created DESC LIMIT 3')]",
    "except Exception as exc:",
    "    out['transcripts'] = []",
    "print(json.dumps(out))",
  ].join('\n');
  try {
    return JSON.parse(execFileSync('python', ['-c', script, DATA_ROOT], { encoding: 'utf8' }));
  } catch (error) {
    return { error: String((error && error.message) || error), fixes: [], transcripts: [] };
  }
}

/** The engine session (url + token) — local, never the Muse key. */
function engineSession() {
  return JSON.parse(fs.readFileSync(path.join(DATA_ROOT, 'desktop-session.json'), 'utf8'));
}

async function engineCall(route, body) {
  const session = engineSession();
  const address = new URL(session.url);
  const response = await fetch(`${session.url}${route}`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${session.token}`,
      origin: address.origin,
    },
    body: JSON.stringify(body ?? {}),
  });
  const text = await response.text();
  let payload = null;
  try {
    payload = JSON.parse(text);
  } catch {
    payload = text.slice(0, 300);
  }
  return { status: response.status, payload };
}

/** Mode: the normal Transcriptions feature, driven exactly as a person would. */
async function runTranscriptions(page) {
  const phrase = PHRASES[PHRASE];
  await goto(page, '#/transcription');
  await page.waitForSelector("[data-testid='record-button']", { timeout: 30000 });
  // What the feature says it is doing: this must read Muse, never practice mode.
  const mode = await page.locator("[data-testid='transcription-mode']").innerText().catch(() => '');
  await page.click("[data-testid='record-button']");
  await page.waitForSelector("[data-testid='recording-bar']", { timeout: 30000 });
  await wait(RECORD_MS);
  const live = await page.locator("[data-testid='live-text']").innerText().catch(() => '');
  await page.click("[data-testid='stop-button']");
  let timedOut = false;
  try {
    await page.waitForFunction(
      () => {
        const element = document.querySelector("[data-testid='transcript-text']");
        return Boolean(element && (element.textContent || '').trim().length > 12);
      },
      null,
      { timeout: 150000 }
    );
  } catch {
    timedOut = true;
  }
  const diagnostics = timedOut
    ? await page.evaluate(() => ({
        progress: document.querySelector("[data-testid='progress-label']")?.textContent || '',
        messages: Array.from(document.querySelectorAll('.arco-message, .arco-notification')).map((el) => (el.textContent || '').slice(0, 200)),
        rows: Array.from(document.querySelectorAll("[data-testid='transcript-row']")).map((el) => (el.textContent || '').replace(/\s+/g, ' ').slice(0, 80)),
        transcriptText: (document.querySelector("[data-testid='transcript-text']")?.textContent || '').slice(0, 300),
      }))
    : null;
  const text = timedOut
    ? ''
    : (await page.locator("[data-testid='transcript-text']").innerText()).trim();
  await page.screenshot({ path: path.join(OUT_DIR, `transcriptions-${timedOut ? 'failed' : 'ok'}-${STAMP}.png`) });
  const words = phrase.words.map((word) => word.toLowerCase());
  const haystack = text.toLowerCase();
  return {
    timedOut,
    diagnostics,
    modeLabel: mode.replace(/\s+/g, ' ').trim().slice(0, 200),
    liveText: live.replace(/\s+/g, ' ').trim().slice(0, 200),
    transcript: text.slice(0, 800),
    expectedPhrase: phrase.label,
    recognisedWords: words.filter((word) => haystack.includes(word)),
    recognisedAll: words.every((word) => haystack.includes(word)),
    usedPracticeText: /local practice transcript/i.test(text),
  };
}

async function openCapture(page, attempts = 6) {
  for (let index = 0; index < attempts; index += 1) {
    await page.keyboard.press('Control+Shift+F');
    try {
      await page.waitForSelector("[data-testid='fix-capture-overlay']", { timeout: 2500 });
      return;
    } catch {
      await wait(1200);
    }
  }
  throw new Error('Ctrl+Shift+F never opened the capture overlay');
}

/** Mode: Fix Capture end to end — and, with an unusable key, its honest failure path. */
async function runFixCapture(page, expectFailure) {
  const phrase = PHRASES[PHRASE];
  await goto(page, '#/settings/about');
  await openCapture(page);
  await page.click('button:has-text("Check for updates")');
  await page.waitForSelector("[data-testid='fix-capture-panel'][data-phase='recording']", { timeout: 25000 });
  await wait(RECORD_MS);
  await page.keyboard.press('Control+Shift+F');
  await page.waitForSelector("[data-testid='fix-capture-panel'][data-phase='review']", { timeout: 90000 });
  const transcript = (await page.inputValue("[data-testid='fix-capture-transcript']")).trim();
  const note = (await page.locator("[data-testid='fix-capture-note']").innerText().catch(() => '')).replace(/\s+/g, ' ').trim();
  const retryAvailable = (await page.locator("[data-testid='fix-capture-retry']").count()) > 0;
  await page.screenshot({ path: path.join(OUT_DIR, `${expectFailure ? 'failure' : 'fix-capture'}-${STAMP}.png`) });

  if (expectFailure) {
    let afterRetry = '';
    let noteAfterRetry = '';
    if (retryAvailable) {
      await page.click("[data-testid='fix-capture-retry']");
      await wait(8000);
      afterRetry = (await page.inputValue("[data-testid='fix-capture-transcript']")).trim();
      noteAfterRetry = (await page.locator("[data-testid='fix-capture-note']").innerText().catch(() => '')).replace(/\s+/g, ' ').trim();
    }
    const saveDisabled = (await page.locator("[data-testid='fix-capture-save']").first().evaluate(
      (element) => element.disabled
    ).catch(() => null));
    const everything = `${note} ${noteAfterRetry} ${transcript} ${afterRetry}`;
    return {
      phase: 'review',
      transcript,
      note,
      retryAvailable,
      afterRetry,
      noteAfterRetry,
      saveDisabled,
      // Muse can refuse at the handshake (no session) or at the transcription itself; either way the
      // panel must say something true and must never fall back to invented or practice words.
      truthfulError: note.length > 0,
      noCannedText: !/local practice transcript/i.test(everything),
      noInventedWords: transcript === '' && afterRetry === '',
    };
  }

  await page.click("[data-testid='fix-capture-save']");
  const panel = page.locator("[data-testid='fix-capture-panel']");
  await panel.locator('text=/Saved as FIX-/').first().waitFor({ timeout: 60000 });
  const savedText = (await panel.innerText()).replace(/\s+/g, ' ').trim();
  const id = (savedText.match(/FIX-\d+/) || [null])[0];
  const words = phrase.words.map((word) => word.toLowerCase());
  const haystack = transcript.toLowerCase();
  await goto(page, '#/dogfood');
  const pageText = await bodyText(page);
  return {
    fixId: id,
    transcript: transcript.slice(0, 800),
    expectedPhrase: phrase.label,
    recognisedWords: words.filter((word) => haystack.includes(word)),
    recognisedAll: words.every((word) => haystack.includes(word)),
    usedPracticeText: /local practice transcript/i.test(transcript),
    visibleInDogfood: Boolean(id) && pageText.includes(id) && pageText.includes(transcript.slice(0, 30)),
  };
}

/** Mode: no fake audio — does the app open the real microphone, and is the room quiet? */
async function runDeviceCheck(page) {
  const report = await page.evaluate(async () => {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const mics = devices.filter((entry) => entry.kind === 'audioinput').map((entry) => entry.label || '(unlabelled)');
    let opened = false;
    let peak = 0;
    let error = '';
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      opened = true;
      const context = new AudioContext({ sampleRate: 24000 });
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      const data = new Float32Array(analyser.fftSize);
      for (let index = 0; index < 20; index += 1) {
        await new Promise((resolve) => setTimeout(resolve, 150));
        analyser.getFloatTimeDomainData(data);
        for (const value of data) peak = Math.max(peak, Math.abs(value));
      }
      stream.getTracks().forEach((track) => track.stop());
      await context.close();
    } catch (caught) {
      error = String(caught);
    }
    return { mics, opened, peak, error };
  });
  return { ...report, peakIsSilence: report.peak < 0.005 };
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const result = {
    mode: MODE,
    phrase: MODE === 'transcriptions' ? 'a' : PHRASE,
    startedAt: new Date().toISOString(),
    app: APP,
    dataRoot: DATA_ROOT,
    consoleErrors: [],
  };
  const fakeAudio = ['transcriptions', 'fix-capture', 'failure'].includes(MODE);
  const args = [];
  if (fakeAudio) {
    // Both flags are required: the fake device makes getUserMedia reproducible, the file becomes its
    // audio. Without the device flag the file is ignored and the capture is silence.
    args.push(
      '--use-fake-device-for-media-stream',
      '--use-fake-ui-for-media-stream',
      `--use-file-for-fake-audio-capture=${PHRASES[PHRASE].file}`
    );
  }
  const env = MODE === 'failure' ? { META_API_KEY: 'invalid-muse-key-for-the-failure-path' } : {};
  const port = await freePort();
  const child = launchApp(port, args, env, `${MODE}-${STAMP}.log`);
  let session = null;
  try {
    await waitForCdp(port);
    session = await attach(port, result.consoleErrors);
    const { page } = session;
    const before = engineFacts();
    result.before = { fixes: (before.fixes || []).length, transcripts: (before.transcripts || []).length };
    if (MODE === 'transcriptions') result.transcriptions = await runTranscriptions(page);
    else if (MODE === 'fix-capture') result.fixCapture = await runFixCapture(page, false);
    else if (MODE === 'failure') result.failure = await runFixCapture(page, true);
    else result.device = await runDeviceCheck(page);
    const after = engineFacts();
    result.after = {
      fixes: (after.fixes || []).length,
      newestFix: (after.fixes || [])[(after.fixes || []).length - 1] || null,
      newestTranscript: (after.transcripts || [])[0] || null,
    };
    if (MODE === 'failure') {
      const practice =
        'This is a local practice transcript so the recording and saving flow can be used before a transcription key is connected.';
      result.practiceGuard = await engineCall('/api/dogfood', { action: 'save', transcript: practice });
      result.noFixSavedOnFailure = (after.fixes || []).length === (before.fixes || []).length;
    }
  } finally {
    await stopApp(child, session ? session.browser : null);
    await wait(1200);
    let processes = '';
    try {
      processes = execFileSync('tasklist', { encoding: 'utf8' });
    } catch {
      processes = '';
    }
    result.orphanEngineProcesses = (processes.match(/KelEngine\.exe/gi) || []).length;
    fs.writeFileSync(OUT_FILE, JSON.stringify(result, null, 2), 'utf8');
    console.log(JSON.stringify(result, null, 2));
    console.log('evidence:', OUT_FILE);
  }
}

main().catch((error) => {
  console.error('MUSE VERIFICATION FAILED:', error && error.stack ? error.stack : error);
  process.exit(1);
});
