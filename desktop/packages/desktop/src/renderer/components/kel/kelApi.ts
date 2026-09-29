/**
 * Typed access to the Kel engine through the preload bridge (`window.kelAPI.request`).
 * Only allowlisted routes reach the engine — see process/services/kel/KelService.ts.
 */
import { type EngineStateFrame } from './engineFailure';
import type { KelUsage } from '@/common/chat/kelMessageMeta';

export type { KelUsage };

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
  /** D-65: coding work only — where its checked change stands (and whether it waits for you). */
  application?: KelChangeApplication | null;
}

export interface KelContinuationCandidate {
  job_id?: string;
  job?: { id?: string; state?: string; verdict?: string };
  state?: string;
  verdict?: string;
  summary?: string;
  /** The engine's short title for the job (first 80 characters of the request). */
  title?: string;
  /** The engine conversation the job belongs to. */
  conversation?: string;
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
      /** LIVE-7: a chat's Kel history gained details (scoping card, result) while it is open. */
      onHistoryUpdated?: (callback: (update: { conversationId: string }) => void) => () => void;
      /** OS-backed credential custody: metadata only — there is deliberately no value getter. */
      credentials?: {
        status: () => Promise<{ available: boolean; providers: Record<string, string[]> }>;
        /** V2-01: what the OS store holds for Connections — field names only, never values. */
        connectionStatus?: () => Promise<Record<string, string[]>>;
        set: (
          provider: string,
          field: string,
          value: string
        ) => Promise<{ provider: string; fields: string[] }>;
        remove: (provider: string) => Promise<{ provider: string; removed: number }>;
        /** V2-02: check a connection using its stored credential. Returns the record, not a value. */
        testConnection?: (connectionId: string) => Promise<KelConnection>;
        /** V2-04: do one thing with a connection. Returns the service's answer, never a value. */
        runConnection?: (
          connectionId: string,
          actionId: string,
          params?: Record<string, unknown>,
          confirmed?: boolean
        ) => Promise<KelConnectionRun>;
        /** V2-04b: finish the account sign-in in the main process; tokens never come back here. */
        oauthConnect?: (
          connectionId: string
        ) => Promise<{ state: string; note?: string; fields?: string[] }>;
        oauthRevoke?: (connectionId: string) => Promise<{ state?: string; note?: string }>;
      };
      /**
       * Fix Capture: one screenshot of Kel's own window, written into the data root. Absent on the
       * remote surface, where reading Kel's window is impossible by design.
       */
      dogfood?: {
        capture: () => Promise<{
          screenshot: string;
          image: { width: number; height: number };
          content: { width: number; height: number };
          display: { scale: number };
          captured_at: number;
        }>;
        screenshot: (relpath: string) => Promise<{ data_url: string }>;
      };
      /** Reveal a store-relative path in the OS file manager (best effort on the remote surface). */
      revealArtifact?: (relpath: string) => Promise<unknown>;
      /**
       * D-57: the app chat for an engine conversation (a scheduled run's), made on first use.
       * Null when the engine no longer has that conversation. Absent on the remote surface.
       */
      openEngineConversation?: (cid: string) => Promise<string | null>;
      /**
       * D-57: ask the main process to bring the chat list in step with the schedules now; `hidden`
       * names the engine chats a deleted schedule's runs opened, whose app chats leave the list.
       */
      schedulesChanged?: (change?: { hidden?: string[] }) => Promise<unknown>;
    };
  }
}

// D13 — the gateway's failure codes are for machines; the person in front of the remote browser
// gets a sentence. Unknown codes fall back to the engine's own message, never to a raw string.

/** One engine call with the bridge/gateway fallback rules; for feature modules that own a route. */
export const kelRequest = <T,>(route: string, body?: unknown): Promise<T> => call<T>(route, body);
const GATEWAY_FAILURE_TEXT: Record<string, string> = {
  KEL_ENGINE_UNAVAILABLE:
    "Kel isn't running on the computer that serves this page right now. Open Kel there, then try again.",
  KEL_ENGINE_UNREACHABLE:
    'Kel stopped answering on that computer. Your work is kept — try again in a moment.',
};

/**
 * D-78 motion captures only: a script driving an off-screen copy of Kel over the DevTools protocol can
 * answer chosen engine reads with scripted states (so every moment can be recorded without running
 * real work). Nothing in the app sets it; when it is absent (always, in use) this is a no-op.
 */
type CaptureFixture = (route: string, body?: unknown) => unknown;
const captureFixture = (): CaptureFixture | undefined =>
  typeof window === 'undefined' ? undefined : (window as unknown as { __kelCaptureFixture?: CaptureFixture }).__kelCaptureFixture;

