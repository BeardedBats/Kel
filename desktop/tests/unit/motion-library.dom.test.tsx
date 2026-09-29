/**
 * D-78 — the renderer motion library (docs/v2/design/MOTION.md §1–§8, §11): presets and their
 * linear() easings, retargeting that keeps velocity, reduced motion (cross-fades only), interruption,
 * FLIP, the stretching indicator, the settling-fade rule, the no-layout-shift probe, and that the
 * per-frame loop never reads layout.
 */
import React from 'react';
import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  PRESETS,
  ProgressFill,
  RollText,
  SETTLING_MOMENTS,
  SwapIn,
  cardStateTransition,
  classifyTransition,
  edgeIndicator,
  enter,
  exit,
  exitGhost,
  flip,
  layoutViolations,
  linearEasing,
  morph,
  LOOKS,
  motionClock,
  motionCustomProperties,
  overshoot,
  playFlip,
  settleIn,
  settleTime,
  setReducedMotionOverride,
  spring,
  stepTickTransition,
  MOTION,
  type ProbeFrame,
} from '@renderer/motion';

const rect = (x: number, y: number, w = 100, h = 20) =>
  ({ left: x, top: y, x, y, width: w, height: h, right: x + w, bottom: y + h, toJSON: () => ({}) }) as DOMRect;

beforeEach(() => {
  motionClock.setManual(true);
  setReducedMotionOverride(false);
});
afterEach(() => {
  motionClock.reset();
  motionClock.setManual(false);
  setReducedMotionOverride(null);
  cleanup();
  document.body.innerHTML = '';
});

