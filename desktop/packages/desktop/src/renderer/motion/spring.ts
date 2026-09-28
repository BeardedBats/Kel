/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Closed-form damped springs (MOTION.md §1).
 *
 * A value at time t comes from a formula, not from stepping frame by frame, so it is exact, frame-rate
 * independent and interruptible. Retargeting re-seeds from the current position and velocity.
 */

import { onFrame, frameNow } from './frameLoop';

export type SpringPreset = {
  /** Perceptual duration in seconds (the period of the undamped spring). */
  duration: number;
  /** 1 − damping ratio. 0 is critically damped. */
  bounce: number;
  stiffness: number;
  damping: number;
  /** Damping ratio ζ. */
  zeta: number;
  /** Time to settle within 0.2%, in ms: the duration CSS uses for this spring's `linear()` form. */
  settleMs: number;
};

export function springFromDuration(duration: number, bounce: number, settleMs?: number): SpringPreset {
  const stiffness = ((2 * Math.PI) / duration) ** 2;
  const zeta = 1 - bounce;
  const preset = { duration, bounce, stiffness, damping: 2 * zeta * Math.sqrt(stiffness), zeta, settleMs: 0 };
  preset.settleMs = settleMs ?? Math.ceil(springSettleTime(preset) * 1000);
  return preset;
}

/** The approved presets (MOTION.md §1). Settle times are the table's, which the CSS strings use. */
export const SPRINGS = {
  /** Press, hover, check and icon swaps, the leading edge of indicators. */
  micro: springFromDuration(0.22, 0.1, 229),
  /** Indicators, chips, menus, rows, sibling FLIPs, label rolls. */
  snappy: springFromDuration(0.34, 0.18, 450),
  /** Shared-element morphs. */
  morph: springFromDuration(0.48, 0.15, 617),
  /** Long travel: the hand-off flight, sidebar list shifts. */
  gentle: springFromDuration(0.62, 0.1, 642),
} as const;

export type SpringName = keyof typeof SPRINGS;

export type SpringState = { value: number; velocity: number };

/**
 * Solve one spring segment. Returns position and velocity (units per second) at `t` seconds after
 * the segment started from `from` with `velocity`, heading to `to`. Mass is 1.
 */
export function solveSpring(
  preset: Pick<SpringPreset, 'stiffness' | 'damping'>,
  from: number,
  to: number,
  velocity = 0
): (t: number) => SpringState {
  const x0 = from - to;
  const v0 = velocity;
  const w = Math.sqrt(preset.stiffness);
  const zeta = preset.damping / (2 * w);

  if (zeta < 1) {
    const wd = w * Math.sqrt(1 - zeta * zeta);
    const b = (v0 + zeta * w * x0) / wd;
    return (t) => {
      const decay = Math.exp(-zeta * w * t);
      const cos = Math.cos(wd * t);
      const sin = Math.sin(wd * t);
      return {
        value: to + decay * (x0 * cos + b * sin),
        velocity: decay * (v0 * cos - ((zeta * w * v0 + w * w * x0) / wd) * sin),
      };
    };
  }
  if (zeta === 1) {
    const b = v0 + w * x0;
    return (t) => {
      const decay = Math.exp(-w * t);
      return { value: to + (x0 + b * t) * decay, velocity: (v0 - w * b * t) * decay };
    };
  }
  const root = w * Math.sqrt(zeta * zeta - 1);
  const r1 = -zeta * w + root;
  const r2 = -zeta * w - root;
  const a = (v0 - r2 * x0) / (r1 - r2);
  const c = x0 - a;
  return (t) => {
    const e1 = Math.exp(r1 * t);
    const e2 = Math.exp(r2 * t);
    return { value: to + a * e1 + c * e2, velocity: a * r1 * e1 + c * r2 * e2 };
  };
}

/** Peak overshoot past the target for a move from rest, as a fraction of the distance. */
export function springOvershoot(preset: SpringPreset): number {
  if (preset.zeta >= 1) return 0;
  return Math.exp((-Math.PI * preset.zeta) / Math.sqrt(1 - preset.zeta * preset.zeta));
}

/**
 * Time in seconds after which a move from rest stays within `precision` of the distance, in both
 * position and velocity (velocity scaled by the natural frequency). 0.2% by default, the "Settles"
 * column of MOTION.md §1.
 */
export function springSettleTime(preset: Pick<SpringPreset, 'stiffness' | 'damping'>, precision = 0.002): number {
  const solve = solveSpring(preset, 1, 0, 0);
  const w = Math.sqrt(preset.stiffness);
  const step = 0.0005;
  const limit = 10;
  let last = 0;
  for (let t = 0; t <= limit; t += step) {
    const { value, velocity } = solve(t);
    if (Math.abs(value) > precision || Math.abs(velocity) / w > precision) last = t;
  }
  return last + step;
}

/** Below these the spring is at rest and snaps to its target. */
const REST_DISTANCE = 0.005;
const REST_VELOCITY = 0.5;

export type SpringOptions = {
  preset: SpringPreset | SpringName;
  onUpdate?: (value: number, velocity: number) => void;
  onRest?: (value: number) => void;
};

