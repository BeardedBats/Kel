/**
 * D6 — "While you were away": a DERIVED-ONLY resumption brief (the Home "Needs you" card).
 *
 * Reopening Kel should say, in plain language, what durable state already knows: what needs you,
 * what is paused, what finished (and whether it was checked), what is still running, and any
 * recorded restore outcome. This module owns no workflow truth and invents nothing:
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
  collectAttention,
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
  restore?: { ok: boolean; detail?: string; at?: number } | null;
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

export function buildResumptionBrief(payload: ResumptionPayload): ResumptionBrief {
  const jobs = (payload.jobs ?? []).toSorted(byUpdatedDesc);
  const candidates = payload.continuation ?? [];
  const now = payload.now ?? Date.now();
  const lines: BriefLine[] = [];

  // 1) A failed restore is the first thing to say — it is durable truth recorded by the engine.
  if (payload.restore && !payload.restore.ok) {
    lines.push({
      id: 'restore-failed',
      kind: 'restore',
      tone: 'attention',
      title: 'A restore did not finish',
      detail:
        payload.restore.detail?.trim() ||
        'Kel recorded a restore attempt that failed. Your previous data is kept beside the data folder.',
      action: { label: 'Open Settings', to: '/settings' },
    });
  }

  // 2) What needs you: jobs that wait on a decision (shared table), then permission and setup asks.
  const needsYouJobs = jobs.filter((job) => job.state !== 'PAUSED' && workWords(job).needsYou);
  const jobNeeds: BriefLine[] = needsYouJobs.map((job) => {
    const view = workWords(job);
    const reason = view.label === 'Interrupted' ? recordedReason(job) : undefined;
    return {
      id: `brief-needs-${job.id}`,
      kind: 'needs-you',
      tone: 'attention',
      title: titleOf(job, candidates),
      detail: reason ? `${view.label} — ${sentence(reason)}. ${view.sentence}` : `${view.label} — ${view.sentence}`,
      action: jobChatAction(job),
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
    lines.push({
      id: `brief-stopped-${job.id}`,
      kind: 'stopped',
      tone: 'attention',
      title: titleOf(job, candidates),
      detail: reason ? `${view.label} — ${sentence(reason)}. Open its chat to pick it back up.` : `${view.label} — open its chat to pick it back up.`,
      action: jobChatAction(job),
    });
  }

  // 4) What finished, in the same words its card uses ("Done and checked" only for VERIFIED).
  for (const job of jobs.filter((entry) => entry.state === 'CLOSED').slice(0, BRIEF_SECTION_CAP)) {
    const view = workWords(job);
    lines.push({
      id: `brief-finished-${job.id}`,
      kind: 'finished',
      tone: view.tone === 'verified' ? 'success' : 'attention',
      title: titleOf(job, candidates),
      detail: `${view.label} — ${view.sentence}`,
      action: jobChatAction(job),
    });
  }

  // 5) What is still going on its own (running, queued, or waiting for a model).
  const going = jobs.filter((job) => workWords(job).section === 'now' && job.state !== 'CANCELLING' && job.state !== 'CANCEL_REQUESTED');
  for (const job of going.slice(0, BRIEF_SECTION_CAP)) {
    const view = workWords(job);
    const reason = job.state === 'WAITING_RESOURCE' ? job.route_block : undefined;
    lines.push({
      id: `brief-active-${job.id}`,
      kind: 'active',
      tone: 'active',
      title: titleOf(job, candidates),
      detail: reason ? `${view.label} — ${sentence(reason)}. ${view.sentence}` : `${view.label} — ${view.sentence}`,
      action: jobChatAction(job),
    });
  }

  // 6) A successful restore is only worth a line soon after it happened. The engine records epoch
  // seconds (backup module); milliseconds are accepted too so the freshness check cannot misread
  // the units and lie in either direction.
  const normalizeRestoreAt = (value: number | undefined): number | null => {
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) return null;
    return value < 1e12 ? value * 1000 : value;
  };
  const restoreAtMs = normalizeRestoreAt(payload.restore?.at);
  if (payload.restore?.ok && restoreAtMs !== null && now - restoreAtMs <= RESTORE_FRESH_MS) {
    lines.push({
      id: 'restore-ok',
      kind: 'restore',
      tone: 'success',
      title: 'Your data was restored',
      detail: payload.restore.detail?.trim() || 'Kel opened with the restored data.',
      action: { label: 'Open Settings', to: '/settings' },
    });
  }

  // Counts come from the emitted lines, so the headline summary can never overstate what is shown.
  const countOf = (kind: BriefKind): number => lines.filter((line) => line.kind === kind && line.id !== 'needs-you-more').length;
  const needsYou = needs.length;
  const parts: string[] = [];
  if (needsYou) parts.push(`${needsYou} need${needsYou === 1 ? 's' : ''} you`);
  if (countOf('stopped')) parts.push(`${countOf('stopped')} paused`);
  if (countOf('finished')) parts.push(`${countOf('finished')} finished`);
  if (countOf('active')) parts.push(`${countOf('active')} still going`);

  return {
    quiet: lines.length === 0,
    headline: 'While you were away',
    summary: parts.length ? parts.join(' · ') : 'Nothing needs you right now.',
    lines,
  };
}
