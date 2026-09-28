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

import type { KelBoundaryRequest, KelContinuationCandidate, KelSchedule, KelWorkJob } from './kelApi';
import { workWords } from './workLanguage';
import { workTitle } from './jobLabels';

export type AttentionKind =
  | 'approval'
  | 'input'
  | 'permission'
  | 'failure'
  | 'review'
  | 'continuation'
  | 'connection'
  | 'schedule'
  | 'stale';

export interface AttentionItem {
  /** Stable, derived key — built only from authoritative ids present in the payload. */
  id: string;
  kind: AttentionKind;
  title: string;
  detail: string;
  /** The project this item is BOUND to by the payload (never inferred). */
  projectId?: string;
  /** Where the existing authoritative decision lives; absent = no action may be shown. */
  action?: AttentionAction;
  /** True when the person must decide or act; a finished-but-unchecked result is not that. */
  needsYou: boolean;
  /** The job this item is about, when it is about one. */
  jobId?: string;
  at: number;
}

export interface AttentionAction {
  label: string;
  to: string;
  /** Where to go when `to` names a chat this device cannot open (the job, highlighted on Activity). */
  fallback?: string;
  /** D-70: the work has a card at the top of its chat; the action opens that card (answer it there). */
  card?: string;
}

export interface AttentionProviderState {
  /** Engine provider id (code — never rendered as machinery). */
  id: string;
  /** The provider's user-facing name, when the engine reports one. */
  label?: string;
  status?: string;
  /** Engine detail, e.g. 'API key needed' or 'sign-in needed'. */
  note?: string;
}

export interface AttentionPayload {
  jobs?: KelWorkJob[];
  continuation?: KelContinuationCandidate[];
  boundaryRequests?: KelBoundaryRequest[];
  /** Provider statuses from the same /api/state read (D5: setup needs are attention too). */
  providers?: AttentionProviderState[];
  /** D-57: scheduled tasks; one whose recipe, project or chat is gone is paused with a problem. */
  schedules?: KelSchedule[];
}

export interface AttentionFilter {
  projectId?: string;
}

const jobConversation = (job: KelWorkJob): string | undefined => job.conversation;
export const jobProject = (job: KelWorkJob): string | undefined => job.contract?.project_id;

/** A job's title: the name its work card shows (VIS-13, `workTitle`), never an id. */
export const requestTitle = (job: Pick<KelWorkJob, 'contract'> | null | undefined, fallback = 'Untitled work'): string =>
  workTitle(job, fallback);

/**
 * Activity, with this job highlighted. D-70: the Work page is retired; Activity lists every job
 * (including work from before the work cards) with its one next step.
 */
export const jobRouteFor = (jobId: string | undefined): string =>
  jobId ? `/activity?job=${encodeURIComponent(jobId)}` : '/activity';

/** D-70: staffed work has its own card at the top of the chat (older work does not). */
export const hasWorkCard = (job: Pick<KelWorkJob, 'contract'> | null | undefined): boolean =>
  Boolean((job?.contract as { staffing?: unknown } | undefined)?.staffing);

/**
 * D-70: when a job has a card, Needs you defers to it — the one action opens the chat with that
 * card's panel open, where Kel's question and its answer box are.
 */
export function cardAction(job: Pick<KelWorkJob, 'id' | 'conversation'>, label = 'Answer on its card'): AttentionAction {
  return { ...jobChatAction(job, label), card: job.id };
}

/**
 * "Open the chat" for a job: its conversation when the payload names one, with the job highlighted
 * on Activity as the fallback (and as the target when no conversation is known). Never a guessed chat.
 */
export function jobChatAction(job: Pick<KelWorkJob, 'id' | 'conversation'>, label = 'Open the chat'): AttentionAction {
  const conversation = job.conversation;
  return conversation
    ? { label, to: `/conversation/${conversation}`, fallback: jobRouteFor(job.id) }
    : { label, to: jobRouteFor(job.id) };
}

function openAction(conversation: string | undefined, label: string, jobId?: string): AttentionAction {
  // Both targets are existing surfaces that already own the follow-up: the conversation route
  // that hosts the approval/result, or the Activity list when the payload cannot name a conversation.
  return conversation
    ? { label, to: `/conversation/${conversation}`, ...(jobId ? { fallback: jobRouteFor(jobId) } : {}) }
    : { label, to: jobRouteFor(jobId) };
}

/**
 * Resolve an action to a route this device can open. `mapChat` turns an engine conversation route
 * into the app's own chat route and returns the input unchanged when it cannot; in that case the
 * action's fallback (the job on Activity) is used instead of a chat that would not open.
 */
export function resolveAttentionRoute(action: AttentionAction, mapChat: (to: string) => string): string {
  const mapped = mapChat(action.to);
  if (mapped === action.to && action.to.startsWith('/conversation/') && action.fallback) return action.fallback;
  return mapped;
}

