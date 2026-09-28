/**
 * Shared user-language for work state (D12/D14). The Work page and the Activity view must say the
 * same things about the same engine facts; this module is the one place those sentences live.
 */
import type { KelJobRoute } from './kelApi';

/** Verdict words — the same labels the state table uses for a closed job. */
export const VERDICT_TEXT: Record<string, string> = {
  VERIFIED: 'Done and checked',
  FAILED: "Didn't pass its checks",
  UNCERTAIN: 'Finished — not fully checked',
};

export const ROUTE_REASON_TEXT: Record<string, string> = {
  'user choice': 'you set another provider as the choice',
  'not installed': 'it is not installed',
  'authentication unavailable': 'its key is not set',
  'missing capability': "it can't do this kind of work",
  'quota exhausted': 'its quota is used up',
  'health circuit open': 'it had recent failures',
  'privacy scope': 'it is not private enough for this job',
  'quality floor not established': 'it has no track record yet',
};

/** D12: one plain sentence about why a run landed on this provider, honest about unknowns.
 *  D19: engine provider ids never reach the sentence — `labels` maps an id to the name a person
 *  knows, and the fallback humanizes the id rather than showing it raw. */
export const routeSentence = (
  route: KelJobRoute | undefined,
  labels: Record<string, string> = {}
): string | null => {
  if (!route) return null;
  const name = (id: string | null | undefined): string => {
    if (!id) return 'an unnamed provider';
    return labels[id] ?? id.replace(/-/g, ' ');
  };
  const policy = route.route.policy === 'eligible-cost-v1' ? 'the cheapest eligible option' : null;
  const unknown = route.route.unknown_cost ? 'its cost is not known yet' : null;
  const head = `Running on ${name(route.provider || route.route.selected)}${policy ? ` — ${policy}` : ''}${unknown ? ` (${unknown})` : ''}.`;
  const fallback = route.route.fallbacks?.[0]
    ? ` If it fails, Kel will try ${name(route.route.fallbacks[0])}.`
    : '';
  const skipped = Object.entries(route.route.excluded ?? {})
    .slice(0, 3)
    .map(([id, reasons]) => `${name(id)} (${(reasons ?? []).map((reason) => ROUTE_REASON_TEXT[reason] ?? reason).join(', ')})`);
  const skippedSentence = skipped.length ? ` Skipped: ${skipped.join('; ')}.` : '';
  return head + fallback + skippedSentence;
};

/* ─────────────────────────────────────────────────────────────────────────────────────────────
 * One job, one story (WK-4, CH-15). Every surface that talks about a job — Work, Activity, the
 * Home "Needs you" card, the in-chat work card, status chips, the palette — reads its words from
 * this table, so the same engine facts can never be described two different ways. Each job also
 * belongs to exactly one Activity section.
 *
 * Only a VERIFIED verdict may say "checked" (D-53).
 * ───────────────────────────────────────────────────────────────────────────────────────────── */

/** Chip tone. Mirrors KelPrimitives' KelStatus (kept structural so this module stays React-free). */
export type WorkTone =
  | 'running'
  | 'waiting'
  | 'verified'
  | 'uncertain'
  | 'failed'
  | 'blocked'
  | 'queued'
  | 'finished'
  | 'stopping'
  | 'stopped';

/** The one Activity section a job belongs to. */
export type WorkSection = 'now' | 'waiting' | 'finished';

export interface WorkWords {
  /** Short label for chips and headlines ("Done and checked"). */
  label: string;
  /** One plain sentence for detail lines. */
  sentence: string;
  tone: WorkTone;
  section: WorkSection;
  /** True only when the person has to decide or act before the work can go on. */
  needsYou: boolean;
}

export interface WorkFacts {
  state?: string | null;
  verdict?: string | null;
  /** Set while the engine waits for a model; such a job resumes by itself. */
  route_block?: string | null;
}

const words = (label: string, sentence: string, tone: WorkTone, section: WorkSection, needsYou = false): WorkWords => ({
  label,
  sentence,
  tone,
  section,
  needsYou,
});

