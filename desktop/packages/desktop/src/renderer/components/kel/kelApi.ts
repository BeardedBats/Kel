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

export const kelRecipeGet = (recipeId: string, conversation = 'main') =>
  call<{ recipe: { recipe_id: string; name: string; inputs: KelRecipeInput[]; steps: Array<{ id: string; title: string }> } }>('/api/recipes', {
    action: 'get', recipe_id: recipeId, conversation,
  });

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
export const kelRecipeHistory = (recipeId: string, conversation = 'main') =>
  call<{ history: KelRecipeRun[] }>('/api/recipes', {
    action: 'history',
    recipe_id: recipeId,
    conversation,
  });

/** The one-line answer to "what happened last time I ran this?" */
export const kelRecipeLastResult = (recipeId: string, conversation = 'main') =>
  call<{ recipe_id: string; state: string; sentence: string } & Record<string, unknown>>(
    '/api/recipes',
    { action: 'last_result', recipe_id: recipeId, conversation }
  );

/** The library's own controls (V2-07): search, categories, favourites, recent, duplicate. */
export const kelRecipeSearch = (query: string, conversation = 'main') =>
  call<{ entries: KelRecipeEntry[] }>('/api/recipes', { action: 'search', query, conversation });

export const kelRecipeCategories = (conversation = 'main') =>
  call<{ categories: Array<{ name: string; count: number }> }>('/api/recipes', { action: 'categories', conversation });

export const kelRecipeRecent = (limit = 5, conversation = 'main') =>
  call<{ recent: KelRecipeEntry[] }>('/api/recipes', { action: 'recent', limit, conversation });

/** Star or unstar one recipe. */
export const kelRecipeFavourite = (recipeId: string, favourite: boolean, conversation = 'main') =>
  call<Record<string, unknown>>('/api/recipes', {
    action: 'favourites',
    recipe_id: recipeId,
    favourite,
    conversation,
  });

/** Copy a recipe inside this project (the engine keeps the copy in the project scope). */
export const kelRecipeDuplicate = (recipeId: string, conversation = 'main') =>
  call<{ recipe_id?: string; id?: string } & Record<string, unknown>>('/api/recipes', {
    action: 'duplicate',
    recipe_id: recipeId,
    conversation,
  });

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
  /**
   * Kibble Build Update (D-46/D-47): turn selected findings into a development mission and a
   * reviewable candidate. Fix Capture statuses are never touched by any of it, and `promote` is
   * exposed so the surface can show the engine's own refusal — installing is a separate decision.
   */
  buildUpdate: {
    start: (findings: string[], sourceRoot: string, tests: string[] = []) =>
      call<{ mission: KelBuildMission; job: string; contract: Record<string, unknown> }>(
        '/api/dogfood',
        { action: 'build_update', op: 'start', findings, source_root: sourceRoot, tests }
      ),
    status: (mission: string) =>
      call<{
        mission: KelBuildMission;
        job: { id: string; state?: string; verdict?: string; milestones?: Record<string, { state?: string; attempts?: number }> } | null;
        candidate: KelBuildCandidate | null;
      }>('/api/dogfood', { action: 'build_update', op: 'status', mission }),
    candidate: (mission: string) =>
      call<{ state: string; candidate: KelBuildCandidate | null; job_state?: string }>(
        '/api/dogfood',
        { action: 'build_update', op: 'candidate', mission }
      ),
    review: (candidate: string, decision: 'approve' | 'reject', note = '') =>
      call<KelBuildCandidate>('/api/dogfood', {
        action: 'build_update',
        op: 'review',
        candidate,
        decision,
        note,
      }),
    promote: (candidate: string) =>
      call<Record<string, unknown>>('/api/dogfood', {
        action: 'build_update',
        op: 'promote',
        candidate,
      }),
  },
};

export interface KelBuildMission {
  id: string;
  job_id?: string | null;
  stage?: string;
  source_root?: string;
  baseline_revision?: string | null;
  findings?: string[];
}

export interface KelBuildCandidate {
  id: string;
  mission_id?: string;
  review_state?: string;
  revision?: string | null;
  artifact_location?: string | null;
  evidence?: { verified?: boolean; [key: string]: unknown };
  fixed_findings?: string[];
  unresolved_findings?: string[];
  limitations?: string[];
  note?: string | null;
}

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

export const kelState = (conversation = 'main') =>
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
  }>(`/api/state?conversation=${encodeURIComponent(conversation)}`);

/** Markdown artifact text for an ACCEPTED milestone (the engine refuses anything unverified). */
export const kelArtifact = (job: string, milestone: string) =>
  call<unknown>(
    `/api/artifact?job=${encodeURIComponent(job)}&milestone=${encodeURIComponent(milestone)}`
  );

export const kelControl = (job: string, action: 'pause' | 'resume' | 'cancel') =>
  call<{ ok: boolean }>('/api/control', { job, action });

/** Answer the permission request a Work row is waiting on. */
export const kelApproval = (id: string, allow: boolean, conversation?: string) =>
  call<{ ok?: boolean } & Record<string, unknown>>('/api/approval', {
    id,
    allow,
    ...(conversation ? { conversation } : {}),
  });

/** A fenced run resumes as a normal conversation continuation, never as a silent replay. */
export const kelSend = (conversation: string, text: string) =>
  call<{ id: string }>('/api/send', { conversation, text });

/** Retry a saved request that failed. The engine refuses anything that is not FAILED/INTERRUPTED. */
export const kelRetry = (id: string) => call<{ id: string }>('/api/retry', { id });

/** One row of the V2-06 attention surface: what it is, why, and the one action it offers. */
export interface KelWorkRow {
  job_id: string;
  needs_you?: boolean;
  priority?: 'now' | 'soon' | 'running' | 'later';
  reason?: string;
  next?: string;
  direct?: { action: string; route: string; hint?: string; id?: string | null } | null;
  related?: { project_id?: string; conversation?: string; approvals?: number; milestones?: number };
}

/** The rows themselves — the same authoritative surface the chat's Work panel reads. */
export const kelWorkRows = (conversation = 'main') =>
  call<{ work?: { jobs?: KelWorkRow[] } }>(`/api/work?conversation=${encodeURIComponent(conversation)}`)
    .then((payload) => payload.work?.jobs ?? []);

export const kelBriefs = {
  list: (projectId = 'default') =>
    call<{ briefs: Array<{ brief_id: string; goal: string; state: string; chosen_option: string | null; updated: number }> }>(
      '/api/brief',
      { action: 'list', project_id: projectId }
    ),
};
