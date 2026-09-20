/**
 * Typed access to the Kel engine through the preload bridge (`window.kelAPI.request`).
 * Only allowlisted routes reach the engine — see process/services/kel/KelService.ts.
 */
import { type EngineStateFrame } from './engineFailure';

export interface KelAssignment {
  assignment_id: string;
  job_id: string;
  milestone_id: string;
  run_id: string | null;
  role: string;
  role_version: number;
  derived_state: string;
  blocker: string | null;
  budget: number | null;
  spent: number | null;
  provider: string | null;
  model: string | null;
  created: number;
  updated: number;
  snapshot_digest: string;
}

export interface KelRole {
  template_id: string;
  name: string;
  department: string;
  status: string;
  version: number | null;
  assignments: number;
}

export interface KelTeamEvent {
  seq: number;
  at: number;
  kind: string;
  actor: string;
  detail: Record<string, unknown> | null;
  refs: Record<string, unknown> | null;
}

export interface KelRoleDetail {
  template_id: string;
  role_version: number;
  fields: Record<string, unknown>;
  sources: string[];
  locked_block: Array<{ rule: string; text: string; test: string }>;
}

export interface KelJobMilestoneRuntime {
  state?: string;
  attempts?: number;
  artifact?: string;
  digest?: string;
  /** Plain engine reason recorded when a milestone needed repair or reconciliation. */
  error?: string;
}

export interface KelJobContractMilestone {
  id: string;
  objective?: string;
  filename?: string;
  depends_on?: string[];
  checks?: Array<{ kind?: string; value?: unknown }>;
}

export interface KelWorkJob {
  id: string;
  conversation?: string;
  state: string;
  verdict?: string;
  spent?: number;
  budget?: number;
  /** Engine-reported last update, when the engine provides one. */
  updated?: number;
  /**
   * Set while the engine waits for an available model route (D7): such a job resumes automatically
   * when a route is available, so it is NOT a human interruption. Absent while waiting because an
   * expired/orphaned run needs reconciliation — that one genuinely needs a person.
   */
  route_block?: string;
  contract?: { request?: string; project_id?: string; milestones?: KelJobContractMilestone[] };
  milestones?: Record<string, KelJobMilestoneRuntime>;
}

export interface KelContinuationCandidate {
  job_id?: string;
  job?: { id?: string; state?: string; verdict?: string };
  state?: string;
  verdict?: string;
  summary?: string;
  reasons?: string[];
}

declare global {
  interface Window {
    kelAPI?: {
      request: (route: string, body?: unknown) => Promise<unknown>;
      history: (id: string) => Promise<unknown>;
      conversation: (id: string) => Promise<unknown>;
      historySearch: (query: string) => Promise<unknown>;
      /** Batch 6: the shell's honest engine-link view + support actions. */
      engineState?: () => Promise<unknown>;
      engineRetry?: () => Promise<unknown>;
      diagnostics?: () => Promise<unknown>;
      onEngineState?: (callback: (frame: unknown) => void) => () => void;
      /** OS-backed credential custody: metadata only — there is deliberately no value getter. */
      credentials?: {
        status: () => Promise<{ available: boolean; providers: Record<string, string[]> }>;
        set: (
          provider: string,
          field: string,
          value: string
        ) => Promise<{ provider: string; fields: string[] }>;
        remove: (provider: string) => Promise<{ provider: string; removed: number }>;
      };
    };
  }
}

// D13 — the gateway's failure codes are for machines; the person in front of the remote browser
// gets a sentence. Unknown codes fall back to the engine's own message, never to a raw string.
const GATEWAY_FAILURE_TEXT: Record<string, string> = {
  KEL_ENGINE_UNAVAILABLE:
    "Kel isn't running on the computer that serves this page right now. Open Kel there, then try again.",
  KEL_ENGINE_UNREACHABLE:
    'Kel stopped answering on that computer. Your work is kept — try again in a moment.',
};

