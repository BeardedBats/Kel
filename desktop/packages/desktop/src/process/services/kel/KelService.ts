/** Kel integration: connect the donor UI host to the durable Kel engine. */
import { rendererKelRequestRefusal } from './kelRequestGuard';
import { migrateDonorSchedules } from './scheduleMigration';
import { applyWorkspaceRepairs, listConversationsForRepair, planWorkspaceRepairs } from './repairWorkspacePaths';
import { app, BrowserWindow, ipcMain, shell } from 'electron';
import { spawn, type ChildProcess } from 'child_process';
import fs from 'fs';
import path from 'path';
import {
  donorsForMessages,
  ensureWorkCards,
  historyRow,
  recoverHistory,
  type HistoryMessage,
  type KelMessage,
} from './reconcileHistory';
import { engineVersionAccepted } from './engineVersion';
import { EngineHealthMachine } from './engineHealth';
import { conversationCounts, knownEmpty } from './conversationCounts';
import {
  connectionCredentialKey,
  connectionCredentialStatus,
  credentialStatus,
  getCredential,
  removeCredential,
  setCredential,
} from './kelCredentials';
import { registerKelCredentialIpc } from './kelCredentialIpc';
import { MUSE_ENV, MUSE_FIELD, MUSE_PROVIDER, syncMuseCustody } from './museCustody';
import { registerKelDogfoodIpc } from './kelDogfoodIpc';
import { ChatLinks, chatStoreOverride } from './chatLinks';
import { migrateToOneChatStore } from './chatStoreMigration';
import { getDataPath } from '../../utils/utils';
import { memoryRoot, protectedPaths } from './protectedPaths';
import { assertTrustedSender } from '../../../common/senderGuard';
type Descriptor = { url: string; token: string; engine_version: string };
let descriptor: Descriptor;
/**
 * The Kel engine's data root — the one directory the engine writes its `desktop-session.json` into.
 * Exported because the WebUI gateway must read the descriptor from the *same* root the engine uses;
 * handed a different directory it answered `/kel/*` with the SPA and every Kel surface rendered its
 * failure card while the engine was perfectly healthy.
 */
export const kelDataRoot = () => process.env.KEL_DATA_DIR || path.join(app.getPath('appData'), 'kel-desktop', 'work');
const dataRoot = kelDataRoot;
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
  // Routing 2 §5.6: DeepSeek and OpenRouter keys (saved on the Providers page under the engine's
  // provider id) reach the engine the same way; without one the engine says the key is needed.
  const deepseekKey = getCredential('deepseek', 'api_key');
  if (deepseekKey) injectedEnv.DEEPSEEK_API_KEY = deepseekKey;
  const openrouterKey = getCredential('openrouter', 'api_key');
  if (openrouterKey) injectedEnv.OPENROUTER_API_KEY = openrouterKey;
  // D-75.3: the Muse (Ramble) key from the same custody; the engine takes it out of its environment.
  const museKey = getCredential(MUSE_PROVIDER, MUSE_FIELD);
  if (museKey) injectedEnv[MUSE_ENV] = museKey;
  // FN-01: the installed app and the person's credential folders are off limits to every model
  // runtime; the engine's runtime guard reads this list.
  injectedEnv.KEL_PROTECTED_PATHS = protectedPaths({
    existing: process.env.KEL_PROTECTED_PATHS,
    home: app.getPath('home'),
    appDir: app.isPackaged ? path.dirname(app.getPath('exe')) : undefined,
    appData: process.env.APPDATA,
    localAppData: process.env.LOCALAPPDATA,
  });
  // D-81: the Memory folder beside the installed App — the AI tools' only place to read and write.
  const memory = memoryRoot({
    existing: process.env.KEL_MEMORY_ROOT,
    appDir: app.isPackaged ? path.dirname(app.getPath('exe')) : undefined,
  });
  if (memory) injectedEnv.KEL_MEMORY_ROOT = memory;
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
    // A spawn that failed outright must be reported fast — a missing binary (pid never assigned)
    // or an immediately-dead child should not wait out a full deadline.
    if (child && (child.pid === undefined || child.exitCode !== null)) return false;
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

