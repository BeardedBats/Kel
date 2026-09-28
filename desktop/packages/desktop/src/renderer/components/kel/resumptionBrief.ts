/**
 * D6 — "While you were away": a DERIVED-ONLY resumption brief (the Home "Needs you" card).
 *
 * Reopening Kel should say, in plain language, what durable state already knows: what needs you,
 * what is paused, and any recorded restore outcome. D-70: the card is headed "Needs you", so
 * finished and still-running work is not listed here (the work cards at the top of each chat carry
 * it), and work that has a card is answered on that card. This module owns no workflow truth and
 * invents nothing:
 *   - job lines use the one shared state→words table (workLanguage.ts), so a job reads the same
 *     here as on Activity and its in-chat card — and each job appears on exactly one line;
 *   - permission and setup needs reuse the attention aggregator (needsAttention.ts);
 *   - the restore line reads the engine's recorded restore outcome (audit PER-02) — silence when
 *     no restore was ever attempted.
 * When there is nothing to say the brief is `quiet` and the caller renders nothing at all.
 *
 * Continuation is a human decision: the brief never resumes anything on its own. Every job line
 * names the job by its title and opens that job's chat (or the job on Activity when no chat is known).
 */
import type { KelBoundaryRequest, KelContinuationCandidate, KelSchedule, KelWorkJob } from './kelApi';
import {
  cardAction,
  collectAttention,
  hasWorkCard,
  jobChatAction,
  requestTitle,
  type AttentionAction,
  type AttentionProviderState,
} from './needsAttention';
import { workWords } from './workLanguage';

export type BriefKind = 'restore' | 'needs-you' | 'finished' | 'stopped' | 'resumable' | 'active';

export interface BriefLine {
  id: string;
  kind: BriefKind;
  title: string;
  detail: string;
  /** How the line should read at a glance: a checked result, something to look at, or live work. */
  tone: 'success' | 'attention' | 'active';
  action?: AttentionAction;
}

export interface ResumptionBrief {
  quiet: boolean;
  headline: string;
  summary: string;
  lines: BriefLine[];
}

export interface ResumptionPayload {
  jobs?: KelWorkJob[];
  continuation?: KelContinuationCandidate[];
  boundaryRequests?: KelBoundaryRequest[];
  providers?: AttentionProviderState[];
  /** D-57: a scheduled task paused because something it needs is gone needs you too. */
  schedules?: KelSchedule[];
  /** FN-02: `title` names the outcome; `notice: false` once the one-time notice has been shown. */
  restore?: { ok: boolean; detail?: string; at?: number; title?: string; notice?: boolean } | null;
  now?: number;
}

/** Per-section cap: the brief is a nudge, not a second Work page. */
export const BRIEF_SECTION_CAP = 3;
/** An informational "restored" line is only worth showing soon after the restore. */
export const RESTORE_FRESH_MS = 48 * 60 * 60 * 1000;

const byUpdatedDesc = (a: KelWorkJob, b: KelWorkJob): number => (b.updated ?? 0) - (a.updated ?? 0);

/** The job's title, falling back to the engine's continuation title before a neutral label. */
const titleOf = (job: KelWorkJob, candidates: KelContinuationCandidate[]): string => {
  const fromJob = requestTitle(job, '');
  if (fromJob) return fromJob;
  const candidate = candidates.find((entry) => (entry.job_id || entry.job?.id) === job.id);
  return candidate?.title?.trim() || candidate?.summary?.trim() || 'Untitled work';
};

/** The engine's recorded reason for a stop, when there is one (never invented). */
const recordedReason = (job: KelWorkJob): string | undefined =>
  job.route_block || Object.values(job.milestones ?? {}).find((entry) => entry.error)?.error || undefined;

const sentence = (text: string): string => text.trim().replace(/\.$/, '');

/**
 * LIVE-3 / FN-03 — why a job waits on Nick, as the engine's resume brief names it (`wait`):
 * a restart stopped a step part-way (`interrupted`), it ran out of tries (`stuck`), its Fixed model
 * can't run here (`fixed`), nothing set up here can do it (`no_route`), or it reached its budget
 * (`budget`). Only Nick moves these on.
 */
export type BriefWait = 'interrupted' | 'stuck' | 'fixed' | 'no_route' | 'budget';
const WAITS = new Set<BriefWait>(['interrupted', 'stuck', 'fixed', 'no_route', 'budget']);

/** The engine's route-block prefixes (runtime/kel/core.py `route_wait_kind`), then its plain words. */
const ROUTE_WAITS: Array<[string, BriefWait]> = [
  ['Fixed model not available: ', 'fixed'],
  ['Budget reached: ', 'budget'],
  ['Out of tries: ', 'stuck'],
  ['No model can do this: ', 'no_route'],
];

