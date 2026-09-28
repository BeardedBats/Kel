/**
 * D-70 — one live view. The in-thread line, the done card's Details and the Needs-you surfaces all
 * open the SAME top card's panel instead of drawing a second copy of the work. They ask through a
 * window event; the work-card row answers it. A request made before the row is on screen (the
 * person was on Home and the chat is still opening) waits here until the row mounts and asks for it.
 */
export const OPEN_WORK_CARD_EVENT = 'kel:open-work-card';
export const REFRESH_WORK_CARDS_EVENT = 'kel:refresh-work-cards';

/** A request nobody took within this long is stale (the person moved on). */
export const PENDING_WORK_CARD_MS = 15000;

let pending: { job: string; at: number } | null = null;

/** Open this job's card panel at the top of the chat (now, or as soon as the row is there). */
export const openWorkCard = (job: string): void => {
  if (!job) return;
  pending = { job, at: Date.now() };
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(OPEN_WORK_CARD_EVENT, { detail: { job } }));
};

/** The row takes a waiting request once (null when none). */
export const takePendingWorkCard = (): string | null => {
  const taken = pending;
  pending = null;
  return taken && Date.now() - taken.at <= PENDING_WORK_CARD_MS ? taken.job : null;
};

/** Ask the row to read the engine again now (after Start, an answer, or an undo). */
export const refreshWorkCards = (): void => {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(REFRESH_WORK_CARDS_EVENT));
};
