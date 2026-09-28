/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * The one requestAnimationFrame loop that drives every spring (MOTION.md §8). Callbacks only write;
 * nothing in a frame reads layout. The scheduler is swappable so tests can step time by hand.
 */

export type FrameCallback = (now: number) => boolean;

export type FrameScheduler = {
  now: () => number;
  request: (run: () => void) => unknown;
  cancel: (handle: unknown) => void;
};

function browserScheduler(): FrameScheduler {
  const hasRaf = typeof requestAnimationFrame === 'function';
  return {
    now: () => (typeof performance !== 'undefined' ? performance.now() : Date.now()),
    request: (run) => (hasRaf ? requestAnimationFrame(() => run()) : setTimeout(run, 16)),
    cancel: (handle) =>
      hasRaf ? cancelAnimationFrame(handle as number) : clearTimeout(handle as ReturnType<typeof setTimeout>),
  };
}

let scheduler: FrameScheduler = browserScheduler();
const callbacks = new Set<FrameCallback>();
let handle: unknown = null;

function runFrame(): void {
  handle = null;
  const now = scheduler.now();
  for (const callback of Array.from(callbacks)) {
    if (!callbacks.has(callback)) continue;
    if (!callback(now)) callbacks.delete(callback);
  }
  if (callbacks.size > 0) handle = scheduler.request(runFrame);
}

/** Run `callback` every frame until it returns false or the returned stop function is called. */
export function onFrame(callback: FrameCallback): () => void {
  callbacks.add(callback);
  if (handle === null) handle = scheduler.request(runFrame);
  return () => {
    callbacks.delete(callback);
    if (callbacks.size === 0 && handle !== null) {
      scheduler.cancel(handle);
      handle = null;
    }
  };
}

export function frameNow(): number {
  return scheduler.now();
}

/** Tests only: replace the clock and frame source. Pass nothing to restore the browser's. */
export function setFrameScheduler(next?: FrameScheduler): void {
  if (handle !== null) scheduler.cancel(handle);
  handle = null;
  callbacks.clear();
  scheduler = next ?? browserScheduler();
}

/** Tests only: a manual clock. `advance(ms)` runs frames 16 ms apart up to the new time. */
export function createManualScheduler(): FrameScheduler & { advance: (ms: number) => void; time: number } {
  let queued: Array<{ id: number; run: () => void }> = [];
  let nextId = 1;
  const manual = {
    time: 0,
    now: () => manual.time,
    request: (fn: () => void) => {
      const id = nextId++;
      queued.push({ id, run: fn });
      return id;
    },
    cancel: (id: unknown) => {
      queued = queued.filter((entry) => entry.id !== id);
    },
    advance: (ms: number) => {
      const end = manual.time + ms;
      while (manual.time < end) {
        manual.time = Math.min(end, manual.time + 16);
        const due = queued;
        queued = [];
        for (const entry of due) entry.run();
      }
    },
  };
  return manual;
}
