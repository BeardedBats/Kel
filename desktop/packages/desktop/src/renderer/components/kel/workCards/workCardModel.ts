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

/** LIVE-10: work Kel could not fully check is not work that failed its checks. */
export const UNCERTAIN_LABEL = 'Couldn’t fully check';

const UNCERTAIN_WORDS = new Set(['not_confirmed', 'uncertain', 'unconfirmed', 'not_checked']);

/**
 * Finished work whose checks could not be confirmed (the engine's UNCERTAIN verdict). The detail says
 * so through `verification.result` ("not_confirmed") or the review verdict; a list item through its
 * optional `verdict`.
 */
export const isUncertain = (item: Partial<Pick<OfficeItemDetail, 'verification' | 'review'>> & { verdict?: string | null }): boolean =>
  UNCERTAIN_WORDS.has(word(item.verification?.result)) || word(item.review?.verdict) === 'uncertain' || word(item.verdict) === 'uncertain';

/** The card's state words: "Couldn't fully check" instead of "Failed" when the checks were only unconfirmed. */
export const cardStateLabel = (item: Pick<OfficeItem, 'state'> & { verdict?: string | null }): string =>
  item.state === 'failed' && isUncertain(item) ? UNCERTAIN_LABEL : stateLabel(item.state);

/** The detail header's state: only work whose checks passed may say "checked" (D-53). */
export const detailStateLabel = (item: Pick<OfficeItemDetail, 'state' | 'verification' | 'review'> & { verdict?: string | null }): string => {
  if (item.state === 'done' && passed(item)) return 'Done and checked';
  if (item.state === 'failed' && isUncertain(item)) return UNCERTAIN_LABEL;
  return stateLabel(item.state);
};

const PASS_WORDS = new Set(['passed', 'pass', 'verified', 'ok', 'success']);
const FAIL_WORDS = new Set(['failed', 'fail', 'did_not_pass']);

function word(value: string | null | undefined): string {
  return (value ?? '').trim().toLowerCase();
}

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
export const STANDARD_PLAN_LINE = 'Planned with Kel’s standard plan';

/**
 * LIVE-10: Kel's own row when no planning model answered because Kel used its standard plan for this
 * kind of work (the engine says so in the row's note, or with `plan: 'standard'`).
 */
export const usedStandardPlan = (member: OfficeStaff & { plan?: string | null }): boolean =>
  isCommander(member) &&
  !(member.model_label ?? member.model) &&
  (member.standard_plan === true || word(member.plan) === 'standard' || /standard\b.*\bplan/i.test(member.note ?? ''));

