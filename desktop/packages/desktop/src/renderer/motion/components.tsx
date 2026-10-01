/**
 * React pieces of the motion language. Each keeps the rule "final layout first": the new state is
 * laid out from the first frame and only its look animates (opacity, blur, transform, clip-path).
 * Old words and old icons leave from the same slot they occupied; nothing moves between rows and
 * nothing re-lays out after the motion settles. Motion is keyed to real value changes, never to
 * re-renders, and never plays on first paint.
 */
import React, { useLayoutEffect, useRef } from 'react';
import { drawOn, enter, exit, prepareEnter, settleIn, turnOnce } from './fx';
import { measure, playFlip, type Point } from './flip';
import { ghostOf } from './morph';
import { useEdgeIndicator } from './indicator';
import { isReducedMotion } from './reduced';
import { frameWrite, spring, type SpringHandle } from './spring';
import { BLUR, MOTION } from './tokens';
import { animateString, type StringMotionHandle } from './stringMotion';
import { useReducedMotion } from './reduced';

/* ─────────────────────────────── label roll ─────────────────────────────── */

type RollProps = {
  value: React.ReactNode;
  /** A comparable identity for the value (defaults to the value when it is a string or number). */
  valueKey?: string | number;
  className?: string;
  /** The new words are a resting end state: arrive with the settling fade. */
  settle?: boolean;
  /** Roll direction: 1 = old up and out, new up from below. */
  dir?: 1 | -1;
  /** FLIP the following siblings when the width changes (default on). */
  flipSiblings?: boolean;
  testId?: string;
  as?: 'span' | 'div';
};

const followingSiblings = (el: HTMLElement): HTMLElement[] => {
  const out: HTMLElement[] = [];
  let next = el.nextElementSibling;
  while (next) {
    out.push(next as HTMLElement);
    next = next.nextElementSibling;
  }
  return out;
};

/**
 * Label swaps roll (§4): the old words leave upward and the new ones arrive from below (7 px, blur
 * 3 px) in the same slot, which already has the new width; neighbours FLIP to their new places.
 */
export const RollText: React.FC<RollProps> = ({ value, valueKey, className, settle = false, dir = 1, flipSiblings = true, testId, as = 'span' }) => {
  const reducedPreference = useReducedMotion();
  const strings = useRef<StringMotionHandle[]>([]);
  const oldCopies = useRef<HTMLElement[]>([]);
  const key = valueKey ?? (typeof value === 'string' || typeof value === 'number' ? value : null);
  const slotRef = useRef<HTMLElement>(null);
  const nowRef = useRef<HTMLElement>(null);
  const committed = useRef<{ key: unknown; ghost: HTMLElement | null } | null>(null);
  const pending = useRef<{ key: unknown; ghost: HTMLElement | null; siblings: Map<HTMLElement, Point> } | null>(null);

  const slot = slotRef.current;
  if (slot && committed.current && key !== committed.current.key && pending.current?.key !== key) {
    pending.current = {
      key,
      ghost: nowRef.current ? ghostOf(nowRef.current) : null,
      siblings: flipSiblings ? measure(followingSiblings(slot)) : new Map(),
    };
  }

  useLayoutEffect(() => {
    const first = committed.current === null;
    committed.current = { key, ghost: null };
    const snap = pending.current;
    pending.current = null;
    if (first || !snap || snap.key !== key) return;
    const host = slotRef.current;
    const now = nowRef.current;
    if (!host || !now) return;
    const reduced = isReducedMotion();
    strings.current.forEach((handle) => handle.stop());
    strings.current = [];
    oldCopies.current.forEach((copy) => copy.remove());
    oldCopies.current = [];
    const stringValue = typeof value === 'string' || typeof value === 'number';
    if (snap.ghost) {
      const ghost = snap.ghost;
      ghost.classList.remove('kel-roll__now');
      ghost.classList.add('kel-roll__old');
      host.appendChild(ghost);
      oldCopies.current.push(ghost);
      if (stringValue && !settle && !reduced) {
        const leaving = animateString(ghost, 0, ghost.textContent?.length ?? 0, 'exit');
        strings.current.push(leaving);
        void leaving.finished.then(() => ghost.remove());
      } else void exit(ghost, reduced ? {} : { y: -7 * dir, blur: BLUR.roll, ms: 130 }).then(() => ghost.remove());
    }
    if (settle) {
      prepareEnter(now, { y: 0, blur: MOTION.settleBlurPx });
      void settleIn(now, { delay: reduced ? 0 : 60 });
    } else if (stringValue && !reduced) {
      strings.current.push(animateString(now));
    } else {
      prepareEnter(now, { y: 7 * dir, blur: BLUR.roll });
      void enter(now, { y: 7 * dir, blur: BLUR.roll, ms: MOTION.rollMs, delay: 60 });
    }
    if (snap.siblings.size) void playFlip(snap.siblings, 'snappy', { axis: 'x' });
  }, [key]);

  useLayoutEffect(() => {
    if (reducedPreference) {
      strings.current.forEach((handle) => handle.stop());
      oldCopies.current.forEach((copy) => copy.remove());
    }
  }, [reducedPreference]);
  useLayoutEffect(() => () => {
    strings.current.forEach((handle) => handle.stop());
    oldCopies.current.forEach((copy) => copy.remove());
  }, []);

  const Tag = as;
  return (
    <Tag ref={slotRef as React.Ref<HTMLSpanElement & HTMLDivElement>} className={`kel-roll${className ? ` ${className}` : ''}`}>
      <span ref={nowRef} className='kel-roll__now' data-testid={testId}>
        {value}
      </span>
    </Tag>
  );
};

