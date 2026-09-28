/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * CSS forms of the springs, for work CSS must do itself (hover, :active, aria-* state), and the timed
 * tweens for opacity and blur (MOTION.md §1–§2). The `linear()` strings are generated here and never
 * typed by hand.
 */

import { SPRINGS, solveSpring, type SpringName, type SpringPreset } from './spring';

export type CssSpring = { easing: string; durationMs: number };

function formatNumber(value: number, digits: number): string {
  return value.toFixed(digits).replace(/\.?0+$/, '') || '0';
}

/** A CSS `linear()` easing sampled from the closed form at `points` intervals, plus its duration. */
export function springToCss(preset: SpringPreset, points = 16): CssSpring {
  const durationMs = preset.settleMs;
  const solve = solveSpring(preset, 0, 1, 0);
  const stops = ['0'];
  for (let i = 1; i < points; i++) {
    const fraction = i / points;
    const value = solve((durationMs / 1000) * fraction).value;
    stops.push(`${value.toFixed(4)} ${formatNumber(fraction * 100, 1)}%`);
  }
  stops.push('1');
  return { easing: `linear(${stops.join(', ')})`, durationMs };
}

export const SPRING_NAMES = Object.keys(SPRINGS) as SpringName[];

export function cssSprings(): Record<SpringName, CssSpring> {
  return Object.fromEntries(SPRING_NAMES.map((name) => [name, springToCss(SPRINGS[name])])) as Record<
    SpringName,
    CssSpring
  >;
}

/**
 * Write `--kel-spring-{name}` (the easing) and `--kel-spring-{name}-ms` (the duration) on the root
 * once at startup, so CSS can write `transition: transform var(--kel-spring-snappy-ms) var(--kel-spring-snappy)`.
 */
export function installSpringProperties(
  root: HTMLElement | null = typeof document !== 'undefined' ? document.documentElement : null
): void {
  if (!root) return;
  for (const [name, css] of Object.entries(cssSprings())) {
    root.style.setProperty(`--kel-spring-${name}`, css.easing);
    root.style.setProperty(`--kel-spring-${name}-ms`, `${css.durationMs}ms`);
  }
}

/** Timed tweens (MOTION.md §2). Opacity and blur never ride springs: a fade cannot overshoot. */
export const TWEEN = {
  easeIn: 'cubic-bezier(0.32, 0, 0.67, 0)',
  easeOut: 'cubic-bezier(0.33, 1, 0.68, 1)',
  exitMs: 120,
  enterMs: 200,
  enterDelayMs: 130,
  staggerMs: 30,
  staggerCapMs: 200,
  surfaceColorMs: 240,
  surfaceColorDelayMs: 30,
  reducedOutMs: 100,
  reducedInMs: 150,
  reducedInDelayMs: 60,
  indicatorBlinkOutMs: 70,
  indicatorBlinkInMs: 110,
} as const;

/** Delay for the `index`-th sibling in a stagger, capped so the whole stagger stays under 200 ms. */
export function staggerDelay(index: number, count: number, step: number = TWEEN.staggerMs): number {
  if (count <= 1) return 0;
  const each = Math.min(step, TWEEN.staggerCapMs / (count - 1));
  return Math.round(index * each);
}
