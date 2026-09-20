/**
 * D6 — "While you were away": a DERIVED-ONLY resumption brief.
 *
 * Reopening Kel should say, in plain language, what durable state already knows: what needs you,
 * what finished, what stopped, what is waiting for your go-ahead, what is still running, and any
 * recorded restore outcome. This module owns no workflow truth and invents nothing:
 *   - needs-you lines reuse the attention aggregator (jobs, boundary requests, provider setup);
 *   - resumable lines come from the engine's continuation candidates (durable job/milestone state);
 *   - finished/stopped/active lines read the same job records the Work surface renders;
 *   - the restore line reads the engine's recorded restore outcome (audit PER-02) — silence when
 *     no restore was ever attempted.
 * When there is nothing to say the brief is `quiet` and the caller renders nothing at all.
 *
 * Continuation is a human decision: the brief never resumes anything on its own, and its only
 * actions open the existing surface that owns the follow-up.
 */
import type { KelBoundaryRequest, KelContinuationCandidate, KelWorkJob } from './kelApi';
import { collectAttention, type AttentionProviderState } from './needsAttention';

export type BriefKind = 'restore' | 'needs-you' | 'finished' | 'stopped' | 'resumable' | 'active';

export interface BriefLine {
  id: string;
  kind: BriefKind;
  title: string;
  detail: string;
  action?: { label: string; to: string };
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
  restore?: { ok: boolean; detail?: string; at?: number } | null;
  now?: number;
}

/** Per-section cap: the brief is a nudge, not a second Work page. */
export const BRIEF_SECTION_CAP = 3;
/** An informational "restored" line is only worth showing soon after the restore. */
export const RESTORE_FRESH_MS = 48 * 60 * 60 * 1000;

const requestOf = (job: KelWorkJob): string => job.contract?.request?.trim() || 'Untitled work';

const openChat = (conversation: string | undefined): { label: string; to: string } => ({
  label: 'Open the chat',
  to: conversation ? `/conversation/${conversation}` : '/work',
});

const byUpdatedDesc = (a: KelWorkJob, b: KelWorkJob): number => (b.updated ?? 0) - (a.updated ?? 0);

export function buildResumptionBrief(payload: ResumptionPayload): ResumptionBrief {
  const jobs = payload.jobs ?? [];
  const now = payload.now ?? Date.now();
  const lines: BriefLine[] = [];

  // 1) A failed restore is the first thing to say — it is durable truth recorded by the engine.
  if (payload.restore && !payload.restore.ok) {
    lines.push({
      id: 'restore-failed',
      kind: 'restore',
      title: 'A restore did not finish',
      detail:
        payload.restore.detail?.trim() ||
        'Kel recorded a restore attempt that failed. Your previous data is kept beside the data folder.',
      action: { label: 'Open Settings', to: '/settings' },
    });
  }

  // 2) What needs you — the same derived items the Work surface shows, minus the resumable kind.
  const attention = collectAttention({
    jobs,
    continuation: payload.continuation ?? [],
    boundaryRequests: payload.boundaryRequests ?? [],
    providers: payload.providers ?? [],
  }).filter((item) => item.kind !== 'continuation' && item.kind !== 'stale');
  for (const item of attention.slice(0, BRIEF_SECTION_CAP)) {
    lines.push({
      id: `brief-${item.id}`,
      kind: 'needs-you',
      title: item.title,
      detail: item.detail,
      action: item.action,
    });
  }
  if (attention.length > BRIEF_SECTION_CAP) {
    lines.push({
      id: 'needs-you-more',
      kind: 'needs-you',
      title: `${attention.length - BRIEF_SECTION_CAP} more things need you`,
      detail: 'The Work page lists every one of them.',
      action: { label: 'Open Work', to: '/work' },
    });
  }

  // 3) What finished cleanly while you were away.
  const finished = jobs.filter((job) => job.state === 'CLOSED' && (job.verdict || '').toUpperCase() === 'VERIFIED').toSorted(byUpdatedDesc);
  for (const job of finished.slice(0, BRIEF_SECTION_CAP)) {
    lines.push({
      id: `brief-finished-${job.id}`,
      kind: 'finished',
      title: `Finished: ${requestOf(job)}`,
      detail: 'The result passed its checks.',
      action: openChat(job.conversation),
    });
  }

  // 4) What stopped short of finishing (paused / waiting on a resource — not "needs you").
  const stopped = jobs
    .filter((job) => job.state === 'PAUSED' || job.state === 'WAITING_RESOURCE')
    .toSorted(byUpdatedDesc);
  for (const job of stopped.slice(0, BRIEF_SECTION_CAP)) {
    lines.push({
      id: `brief-stopped-${job.id}`,
      kind: 'stopped',
      title: `Stopped: ${requestOf(job)}`,
      detail: 'It stopped before finishing. Open the chat to pick it back up.',
      action: openChat(job.conversation),
    });
  }

  // 5) What is waiting for your go-ahead — durable continuation candidates.
  const resumable = payload.continuation ?? [];
  for (const candidate of resumable.slice(0, BRIEF_SECTION_CAP)) {
    const jobId = candidate.job_id || candidate.job?.id || 'unknown';
    // A candidate's embedded job is a partial record; the full job (when present) carries the chat.
    const job = jobs.find((entry) => entry.id === jobId);
    const reasons = (candidate.reasons ?? []).filter(Boolean);
    lines.push({
      id: `brief-resumable-${jobId}`,
      kind: 'resumable',
      title: `Waiting for your go-ahead: ${candidate.summary ?? (job ? requestOf(job) : 'a paused task')}`,
      detail: `${reasons.length ? `${reasons.join(', ')}. ` : ''}Reply “continue” in that chat — Kel never resumes on its own.`,
      action: openChat(job?.conversation),
    });
  }

  // 6) What is still running.
  const active = jobs.filter((job) => job.state === 'RUNNING').toSorted(byUpdatedDesc);
  for (const job of active.slice(0, BRIEF_SECTION_CAP)) {
    lines.push({
      id: `brief-active-${job.id}`,
      kind: 'active',
      title: `Still working: ${requestOf(job)}`,
      detail: 'This one was already underway when you left.',
      action: openChat(job.conversation),
    });
  }

  // 7) A successful restore is only worth a line soon after it happened. The engine records epoch
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
      title: 'Your data was restored',
      detail: payload.restore.detail?.trim() || 'Kel opened with the restored data.',
      action: { label: 'Open Settings', to: '/settings' },
    });
  }

  const needsYou = lines.filter((line) => line.kind === 'needs-you').length;
  const parts: string[] = [];
  if (needsYou) parts.push(`${needsYou} need${needsYou === 1 ? 's' : ''} you`);
  if (finished.length) parts.push(`${finished.length} finished`);
  if (stopped.length) parts.push(`${stopped.length} stopped`);
  if (resumable.length) parts.push(`${resumable.length} waiting for your go-ahead`);
  if (active.length) parts.push(`${active.length} still running`);

  return {
    quiet: lines.length === 0,
    headline: 'While you were away',
    summary: parts.length ? parts.join(' · ') : 'Nothing needs you right now.',
    lines,
  };
}