/* ─────────────────────────────── icon swap ─────────────────────────────── */

type SwapProps = {
  /** The icon's identity (e.g. the state). The swap plays when it changes. */
  swapKey: string;
  children: React.ReactNode;
  className?: string;
  /** Draw the new icon on (a check). */
  draw?: boolean;
  /** Turn the new icon once (a step's loader when the step starts). */
  turn?: boolean;
  /** The new icon is a resting end state (the done check): settle rather than pop. */
  settle?: boolean;
  testId?: string;
};

/**
 * Icon swaps (§4): the old icon shrinks to 0.4 and blurs out in its own slot while the new one grows
 * from 0.5, draws on, or settles. The slot has a fixed size, so the row never re-lays out.
 */
export const SwapIn: React.FC<SwapProps> = ({ swapKey, children, className, draw = false, turn = false, settle = false, testId }) => {
  const slotRef = useRef<HTMLSpanElement>(null);
  const committed = useRef<string | null>(null);
  const pending = useRef<{ key: string; ghost: HTMLElement | null } | null>(null);

  const slot = slotRef.current;
  if (slot && committed.current !== null && swapKey !== committed.current && pending.current?.key !== swapKey) {
    const current = slot.querySelector(':scope > .kel-swap__now');
    pending.current = { key: swapKey, ghost: current ? ghostOf(current) : null };
  }

  useLayoutEffect(() => {
    const first = committed.current === null;
    committed.current = swapKey;
    const snap = pending.current;
    pending.current = null;
    const host = slotRef.current;
    if (first || !snap || !host) return;
    const now = host.querySelector<HTMLElement>(':scope > .kel-swap__now');
    const reduced = isReducedMotion();
    if (snap.ghost) {
      const ghost = snap.ghost;
      ghost.classList.remove('kel-swap__now');
      ghost.classList.add('kel-swap__old');
      host.appendChild(ghost);
      void exit(ghost, reduced ? {} : { y: 0, blur: 2, ms: 110, scale: 0.4 }).then(() => ghost.remove());
    }
    if (!now) return;
    const icon = (now.querySelector('img, svg') as HTMLElement | null) ?? now;
    if (draw) {
      if (settle) {
        prepareEnter(now, { y: 0, blur: MOTION.settleBlurPx });
        void settleIn(now, { delay: 40 });
      }
      void drawOn(icon, { delay: reduced ? 0 : 60 });
    } else if (settle) {
      prepareEnter(now, { y: 0, blur: MOTION.settleBlurPx });
      void settleIn(now, { delay: 40 });
    } else {
      prepareEnter(now, { y: 0, blur: 2, scale: 0.5 });
      void enter(now, { y: 0, blur: 2, ms: 160, scale: 0.5, delay: 40 });
    }
    if (turn) void turnOnce(icon, 360, 'gentle', 40);
  }, [swapKey]);

  return (
    <span ref={slotRef} className={`kel-swap${className ? ` ${className}` : ''}`} data-testid={testId} aria-hidden='true'>
      <span className='kel-swap__now'>{children}</span>
    </span>
  );
};

