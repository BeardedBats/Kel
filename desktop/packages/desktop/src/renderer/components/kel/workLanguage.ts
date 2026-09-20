/**
 * Shared user-language for work state (D12/D14). The Work page and the Activity view must say the
 * same things about the same engine facts; this module is the one place those sentences live.
 */
import type { KelJobRoute } from './kelApi';

export const VERDICT_TEXT: Record<string, string> = {
  VERIFIED: 'verified',
  FAILED: 'failed — see the checks',
  UNCERTAIN: 'not confirmed yet — needs evidence',
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

/** Plain words for a job's state; unknown states degrade to readable text, never a raw enum. */
export const JOB_STATE_TEXT: Record<string, string> = {
  QUEUED: 'queued',
  READY: 'waiting to start',
  RUNNING: 'in progress',
  VERIFYING: 'being checked',
  VERIFIED: 'finished — results are being checked',
  WAITING_RESOURCE: 'waiting for an available model',
  AWAITING_USER: 'waiting on you',
  BLOCKED: 'needs a hand',
  PAUSED: 'paused',
  CANCEL_REQUESTED: 'stopping',
  CANCELLING: 'stopping',
};

export const jobStateText = (state: string | undefined): string => {
  if (!state) return 'unknown';
  return JOB_STATE_TEXT[state] ?? state.toLowerCase().replace(/_/g, ' ');
};