export const modelLine = (member: OfficeStaff): string => {
  if (usedStandardPlan(member)) return STANDARD_PLAN_LINE;
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

const sentence = (text: string): string => {
  const trimmed = text.trim();
  if (!trimmed) return trimmed;
  const capital = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  return /[.!?…]$/.test(capital) ? capital : `${capital}.`;
};

/**
 * The Oracle's lines under its name (LIVE-10): what it concluded first — "No problems found." or its
 * open findings — and why it was asked second. While it has not concluded, why it is being asked.
 */
export const oracleLines = (oracle: OfficeOracle | null | undefined): { line: string; why: string | null } => {
  const why = (oracle?.why ?? '').trim();
  switch (oracle?.state) {
    case 'not_needed':
      return { line: 'Not asked for this work.', why: null };
    case 'waiting':
      return { line: 'Second opinion before hand-over.', why: why ? `Asked because: ${why}` : null };
    case 'running':
      return { line: 'Giving a second opinion now.', why: why ? `Asked because: ${why}` : null };
    case 'could_not_run':
      return { line: why ? `Couldn’t run: ${why}` : 'Couldn’t run for this work.', why: null };
    case 'done': {
      // The engine's own sentence when it sends one; otherwise read from the findings.
      const told = (oracle.conclusion ?? '').trim();
      if (told) return { line: sentence(told), why: why ? `Asked because: ${why}` : null };
      const open = (oracle.findings ?? []).filter((finding) => finding.status !== 'resolved');
      const summaries = open.map((finding) => (finding.summary ?? '').trim()).filter(Boolean);
      const line = !open.length
        ? 'No problems found.'
        : summaries.length
          ? `${open.length === 1 ? 'Found' : `Found ${open.length} things`}: ${summaries.map((text) => sentence(text)).join(' ')}`
          : `Found ${open.length} thing${open.length === 1 ? '' : 's'} to look at.`;
      return { line, why: why ? `Asked because: ${why}` : null };
    }
    default:
      return { line: 'Not asked for this work.', why: null };
  }
};

/** One line for the Oracle (its conclusion, then why it was asked). */
export const oracleLine = (oracle: OfficeOracle | null | undefined): string => {
  const { line, why } = oracleLines(oracle);
  return why ? `${line} ${sentence(why)}` : line;
};

/**
 * LIVE-10: the engine's independence word in plain words. "full"/empty says nothing; "different" names
 * the other model family; "reduced"/"same" says the check is less independent.
 */
export const independenceWords = (value: string | null | undefined, who: 'check' | 'second_opinion' = 'check'): string | null => {
  const key = word(value);
  if (!key || key === 'full' || key === 'none') return null;
  if (key === 'different')
    return who === 'check' ? 'Checked by a different model family.' : 'Given by a different model family.';
  if (key === 'reduced' || key === 'same')
    return who === 'check'
      ? 'Less independent: checked by the same model family.'
      : 'Less independent: given by the same model family.';
  return null;
};

/* ─── Result and verification text ───────────────────────────────────────────────────────── */

/**
 * A raw model id in plain words when no label came with it: "claude-opus-5-5" → "Claude Opus 5.5",
 * "gpt-6-astra" → "GPT-6 Astra".
 */
export const prettyModelId = (raw: string | null | undefined): string | null => {
  const id = String(raw ?? '').trim().split('/').pop() ?? '';
  if (!id) return null;
  const parts = id.split(/[-_\s]+/).filter(Boolean);
  const out: string[] = [];
  for (let index = 0; index < parts.length; index += 1) {
    const part = parts[index];
    if (/^gpt$/i.test(part) && /^\d/.test(parts[index + 1] ?? '')) {
      out.push(`GPT-${parts[index + 1]}`);
      index += 1;
    } else if (/^\d+$/.test(part) && out.length && /\d$/.test(out[out.length - 1]) && !/^GPT-/.test(out[out.length - 1])) {
      out[out.length - 1] = `${out[out.length - 1]}.${part}`;
    } else if (/^\d/.test(part)) {
      out.push(part);
    } else {
      out.push(part.charAt(0).toUpperCase() + part.slice(1));
    }
  }
  return out.join(' ');
};

/** "Claude Code (claude-opus-5-5), Codex (gpt-6-astra)" → the model names, in plain words. */
const workerNames = (text: string): string[] =>
  text
    .split(/,\s*(?![^()]*\))/)
    .map((part) => {
      const inner = part.match(/\(([^)]+)\)/)?.[1];
      return (inner ? prettyModelId(inner) : part.trim()) ?? '';
    })
    .filter(Boolean);

const unique = (values: Array<string | null | undefined>): string[] =>
  values.filter((value): value is string => Boolean(value && value.trim())).filter((value, index, all) => all.indexOf(value) === index);

const VERDICT_LINE = /^(verified|passed|failed|uncertain|not confirmed|could not be confirmed)\.?$/i;

/**
 * VIS-4 / LIVE-10: the engine's verification summary as clean list lines — no verdict line (the
 * header already says it), no "• " bullets, and "Executed by / Reviewed by" as one plain
 * "Built by <model> · Checked by <model>" line (model names from the team when it reported them).
 */
