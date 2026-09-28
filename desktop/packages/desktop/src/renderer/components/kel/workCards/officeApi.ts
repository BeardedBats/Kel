/**
 * D-66 / D-68 — the live Office state the work cards read.
 *
 * The contract is docs/v2/design/D-66_WORKFORCE_LIVE.md §4 (`GET /api/office`, `GET /api/office/item`)
 * plus the dismiss action for finished items (`POST /api/office {action:'dismiss', id}`). The engine
 * side and the typed functions in kelApi.ts are owned by the workforce increment; until they land this
 * module is a thin adapter over `kelRequest` with the same routes and shapes as kelApi.ts's
 * `kelOffice` / `kelOfficeItem` / `kelOfficeDismiss` (swap to those once they are committed). Every field the engine may
 * leave out is optional here, so a partial payload renders what it has and invents nothing.
 */
import { kelRequest, type KelChangeApplication, type KelUsage } from '../kelApi';

/** D-70: `scoping` — Kel is asking its "before I start" questions; nothing has started yet. */
export type OfficeState = 'scoping' | 'working' | 'in_review' | 'needs_you' | 'done' | 'stopped' | 'failed';
export type OfficeKind = 'code' | 'writing' | 'research' | 'recipe';
export type OfficeStaffState = 'working' | 'done' | 'failed' | 'stopped' | 'waiting';

export interface OfficeProgress {
  done: number;
  total: number;
  /** The phase in words ("2 of 3 steps done", "Checking the result") — never a percentage. */
  label?: string | null;
}

/** A short team entry some list payloads carry so a card can show initials without a detail read. */
export interface OfficeTeamChip {
  role: string;
  role_label?: string | null;
  state?: OfficeStaffState | null;
}

export interface OfficeItem {
  job_id: string;
  title: string;
  project_id?: string | null;
  conversation_id?: string | null;
  submission_id?: string | null;
  kind?: OfficeKind | string | null;
  state: OfficeState;
  status_line?: string | null;
  needs_you?: boolean;
  progress?: OfficeProgress | null;
  team_size?: number | null;
  team?: OfficeTeamChip[] | null;
  started_at?: number | null;
  updated_at?: number | null;
  finished_at?: number | null;
  finished?: boolean;
  /** An explicit position from the engine; when present the row follows it. */
  order?: number | null;
  /** D-70 scoping cards: how many questions Kel is asking, and the scoping record. */
  questions?: number | null;
  scoping_id?: string | null;
  message_seq?: number | null;
  /**
   * LIVE-10: the checks' outcome on finished work ('verified' | 'failed' | 'uncertain'), so a card can
   * say "Couldn't fully check" instead of "Failed". Optional until the engine sends it.
   */
  verdict?: string | null;
  /** VIS-6: the work is paused (the engine's PAUSED / PAUSING), so its open step shows "Paused". */
  paused?: boolean | null;
  /** LIVE-12: set once Nick undid an applied change — when, and how many files and folders it put back. */
  undone?: OfficeUndone | null;
  /** Coding work: where its checked change stands (APPLIED / UNDONE / waiting…), without a detail read. */
  application?: OfficeApplicationState | null;
}

export interface OfficeUndone {
  at?: number | null;
  files?: number | null;
  folders?: number | null;
}

export interface OfficeApplicationState {
  state?: string | null;
  decision?: string | null;
  waiting_reason?: string | null;
}

export interface OfficeList {
  generated?: number;
  project?: string;
  items: OfficeItem[];
}

export interface OfficeAsked {
  model_label?: string | null;
  reasoning?: string | null;
}

export interface OfficeStaff {
  id: string;
  role: string;
  role_label?: string | null;
  /** Parallel code streams: 'Part 2 of 3: …' or 'Combining the parts'; null for one-step work. */
  step_label?: string | null;
  doing?: string | null;
  state?: OfficeStaffState | null;
  model?: string | null;
  model_label?: string | null;
  version?: string | null;
  model_confirmed?: boolean | null;
  provider?: string | null;
  runtime?: string | null;
  runtime_version?: string | null;
  reasoning?: string | null;
  asked?: OfficeAsked | null;
  /** Why what ran differs from what was asked, in plain words. */
  note?: string | null;
  independence?: 'different' | 'reduced' | string | null;
  /** The engine's own words for how independent this member's check is (LIVE-10). */
  independence_label?: string | null;
  started_at?: number | null;
  finished_at?: number | null;
  /** LIVE-10: Kel's row — no planning model answered because Kel used its standard plan. */
  standard_plan?: boolean | null;
}

export interface OfficeStep {
  id: string;
  label: string;
  state?: string | null;
  at?: number | null;
  attempts?: number | null;
  /** LIVE-3: a restart or a lost worker stopped this step part-way; Kel won't repeat it on its own. */
  interrupted?: boolean | null;
}