describe('springs', () => {
  it('keeps every preset to the tiny overshoot Nick approved (0.15–1.1%)', () => {
    for (const name of Object.keys(PRESETS) as Array<keyof typeof PRESETS>) {
      expect(overshoot(name)).toBeLessThanOrEqual(0.0115);
      expect(overshoot(name)).toBeGreaterThan(0.001);
    }
    expect(overshoot('snappy')).toBeCloseTo(0.011, 3);
  });

  it('settles in the times MOTION.md lists', () => {
    expect(settleTime('micro', 0.002) * 1000).toBeCloseTo(229, -1);
    expect(settleTime('snappy', 0.002) * 1000).toBeCloseTo(450, -1);
    expect(settleTime('gentle', 0.002) * 1000).toBeCloseTo(642, -1);
  });

  it('exports CSS linear() easings and custom properties generated from the closed form', () => {
    const snappy = linearEasing('snappy');
    expect(snappy.easing.startsWith('linear(0, ')).toBe(true);
    expect(snappy.easing.endsWith(', 1)')).toBe(true);
    expect(snappy.duration).toBeGreaterThan(400);
    const props = motionCustomProperties();
    expect(props['--kel-spring-morph']).toMatch(/^linear\(/);
    expect(props['--kel-spring-gentle-ms']).toMatch(/^\d+ms$/);
    expect(props['--kel-settle-ms']).toBe(`${MOTION.settleMs}ms`);
  });

  it('reaches its target on the loop and never overshoots by more than ~1%', () => {
    const values: number[] = [];
    spring(0, 100, 'snappy', (v) => values.push(v));
    motionClock.advance(800);
    expect(values[values.length - 1]).toBe(100);
    expect(Math.max(...values)).toBeLessThan(101.2);
  });

  it('retargets mid-flight from its current position and velocity (no jump)', () => {
    const values: number[] = [];
    const h = spring(0, 100, 'morph', (v) => values.push(v));
    motionClock.advance(100);
    const before = h.value;
    const velocity = h.velocity;
    expect(velocity).toBeGreaterThan(0);
    h.retarget(-50);
    motionClock.advance(17);
    // One frame later it is still near where it was, still moving the old way (velocity kept).
    expect(Math.abs(h.value - before)).toBeLessThan(20);
    expect(h.value).toBeGreaterThan(before - 1);
    motionClock.advance(900);
    expect(h.value).toBe(-50);
  });
});

describe('enter, exit and the settling fade', () => {
  it('enters with opacity, blur and offset, and clears them at rest', async () => {
    const el = document.createElement('div');
    document.body.appendChild(el);
    const done = enter(el, { ms: 200 });
    motionClock.advance(50);
    expect(Number(el.style.opacity)).toBeGreaterThan(0);
    expect(el.style.filter).toMatch(/blur/);
    expect(el.style.transform).toMatch(/translate/);
    motionClock.advance(200);
    await done;
    expect(el.style.opacity).toBe('');
    expect(el.style.filter).toBe('');
    expect(el.style.transform).toBe('');
  });

  it('reduced motion: cross-fades only — nothing moves, scales or blurs', async () => {
    setReducedMotionOverride(true);
    const el = document.createElement('div');
    const seen: string[] = [];
    const done = enter(el, { ms: 200, scale: 0.5 });
    for (let i = 0; i < 10; i++) {
      motionClock.advance(16);
      seen.push(`${el.style.transform}|${el.style.filter}`);
    }
    await done;
    expect(seen.every((s) => s === '|')).toBe(true);
    const out = document.createElement('div');
    const leaving = exit(out, { scale: 0.9, y: -8 });
    motionClock.advance(50);
    expect(out.style.transform).toBe('');
    expect(out.style.filter).toBe('');
    motionClock.advance(100);
    await leaving;
    expect(Number(out.style.opacity)).toBe(0);
  });

  it('an interruption takes over from the current opacity (no jump back to 1 or 0)', () => {
    const el = document.createElement('div');
    void enter(el, { ms: 200 });
    motionClock.advance(100);
    const mid = Number(el.style.opacity);
    expect(mid).toBeGreaterThan(0.3);
    void exit(el, { ms: 120 });
    motionClock.advance(1);
    expect(Math.abs(Number(el.style.opacity) - mid)).toBeLessThan(0.1);
  });

  it('the settling fade is longer than a normal enter, and stays a gentle fade under reduced motion', async () => {
    const quick = document.createElement('div');
    const slow = document.createElement('div');
    void enter(quick, { ms: MOTION.enterMs });
    void settleIn(slow);
    motionClock.advance(250);
    expect(quick.style.opacity).toBe('');
    expect(Number(slow.style.opacity)).toBeLessThan(1);
    expect(slow.style.filter).toMatch(/blur/);
    motionClock.advance(400);
    expect(slow.style.opacity).toBe('');
    setReducedMotionOverride(true);
    const calm = document.createElement('div');
    void settleIn(calm);
    motionClock.advance(100);
    const o = Number(calm.style.opacity);
    expect(o).toBeGreaterThan(0);
    expect(o).toBeLessThan(1);
    expect(calm.style.filter).toBe('');
  });
});

describe('the settling-fade rule', () => {
  it('classifies only resting end states that stay more than 5 s as settling', () => {
    expect(classifyTransition({ final: true, staysMs: Infinity })).toBe('settling');
    expect(classifyTransition({ final: true, staysMs: 2600 })).toBe('quick');
    expect(classifyTransition({ final: false, staysMs: Infinity })).toBe('quick');
    expect(cardStateTransition('done')).toBe('settling');
    expect(cardStateTransition('failed')).toBe('settling');
    expect(cardStateTransition('stopped')).toBe('settling');
    expect(cardStateTransition('in_review')).toBe('quick');
    expect(stepTickTransition(4, 5)).toBe('settling');
    expect(stepTickTransition(2, 5)).toBe('quick');
    expect(classifyTransition(SETTLING_MOMENTS['You answered · Kel is continuing'])).toBe('settling');
    expect(classifyTransition(SETTLING_MOMENTS.toast)).toBe('quick');
  });
});

describe('FLIP and the loop', () => {
  it('springs siblings from their old place with transform only, and never reads layout per frame', async () => {
    const a = document.createElement('div');
    document.body.appendChild(a);
    let top = 0;
    a.getBoundingClientRect = () => rect(0, top);
    const done = flip([a], () => {
      top = 40;
    }, 'snappy');
    expect(a.style.transform).toBe('translate(0.00px, -40.00px)');
    const spy = vi.spyOn(a, 'getBoundingClientRect');
    const layoutSpy = vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get');
    motionClock.advance(600);
    await done;
    expect(spy).not.toHaveBeenCalled();
    expect(layoutSpy).not.toHaveBeenCalled();
    expect(a.style.transform).toBe('');
  });

  it('a second change mid-FLIP re-seeds from the current offset', () => {
    const a = document.createElement('div');
    document.body.appendChild(a);
    let top = 0;
    a.getBoundingClientRect = () => rect(0, top + (parseFloat(a.style.transform.split(',')[1] ?? '0') || 0));
    void flip([a], () => {
      top = 100;
    });
    motionClock.advance(80);
    const visual = a.getBoundingClientRect().top;
    const before = new Map([[a, { left: 0, top: visual }]]);
    top = 200;
    void playFlip(before);
    // The element has not jumped: its visual place is where it was.
    expect(Math.abs(a.getBoundingClientRect().top - visual)).toBeLessThan(0.5);
  });

  it('reduced motion skips FLIPs (siblings simply take their new places)', () => {
    setReducedMotionOverride(true);
    const a = document.createElement('div');
    let top = 0;
    a.getBoundingClientRect = () => rect(0, top);
    document.body.appendChild(a);
    void flip([a], () => {
      top = 50;
    });
    expect(a.style.transform).toBe('');
  });
});

describe('the stretching indicator', () => {
  it('leads with one edge and trails with the other, then lands exactly', async () => {
    const pill = document.createElement('div');
    const ind = edgeIndicator(pill, 'y');
    ind.place({ a: 0, b: 28, cross: 10, crossSize: 180 });
    expect(pill.style.transform).toBe('translate(10.00px, 0.00px)');
    const done = ind.to({ a: 96, b: 124, cross: 10, crossSize: 180 });
    motionClock.advance(60);
    // Moving down: the bottom edge (leading) is further along than the top edge.
    const { a, b } = ind.state;
    expect(b - 28).toBeGreaterThan(a - 0);
    expect(b - a).toBeGreaterThan(28);
    motionClock.advance(800);
    await done;
    expect(ind.state.a).toBe(96);
    expect(ind.state.b).toBe(124);
    expect(parseFloat(pill.style.height)).toBe(28);
  });

  it('blinks across under reduced motion', () => {
    setReducedMotionOverride(true);
    const pill = document.createElement('div');
    const ind = edgeIndicator(pill, 'x');
    ind.place({ a: 0, b: 60, cross: 0, crossSize: 28 });
    void ind.to({ a: 80, b: 140, cross: 0, crossSize: 28 });
    motionClock.advance(40);
    expect(ind.state.a).toBe(0);
    expect(Number(pill.style.opacity)).toBeLessThan(1);
  });
});

describe('the shared-element morph', () => {
  it('lands exactly on B and hands over (B shown on landing, surface removed)', async () => {
    const land = vi.fn();
    const handle = morph({
      from: { x: 10, y: 10, w: 198, h: 70 },
      to: { x: 10, y: 90, w: 900, h: 400 },
      fromLook: LOOKS.card,
      toLook: LOOKS.panel,
      presets: { h: 'gentle' },
      onLand: land,
    });
    const surface = document.querySelector<HTMLElement>('.kel-motion-surface')!;
    expect(parseFloat(surface.style.width)).toBe(198);
    motionClock.advance(120);
    expect(land).not.toHaveBeenCalled();
    motionClock.advance(900);
    await handle.finished;
    expect(land).toHaveBeenCalledTimes(1);
    expect(document.querySelector('.kel-motion-surface')).toBeNull();
  });

  it('under reduced motion hands over at once with no surface', () => {
    setReducedMotionOverride(true);
    const land = vi.fn();
    morph({ from: { x: 0, y: 0, w: 1, h: 1 }, to: { x: 0, y: 0, w: 2, h: 2 }, fromLook: LOOKS.card, toLook: LOOKS.panel, onLand: land });
    expect(land).toHaveBeenCalled();
    expect(document.querySelector('.kel-motion-surface')).toBeNull();
  });

  it('an exit ghost is inert and carries no test ids', async () => {
    const menu = document.createElement('div');
    menu.dataset.testid = 'menu';
    menu.innerHTML = '<button data-testid="row">Row</button>';
    document.body.appendChild(menu);
    menu.getBoundingClientRect = () => rect(0, 0, 200, 100);
    const done = exitGhost(menu);
    const ghost = document.querySelector<HTMLElement>('.kel-motion-exit')!;
    expect(ghost.hasAttribute('inert')).toBe(true);
    expect(ghost.querySelector('[data-testid]')).toBeNull();
    motionClock.advance(200);
    await done;
    expect(document.querySelector('.kel-motion-exit')).toBeNull();
  });
});

describe('popovers', () => {
  it('a popover’s rows enter, but its stretching pill keeps its own transform', async () => {
    const { popIn } = await import('@renderer/motion');
    const menu = document.createElement('div');
    menu.innerHTML = '<span class="kel-edge-pill" style="transform: translate(0px, 70px)"></span><button>A</button><button>B</button>';
    document.body.appendChild(menu);
    const pill = menu.querySelector<HTMLElement>('.kel-edge-pill')!;
    const done = popIn(menu, 'top left');
    motionClock.advance(30);
    expect(pill.style.transform).toBe('translate(0px, 70px)');
    expect(Number(menu.querySelector<HTMLElement>('button')!.style.opacity)).toBeLessThan(1);
    await motionClock.advanceAsync(800);
    await done;
    expect(pill.style.transform).toBe('translate(0px, 70px)');
  });
});

describe('React pieces keep the final layout first', () => {
  it('RollText shows the new words at once, rolls the old ones out of the same slot, and never replays on re-render', async () => {
    const { container, rerender, getByTestId } = render(<RollText value='Working' testId='label' />);
    expect(container.querySelector('.kel-roll__old')).toBeNull();
    rerender(<RollText value='Working' testId='label' />);
    expect(container.querySelector('.kel-roll__old')).toBeNull();
    rerender(<RollText value='In review' testId='label' />);
    expect(getByTestId('label').textContent).toBe('In review');
    const old = container.querySelector('.kel-roll__old');
    expect(old?.textContent).toBe('Working');
    expect(old?.getAttribute('aria-hidden')).toBe('true');
    await act(async () => {
      await motionClock.advanceAsync(700);
    });
    expect(container.querySelector('.kel-roll__old')).toBeNull();
  });

  it('SwapIn keeps the old icon in its own slot while the new one grows in', async () => {
    const { container, rerender } = render(
      <SwapIn swapKey='working'>
        <img alt='' src='dot.svg' />
      </SwapIn>
    );
    rerender(
      <SwapIn swapKey='done' draw settle>
        <img alt='' src='check.svg' />
      </SwapIn>
    );
    const slot = container.querySelector('.kel-swap')!;
    const old = slot.querySelector('.kel-swap__old img');
    expect(old?.getAttribute('src')).toBe('dot.svg');
    const now = slot.querySelector<HTMLElement>('.kel-swap__now img')!;
    expect(now.getAttribute('src')).toBe('check.svg');
    act(() => motionClock.advance(120));
    expect(now.style.clipPath).toMatch(/inset/);
    await act(async () => {
      await motionClock.advanceAsync(900);
    });
    expect(slot.querySelector('.kel-swap__old')).toBeNull();
    expect(now.style.clipPath).toBe('');
  });

  it('ProgressFill has its final width from the first frame and animates only clip-path', async () => {
    const { container, rerender } = render(
      <span className='kel-wc-progress'>
        <ProgressFill fraction={0.2} tone='working' />
      </span>
    );
    const fill = container.querySelector<HTMLElement>('.kel-wc-progress__fill')!;
    rerender(
      <span className='kel-wc-progress'>
        <ProgressFill fraction={0.6} tone='in_review' />
      </span>
    );
    expect(parseFloat(fill.style.width)).toBe(60);
    expect(fill.style.clipPath).toMatch(/inset/);
    expect(container.querySelector('.kel-progress-lead')).not.toBeNull();
    expect(container.querySelector('.kel-progress-old')).not.toBeNull();
    await act(async () => {
      await motionClock.advanceAsync(1200);
    });
    expect(fill.style.clipPath).toBe('');
    expect(parseFloat(fill.style.width)).toBe(60);
  });
});

describe('the no-layout-shift probe', () => {
  const frames = (ys: number[], text?: string[]): ProbeFrame[] =>
    ys.map((y, i) => ({ t: i * 16, boxes: { title: { x: 0, y, w: 100, h: 20 } }, text: text ? { title: text[i] } : undefined }));

  it('passes a smooth move that then stays put', () => {
    expect(layoutViolations(frames([0, 6, 14, 22, 28, 31, 32, 32, 32]), { settledAfter: 100 })).toEqual([]);
  });

  it('flags a snap (an icon on the wrong line corrected in one frame)', () => {
    const v = layoutViolations(frames([0, 0, 0, 28, 28, 28, 28]), { settledAfter: 200 });
    expect(v.some((x) => x.kind === 'jump')).toBe(true);
  });

  it('flags anything that moves or re-words after the motion settled', () => {
    const moved = layoutViolations(frames([0, 0, 0, 0, 0, 3, 3]), { settledAfter: 32 });
    expect(moved.some((x) => x.kind === 'moved-after-settle')).toBe(true);
    const reworded = layoutViolations(frames([0, 0, 0, 0], ['Card', 'Card', 'Card', 'Done']), { settledAfter: 0 });
    expect(reworded.some((x) => x.kind === 'text-after-settle')).toBe(true);
  });
});
