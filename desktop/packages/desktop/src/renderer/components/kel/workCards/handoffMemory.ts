/**
 * FIX-0025: what the thread remembers about each hand-off across re-renders of its row. When a reply
 * finishes, the list can re-key the row and mount the card again; without this it flashed "Getting
 * started…" (a taller card) for a frame and replayed the line's reveal, jolting the thread.
 * No dependencies, so the test setup can clear it between tests.
 */
import type { KelHandoff } from '../kelApi';

/** The last state each hand-off (by submission id) showed. */
export const lastHandoffViews = new Map<string, KelHandoff>();

/** Hand-offs whose in-thread line has already revealed. */
export const revealedHandoffLines = new Set<string>();

export const resetHandoffMemory = (): void => {
  lastHandoffViews.clear();
  revealedHandoffLines.clear();
};
