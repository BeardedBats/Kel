/**
 * D-67 / D-70 item 3 — the model each staff role runs on, read and changed through the engine's
 * allowlisted `/api/model` route (docs/v2/design/D-66_WORKFORCE_LIVE.md §2 "Settings API"):
 * `{action:'roles'}`, `{action:'set_role', role, mode, model?, reasoning?}`, `{action:'reset_role', role}`.
 * Every action answers with the whole listing, so the page always renders what the engine now holds.
 * The engine owns the catalog and what can run here; this module only asks and names things plainly.
 */
import { kelRequest } from '../kelApi';

export type StaffMode = 'AUTOMATIC' | 'PREFERRED' | 'FIXED';

export interface StaffRoleRow {
  role: string;
  label: string;
  mode: StaffMode;
  mode_label?: string | null;
  model: string | null;
  model_label?: string | null;
  reasoning: string;
  reasoning_label?: string | null;
  reasoning_options?: string[];
  /** False when the chosen model cannot run on this computer; `note` says why in plain words. */
  available?: boolean;
  note?: string | null;
  is_default?: boolean;
  /** Models the role falls back to (labels) when its preferred one cannot run. */
  fallbacks?: string[];
  default?: { mode: StaffMode; model: string | null; reasoning: string } | null;
  /** What this role's last run asked for and what actually ran (the engine's record). */
  last_run?: StaffLastRun | null;
  /** LIVE-3: the work the role exists for — `code` (changes code), `web` (searches the web) or `text`. */
  purpose?: StaffPurpose | string | null;
  /**
   * LIVE-3: the models this role can pick, each available or not *for this role* with the engine's
   * reason (DeepSeek Flash can't be the Builder: it can't change code).
   */
  model_options?: StaffRoleModelOption[] | null;
}

export type StaffPurpose = 'code' | 'web' | 'text';

export interface StaffRoleModelOption {
  id: string;
  label: string;
  available?: boolean;
  note?: string | null;
}

/** What each purpose asks of a model, in plain words. */
export const PURPOSE_WORDS: Record<string, string> = {
  code: 'Needs a model that can change code',
  web: 'Needs a model that can search the web',
  text: 'Any model that writes well',
};

/**
 * FN-06 — Kel's own model, and whether a chat overrides it (`in_effect`), exactly as the engine holds
 * it (the roles payload and `/api/model get` both carry it).
 */
export interface KelModelView {
  kel?: { source?: string | null; mode?: StaffMode | null; model?: string | null; reasoning?: string | null; label?: string | null } | null;
  conversation_override?: { provider?: string | null; model?: string | null; label?: string | null } | null;
  in_effect?: 'kel' | 'conversation' | string | null;
}

/**
 * The one line that says which model is in effect: for a chat, "This chat uses its own model: X"
 * or "This chat uses Kel's model: Y"; with no chat, Kel's model and that a chat may pick its own.
 */
export const inEffectLine = (view: KelModelView | null | undefined, forChat: boolean): string | null => {
  if (!view?.kel) return null;
  const kel = (view.kel.label ?? '').trim() || 'Automatic';
  const own = (view.conversation_override?.label ?? view.conversation_override?.model ?? '').trim();
  if (forChat && view.in_effect === 'conversation' && own) {
    return `This chat uses its own model: ${own}. Kel’s model (the Kel row below) is ${kel}.`;
  }
  if (forChat) return `This chat uses Kel’s model: ${kel}.`;
  return `Kel’s model: ${kel}. Every chat uses it unless you pick another model in that chat.`;
};

export interface StaffLastRun {
  asked?: string | null;
  asked_label?: string | null;
  ran?: string | null;
  ran_label?: string | null;
  /** False until the runtime reported the model (then `ran` is the model Kel handed the work to). */
  confirmed?: boolean;
  fell_back?: boolean;
  at?: number | null;
  why?: string | null;
}