async function call<T>(route: string, body?: unknown): Promise<T> {
  const scripted = captureFixture()?.(route, body);
  if (scripted !== undefined) return (await scripted) as T;
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

/** LIVE-7: called with the app conversation id whose Kel history (`kelAPI.history`) just changed. */
export function onKelHistoryUpdated(listener: (conversationId: string) => void): () => void {
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  if (!api?.onHistoryUpdated) return () => undefined;
  return api.onHistoryUpdated((update) => {
    if (update && typeof update.conversationId === 'string') listener(update.conversationId);
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
  /** D-54: the project the record belongs to (set by the renderer when it reads several projects). */
  project_id?: string;
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

/** D17: one tool/skill the engine can use, with its honest availability state. */
export interface KelCapabilityRow {
  id: string;
  label: string;
  description: string;
  availability: 'available' | 'needs_setup' | 'unavailable';
  availability_reason: string;
  global: 'on' | 'off';
  override: 'default' | 'on' | 'off';
  effective: 'on' | 'off';
  usable: boolean;
}

/** D17 — the integrations inventory (the same rows the per-chat tools pill draws). */
export const kelCapabilities = (conversation?: string) =>
  call<KelCapabilityRow[]>('/api/capabilities', { action: 'get', conversation });

/**
 * V2-01 — a Connection: Kel has credentials for this service and can use its API. The engine owns
 * the record and the state; the credential value itself lives in the OS-backed store, and the shell's
 * `connection:<id>` entry is the only place it exists.
 */
export interface KelConnection {
  id: string;
  name: string;
  kind: 'api_key' | 'oauth' | 'bot';
  kind_label: string;
  base_url: string;
  auth_method: 'header' | 'bearer' | 'query' | 'basic';
  auth_header: string;
  /** The word the service wants before the credential; '' means send it as it is; null means Kel works it out. */
  auth_prefix: string | null;
  docs_url: string;
  test_endpoint: string;
  notes: string;
  /** A pointer the engine keeps (`kel:connection:<id>`) — never the credential. */
  credential_ref: string | null;
  credential_fields: string[];
  has_credentials: boolean;
  state: 'ready' | 'needs_credentials';
  /** V2-02: whether Kel has an address it could check. */
  can_test: boolean;
  /** V2-02: what the last check found — the status is what the service answered, if it answered. */
  last_test_at: number | null;
  last_test_state: 'ok' | 'refused' | 'not_found' | 'busy' | 'error' | 'unreachable' | 'timeout' | null;
  last_test_status: number | null;
  last_test_ms: number | null;
  last_test_note: string;
  created: number;
  updated: number;
  /** V2-04b: the account sign-in state in plain words (empty for kinds that do not sign in). */
  auth_state: string;
  auth_scopes: string[];
  auth_expires: number | null;
  oauth_provider: string;
}

export interface KelConnectionList {
  connections: KelConnection[];
  counts: Record<'ready' | 'needs_credentials', number>;
  states: string[];
  kinds: Array<KelConnection['kind']>;
  /** V2-04: the three kinds of credential in the engine's own words — the only place they live. */
  templates: KelConnectionTemplate[];
}

/** A template: what a kind of credential means and what Kel will do with it. */
export interface KelConnectionTemplate {
  id: KelConnection['kind'];
  label: string;
  hint: string;
  credential_field: string;
  credential_label: string;
  check: string;
}

/**
 * The template for one kind, from the list the engine sent. The renderer keeps no kind vocabulary of its
 * own: the words a person reads come from the framework, so there is only one place to change them.
 */
export const connectionTemplate = (
  list: Pick<KelConnectionList, 'templates'> | null,
  kind: KelConnection['kind']
): KelConnectionTemplate | undefined => list?.templates?.find((item) => item.id === kind);

/** The credential field a kind normally uses, as the framework defines it. */
export const connectionCredentialField = (
  list: Pick<KelConnectionList, 'templates'> | null,
  kind: KelConnection['kind'],
  fallback = 'api_key'
): string => connectionTemplate(list, kind)?.credential_field || fallback;

/** The custody namespace the shell stores a connection's credential under. */
export const connectionCustodyKey = (id: string): string => `connection:${id}`;

/**
 * V2-03 — a service Kel already knows about. This is a row of data: address, how the credential is
 * presented, where the documentation is, and what Nick has to go and get. Nothing here decides how Kel
 * behaves; a service added by hand is exactly the same kind of connection.
 */
export interface KelKnownService {
  id: string;
  name: string;
  kind: KelConnection['kind'];
  base_url: string;
  auth_method: KelConnection['auth_method'];
  auth_header: string;
  auth_prefix: string | null;
  docs_url: string;
  test_endpoint: string;
  /** What Nick has to fetch, in his words. */
  credential: string;
  /** How sure Kel is about the addresses: 'documented' | 'assumed' | 'to-confirm'. */
  source: 'documented' | 'assumed' | 'to-confirm';
  note?: string;
}

/** The form draft a known service fills in when Nick picks it. */
export interface ConnectionDraft {
  id?: string;
  name: string;
  kind: KelConnection['kind'];
  base_url: string;
  auth_method: KelConnection['auth_method'];
  auth_header: string;
  auth_prefix: string | null;
  docs_url: string;
  test_endpoint: string;
  notes: string;
}

export const knownServiceDraft = (service: KelKnownService): ConnectionDraft => ({
  name: service.name,
  kind: service.kind,
  base_url: service.base_url,
  auth_method: service.auth_method,
  auth_header: service.auth_header,
  auth_prefix: service.auth_prefix,
  docs_url: service.docs_url,
  test_endpoint: service.test_endpoint,
  notes: service.note ?? '',
});

/** What a person should be told about a service Kel is not certain about. */
export const KNOWN_SERVICE_SOURCE_LABELS: Record<KelKnownService['source'], string> = {
  documented: 'Kel knows this address from the service’s own documentation.',
  assumed: 'Kel assumes the usual address — correct it if this service gave you a different one.',
  'to-confirm': 'Kel does not know this address; the service tells you when it issues your credential.',
};

/** V2-04 — one thing Kel can do with a service. Data: the request it makes and what it gives back. */
export interface KelConnectionAction {
  id: string;
  service: string;
  name: string;
  description: string;
  method: string;
  path: string;
  params: string[];
  returns: string;
  /** True when running it would change something in Nick's account — Kel asks before those. */
  mutating: boolean;
  source: 'documented' | 'assumed';
}

/** What came back from running an action. The answer is handed over, never stored. */
export interface KelConnectionRun {
  connection: string;
  action: string;
  name: string;
  state: string;
  status: number | null;
  attempts: number;
  ms: number;
  note: string;
  result: unknown;
  at: number;
}

/** One line of the access history: the fact of a call, with no payload in it. */
export interface KelConnectionEvent {
  at: number;
  connection: string;
  action: string;
  domain: string;
  status: number | null;
  state: string;
  attempts: number;
  ms: number;
}

/** How an answer looks when it is shown: bounded, and never mistaken for a secret store. */
export const connectionAnswerText = (result: unknown, limit = 2000): string => {
  if (result === null || result === undefined) return '';
  const text = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
  return text.length > limit ? `${text.slice(0, limit)}\n… (the answer was longer)` : text;
};
/** What a check of a connection found, in the words a person uses. */
export const CONNECTION_CHECK_LABELS: Record<string, string> = {
  ok: 'Working',
  refused: 'Credential refused',
  not_found: 'Nothing at that address',
  busy: 'Busy right now',
  error: 'Not working',
  unreachable: 'Not reachable',
  timeout: 'No answer',
};

/**
 * The honest one-line result of the last check. `when` is passed in so this stays a pure function of
 * the record and the clock the surface is showing.
 */
export const connectionCheckSentence = (connection: KelConnection, when: string): string | null => {
  if (!connection.last_test_at) return null;
  const label = connection.last_test_state
    ? CONNECTION_CHECK_LABELS[connection.last_test_state] ?? 'Checked'
    : 'Checked';
  const detail = connection.last_test_note || 'Kel did not record a result.';
  return `${label} — checked ${when}. ${detail}`;
};

export const kelConnections = {
  list: () => call<KelConnectionList>('/api/connections', { action: 'list' }),
  /** V2-03: the services Kel already knows how to talk to, as data. */
  knownServices: () =>
    call<{ services: KelKnownService[] }>('/api/connections', { action: 'catalogue' }),
  /** V2-04: what Kel can do with one connection, as data. */
  actions: (id: string) =>
    call<{ connection: string; actions: KelConnectionAction[] }>('/api/connections', {
      action: 'actions',
      id,
    }),
  /** V2-04: what Kel has asked this connection for, most recent first. */
  events: (id?: string, limit = 20) =>
    call<{ events: KelConnectionEvent[] }>('/api/connections', { action: 'events', id, limit }),
  get: (id: string) => call<KelConnection>('/api/connections', { action: 'get', id }),
  save: (draft: {
    id?: string;
    name: string;
    kind?: KelConnection['kind'];
    base_url?: string;
    auth_method?: KelConnection['auth_method'];
    auth_header?: string;
    auth_prefix?: string | null;
    docs_url?: string;
    test_endpoint?: string;
    notes?: string;
  }) => call<KelConnection>('/api/connections', { action: 'save', ...draft }),
  remove: (id: string) =>
    call<{ id: string; removed: boolean }>('/api/connections', { action: 'remove', id }),
  /** Metadata only: which field names exist and a pointer — the value never leaves the shell. */
  setCredential: (id: string, fields: string[]) =>
    call<KelConnection>('/api/connections', {
      action: 'set_credential',
      id,
      fields,
      credential_ref: `kel:connection:${id}`,
    }),
  deleteCredential: (id: string) =>
    call<KelConnection>('/api/connections', { action: 'delete_credential', id }),
};

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
  category?: string;
  /** The engine's own mark for a starred recipe (`entries()` carries it with the library row). */
  favourite?: boolean;
  /** D-54: the project a project recipe belongs to (built-ins have none). */
  project_id?: string;
}

export interface KelRecipeInput {
  name: string;
  type: 'text' | 'path' | 'choice' | 'bool';
  required: boolean;
  description?: string;
  choices?: string[];
  default?: string | boolean;
  max_chars?: number;
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

/**
 * D-54: what an engine call is about — one conversation (the engine looks up its project) or one
 * project by id. `{ project: '*' }` reads every project; the engine refuses it for writes.
 */
export type KelScope = { conversation: string } | { project: string };

/** A bare string is a conversation id (the older call shape). */
const scopeBody = (scope: string | KelScope): KelScope =>
  typeof scope === 'string' ? { conversation: scope } : scope;

const scopeQuery = (scope: string | KelScope): string => {
  const body = scopeBody(scope);
  return 'project' in body
    ? `project=${encodeURIComponent(body.project)}`
    : `conversation=${encodeURIComponent(body.conversation)}`;
};

/** General, the default project (where the engine's hidden 'main' conversation lives). */
const GENERAL_SCOPE: KelScope = { project: 'default' };

export const kelWork = (scope: string | KelScope = GENERAL_SCOPE) => call<KelWork>(`/api/work?${scopeQuery(scope)}`);

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
  scope: string | KelScope = GENERAL_SCOPE
) => call<Record<string, unknown>>('/api/memory', { action, id, ...scopeBody(scope), ...extra });

export const kelMapAction = (action: string, scope: string | KelScope = GENERAL_SCOPE, extra: Record<string, unknown> = {}) =>
  call<Record<string, unknown>>('/api/map', { action, ...scopeBody(scope), ...extra });

export const kelRecipes = (scope: string | KelScope = GENERAL_SCOPE) =>
  call<Record<string, unknown>>('/api/recipes', { action: 'list', ...scopeBody(scope) });

export const kelRecipeGet = (recipeId: string, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ recipe: { recipe_id: string; name: string; description?: string; inputs: KelRecipeInput[]; steps: Array<{ id: string; title: string; objective?: string }> } }>('/api/recipes', {
    action: 'get', recipe_id: recipeId, ...scopeBody(scope),
  });

/**
 * Compile a recipe without running it — the engine's preview/dry-run path. A recipe that needs a
 * project detail answers `needs_project` with the `project_id` and what is `missing`.
 */
export const kelRecipePreview = (recipeId: string, inputs: Record<string, unknown> = {}, scope: string | KelScope = GENERAL_SCOPE) =>
  call<Record<string, unknown> & { needs_project?: boolean; project_id?: string; missing?: Array<'folder' | 'test_command'> }>('/api/recipes', {
    action: 'preview',
    recipe_id: recipeId,
    inputs,
    ...scopeBody(scope),
  });

/** Draft a recipe from a settled job — preview only; saving needs explicit confirmation. */
export const kelRecipePropose = (jobId: string, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ recipe: Record<string, unknown>; preview: { steps: string[]; kind: string; milestones: number } }>(
    '/api/recipes',
    { action: 'propose_from_job', job_id: jobId, ...scopeBody(scope) }
  );

/**
 * Run a recipe by compiling it into the existing execution (a normal job). With a project scope the
 * engine runs it in that project's own hidden chat and names that `conversation`.
 */
export const kelRecipeRun = (
  recipeId: string,
  inputs: Record<string, unknown> = {},
  scope: string | KelScope = GENERAL_SCOPE
) => call<{ submission: string; conversation?: string }>('/api/recipes', { action: 'run', recipe_id: recipeId, inputs, ...scopeBody(scope) });

/** Save a project recipe. The engine refuses unless confirmation is explicit. */
export const kelRecipeSave = (recipe: Record<string, unknown>, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ saved: boolean; digest: string; recipe_id?: string; version?: string; reason?: string }>(
    '/api/recipes',
    { action: 'save', recipe, confirm: true, ...scopeBody(scope) }
  );

/** One run of a recipe — the engine reads these from the jobs it already keeps. */
export interface KelRecipeRun {
  job_id: string;
  state?: string;
  verdict?: string;
  created?: number;
  request?: string;
  artifact?: string | null;
  artifact_sha256?: string | null;
}

/** This recipe's runs, newest first: what the person reopens after a run. */
export const kelRecipeHistory = (recipeId: string, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ history: KelRecipeRun[] }>('/api/recipes', {
    action: 'history',
    recipe_id: recipeId,
    ...scopeBody(scope),
  });

/** The one-line answer to "what happened last time I ran this?" */
export const kelRecipeLastResult = (recipeId: string, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ recipe_id: string; state: string; sentence: string } & Record<string, unknown>>(
    '/api/recipes',
    { action: 'last_result', recipe_id: recipeId, ...scopeBody(scope) }
  );

/** The library's own controls (V2-07): search, categories, favourites, recent, duplicate. */
export const kelRecipeSearch = (query: string, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ entries: KelRecipeEntry[] }>('/api/recipes', { action: 'search', query, ...scopeBody(scope) });

export const kelRecipeCategories = (scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ categories: Array<{ name: string; count: number }> }>('/api/recipes', { action: 'categories', ...scopeBody(scope) });

export const kelRecipeRecent = (limit = 5, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ recent: KelRecipeEntry[] }>('/api/recipes', { action: 'recent', limit, ...scopeBody(scope) });

/** Star or unstar one recipe. */
export const kelRecipeFavourite = (recipeId: string, favourite: boolean, scope: string | KelScope = GENERAL_SCOPE) =>
  call<Record<string, unknown>>('/api/recipes', {
    action: 'favourites',
    recipe_id: recipeId,
    favourite,
    ...scopeBody(scope),
  });

/** Copy a recipe inside this project (the engine keeps the copy in the project scope). */
/** FN-12: one step as the Recipes page writes it (an existing step keeps its id). */
export type KelRecipeStepDraft = { id?: string; title?: string; objective: string };

/** FN-12: write a new recipe in this project (saved at once). */
export const kelRecipeCreate = (
  draft: { name: string; description?: string; steps: KelRecipeStepDraft[] },
  scope: string | KelScope = GENERAL_SCOPE
) => call<{ saved: boolean; recipe_id?: string }>('/api/recipes', { action: 'create', ...draft, ...scopeBody(scope) });

/** FN-12: rename or edit a recipe (a new version in this project; history is kept). */
export const kelRecipeUpdate = (
  recipeId: string,
  changes: { name?: string; description?: string; steps?: KelRecipeStepDraft[] },
  scope: string | KelScope = GENERAL_SCOPE
) => call<{ saved: boolean; reason?: string }>('/api/recipes', { action: 'update', recipe_id: recipeId, ...changes, ...scopeBody(scope) });

export const kelRecipeDuplicate = (recipeId: string, scope: string | KelScope = GENERAL_SCOPE) =>
  call<{ recipe_id?: string; id?: string } & Record<string, unknown>>('/api/recipes', {
    action: 'duplicate',
    recipe_id: recipeId,
    ...scopeBody(scope),
  });

// ---------------------------------------------------------------------------------------------
// D-57 Scheduled tasks: a schedule is a trigger the engine keeps. Each firing becomes an ordinary
// submission → hand-off → job, so its runs show on Work, Activity and Needs you like any other
// work. The engine owns the list, the cadence maths ("Every weekday at 9:00", the next runs) and
// each schedule's run history; this surface only renders and edits.
// ---------------------------------------------------------------------------------------------
export type KelScheduleCadence =
  | { kind: 'manual' }
  | { kind: 'cron'; expr: string }
  | { kind: 'interval'; minutes: number }
  /** `at` is epoch seconds, like every engine time. */
  | { kind: 'once'; at: number };

export type KelScheduleTarget =
  | { kind: 'instruction'; text: string }
  | { kind: 'recipe'; recipe_id: string; inputs?: Record<string, unknown>; recipe_name?: string | null };

/** Same shape as the model control's choice; null or no provider means Automatic. */
export interface KelModelChoice {
  provider: string | null;
  model: string | null;
}

export type KelScheduleStartMode = 'new_conversation' | 'existing';

export interface KelScheduleRun {
  at?: number | null;
  slot?: number | null;
  late_by?: number | null;
  /** The engine conversation the run posted in. */
  conversation?: string | null;
  job_id?: string | null;
  submission_id?: string | null;
  /**
   * running | needs_you | success | needs_look | stopped | not_started | settled | skipped | queued |
   * coalesced | missed | imported — for colour only; the words are in `label`.
   */
  status?: string | null;
  /** The engine's plain label: "Success", "Failed", "Finished — needs a look", "Missed 3 runs…". */
  label?: string | null;
  /** Why, in plain words, when there is a reason worth saying. */
  cause?: string | null;
}

export interface KelSchedule {
  id: string;
  name: string;
  project_id: string;
  project_name?: string | null;
  target: KelScheduleTarget | null;
  cadence: KelScheduleCadence | null;
  timezone?: string | null;
  start_mode: KelScheduleStartMode;
  conversation_id?: string | null;
  model?: KelModelChoice | null;
  /** The engine's plain name for the model ("Automatic" when none). */
  model_label?: string | null;
  conversation_title?: string | null;
  timezone_label?: string | null;
  skip_if_running: boolean;
  enabled: boolean;
  /** active | paused | needs_attention | done | manual (the engine's own reading). */
  status?: string | null;
  /** A run of it is going right now. */
  running?: boolean;
  next_due_at?: number | null;
  last_slot?: number | null;
  /** Set (and the schedule paused) when its recipe, project or conversation is gone. */
  problem?: string | null;
  /** The migrated donor task id, for links written before the move (`/scheduled?origin=…`). */
  origin?: string | null;
  /** The engine's own sentence for the cadence. */
  description?: string | null;
  created?: number | null;
  updated?: number | null;
  deleted?: number | null;
  last_run?: KelScheduleRun | null;
}

export interface KelScheduleDraft {
  name: string;
  project_id: string;
  target: KelScheduleTarget;
  cadence: KelScheduleCadence;
  /** An IANA zone, or null to follow this computer's zone. */
  timezone: string | null;
  start_mode: KelScheduleStartMode;
  conversation_id?: string | null;
  model: KelModelChoice | null;
  skip_if_running: boolean;
}

export interface KelSchedulePreview {
  /** False when Kel cannot use this timing; `message` says why. The engine never refuses a preview. */
  valid?: boolean;
  message?: string | null;
  description?: string;
  timezone_label?: string | null;
  /** The next few due times, epoch seconds. */
  next?: number[];
}

const parseMaybeJson = (value: unknown): unknown => {
  if (typeof value !== 'string') return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
};

const truthy = (value: unknown, fallback: boolean): boolean =>
  value === undefined || value === null ? fallback : value === true || value === 1 || value === '1' || value === 'true';

const numberOrNull = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null);

const normalizeCadence = (value: unknown): KelScheduleCadence | null => {
  const raw = parseMaybeJson(value) as Record<string, unknown> | null;
  if (!raw || typeof raw !== 'object') return null;
  switch (raw.kind) {
    case 'manual':
      return { kind: 'manual' };
    case 'cron':
      return typeof raw.expr === 'string' ? { kind: 'cron', expr: raw.expr } : null;
    case 'interval':
      return typeof raw.minutes === 'number' ? { kind: 'interval', minutes: raw.minutes } : null;
    case 'once': {
      const at = typeof raw.at === 'number' ? raw.at : typeof raw.at === 'string' ? Date.parse(raw.at) / 1000 : NaN;
      return Number.isFinite(at) ? { kind: 'once', at } : null;
    }
    default:
      return null;
  }
};

const normalizeTarget = (value: unknown): KelScheduleTarget | null => {
  const raw = parseMaybeJson(value) as Record<string, unknown> | null;
  if (!raw || typeof raw !== 'object') return null;
  if (raw.kind === 'instruction' && typeof raw.text === 'string') return { kind: 'instruction', text: raw.text };
  if (raw.kind === 'recipe' && typeof raw.recipe_id === 'string') {
    const inputs = parseMaybeJson(raw.inputs);
    return {
      kind: 'recipe',
      recipe_id: raw.recipe_id,
      recipe_name: typeof raw.recipe_name === 'string' ? raw.recipe_name : null,
      ...(inputs && typeof inputs === 'object' ? { inputs: inputs as Record<string, unknown> } : {}),
    };
  }
  return null;
};

const normalizeModel = (value: unknown): KelModelChoice | null => {
  const raw = parseMaybeJson(value) as Record<string, unknown> | null;
  if (!raw || typeof raw !== 'object' || typeof raw.provider !== 'string' || !raw.provider) return null;
  return { provider: raw.provider, model: typeof raw.model === 'string' ? raw.model : null };
};

const normalizeRun = (value: unknown): KelScheduleRun | null => {
  if (!value || typeof value !== 'object') return null;
  const raw = value as Record<string, unknown>;
  const text = (key: string) => (typeof raw[key] === 'string' && raw[key] ? (raw[key] as string) : null);
  return {
    at: numberOrNull(raw.at),
    slot: numberOrNull(raw.slot),
    late_by: numberOrNull(raw.late_by),
    conversation: text('conversation') ?? text('conversation_id'),
    job_id: text('job_id'),
    submission_id: text('submission_id'),
    status: text('status'),
    label: text('label'),
    cause: text('cause'),
  };
};

/**
 * One schedule as this surface can use it, or null when the payload is not one (JR-47: a row the
 * engine sends in another shape degrades to "unavailable", it never breaks the page). The engine
 * keeps target/cadence/model as JSON text; either form is accepted.
 */
export const normalizeSchedule = (value: unknown): KelSchedule | null => {
  if (!value || typeof value !== 'object') return null;
  const raw = value as Record<string, unknown>;
  if (typeof raw.id !== 'string' || !raw.id) return null;
  const project = raw.project as { name?: unknown } | undefined;
  return {
    id: raw.id,
    name: typeof raw.name === 'string' && raw.name.trim() ? raw.name : 'Untitled task',
    project_id: typeof raw.project_id === 'string' ? raw.project_id : 'default',
    project_name:
      typeof raw.project_name === 'string' ? raw.project_name : typeof project?.name === 'string' ? project.name : null,
    target: normalizeTarget(raw.target),
    cadence: normalizeCadence(raw.cadence),
    timezone: typeof raw.timezone === 'string' ? raw.timezone : null,
    start_mode: raw.start_mode === 'existing' ? 'existing' : 'new_conversation',
    conversation_id: typeof raw.conversation_id === 'string' && raw.conversation_id ? raw.conversation_id : null,
    model: normalizeModel(raw.model),
    model_label: typeof raw.model_label === 'string' && raw.model_label ? raw.model_label : null,
    conversation_title: typeof raw.conversation_title === 'string' && raw.conversation_title ? raw.conversation_title : null,
    timezone_label: typeof raw.timezone_label === 'string' && raw.timezone_label ? raw.timezone_label : null,
    skip_if_running: truthy(raw.skip_if_running, true),
    enabled: truthy(raw.enabled, true),
    status: typeof raw.status === 'string' && raw.status ? raw.status : null,
    running: truthy(raw.running, false),
    next_due_at: numberOrNull(raw.next_due_at),
    last_slot: numberOrNull(raw.last_slot),
    problem: typeof raw.problem === 'string' && raw.problem.trim() ? raw.problem : null,
    origin: typeof raw.origin === 'string' && raw.origin ? raw.origin : null,
    description: typeof raw.description === 'string' && raw.description.trim() ? raw.description : null,
    created: numberOrNull(raw.created),
    updated: numberOrNull(raw.updated),
    deleted: numberOrNull(raw.deleted),
    last_run: normalizeRun(raw.last_run),
  };
};

const listOf = (payload: unknown, keys: string[]): unknown[] => {
  if (Array.isArray(payload)) return payload;
  const body = (payload ?? {}) as Record<string, unknown>;
  for (const key of keys) if (Array.isArray(body[key])) return body[key] as unknown[];
  return [];
};

/** Live (not deleted) schedules from a list answer; rows in another shape are dropped. */
export const normalizeScheduleList = (payload: unknown): KelSchedule[] =>
  listOf(payload, ['schedules', 'items'])
    .map(normalizeSchedule)
    .filter((item): item is KelSchedule => item !== null && !item.deleted);

export const normalizeScheduleHistory = (payload: unknown): KelScheduleRun[] =>
  listOf(payload, ['rows', 'history', 'runs', 'items'])
    .map(normalizeRun)
    .filter((item): item is KelScheduleRun => item !== null);

const scheduleAction = <T,>(action: string, body: Record<string, unknown> = {}) =>
  call<T>('/api/schedules', { action, ...body });

const oneSchedule = (payload: unknown): KelSchedule | null =>
  normalizeSchedule((payload as { schedule?: unknown } | null)?.schedule ?? payload);

export const kelSchedules = {
  list: () => scheduleAction<unknown>('list').then(normalizeScheduleList),
  /** By id, or by the donor task id a pre-move link carries. Null when there is none. */
  get: (ref: { id: string } | { origin: string }) => scheduleAction<unknown>('get', ref).then(oneSchedule),
  create: (draft: KelScheduleDraft) => scheduleAction<unknown>('create', { ...draft }).then(oneSchedule),
  /** Only the keys sent change. */
  update: (id: string, changes: Partial<KelScheduleDraft>) =>
    scheduleAction<unknown>('update', { id, ...changes }).then(oneSchedule),
  pause: (id: string) => scheduleAction<unknown>('pause', { id }).then(oneSchedule),
  resume: (id: string) => scheduleAction<unknown>('resume', { id }).then(oneSchedule),
  /**
   * `conversations: 'delete'` hides the chats its finished runs opened (`hidden`, engine ids) while
   * runs still going are kept (`kept_open`).
   */
  remove: (id: string, conversations: 'keep' | 'delete') =>
    scheduleAction<{ ok?: boolean; id?: string; hidden?: string[]; kept_open?: string[] }>('delete', { id, conversations }),
  runNow: (id: string) => scheduleAction<{ submission?: string; conversation?: string } & Record<string, unknown>>('run_now', { id }),
  history: (id: string) => scheduleAction<unknown>('history', { id }).then(normalizeScheduleHistory),
  preview: (cadence: KelScheduleCadence, timezone?: string | null) =>
    scheduleAction<KelSchedulePreview>('preview', { cadence, ...(timezone ? { timezone } : {}) }),
  migrationStatus: () => scheduleAction<Record<string, unknown>>('migration_status'),
};

// ---------------------------------------------------------------------------------------------
// D-54 Projects: the engine owns the project list and the one active project (the same on every
// device). `kind` separates General (the default project), the person's own projects, and the
// engine's plumbing rows, which no surface lists.
// ---------------------------------------------------------------------------------------------
export interface KelProject {
  id: string;
  name: string;
  root?: string | null;
  has_folder?: boolean;
  test_command?: string[] | null;
  kind?: 'general' | 'user' | 'system';
  /** When it was archived (epoch seconds); null/absent while live. */
  archived?: number | null;
  conversations?: number;
  open_work?: number;
  needs_you?: number;
  updated?: number;
  last_active?: number | null;
}

/** The active project id, or '*' for "All projects". */
export type KelActiveProject = string;

const normalizeProjectList = (payload: unknown): { projects: KelProject[]; active?: string } => {
  if (Array.isArray(payload)) return { projects: payload as KelProject[] };
  const body = (payload ?? {}) as { projects?: unknown; active?: unknown; active_project?: unknown };
  const active =
    typeof body.active === 'string' ? body.active : typeof body.active_project === 'string' ? body.active_project : undefined;
  return { projects: Array.isArray(body.projects) ? (body.projects as KelProject[]) : [], ...(active ? { active } : {}) };
};

const projectAction = <T,>(action: string, body: Record<string, unknown> = {}) =>
  call<T>('/api/project', { action, ...body });

export const kelProjects = {
  list: (options: { include_archived?: boolean; include_system?: boolean } = {}) =>
    projectAction<unknown>('list', options).then(normalizeProjectList),
  create: (project: { name: string; root?: string | null; test_command?: string[] | null; context?: string }) =>
    projectAction<{ id: string } & Partial<KelProject>>('create', project),
  /** Only the keys sent change; `test_command: null` removes the command. */
  update: (id: string, changes: Partial<Pick<KelProject, 'name' | 'root' | 'test_command'>> & { context?: string }) =>
    projectAction<{ id: string } & Partial<KelProject>>('update', { id, ...changes }),
  /** The live project for a folder, created (named after the folder) when there is none. */
  forFolder: (root: string) => projectAction<{ id: string } & Partial<KelProject>>('for_folder', { root }),
  archive: (id: string) => projectAction<Record<string, unknown>>('archive', { id }),
  restore: (id: string) => projectAction<Record<string, unknown>>('restore', { id }),
  /** Only a project that owns nothing can be deleted; the engine says what to do otherwise. */
  remove: (id: string) => projectAction<Record<string, unknown>>('delete', { id }),
  setActive: (id: KelActiveProject) => projectAction<{ active?: string } & Record<string, unknown>>('set_active', { id }),
  /** Tie a chat (by its app conversation id) to a project before its first message reaches Kel. */
  bind: (donor: string, project: string) => projectAction<Record<string, unknown>>('bind', { donor, project }),
  /** The project a chat belongs to; `pending` while Kel has not seen its first message yet. */
  of: (target: { conversation?: string; donor?: string }) =>
    projectAction<{ project?: string | (Partial<KelProject> & { id: string }) | null; pending?: boolean }>('of', target),
};

export interface KelProviderStatus {
  /** CH-2/CP-3: Kel can answer with it right now — a usable credential and a way to run it. */
  available: boolean;
  /** Why it is not available, in plain words ("Not supported for chat yet"); null when it is. */
  available_note: string | null;
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
  models: Array<{ id: string; capabilities: string[]; label?: string }>;
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
      chosen: { provider: string; model: string; label: string; model_label?: string; status: string; auth_mode: string } | null;
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

// ---------------------------------------------------------------------------------------------
// Fix Capture (V2.0 preflight): a fix is Nick's own words plus the context Kel captured for it.
// The statuses are deliberately the only workflow this has.
// ---------------------------------------------------------------------------------------------
export const FIX_STATUSES = ['OPEN', 'BATCHED', 'FIXED', 'DISMISSED'] as const;
export type KelFixStatus = (typeof FIX_STATUSES)[number];

export interface KelFixElement {
  tag?: string;
  role?: string | null;
  text?: string;
  label?: string | null;
  selector?: string;
  rect?: { x: number; y: number; width: number; height: number };
}

export interface KelFixWindow {
  width?: number;
  height?: number;
  scale?: number;
}

export interface KelFix {
  id: string;
  created: number;
  updated: number;
  status: KelFixStatus;
  transcript: string;
  screenshot?: string | null;
  has_screenshot?: boolean;
  route?: string | null;
  page_title?: string | null;
  element?: KelFixElement | null;
  window?: KelFixWindow | null;
  project_id?: string | null;
  conversation?: string | null;
  version?: string | null;
  prompt_id?: string | null;
}

export interface KelFixList {
  fixes: KelFix[];
  counts: Record<KelFixStatus, number>;
  statuses: KelFixStatus[];
}

/** What the main process hands back for one captured window. */
export interface KelFixCapture {
  screenshot: string;
  image: { width: number; height: number };
  content: { width: number; height: number };
  display: { scale: number };
  captured_at: number;
}

export const kelDogfood = {
  list: (status?: KelFixStatus) =>
    call<KelFixList>('/api/dogfood', status ? { action: 'list', status } : undefined),
  get: (id: string) => call<KelFix>(`/api/dogfood?action=get&id=${encodeURIComponent(id)}`),
  save: (body: {
    transcript: string;
    screenshot?: string | null;
    route?: string | null;
    page_title?: string | null;
    element?: KelFixElement | null;
    window?: KelFixWindow | null;
    version?: string | null;
    conversation?: string | null;
  }) => call<KelFix>('/api/dogfood', { action: 'save', ...body }),
  setStatus: (id: string, status: KelFixStatus) =>
    call<KelFix>('/api/dogfood', { action: 'set_status', id, status }),
  preparePrompt: (fixIds?: string[]) =>
    call<{ prompt: string; prompt_id: string; path: string; fix_ids: string[]; marked: string }>(
      '/api/dogfood',
      { action: 'prepare_prompt', ...(fixIds && fixIds.length ? { fix_ids: fixIds } : {}) }
    ),
  /**
   * One window capture, written by the main process into the data root. Returns null on surfaces
   * that cannot read Kel's window (the remote browser) so the caller can say so honestly.
   */
  capture: async (): Promise<KelFixCapture | null> => {
    const api = typeof window === 'undefined' ? undefined : window.kelAPI;
    if (!api?.dogfood?.capture) return null;
    try {
      return (await api.dogfood.capture()) as KelFixCapture;
    } catch {
      return null;
    }
  },
  /** A saved screenshot as a data URL for display; null when it cannot be read here. */
  screenshot: async (relpath: string | null | undefined): Promise<string | null> => {
    const api = typeof window === 'undefined' ? undefined : window.kelAPI;
    if (!relpath || !api?.dogfood?.screenshot) return null;
    try {
      return ((await api.dogfood.screenshot(relpath)) as { data_url: string }).data_url;
    } catch {
      return null;
    }
  },
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

/**
 * D-64: how much Kel does without asking. `full` (the default Nick chose) lets Kel act without
 * approval prompts; `ask` brings the prompts back. Only the person's own request changes it.
 */
export type KelAuthorityMode = 'full' | 'ask';
export interface KelAuthorityState {
  mode?: string;
  /** Tolerated alias; the engine answers with `mode`. */
  authority_mode?: string;
  label?: string;
  description?: string;
  updated?: number | null;
  changed_by_you?: boolean;
}

/** The mode in an engine answer, or null when the answer carries none (an engine without D-64). */
export const authorityModeOf = (state: KelAuthorityState | null | undefined): KelAuthorityMode | null => {
  const value = state?.mode ?? state?.authority_mode;
  return value === 'full' || value === 'ask' ? value : null;
};

export const kelAuthority = {
  get: () => call<KelAuthorityState>('/api/autonomy', { action: 'mode' }),
  set: (mode: KelAuthorityMode) => call<KelAuthorityState>('/api/autonomy', { action: 'set_mode', mode }),
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
      /** FN-14: how long Kel's model took to answer recent messages (null until one is measured). */
      first_reply?: { latest_ms: number; median_ms: number; samples: number; basis: string } | null;
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

/** `/api/state` scope for every conversation's work (Work, Activity, Permissions, Needs you, palette). */
export const KEL_ALL_CONVERSATIONS = '*';

export const kelState = (conversation = 'main', project?: KelActiveProject) =>
  call<{
    jobs: KelWorkJob[];
    continuation?: KelContinuationCandidate[];
    approvals?: Array<Record<string, unknown>>;
    providers: string[];
    /** D12: routing decisions for active jobs, keyed by job id. */
    routes?: Record<string, KelJobRoute>;
    projects: Array<{ id: string; name: string } & Partial<KelProject>>;
    /** D-54: the engine's active project id, or '*' for all projects. */
    active_project?: string;
    engine_version?: string;
    draining?: boolean;
    /** D6: the engine's recorded restore outcome (audit PER-02); null when never attempted. */
    restore?: { ok: boolean; detail?: string; at?: number } | null;
  }>(`/api/state?conversation=${encodeURIComponent(conversation)}${project ? `&project=${encodeURIComponent(project)}` : ''}`);

export const kelControl = (job: string, action: 'pause' | 'resume' | 'cancel') =>
  call<{ ok: boolean }>('/api/control', { job, action });

/**
 * D-65: where a verified coding change stands in the project folder. `state` is the application
 * journal (null = not applied yet); `auto` = Full access applied it on its own; `waiting_reason` =
 * why it waits for you to Apply or Leave it (null once applied or answered); `ask_first` = it waits
 * only because Ask first was on (so the card offers "Apply", not "Apply anyway").
 */
export interface KelChangeApplication {
  state: 'PREPARED' | 'APPLIED' | 'BLOCKED' | 'UNDOING' | 'UNDONE' | null;
  auto: boolean;
  decision?: string | null;
  root: string | null;
  files: number | null;
  waiting_reason: string | null;
  ask_first?: boolean;
  /** The project's saved name and its folder's name (the full path stays in `root`, for Open folder). */
  project_name?: string | null;
  folder?: string | null;
}

/** D-65: put back the files an applied change replaced, from the saved backup. */
export const kelUndoChange = (job: string) => call<Record<string, unknown>>('/api/apply', { job, action: 'undo' });

/** Retry a saved request that failed. The engine refuses anything that is not FAILED/INTERRUPTED. */
export const kelRetry = (id: string) => call<{ id: string }>('/api/retry', { id });

/** D-53: where one conversational hand-off stands, for its in-chat card. */
export type KelHandoffPhase =
  | 'starting'
  | 'running'
  | 'needs_you'
  | 'waiting'
  | 'done'
  | 'needs_look'
  | 'stopped'
  | 'failed_to_start';

export interface KelHandoff {
  submission_id: string;
  conversation: string;
  submission_state: string;
  title: string | null;
  ack_seq: number | null;
  job_id: string | null;
  state: string | null;
  verdict: string | null;
  accepted: number;
  total: number;
  why: string | null;
  next: string | null;
  error: string | null;
  phase: KelHandoffPhase;
  can_stop: boolean;
  can_retry: boolean;
  /** D-65: coding work only. */
  application?: KelChangeApplication | null;
}

/** The engine refuses a submission that belongs to another conversation. */
export const kelHandoff = (conversation: string, submission: string) =>
  call<KelHandoff>(
    `/api/handoff?conversation=${encodeURIComponent(conversation)}&submission=${encodeURIComponent(submission)}`
  );

// ---------------------------------------------------------------------------------------------
// D-66 / D-68 — the live work view (the row of work cards at the top of the chat). Read-only
// engine state apart from removing a finished card. Contract: docs/v2/design/D-66_WORKFORCE_LIVE.md §4.
// A model is only named once its runtime reported it (`model_confirmed`); what was asked for and
// why it differs are separate fields, so the page never shows a model that did not run.
// ---------------------------------------------------------------------------------------------

export type KelOfficeState = 'working' | 'in_review' | 'needs_you' | 'done' | 'stopped' | 'failed';
export type KelOfficeKind = 'code' | 'writing' | 'research' | 'recipe';
export type KelOfficeStaffState = 'working' | 'done' | 'failed' | 'stopped' | 'waiting';

export interface KelOfficeProgress {
  done: number;
  total: number;
  /** The phase in words ("2 of 3 steps done", "Checking the result") — never a percentage. */
  label: string;
}

export interface KelOfficeTeamChip {
  role: string;
  role_label: string;
  state: KelOfficeStaffState;
}

export interface KelOfficeItem {
  job_id: string;
  title: string;
  project_id: string | null;
  conversation_id: string | null;
  submission_id: string | null;
  kind: KelOfficeKind;
  state: KelOfficeState;
  /** True for done / failed / stopped: the card stays until Nick removes it (D-68). */
  finished: boolean;
  /** Kel's one-line plain status. */
  status_line: string | null;
  needs_you: boolean;
  progress: KelOfficeProgress;
  team: KelOfficeTeamChip[];
  team_size: number;
  started_at: number | null;
  updated_at: number | null;
  finished_at: number | null;
  /** The engine's stable order: needs-you, then working / in review, then finished (newest first). */
  order: number;
}

export interface KelOfficeList {
  generated: number;
  scope: { conversation: string | null; project: string | null };
  items: KelOfficeItem[];
}

export interface KelOfficeStaff {
  id: string;
  role: string;
  role_label: string;
  instance: number | null;
  doing: string;
  state: KelOfficeStaffState;
  /** Set only when the runtime reported it (`model_confirmed`). */
  model: string | null;
  model_label: string | null;
  version: string | null;
  model_confirmed: boolean;
  provider: string | null;
  runtime: string | null;
  runtime_version: string | null;
  reasoning: string | null;
  /** What the role asked for, when it is not (yet) what ran. */
  asked: { model_label: string | null; reasoning: string | null } | null;
  /** Why it differs, in plain words (a fallback, a less independent review). */
  note: string | null;
  independence: 'different' | 'reduced' | null;
  step: string | null;
  started_at: number | null;
  finished_at: number | null;
}

export interface KelOfficeFinding {
  severity: 'blocker' | 'critical' | 'note';
  area: string;
  summary: string;
  where: string | null;
  status: 'open' | 'resolved';
}

export interface KelOfficeDetail extends KelOfficeItem {
  why: string | null;
  next: string | null;
  staff: KelOfficeStaff[];
  steps: { id: string; label: string; state: string; at: number | null; attempts: number | null }[];
  review: { verdict: string | null; checked_by: string | null; independence: string | null; findings: KelOfficeFinding[] };
  oracle: {
    state: 'not_needed' | 'waiting' | 'running' | 'done' | 'could_not_run';
    why: string | null;
    independence: string | null;
    model_label: string | null;
    reasoning: string | null;
    findings: KelOfficeFinding[];
  };
  files_changed: string[] | null;
  application: KelChangeApplication | null;
  verification: { result: 'passed' | 'failed' | 'not_confirmed' | null; summary: string[] };
  /** The published result, shortened, once there is one. */
  result: string | null;
  links: { conversation_id: string | null; submission_id: string | null; message_seq: number | null };
  /** D-72: the work's totals — tokens, time and approximate cost — for the detail header. */
  usage?: KelUsage | null;
}

/** D-72: what Kel's messages in one conversation used ({message seq: usage}), or one job's totals. */
export type KelUsageView = {
  conversation?: string;
  messages?: Record<string, KelUsage>;
  job?: string;
  usage?: KelUsage | null;
};

export const kelUsage = (scope: { conversation: string } | { job: string }) =>
  call<KelUsageView>(
    'conversation' in scope
      ? `/api/usage?conversation=${encodeURIComponent(scope.conversation)}`
      : `/api/usage?job=${encodeURIComponent(scope.job)}`
  );

/** The work cards for one chat, one project, or everything (`'*'`). */
export const kelOffice = (scope: { conversation: string } | { project: string } | '*' = '*') => {
  if (scope === '*') return call<KelOfficeList>('/api/office?project=*');
  if ('conversation' in scope) return call<KelOfficeList>(`/api/office?conversation=${encodeURIComponent(scope.conversation)}`);
  return call<KelOfficeList>(`/api/office?project=${encodeURIComponent(scope.project || '*')}`);
};

/** One piece of work in full: team, steps, review and second opinion, files, verification. */
export const kelOfficeItem = (job: string) => call<KelOfficeDetail>(`/api/office/item?job=${encodeURIComponent(job)}`);

/** Remove a finished card (D-68). Idempotent; the work, its chat and its evidence are kept. */
export const kelOfficeDismiss = (job: string) =>
  call<{ dismissed: boolean; already: boolean; job_id: string }>('/api/office', { action: 'dismiss', id: job });