const OPEN_STATES = new Set(['CLOSED', 'DONE', 'CANCELLED', 'CANCELLING', 'PAUSED', 'PAUSING']);

/**
 * The job's `wait`: the engine's own when the payload carries it (on the job or its continuation
 * entry), else read from the same facts the engine reads — the route block's prefix, or a step the
 * engine marked `interrupted` (a WAITING_RESOURCE job without a route block is a fenced one).
 */
export const briefWait = (job: KelWorkJob, candidate?: KelContinuationCandidate | null): BriefWait | null => {
  const told = (job as { wait?: unknown }).wait ?? (candidate as { wait?: unknown } | null | undefined)?.wait;
  if (typeof told === 'string' && WAITS.has(told as BriefWait)) return told as BriefWait;
  const state = String(job.state ?? '').toUpperCase();
  if (OPEN_STATES.has(state)) return null;
  const block = String(job.route_block ?? '');
  if (state === 'WAITING_RESOURCE' && block) return ROUTE_WAITS.find(([prefix]) => block.startsWith(prefix))?.[1] ?? null;
  const marked = Object.values(job.milestones ?? {}).some((entry) => (entry as { interrupted?: boolean }).interrupted === true);
  if (state === 'WAITING_RESOURCE' || marked) return 'interrupted';
  return null;
};

/** The route block's own sentence without its prefix ("GPT-6 Astra can't run here: …"). */
const routeWords = (job: KelWorkJob): string | null => {
  const block = String(job.route_block ?? '').trim();
  const prefix = ROUTE_WAITS.find(([lead]) => block.startsWith(lead))?.[0];
  const rest = (prefix ? block.slice(prefix.length) : '').trim();
  return rest ? sentence(rest) : null;
};

/** What the Home brief says for each `wait`, and what to do — on the work's card when it has one. */
export const waitWords = (wait: BriefWait, job: KelWorkJob, onCard: boolean): { label: string; detail: string } => {
  const reason = routeWords(job);
  const where = (action: string) => (onCard ? `${action} on its card` : `${action} in its chat`);
  switch (wait) {
    case 'interrupted':
      return {
        label: 'Interrupted',
        detail: `Kel’s worker stopped unexpectedly (the app restarted) before a step finished, and Kel won’t repeat it on its own. ${
          onCard ? 'Choose Try again on its card' : 'Reply “continue” in its chat'
        } to start that step again.`,
      };
    case 'stuck':
      return {
        label: 'Out of tries',
        detail: `It ran out of tries before it passed its checks${reason ? ` (${reason})` : ''}. ${
          onCard ? 'Choose Try again on its card' : 'Reply “continue” in its chat'
        } to give it more tries, or stop it.`,
      };
    case 'fixed':
      return {
        label: 'No model can run it',
        detail: `${reason ?? 'Its Fixed model can’t run on this computer'}. Change the model in Settings → Staff & models, then ${
          onCard ? 'choose Try again on its card' : 'reply “continue” in its chat'
        }.`,
      };
    case 'no_route':
      return {
        label: 'No model can run it',
        detail: `${reason ?? 'No model set up on this computer can do this kind of work'}. Change the model in Settings → Staff & models (or set one up), then ${
          onCard ? 'choose Try again on its card' : 'reply “continue” in its chat'
        }.`,
      };
    case 'budget':
      return {
        label: 'Stopped at its budget',
        detail: `${reason ?? 'It used the budget it was given'}. ${where('Raise its budget')} to let it continue, or stop it.`,
      };
  }
};