/** "Fell back to Codex last time: <why>." — null when the last run ran what was asked. */
export const fellBackLine = (last: StaffLastRun | null | undefined): string | null => {
  if (!last?.fell_back || !last.ran_label) return null;
  const why = String(last.why ?? '').trim().replace(/[.\s]+$/, '');
  return `Fell back to ${last.ran_label} last time${last.asked_label ? ` (asked for ${last.asked_label})` : ''}${why ? `: ${why}` : ''}.`;
};

export interface StaffModelOption {
  id: string;
  label: string;
  version?: string | null;
  runtime?: string | null;
  available?: boolean;
  note?: string | null;
  reasoning_options?: string[];
}

export interface StaffListing {
  roles: StaffRoleRow[];
  models: StaffModelOption[];
  modes?: Array<{ id: StaffMode; label: string }>;
  /** FN-06: Kel's own model (no chat, so `in_effect` is always Kel's here). */
  kel_model?: KelModelView | null;
}

export interface StaffRoleChoice {
  mode: StaffMode;
  model?: string | null;
  reasoning?: string;
}

const normalise = (payload: unknown): StaffListing => {
  const data = (payload && typeof payload === 'object' ? payload : {}) as Partial<StaffListing>;
  return {
    roles: Array.isArray(data.roles) ? data.roles : [],
    models: Array.isArray(data.models) ? data.models : [],
    modes: Array.isArray(data.modes) ? data.modes : undefined,
    kel_model: data.kel_model && typeof data.kel_model === 'object' ? data.kel_model : null,
  };
};

export const kelStaffRoles = async (): Promise<StaffListing> =>
  normalise(await kelRequest<unknown>('/api/model', { action: 'roles' }));

/** FN-06: Kel's model and whether this chat (the engine's conversation id) uses its own instead. */
export const kelModelInEffect = async (conversation: string): Promise<KelModelView | null> => {
  const payload = (await kelRequest<unknown>('/api/model', { action: 'get', conversation })) as { kel_model?: KelModelView | null } | null;
  return payload?.kel_model && typeof payload.kel_model === 'object' ? payload.kel_model : null;
};

/**
 * D-73.3 — one "Kel's model". The Kel row here IS Kel's model: Settings → Model, the Kel row in Staff &
 * models and the composer's "Kel's model" tab all read and write it. The older default-model setting
 * (`/api/model set_default`, which the engine still ranks first) is cleared whenever Kel's model is
 * written, so it cannot quietly override the one value; a chat's own pick stays a per-chat override.
 */
export const KELS_MODEL_ROLE = 'kel';
export const KELS_MODEL_CHANGED_EVENT = 'kel:kels-model-changed';

const settleKelsModel = async (role: string): Promise<void> => {
  if (role !== KELS_MODEL_ROLE) return;
  try {
    await kelRequest<unknown>('/api/model', { action: 'set_default', choice: null });
  } catch {
    // The Kel row saved; an engine without the older setting has nothing to clear.
  }
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(KELS_MODEL_CHANGED_EVENT));
};

export const kelStaffSetRole = async (role: string, choice: StaffRoleChoice): Promise<StaffListing> => {
  const listing = normalise(
    await kelRequest<unknown>('/api/model', {
      action: 'set_role',
      role,
      mode: choice.mode,
      ...(choice.mode === 'AUTOMATIC' ? {} : { model: choice.model ?? null }),
      reasoning: choice.reasoning || 'auto',
    })
  );
  await settleKelsModel(role);
  return listing;
};

export const kelStaffResetRole = async (role: string): Promise<StaffListing> => {
  const listing = normalise(await kelRequest<unknown>('/api/model', { action: 'reset_role', role }));
  await settleKelsModel(role);
  return listing;
};

/** Settings order (D-70): the order work flows through the team, Kel first, small jobs last. */
export const STAFF_ORDER = [
  'kel',
  'discovery',
  'architect',
  'designer',
  'builder',
  'verifier',
  'sentinel',
  'release',
  'oracle',
  'utility',
] as const;