export const verificationLines = (
  summary: string[] | null | undefined,
  staff: OfficeStaff[] | null | undefined = [],
  checkedBy?: string | null
): string[] => {
  const lines: string[] = [];
  let built: string[] = [];
  let checked: string[] = [];
  (summary ?? []).forEach((raw, index) => {
    const text = String(raw ?? '')
      .replace(/^\s*(?:[•·*-]|•)\s*/, '')
      .replace(/`([^`\n]+)`/g, '$1')
      .trim();
    if (!text) return;
    if (index === 0 && VERDICT_LINE.test(text)) return;
    const executed = text.match(/^executed by:\s*(.+)$/i);
    if (executed) {
      built = workerNames(executed[1]);
      return;
    }
    const reviewed = text.match(/^reviewed by:\s*(.+)$/i);
    if (reviewed) {
      checked = workerNames(reviewed[1]);
      return;
    }
    const tests = text.match(/^tests:\s*(.+)$/i);
    const line = tests ? `Tests ${tests[1]}` : text;
    lines.push((line.charAt(0).toUpperCase() + line.slice(1)).replace(/\.$/, ''));
  });
  const team = staff ?? [];
  const labelOf = (member: OfficeStaff) => (member.model_confirmed === false ? null : member.model_label ?? prettyModelId(member.model));
  const teamBuilt = unique(team.filter((member) => word(member.role) === 'builder').map(labelOf));
  const teamChecked = unique(team.filter((member) => word(member.role) === 'verifier').map(labelOf));
  if (built.length || checked.length) {
    const builders = teamBuilt.length ? teamBuilt : built;
    const checkers = teamChecked.length ? teamChecked : checked.length ? checked : unique([checkedBy]);
    const parts = [
      builders.length ? `Built by ${builders.join(', ')}` : null,
      checkers.length ? `Checked by ${checkers.join(', ')}` : null,
    ].filter(Boolean);
    if (parts.length) lines.push(parts.join(' · '));
  }
  return lines;
};

const APPLIED_LEAD = /^(?:Your new project is ready\.\s*)?Applied to [^\n]+?:\s+(?=(?:changed|added|removed|no files)\b)/i;
const UNDO_HINT = /\s*The earlier files are saved\s*[—-]\s*Undo on the result card puts them back\.?/gi;

/**
 * The finished result as plain text for the card (LIVE-10 / LIVE-12): no literal backticks around
 * commands; when the card already says where the change went (or that it was undone), no second
 * "Applied to <full path>:" lead and no Undo hint.
 */
export const plainResultText = (text: string | null | undefined, application?: { state?: string | null } | null): string => {
  let body = String(text ?? '').replace(/`([^`\n]+)`/g, '$1');
  if (application) {
    body = body
      .split(/\n/)
      .map((line) => {
        const match = line.match(APPLIED_LEAD);
        if (!match) return line;
        const rest = line.slice(match[0].length).trim();
        return rest ? rest.charAt(0).toUpperCase() + rest.slice(1) : '';
      })
      .join('\n')
      .replace(UNDO_HINT, '');
  }
  return body.replace(/\n{3,}/g, '\n\n').trim();
};

/**
 * The Team section's count (Figma 4b "Kel + 3", 4d "Kel + 3, all done"). Kel alone is "Kel"; "all
 * done" only for work that finished as done with every member done (never on stopped or failed work).
 */
export const teamMeta = (staff: Array<Pick<OfficeStaff, 'role' | 'state'>>, itemState: OfficeState | string): string | null => {
  if (!staff.length) return null;
  const helpers = staff.filter((member) => !isCommander(member)).length;
  const hasKel = staff.some(isCommander);
  const base = hasKel ? (helpers ? `Kel + ${helpers}` : 'Kel') : `${helpers}`;
  const allDone = itemState === 'done' && staff.every((member) => word(member.state) === 'done');
  return allDone && helpers ? `${base}, all done` : base;
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
