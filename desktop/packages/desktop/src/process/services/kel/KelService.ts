/** Kel integration: connect the donor UI host to the durable Kel engine. */
import { app, BrowserWindow, ipcMain, shell } from 'electron';
import { spawn, type ChildProcess } from 'child_process';
import fs from 'fs';
import path from 'path';
import { recoverHistory, type HistoryMessage } from './reconcileHistory';
import { engineVersionAccepted } from './engineVersion';
import { EngineHealthMachine } from './engineHealth';
import { credentialStatus, getCredential, removeCredential, setCredential } from './kelCredentials';
type Descriptor = { url: string; token: string; engine_version: string };
let descriptor: Descriptor;
const dataRoot = () => process.env.KEL_DATA_DIR || path.join(app.getPath('appData'), 'kel-desktop', 'work');
async function kelRequest(route: string, body?: unknown, timeoutMs = 30000) {
  const address = new URL(descriptor.url);
  if (address.protocol !== 'http:' || address.hostname !== '127.0.0.1') throw new Error('Invalid local Kel address');
  const response = await fetch(new URL(route, descriptor.url), {
    signal: AbortSignal.timeout(timeoutMs),
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: 'Bearer ' + descriptor.token, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error((await response.json()).error || 'Kel request failed');
  return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.text();
}

// --------------------------------------------------------------------------------------------
// Batch 6 (visual findings 16/17): engine launch helpers + honest supervision.
// The launch helpers are shared by the first boot and by the supervised restart; the health
// machine (./engineHealth) decides when a restart is due and never claims success it has not
// observed. States are presentation-only — durable truth stays in the engine's own records.
// --------------------------------------------------------------------------------------------
const HEALTH_INTERVAL_MS = 5000;
const HEALTH_TIMEOUT_MS = 4000;
const PATIENT_PING_TIMEOUT_MS = 20000;
const ENGINE_WAIT_MS = 45000;
let spawnedByUs = false;
let quitRequested = false;
let healthMachine: EngineHealthMachine | undefined;
let healthTimer: NodeJS.Timeout | undefined;
let restartInFlight = false;
let lastBroadcastState = '';

function engineLaunchSpec() {
  const packed = path.join(process.resourcesPath, 'kel-engine', 'KelEngine.exe');
  const source = process.env.KEL_SOURCE_ROOT || path.resolve(process.cwd(), '../runtime');
  // AionCore validates the ACP agent's CLI via its whitespace-split `binary_name`
  // (`cli_not_found` on any spaced path). Stage the bundled engine into the
  // space-free application-data directory so agent registration and ACP spawn
  // never depend on the install path. Falls back to the packed path when it is
  // already space-free or when even the data dir contains spaces.
  const command = (() => {
    if (!fs.existsSync(packed)) {
      return { command: process.env.KEL_PYTHON || 'python', baseArgs: ['-m', 'kel.service'], cwd: source };
    }
    if (!/\s/.test(packed)) {
      return { command: packed, baseArgs: [], cwd: path.dirname(packed) };
    }
    const stagedDir = path.join(dataRoot(), 'engine');
    const staged = path.join(stagedDir, 'KelEngine.exe');
    if (!/\s/.test(staged) && fs.existsSync(path.join(process.resourcesPath, 'kel-engine', '_internal'))) {
      try {
        let fresh = false;
        if (!fs.existsSync(staged)) fresh = true;
        else {
          const ps = fs.statSync(packed);
          const ss = fs.statSync(staged);
          fresh = ps.size !== ss.size || ps.mtimeMs > ss.mtimeMs;
        }
        if (fresh) {
          fs.cpSync(path.join(process.resourcesPath, 'kel-engine'), stagedDir, { recursive: true, force: true });
          console.log('[KEL-BOOT] staged engine into space-free data dir');
        }
        return { command: staged, baseArgs: [], cwd: stagedDir };
      } catch (error) {
        console.warn('[Kel] Engine staging failed; using packed path.', error);
      }
    }
    return { command: packed, baseArgs: [], cwd: path.dirname(packed) };
  })();
  return { ...command, packed, source };
}

function expectedEngineVersion(): string {
  return process.env.KEL_ENGINE_VERSION || (app.isPackaged ? app.getVersion() : '');
}

async function expectedEngineAnswered(): Promise<boolean> {
  const state = (await kelRequest('/api/state', undefined, HEALTH_TIMEOUT_MS)) as
    | { engine_version?: string }
    | undefined;
  return engineVersionAccepted(state?.engine_version, expectedEngineVersion());
}

function spawnEngine(root: string): ChildProcess {
  const spec = engineLaunchSpec();
  const log = fs.openSync(path.join(root, 'desktop.log'), 'a');
  // V1.5 credential injection: Kel-managed values are decrypted in the main process at engine
  // spawn and passed only through this child's environment. Values never enter the renderer, the
  // engine database, exports, or logs; native children and test commands strip them again.
  const injectedEnv: NodeJS.ProcessEnv = { ...process.env };
  const anthropicKey = getCredential('anthropic', 'api_key');
  if (anthropicKey) injectedEnv.ANTHROPIC_API_KEY = anthropicKey;
  const child = spawn(spec.command, [...spec.baseArgs, '--data', root], {
    cwd: spec.cwd,
    detached: true,
    windowsHide: true,
    env: injectedEnv,
    stdio: ['ignore', log, log],
  });
  child.unref();
  fs.closeSync(log);
  spawnedByUs = true;
  return child;
}

async function waitForEngineReady(child: ChildProcess | null, descriptorPath: string): Promise<boolean> {
  const deadline = Date.now() + ENGINE_WAIT_MS;
  while (Date.now() < deadline) {
    // A spawn that failed outright (missing binary, refused start) must be reported fast — the
    // person should not wait out a full deadline for a process that never existed.
    if (child && child.exitCode !== null) return false;
    try {
      descriptor = JSON.parse(fs.readFileSync(descriptorPath, 'utf8'));
      // The descriptor file is shared with any leftover engine: keep waiting until the engine
      // this build expects answers instead of connecting to whatever answers first (A1 / ENG-01).
      if (!(await expectedEngineAnswered())) throw new Error('waiting for the expected engine');
      return true;
    } catch {
      await new Promise((r) => setTimeout(r, 250));
    }
  }
  return false;
}

function engineStateFrame() {
  const snap = healthMachine?.snapshot();
  return {
    state: snap?.state ?? 'starting',
    attempts: snap?.restarts ?? 0,
    maxAttempts: snap?.maxRestarts ?? 2,
    at: snap?.at ?? Date.now(),
  };
}

function broadcastEngineState(force = false): void {
  const frame = engineStateFrame();
  const key = `${frame.state}:${frame.attempts}`;
  if (!force && key === lastBroadcastState) return;
  lastBroadcastState = key;
  // Packaged evidence + support: link transitions land beside the engine log (the packaged app
  // has no console). Best-effort only — logging must never break supervision.
  try {
    fs.appendFileSync(
      path.join(dataRoot(), 'desktop-link.log'),
      `[KEL-LINK] ${new Date().toISOString()} state=${frame.state} attempts=${frame.attempts}\n`
    );
  } catch {
    // Best effort.
  }
  for (const window of BrowserWindow.getAllWindows()) {
    try {
      window.webContents.send('kel:engine-state', frame);
    } catch {
      // Window disposed mid-broadcast: nothing to do.
    }
  }
}

async function healthPing(): Promise<boolean> {
  try {
    await kelRequest('/api/state', undefined, HEALTH_TIMEOUT_MS);
    return true;
  } catch {
    return false;
  }
}

async function performEngineRestart(root: string, descriptorPath: string): Promise<void> {
  if (restartInFlight || quitRequested) return;
  restartInFlight = true;
  try {
    // Give a slow-but-alive engine a patient chance to answer first: it must never be duplicated
    // (two engines would share one data root). Only a confirmed unreachable engine is re-spawned.
    try {
      await kelRequest('/api/state', undefined, PATIENT_PING_TIMEOUT_MS);
      healthMachine?.alive();
      broadcastEngineState(true);
      return;
    } catch {
      // Confirmed unreachable — fall through to the restart.
    }
    const child = spawnEngine(root);
    const ok = await waitForEngineReady(child, descriptorPath);
    healthMachine?.restartFinished(ok);
    broadcastEngineState(true);
  } finally {
    restartInFlight = false;
  }
}

async function engineHealthTick(root: string, descriptorPath: string): Promise<void> {
  if (restartInFlight || quitRequested) return;
  const machine = healthMachine;
  if (!machine) return;
  const ok = await healthPing();
  const decision = ok ? machine.alive() : machine.missed();
  broadcastEngineState();
  if (decision.action === 'restart') await performEngineRestart(root, descriptorPath);
}

function startEngineSupervision(root: string, descriptorPath: string): void {
  healthMachine = new EngineHealthMachine();
  lastBroadcastState = '';
  broadcastEngineState(true);
  if (healthTimer) clearInterval(healthTimer);
  healthTimer = setInterval(() => {
    void engineHealthTick(root, descriptorPath);
  }, HEALTH_INTERVAL_MS);
  healthTimer.unref?.();
}

function readLogTail(root: string, lines = 40): string {
  try {
    const file = path.join(root, 'desktop.log');
    const size = fs.statSync(file).size;
    const start = Math.max(0, size - 16 * 1024);
    const fd = fs.openSync(file, 'r');
    const buffer = Buffer.alloc(size - start);
    fs.readSync(fd, buffer, 0, buffer.length, start);
    fs.closeSync(fd);
    return buffer.toString('utf8').split(/\r?\n/).slice(-lines).join('\n');
  } catch {
    return '';
  }
}

export async function initializeKel(port: number): Promise<void> {
  console.log(`[KEL-BOOT] initializeKel entry (aioncorePort=${port})`);
  const root = dataRoot();
  fs.mkdirSync(root, { recursive: true });
  // Register the drain hook FIRST: if anything below fails, a quit must still
  // ask the engine to stop so a failed startup never orphans KelEngine.
  // The hook blocks the quit briefly so the HTTP drain cannot race process exit.
  // Registered without removeAllListeners: other before-quit handlers (e.g. the
  // config flush) must keep running.
  let drained = false;
  app.on('before-quit', (event) => {
    quitRequested = true;
    // Batch 6 (findings 16/17) — the loaded gun: only the instance that SPAWNED the engine may
    // ask it to stop. An instance that merely reused a running engine (second window, second
    // launch) must never stop an engine someone else is using when it quits.
    if (drained || !descriptor || !spawnedByUs) return;
    event.preventDefault();
    drained = true;
    kelRequest('/api/shutdown-idle', {})
      .catch((): undefined => undefined)
      .finally(() => {
        setTimeout(() => app.quit(), 50);
      });
  });
  const descriptorPath = path.join(root, 'desktop-session.json');
  let connected = false;
  try {
    descriptor = JSON.parse(fs.readFileSync(descriptorPath, 'utf8'));
    if (!(await expectedEngineAnswered())) throw new Error('stale engine descriptor');
    connected = true;
    console.log('[KEL-BOOT] initializeKel reused running engine');
  } catch {
    console.log('[KEL-BOOT] initializeKel no live engine; spawning');
  }
  // Audit A1 / ENG-01: something answering /api/state is not proof that it is the engine this build
  // shipped with — an upgrade replaces `resources/kel-engine`, so a leftover engine of another
  // version must not be reused. `expectedEngineAnswered` (module scope) enforces this at every
  // connect, including supervised restarts.
  const launch = engineLaunchSpec();
  const { packed, source } = launch;
  const command = launch.command;
  const baseArgs = launch.baseArgs;
  if (!connected) {
    const child = spawnEngine(root);
    console.log('[KEL-BOOT] initializeKel spawned engine child');
    if (!(await waitForEngineReady(child, descriptorPath))) throw new Error('Kel engine did not start. See desktop.log.');
  }
  console.log('[KEL-BOOT] initializeKel engine ready');
  startEngineSupervision(root, descriptorPath);
  async function core(route: string, body?: unknown, method?: string) {
    const r = await fetch(`http://127.0.0.1:${port}${route}`, {
      method: method || (body === undefined ? 'GET' : 'POST'),
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`Kel integration ${route}: ${r.status} ${await r.text()}`);
    if (r.status === 204) return null;
    const payload = await r.json();
    return payload.data ?? payload;
  }
  const agents = await core('/api/agents/management');
  console.log('[KEL-BOOT] initializeKel agents/management ok');
  const found = agents.find((a: { name: string }) => a.name === 'Kel');
  const spec = {
    name: 'Kel',
    command,
    args: fs.existsSync(packed) ? ['--acp', '--data', root] : [path.join(source, 'kel', 'acp_host.py'), '--data', root],
    env: fs.existsSync(packed) ? [] : [{ name: 'PYTHONPATH', value: source }],
    advanced: { description: 'One assistant. Durable work and checked results.' },
  };
  const agent = found
    ? await core('/api/agents/custom/' + (found.custom_agent_id || found.id), spec, 'PUT')
    : await core('/api/agents/custom', spec);
  console.log('[KEL-BOOT] initializeKel agent registered');
  const all = await core('/api/assistants');
  if (!all.some((a: { id: string }) => a.id === 'kel'))
    await core('/api/assistants', {
      id: 'kel',
      name: 'Kel',
      agent_id: agent.id,
      description: 'Your assistant for projects and everyday work.',
      disabled_builtin_skills: [
        'aionui-config',
        'conversation-create',
        'cron',
        'officecli',
        'session-message',
        'skill-creator',
      ],
      recommended_prompts: [
        'Explain this project in plain words.',
        'Review this project and suggest the next useful change.',
      ],
    });
  for (const a of await core('/api/assistants')) {
    if (a.enabled !== (a.id === 'kel'))
      await core('/api/assistants/' + a.id + '/state', { enabled: a.id === 'kel' }, 'PATCH');
  }
  console.log('[KEL-BOOT] initializeKel assistants enforced');
  const mapPath = path.join(root, 'aion-conversations.json');
  const historyPath = path.join(root, 'aion-history.json');
  const mapping: Record<string, string> = fs.existsSync(mapPath) ? JSON.parse(fs.readFileSync(mapPath, 'utf8')) : {};
  const history: Record<string, unknown[]> = fs.existsSync(historyPath)
    ? JSON.parse(fs.readFileSync(historyPath, 'utf8'))
    : {};
  const liveMapDir = path.join(root, 'aion-session-map');
  if (fs.existsSync(liveMapDir))
    for (const file of fs.readdirSync(liveMapDir).filter((n) => n.endsWith('.json')))
      Object.assign(mapping, JSON.parse(fs.readFileSync(path.join(liveMapDir, file), 'utf8')));
  const saved = await kelRequest('/api/state');
  console.log('[KEL-BOOT] initializeKel engine state ok');
  const catalog = await core('/api/conversations?page_size=200');
  for (const donor of catalog.items || [])
    if (donor.extra?.kel_conversation_id) mapping[donor.id] = donor.extra.kel_conversation_id;
  const mapped = new Set(Object.values(mapping));
  for (const conversation of saved.conversations) {
    if (mapped.has(conversation.id)) continue;
    const existing = await kelRequest('/api/state?conversation=' + conversation.id);
    if (!existing.messages.length && !existing.jobs.length) continue;
    const project = saved.projects.find((item: { id: string }) => item.id === conversation.project_id);
    const workspace = project?.root || path.join(root, 'aion-workspaces', conversation.id);
    fs.mkdirSync(workspace, { recursive: true });
    const donor = await core('/api/conversations', {
      type: 'acp',
      name: conversation.title,
      assistant: { id: 'kel' },
      extra: { workspace, custom_workspace: Boolean(project?.root), kel_conversation_id: conversation.id },
    });
    mapping[donor.id] = conversation.id;
    history[donor.id] = existing.messages.map((message: { seq: number; at: number; role: string; text: string }) => ({
      id: 'kel-history-' + message.seq,
      msg_id: 'kel-history-' + message.seq,
      type: 'text',
      position: message.role === 'user' ? 'right' : 'left',
      conversation_id: donor.id,
      created_at: message.at * 1000,
      content: { content: message.text },
    }));
    for (const [file, value] of [
      [mapPath, mapping],
      [historyPath, history],
    ] as const) {
      fs.writeFileSync(file + '.tmp', JSON.stringify(value));
      fs.renameSync(file + '.tmp', file);
    }
  }
  // Reconcile before any renderer/ACP session opens, so streaming messages
  // cannot race this snapshot. Original Kel and donor databases stay untouched.
  async function reconcile(id: string, cid: string) {
    const info = await core('/api/conversations/' + encodeURIComponent(id));
    if (info.runtime?.is_processing) return;
    const native: HistoryMessage[] = [];
    let before = '';
    try {
      for (let page = 0; ; page++) {
        if (page >= 1000) throw new Error('Kel history recovery exceeded its page limit');
        const result = await core(
          '/api/conversations/' +
            encodeURIComponent(id) +
            '/messages?limit=200&content_mode=full' +
            (before ? '&before=' + encodeURIComponent(before) : '')
        );
        native.unshift(...result.items);
        if (!result.has_more_before) break;
        if (!result.oldest_cursor || result.oldest_cursor === before)
          throw new Error('Kel history recovery returned an invalid cursor');
        before = result.oldest_cursor;
      }
    } catch (error) {
      if (String(error).includes(': 404 ')) return; // Deleted donor conversation.
      throw error;
    }
    const current = await kelRequest('/api/state?conversation=' + cid);
    history[id] = recoverHistory(id, (history[id] || []) as HistoryMessage[], current.messages, native);
    // In-chat approvals (V1.6): one card anchored to the message Kel posted, so the
    // conversation shows the decision where it belongs - pending and settled alike.
    try {
      const approvals = (await kelRequest(
        '/api/approvals?conversation=' + encodeURIComponent(cid)
      )) as {
        items?: Array<{
          id: string;
          kind: 'access' | 'action';
          message_seq?: number | null;
          message_at?: number | null;
          created?: number | null;
        }>;
      };
      for (const item of approvals?.items || []) {
        if (!item?.message_seq) continue;
        const anchorId = 'kel-approval-' + item.kind + '-' + item.id;
        if (history[id].some((row: HistoryMessage) => row.id === anchorId)) continue;
        history[id].push({
          id: anchorId,
          msg_id: anchorId,
          type: 'kel_approval',
          position: 'left',
          conversation_id: id,
          created_at: (item.message_at ?? item.created ?? 0) * 1000 + 1,
          content: { kind: item.kind, ref_id: item.id },
        });
      }
    } catch {
      // Approvals view unavailable: chat keeps its plain messages; the next
      // reconcile (or any job-state change) retries automatically.
    }
    // A disconnected ACP stream cannot update its old progress row. Project
    // the engine's current verdict over that row without changing donor storage.
    for (const row of native) {
      if (row.type !== 'acp_tool_call') continue;
      const content = row.content as unknown as { update: { tool_call_id: string; status: string; title: string } };
      const job = current.jobs.find((item: { id: string }) => item.id === content.update?.tool_call_id);
      if (!job) continue;
      const status =
        job.state === 'CLOSED'
          ? job.verdict === 'VERIFIED'
            ? 'completed'
            : 'failed'
          : job.state === 'CANCELLED'
            ? 'failed'
            : ['PAUSED', 'AWAITING_USER', 'WAITING_RESOURCE'].includes(job.state)
              ? 'pending'
              : 'in_progress';
      history[id] = history[id].filter((item) => (item as { id: string }).id !== row.id);
      history[id].push({
        ...row,
        content: {
          ...content,
          update: { ...content.update, status, title: 'Kel work: ' + job.state + ' / ' + job.verdict },
        },
      });
    }
  }
  for (const [id, cid] of Object.entries(mapping)) {
    try {
      await reconcile(id, cid);
    } catch (error) {
      if (!String(error).includes(': 404 ')) throw error;
      // Stale mapping: the donor conversation is gone; drop the pair so the
      // catalog never re-imports a dead mapping on later launches.
      delete mapping[id];
      delete history[id];
    }
  }
  fs.writeFileSync(historyPath + '.tmp', JSON.stringify(history));
  fs.renameSync(historyPath + '.tmp', historyPath);
  ipcMain.removeHandler('kel:conversation');
  ipcMain.handle('kel:conversation', (event, id: string) => {
    if (event.senderFrame !== event.sender.mainFrame || !event.senderFrame?.url.startsWith('file:'))
      throw new Error('Unknown Kel window');
    if (mapping[id]) return mapping[id];
    if (fs.existsSync(liveMapDir))
      for (const file of fs.readdirSync(liveMapDir).filter((n) => n.endsWith('.json'))) {
        const live = JSON.parse(fs.readFileSync(path.join(liveMapDir, file), 'utf8'));
        if (live[id]) return live[id];
      }
    return null;
  });
  ipcMain.removeHandler('kel:history-search');
  ipcMain.handle('kel:history-search', (event, query: string) => {
    if (event.senderFrame !== event.sender.mainFrame || !event.senderFrame?.url.startsWith('file:'))
      throw new Error('Unknown Kel window');
    if (typeof query !== 'string' || query.trim().length < 1) return [];
    return Object.values(history)
      .flat()
      .filter((row) =>
        String((row as { content: { content?: string } }).content.content || '')
          .toLocaleLowerCase()
          .includes(query.toLocaleLowerCase())
      );
  });
  ipcMain.removeHandler('kel:history');
  ipcMain.handle('kel:history', async (event, id: string) => {
    if (event.senderFrame !== event.sender.mainFrame || !event.senderFrame?.url.startsWith('file:'))
      throw new Error('Unknown Kel window');
    if (!mapping[id] && fs.existsSync(liveMapDir))
      for (const file of fs.readdirSync(liveMapDir).filter((n) => n.endsWith('.json')))
        Object.assign(mapping, JSON.parse(fs.readFileSync(path.join(liveMapDir, file), 'utf8')));
    if (mapping[id]) {
      const before = JSON.stringify(history[id]);
      await reconcile(id, mapping[id]);
      if (JSON.stringify(history[id]) !== before) {
        fs.writeFileSync(historyPath + '.tmp', JSON.stringify(history));
        fs.renameSync(historyPath + '.tmp', historyPath);
      }
    }
    return history[id] || [];
  });
  // The engine drain hook was registered at the top of initializeKel so a
  // quit during ANY later failure still stops a freshly spawned engine.
  ipcMain.removeHandler('kel:request');
  ipcMain.handle('kel:request', async (event, route: string, body?: unknown) => {
    const url = event.senderFrame?.url || '';
    if (
      event.senderFrame !== event.sender.mainFrame ||
      (!url.startsWith('file:') && !url.startsWith('http://localhost:'))
    )
      throw new Error('Unknown Kel window');
    if (
      !/^\/api\/(state(?:\?conversation=[a-zA-Z0-9-]+)?|work\?conversation=[a-zA-Z0-9-]+|project|send|memory|map|recipes|brief|team|vetting|transcription|model|capabilities|data-path|backup|search|providers|autonomy|diagnostics|control|approval|approvals(?:\?conversation=[a-zA-Z0-9-]+)?|retry|apply|lineage\?job=[a-zA-Z0-9-]+(?:&milestone=[a-zA-Z0-9_-]+)?|artifact\?job=[a-zA-Z0-9-]+&milestone=[a-zA-Z0-9_-]+|artifact\?lineage=[a-zA-Z0-9-]+)$/.test(
        route
      )
    )
      throw new Error('Unknown Kel action');
    return kelRequest(route, body);
  });
  // Batch 6 (findings 16/17): the shell's honest view of the engine link, plus the support
  // actions the failure surfaces offer. Presentation-only — no durable state is owned here.
  const guardKelWindow = (event: Electron.IpcMainInvokeEvent) => {
    const url = event.senderFrame?.url || '';
    if (event.senderFrame !== event.sender.mainFrame || (!url.startsWith('file:') && !url.startsWith('http://localhost:')))
      throw new Error('Unknown Kel window');
  };
  ipcMain.removeHandler('kel:engine-state');
  ipcMain.handle('kel:engine-state', (event) => {
    guardKelWindow(event);
    return engineStateFrame();
  });
  ipcMain.removeHandler('kel:engine-retry');
  ipcMain.handle('kel:engine-retry', async (event) => {
    guardKelWindow(event);
    const machine = healthMachine;
    if (!machine) return engineStateFrame();
    const decision = machine.manualRetry();
    broadcastEngineState(true);
    if (decision.action === 'restart') await performEngineRestart(root, descriptorPath);
    return engineStateFrame();
  });
  ipcMain.removeHandler('kel:diagnostics');
  ipcMain.handle('kel:diagnostics', (event) => {
    guardKelWindow(event);
    return {
      engineVersion: descriptor?.engine_version,
      address: descriptor?.url,
      state: engineStateFrame(),
      logTail: readLogTail(root),
    };
  });
  // Artifact lineage: reveal a produced artifact in the OS file manager. The renderer sends the
  // store-relative path; main resolves it against the engine root and refuses anything that
  // escapes - the renderer never builds an absolute path.
  ipcMain.removeHandler('kel:artifact-reveal');
  ipcMain.handle('kel:artifact-reveal', (event, relpath: string) => {
    // Same frame guard as the other privileged handlers: only the app's own main frame may ask the
    // OS to reveal a path (audit INT-01 - this handler was the one that skipped the check).
    const url = event.senderFrame?.url || '';
    if (event.senderFrame !== event.sender.mainFrame || !url.startsWith('file:'))
      throw new Error('Unknown Kel window');
    if (typeof relpath !== 'string' || !relpath) throw new Error('Missing artifact path');
    const root = path.resolve(dataRoot());
    const target = path.resolve(root, relpath);
    if (!target.startsWith(root + path.sep)) throw new Error('That path is not inside Kel data');
    shell.showItemInFolder(target);
    return { ok: true };
  });
  // OS-backed credential custody (V1.4 Gate 6): values are encrypted with safeStorage (DPAPI on
  // Windows) in the main process; the engine only ever receives metadata, and no IPC returns a value.
  ipcMain.handle('kel:credential-status', () => credentialStatus());
  ipcMain.handle(
    'kel:credential-set',
    async (event, provider: string, field: string, value: string): Promise<{ provider: string; fields: string[] }> => {
      const stored = setCredential(provider, field, value);
      await kelRequest('/api/providers', {
        action: 'set_credential',
        provider,
        fields: stored.fields,
        credential_ref: `kel:provider:${provider}:${field}`,
      }).catch((): undefined => undefined);
      return { provider: stored.provider, fields: stored.fields };
    }
  );
  ipcMain.handle('kel:credential-delete', async (event, provider: string): Promise<{ provider: string; removed: number }> => {
    const removed = removeCredential(provider);
    await kelRequest('/api/providers', { action: 'delete_credential', provider }).catch(
      (): undefined => undefined
    );
    return removed;
  });
}
