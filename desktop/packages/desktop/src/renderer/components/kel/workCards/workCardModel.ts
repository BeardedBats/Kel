/**
 * D-68 — the plain rules behind the work-card row: words per state, order, how many cards fit,
 * what each staff member is shown as, and the model-honesty line (D-66: never show a model that
 * did not run as if it did). React-free so the rules are tested on their own.
 */
import type {
  OfficeItem,
  OfficeItemDetail,
  OfficeOracle,
  OfficeStaff,
  OfficeStaffState,
  OfficeState,
  OfficeTeamChip,
} from './officeApi';

/** Figma 4a: every card is 198 wide, 8 apart; the overflow control is at least 88 wide. */
export const CARD_WIDTH = 198;
export const CARD_GAP = 8;
export const OVERFLOW_MIN_WIDTH = 88;
/** The overflow control's padding (10 left, 8 right) around its row of 16px dots, 2 apart. */
const OVERFLOW_PADDING = 18;
const DOT = 16;
const DOT_GAP = 2;
/** More dots than this would crowd the row; the "+N more" count still says how many are hidden. */
export const OVERFLOW_MAX_DOTS = 8;

export const POLL_ACTIVE_MS = 4000;
export const POLL_IDLE_MS = 30000;

export const RUNNING_STATES: OfficeState[] = ['working', 'in_review', 'needs_you'];
export const FINISHED_STATES: OfficeState[] = ['done', 'failed', 'stopped'];

export const isRunning = (state: OfficeState | string | undefined | null): boolean =>
  RUNNING_STATES.includes(state as OfficeState);
export const isFinished = (state: OfficeState | string | undefined | null): boolean =>
  FINISHED_STATES.includes(state as OfficeState);

/** The short label a card shows beside its state icon. Colour is never the only signal. */
export const STATE_LABEL: Record<OfficeState, string> = {
  scoping: 'Scoping',
  working: 'Working',
  in_review: 'In review',
  needs_you: 'Needs you',
  done: 'Done',
  failed: 'Failed',
  stopped: 'Stopped',
};

export const stateLabel = (state: OfficeState | string): string => STATE_LABEL[state as OfficeState] ?? 'Working';

/** The detail header's state: only work whose checks passed may say "checked" (D-53). */
export const detailStateLabel = (item: Pick<OfficeItemDetail, 'state' | 'verification' | 'review'>): string => {
  if (item.state === 'done' && passed(item)) return 'Done and checked';
  return stateLabel(item.state);
};

const PASS_WORDS = new Set(['passed', 'pass', 'verified', 'ok', 'success']);
const FAIL_WORDS = new Set(['failed', 'fail', 'did_not_pass']);

const word = (value: string | null | undefined): string => (value ?? '').trim().toLowerCase();

/** Did the engine report this work's checks as passed? */
export const passed = (item: Pick<OfficeItemDetail, 'verification' | 'review'>): boolean =>
  PASS_WORDS.has(word(item.verification?.result)) || word(item.review?.verdict) === 'verified';

export const failedChecks = (item: Pick<OfficeItemDetail, 'verification' | 'review'>): boolean =>
  FAIL_WORDS.has(word(item.verification?.result)) || word(item.review?.verdict) === 'failed';

/** D-70: a scoping card counts Kel's questions instead of steps ("3 questions"). */
export const questionCount = (item: Pick<OfficeItem, 'questions'>): string | null => {
  const count = item.questions;
  if (!count || !(count > 0)) return null;
  return `${count} question${count === 1 ? '' : 's'}`;
};

/** Open work shows the row as live (poll fast): running, needs-you, or still being scoped. */
export const isLive = (state: OfficeState | string | undefined | null): boolean => isRunning(state) || state === 'scoping';

/** "X of Y" only when the engine counts real steps; nothing is invented when it does not. */
export const stepCount = (item: Pick<OfficeItem, 'progress'>): string | null => {
  const progress = item.progress;
  if (!progress || !(progress.total > 0)) return null;
  return `${Math.min(progress.done, progress.total)} of ${progress.total}`;
};