/* ─────────────────────────────── progress fill ─────────────────────────────── */

export type FillTone = 'working' | 'in_review' | 'needs_you' | 'done' | 'failed' | 'stopped' | 'uncertain' | 'scoping';

const TONE_VAR: Record<FillTone, string> = {
  working: 'var(--kel-wc-blue)',
  scoping: 'var(--kel-wc-blue)',
  in_review: 'var(--kel-wc-cyan)',
  needs_you: 'var(--kel-wc-amber)',
  uncertain: 'var(--kel-wc-amber)',
  done: 'var(--kel-wc-green)',
  failed: 'var(--kel-wc-red)',
  stopped: 'var(--kel-wc-grey)',
};

export const fillTone = (state: string, uncertain = false): FillTone =>
  uncertain && state === 'failed' ? 'uncertain' : ((TONE_VAR as Record<string, string>)[state] ? (state as FillTone) : 'working');

type FillProps = { fraction: number; tone: FillTone; className?: string; /** Animate the first paint from here (a card that just started). */ mountFrom?: number };

/**
 * A progress fill whose right edge follows on `gentle` while a brighter lead segment runs ahead on
 * `micro` and collapses into it (§6). A new state colour sweeps in from the left over the old one.
 * The fill's width is its final width from the first frame; only clip-path animates.
 */
export const ProgressFill: React.FC<FillProps> = ({ fraction, tone, className, mountFrom }) => {
  const fillRef = useRef<HTMLSpanElement>(null);
  const prev = useRef<{ fraction: number; tone: FillTone } | null>(mountFrom !== undefined ? { fraction: mountFrom, tone } : null);
  const shown = useRef<{ value: number; handle: SpringHandle | null }>({ value: mountFrom ?? fraction, handle: null });
  const clamped = Math.max(0, Math.min(1, fraction));
  const width = `${(clamped * 100).toFixed(2)}%`;

  useLayoutEffect(() => {
    const before = prev.current;
    prev.current = { fraction: clamped, tone };
    const fill = fillRef.current;
    if (!before || !fill) {
      shown.current.value = clamped;
      return;
    }
    const track = fill.parentElement;
    if (!track || isReducedMotion()) {
      shown.current.handle?.stop();
      shown.current.value = clamped;
      fill.style.clipPath = '';
      return;
    }
    const from = shown.current.value;
    const to = clamped;
    // Colour arrives by moving: the old colour is uncovered from the left by the new one.
    if (before.tone !== tone && from > 0.001) {
      const old = document.createElement('span');
      old.className = 'kel-progress-old';
      old.style.background = TONE_VAR[before.tone];
      old.style.width = `${(from * 100).toFixed(2)}%`;
      track.appendChild(old);
      void spring(0, 100, 'snappy', (v) => {
        frameWrite(old, () => {
          old.style.clipPath = `inset(0 0 0 ${v.toFixed(2)}% round 2px)`;
        });
      }, { eps: 0.1 }).finished.then(() => old.remove());
    }
    if (Math.abs(from - to) < 0.0005) return;
    const span = Math.max(from, to, 0.0001);
    fill.style.width = `${(span * 100).toFixed(2)}%`;
    const edge = (f: number) => `inset(0 ${Math.max(0, (1 - f / span) * 100).toFixed(3)}% 0 0 round 2px)`;
    fill.style.clipPath = edge(from);
    // The brighter lead segment, only while growing.
    let lead: HTMLSpanElement | null = null;
    const ls = { l: from, r: from };
    if (to > from) {
      lead = document.createElement('span');
      lead.className = 'kel-progress-lead';
      lead.style.background = TONE_VAR[tone];
      track.appendChild(lead);
      const drawLead = () =>
        frameWrite(lead, () => {
          if (!lead) return;
          lead.style.clipPath = `inset(0 ${Math.max(0, (1 - ls.r) * 100).toFixed(3)}% 0 ${(ls.l * 100).toFixed(3)}% round 2px)`;
        });
      drawLead();
      void spring(from, to, 'micro', (v) => {
        ls.r = v;
        drawLead();
      }, { eps: 0.0005 });
      const leadRef = lead;
      shown.current.handle?.stop();
      shown.current.handle = spring(from, to, 'gentle', (v) => {
        shown.current.value = v;
        ls.l = v;
        drawLead();
        frameWrite(fill, () => {
          fill.style.clipPath = edge(v);
        });
      }, { eps: 0.0005, delay: 40 });
      void shown.current.handle.finished.then(() => leadRef.remove());
    } else {
      shown.current.handle?.stop();
      shown.current.handle = spring(from, to, 'gentle', (v) => {
        shown.current.value = v;
        frameWrite(fill, () => {
          fill.style.clipPath = edge(v);
        });
      }, { eps: 0.0005 });
    }
    const mine = shown.current.handle;
    void mine.finished.then(() => {
      if (shown.current.handle !== mine) return;
      shown.current.value = to;
      fill.style.width = width;
      fill.style.clipPath = '';
    });
  }, [clamped, tone]);

  return <span ref={fillRef} className={`kel-wc-progress__fill${className ? ` ${className}` : ''}`} style={{ width }} />;
};

