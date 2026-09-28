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

export type OfficeState = 'working' | 'in_review' | 'needs_you' | 'done' | 'stopped' | 'failed';
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