async function call<T>(route: string, body?: unknown): Promise<T> {
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  if (api) return (await api.request(route, body)) as T;
  // D11 — away from the desktop (the remote browser) the same renderer talks to the engine through
  // the desktop web-host's session-gated gateway: /kel/* is proxied server-side with the
  // process-held bearer token, so no credential ever reaches the browser. Bodyless calls are GETs,
  // exactly like the preload bridge, because the engine serves its reads as GET-with-query.
  const hasBody = body !== undefined;
  let response: Response;
  try {
    response = await fetch(`/kel${route}`, {
      method: hasBody ? 'POST' : 'GET',
      ...(hasBody
        ? { headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }
        : {}),
    });
  } catch {
    // The browser itself could not reach the page's own origin — a network drop, not a Kel fault.
    throw new Error("This device can't reach Kel right now — check the connection and try again.");
  }
  const payload = (await response.json().catch((): null => null)) as unknown;
  if (!response.ok) {
    const code =
      payload && typeof payload === 'object' && 'error' in payload
        ? String((payload as { error: unknown }).error)
        : '';
    throw new Error(GATEWAY_FAILURE_TEXT[code] ?? `Kel is not answering right now (${response.status}).`);
  }
  return payload as T;
}

// ---------------------------------------------------------------------------------------------
// Batch 6 (findings 16/17): engine-link helpers for the failure surfaces. When the bridge does not
// expose them (older preload), the helpers degrade honestly to "connected, nothing to report"
// rather than inventing an incident.
// ---------------------------------------------------------------------------------------------
const DEFAULT_ENGINE_FRAME = (): EngineStateFrame => ({ state: 'connected', attempts: 0, maxAttempts: 2, at: Date.now() });

export async function engineState(): Promise<EngineStateFrame> {
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  if (!api?.engineState) return DEFAULT_ENGINE_FRAME();
  try {
    return (await api.engineState()) as EngineStateFrame;
  } catch {
    return DEFAULT_ENGINE_FRAME();
  }
}

export async function engineRetry(): Promise<EngineStateFrame> {
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  if (!api?.engineRetry) return DEFAULT_ENGINE_FRAME();
  try {
    return (await api.engineRetry()) as EngineStateFrame;
  } catch {
    return { ...DEFAULT_ENGINE_FRAME(), state: 'unrecoverable' };
  }
}

export interface KelDesktopDiagnostics {
  engineVersion?: string;
  address?: string;
  state?: EngineStateFrame;
  logTail?: string;
}

export async function engineDiagnostics(): Promise<KelDesktopDiagnostics> {
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  if (!api?.diagnostics) return {};
  try {
    return (await api.diagnostics()) as KelDesktopDiagnostics;
  } catch {
    return {};
  }
}

export function onEngineState(listener: (frame: EngineStateFrame) => void): () => void {
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  if (!api?.onEngineState) return () => undefined;
  return api.onEngineState((frame) => {
    if (frame && typeof frame === 'object') listener(frame as EngineStateFrame);
  });
}

export interface KelMemoryRecord {
  id: string;
  type: string;
  topic: string;
  summary: string;
  trust: number;
  status: string;
  user_confirmed: number;
  source_type: string;
  source_ref: string;
  confidence: number;
  updated: number;
  /** The engine returns the stored JSON column as-is (a string in the /api/work payload). */
  value?: string | Record<string, unknown>;
}

/** A change Kel proposes but never applies by itself — a person accepts, defers, or rejects it. */
export interface KelMemoryProposal {
  id: string;
  kind: string;
  state: string;
  topic?: string;
  summary?: string;
  why?: string;
  updated?: number;
}

export interface KelMapSection {
  name: string;
  trust: string;
  stale: boolean;
  updated: number;
  digest: string;
  sources: string[];
}

