/**
 * CH-11 — which chats have live background work (D-53 hand-offs), for the sidebar rows.
 *
 * One shared, light store for every row: a single `/api/state?conversation=*` read every
 * LIVE_WORK_POLL_MS while at least one row is mounted and the window is visible, plus instant
 * updates from the in-chat work cards (which already poll their own hand-off). Rows never poll on
 * their own. The words behind "working" / "waiting" come from the shared state table.
 */
import { useSyncExternalStore } from 'react';
import { KEL_ALL_CONVERSATIONS, kelState, type KelWorkJob } from './kelApi';
import { workWords } from './workLanguage';

export type LiveWork = 'working' | 'waiting';

export const LIVE_WORK_POLL_MS = 20_000;

let polled = new Map<string, LiveWork>();
/** engine conversation → hand-off submissions its cards report as still live. */
const cards = new Map<string, Set<string>>();
const listeners = new Set<() => void>();
let timer: ReturnType<typeof setInterval> | undefined;
let inFlight = false;

const emit = () => listeners.forEach((listener) => listener());

/** The live state of each conversation's jobs: waiting on a decision beats working. */
export function liveWorkByConversation(jobs: KelWorkJob[]): Map<string, LiveWork> {
  const out = new Map<string, LiveWork>();
  for (const job of jobs) {
    if (!job.conversation) continue;
    if (job.state === 'AWAITING_USER' || job.state === 'BLOCKED') {
      out.set(job.conversation, 'waiting');
    } else if (workWords(job).section === 'now' && out.get(job.conversation) !== 'waiting') {
      out.set(job.conversation, 'working');
    }
  }
  return out;
}

const same = (a: Map<string, LiveWork>, b: Map<string, LiveWork>): boolean =>
  a.size === b.size && [...a].every(([key, value]) => b.get(key) === value);

export async function refreshLiveWork(): Promise<void> {
  if (inFlight) return;
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
  inFlight = true;
  try {
    const state = await kelState(KEL_ALL_CONVERSATIONS);
    const next = liveWorkByConversation(state.jobs ?? []);
    if (!same(next, polled)) {
      polled = next;
      emit();
    }
  } catch {
    // Honest silence: a failed read never invents or clears a "working" mark on its own.
  } finally {
    inFlight = false;
  }
}

/** Called by an in-chat work card each time it reads its hand-off. */
export function announceHandoffLive(conversation: string, submission: string, live: boolean): void {
  const set = cards.get(conversation) ?? new Set<string>();
  const had = set.has(submission);
  if (live) set.add(submission);
  else set.delete(submission);
  if (set.size) cards.set(conversation, set);
  else cards.delete(conversation);
  if (had !== live) {
    // A hand-off that just settled makes the last poll's "working" mark stale; drop it now (the
    // next poll restores it if other work in that chat is still going).
    if (!live && polled.get(conversation) === 'working') {
      polled = new Map(polled);
      polled.delete(conversation);
    }
    emit();
  }
}

export function liveWorkFor(conversation: string | undefined): LiveWork | null {
  if (!conversation) return null;
  const fromPoll = polled.get(conversation) ?? null;
  if (fromPoll === 'waiting') return 'waiting';
  if (cards.get(conversation)?.size) return 'working';
  return fromPoll;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (listeners.size === 1) {
    void refreshLiveWork();
    timer = setInterval(() => void refreshLiveWork(), LIVE_WORK_POLL_MS);
  }
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && timer) {
      clearInterval(timer);
      timer = undefined;
    }
  };
}

/** Test seam: forget everything the store knows. */
export function resetLiveWork(): void {
  polled = new Map();
  cards.clear();
  emit();
}

/** Live background work for one engine conversation id (null when there is none). */
export function useKelLiveWork(conversation: string | undefined): LiveWork | null {
  return useSyncExternalStore(
    subscribe,
    () => liveWorkFor(conversation),
    (): LiveWork | null => null
  );
}