/** What each role does, in one plain line (D-66: Kel alone manages the staff). */
export const STAFF_DESCRIPTIONS: Record<string, string> = {
  kel: 'Talks with you, plans the work and hands it to the staff.',
  discovery: 'Researches first: reads sources and gathers the facts.',
  architect: 'Works out how a larger change fits together.',
  designer: 'Shapes how things look and read.',
  builder: 'Does the work: writes the code or the document.',
  verifier: "Checks the Builder's result before you see it.",
  sentinel: 'Looks for security and safety problems.',
  release: 'Gets finished work ready to ship.',
  oracle: 'Gives an independent second opinion on big or risky changes.',
  utility: 'Handles small side jobs, like titles and short summaries.',
};

export const MODE_LABELS: Record<StaffMode, string> = {
  AUTOMATIC: 'Automatic',
  PREFERRED: 'Preferred',
  FIXED: 'Fixed',
};

/** What each mode means, for the mode control's hint. */
export const MODE_HINTS: Record<StaffMode, string> = {
  AUTOMATIC: 'Kel chooses by health, capability and cost.',
  PREFERRED: 'This model when it can run here; otherwise Kel falls back and says so.',
  FIXED: 'Only this model. If it cannot run, the work waits and Kel says why.',
};

export const REASONING_LABELS: Record<string, string> = {
  auto: 'Auto',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  xhigh: 'Extra high',
  max: 'Max',
  ultra: 'Ultra',
};

export const reasoningLabel = (level: string | null | undefined): string =>
  (level && REASONING_LABELS[level]) || 'Auto';

export const orderRoles = (rows: StaffRoleRow[]): StaffRoleRow[] => {
  const rank = (role: string) => {
    const index = (STAFF_ORDER as readonly string[]).indexOf(role);
    return index === -1 ? STAFF_ORDER.length : index;
  };
  return rows.toSorted((a, b) => rank(a.role) - rank(b.role));
};

/* ─── When Kel asks scoping questions first (D-70 item 4's one threshold setting) ──────────── */

export interface ScopingThresholdOption {
  id: string;
  label: string;
  hint?: string | null;
}

export interface ScopingThresholdView {
  threshold: string;
  default?: string;
  options: ScopingThresholdOption[];
}

const normaliseThreshold = (payload: unknown): ScopingThresholdView => {
  const data = (payload && typeof payload === 'object' ? payload : {}) as Partial<ScopingThresholdView>;
  return {
    threshold: typeof data.threshold === 'string' ? data.threshold : 'D2',
    default: typeof data.default === 'string' ? data.default : undefined,
    options: Array.isArray(data.options) ? data.options.filter((option) => option && typeof option.id === 'string') : [],
  };
};

export const kelScopingThreshold = async (): Promise<ScopingThresholdView> =>
  normaliseThreshold(await kelRequest<unknown>('/api/scoping', { action: 'threshold' }));

export const kelSetScopingThreshold = async (value: string): Promise<ScopingThresholdView> =>
  normaliseThreshold(await kelRequest<unknown>('/api/scoping', { action: 'set_threshold', value }));

/* ─── How Kel picks models: the read-only per-task-class ranking (Routing 2 §5.8) ────────────── */

export interface RankingModel {
  id: string;
  label: string;
  rank: number;
  runnable: boolean;
  protected?: boolean;
  why?: string | null;
}

export interface RankingClass {
  task_class: string;
  label: string;
  role: string;
  role_label: string;
  mode: StaffMode;
  mode_label?: string | null;
  tier: string;
  tier_label?: string | null;
  models: RankingModel[];
}

export interface RankingView {
  classes: RankingClass[];
  calibration_note?: string | null;
}

export const kelStaffRanking = async (): Promise<RankingView> => {
  const payload = (await kelRequest<unknown>('/api/model', { action: 'ranking' })) as Partial<RankingView> | null;
  const classes = Array.isArray(payload?.classes)
    ? payload!.classes.filter((entry) => entry && typeof entry.task_class === 'string' && Array.isArray(entry.models))
    : [];
  return { classes, calibration_note: payload?.calibration_note ?? null };
};

/** How much model each kind of work gets, in plain words (the engine's dispatch tiers). */
export const TIER_WORDS: Record<string, string> = {
  fast: 'Quick',
  standard: 'Standard',
  deep: 'Thorough',
  assurance: 'Most careful',
};
