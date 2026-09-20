/**
 * D1 — provider state in user language.
 *
 * The engine states (`runtime/kel/providers.py`) are the truth; this module maps them to the
 * plain-language labels the product promises — Available · Needs setup · Temporarily unavailable ·
 * Unavailable — with a concrete reason. It never upgrades a state: an unauthenticated or paused
 * provider can never read "Available".
 */

export type ProviderTone = 'ok' | 'wait' | 'uncertain' | 'failed';

export interface ProviderPresentation {
  label: string;
  tone: ProviderTone;
  reason: string;
  /** When a paused provider resumes automatically (epoch ms), if known. */
  until: number | null;
}

export interface ProviderStateInput {
  status: string;
  class?: string;
  note?: string | null;
  failures?: number;
  circuit_until?: number | null;
  quota?: number | null;
  quota_reset?: number | null;
}

const humanize = (value: string): string => (value || 'unknown').replace(/_/g, ' ');

/** Engine statuses that mean "Kel can use this provider right now". */
export const USABLE_STATUSES = ['healthy', 'quota', 'quota_not_reported'] as const;

export function usableNow(provider: { status: string }): boolean {
  return (USABLE_STATUSES as readonly string[]).includes(provider.status);
}

export function toneChipClass(tone: ProviderTone): string {
  if (tone === 'ok') return 'kel-chip kel-chip--ok';
  if (tone === 'wait') return 'kel-chip kel-chip--wait';
  if (tone === 'uncertain') return 'kel-chip kel-chip--uncertain';
  return 'kel-chip kel-chip--failed';
}

export function presentProvider(provider: ProviderStateInput): ProviderPresentation {
  const failures = provider.failures ?? 0;
  const until = provider.circuit_until ?? null;
  switch (provider.status) {
    case 'healthy':
      return { label: 'Available', tone: 'ok', reason: 'Ready to use.', until: null };
    case 'quota':
      return {
        label: 'Available',
        tone: 'ok',
        reason:
          provider.quota !== null && provider.quota !== undefined
            ? `${provider.quota}% of the plan left.`
            : 'Within the plan quota.',
        until: null,
      };
    case 'quota_not_reported':
      return {
        label: 'Available',
        tone: 'ok',
        reason: 'Ready to use — this provider does not report usage.',
        until: null,
      };
    case 'installed_not_authenticated':
      return {
        label: 'Needs setup',
        tone: 'wait',
        reason:
          provider.note === 'sign-in needed'
            ? 'The CLI is installed but not signed in yet.'
            : provider.note === 'API key needed'
              ? 'No API key is stored for this provider yet.'
              : provider.note || 'Finish setting this provider up.',
        until: null,
      };
    case 'not_installed':
      return {
        label: 'Unavailable',
        tone: 'failed',
        reason: 'Not installed on this computer yet.',
        until: null,
      };
    case 'degraded':
      return {
        label: 'Temporarily unavailable',
        tone: 'uncertain',
        reason:
          failures > 0
            ? `Paused after ${failures} recent failure${failures === 1 ? '' : 's'}.`
            : 'Paused after recent problems.',
        until,
      };
    case 'unavailable':
      return { label: 'Unavailable', tone: 'failed', reason: 'The usage quota is used up.', until: null };
    default:
      return {
        label: humanize(provider.status),
        tone: 'uncertain',
        reason: provider.note || 'Kel has not classified this state yet.',
        until: null,
      };
  }
}
