/**
 * Kel integration for the standalone WebUI host (`bun run webui`).
 *
 * The Electron desktop performs this integration in its main process
 * (`packages/desktop/src/process/services/kel/KelService.ts` → `initializeKel`):
 * register the Kel ACP agent, create the single `kel` assistant, and leave
 * exactly that assistant enabled. The standalone webui never runs Electron
 * main, so a browser profile hosted by it otherwise has no assistant the shell
 * can select — the guid page filters the catalog to `kel`, finds nothing, and
 * the composer's send can never be enabled (V2-05, measured in
 * `docs/v2/evidence/v2-05/`).
 *
 * Everything here talks to the aioncore backend on loopback exactly like the
 * desktop does — same routes, same fields, same assistant state. The one
 * deliberate difference is the agent spawn: this host must use module mode
 * (`python -m kel.acp_host`), because the script-path form cannot resolve the
 * ACP host's relative imports during `initialize` (measured). No model turn is
 * involved and nothing is kept beyond the backend's own tables.
 */

export type KelIntegrationResult = {
  /** Whether the Kel agent row was created or refreshed. */
  agent: 'created' | 'updated';
  /** Whether the `kel` assistant row was created or already existed. */
  assistant: 'created' | 'existing';
  /** How many assistants' enabled state was brought in line (0 on a settled profile). */
  enablementPatches: number;
  /** Which assistants were enabled before the enablement pass (for logs/tests). */
  enabledBefore: string[];
};

export type KelIntegrationOptions = {
  /** aioncore's loopback port. */
  backendPort: number;
  /** The Kel engine's data root (`KEL_DATA_DIR`) — the same root the running engine uses. */
  dataRoot: string;
  /** Directory containing `kel/acp_host.py` (the Kel runtime, e.g. `<repo>/runtime`). */
  sourceRoot: string;
  /** Python executable for the ACP host. Default: `python` (`KEL_PYTHON` overrides at the call site). */
  python?: string;
  /** Where progress lines go. Default: `console.log`. */
  log?: (line: string) => void;
};

const DISABLED_BUILTIN_SKILLS = [
  'aionui-config',
  'conversation-create',
  'cron',
  'officecli',
  'session-message',
  'skill-creator',
];

const RECOMMENDED_PROMPTS = [
  'Explain this project in plain words.',
  'Review this project and suggest the next useful change.',
];

const AGENT_DESCRIPTION = 'One assistant. Durable work and checked results.';
const ASSISTANT_DESCRIPTION = 'Your assistant for projects and everyday work.';

type Json = Record<string, unknown>;

type RequestInitLike = { method?: string; body?: unknown };

export async function ensureKelIntegration(options: KelIntegrationOptions): Promise<KelIntegrationResult> {
  const log = options.log ?? ((line: string) => console.log(line));
  const base = `http://127.0.0.1:${options.backendPort}`;

  const request = async <T>(route: string, init?: RequestInitLike): Promise<T> => {
    const response = await fetch(base + route, {
      method: init?.method ?? (init?.body === undefined ? 'GET' : 'POST'),
      headers: { 'Content-Type': 'application/json' },
      body: init?.body === undefined ? undefined : JSON.stringify(init.body),
    });
    if (!response.ok) {
      throw new Error(`Kel integration ${route}: ${response.status} ${(await response.text()).slice(0, 300)}`);
    }
    const payload = (await response.json()) as { data?: T };
    return (payload?.data ?? payload) as T;
  };

  // 1. Register (or refresh) the Kel agent aioncore spawns for a conversation.
  // Module mode (`-m kel.acp_host`) is required: the script-path form cannot resolve the host's
  // relative imports during ACP `initialize`, and there is no packed engine on this source line.
  // Same pattern as the desktop's service spawn (`-m kel.service`).
  const spec = {
    name: 'Kel',
    command: options.python?.trim() || 'python',
    args: ['-m', 'kel.acp_host', '--data', options.dataRoot],
    env: [{ name: 'PYTHONPATH', value: options.sourceRoot }],
    advanced: { description: AGENT_DESCRIPTION },
  };
  const agents = await request<Json[]>('/api/agents/management');
  const existing = Array.isArray(agents) ? agents.find((agent) => agent.name === 'Kel') : undefined;
  let agentId: string;
  let agentState: KelIntegrationResult['agent'];
  if (existing) {
    const id = String(existing.custom_agent_id || existing.id || '');
    if (!id) throw new Error('Kel integration: the Kel agent row has no id');
    const updated = await request<Json>(`/api/agents/custom/${encodeURIComponent(id)}`, { method: 'PUT', body: spec });
    agentId = String(updated?.id ?? id);
    agentState = 'updated';
    log(`[KEL-BOOT] kel-integration: agent refreshed (${agentId})`);
  } else {
    const created = await request<Json>('/api/agents/custom', { body: spec });
    const id = String(created?.id ?? '');
    if (!id) throw new Error('Kel integration: agent create returned no id');
    agentId = id;
    agentState = 'created';
    log(`[KEL-BOOT] kel-integration: agent registered (${agentId})`);
  }

  // 2. Ensure the single `kel` assistant exists, pointing at that agent.
  const assistants = await request<Json[]>('/api/assistants');
  const hasKel = Array.isArray(assistants) && assistants.some((assistant) => assistant.id === 'kel');
  let assistantState: KelIntegrationResult['assistant'] = 'existing';
  if (!hasKel) {
    await request('/api/assistants', {
      body: {
        id: 'kel',
        name: 'Kel',
        agent_id: agentId,
        description: ASSISTANT_DESCRIPTION,
        disabled_builtin_skills: [...DISABLED_BUILTIN_SKILLS],
        recommended_prompts: [...RECOMMENDED_PROMPTS],
      },
    });
    assistantState = 'created';
    log('[KEL-BOOT] kel-integration: assistant created');
  }

  // 3. Enforce enablement: only `kel` is enabled, everything else is off.
  const current = await request<Json[]>('/api/assistants');
  const rows = Array.isArray(current) ? current : [];
  const enabledBefore = rows.filter((row) => row.enabled !== false).map((row) => String(row.id));
  let enablementPatches = 0;
  for (const row of rows) {
    const shouldBeEnabled = row.id === 'kel';
    if (row.enabled !== shouldBeEnabled) {
      await request(`/api/assistants/${encodeURIComponent(String(row.id))}/state`, {
        method: 'PATCH',
        body: { enabled: shouldBeEnabled },
      });
      enablementPatches += 1;
    }
  }
  log(`[KEL-BOOT] kel-integration: assistants enforced (${enablementPatches} changed)`);

  return { agent: agentState, assistant: assistantState, enablementPatches, enabledBefore };
}