export interface OfficeFinding {
  severity?: 'blocker' | 'critical' | 'note' | string | null;
  area?: string | null;
  summary?: string | null;
  where?: string | null;
  status?: 'open' | 'resolved' | string | null;
}

export interface OfficeReview {
  verdict?: string | null;
  checked_by?: string | null;
  independence?: string | null;
  /** The engine's own words for how independent the check was (LIVE-10). */
  independence_label?: string | null;
  findings?: OfficeFinding[] | null;
}

export interface OfficeOracle {
  state?: 'not_needed' | 'waiting' | 'running' | 'done' | 'could_not_run' | string | null;
  why?: string | null;
  independence?: string | null;
  model_label?: string | null;
  reasoning?: string | null;
  findings?: OfficeFinding[] | null;
  /** LIVE-10: what the second opinion concluded, in one plain sentence (null while it runs). */
  conclusion?: string | null;
  /** What the second opinion looked at, and what it could not, in its own words. */
  coverage?: string | null;
  /** The engine's own words for how independent the second opinion was. */
  independence_label?: string | null;
}

export interface OfficeVerification {
  result?: string | null;
  summary?: string[] | null;
}

export interface OfficeItemDetail extends Omit<OfficeItem, 'team'> {
  why?: string | null;
  next?: string | null;
  /** The finished result in plain words, when the engine reports one. */
  result?: string | null;
  staff?: OfficeStaff[] | null;
  steps?: OfficeStep[] | null;
  review?: OfficeReview | null;
  oracle?: OfficeOracle | null;
  /** bc873da: Sentinel's security / data-safety review and the Red Team's attack, in the Oracle's shape. */
  sentinel?: OfficeOracle | null;
  red_team?: OfficeOracle | null;
  files_changed?: string[] | null;
  verification?: OfficeVerification | null;
  /** D-65, coding work: where the checked change stands in the project folder. */
  application?: KelChangeApplication | null;
  links?: { conversation_id?: string | null; submission_id?: string | null; message_seq?: number | null } | null;
  /** D-70: the question a needs-you card asks, when the work is waiting on Nick. */
  question?: OfficeQuestion | null;
  /** D-72: the work's totals (tokens, time, approximate cost) for the detail header. */
  usage?: KelUsage | null;
  /** Routing 2 §5.4: the work's budget, whether it stopped on it, and whether Nick can raise it. */
  budget?: OfficeBudget | null;
}

export interface OfficeBudgetCeilings {
  tokens?: number | null;
  minutes?: number | null;
  cost?: number | null;
}

export interface OfficeBudget {
  class: string;
  ceilings?: OfficeBudgetCeilings | null;
  used?: { tokens?: number | null; ms?: number | null; cost?: number | null } | null;
  held?: { tokens?: number | null; ms?: number | null; cost?: number | null } | null;
  stopped?: boolean;
  can_raise?: boolean;
  next?: string | null;
  next_ceilings?: OfficeBudgetCeilings | null;
}

export interface OfficeRaised {
  job_id: string;
  from: string;
  to: string;
  ceilings?: OfficeBudgetCeilings | null;
}

/**
 * What kind of wait a needs-you card is (D-70), which decides where its answer goes. LIVE-3:
 * `no_model` (no model here can run it) and `out_of_tries` (it ran out of tries) answer "Try again"
 * like `interrupted`.
 */
export type OfficeWaitKind =
  | 'approval'
  | 'apply'
  | 'second_opinion'
  | 'paused'
  | 'interrupted'
  | 'no_model'
  | 'out_of_tries'
  | 'blocked'
  | 'clarification';

export interface OfficeQuestionOption {
  id: string;
  label: string;
  /**
   * LIVE-3: an option that is not an answer but a place to go (`open_settings`, with `target`
   * 'staff' for Settings → Staff & models). Nothing is sent to Kel for it.
   */
  action?: 'open_settings' | string | null;
  target?: string | null;
}

export interface OfficeQuestion {
  kind: OfficeWaitKind | string;
  /** The kind of wait in words ("Waiting for your OK"). */
  wait?: string | null;
  text: string;
  detail?: string | null;
  options?: OfficeQuestionOption[] | null;
  answer_box?: boolean;
  conversation_id?: string | null;
  job_id?: string | null;
  ref?: { approval_kind?: string | null; approval_id?: string | null; job?: string | null } | null;
  /** bc873da: which independent pass raised a second-opinion wait (its words are already in `text`). */
  source?: 'sentinel' | 'oracle' | 'red_team' | string | null;
}

const asList = (payload: unknown): OfficeList => {
  const body = (payload ?? {}) as Partial<OfficeList>;
  const items = Array.isArray(body.items) ? body.items.filter((item) => item && typeof item.job_id === 'string') : [];
  return { ...body, items };
};

