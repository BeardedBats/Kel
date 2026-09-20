/**
 * D5 — restrained attention notifications (pure core).
 *
 * The "Needs your attention" surface is derived from authoritative state; this core decides which
 * TRANSITIONS deserve a desktop notification. Hard rules:
 *   - the first snapshot after launch is silent (a person opening Kel sees the surface itself);
 *   - only meaningful kinds notify (approval/input/permission/failure/review/provider, plus work
 *     that finished cleanly); continuation offers and stale self-healing rows never do;
 *   - per-item cooldown + a per-tick cap keep bursts reaspose;
 *   - delivery/visibility gating stays with the existing notification bridge (window focus + the
 *     system.notificationEnabled setting) — this core never decides to interrupt by itself.
 */
import type { AttentionItem } from '@renderer/components/kel/needsAttention';

export const NOTIFIABLE_KINDS = ['approval', 'input', 'permission', 'failure', 'review', 'connection'] as const;
export const NOTIFICATION_COOLDOWN_MS = 30 * 60 * 1000;
export const MAX_EVENTS_PER_TICK = 3;
export const EVENT_BODY_MAX = 180;

export interface AttentionEvent {
  key: string;
  body: string;
  conversation_id?: string;
}

export interface AttentionNotificationState {
  initialized: boolean;
  seen: Set<string>;
  lastNotified: Map<string, number>;
}

export interface FinishedWork {
  id: string;
  title: string;
  conversation_id?: string;
}

export const emptyAttentionNotificationState = (): AttentionNotificationState => ({
  initialized: false,
  seen: new Set(),
  lastNotified: new Map(),
});

const conversationOf = (target: string | undefined): string | undefined => {
  const match = /^\/conversation\/([^/?#]+)/.exec(target || '');
  return match ? decodeURIComponent(match[1]) : undefined;
};

const bodyOf = (title: string, detail: string): string => {
  const text = detail ? `${title} — ${detail}` : title;
  return text.length > EVENT_BODY_MAX ? `${text.slice(0, EVENT_BODY_MAX - 1)}…` : text;
};

interface DiffOptions {
  kinds?: readonly string[];
  kindFor?: (candidate: { id: string }) => string | undefined;
  keyFor: (candidate: { id: string }) => string;
  eventFor: (candidate: { id: string }) => AttentionEvent | null;
}

function diffOne(
  state: AttentionNotificationState,
  candidates: { id: string }[],
  now: number,
  options: DiffOptions
): { state: AttentionNotificationState; events: AttentionEvent[] } {
  // `seen` mirrors THIS snapshot (a resolved item that returns later counts as new again);
  // `lastNotified` persists so the cooldown can gate re-notification, and is pruned past the
  // cooldown horizon so it cannot grow without bound.
  const previous = state.seen;
  const seen = new Set<string>();
  const lastNotified = new Map(state.lastNotified);
  const allowed = options.kinds ? new Set<string>(options.kinds) : null;
  const events: AttentionEvent[] = [];
  for (const candidate of candidates) {
    const key = options.keyFor(candidate);
    const isNew = !previous.has(key);
    seen.add(key);
    if (!state.initialized || !isNew) continue;
    if (allowed) {
      const kind = options.kindFor ? options.kindFor(candidate) : undefined;
      if (!kind || !allowed.has(kind)) continue;
    }
    const last = lastNotified.get(key) ?? Number.NEGATIVE_INFINITY;
    if (now - last < NOTIFICATION_COOLDOWN_MS) continue;
    if (events.length >= MAX_EVENTS_PER_TICK) break;
    const event = options.eventFor(candidate);
    if (!event) continue;
    lastNotified.set(key, now);
    events.push(event);
  }
  for (const [key, at] of lastNotified) {
    if (now - at > NOTIFICATION_COOLDOWN_MS) lastNotified.delete(key);
  }
  return { state: { initialized: true, seen, lastNotified }, events };
}

/**
 * Attention items → events for items that are NEW since the previous snapshot. The first call
 * (state.initialized === false) only records the baseline and emits nothing.
 */
export function diffAttentionEvents(
  state: AttentionNotificationState,
  items: AttentionItem[],
  now: number
): { state: AttentionNotificationState; events: AttentionEvent[] } {
  return diffOne(state, items, now, {
    kinds: NOTIFIABLE_KINDS,
    kindFor: (item) => (item as AttentionItem).kind,
    keyFor: (item) => item.id,
    eventFor: (raw) => {
      const item = raw as AttentionItem;
      return {
        key: item.id,
        body: bodyOf(item.title, item.detail),
        conversation_id: conversationOf(item.action?.to),
      };
    },
  });
}

/**
 * Work that finished cleanly (engine CLOSED + VERIFIED) → events, same first-snapshot and
 * cooldown discipline. The caller feeds only cleanly-finished jobs; failures/reviews notify
 * through the attention path above.
 */
export function diffFinishedEvents(
  state: AttentionNotificationState,
  finished: FinishedWork[],
  now: number
): { state: AttentionNotificationState; events: AttentionEvent[] } {
  return diffOne(
    state,
    finished,
    now,
    {
      keyFor: (work) => `finished-${work.id}`,
      eventFor: (raw) => {
        const work = raw as FinishedWork;
        return { key: `finished-${work.id}`, body: bodyOf('Work finished', work.title), conversation_id: work.conversation_id };
      },
    }
  );
}
