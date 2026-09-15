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

export interface KelWorkJob {
  id: string;
  state: string;
  spent?: number;
  budget?: number;
  contract?: { request?: string; milestones?: Array<{ id: string; objective?: string }> };
  milestones?: Record<string, { state?: string; attempts?: number; checks?: unknown[] }>;
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
  call<{ jobs: KelWorkJob[]; providers: string[]; projects: Array<{ id: string; name: string }> }>(
    '/api/state'
  );

export const kelBriefs = {
  list: (projectId = 'default') =>
    call<{ briefs: Array<{ brief_id: string; goal: string; state: string; chosen_option: string | null; updated: number }> }>(
      '/api/brief',
      { action: 'list', project_id: projectId }
    ),
};