/** Office items for one project, or every project with `'*'`. */
export const officeList = (project: string): Promise<OfficeList> =>
  kelRequest<unknown>(`/api/office?project=${encodeURIComponent(project || '*')}`).then(asList);

/** One chat's own work cards (the engine's conversation id), whatever project each landed in. */
export const officeListForChat = (conversation: string): Promise<OfficeList> =>
  kelRequest<unknown>(`/api/office?conversation=${encodeURIComponent(conversation)}`).then(asList);

/** The detail of one piece of work (team, steps, review, Oracle, files, verification). */
export const officeItem = (job: string): Promise<OfficeItemDetail> =>
  kelRequest<OfficeItemDetail>(`/api/office/item?job=${encodeURIComponent(job)}`);

export interface OfficeDismissed {
  dismissed?: boolean;
  already?: boolean;
  job_id?: string;
  /** D-74.3: the id was an open scoping card's, so "Not now" cancelled its questions. */
  scoping?: boolean;
}

/**
 * Remove a finished card; finished work stays at the top until Nick does this (D-68). With a scoping
 * card's `scoping_id` it is "Not now" (D-74.3): the questions are cancelled and nothing starts.
 */
export const officeDismiss = (id: string): Promise<OfficeDismissed> =>
  kelRequest<OfficeDismissed>('/api/office', { action: 'dismiss', id });

/** Move a budget-stopped job one budget size up so it continues (Nick's own act; Routing 2 §5.4). */
export const officeRaiseBudget = (id: string): Promise<OfficeRaised> =>
  kelRequest<OfficeRaised>('/api/office', { action: 'raise_budget', id });

/* ─── D-70: answering a needs-you card, and scoping ─────────────────────────────────────── */

/** The in-chat approval's own approve/deny route (the same one its card in the thread uses). */
export const answerApproval = (kind: string, id: string, allow: boolean, conversation?: string | null) =>
  kelRequest<unknown>('/api/approvals', { action: 'resolve', kind, id, allow, ...(conversation ? { conversation } : {}) });

/** "Apply anyway" / "Leave it" on the existing apply route, with Nick as the actor. */
export const answerApply = (job: string, choice: 'apply_anyway' | 'leave') =>
  kelRequest<unknown>('/api/apply', { job, action: choice });

/** Resume paused work (the existing control). */
export const answerResume = (job: string) => kelRequest<unknown>('/api/control', { job, action: 'resume' });

/** A normal message to Kel in the work's own conversation (the D-55 restart rule applies to it). */
export const answerMessage = (conversation: string, text: string, job?: string) =>
  kelRequest<{ id: string }>('/api/send', { conversation, text, ...(job ? { job_id: job } : {}) });

export interface ScopingAnswer {
  option?: string;
  text?: string;
}

export interface ScopingQuestion {
  id: string;
  question: string;
  options: Array<{ code: string; label: string }>;
  best?: string | null;
}

export interface ScopingView {
  id: string;
  title: string;
  /** `dismissed`: Nick chose "Not now" (D-74.3) — nothing started. */
  state: 'open' | 'started' | 'best_guess' | 'dismissed';
  conversation_id: string;
  project_id?: string | null;
  questions: ScopingQuestion[];
  summary: string;
  why?: string | null;
  created?: number | null;
  started_at?: number | null;
  started_submission?: string | null;
  answer_line?: string | null;
  submission_id?: string;
  already?: boolean;
  dismissed?: boolean;
  /** Answers recorded while the card is open — typed in the chat, understood by Kel — by question id. */
  recorded?: Record<string, ScopingRecorded> | null;
}

export interface ScopingRecorded {
  /** The option's code when the answer is one of the quick picks. */
  option?: string | null;
  /** What was typed when it is not one of them ("Something else…"). */
  text?: string | null;
  label?: string | null;
}

export const scopingView = (id: string, conversation?: string | null) =>
  kelRequest<ScopingView>(
    `/api/scoping?id=${encodeURIComponent(id)}${conversation ? `&conversation=${encodeURIComponent(conversation)}` : ''}`
  );

/** Start the scoped work with these answers (Nothing starts until Nick chooses, D-55). */
export const scopingStart = (id: string, answers: Record<string, ScopingAnswer>, conversation?: string | null) =>
  kelRequest<ScopingView>('/api/scoping', { action: 'start', id, answers, ...(conversation ? { conversation } : {}) });

/** "Just start with your best guess": starts at once; Kel's assumptions are recorded. */
export const scopingBestGuess = (id: string, conversation?: string | null) =>
  kelRequest<ScopingView>('/api/scoping', { action: 'best_guess', id, ...(conversation ? { conversation } : {}) });

/** D-74.3 "Not now": cancel an open scoping card. Nothing is started; Kel says so in the chat. */
export const scopingDismiss = (id: string, conversation?: string | null) =>
  kelRequest<ScopingView>('/api/scoping', { action: 'not_now', id, ...(conversation ? { conversation } : {}) });
