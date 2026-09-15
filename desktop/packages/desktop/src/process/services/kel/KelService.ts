/** Kel integration: connect the donor UI host to the durable Kel engine. */
import { app, ipcMain } from 'electron';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { recoverHistory, type HistoryMessage } from './reconcileHistory';
type Descriptor = { url: string; token: string; engine_version: string };
let descriptor: Descriptor;
const dataRoot = () => process.env.KEL_DATA_DIR || path.join(app.getPath('appData'), 'kel-desktop', 'work');
async function kelRequest(route: string, body?: unknown) {
  const address = new URL(descriptor.url);
  if (address.protocol !== 'http:' || address.hostname !== '127.0.0.1') throw new Error('Invalid local Kel address');
  const response = await fetch(new URL(route, descriptor.url), {
    signal: AbortSignal.timeout(30000),
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: 'Bearer ' + descriptor.token, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error((await response.json()).error || 'Kel request failed');
  return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.text();
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
    if (drained || !descriptor) return;
    event.preventDefault();
    drained = true;
    kelRequest('/api/shutdown-idle', {})
      .catch(() => undefined)
      .finally(() => {
        setTimeout(() => app.quit(), 50);
      });
  });
  const descriptorPath = path.join(root, 'desktop-session.json');
  let connected = false;
  try {
    descriptor = JSON.parse(fs.readFileSync(descriptorPath, 'utf8'));
    await kelRequest('/api/state');
    connected = true;
    console.log('[KEL-BOOT] initializeKel reused running engine');
  } catch {
    console.log('[KEL-BOOT] initializeKel no live engine; spawning');
  }
  const packed = path.join(process.resourcesPath, 'kel-engine', 'KelEngine.exe');
  const source = process.env.KEL_SOURCE_ROOT || path.resolve(process.cwd(), '../runtime');
  // AionCore validates the ACP agent's CLI via its whitespace-split `binary_name`
  // (`cli_not_found` on any spaced path). Stage the bundled engine into the
  // space-free application-data directory so agent registration and ACP spawn
  // never depend on the install path. Falls back to the packed path when it is
  // already space-free or when even the data dir contains spaces.
  const engineCommand = (() => {
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
  const command = engineCommand.command;
  const baseArgs = engineCommand.baseArgs;
  if (!connected) {
    const log = fs.openSync(path.join(root, 'desktop.log'), 'a');
    const child = spawn(command, [...baseArgs, '--data', root], {
      cwd: engineCommand.cwd,
      detached: true,
      windowsHide: true,
      stdio: ['ignore', log, log],
    });
    child.unref();
    fs.closeSync(log);
    console.log('[KEL-BOOT] initializeKel spawned engine child');
    const deadline = Date.now() + 45000;
    while (Date.now() < deadline) {
      try {
        descriptor = JSON.parse(fs.readFileSync(descriptorPath, 'utf8'));
        await kelRequest('/api/state');
        connected = true;
        break;
      } catch {
        await new Promise((r) => setTimeout(r, 250));
      }
    }
    if (!connected) throw new Error('Kel engine did not start. See desktop.log.');
  }
  console.log('[KEL-BOOT] initializeKel engine ready');
  async function core(route: string, body?: unknown, method?: string) {
    const r = await fetch(`http://127.0.0.1:${port}${route}`, {
      method: method || (body === undefined ? 'GET' : 'POST'),
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`AionUI integration ${route}: ${r.status} ${await r.text()}`);
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
      !/^\/api\/(state(?:\?conversation=[a-zA-Z0-9-]+)?|work\?conversation=[a-zA-Z0-9-]+|project|send|memory|map|recipes|control|approval|retry|apply|artifact\?job=[a-zA-Z0-9-]+&milestone=[a-zA-Z0-9_-]+)$/.test(
        route
      )
    )
      throw new Error('Unknown Kel action');
    return kelRequest(route, body);
  });
}