export interface KelRecipeEntry {
  id?: string;
  recipe_id?: string;
  name?: string;
  title?: string;
  steps?: unknown[];
  inputs?: unknown[];
  source?: string;
}

export interface KelWork {
  project_id: string;
  memory: {
    records: KelMemoryRecord[];
    proposals: KelMemoryProposal[];
    conflicts: Array<Record<string, unknown>>;
  };
  map: { version: number; fingerprint: string; updated: number; note?: string; sections: KelMapSection[] } | null;
  recipes: { entries: KelRecipeEntry[] };
}

export const kelWork = (conversation = 'main') =>
  call<KelWork>(`/api/work?conversation=${encodeURIComponent(conversation)}`);

export const kelMemoryAction = (
  action:
    | 'confirm'
    | 'retract'
    | 'forget'
    | 'correct'
    | 'accept_proposal'
    | 'reject_proposal'
    | 'defer_proposal',
  id: string,
  extra: Record<string, unknown> = {},
  conversation = 'main'
) => call<Record<string, unknown>>('/api/memory', { action, id, conversation, ...extra });

export const kelMapAction = (action: string, conversation = 'main', extra: Record<string, unknown> = {}) =>
  call<Record<string, unknown>>('/api/map', { action, conversation, ...extra });

export const kelRecipes = (conversation = 'main') =>
  call<Record<string, unknown>>('/api/recipes', { action: 'list', conversation });

/** Compile a recipe without running it — the engine's preview/dry-run path. */
export const kelRecipePreview = (recipeId: string, inputs: Record<string, unknown> = {}) =>
  call<Record<string, unknown>>('/api/recipes', {
    action: 'preview',
    recipe_id: recipeId,
    inputs,
    conversation: 'main',
  });

/** Draft a recipe from a settled job — preview only; saving needs explicit confirmation. */
export const kelRecipePropose = (jobId: string, conversation = 'main') =>
  call<{ recipe: Record<string, unknown>; preview: { steps: string[]; kind: string; milestones: number } }>(
    '/api/recipes',
    { action: 'propose_from_job', job_id: jobId, conversation }
  );

/** Run a recipe by compiling it into the existing execution (a normal job). */
export const kelRecipeRun = (
  recipeId: string,
  inputs: Record<string, unknown> = {},
  conversation = 'main'
) => call<{ submission: string }>('/api/recipes', { action: 'run', recipe_id: recipeId, inputs, conversation });

/** Save a project recipe. The engine refuses unless confirmation is explicit. */
export const kelRecipeSave = (recipe: Record<string, unknown>, conversation = 'main') =>
  call<{ saved: boolean; digest: string; recipe_id?: string; version?: string; reason?: string }>(
    '/api/recipes',
    { action: 'save', recipe, confirm: true, conversation }
  );

export interface KelProviderStatus {
  provider: string;
  label: string;
  class: 'native-cli' | 'api';
  auth_mode: string;
  base_url?: string | null;
  capabilities: string[];
  status: string;
  note: string;
  installed: boolean;
  authenticated: boolean;
  failures: number;
  circuit_until: number | null;
  quota: number | null;
  quota_unit?: string | null;
  quota_reset?: number | null;
  quota_source?: string | null;
  planType?: string | null;
  models: Array<{ id: string; capabilities: string[] }>;
}

export interface KelCredentialMetadata {
  provider: string;
  fields: string[];
  credential_ref: string;
  created?: number;
  updated?: number;
}

export interface KelLease {
  lease_id: string;
  job_id: string;
  project_id: string;
  profile: string;
  review_ref: string;
  issued_at: number;
  expires_at: number;
  state: string;
  reason?: string | null;
  expired: boolean;
  scope: Array<{ kind: string; value: string; uses_remaining: number }>;
}

export interface KelBoundaryRequest {
  request_id: string;
  lease_id: string;
  scope: string;
  target: string;
  what?: string;
  why?: string;
  benefit?: string;
  fallback?: string;
  risk?: string;
  status: string;
  grant_kind?: string | null;
  created: number;
}

