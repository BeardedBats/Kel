/**
 * MOTION.md §4 — FLIP for in-flow siblings. The DOM takes its final layout in one pass; each sibling
 * then springs from where it was to where it is with transform only. Keyed to real ids, so polling
 * re-renders never replay; interrupted FLIPs re-seed from the current offset and velocity.
 */
import { useLayoutEffect, useRef, type RefObject } from 'react';
import { isReducedMotion } from './reduced';
import { frameWrite, spring, type PresetName, type SpringHandle } from './spring';

type Offset = { x: number; y: number; hx: SpringHandle | null; hy: SpringHandle | null };
const offsets = new WeakMap<HTMLElement, Offset>();

export type Point = { left: number; top: number };

const render = (el: HTMLElement, o: Offset) =>
  frameWrite(el, () => {
    el.style.transform = Math.abs(o.x) < 0.01 && Math.abs(o.y) < 0.01 ? '' : `translate(${o.x.toFixed(2)}px, ${o.y.toFixed(2)}px)`;
  });

/** Where elements are on screen now (their visual place, including any FLIP in flight). */
export const measure = (els: Iterable<HTMLElement>): Map<HTMLElement, Point> => {
  const out = new Map<HTMLElement, Point>();
  for (const el of els) {
    const r = el.getBoundingClientRect();
    out.set(el, { left: r.left, top: r.top });
  }
  return out;
};

/** Spring each element from its recorded place to its new layout place. Returns when all settle. */
export const playFlip = (
  before: Map<HTMLElement, Point>,
  preset: PresetName = 'snappy',
  opts: { delay?: number; axis?: 'x' | 'y' | 'both' } = {}
): Promise<void> => {
  const jobs: Promise<void>[] = [];
  const reduced = isReducedMotion();
  for (const [el, a] of before) {
    if (!el.isConnected) continue;
    const current = offsets.get(el);
    const r = el.getBoundingClientRect();
    // The layout place is the visual place minus the offset this helper wrote.
    const layoutLeft = r.left - (current?.x ?? 0);
    const layoutTop = r.top - (current?.y ?? 0);
    let dx = opts.axis === 'y' ? 0 : a.left - layoutLeft;
    let dy = opts.axis === 'x' ? 0 : a.top - layoutTop;
    if (reduced) {
      dx = 0;
      dy = 0;
    }
    if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5 && !current) continue;
    const vx = current?.hx && !current.hx.done ? current.hx.velocity : 0;
    const vy = current?.hy && !current.hy.done ? current.hy.velocity : 0;
    current?.hx?.stop();
    current?.hy?.stop();
    const o: Offset = { x: dx, y: dy, hx: null, hy: null };
    offsets.set(el, o);
    render(el, o);
    if (reduced || (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5)) {
      o.x = 0;
      o.y = 0;
      render(el, o);
      offsets.delete(el);
      continue;
    }
    o.hx = spring(dx, 0, preset, (v) => {
      o.x = v;
      render(el, o);
    }, { velocity: vx, delay: opts.delay, eps: 0.05 });
    o.hy = spring(dy, 0, preset, (v) => {
      o.y = v;
      render(el, o);
    }, { velocity: vy, delay: opts.delay, eps: 0.05 });
    jobs.push(
      Promise.all([o.hx.finished, o.hy.finished]).then(() => {
        if (offsets.get(el) === o) {
          offsets.delete(el);
          el.style.transform = '';
        }
      })
    );
  }
  return Promise.all(jobs).then((): void => undefined);
};

/** Record, mutate, then FLIP (for imperative code and tests). */
export const flip = (els: Iterable<HTMLElement>, mutate: () => void, preset: PresetName = 'snappy', opts: { delay?: number } = {}): Promise<void> => {
  const before = measure(els);
  mutate();
  return playFlip(before, preset, opts);
};

export type UseFlipOptions = {
  /** The children that move (default: direct children). */
  selector?: string;
  preset?: PresetName;
  axis?: 'x' | 'y' | 'both';
  /** Skip when this is false (e.g. the phone strip, which scrolls). */
  enabled?: boolean;
};

/**
 * Sibling FLIP keyed to a list's real identity (`key`, e.g. the ids joined). When the key changes the
 * hook reads where the children are during render, before React touches the DOM, and plays the FLIP
 * after commit. A key that changes because the window was resized snaps (§9): no FLIP when the
 * container's width changed.
 */
export const useFlip = (containerRef: RefObject<HTMLElement | null>, key: string, opts: UseFlipOptions = {}): void => {
  const committed = useRef<string | null>(null);
  const pending = useRef<{ key: string; width: number; before: Map<HTMLElement, Point> } | null>(null);
  const enabled = opts.enabled !== false;

  const node = containerRef.current;
  if (enabled && node && committed.current !== null && key !== committed.current && pending.current?.key !== key) {
    const kids = Array.from(opts.selector ? node.querySelectorAll<HTMLElement>(opts.selector) : (node.children as HTMLCollectionOf<HTMLElement>));
    pending.current = { key, width: node.clientWidth, before: measure(kids) };
  }

  useLayoutEffect(() => {
    const first = committed.current === null;
    committed.current = key;
    const snap = pending.current;
    pending.current = null;
    if (first || !snap || snap.key !== key || !enabled) return;
    const container = containerRef.current;
    if (!container || Math.abs(container.clientWidth - snap.width) > 0.5) return;
    void playFlip(snap.before, opts.preset ?? 'snappy', { axis: opts.axis });
  }, [key, enabled]);
};

const glides = new WeakMap<HTMLElement, { y: number; h: SpringHandle | null }>();

/**
 * The thread follows new content (a sent message, Thinking, a reply streaming in, a done card): when
 * the list scrolls itself to the bottom by dy, the content is shown where it was and springs up by dy
 * instead of jumping — "earlier messages FLIP up" (§10.1). Consecutive follows retarget one spring.
 * Only for the list's own follow, never for Nick's scrolling.
 */
export const glide = (el: HTMLElement, dy: number, opts: { clip?: HTMLElement | null } = {}): void => {
  if (isReducedMotion() || Math.abs(dy) < 0.5) return;
  const st = glides.get(el) ?? { y: 0, h: null };
  glides.set(el, st);
  const velocity = st.h && !st.h.done ? st.h.velocity : 0;
  st.h?.stop();
  st.y += dy;
  // FIX-0025: a transform inside a scroll container adds to what it can scroll, and at the bottom the
  // browser then clamps the scroll as the glide shrinks — cancelling the glide and jolting the thread.
  // A clipping box between the two keeps the moving content out of the scroll range while it moves
  // (the newest lines are revealed from the bottom edge as the thread settles).
  const clip = opts.clip ?? null;
  const write = () =>
    frameWrite(el, () => {
      const moving = Math.abs(st.y) >= 0.05;
      el.style.transform = moving ? `translateY(${st.y.toFixed(2)}px)` : '';
      if (clip) clip.style.overflow = moving ? 'clip' : '';
    });
  write();
  // `gentle` (0.15% overshoot): a long glide of the whole thread must not bob at the end.
  st.h = spring(st.y, 0, 'gentle', (v) => {
    st.y = v;
    write();
  }, { velocity, eps: 0.05 });
};
