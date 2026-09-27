/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-57: move the donor scheduler's tasks into the engine, once, through the engine API.
 *
 * Order is the whole point. Each task is imported first (the engine keys it by its donor id, so a
 * repeat import answers with the schedule it already has and never replays a run) and the donor
 * task is switched off only after the engine confirms the import. A crash in between leaves the
 * donor task running and the next launch finishes the job; nothing is ever lost or doubled. The
 * donor rows are disabled, not deleted, for one release.
 *
 * A task the engine refuses as-is is imported again paused with the reason as its problem (and, if
 * even that is refused, as a manual task in General), so the person always finds it on the
 * Scheduled page instead of having it silently keep running in the old scheduler.
 *
 * Pure orchestration: the engine and donor calls are injected so the ordering is testable.
 */

/** The donor scheduler's task, as `GET /api/cron/jobs` returns it (only what is read here). */
export interface DonorCronJob {
  id: string;
  name?: string;
  enabled?: boolean;
  schedule?:
    | { kind: 'at'; atMs?: number }
    | { kind: 'every'; everyMs?: number }
    | { kind: 'cron'; expr?: string; tz?: string }
    | { kind?: string; [key: string]: unknown };
  target?: { payload?: { text?: string }; execution_mode?: 'existing' | 'new_conversation' };
  metadata?: {
    conversation_id?: string;
    agent_config?: {
      model_id?: string;
      model?: { provider_id?: string; model?: string; use_model?: string };
      workspace?: string;
    };
  };
  state?: { queue_enabled?: boolean };
}

type DonorConversation = { id: string; created_at?: number; modify_time?: number; updated_at?: number; extra?: { kel_conversation_id?: string } };

type Cadence =
  | { kind: 'manual' }
  | { kind: 'cron'; expr: string }
  | { kind: 'interval'; minutes: number }
  | { kind: 'once'; at: number };

export interface ScheduleImport {
  origin: string;
  name: string;
  project_id: string;
  target: { kind: 'instruction'; text: string };
  cadence: Cadence;
  timezone: string | null;
  start_mode: 'new_conversation' | 'existing';
  conversation_id: string | null;
  model: { provider: string; model: string | null } | null;
  skip_if_running: boolean;
  enabled: boolean;
  problem: string | null;
  /** Plain sentences about what changed in the move (shown with the imported event). */
  notes: string[];
  /** Up to 20 earlier runs, newest first, recorded as `schedule.imported_run` events. */
  runs: Array<{ conversation_id: string; at: number }>;
}

/** One line of the engine's import answer. */
export interface ImportResult {
  origin: string;
  id?: string | null;
  status?: 'imported' | 'imported_paused' | 'exists' | 'refused' | string;
  problem?: string | null;
  message?: string | null;
}

const confirmedId = (result: ImportResult | undefined): string | null =>
  result && result.status !== 'refused' && typeof result.id === 'string' && result.id ? result.id : null;

export interface ScheduleMigrationDeps {
  /** The engine API (main-process custody: may call `import`). Throws the engine's refusal. */
  engine: (route: string, body?: unknown) => Promise<unknown>;
  /** The donor backend. `method` defaults to GET without a body, POST with one. */
  donor: (route: string, body?: unknown, method?: string) => Promise<unknown>;
  /** The engine conversation a donor chat is mapped to, when it is. */
  engineConversationFor: (donorId: string) => string | undefined;
  /** Local "already done" marker, so a finished migration costs nothing on later launches. */
  isDone: () => boolean;
  markDone: (summary: ScheduleMigrationReport) => void;
  now?: () => number;
  log?: (line: string) => void;
}

export interface ScheduleMigrationReport {
  state: 'done' | 'skipped' | 'incomplete';
  reason?: string;
  imported: string[];
  paused: string[];
  disabled: string[];
  failed: Array<{ id: string; reason: string }>;
}

const MIN_MINUTES = 5;
const MAX_RUNS = 20;

const message = (error: unknown): string => String((error as Error)?.message || error || 'refused').trim();

