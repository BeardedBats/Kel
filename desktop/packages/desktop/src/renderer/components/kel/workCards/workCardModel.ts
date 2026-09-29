/**
 * D-68 — the plain rules behind the work-card row: words per state, order, how many cards fit,
 * what each staff member is shown as, and the model-honesty line (D-66: never show a model that
 * did not run as if it did). React-free so the rules are tested on their own.
 */
import type {
  OfficeFinding,
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

/** LIVE-10: finished work the list itself marks as unconfirmed (its `verdict`), not failed. */
export const cardUncertain = (item: Pick<OfficeItem, 'state'> & { verdict?: string | null }): boolean =>
  item.state === 'failed' && isUncertain(item);

/** LIVE-12: Nick undid this work's applied change (the list's `undone`, or its application's state). */
export const isUndone = (item: Pick<OfficeItem, 'undone'> & { application?: { state?: string | null } | null }): boolean =>
  Boolean(item.undone) || word(item.application?.state) === 'undone';

export const UNDONE_LABEL = 'Undone';

/**
 * The card's state words: "Couldn't fully check" instead of "Failed" when the checks were only
 * unconfirmed (the list's `verdict`), and "Undone" for checked work whose change Nick undid.
 */
export const cardStateLabel = (
  item: Pick<OfficeItem, 'state'> & { verdict?: string | null; undone?: OfficeItem['undone']; application?: { state?: string | null } | null }
): string => {
  if (cardUncertain(item)) return UNCERTAIN_LABEL;
  if (item.state === 'done' && isUndone(item)) return UNDONE_LABEL;
  return stateLabel(item.state);
};

/**
 * "Undone at 10:42 AM — 3 files are back as they were; 1 empty folder removed." from the engine's
 * record of the undo (LIVE-12). Null when the change was not undone.
 */
export const undoneLine = (
  item: Pick<OfficeItem, 'undone'> & { application?: { state?: string | null } | null }
): string | null => {
  if (!isUndone(item)) return null;
  const when = clockTime(item.undone?.at);
  const files = item.undone?.files;
  const folders = item.undone?.folders;
  const back =
    typeof files === 'number' && files > 0
      ? `${files === 1 ? 'the file is' : `${files} files are`} back as ${files === 1 ? 'it was' : 'they were'}`
      : 'the earlier files are back';
  const removed = typeof folders === 'number' && folders > 0 ? `; ${folders} empty folder${folders === 1 ? '' : 's'} removed` : '';
  return `Undone${when ? ` at ${when}` : ''} — ${back}${removed}.`;
};

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
const REVIEW_ROLES = new Set(['verifier', 'oracle', 'sentinel', 'red_team']);

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
  red_team: 'Red Team',
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
/** The independent passes after the checks, in the order the engine runs them (bc873da). */
export type ReviewPassKind = 'sentinel' | 'oracle' | 'red_team';
export const REVIEW_PASSES: ReadonlyArray<{ kind: ReviewPassKind; name: string }> = [
  { kind: 'sentinel', name: 'Sentinel' },
  { kind: 'oracle', name: 'Oracle' },
  { kind: 'red_team', name: 'Red Team' },
];
const PASS_WAITING: Record<ReviewPassKind, string> = {
  sentinel: 'Security and data-safety check before hand-over.',
  oracle: 'Second opinion before hand-over.',
  red_team: 'Will try to break the accepted result before hand-over.',
};
const PASS_RUNNING: Record<ReviewPassKind, string> = {
  sentinel: 'Checking it for security and data safety now.',
  oracle: 'Giving a second opinion now.',
  red_team: 'Trying to break the accepted result now.',
};

/**
 * Sentinel and the Red Team only show when they have something to say: a pass the engine did not
 * need and gave no reason for is left out (the Oracle always shows, as Figma 4b/4d draw it).
 */
export const showReviewPass = (kind: ReviewPassKind, pass: OfficeOracle | null | undefined): boolean => {
  if (kind === 'oracle') return true;
  if (!pass || !pass.state) return false;
  if (pass.state !== 'not_needed') return true;
  return Boolean((pass.why ?? '').trim() || (pass.conclusion ?? '').trim());
};

export const oracleLines = (
  oracle: OfficeOracle | null | undefined,
  kind: ReviewPassKind = 'oracle'
): { line: string; why: string | null } => {
  const why = (oracle?.why ?? '').trim();
  switch (oracle?.state) {
    case 'not_needed': {
      // A skipped pass says why in the engine's words ("An earlier review already stands.").
      const told = (oracle.conclusion ?? '').trim() || why;
      if (kind !== 'oracle' && told) return { line: `Not needed: ${lowerFirst(sentence(told))}`, why: null };
      return { line: 'Not asked for this work.', why: null };
    }
    case 'waiting':
      return { line: PASS_WAITING[kind], why: why ? `Asked because: ${why}` : null };
    case 'running':
      return { line: PASS_RUNNING[kind], why: why ? `Asked because: ${why}` : null };
    case 'could_not_run': {
      const told = (oracle.conclusion ?? '').trim();
      if (told) return { line: sentence(told), why: null };
      return { line: why ? `Couldn’t run: ${why}` : 'Couldn’t run for this work.', why: null };
    }
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

/** What the second opinion looked at (and could not), in its own words — only once it concluded. */
export const oracleCoverage = (oracle: OfficeOracle | null | undefined): string | null => {
  const coverage = (oracle?.coverage ?? '').trim();
  if (!coverage || oracle?.state !== 'done') return null;
  const text = lowerFirst(coverage);
  return `What it looked at: ${/[.!?…]$/.test(text) ? text : `${text}.`}`;
};

const lowerFirst = (text: string): string => {
  // Keep a leading proper name or acronym ("GPT-6", "Kel") as it is.
  if (/^[A-Z][A-Z0-9-]/.test(text) || /^Kel\b/.test(text)) return text;
  return text.charAt(0).toLowerCase() + text.slice(1);
};

/**
 * LIVE-10: how independent a check was, in plain words. The engine's own `independence_label` wins
 * ("Checked by a different model family from the one that did the work."); without it the engine's
 * word is read here: "full"/empty says nothing; "different" names the other model family;
 * "reduced"/"same" says the check is less independent.
 */
export const independenceWords = (
  value: string | null | undefined,
  who: 'check' | 'second_opinion' = 'check',
  label?: string | null
): string | null => {
  const told = (label ?? '').trim();
  if (told) return sentence(`${who === 'check' ? 'Checked by' : 'Given by'} ${lowerFirst(told)}`);
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

/* ─── D-79: the simplified detail panel ──────────────────────────────────────────────────── */

/** D-79: finished work whose checks passed reads "Complete" (the when is in its tooltip). */
export const COMPLETE_LABEL = 'Complete';

/** The panel's (and the done card's) status words: "Complete", else the plain short state words. */
export const panelStateLabel = (item: Pick<OfficeItemDetail, 'state' | 'verification' | 'review'> & { verdict?: string | null }): string => {
  const label = detailStateLabel(item);
  return label === 'Done and checked' ? COMPLETE_LABEL : label;
};

/** "09/29/26 09:31 AM" (MM/DD/YY hh:mm AM/PM) for the "Complete" tooltip. */
export const completedAt = (epoch: number | null | undefined): string | null => {
  if (!epoch || !Number.isFinite(epoch)) return null;
  const d = new Date(epoch < 1e12 ? epoch * 1000 : epoch);
  const two = (n: number) => String(n).padStart(2, '0');
  const hours = d.getHours() % 12 || 12;
  return `${two(d.getMonth() + 1)}/${two(d.getDate())}/${two(d.getFullYear() % 100)} ${two(hours)}:${two(d.getMinutes())} ${d.getHours() < 12 ? 'AM' : 'PM'}`;
};

/** "Team · 4 agents". */
export const teamHeading = (staff: unknown[]): string => `Team · ${staff.length} agent${staff.length === 1 ? '' : 's'}`;

/** The role's colour key (every instance of a role shares it; unknown roles use the neutral one). */
export const ROLE_COLOR_KEYS = ['kel', 'builder', 'verifier', 'oracle', 'sentinel', 'red-team', 'designer', 'discovery', 'architect', 'release', 'utility'] as const;
export type RoleColorKey = (typeof ROLE_COLOR_KEYS)[number] | 'other';

export const roleColorKey = (member: Pick<OfficeStaff, 'role'>): RoleColorKey => {
  if (isCommander(member)) return 'kel';
  const key = word(member.role).replace(/[\s_]+/g, '-');
  return (ROLE_COLOR_KEYS as readonly string[]).includes(key) ? (key as RoleColorKey) : 'other';
};

/** What the agent did (its hover tooltip); the fallback note rides along. */
export const memberTooltip = (member: Pick<OfficeStaff, 'doing' | 'note'> & { plan?: string | null }): string | undefined => {
  const parts = [member.doing, member.note && !usedStandardPlan(member as OfficeStaff) ? member.note : null]
    .map((part) => (part ?? '').trim())
    .filter(Boolean);
  return parts.length ? parts.join('\n') : undefined;
};

export type ReviewTeamState = 'Not started' | 'In progress' | 'Failed' | 'Passed' | typeof UNCERTAIN_LABEL;

type ReviewView = Pick<OfficeItemDetail, 'state' | 'verification' | 'review' | 'staff'> & {
  verdict?: string | null;
  sentinel?: OfficeOracle | null;
  oracle?: OfficeOracle | null;
  red_team?: OfficeOracle | null;
};

const PASS_NAMES: Array<[keyof ReviewView, string]> = [
  ['review', 'Verifier'],
  ['sentinel', 'Sentinel'],
  ['oracle', 'Oracle'],
  ['red_team', 'Red Team'],
];

const openProblems = (view: ReviewView): Array<{ by: string; summary: string }> => {
  const out: Array<{ by: string; summary: string }> = [];
  for (const [key, by] of PASS_NAMES) {
    const findings = (view[key] as { findings?: OfficeFinding[] | null } | null | undefined)?.findings ?? [];
    for (const finding of findings) {
      if (finding.status === 'resolved' || finding.severity === 'note') continue;
      const summary = (finding.summary ?? '').trim();
      if (summary) out.push({ by, summary });
    }
  }
  return out;
};

/**
 * D-79 "Review Team": one status — Not started, In progress, Failed or Passed. (LIVE-10 keeps
 * "Couldn’t fully check" for work whose checks could not run: that is not a failure.)
 */
export const reviewTeamState = (view: ReviewView): ReviewTeamState => {
  if (passed(view)) return 'Passed';
  if (isFinished(view.state) && isUncertain(view)) return UNCERTAIN_LABEL;
  if (failedChecks(view) || (isFinished(view.state) && view.state === 'failed')) return 'Failed';
  const started =
    view.state === 'in_review' ||
    Boolean(view.verification?.result) ||
    Boolean(view.review?.verdict) ||
    openProblems(view).length > 0 ||
    PASS_NAMES.some(([key]) => key !== 'review' && ['running', 'done'].includes(String((view[key] as OfficeOracle | null | undefined)?.state ?? '')));
  return started ? 'In progress' : 'Not started';
};

const lowerLead = (text: string) => (/^[A-Z](?![A-Z0-9-])/.test(text) ? text.charAt(0).toLowerCase() + text.slice(1) : text);

/**
 * When there is a problem: what it is and who is on it, in one line — "Sentinel found a password
 * stored in plain text · Builder is fixing it". Null when nothing is open.
 */
export const reviewProblemLine = (view: ReviewView): string | null => {
  const problems = openProblems(view);
  if (!problems.length) return null;
  const first = problems[0];
  const what = `${first.by} found ${lowerLead(first.summary.replace(/[.!]+$/, ''))}`;
  const more = problems.length > 1 ? ` (+${problems.length - 1} more)` : '';
  const fixer = !isFinished(view.state)
    ? (view.staff ?? []).find((member) => word(member.role) === 'builder' && word(member.state) === 'working')
    : undefined;
  return fixer ? `${what}${more} · ${roleName(fixer)} is fixing it` : `${what}${more}`;
};