export const WORK_WORDS = {
  QUEUED: words('Queued', 'Kel will start this in order.', 'queued', 'now'),
  READY: words('Queued', 'Ready to start as soon as a model is free.', 'queued', 'now'),
  RUNNING: words('Working on it', 'Kel is working on this now.', 'running', 'now'),
  VERIFYING: words('Checking the result', 'The work is done and Kel is checking it.', 'running', 'now'),
  PAUSED: words('Paused', 'Paused — resume it when you are ready.', 'waiting', 'waiting', true),
  AWAITING_USER: words('Waiting for your OK', 'Kel is holding until you decide.', 'waiting', 'waiting', true),
  WAITING_RESOURCE: words('Waiting for a model', 'Kel will continue on its own as soon as a model is free.', 'queued', 'now'),
  BLOCKED: words('Blocked — needs your OK', 'A safety rule stopped it; it goes on only with your decision.', 'blocked', 'waiting', true),
  CANCELLING: words('Stopping', 'Kel is stopping this.', 'stopping', 'now'),
  CANCELLED: words('Stopped', 'This work was stopped. Its saved request is kept.', 'stopped', 'finished'),
  VERIFIED: words('Done and checked', 'The result passed its checks.', 'verified', 'finished'),
  UNCHECKED: words('Finished — not fully checked', 'Kel finished, but could not fully check the result.', 'uncertain', 'finished'),
  FAILED: words("Didn't pass its checks", 'The result did not pass its checks. Nothing was retried on its own.', 'failed', 'finished'),
  INTERRUPTED: words('Interrupted', 'It stopped part-way. Your work is kept — reply “continue” in its chat to pick it up.', 'waiting', 'waiting', true),
} as const;

/** The words for one job's engine facts. Unknown states degrade to readable text, never a raw enum. */
export function workWords(job: WorkFacts | null | undefined): WorkWords {
  const state = String(job?.state ?? '').toUpperCase();
  const verdict = String(job?.verdict ?? '').toUpperCase();
  switch (state) {
    case 'QUEUED':
      return WORK_WORDS.QUEUED;
    case 'READY':
      return WORK_WORDS.READY;
    case 'RUNNING':
      return WORK_WORDS.RUNNING;
    case 'VERIFYING':
      return WORK_WORDS.VERIFYING;
    case 'PAUSED':
      return WORK_WORDS.PAUSED;
    case 'AWAITING_USER':
      return WORK_WORDS.AWAITING_USER;
    case 'WAITING_RESOURCE':
      // A route-blocked job resumes by itself; one without a route block is a fenced, interrupted
      // run that the engine will not replay on its own (D7/D19).
      return job?.route_block ? WORK_WORDS.WAITING_RESOURCE : WORK_WORDS.INTERRUPTED;
    case 'BLOCKED':
      return WORK_WORDS.BLOCKED;
    case 'CANCEL_REQUESTED':
    case 'CANCELLING':
      return WORK_WORDS.CANCELLING;
    case 'CANCELLED':
      return WORK_WORDS.CANCELLED;
    case 'ORPHANED':
    case 'INTERRUPTED':
      return WORK_WORDS.INTERRUPTED;
    case 'CLOSED':
    case 'DONE':
      if (verdict === 'VERIFIED') return WORK_WORDS.VERIFIED;
      if (verdict === 'FAILED') return WORK_WORDS.FAILED;
      return WORK_WORDS.UNCHECKED;
    case 'FAILED':
      return WORK_WORDS.FAILED;
    default: {
      const readable = state ? state.toLowerCase().replace(/_/g, ' ') : 'unknown';
      const label = readable.charAt(0).toUpperCase() + readable.slice(1);
      return words(label, label + '.', 'queued', 'now');
    }
  }
}

/** Plain words for a bare engine state (no verdict known). Prefer `workWords(job)` when you have the job. */
export const jobStateText = (state: string | undefined): string => {
  if (!state) return 'Unknown';
  return workWords({ state, route_block: state === 'WAITING_RESOURCE' ? 'route' : null }).label;
};

/* ── Access in plain words (JR-18): what Kel may touch, never "scope: kind: value" ──────────── */

/** The last folder or file name of a path — never the absolute path (JR-16). */
export const shortPlace = (value: string | null | undefined): string => {
  const trimmed = String(value ?? '').trim().replace(/[\\/]+$/, '');
  if (!trimmed) return 'this project';
  const parts = trimmed.split(/[\\/]/).filter(Boolean);
  return parts.at(-1) ?? trimmed;
};

/** One access entry (a permission's kind + target) as a person would say it. */
export const accessLabel = (kind: string | null | undefined, value: string | null | undefined): string => {
  const target = String(value ?? '').trim();
  switch (String(kind ?? '').toLowerCase()) {
    case 'root':
    case 'read':
      return `Read files in ${shortPlace(target)}`;
    case 'write':
      return `Change files in ${shortPlace(target)}`;
    case 'destructive':
      return `Delete or overwrite files in ${shortPlace(target)}`;
    case 'repo':
      return `Work in the ${shortPlace(target)} repository`;
    case 'domain':
    case 'browser':
      return target ? `Visit ${target}` : 'Visit websites';
    case 'tool':
      return target ? `Use the ${target.replace(/[_-]+/g, ' ')} tool` : 'Use a tool';
    case 'external':
    case 'external_api':
      return target ? `Use the outside service ${target}` : 'Use an outside service';
    default:
      return target ? `${String(kind ?? 'Access').replace(/_/g, ' ')}: ${shortPlace(target)}` : 'Access';
  }
};