/** The smallest gap between two firings of a 5-field cron minute/hour pattern, in minutes. */
export function cronMinimumGapMinutes(expr: string): number {
  const [minute = '', hour = ''] = expr.trim().split(/\s+/);
  const expand = (field: string, max: number): number[] | null => {
    const values = new Set<number>();
    for (const part of field.split(',')) {
      const [range, stepText] = part.split('/');
      const step = stepText ? Number(stepText) : 1;
      if (!Number.isInteger(step) || step < 1) return null;
      let start = 0;
      let end = max;
      if (range !== '*') {
        const [a, b] = range.split('-');
        start = Number(a);
        end = b === undefined ? (stepText ? max : start) : Number(b);
      }
      if (!Number.isInteger(start) || !Number.isInteger(end)) return null;
      for (let value = start; value <= end; value += step) values.add(value);
    }
    return [...values].sort((x, y) => x - y);
  };
  const minutes = expand(minute, 59);
  if (!minutes || minutes.length === 0) return Infinity;
  // One minute past the hour fires at most hourly.
  if (minutes.length === 1) return 60;
  const gaps = minutes.slice(1).map((value, index) => value - minutes[index]);
  // The wrap from the last minute of an hour to the first of the next counts only when every
  // hour fires; with chosen hours the next firing may be much later.
  if (hour === '*') gaps.push(60 - minutes[minutes.length - 1] + minutes[0]);
  return Math.min(...gaps);
}

function mapCadence(
  job: DonorCronJob,
  nowMs: number
): { cadence: Cadence; timezone?: string; paused?: boolean; problem?: string; note?: string } {
  const schedule = (job.schedule ?? {}) as { kind?: string; expr?: unknown; tz?: unknown; everyMs?: unknown; atMs?: unknown };
  if (schedule.kind === 'every') {
    const minutes = Math.max(1, Math.round(Number(schedule.everyMs) / 60000) || 0);
    if (minutes < MIN_MINUTES)
      return {
        cadence: { kind: 'interval', minutes: MIN_MINUTES },
        paused: true,
        problem: `It ran every ${minutes} minute${minutes === 1 ? '' : 's'} before the move. Kel runs a task at most every ${MIN_MINUTES} minutes, so it is paused until you pick a new time.`,
      };
    return { cadence: { kind: 'interval', minutes } };
  }
  if (schedule.kind === 'at') {
    const atMs = Number(schedule.atMs);
    if (!Number.isFinite(atMs)) return { cadence: { kind: 'manual' }, note: 'Its one-off time could not be read, so it runs only when you choose Run now.' };
    if (atMs <= nowMs)
      return { cadence: { kind: 'once', at: atMs / 1000 }, paused: true, note: 'Its one-off time had already passed, so it is paused.' };
    return { cadence: { kind: 'once', at: atMs / 1000 } };
  }
  const expr = typeof schedule.expr === 'string' ? schedule.expr.trim() : '';
  const tz = typeof schedule.tz === 'string' && schedule.tz.trim() ? schedule.tz.trim() : undefined;
  if (!expr) return { cadence: { kind: 'manual' }, timezone: tz };
  const gap = cronMinimumGapMinutes(expr);
  if (gap < MIN_MINUTES)
    return {
      cadence: { kind: 'cron', expr },
      timezone: tz,
      paused: true,
      problem: `It ran every ${gap} minute${gap === 1 ? '' : 's'} before the move. Kel runs a task at most every ${MIN_MINUTES} minutes, so it is paused until you pick a new time.`,
    };
  return { cadence: { kind: 'cron', expr }, timezone: tz };
}

type ModelOption = { id: string; label?: string; available?: boolean };
type ModelProvider = { id: string; label?: string; options?: ModelOption[] };

function resolveModel(
  job: DonorCronJob,
  providers: ModelProvider[]
): { model: ScheduleImport['model']; note?: string } {
  const config = job.metadata?.agent_config;
  const wanted = (config?.model_id || config?.model?.use_model || config?.model?.model || '').trim();
  if (!wanted) return { model: null };
  const ordered = config?.model?.provider_id
    ? [...providers].sort((a, b) => Number(b.id === config.model?.provider_id) - Number(a.id === config.model?.provider_id))
    : providers;
  for (const provider of ordered) {
    const option = (provider.options ?? []).find((entry) => entry.id === wanted || entry.label === wanted);
    if (option) return { model: { provider: provider.id, model: option.id } };
  }
  return { model: null, note: `Its model (${wanted}) is not one Kel can use, so it uses Automatic.` };
}

