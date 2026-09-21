/**
 * V2-05 — the standalone webui's Kel bootstrap.
 *
 * Pins what `ensureKelIntegration` does against a stub aioncore: register the
 * Kel agent with the exact ACP spec, create the single `kel` assistant, force
 * enablement to `kel` only, and stay idempotent and honest on re-runs and
 * backend failures. This mirrors `initializeKel` in the desktop main process;
 * the browser profile the phone uses has no other path to a selectable
 * assistant.
 */
import { describe, it, expect, afterEach } from 'vitest';
import http from 'node:http';
import { ensureKelIntegration } from './kel-integration.js';

type Assistant = Record<string, unknown> & { id: string; enabled?: boolean; agent_id?: string };
type SeenRequest = { method: string; url: string; body: string };

type MockBackend = {
  port: number;
  agents: Array<Record<string, unknown>>;
  assistants: Assistant[];
  requests: SeenRequest[];
  failNext: { status: number; body: string } | null;
  close: () => Promise<void>;
};

async function startMockBackend(
  initial: { agents?: Array<Record<string, unknown>>; assistants?: Assistant[] } = {}
): Promise<MockBackend> {
  const state: MockBackend = {
    port: 0,
    agents: [...(initial.agents ?? [])],
    assistants: [...(initial.assistants ?? [])],
    requests: [],
    failNext: null,
    close: async () => undefined,
  };
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (chunk: Buffer) => (body += chunk.toString()));
    req.on('end', () => {
      const url = req.url || '/';
      const method = req.method || 'GET';
      state.requests.push({ method, url, body });
      const reply = (status: number, payload: unknown) => {
        res.writeHead(status, { 'content-type': 'application/json' });
        res.end(JSON.stringify(payload));
      };
      if (state.failNext) {
        const failure = state.failNext;
        state.failNext = null;
        return reply(failure.status, { error: failure.body });
      }
      if (method === 'GET' && url === '/api/agents/management') return reply(200, { data: state.agents });
      if (method === 'POST' && url === '/api/agents/custom') {
        const spec = JSON.parse(body) as Record<string, unknown>;
        const id = 'kel-agent-1';
        state.agents.push({ ...spec, id, custom_agent_id: id });
        return reply(200, { data: { ...spec, id } });
      }
      if (method === 'PUT' && url.startsWith('/api/agents/custom/')) {
        const spec = JSON.parse(body) as Record<string, unknown>;
        const id = decodeURIComponent(url.split('/').pop() || '');
        const index = state.agents.findIndex((agent) => agent.id === id || agent.custom_agent_id === id);
        if (index >= 0) state.agents[index] = { ...state.agents[index], ...spec };
        return reply(200, { data: { ...spec, id } });
      }
      if (method === 'GET' && url === '/api/assistants') return reply(200, { data: state.assistants });
      if (method === 'POST' && url === '/api/assistants') {
        const spec = JSON.parse(body) as Assistant;
        // Conservative backend contract: a newly created assistant starts disabled; the
        // enablement pass must switch kel on and the donors off.
        state.assistants.push({ ...spec, enabled: false });
        return reply(200, { data: spec });
      }
      const stateMatch = /^\/api\/assistants\/([^/]+)\/state$/.exec(url);
      if (method === 'PATCH' && stateMatch) {
        const id = decodeURIComponent(stateMatch[1]);
        const { enabled } = JSON.parse(body) as { enabled: boolean };
        const row = state.assistants.find((assistant) => assistant.id === id);
        if (row) row.enabled = enabled;
        return reply(200, { data: { id, enabled } });
      }
      return reply(404, { error: 'not found' });
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('mock backend failed to listen');
  state.port = address.port;
  state.close = () => new Promise<void>((resolve) => server.close(() => resolve()));
  return state;
}

const DATA_ROOT = 'C:/Users/Nick/KelV2Runs/prepared/engine';
const SOURCE_ROOT = 'C:/Users/Nick/Desktop/Kel/kel-v2/runtime';

const enabledIds = (assistants: Assistant[]) => assistants.filter((a) => a.enabled !== false).map((a) => a.id);

describe('ensureKelIntegration (standalone webui)', () => {
  let backend: MockBackend | null = null;

  afterEach(async () => {
    await backend?.close();
    backend = null;
  });

  it('creates the Kel agent and assistant on a fresh profile, leaving only kel enabled', async () => {
    backend = await startMockBackend({
      assistants: [
        { id: 'aion-cli', enabled: true },
        { id: 'claude-code', enabled: true },
        { id: 'codex-cli', enabled: true },
      ],
    });
    const result = await ensureKelIntegration({ backendPort: backend.port, dataRoot: DATA_ROOT, sourceRoot: SOURCE_ROOT, log: () => undefined });

    expect(result.agent).toBe('created');
    expect(result.assistant).toBe('created');
    expect(result.enabledBefore).toEqual(['aion-cli', 'claude-code', 'codex-cli']);
    expect(result.enablementPatches).toBe(4);

    // The agent carries the exact ACP spec aioncore will spawn (module mode — the script-path
    // form cannot resolve the host's relative imports during initialize).
    const agent = backend.agents.find((row) => row.name === 'Kel');
    expect(agent).toBeTruthy();
    expect(agent?.command).toBe('python');
    expect(agent?.args).toEqual(['-m', 'kel.acp_host', '--data', DATA_ROOT]);
    expect(agent?.env).toEqual([{ name: 'PYTHONPATH', value: SOURCE_ROOT }]);

    const kel = backend.assistants.find((row) => row.id === 'kel');
    expect(kel?.agent_id).toBe('kel-agent-1');
    expect(enabledIds(backend.assistants)).toEqual(['kel']);
  });

  it('is idempotent on a settled profile and refreshes the agent spec on re-run', async () => {
    backend = await startMockBackend({ assistants: [{ id: 'aion-cli', enabled: true }] });
    await ensureKelIntegration({ backendPort: backend.port, dataRoot: DATA_ROOT, sourceRoot: SOURCE_ROOT, log: () => undefined });
    const patchesAfterFirstRun = backend.requests.filter((request) => request.method === 'PATCH').length;
    expect(patchesAfterFirstRun).toBeGreaterThan(0);

    const second = await ensureKelIntegration({
      backendPort: backend.port,
      dataRoot: DATA_ROOT,
      sourceRoot: SOURCE_ROOT,
      python: 'py312',
      log: () => undefined,
    });

    expect(second.agent).toBe('updated');
    expect(second.assistant).toBe('existing');
    expect(second.enablementPatches).toBe(0);
    expect(backend.agents.filter((row) => row.name === 'Kel')).toHaveLength(1);
    expect(backend.agents.find((row) => row.name === 'Kel')?.command).toBe('py312');
    expect(backend.assistants.filter((row) => row.id === 'kel')).toHaveLength(1);
    // Second run touches no assistant state at all.
    expect(backend.requests.filter((request) => request.method === 'PATCH').length).toBe(patchesAfterFirstRun);
  });

  it('repairs a profile where kel exists but is disabled and another assistant is enabled', async () => {
    backend = await startMockBackend({
      agents: [{ id: 'kel-agent-1', custom_agent_id: 'kel-agent-1', name: 'Kel' }],
      assistants: [
        { id: 'kel', enabled: false, agent_id: 'kel-agent-1' },
        { id: 'claude-code', enabled: true },
      ],
    });
    const result = await ensureKelIntegration({ backendPort: backend.port, dataRoot: DATA_ROOT, sourceRoot: SOURCE_ROOT, log: () => undefined });

    expect(result.agent).toBe('updated');
    expect(result.assistant).toBe('existing');
    expect(result.enablementPatches).toBe(2);
    expect(enabledIds(backend.assistants)).toEqual(['kel']);
  });

  it('fails honestly when the backend refuses a step', async () => {
    backend = await startMockBackend({ assistants: [] });
    backend.failNext = { status: 500, body: 'backend exploded' };
    const failure = await ensureKelIntegration({
      backendPort: backend.port,
      dataRoot: DATA_ROOT,
      sourceRoot: SOURCE_ROOT,
      log: () => undefined,
    }).catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(Error);
    expect(String(failure)).toContain('/api/agents/management: 500');
    expect(String(failure)).toContain('backend exploded');
  });
});