type Segment = { start: number; target: number; solve: (t: number) => SpringState };
type Pending = { at: number; target: number };

/**
 * An animated value. `set` retargets from the current position and velocity; nothing restarts
 * from rest. Every Spring shares the one requestAnimationFrame loop (MOTION.md §8).
 */
export class Spring {
  private preset: SpringPreset;
  private segment: Segment | null = null;
  private pending: Pending | null = null;
  private resting: SpringState;
  private target: number;
  private stopFrame: (() => void) | null = null;
  private waiters: Array<() => void> = [];
  private readonly onUpdate?: SpringOptions['onUpdate'];
  private readonly onRest?: SpringOptions['onRest'];

  constructor(initial: number, options: SpringOptions) {
    this.preset = typeof options.preset === 'string' ? SPRINGS[options.preset] : options.preset;
    this.onUpdate = options.onUpdate;
    this.onRest = options.onRest;
    this.resting = { value: initial, velocity: 0 };
    this.target = initial;
  }

  /** Current position and velocity, computed for this instant. */
  state(now = frameNow()): SpringState {
    if (!this.segment) return this.resting;
    return this.segment.solve((now - this.segment.start) / 1000);
  }

  get value(): number {
    return this.state().value;
  }

  get goal(): number {
    return this.pending ? this.pending.target : this.target;
  }

  get isAnimating(): boolean {
    return this.segment !== null || this.pending !== null;
  }

  /** Head for `target`, optionally after `delay` ms. Carries the current velocity. */
  set(target: number, options: { delay?: number; preset?: SpringPreset | SpringName } = {}): void {
    if (options.preset) {
      this.preset = typeof options.preset === 'string' ? SPRINGS[options.preset] : options.preset;
    }
    const now = frameNow();
    if (options.delay && options.delay > 0) {
      this.pending = { at: now + options.delay, target };
      this.ensureRunning();
      return;
    }
    this.pending = null;
    this.retarget(target, now);
  }

  /** Put the value at `value` at once, with no velocity, and stop. */
  jump(value: number): void {
    this.pending = null;
    this.segment = null;
    this.target = value;
    this.resting = { value, velocity: 0 };
    this.halt();
    this.onUpdate?.(value, 0);
    this.flushWaiters();
  }

  /**
   * Move the value, its target and any motion in flight by `offset`, keeping the velocity. FLIP uses
   * this when layout moves the element under an in-flight transform.
   */
  shift(offset: number): void {
    if (offset === 0) return;
    const now = frameNow();
    const current = this.state(now);
    this.target += offset;
    if (this.pending) this.pending = { ...this.pending, target: this.pending.target + offset };
    if (!this.segment) {
      this.resting = { value: current.value + offset, velocity: 0 };
      return;
    }
    this.segment = {
      start: now,
      target: this.target,
      solve: solveSpring(this.preset, current.value + offset, this.target, current.velocity),
    };
  }

  /** Stop where it is now. */
  stop(): void {
    const current = this.state();
    this.pending = null;
    this.segment = null;
    this.target = current.value;
    this.resting = { value: current.value, velocity: 0 };
    this.halt();
    this.flushWaiters();
  }

  /** Resolves when the spring is at rest. */
  settle(): Promise<void> {
    if (!this.isAnimating) return Promise.resolve();
    return new Promise((resolve) => this.waiters.push(resolve));
  }

  private retarget(target: number, now: number): void {
    const current = this.state(now);
    this.target = target;
    if (Math.abs(current.value - target) < REST_DISTANCE && Math.abs(current.velocity) < REST_VELOCITY) {
      this.segment = null;
      this.resting = { value: target, velocity: 0 };
      this.onUpdate?.(target, 0);
      if (!this.pending) {
        this.halt();
        this.flushWaiters();
      }
      return;
    }
    this.segment = { start: now, target, solve: solveSpring(this.preset, current.value, target, current.velocity) };
    this.ensureRunning();
  }

  private ensureRunning(): void {
    if (!this.stopFrame) this.stopFrame = onFrame((now) => this.tick(now));
  }

  private tick(now: number): boolean {
    if (this.pending && now >= this.pending.at) {
      const { target } = this.pending;
      this.pending = null;
      this.retarget(target, now);
    }
    if (!this.segment) return this.pending !== null;
    const current = this.state(now);
    if (Math.abs(current.value - this.target) < REST_DISTANCE && Math.abs(current.velocity) < REST_VELOCITY) {
      this.segment = null;
      this.resting = { value: this.target, velocity: 0 };
      this.onUpdate?.(this.target, 0);
      if (this.pending) return true;
      this.stopFrame = null;
      this.onRest?.(this.target);
      this.flushWaiters();
      return false;
    }
    this.onUpdate?.(current.value, current.velocity);
    return true;
  }

  private halt(): void {
    this.stopFrame?.();
    this.stopFrame = null;
  }

  private flushWaiters(): void {
    const waiters = this.waiters;
    this.waiters = [];
    for (const resolve of waiters) resolve();
  }
}