export function buildResumptionBrief(payload: ResumptionPayload): ResumptionBrief {
  const jobs = (payload.jobs ?? []).toSorted(byUpdatedDesc);
  const candidates = payload.continuation ?? [];
  const now = payload.now ?? Date.now();
  const lines: BriefLine[] = [];

  // 1) A failed restore is the first thing to say — it is durable truth recorded by the engine.
  // FN-02: a one-time notice — once shown it is marked seen, and Settings → System keeps the record.
  if (payload.restore && !payload.restore.ok && payload.restore.notice !== false) {
    lines.push({
      id: 'restore-failed',
      kind: 'restore',
      tone: 'attention',
      title: payload.restore.title?.trim() || 'A restore did not finish',
      detail:
        payload.restore.detail?.trim() ||
        'Kel recorded a restore attempt that failed. Your previous data is kept beside the data folder.',
      action: { label: 'Open Data and backup', to: '/settings/system' },
    });
  }

  // 2) What needs you: jobs that wait on a decision (shared table), then permission and setup asks.
  // LIVE-3 / FN-03: work that only Nick can move on (`wait`) needs him even while it waits on a route.
  const candidateOf = (job: KelWorkJob) => candidates.find((entry) => (entry.job_id || entry.job?.id) === job.id) ?? null;
  const needsYouJobs = jobs.filter((job) => job.state !== 'PAUSED' && (workWords(job).needsYou || briefWait(job, candidateOf(job))));
  const jobNeeds: BriefLine[] = needsYouJobs.map((job) => {
    const wait = briefWait(job, candidateOf(job));
    if (wait) {
      const onCard = hasWorkCard(job);
      const words = waitWords(wait, job, onCard);
      return {
        id: `brief-needs-${job.id}`,
        kind: 'needs-you',
        tone: 'attention',
        title: titleOf(job, candidates),
        detail: `${words.label} — ${words.detail}`,
        action: onCard ? cardAction(job, wait === 'budget' ? 'Open its card' : 'Try again on its card') : jobChatAction(job),
      };
    }
    const view = workWords(job);
    const reason = view.label === 'Interrupted' ? recordedReason(job) : undefined;
    return {
      id: `brief-needs-${job.id}`,
      kind: 'needs-you',
      tone: 'attention',
      title: titleOf(job, candidates),
      detail: reason ? `${view.label} — ${sentence(reason)}. ${view.sentence}` : `${view.label} — ${view.sentence}`,
      // D-70: work with a card is answered on that card; the line opens it.
      action: hasWorkCard(job) ? cardAction(job) : jobChatAction(job),
    };
  });
  const otherNeeds: BriefLine[] = collectAttention({
    boundaryRequests: payload.boundaryRequests ?? [],
    providers: payload.providers ?? [],
    schedules: payload.schedules ?? [],
  })
    .filter((item) => item.needsYou)
    .map((item) => ({
      id: `brief-${item.id}`,
      kind: 'needs-you',
      tone: 'attention',
      title: item.title,
      detail: item.detail,
      action: item.action,
    }));
  const needs = [...jobNeeds, ...otherNeeds];
  lines.push(...needs.slice(0, BRIEF_SECTION_CAP));
  if (needs.length > BRIEF_SECTION_CAP) {
    lines.push({
      id: 'needs-you-more',
      kind: 'needs-you',
      tone: 'attention',
      title: `${needs.length - BRIEF_SECTION_CAP} more things need you`,
      detail: 'Activity lists every one of them.',
      action: { label: 'Open Activity', to: '/activity' },
    });
  }

  // 3) Paused work: a deliberate stop that waits for the person to resume it.
  for (const job of jobs.filter((entry) => entry.state === 'PAUSED').slice(0, BRIEF_SECTION_CAP)) {
    const view = workWords(job);
    const reason = recordedReason(job);
    // VIS-12 / D-70: paused work with a card is picked back up on that card, like everything else it
    // needs; older work without a card still opens its chat.
    const onCard = hasWorkCard(job);
    const next = onCard ? 'pick it back up on its card' : 'open its chat to pick it back up';
    lines.push({
      id: `brief-stopped-${job.id}`,
      kind: 'stopped',
      tone: 'attention',
      title: titleOf(job, candidates),
      detail: reason ? `${view.label} — ${sentence(reason)}. ${next[0].toUpperCase()}${next.slice(1)}.` : `${view.label} — ${next}.`,
      action: onCard ? cardAction(job, 'Open its card') : jobChatAction(job),
    });
  }

  // 4) and 5) are gone (D-70): this card is headed "Needs you", so it never lists finished ("Done and
  // checked") or still-running work — that lives on the work cards at the top of each chat.

  // 6) A successful restore is only worth a line soon after it happened. The engine records epoch
  // seconds (backup module); milliseconds are accepted too so the freshness check cannot misread
  // the units and lie in either direction.
  const normalizeRestoreAt = (value: number | undefined): number | null => {
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) return null;
    return value < 1e12 ? value * 1000 : value;
  };
  const restoreAtMs = normalizeRestoreAt(payload.restore?.at);
  if (
    payload.restore?.ok &&
    payload.restore.notice !== false &&
    restoreAtMs !== null &&
    now - restoreAtMs <= RESTORE_FRESH_MS
  ) {
    lines.push({
      id: 'restore-ok',
      kind: 'restore',
      tone: 'success',
      title: payload.restore.title?.trim() || 'Your data was restored',
      detail: payload.restore.detail?.trim() || 'Kel opened with the restored data.',
      action: { label: 'Open Data and backup', to: '/settings/system' },
    });
  }

  // Counts come from the emitted lines, so the headline summary can never overstate what is shown.
  const countOf = (kind: BriefKind): number => lines.filter((line) => line.kind === kind && line.id !== 'needs-you-more').length;
  const needsYou = needs.length;
  const parts: string[] = [];
  if (needsYou) parts.push(`${needsYou} need${needsYou === 1 ? 's' : ''} you`);
  if (countOf('stopped')) parts.push(`${countOf('stopped')} paused`);

  return {
    quiet: lines.length === 0,
    headline: 'While you were away',
    summary: parts.length ? parts.join(' · ') : 'Nothing needs you right now.',
    lines,
  };
}