/* ─────────────────────────────── mount-once entrance ─────────────────────────────── */

/**
 * Plays an entrance on the elements matching `parts` inside `ref` when `play` is true at mount
 * (an arrival, not first paint). Use for things that appear while Nick watches.
 */
export const useEntrance = (
  ref: React.RefObject<HTMLElement | null>,
  play: boolean,
  opts: { parts?: string[]; stagger?: number; settle?: boolean; delay?: number; y?: number; blur?: number; x?: number; scale?: number } = {}
): void => {
  const done = useRef(false);
  useLayoutEffect(() => {
    if (done.current) return;
    done.current = true;
    const root = ref.current;
    if (!play || !root) return;
    const parts = opts.parts?.length ? opts.parts.flatMap((sel) => Array.from(root.querySelectorAll<HTMLElement>(sel))) : [root];
    if (opts.settle) {
      prepareEnter(parts, { y: 0, blur: MOTION.settleBlurPx });
      void settleIn(parts, { stagger: opts.stagger, delay: opts.delay });
    } else {
      prepareEnter(parts, { y: opts.y, blur: opts.blur, x: opts.x, scale: opts.scale });
      void enter(parts, { stagger: opts.stagger ?? MOTION.staggerMs, delay: opts.delay, y: opts.y, blur: opts.blur, x: opts.x, scale: opts.scale });
    }
  }, []);
};

/* ─────────────────────────────── stretching indicator ─────────────────────────────── */

type EdgePillProps = {
  /** The track (the pill's parent; position: relative). */
  containerRef: React.RefObject<HTMLElement | null>;
  /** Selects the selected row/tab inside the track. */
  active: string;
  /** The real selection (route, tab id): the pill moves only when this changes. */
  trigger: unknown;
  axis?: 'x' | 'y';
  className?: string;
  enabled?: boolean;
};

/** §6: the selection highlight as one element whose two edges ride two springs. */
export const EdgePill: React.FC<EdgePillProps> = ({ containerRef, active, trigger, axis = 'y', className, enabled = true }) => {
  const pillRef = useRef<HTMLSpanElement>(null);
  useEdgeIndicator(containerRef, pillRef, active, trigger, { axis, enabled });
  return <span ref={pillRef} className={`kel-edge-pill${className ? ` ${className}` : ''}`} aria-hidden='true' data-testid='kel-edge-pill' />;
};
