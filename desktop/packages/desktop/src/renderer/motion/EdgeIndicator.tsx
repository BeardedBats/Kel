/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * An indicator with two edges on two springs (MOTION.md §6). The edge toward the new place leads on
 * `micro`; the trailing edge follows on `snappy` about 33 ms later, so the indicator stretches and
 * the tail catches up. One element spans the track and is clipped with `clip-path`, so it is the only
 * highlight: nothing else fades. Under reduced motion it blinks across (out 70 ms, in 110 ms).
 *
 * The track must be positioned; the indicator fills it (`position: absolute; inset: 0`).
 */

import React, { useEffect, useLayoutEffect, useRef } from 'react';

import { TWEEN } from './easing';
import { prefersReducedMotion } from './reducedMotion';
import { Spring } from './spring';

const TRAIL_DELAY_MS = 33;

export type EdgeIndicatorProps = {
  /** Offset of the selected item's near edge from the track's start, in px. Null hides it. */
  start: number | null;
  /** Offset of the selected item's far edge from the track's start, in px. */
  end: number | null;
  axis?: 'x' | 'y';
  radius?: number;
  className?: string;
  style?: React.CSSProperties;
};

export function edgeClipPath(axis: 'x' | 'y', start: number, end: number, radius: number): string {
  const round = radius > 0 ? ` round ${radius}px` : '';
  return axis === 'x'
    ? `inset(0 calc(100% - ${end}px) 0 ${start}px${round})`
    : `inset(${start}px 0 calc(100% - ${end}px) 0${round})`;
}

export const EdgeIndicator: React.FC<EdgeIndicatorProps> = ({
  start,
  end,
  axis = 'x',
  radius = 0,
  className,
  style,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const edges = useRef<{ start: Spring; end: Spring } | null>(null);
  const shown = useRef(false);

  const paint = () => {
    const el = ref.current;
    const springs = edges.current;
    if (!el || !springs) return;
    el.style.clipPath = edgeClipPath(axis, springs.start.value, springs.end.value, radius);
  };
  const paintRef = useRef(paint);
  paintRef.current = paint;

  if (!edges.current) {
    edges.current = {
      start: new Spring(start ?? 0, { preset: 'snappy', onUpdate: () => paintRef.current() }),
      end: new Spring(end ?? 0, { preset: 'snappy', onUpdate: () => paintRef.current() }),
    };
  }

  useLayoutEffect(() => {
    const el = ref.current;
    const springs = edges.current;
    if (!el || !springs) return;
    if (start === null || end === null) {
      el.style.visibility = 'hidden';
      shown.current = false;
      return;
    }
    el.style.visibility = '';
    // First appearance: no motion on first paint (MOTION.md §9).
    if (!shown.current) {
      shown.current = true;
      springs.start.jump(start);
      springs.end.jump(end);
      paint();
      return;
    }
    if (springs.start.goal === start && springs.end.goal === end) return;
    if (prefersReducedMotion()) {
      blink(el, () => {
        springs.start.jump(start);
        springs.end.jump(end);
      });
      return;
    }
    const forward = start + end >= springs.start.goal + springs.end.goal;
    const [lead, trail, leadTo, trailTo] = forward
      ? [springs.end, springs.start, end, start]
      : [springs.start, springs.end, start, end];
    lead.set(leadTo, { preset: 'micro' });
    trail.set(trailTo, { preset: 'snappy', delay: TRAIL_DELAY_MS });
    // paint is a stable writer over refs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start, end, axis, radius]);

  useEffect(
    () => () => {
      edges.current?.start.stop();
      edges.current?.end.stop();
    },
    []
  );

  return (
    <div
      ref={ref}
      aria-hidden
      className={className}
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none', ...style }}
    />
  );
};

function blink(el: HTMLElement, move: () => void): void {
  if (typeof el.animate !== 'function') {
    move();
    return;
  }
  const out = el.animate([{ opacity: 1 }, { opacity: 0 }], {
    duration: TWEEN.indicatorBlinkOutMs,
    easing: 'linear',
    fill: 'forwards',
  });
  void out.finished
    .catch((): void => undefined)
    .then(() => {
      move();
      out.cancel();
      el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: TWEEN.indicatorBlinkInMs, easing: 'linear' });
    });
}

export default EdgeIndicator;