export const kelProviders = {
  list: () => call<{ providers: KelProviderStatus[] }>('/api/providers', { action: 'list' }),
  readiness: (capability = 'text', prefer = '') =>
    call<{
      chosen: { provider: string; model: string; label: string; status: string; auth_mode: string } | null;
      chain: string[];
      reasons: string[];
      reason: string;
    }>('/api/providers', { action: 'readiness', capability, prefer }),
  credentials: (provider?: string) =>
    call<{ credentials: KelCredentialMetadata[] }>('/api/providers', {
      action: 'credentials',
      provider,
    }),
  setCredential: (provider: string, fields: string[], credentialRef: string) =>
    call<Record<string, unknown>>('/api/providers', {
      action: 'set_credential',
      provider,
      fields,
      credential_ref: credentialRef,
    }),
  deleteCredential: (provider: string) =>
    call<Record<string, unknown>>('/api/providers', { action: 'delete_credential', provider }),
  usage: (provider?: string) =>
    call<{ usage: Array<{ provider: string; at: number; data: Record<string, unknown> }> }>(
      '/api/providers',
      { action: 'usage', provider }
    ),
};

export const kelAutonomy = {
  leases: (jobId?: string) =>
    call<{ leases: KelLease[] }>('/api/autonomy', { action: 'leases', job_id: jobId }),
  requests: (leaseId?: string) =>
    call<{ requests: KelBoundaryRequest[] }>('/api/autonomy', { action: 'requests', lease_id: leaseId }),
  guardrails: () =>
    call<{ rules: Array<{ rule: string; text: string; test: string }>; digest: string }>(
      '/api/autonomy',
      { action: 'guardrails' }
    ),
  check: (leaseId: string, kind: string, target = '', tool = '') =>
    call<{ allowed: boolean; rule: string; reason: string }>('/api/autonomy', {
      action: 'check',
      lease_id: leaseId,
      kind,
      target,
      tool,
    }),
  revoke: (leaseId: string, reason = '') =>
    call<Record<string, unknown>>('/api/autonomy', { action: 'revoke', lease_id: leaseId, reason }),
  emergencyStop: () =>
    call<{ stopped: string[]; count: number; paused_jobs: string[]; paused_count: number }>(
      '/api/autonomy',
      { action: 'emergency_stop' }
    ),
  resolveRequest: (requestId: string, allow: boolean, grantKind: 'once' | 'project' = 'once') =>
    call<Record<string, unknown>>('/api/autonomy', {
      action: 'resolve',
      request_id: requestId,
      allow,
      grant_kind: grantKind,
    }),
};

export interface KelDiagnosticsSnapshot {
  engine_version: string;
  counts: { jobs: number; runs: number };
  database: {
    integrity: string;
    size_bytes: number;
    wal_bytes: number;
    page_size: number;
    page_count: number;
    freelist_pages: number;
    fragmentation_percent: number;
    problems: string[];
  };
  jobs: Record<string, number>;
  runs: { by_state: Record<string, number>; expired_unfenced: number };
  policy?: {
    version: string | null;
    by_decision: Record<string, number>;
    recent: Array<{
      at: number;
      decision: string;
      rule: string | null;
      reason: string | null;
      actor: string;
      job_id: string | null;
      action_kind: string;
      policy_version: string;
    }>;
    error?: string;
  };
  leases?: Record<string, number>;
  migrations?: Array<{ version: number; name: string }>;
  providers: Record<string, Record<string, unknown>>;
  processes: Array<{
    run_id: string;
    pid: number;
    identity: string;
    deadline: number;
    alive: boolean;
    past_deadline: boolean;
  }>;
}

