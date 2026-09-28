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
import { kelRequest, type KelChangeApplication } from '../kelApi';

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
  started_at?: number | null;
  finished_at?: number | null;
}

export interface OfficeStep {
  id: string;
  label: string;
  state?: string | null;
  at?: number | null;
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
  findings?: OfficeFinding[] | null;
}

export interface OfficeOracle {
  state?: 'not_needed' | 'waiting' | 'running' | 'done' | 'could_not_run' | string | null;
  why?: string | null;
  independence?: string | null;
  model_label?: string | null;
  reasoning?: string | null;
  findings?: OfficeFinding[] | null;
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
  files_changed?: string[] | null;
  verification?: OfficeVerification | null;
  /** D-65, coding work: where the checked change stands in the project folder. */
  application?: KelChangeApplication | null;
  links?: { conversation_id?: string | null; submission_id?: string | null; message_seq?: number | null } | null;
  /** D-70: the question a needs-you card asks, when the work is waiting on Nick. */
  question?: OfficeQuestion | null;
}

/** What kind of wait a needs-you card is (D-70), which decides where its answer goes. */
export type OfficeWaitKind = 'approval' | 'apply' | 'second_opinion' | 'paused' | 'interrupted' | 'blocked' | 'clarification';

export interface OfficeQuestionOption {
  id: string;
  label: string;
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
}

const asList = (payload: unknown): OfficeList => {
  const body = (payload ?? {}) as Partial<OfficeList>;
  const items = Array.isArray(body.items) ? body.items.filter((item) => item && typeof item.job_id === 'string') : [];
  return { ...body, items };
};

/** Office items for one project, or every project with `'*'`. */
export const officeList = (project: string): Promise<OfficeList> =>
  kelRequest<unknown>(`/api/office?project=${encodeURIComponent(project || '*')}`).then(asList);

/** The detail of one piece of work (team, steps, review, Oracle, files, verification). */
export const officeItem = (job: string): Promise<OfficeItemDetail> =>
  kelRequest<OfficeItemDetail>(`/api/office/item?job=${encodeURIComponent(job)}`);

/** Remove a finished card; finished work stays at the top until Nick does this (D-68). */
export const officeDismiss = (id: string): Promise<unknown> => kelRequest<unknown>('/api/office', { action: 'dismiss', id });

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
  state: 'open' | 'started' | 'best_guess';
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