const asArray = <T,>(value: unknown, key?: string): T[] => {
  if (Array.isArray(value)) return value as T[];
  if (key && value && typeof value === 'object' && Array.isArray((value as Record<string, unknown>)[key]))
    return (value as Record<string, unknown>)[key] as T[];
  return [];
};

export async function migrateDonorSchedules(deps: ScheduleMigrationDeps): Promise<ScheduleMigrationReport> {
  const log = deps.log ?? (() => undefined);
  const now = deps.now ?? Date.now;
  const report: ScheduleMigrationReport = { state: 'incomplete', imported: [], paused: [], disabled: [], failed: [] };
  if (deps.isDone()) return { ...report, state: 'skipped', reason: 'already done' };

  // The engine must know schedules before anything moves; an older engine leaves the donor as is.
  let status: { done?: unknown } | null;
  try {
    status = (await deps.engine('/api/schedules', { action: 'migration_status' })) as { done?: unknown } | null;
  } catch (error) {
    return { ...report, state: 'skipped', reason: 'engine has no schedules yet: ' + message(error) };
  }
  if (status?.done === true) {
    deps.markDone({ ...report, state: 'done', reason: 'engine says done' });
    return { ...report, state: 'done', reason: 'engine says done' };
  }

  let jobs: DonorCronJob[];
  try {
    jobs = asArray<DonorCronJob>(await deps.donor('/api/cron/jobs'), 'items').filter((job) => job && typeof job.id === 'string');
  } catch (error) {
    return { ...report, state: 'skipped', reason: 'old scheduler not answering: ' + message(error) };
  }

  let providers: ModelProvider[] = [];
  if (jobs.length > 0) {
    try {
      providers = asArray<ModelProvider>(await deps.engine('/api/model', { action: 'get' }), 'providers');
    } catch (error) {
      // Without the model list a chosen model cannot be checked; try again next launch.
      return { ...report, state: 'skipped', reason: 'model list unavailable: ' + message(error) };
    }
  }
  const conversationProject = new Map<string, string>();
  try {
    for (const row of asArray<{ id?: string; project_id?: string }>(await deps.engine('/api/conversations'), 'conversations'))
      if (row?.id && row.project_id) conversationProject.set(row.id, row.project_id);
  } catch {
    // Unknown chat projects fall back to General below.
  }

  const items: ScheduleImport[] = [];
  for (const job of jobs) {
    const notes: string[] = [];
    const cadence = mapCadence(job, now());
    if (cadence.note) notes.push(cadence.note);

    const donorChat = job.metadata?.conversation_id || '';
    const chatCid = donorChat ? deps.engineConversationFor(donorChat) : undefined;
    let start_mode: ScheduleImport['start_mode'] = 'new_conversation';
    let conversation_id: string | null = null;
    if (job.target?.execution_mode === 'existing') {
      if (chatCid) {
        start_mode = 'existing';
        conversation_id = chatCid;
      } else {
        notes.push('Its chat could not be found, so each run now starts a new conversation.');
      }
    }

    let project_id = '';
    const workspace = job.metadata?.agent_config?.workspace?.trim();
    if (workspace) {
      try {
        const project = (await deps.engine('/api/project', { action: 'for_folder', root: workspace })) as { id?: unknown } | null;
        if (typeof project?.id === 'string') project_id = project.id;
      } catch {
        notes.push('Its folder is no longer available, so it belongs to its chat’s project.');
      }
    }
    if (!project_id && chatCid) project_id = conversationProject.get(chatCid) || '';
    if (!project_id) project_id = 'default';

    const { model, note: modelNote } = resolveModel(job, providers);
    if (modelNote) notes.push(modelNote);

    const runs: ScheduleImport['runs'] = [];
    try {
      const listed = asArray<DonorConversation>(await deps.donor(`/api/cron/jobs/${encodeURIComponent(job.id)}/conversations`), 'items');
      const when = (row: DonorConversation) => Number(row.modify_time ?? row.updated_at ?? row.created_at ?? 0);
      for (const row of listed.toSorted((a, b) => when(b) - when(a))) {
        const cid = deps.engineConversationFor(row.id) || row.extra?.kel_conversation_id;
        if (cid && !runs.some((run) => run.conversation_id === cid)) runs.push({ conversation_id: cid, at: when(row) / 1000 });
        if (runs.length >= MAX_RUNS) break;
      }
    } catch {
      // Earlier runs are a courtesy; the task itself still moves.
    }

    const text = job.target?.payload?.text?.trim() ?? '';
    let problem = cadence.problem ?? null;
    if (!text && !problem) problem = 'It had no instructions. Add them, then resume it.';
    const item: ScheduleImport = {
      origin: job.id,
      name: job.name?.trim() || 'Scheduled task',
      project_id,
      target: { kind: 'instruction', text },
      cadence: cadence.cadence,
      // A task without its own zone ran on this computer's clock; null keeps following it.
      timezone: cadence.timezone ?? null,
      start_mode,
      conversation_id,
      model,
      skip_if_running: Boolean(job.state?.queue_enabled),
      enabled: job.enabled !== false && !cadence.paused && !problem,
      problem,
      notes,
      runs,
    };

    items.push(item);
  }

  // 1) Import every task (idempotent by origin: a repeat answers `exists` and never replays). The
  //    engine imports an item that fails its checks paused, with the refusal as its problem; one it
  //    still refuses is sent again as a plain paused manual task in General.
  const outcome = new Map<string, ImportResult>();
  const importBatch = async (batch: ScheduleImport[]): Promise<boolean> => {
    if (batch.length === 0) return true;
    try {
      const answer = (await deps.engine('/api/schedules', { action: 'import', items: batch })) as { results?: unknown } | null;
      for (const result of asArray<ImportResult>(answer?.results)) if (result && typeof result.origin === 'string') outcome.set(result.origin, result);
      return true;
    } catch (error) {
      for (const item of batch) report.failed.push({ id: item.origin, reason: 'import not confirmed: ' + message(error) });
      return false;
    }
  };
  if (!(await importBatch(items))) {
    log('[KEL-SCHEDULES] import not confirmed; old tasks left as they were');
    return report;
  }
  const refused = items.filter((item) => outcome.get(item.origin)?.status === 'refused' || !confirmedId(outcome.get(item.origin)));
  const fallback = refused.map((item): ScheduleImport => {
    const reason = outcome.get(item.origin)?.message || outcome.get(item.origin)?.problem || 'Kel could not keep it exactly as it was';
    return {
      ...item,
      enabled: false,
      problem: `Kel could not keep it exactly as it was: ${String(reason).replace(/\.$/, '')}. Check it, then resume it.`,
      cadence: { kind: 'manual' },
      start_mode: 'new_conversation',
      conversation_id: null,
      model: null,
      project_id: 'default',
    };
  });
  if (fallback.length > 0 && !(await importBatch(fallback))) return report;

  // 2) Only now switch each confirmed donor task off.
  for (const item of items) {
    const result = outcome.get(item.origin);
    if (!confirmedId(result)) {
      report.failed.push({ id: item.origin, reason: result?.message || 'the engine did not confirm the import' });
      log(`[KEL-SCHEDULES] import refused for ${item.origin}; old task left as it was`);
      continue;
    }
    report.imported.push(item.origin);
    if (result!.status === 'imported_paused' || fallback.some((entry) => entry.origin === item.origin) || !item.enabled)
      report.paused.push(item.origin);
    try {
      await deps.donor(`/api/cron/jobs/${encodeURIComponent(item.origin)}`, { enabled: false }, 'PUT');
      report.disabled.push(item.origin);
    } catch (error) {
      report.failed.push({ id: item.origin, reason: 'imported, but the old task could not be switched off: ' + message(error) });
    }
  }

  if (report.failed.length > 0) {
    log(`[KEL-SCHEDULES] migration incomplete (${report.failed.length} left); will retry next launch`);
    return report;
  }
  report.state = 'done';
  try {
    await deps.engine('/api/schedules', {
      action: 'migration_status',
      record: { imported: report.imported.length, paused: report.paused.length, origins: report.imported },
    });
  } catch {
    // The local marker below is enough to stop repeats; the engine's record is a courtesy.
  }
  deps.markDone(report);
  log(`[KEL-SCHEDULES] migration done: ${report.imported.length} moved, ${report.paused.length} paused`);
  return report;
}