/** The bar's fill as a fraction of the real step count (0 when there is no count). */
export const progressFraction = (item: Pick<OfficeItem, 'progress'>): number => {
  const progress = item.progress;
  if (!progress || !(progress.total > 0)) return 0;
  return Math.max(0, Math.min(1, progress.done / progress.total));
};

/**
 * Running and needs-you work first, finished work last; the engine's own order is kept inside each
 * group. When the engine gives every item an explicit `order`, that order wins outright.
 */
export const orderItems = (items: OfficeItem[]): OfficeItem[] => {
  if (items.length && items.every((item) => typeof item.order === 'number')) {
    return [...items].sort((a, b) => (a.order as number) - (b.order as number));
  }
  const live = items.filter((item) => !isFinished(item.state));
  const done = items.filter((item) => isFinished(item.state));
  return [...live, ...done];
};

/** The overflow control's width for a number of hidden cards (one 16px dot each, capped). */
export const overflowWidth = (hidden: number): number => {
  const dots = Math.min(Math.max(hidden, 0), OVERFLOW_MAX_DOTS);
  const needed = OVERFLOW_PADDING + dots * DOT + Math.max(dots - 1, 0) * DOT_GAP;
  return Math.max(OVERFLOW_MIN_WIDTH, needed);
};

/**
 * How many cards fit in `width` — all of them when they fit without an overflow control, otherwise
 * as many as fit beside a "+N more" control sized for the rest. Never negative.
 */
export const fitCards = (width: number, count: number): number => {
  if (count <= 0 || !(width > 0)) return 0;
  const span = (cards: number) => cards * CARD_WIDTH + Math.max(cards - 1, 0) * CARD_GAP;
  if (span(count) <= width) return count;
  for (let visible = count - 1; visible >= 0; visible -= 1) {
    const used = visible > 0 ? span(visible) + CARD_GAP : 0;
    if (used + overflowWidth(count - visible) <= width) return visible;
  }
  return 0;
};

/* ─── Staff ───────────────────────────────────────────────────────────────────────────────── */

const COMMANDER_ROLES = new Set(['kel', 'commander']);
const REVIEW_ROLES = new Set(['verifier', 'oracle']);

export const isCommander = (member: Pick<OfficeStaff, 'role'>): boolean => COMMANDER_ROLES.has(word(member.role));

const ROLE_NAMES: Record<string, string> = {
  kel: 'Kel',
  commander: 'Kel',
  builder: 'Builder',
  verifier: 'Verifier',
  oracle: 'Oracle',
  discovery: 'Discovery',
  designer: 'Designer',
  utility: 'Utility',
  architect: 'Architect',
  sentinel: 'Sentinel',
  release: 'Release',
};

/** The role name a person reads: Kel for the Commander, else the engine's label. */
export const roleName = (member: Pick<OfficeStaff, 'role' | 'role_label'>): string => {
  if (isCommander(member)) return 'Kel';
  const label = (member.role_label ?? '').trim();
  if (label) return label;
  const key = word(member.role);
  return ROLE_NAMES[key] ?? (key ? key.charAt(0).toUpperCase() + key.slice(1) : 'Staff');
};

/** Two letters for the small avatar ("Bu", "Ve", "Or"). */
export const initials = (member: Pick<OfficeStaff, 'role' | 'role_label'>): string => {
  const name = roleName(member).replace(/[^A-Za-z]/g, '');
  return name ? name.charAt(0).toUpperCase() + name.charAt(1).toLowerCase() : '?';
};

/** The ring colour of one avatar, as a state name the stylesheet maps to the Figma colours. */
export type RingTone = 'working' | 'review' | 'needs' | 'done' | 'failed' | 'quiet';

export const ringTone = (
  member: Pick<OfficeStaff, 'role' | 'state'>,
  itemState: OfficeState | string
): RingTone => {
  const state = word(member.state) as OfficeStaffState | '';
  if (state === 'done') return 'done';
  if (state === 'failed') return 'failed';
  if (state === 'stopped') return 'quiet';
  if (itemState === 'needs_you') return 'needs';
  if (REVIEW_ROLES.has(word(member.role))) return 'review';
  if (state === 'waiting') return 'quiet';
  return 'working';
};

