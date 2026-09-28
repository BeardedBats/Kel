/**
 * Motion language stage 2 — the spring solver and its CSS forms (MOTION.md §1–§2).
 *
 * The presets must be exactly the approved table, the closed form must be a real solution (its
 * velocity is its derivative, and it is continuous through a retarget), and the generated `linear()`
 * string must be the one the proposal printed. Springs run on a manual clock here.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  SPRINGS,
  Spring,
  solveSpring,
  springFromDuration,
  springOvershoot,
  springSettleTime,
} from '@renderer/motion/spring';
import { cssSprings, springToCss, staggerDelay } from '@renderer/motion/easing';
import { createManualScheduler, setFrameScheduler } from '@renderer/motion/frameLoop';

const TABLE = {
  micro: { k: 815.7, c: 51.41, zeta: 0.9, overshoot: 0.15, settle: 229 },
  snappy: { k: 341.5, c: 30.31, zeta: 0.82, overshoot: 1.1, settle: 450 },
  morph: { k: 171.3, c: 22.25, zeta: 0.85, overshoot: 0.6, settle: 617 },
  gentle: { k: 102.7, c: 18.24, zeta: 0.9, overshoot: 0.15, settle: 642 },
} as const;

describe('spring presets', () => {
  for (const [name, row] of Object.entries(TABLE)) {
    it(`${name} matches the approved table`, () => {
      const preset = SPRINGS[name as keyof typeof SPRINGS];
      expect(preset.stiffness).toBeCloseTo(row.k, 1);
      expect(preset.damping).toBeCloseTo(row.c, 2);
      expect(preset.zeta).toBeCloseTo(row.zeta, 5);
      expect(springOvershoot(preset) * 100).toBeCloseTo(row.overshoot, 1);
      expect(preset.settleMs).toBe(row.settle);
      // The solver's own settle time agrees with the table to within a few ms.
      expect(Math.abs(springSettleTime(preset) * 1000 - row.settle)).toBeLessThan(5);
    });
  }

  it('never overshoots more than about 1%', () => {
    for (const preset of Object.values(SPRINGS)) expect(springOvershoot(preset)).toBeLessThan(0.012);
  });
});

describe('closed-form solver', () => {
  const presets = {
    under: SPRINGS.snappy,
    critical: springFromDuration(0.3, 0),
    over: { stiffness: 300, damping: 60 },
  };

  for (const [kind, preset] of Object.entries(presets)) {
    it(`${kind}-damped: starts where asked, ends on target, velocity is the derivative`, () => {
      const solve = solveSpring(preset, 10, 110, 250);
      expect(solve(0).value).toBeCloseTo(10, 9);
      expect(solve(0).velocity).toBeCloseTo(250, 9);
      expect(solve(3).value).toBeCloseTo(110, 3);
      for (const t of [0.01, 0.05, 0.1, 0.2, 0.4]) {
        const h = 1e-6;
        const numeric = (solve(t + h).value - solve(t - h).value) / (2 * h);
        expect(solve(t).velocity).toBeCloseTo(numeric, 2);
      }
    });
  }
});

describe('CSS forms', () => {
  it('reproduces the snappy linear() string printed in MOTION.md §1', () => {
    expect(springToCss(SPRINGS.snappy)).toEqual({
      easing:
        'linear(0, 0.1015 6.3%, 0.3045 12.5%, 0.5147 18.8%, 0.6906 25%, 0.8206 31.3%, 0.9079 37.5%, ' +
        '0.9615 43.8%, 0.9912 50%, 1.0055 56.3%, 1.0105 62.5%, 1.0108 68.8%, 1.0090 75%, 1.0067 81.3%, ' +
        '1.0045 87.5%, 1.0027 93.8%, 1)',
      durationMs: 450,
    });
  });

  it('generates all four presets', () => {
    const css = cssSprings();
    expect(Object.keys(css)).toEqual(['micro', 'snappy', 'morph', 'gentle']);
    for (const value of Object.values(css)) expect(value.easing).toMatch(/^linear\(0, .*, 1\)$/);
  });

  it('caps a stagger at 200 ms in total', () => {
    expect(staggerDelay(0, 3)).toBe(0);
    expect(staggerDelay(2, 3)).toBe(60);
    expect(staggerDelay(19, 20)).toBeLessThanOrEqual(200);
  });
});

describe('Spring on the shared frame loop', () => {
  let clock: ReturnType<typeof createManualScheduler>;

  beforeEach(() => {
    clock = createManualScheduler();
    setFrameScheduler(clock);
  });
  afterEach(() => setFrameScheduler());

  it('moves toward the target, reports each frame, and comes to rest exactly on it', async () => {
    const seen: number[] = [];
    const spring = new Spring(0, { preset: 'snappy', onUpdate: (value) => seen.push(value) });
    spring.set(100);
    const settled = spring.settle();
    clock.advance(1000);
    await settled;
    expect(spring.isAnimating).toBe(false);
    expect(spring.value).toBe(100);
    expect(seen.length).toBeGreaterThan(10);
    expect(Math.max(...seen)).toBeLessThan(101.2);
  });

  it('retargets from the current position and velocity, never from rest', () => {
    const spring = new Spring(0, { preset: 'morph' });
    spring.set(100);
    clock.advance(96);
    const before = spring.state();
    expect(before.velocity).toBeGreaterThan(0);
    spring.set(-50);
    const after = spring.state();
    expect(after.value).toBeCloseTo(before.value, 9);
    expect(after.velocity).toBeCloseTo(before.velocity, 9);
  });

  it('applies a delayed target only when its time comes', () => {
    const spring = new Spring(0, { preset: 'micro' });
    spring.set(10, { delay: 33 });
    clock.advance(16);
    expect(spring.value).toBe(0);
    clock.advance(400);
    expect(spring.value).toBe(10);
  });

  it('shift moves the value and target together, keeping the motion', () => {
    const spring = new Spring(0, { preset: 'snappy' });
    spring.set(100);
    clock.advance(48);
    const before = spring.state();
    spring.shift(20);
    const after = spring.state();
    expect(after.value).toBeCloseTo(before.value + 20, 9);
    expect(after.velocity).toBeCloseTo(before.velocity, 9);
    expect(spring.goal).toBe(120);
  });

  it('jump puts the value in place with no motion', () => {
    const spring = new Spring(0, { preset: 'gentle' });
    spring.set(100);
    clock.advance(32);
    spring.jump(5);
    expect(spring.isAnimating).toBe(false);
    expect(spring.value).toBe(5);
  });
});