// CP-2: liveness is a trivial engine route; /api/state read every conversation's rows every 5 s.
const HEALTH_ROUTE = '/api/health';

async function healthPing(): Promise<boolean> {
  try {
    await kelRequest(HEALTH_ROUTE, undefined, HEALTH_TIMEOUT_MS);
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
      await kelRequest(HEALTH_ROUTE, undefined, PATIENT_PING_TIMEOUT_MS);
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
    // Source mode must spawn in module form: `python <path>/kel/acp_host.py` cannot resolve the
    // host's relative imports during ACP `initialize`, while `-m kel.acp_host` does (measured).
    // The packed engine keeps its own `--acp` entry.
    args: fs.existsSync(packed) ? ['--acp', '--data', root] : ['-m', 'kel.acp_host', '--data', root],
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
  // V2-04a: hand the engine the connection values the assistant runtime needs. They live in the
  // engine's memory only (nothing durable), and a renderer still never receives a value.
  try {
    let pushed = 0;
    const held = connectionCredentialStatus();
    for (const id of Object.keys(held)) {
      const credentials: Record<string, string> = {};
      for (const field of held[id] ?? []) {
        const value = getCredential(connectionCredentialKey(id), field);
        if (value) credentials[field] = value;
      }
      if (Object.keys(credentials).length > 0) {
        await kelRequest('/api/connections', { action: 'supply', id, credentials });
        pushed += 1;
      }
    }
    console.log('[KEL-BOOT] initializeKel connection custody pushed (' + pushed + ')');
  } catch (error) {
    console.warn('[Kel] Connection custody push failed; the assistant will ask again when a credential changes.', error);
  }
  // D-75.3: the key Ramble saved before moves into custody once; the engine holds the custody key.
  await syncMuseCustody(kelRequest, { get: getCredential, set: setCredential })
    .then((outcome) => console.log('[KEL-BOOT] initializeKel Muse key: ' + outcome))
    .catch((): undefined => undefined);
  const historyPath = path.join(root, 'aion-history.json');
  // D-80: the first launch of the one chat store archives every existing chat (after a backup) so
  // the sidebar starts empty. A switch that did not finish keeps the legacy links for this run and
  // finishes on the next launch.
  const switched = await migrateToOneChatStore({
    engine: (route, body) => kelRequest(route, body, 120000),
    donor: (route, body, method) => core(route, body, method),
    donorDb: path.join(getDataPath(), 'aionui-backend.db'),
    override: chatStoreOverride(),
  });
  console.log('[KEL-BOOT] initializeKel chat store switch: ' + switched.state);
  // CP-10a (D-77): every read and write of "which conversation is this chat" goes through the one
  // link table (engine `chat_links`), or the old files when the `chat_store` switch says legacy.
  const links = await ChatLinks.open(
    root,
    (route, body) => kelRequest(route, body),
    process.env,
    switched.state === 'failed' ? 'legacy' : undefined
  );
  const oneStore = links.mode === 'engine';
  const switchedAt = switched.state === 'done' || switched.state === 'already' ? switched.switchedAt : 0;
  const mapping = links.map;
  console.log('[KEL-BOOT] initializeKel chat links: ' + links.mode);
  const history: Record<string, unknown[]> = fs.existsSync(historyPath)
    ? JSON.parse(fs.readFileSync(historyPath, 'utf8'))
    : {};
  const saved = await kelRequest('/api/state');
  console.log('[KEL-BOOT] initializeKel engine state ok');
  // Re-home Kel scratch folders that point at a missing or moved data root (e.g. the removed
  // KelV2Runs root) so those chats open instead of failing with a workspace-path error. Archived
  // chats are included, and every active chat is read (a plain catalog read is capped at 20 rows).
  const repairCandidates = await listConversationsForRepair((route) => core(route));
  const workspaceRepairs = await applyWorkspaceRepairs(planWorkspaceRepairs(repairCandidates, root), (id, workspace) =>
    core('/api/conversations/' + encodeURIComponent(id), { extra: { workspace }, merge_extra: true }, 'PATCH')
  );
  if (workspaceRepairs.length) console.log('[KEL-BOOT] re-homed chat folders: ' + workspaceRepairs.length);
  // The same full list feeds the chat mapping, so chats past the first 20 keep their engine link.
  const folded = await links.foldDonorLinks(repairCandidates);
  if (folded.conflicts) console.log('[KEL-BOOT] chat links settled conflicts: ' + folded.conflicts);
  const mapped = new Set(Object.values(mapping));
  // ST-23: one grouped engine query says which conversations are empty, so start-up never reads
  // each empty chat's full state. An older engine without the route falls back to reading each.
  let counts: ReturnType<typeof conversationCounts> = null;
  try {
    counts = conversationCounts(await kelRequest('/api/conversations'));
  } catch {
    counts = null;
  }
  const persistMapping = () => {
    links.persist();
    fs.writeFileSync(historyPath + '.tmp', JSON.stringify(history));
    fs.renameSync(historyPath + '.tmp', historyPath);
  };
  const mergeLiveMap = () => links.refresh();
  const donorFor = (cid: string): string | undefined => links.donorFor(cid);
  type EngineConversationState = {
    messages?: KelMessage[];
    jobs?: unknown[];
    conversations?: Array<{ id: string; title?: string; project_id?: string; hidden?: unknown; utility?: unknown }>;
    projects?: Array<{ id: string; root?: string | null }>;
  };
  const adopting = new Map<string, Promise<string | null>>();
  /**
   * The app chat for one engine conversation, made (and remembered) on first use: the mirror row
   * the sidebar and `/conversation/:id` need. Used at start-up for chats Kel already has, and for
   * a scheduled run's new conversation (D-57) while Kel is open. A hidden conversation (its
   * schedule was deleted, policy 2) is never brought back.
   */
  function adoptEngineConversation(cid: string, known?: EngineConversationState): Promise<string | null> {
    const already = donorFor(cid);
    if (already) return Promise.resolve(already);
    const inFlight = adopting.get(cid);
    if (inFlight) return inFlight;
    const work = (async () => {
      const existing: EngineConversationState =
        known ?? (await kelRequest('/api/state?conversation=' + encodeURIComponent(cid)));
      const conversation = (existing.conversations || []).find((item) => item.id === cid);
      // FN-10: a project's utility chat ("Recipe runs") is Kel's own and never becomes an app chat.
      if (!conversation || conversation.hidden || conversation.utility) return null;
      const project = (existing.projects || []).find((item) => item.id === conversation.project_id);
      const workspace = project?.root || path.join(root, 'aion-workspaces', cid);
      fs.mkdirSync(workspace, { recursive: true });
      const donor = await core('/api/conversations', {
        type: 'acp',
        name: conversation.title,
        assistant: { id: 'kel' },
        extra: { workspace, custom_workspace: Boolean(project?.root), kel_conversation_id: cid, kel_project_id: conversation.project_id },
      });
      await links.adopt(donor.id, cid);
      history[donor.id] = (existing.messages || []).map((message: KelMessage) => historyRow(donor.id, message));
      persistMapping();
      return donor.id as string;
    })().finally(() => adopting.delete(cid));
    adopting.set(cid, work);
    return work;
  }
  // CP-10a stage 3: with the one store a chat's app row is made when it is needed (a scheduled run,
  // opening one), never at start-up.
  for (const conversation of oneStore ? [] : saved.conversations) {
    if (mapped.has(conversation.id)) continue;
    if (conversation.hidden) continue;
    if ((conversation as { utility?: unknown }).utility) continue; // FN-10: Kel's own utility chat
    if (knownEmpty(counts, conversation.id)) continue;
    const existing = await kelRequest('/api/state?conversation=' + conversation.id);
    if (!existing.messages.length && !existing.jobs.length) continue;
    await adoptEngineConversation(conversation.id, existing);
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
    // D-53: a hand-off's live card was streamed once; a conversation reopened later (or a stream
    // that dropped) still shows exactly one card beside its acknowledgement.
    history[id] = ensureWorkCards(history[id] as HistoryMessage[], current.submissions || [], native, id, current.messages);
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
        // The anchored card carries the announcement. Keep the engine message durable,
        // but do not show its sentence a second time immediately above the card.
        history[id] = history[id].filter((row: HistoryMessage) => row.id !== 'kel-history-' + item.message_seq);
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
            ? 'completed' // a stop the person asked for is not a failure
            : ['PAUSED', 'AWAITING_USER', 'WAITING_RESOURCE'].includes(job.state)
              ? 'pending'
              : 'in_progress';
      const title = job.state === 'CANCELLED' ? 'Cancelled' : 'Kel work: ' + job.state + ' / ' + job.verdict;
      history[id] = history[id].filter((item) => (item as { id: string }).id !== row.id);
      history[id].push({
        ...row,
        content: {
          ...content,
          update: { ...content.update, status, title },
        },
      });
    }
  }
  // CP-10a stage 3 (AC-6): with the one store start-up reads no chat's history; a chat is reconciled
  // when it is opened (`kel:history`).
  for (const [id, cid] of oneStore ? [] : links.entries()) {
    try {
      await reconcile(id, cid);
    } catch (error) {
      if (!String(error).includes(': 404 ')) throw error;
      // Stale mapping: the donor conversation is gone; drop the pair so the
      // catalog never re-imports a dead mapping on later launches (engine mode retires the link).
      await links.drop(id, 'app chat gone');
      delete history[id];
    }
  }
  fs.writeFileSync(historyPath + '.tmp', JSON.stringify(history));
  fs.renameSync(historyPath + '.tmp', historyPath);
  ipcMain.removeHandler('kel:conversation');
  ipcMain.handle('kel:conversation', (event, id: string) => {
    assertTrustedSender(event);
    return links.lookup(id);
  });
  ipcMain.removeHandler('kel:history-search');
  ipcMain.handle('kel:history-search', (event, query: string) => {
    assertTrustedSender(event);
    if (typeof query !== 'string' || query.trim().length < 1) return [];
    return Object.values(history)
      .flat()
      // A details overlay repeats a streamed row that the chat's own search already finds.
      .filter((row) => !(row as HistoryMessage).kel_overlay)
      .filter((row) =>
        String((row as { content: { content?: string } }).content.content || '')
          .toLocaleLowerCase()
          .includes(query.toLocaleLowerCase())
      );
  });
  ipcMain.removeHandler('kel:history');
  ipcMain.handle('kel:history', async (event, id: string) => {
    assertTrustedSender(event);
    if (!mapping[id]) await links.refresh();
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
  // LIVE-7: a message that carries details (a scoping card, a result, a quiet note) reaches an open
  // chat at once, not only when the chat is next reopened. The engine is asked cheaply for messages
  // with details written since the last look; each affected chat's history is reconciled as soon as
  // its turn has finished streaming, then the windows are told (`kel:history-updated`, donor id) so
  // the open chat re-reads `kel:history`.
  let seenSeq: number | null = null; // null until the first look sets the starting point
  let watching = false;
  const pendingHistory = new Map<string, number>(); // donor id -> first time it was due
  const historyWatch = async (): Promise<void> => {
    if (watching || quitRequested) return;
    watching = true;
    try {
      const route = seenSeq === null ? '/api/messages/since' : '/api/messages/since?after=' + seenSeq;
      const since = (await kelRequest(route, undefined, HEALTH_TIMEOUT_MS)) as {
        latest?: number;
        items?: Array<{ conversation_id?: string; seq?: number }>;
      };
      if (seenSeq !== null) {
        if (links.mode === 'legacy' || since?.items?.length) await mergeLiveMap();
        for (const donorId of donorsForMessages(links, since?.items))
          if (!pendingHistory.has(donorId)) pendingHistory.set(donorId, Date.now());
      }
      if (typeof since?.latest === 'number') seenSeq = Math.max(seenSeq ?? 0, since.latest);
      for (const [donorId, due] of [...pendingHistory]) {
        const cid = mapping[donorId];
        if (!cid || Date.now() - due > 120000) {
          pendingHistory.delete(donorId);
          continue;
        }
        const info = await core('/api/conversations/' + encodeURIComponent(donorId)).catch((): null => null);
        if (!info) {
          pendingHistory.delete(donorId);
          continue;
        }
        if (info.runtime?.is_processing) continue; // still streaming: look again on the next pass
        const before = JSON.stringify(history[donorId]);
        await reconcile(donorId, cid);
        pendingHistory.delete(donorId);
        if (JSON.stringify(history[donorId]) === before) continue;
        persistMapping();
        for (const window of BrowserWindow.getAllWindows()) {
          try {
            window.webContents.send('kel:history-updated', { conversationId: donorId });
          } catch {
            // Window disposed mid-broadcast: nothing to do.
          }
        }
      }
    } catch {
      // A busy or restarting engine is simply asked again on the next pass.
    } finally {
      watching = false;
    }
  };
  const historyWatchTimer = setInterval(() => void historyWatch(), 1200);
  historyWatchTimer.unref?.();
  // D-57: open an engine conversation (a scheduled run's) as an app chat, making it on first use.
  ipcMain.removeHandler('kel:open-engine-conversation');
  ipcMain.handle('kel:open-engine-conversation', async (event, cid: string) => {
    assertTrustedSender(event);
    if (typeof cid !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(cid)) throw new Error('That conversation is not one Kel knows');
    await mergeLiveMap();
    return adoptEngineConversation(cid);
  });
  // D-57: every 20 s (and right after a schedule changes) bring the chat list in step with the
  // schedules. A scheduled run's new conversation gets its app chat: only engine conversations a
  // schedule created (their row carries `schedule_id`) are adopted, so a chat that is still being
  // opened elsewhere is never doubled. When a schedule is deleted, the engine hides its finished
  // runs' chats (policy 2) and names them; their app chats leave the list here.
  let sweeping = false;
  const hiddenToRemove = new Set<string>();
  const scheduleSweep = async (): Promise<void> => {
    if (sweeping || quitRequested) return;
    sweeping = true;
    try {
      await mergeLiveMap();
      let changed = false;
      for (const cid of [...hiddenToRemove]) {
        const donorId = donorFor(cid);
        if (donorId) {
          try {
            await core('/api/conversations/' + encodeURIComponent(donorId), undefined, 'DELETE');
          } catch (error) {
            if (!String(error).includes(': 404 ')) continue; // Retried on the next sweep.
          }
          await links.drop(donorId, 'schedule deleted');
          delete history[donorId];
          changed = true;
        }
        hiddenToRemove.delete(cid);
      }
      const listed = (await kelRequest('/api/conversations')) as {
        conversations?: Array<{
          id?: unknown;
          schedule_id?: unknown;
          message_count?: unknown;
          job_count?: unknown;
          created?: unknown;
        }>;
      };
      for (const row of listed?.conversations || []) {
        if (typeof row?.id !== 'string' || !row.schedule_id || donorFor(row.id)) continue;
        // D-80: a scheduled run from before the switch belongs to the archived past, not the sidebar.
        if (oneStore && switchedAt && Number(row.created) < switchedAt) continue;
        if (row.message_count === 0 && row.job_count === 0) continue;
        if (await adoptEngineConversation(row.id).catch((): null => null)) changed = true;
      }
      if (changed) persistMapping();
    } catch {
      // A busy engine is simply asked again on the next sweep.
    } finally {
      sweeping = false;
    }
  };
  ipcMain.removeHandler('kel:schedules-changed');
  ipcMain.handle('kel:schedules-changed', async (event, change?: { hidden?: unknown }) => {
    assertTrustedSender(event);
    const hidden = Array.isArray(change?.hidden) ? change.hidden : [];
    for (const cid of hidden) if (typeof cid === 'string' && /^[a-zA-Z0-9_-]{1,128}$/.test(cid)) hiddenToRemove.add(cid);
    await scheduleSweep();
    return { ok: true };
  });
  const scheduleSweepTimer = setInterval(() => void scheduleSweep(), 20000);
  scheduleSweepTimer.unref?.();
  // D-57: move the old scheduler's tasks into the engine once (import first, then switch the old
  // task off). Runs in the background so start-up never waits on it; a failure retries next launch.
  const migrationMarker = path.join(root, 'schedule-migration.json');
  void migrateDonorSchedules({
    engine: (route, body) => kelRequest(route, body),
    donor: (route, body, method) => core(route, body, method),
    engineConversationFor: (donorId) => mapping[donorId],
    isDone: () => fs.existsSync(migrationMarker),
    markDone: (summary) => {
      fs.writeFileSync(migrationMarker + '.tmp', JSON.stringify({ at: new Date().toISOString(), ...summary }));
      fs.renameSync(migrationMarker + '.tmp', migrationMarker);
    },
    log: (line) => console.log(line),
  })
    .then(() => scheduleSweep())
    .catch((error) => console.warn('[KEL-SCHEDULES] migration did not finish; it will retry next launch.', error));
  // The engine drain hook was registered at the top of initializeKel so a
  // quit during ANY later failure still stops a freshly spawned engine.
  ipcMain.removeHandler('kel:request');
  ipcMain.handle('kel:request', async (event, route: string, body?: unknown) => {
    assertTrustedSender(event, { allowDevServer: true });
    // Route allowlist plus body check: credential-bearing actions are main-process only (D-33/D-34).
    const refusal = rendererKelRequestRefusal(route, body);
    if (refusal) throw new Error(refusal);
    return kelRequest(route, body);
  });
  // Batch 6 (findings 16/17): the shell's honest view of the engine link, plus the support
  // actions the failure surfaces offer. Presentation-only — no durable state is owned here.
  const guardKelWindow = (event: Electron.IpcMainInvokeEvent) => {
    assertTrustedSender(event, { allowDevServer: true });
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
    assertTrustedSender(event);
    if (typeof relpath !== 'string' || !relpath) throw new Error('Missing artifact path');
    const root = path.resolve(dataRoot());
    const target = path.resolve(root, relpath);
    if (!target.startsWith(root + path.sep)) throw new Error('That path is not inside Kel data');
    shell.showItemInFolder(target);
    return { ok: true };
  });
  // OS-backed credential custody (V1.4 Gate 6): values are encrypted with safeStorage (DPAPI on
  // Windows) in the main process; the engine only ever receives metadata, and no IPC returns a value.
  // Credential custody IPC (Campaign C AUD-MAJOR-002): the trio now runs the shared sender
  // guard like every other privileged channel; the engine sync stays best-effort.
  // V2-01: the same custody holds Connections' credentials, and the sync is routed to the store that
  // owns that kind of credential — model providers and Connections never share a metadata table.
  registerKelCredentialIpc({
    status: credentialStatus,
    connectionStatus: connectionCredentialStatus,
    set: setCredential,
    remove: removeCredential,
    sync: (route, body) => kelRequest(route, body),
    fieldsFor: (id) => connectionCredentialStatus()[id] ?? [],
    read: (id, field) => getCredential(connectionCredentialKey(id), field),
    // V2-02 Test Connection: the value is decrypted here and used by the engine for one request.
    test: (body) => kelRequest('/api/connections', body),
    // V2-04 actions: same rule — one request, the answer comes back, nothing is kept.
    run: (body) => kelRequest('/api/connections', body),
    // V2-04b: the account sign-in opens in the system browser; the tokens land in this custody.
    openExternal: (url) => {
      void shell.openExternal(url).catch((): undefined => undefined);
    },
  });
  // Fix Capture (V2.0 preflight): the window screenshot is written into the engine data root's
  // dogfood/tmp; the engine commits it under the fix id when the fix is saved.
  registerKelDogfoodIpc({ dataRoot });
}

export const kelEngineDataRoot = (): string => dataRoot();