export const kelDiagnostics = {
  snapshot: () => call<KelDiagnosticsSnapshot>('/api/diagnostics', { action: 'snapshot' }),
  observe: () =>
    call<{ subject: string; state: string; snapshot: KelDiagnosticsSnapshot }>('/api/diagnostics', {
      action: 'observe',
    }),
  performance: () =>
    call<{
      startup_spans: Array<{ at: number; phase: string; duration_ms: number; engine_version: string }>;
      slowest_phase_ms: Record<string, number>;
      measurements: Array<{ at: number; name: string; value: number; unit: string; basis: string }>;
      basis: string;
    }>('/api/diagnostics', { action: 'performance' }),
  retention: () =>
    call<{ retention_days: Record<string, number> }>('/api/diagnostics', { action: 'retention' }),
  purge: () =>
    call<{ removed: Record<string, number>; retention_days: Record<string, number> }>(
      '/api/diagnostics',
      { action: 'purge' }
    ),
  compact: () =>
    call<{ before_bytes: number; after_bytes: number; integrity: string; backup: string }>(
      '/api/diagnostics',
      { action: 'compact' }
    ),
  export: () => call<Record<string, unknown>>('/api/diagnostics', { action: 'export' }),
  report: (note: string) =>
    call<{ path: string; bytes: number; redacted: boolean; excluded: string[] }>('/api/diagnostics', {
      action: 'report',
      note,
    }),
};

export const kelTeam = {
  office: (projectId = 'default') =>
    call<{ assignments: KelAssignment[] }>('/api/team', { action: 'office', project_id: projectId }),
  roster: () => call<{ roles: KelRole[]; departments: string[] }>('/api/team', { action: 'roster' }),
  seed: () => call<{ created: string[] }>('/api/team', { action: 'seed' }),
  role: (templateId: string) =>
    call<KelRoleDetail>('/api/team', { action: 'role', template_id: templateId }),
  history: (templateId: string) =>
    call<{ versions: Array<{ version: number; digest: string; author: string; created: number }> }>(
      '/api/team',
      { action: 'history', template_id: templateId }
    ),
  rollback: (templateId: string, to: number) =>
    call<{ version: number }>('/api/team', { action: 'rollback', template_id: templateId, to }),
  timeline: (assignmentId: string) =>
    call<{ events: KelTeamEvent[] }>('/api/team', { action: 'timeline', assignment_id: assignmentId }),
};

/** D12: why the engine routed a run to a provider — selected/fallbacks/excluded + policy flags. */
export interface KelJobRoute {
  provider?: string | null;
  route: {
    selected: string;
    fallbacks?: string[];
    excluded?: Record<string, string[]>;
    policy?: string;
    unknown_cost?: boolean;
    unknown_quota?: boolean;
  };
  at?: number;
}

export const kelState = () =>
  call<{
    jobs: KelWorkJob[];
    continuation?: KelContinuationCandidate[];
    approvals?: Array<Record<string, unknown>>;
    providers: string[];
    /** D12: routing decisions for active jobs, keyed by job id. */
    routes?: Record<string, KelJobRoute>;
    projects: Array<{ id: string; name: string }>;
    engine_version?: string;
    draining?: boolean;
    /** D6: the engine's recorded restore outcome (audit PER-02); null when never attempted. */
    restore?: { ok: boolean; detail?: string; at?: number } | null;
  }>('/api/state');

/** Markdown artifact text for an ACCEPTED milestone (the engine refuses anything unverified). */
export const kelArtifact = (job: string, milestone: string) =>
  call<unknown>(
    `/api/artifact?job=${encodeURIComponent(job)}&milestone=${encodeURIComponent(milestone)}`
  );

export const kelControl = (job: string, action: 'pause' | 'resume' | 'cancel') =>
  call<{ ok: boolean }>('/api/control', { job, action });

export const kelBriefs = {
  list: (projectId = 'default') =>
    call<{ briefs: Array<{ brief_id: string; goal: string; state: string; chosen_option: string | null; updated: number }> }>(
      '/api/brief',
      { action: 'list', project_id: projectId }
    ),
};