/** The team members a card shows (not Kel himself), from a list chip or a detail read. */
export const cardTeam = (team: Array<OfficeTeamChip | OfficeStaff> | null | undefined): OfficeTeamChip[] =>
  (team ?? []).filter((member) => !isCommander(member)).map((member) => ({
    role: member.role,
    role_label: member.role_label ?? null,
    state: member.state ?? null,
  }));

const REASONING_WORDS: Record<string, string> = {
  auto: 'Auto',
  minimal: 'Minimal',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  xhigh: 'Extra high',
  max: 'Max',
  ultra: 'Ultra',
};

/** "high" → "High"; unknown words keep the engine's text with a capital first letter. */
export const reasoningLabel = (value: string | null | undefined): string | null => {
  const key = word(value);
  if (!key) return null;
  return REASONING_WORDS[key] ?? key.charAt(0).toUpperCase() + key.slice(1);
};

const join = (...parts: Array<string | null | undefined>) => parts.filter((part) => part && part.trim()).join(' · ');

/** The label with its version, unless the label already names that version. */
const withVersion = (label: string | null | undefined, version: string | null | undefined): string | null => {
  const base = (label ?? '').trim();
  const v = (version ?? '').trim();
  if (!base) return v || null;
  if (!v || base.toLowerCase().includes(v.toLowerCase())) return base;
  return `${base} ${v}`;
};

/**
 * The model line for one staff member, honest about what actually ran (D-66): the model the runtime
 * reported, with its reasoning level; "Asked for X · ran Y" when it differs from what Kel asked for;
 * "Asked for X · not confirmed yet" while the runtime has not reported the model.
 */
export const modelLine = (member: OfficeStaff): string => {
  const ran = withVersion(member.model_label ?? member.model, member.version);
  const reasoning = reasoningLabel(member.reasoning);
  const asked = (member.asked?.model_label ?? '').trim();
  if (member.model_confirmed === false || !ran) {
    const wanted = asked || ran;
    const askedReasoning = reasoningLabel(member.asked?.reasoning) ?? reasoning;
    return wanted ? join(`Asked for ${wanted}`, askedReasoning, 'not confirmed yet') : 'Model not reported yet';
  }
  if (asked && asked.toLowerCase() !== (member.model_label ?? '').trim().toLowerCase()) {
    return join(`Asked for ${asked}`, `ran ${ran}`, reasoning);
  }
  return join(ran, reasoning);
};

/** The Oracle's line under its name. */
export const oracleLine = (oracle: OfficeOracle | null | undefined): string => {
  const why = (oracle?.why ?? '').trim();
  switch (oracle?.state) {
    case 'not_needed':
      return why || 'Not asked for this work.';
    case 'waiting':
      return why || 'Second opinion before hand-over.';
    case 'running':
      return why || 'Giving a second opinion now.';
    case 'could_not_run':
      return why ? `Couldn’t run: ${why}` : 'Couldn’t run for this work.';
    case 'done': {
      const open = (oracle.findings ?? []).filter((finding) => finding.status !== 'resolved');
      if (why) return why;
      return open.length ? `${open.length} concern${open.length === 1 ? '' : 's'} raised.` : 'No concerns.';
    }
    default:
      return why || 'Not asked for this work.';
  }
};

/** "9:40 AM" in en-US (D-61). */
export const clockTime = (epoch: number | null | undefined): string | null => {
  if (!epoch || !Number.isFinite(epoch)) return null;
  const ms = epoch < 1e12 ? epoch * 1000 : epoch;
  return new Date(ms).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
};

/** "22 min", "1 hr 5 min"; null when it cannot be told. */
export const duration = (start: number | null | undefined, end: number | null | undefined): string | null => {
  if (!start || !end || end < start) return null;
  const seconds = (end < 1e12 ? end : end / 1000) - (start < 1e12 ? start : start / 1000);
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} hr ${rest} min` : `${hours} hr`;
};