export function collectAttention(payload: AttentionPayload, filter: AttentionFilter = {}): AttentionItem[] {
  const jobs = payload.jobs ?? [];
  const byId = new Map<string, KelWorkJob>();
  for (const job of jobs) byId.set(job.id, job);
  const items: AttentionItem[] = [];

  for (const job of jobs) {
    // One story per job: the words come from the shared table (workLanguage.ts).
    const view = workWords(job);
    const base = {
      title: requestTitle(job),
      projectId: jobProject(job),
      jobId: job.id,
      action: hasWorkCard(job) ? cardAction(job) : openAction(jobConversation(job), 'Open the chat', job.id),
      at: job.updated ?? 0,
    };
    if (job.state === 'AWAITING_USER') {
      items.push({ ...base, id: `approval-${job.id}`, kind: 'approval', needsYou: true,
        detail: `${view.label} — ${view.sentence}` });
    } else if (job.state === 'BLOCKED') {
      items.push({ ...base, id: `input-${job.id}`, kind: 'input', needsYou: true,
        detail: `${view.label} — ${view.sentence}` });
    } else if (job.state === 'CLOSED') {
      const verdict = (job.verdict || '').toUpperCase();
      if (verdict === 'FAILED') {
        items.push({ ...base, id: `failure-${job.id}`, kind: 'failure', needsYou: false,
          detail: `${view.label} — ${view.sentence}` });
      } else if (verdict !== 'VERIFIED') {
        // Finished but not fully checked: worth knowing, but not "waiting on you".
        items.push({ ...base, id: `review-${job.id}`, kind: 'review', needsYou: false,
          detail: `${view.label} — ${view.sentence}` });
      }
    } else if (job.state === 'WAITING_RESOURCE' && !job.route_block) {
      // D7: an expired/orphaned run lands here. The engine fences the run and never replays it on
      // its own (reconcile first), so this genuinely needs a person. A route-blocked job
      // (`route_block` set) is the opposite: it resumes automatically once a model is available,
      // so it must NOT be an interruption — it stays in the continuation/Work surfaces.
      const reason = Object.values(job.milestones ?? {}).find(
        (entry) => entry.state === 'UNCERTAIN' && entry.error
      )?.error;
      items.push({ ...base, id: `input-${job.id}`, kind: 'input', needsYou: true,
        detail: `${view.label} — ${reason ? `${reason.replace(/\.$/, '')}. ` : ''}Kel will not replay it on its own; reply “continue” in its chat to pick it up.` });
    }
  }

  // D5: a provider that still needs setup is a genuine human interruption. The engine states
  // `not_installed` / `installed_not_authenticated` are exactly "Needs setup" in user language.
  // The item is deliberately unbound to a project (fail-closed under project filters) and carries
  // no timestamp — it is persistent configuration, not a fleeting event, so it sorts below live asks.
  // Once any provider works, a provider that was never set up (not installed, or an API key never
  // added) is optional, not an interruption; a CLI that is installed but signed out still is.
  const needsSetup = (status?: string) => status === 'not_installed' || status === 'installed_not_authenticated';
  const anyUsable = (payload.providers ?? []).some((provider) => provider.status && !needsSetup(provider.status));
  for (const provider of payload.providers ?? []) {
    if (!needsSetup(provider.status)) continue;
    if (anyUsable && (provider.status === 'not_installed' || provider.note === 'API key needed')) continue;
    items.push({
      id: `connection-${provider.id}`,
      kind: 'connection',
      title: 'A connection needs setup',
      detail: `${provider.label || provider.id} — finish setting it up so Kel can keep it available.`,
      action: { label: 'Set it up', to: '/settings/providers' },
      needsYou: true,
      at: 0,
    });
  }

  for (const candidate of payload.continuation ?? []) {
    const jobId = candidate.job_id || candidate.job?.id;
    const job = jobId ? byId.get(jobId) : undefined;
    // Finished work (done, checked or not) is never something to pick up again (D-70).
    if (job && (job.state === 'CLOSED' || job.state === 'CANCELLED')) continue;
    if (!job) {
      items.push({
        id: `stale-continuation-${jobId ?? 'unknown'}`,
        kind: 'stale',
        title: 'This item is no longer available',
        detail: 'The work it pointed to is gone from the current view. Refresh to see what is current.',
        needsYou: false,
        at: 0,
      });
      continue;
    }
    items.push({
      id: `continuation-${job.id}`,
      kind: 'continuation',
      title: requestTitle(job),
      detail: `${workWords(job).label} — Kel can pick this up where it stopped.`,
      projectId: jobProject(job),
      jobId: job.id,
      action: openAction(jobConversation(job), 'Open the chat', job.id),
      needsYou: false,
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
      action: { label: 'Review the request', to: '/settings/permissions' },
      needsYou: true,
      at: request.created,
    });
  }

  // D-57: a scheduled task the engine paused because something it needs is gone. Bound to the
  // schedule's own project; the one action opens the task's page, where it is fixed and resumed.
  for (const schedule of payload.schedules ?? []) {
    if (!schedule?.id || schedule.deleted) continue;
    if (!schedule.problem && schedule.status !== 'needs_attention') continue;
    items.push({
      id: `schedule-${schedule.id}`,
      kind: 'schedule',
      title: schedule.name || 'A scheduled task',
      detail: `Scheduled task paused — ${schedule.problem?.trim().replace(/\.$/, '') || 'something it needs has changed'}.`,
      projectId: schedule.project_id || undefined,
      action: { label: 'Open the task', to: `/scheduled/${encodeURIComponent(schedule.id)}` },
      needsYou: true,
      at: schedule.updated ?? 0,
    });
  }

  const filtered = filter.projectId ? items.filter((item) => item.projectId === filter.projectId) : items;
  return filtered.sort((a, b) => b.at - a.at);
}
