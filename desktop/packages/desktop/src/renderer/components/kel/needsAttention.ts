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

export type AttentionKind = 'approval' | 'input' | 'permission' | 'failure' | 'review' | 'continuation' | 'connection' | 'stale';

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

export interface AttentionProviderState {
  /** Engine provider id (code — never rendered as machinery). */
  id: string;
  /** The provider's user-facing name, when the engine reports one. */
  label?: string;
  status?: string;
}

export interface AttentionPayload {
  jobs?: KelWorkJob[];
  continuation?: KelContinuationCandidate[];
  boundaryRequests?: KelBoundaryRequest[];
  /** Provider statuses from the same /api/state read (D5: setup needs are attention too). */
  providers?: AttentionProviderState[];
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
    } else if (job.state === 'WAITING_RESOURCE' && !job.route_block) {
      // D7: an expired/orphaned run lands here. The engine fences the run and never replays it on
      // its own (reconcile first), so this genuinely needs a person. A route-blocked job
      // (`route_block` set) is the opposite: it resumes automatically once a model is available,
      // so it must NOT be an interruption — it stays in the continuation/Work surfaces.
      const reason = Object.values(job.milestones ?? {}).find(
        (entry) => entry.state === 'UNCERTAIN' && entry.error
      )?.error;
      if (reason) {
        items.push({
          id: `input-${job.id}`,
          kind: 'input',
          title: 'A run stopped mid-flight and needs a fresh start',
          detail: `${requestTitle(job)} — ${reason}. Kel will not replay it on its own.`,
          projectId: jobProject(job),
          action: openAction(jobConversation(job), 'Open the chat'),
          at: job.updated ?? 0,
        });
      }
    }
  }

  // D5: a provider that still needs setup is a genuine human interruption. The engine states
  // `not_installed` / `installed_not_authenticated` are exactly "Needs setup" in user language.
  // The item is deliberately unbound to a project (fail-closed under project filters) and carries
  // no timestamp — it is persistent configuration, not a fleeting event, so it sorts below live asks.
  for (const provider of payload.providers ?? []) {
    if (provider.status !== 'not_installed' && provider.status !== 'installed_not_authenticated') continue;
    items.push({
      id: `connection-${provider.id}`,
      kind: 'connection',
      title: 'A connection needs setup',
      detail: `${provider.label || provider.id} — finish setting it up so Kel can keep it available.`,
      action: { label: 'Set it up', to: '/providers' },
      at: 0,
    });
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
