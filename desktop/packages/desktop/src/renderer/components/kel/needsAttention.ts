/**
 * R9.D — "Needs your attention": a DERIVED-ONLY view over existing authoritative state.
 *
 * This module owns no workflow truth. It reads exactly what the shell already reads
 * (`/api/state` jobs + continuation, `/api/autonomy` boundary requests), maps each entry to a
 * plain-language item, and attaches only actions that open the surface that already owns the
 * decision. It never invents a mutation, never joins across projects, and never renders worker
 * ids, leases, assignments, runtimes, routing or queue internals.
 *
 * Scoping contract (hostile-project-isolation): when a `projectId` filter is given, an item is
 * kept only if the PAYLOAD itself binds it to that project. Unbound items (or items bound
 * elsewhere) are excluded — fail-closed, never guessed. Items whose referenced entities cannot
 * be resolved are surfaced honestly as `stale` with no action.
 */

import type { KelBoundaryRequest, KelContinuationCandidate, KelWorkJob } from './kelApi';

export type AttentionKind = 'approval' | 'input' | 'permission' | 'failure' | 'review' | 'continuation' | 'stale';

export interface AttentionItem {
  /** Stable, derived key — built only from authoritative ids present in the payload. */
  id: string;
  kind: AttentionKind;
  title: string;
  detail: string;
  /** The project this item is BOUND to by the payload (never inferred). */
  projectId?: string;
  /** Where the existing authoritative decision lives; absent = no action may be shown. */
  action?: { label: string; to: string };
  at: number;
}

export interface AttentionPayload {
  jobs?: KelWorkJob[];
  continuation?: KelContinuationCandidate[];
  boundaryRequests?: KelBoundaryRequest[];
}

export interface AttentionFilter {
  projectId?: string;
}

const jobConversation = (job: KelWorkJob): string | undefined => job.conversation;
export const jobProject = (job: KelWorkJob): string | undefined => job.contract?.project_id;

const requestTitle = (job: KelWorkJob): string => job.contract?.request?.trim() || 'Untitled work';

function openAction(conversation: string | undefined, label: string): { label: string; to: string } {
  // Both targets are existing surfaces that already own the follow-up: the conversation route
  // that hosts the approval/result, or the Work list when the payload cannot name a conversation.
  return conversation ? { label, to: `/conversation/${conversation}` } : { label, to: '/work' };
}

export function collectAttention(payload: AttentionPayload, filter: AttentionFilter = {}): AttentionItem[] {
  const jobs = payload.jobs ?? [];
  const byId = new Map<string, KelWorkJob>();
  for (const job of jobs) byId.set(job.id, job);
  const items: AttentionItem[] = [];

  for (const job of jobs) {
    if (job.state === 'AWAITING_USER') {
      items.push({
        id: `approval-${job.id}`,
        kind: 'approval',
        title: 'An approval is waiting',
        detail: `${requestTitle(job)} — Kel is holding until you decide.`,
        projectId: jobProject(job),
        action: openAction(jobConversation(job), 'Open the chat'),
        at: job.updated ?? 0,
      });
    } else if (job.state === 'BLOCKED') {
      items.push({
        id: `input-${job.id}`,
        kind: 'input',
        title: 'Kel needs a decision to continue',
        detail: `${requestTitle(job)} — a safety rule stopped it; the reason is recorded with the work.`,
        projectId: jobProject(job),
        action: openAction(jobConversation(job), 'Open the chat'),
        at: job.updated ?? 0,
      });
    } else if (job.state === 'CLOSED') {
      const verdict = (job.verdict || '').toUpperCase();
      if (verdict === 'FAILED') {
        items.push({
          id: `failure-${job.id}`,
          kind: 'failure',
          title: 'Finished with a failure',
          detail: `${requestTitle(job)} — the recorded result did not pass. Nothing was retried silently.`,
          projectId: jobProject(job),
          action: openAction(jobConversation(job), 'Open the chat'),
          at: job.updated ?? 0,
        });
      } else if (verdict && verdict !== 'VERIFIED') {
        items.push({
          id: `review-${job.id}`,
          kind: 'review',
          title: 'Finished without a clean verification',
          detail: `${requestTitle(job)} — the result needs a human eye before it counts.`,
          projectId: jobProject(job),
          action: openAction(jobConversation(job), 'Open the chat'),
          at: job.updated ?? 0,
        });
      }
    }
  }

  for (const candidate of payload.continuation ?? []) {
    const jobId = candidate.job_id || candidate.job?.id;
    const job = jobId ? byId.get(jobId) : undefined;
    if (!job) {
      items.push({
        id: `stale-continuation-${jobId ?? 'unknown'}`,
        kind: 'stale',
        title: 'This item is no longer available',
        detail: 'The work it pointed to is gone from the current view. Refresh to see what is current.',
        at: 0,
      });
      continue;
    }
    items.push({
      id: `continuation-${job.id}`,
      kind: 'continuation',
      title: 'Ready to continue when you are',
      detail: `${requestTitle(job)} — Kel can pick this up where it stopped.`,
      projectId: jobProject(job),
      action: openAction(jobConversation(job), 'Open the chat'),
      at: job.updated ?? 0,
    });
  }

  for (const request of payload.boundaryRequests ?? []) {
    if (request.status !== 'PENDING') continue;
    items.push({
      id: `permission-${request.request_id}`,
      kind: 'permission',
      title: 'A permission decision is waiting',
      detail: `${request.what?.trim() || request.scope} — Kel asked before acting; only you can grant it.`,
      // The boundary payload binds to a scope, not to a project; when a project filter is active
      // this item is therefore excluded below (fail-closed) rather than attributed by guess.
      projectId: undefined,
      action: { label: 'Review the request', to: '/autonomy' },
      at: request.created,
    });
  }

  const filtered = filter.projectId ? items.filter((item) => item.projectId === filter.projectId) : items;
  return filtered.sort((a, b) => b.at - a.at);
}
