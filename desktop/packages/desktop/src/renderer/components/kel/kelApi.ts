/**
 * Typed access to the Kel engine through the preload bridge (`window.kelAPI.request`).
 * Only allowlisted routes reach the engine — see process/services/kel/KelService.ts.
 */
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
    };
  }
}

async function call<T>(route: string, body?: unknown): Promise<T> {
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  if (!api) throw new Error('Kel bridge unavailable — restart Kel and try again');
  return (await api.request(route, body)) as T;
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
  value?: Record<string, unknown>;
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
  name?: string;
  title?: string;
  steps?: unknown[];
  inputs?: unknown[];
  source?: string;
}

export interface KelWork {
  project_id: string;
  memory: { records: KelMemoryRecord[]; conflicts: Array<Record<string, unknown>> };
  map: { version: number; fingerprint: string; updated: number; note?: string; sections: KelMapSection[] } | null;
  recipes: { entries: KelRecipeEntry[] };
}

export const kelWork = (conversation = 'main') =>
  call<KelWork>(`/api/work?conversation=${encodeURIComponent(conversation)}`);

export const kelMemoryAction = (
  action: 'confirm' | 'retract' | 'forget' | 'correct',
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

export const kelState = () =>
  call<{
    jobs: KelWorkJob[];
    continuation?: KelContinuationCandidate[];
    approvals?: Array<Record<string, unknown>>;
    providers: string[];
    projects: Array<{ id: string; name: string }>;
    engine_version?: string;
    draining?: boolean;
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
