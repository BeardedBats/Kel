/**
 * MOTION.md §4 — enter and exit choreography, the settling fade, label rolls, icon swaps, draw-on and
 * press. Every helper animates opacity, filter and transform only (clip-path for draw-on), and each
 * element carries at most one running effect: starting a new one takes over from where the old one
 * is (interruption never jumps).
 */
import { isReducedMotion } from './reduced';
import { spring, tween, type Ease, type PresetName, type TweenHandle } from './spring';
import { BLUR, MOTION } from './tokens';

export type Fx = { o?: number; blur?: number; x?: number; y?: number; s?: number };

/** Write one element's transient look. Values at rest clear the inline style. */
export const setFx = (el: HTMLElement | SVGElement, fx: Fx): void => {
  const style = el.style;
  const o = fx.o ?? 1;
  style.opacity = o >= 0.999 ? '' : o.toFixed(3);
  const blur = fx.blur ?? 0;
  style.filter = blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : '';
  const parts: string[] = [];
  if (fx.x || fx.y) parts.push(`translate(${(fx.x ?? 0).toFixed(2)}px, ${(fx.y ?? 0).toFixed(2)}px)`);
  if (fx.s !== undefined && Math.abs(fx.s - 1) > 0.0005) parts.push(`scale(${fx.s.toFixed(4)})`);
  style.transform = parts.join(' ');
};

export const clearFx = (el: HTMLElement | SVGElement): void => {
  el.style.opacity = '';
  el.style.filter = '';
  el.style.transform = '';
};

type Running = { stop: () => void; opacity: () => number };
const running = new WeakMap<Element, Running>();

/** Stop whatever effect an element is running and return its current opacity. */
export const takeOver = (el: Element): number => {
  const current = running.get(el);
  if (!current) {
    const inline = (el as HTMLElement).style?.opacity;
    return inline === '' || inline === undefined ? 1 : Number(inline);
  }
  running.delete(el);
  const o = current.opacity();
  current.stop();
  return o;
};

const listOf = (target: Element | Element[] | NodeListOf<Element> | null | undefined): HTMLElement[] =>
  !target ? [] : target instanceof Element ? [target as HTMLElement] : (Array.from(target) as HTMLElement[]);

const fade = (
  el: HTMLElement,
  from: Fx,
  to: Fx,
  ms: number,
  ease: Ease,
  delay: number,
  clearAtEnd: boolean
): Promise<void> => {
  const lerp = (a: number | undefined, b: number | undefined, p: number, rest: number) => {
    const x = a ?? rest;
    const y = b ?? rest;
    return x + (y - x) * p;
  };
  let o = from.o ?? 1;
  setFx(el, from);
  const handle: TweenHandle = tween(0, 1, ms, ease, (p) => {
    o = lerp(from.o, to.o, p, 1);
    setFx(el, {
      o,
      blur: lerp(from.blur, to.blur, p, 0),
      x: lerp(from.x, to.x, p, 0),
      y: lerp(from.y, to.y, p, 0),
      s: lerp(from.s, to.s, p, 1),
    });
  }, { delay });
  const record: Running = { stop: handle.stop, opacity: () => o };
  running.set(el, record);
  return handle.finished.then(() => {
    if (running.get(el) === record) {
      running.delete(el);
      if (clearAtEnd) clearFx(el);
    }
  });
};

export type EnterOptions = { y?: number; x?: number; blur?: number; ms?: number; stagger?: number; delay?: number; scale?: number };

/** Content enters after its container starts moving: opacity up, blur and offset away, staggered. */
export const enter = (target: Element | Element[] | NodeListOf<Element> | null | undefined, opts: EnterOptions = {}): Promise<void> => {
  const els = listOf(target);
  const reduced = isReducedMotion();
  const gap = opts.stagger ?? 0;
  return Promise.all(
    els.map((el, i) => {
      const from = Math.min(takeOver(el), 1);
      const start = from >= 0.999 ? 0 : from;
      const delay = (opts.delay ?? 0) + Math.min(i * gap, MOTION.staggerCapMs) * (reduced ? 0.5 : 1);
      if (reduced) return fade(el, { o: start }, { o: 1 }, 140, 'linear', delay, true);
      return fade(
        el,
        { o: start, blur: (opts.blur ?? BLUR.enter) * (1 - start), y: (opts.y ?? 6) * (1 - start), x: (opts.x ?? 0) * (1 - start), s: opts.scale },
        { o: 1, blur: 0, y: 0, x: 0, s: 1 },
        opts.ms ?? MOTION.enterMs,
        'out',
        delay,
        true
      );
    })
  ).then((): void => undefined);
};

/** Hide elements that are about to enter (so the first painted frame is already the start state). */
export const prepareEnter = (target: Element | Element[] | NodeListOf<Element> | null | undefined, opts: EnterOptions = {}): void => {
  const reduced = isReducedMotion();
  for (const el of listOf(target)) {
    takeOver(el);
    setFx(el, reduced ? { o: 0 } : { o: 0, blur: opts.blur ?? BLUR.enter, y: opts.y ?? 6, x: opts.x ?? 0, s: opts.scale });
  }
};

export type ExitOptions = { y?: number; blur?: number; ms?: number; delay?: number; scale?: number };

/** Content leaves before the next move: quick, all at once (exits never stagger). Stays hidden. */
export const exit = (target: Element | Element[] | NodeListOf<Element> | null | undefined, opts: ExitOptions = {}): Promise<void> => {
  const els = listOf(target);
  const reduced = isReducedMotion();
  return Promise.all(
    els.map((el) => {
      const o = takeOver(el);
      if (reduced) return fade(el, { o }, { o: 0 }, MOTION.reducedOutMs, 'linear', opts.delay ?? 0, false);
      return fade(
        el,
        { o, blur: 0, y: 0, s: 1 },
        { o: 0, blur: opts.blur ?? BLUR.exit, y: opts.y ?? -4, s: opts.scale ?? 1 },
        opts.ms ?? MOTION.exitMs,
        'in',
        opts.delay ?? 0,
        false
      );
    })
  ).then((): void => undefined);
};

/**
 * The settling fade: a resting end state that will stay on screen fades in slower (opacity plus a
 * small blur-to-sharp, eased out). Reduced motion keeps a gentle cross-fade, never an instant swap.
 */
export const settleIn = (target: Element | Element[] | NodeListOf<Element> | null | undefined, opts: { delay?: number; stagger?: number } = {}): Promise<void> => {
  const els = listOf(target);
  const reduced = isReducedMotion();
  return Promise.all(
    els.map((el, i) => {
      const start = Math.min(takeOver(el), 1);
      const from = start >= 0.999 ? 0 : start;
      const delay = (opts.delay ?? 0) + Math.min(i * (opts.stagger ?? 0), MOTION.staggerCapMs);
      if (reduced) return fade(el, { o: from }, { o: 1 }, MOTION.settleReducedMs, 'linear', delay, true);
      return fade(el, { o: from, blur: MOTION.settleBlurPx * (1 - from) }, { o: 1, blur: 0 }, MOTION.settleMs, 'out', delay, true);
    })
  ).then((): void => undefined);
};

/** A check (or any icon) drawing on: a stroke dash for SVG paths, a left-to-right wipe otherwise. */
export const drawOn = (el: Element | null | undefined, opts: { ms?: number; delay?: number } = {}): Promise<void> => {
  if (!el) return Promise.resolve();
  const node = el as HTMLElement;
  if (isReducedMotion()) {
    node.style.clipPath = '';
    return Promise.resolve();
  }
  const path = typeof SVGPathElement !== 'undefined' && node instanceof SVGPathElement ? node : null;
  if (path && typeof path.getTotalLength === 'function') {
    const len = path.getTotalLength();
    path.style.strokeDasharray = `${len}`;
    return tween(len, 0, opts.ms ?? MOTION.drawMs, 'out', (v) => {
      path.style.strokeDashoffset = `${v}`;
    }, { delay: opts.delay }).finished;
  }
  node.style.clipPath = 'inset(0 100% 0 0)';
  return tween(100, 0, opts.ms ?? MOTION.drawMs, 'out', (v) => {
    node.style.clipPath = v <= 0.01 ? '' : `inset(0 ${v.toFixed(2)}% 0 0)`;
  }, { delay: opts.delay }).finished;
};

/** Press feedback: scale to 0.94 on micro, back on snappy. */
export const press = async (el: HTMLElement | null | undefined): Promise<void> => {
  if (!el || isReducedMotion()) return;
  await spring(1, 0.94, 'micro', (v) => {
    el.style.transform = `scale(${v.toFixed(4)})`;
  }, { eps: 0.001 }).finished;
  spring(0.94, 1, 'snappy', (v) => {
    el.style.transform = Math.abs(v - 1) < 0.0005 ? '' : `scale(${v.toFixed(4)})`;
  }, { eps: 0.001 });
};

/** One turn and stop (never a loop, §9): the step loader when a step starts, Undo's arrow. */
export const turnOnce = (el: HTMLElement | null | undefined, degrees = 360, preset: PresetName = 'gentle', delay = 0): Promise<void> => {
  if (!el || isReducedMotion()) return Promise.resolve();
  return spring(0, degrees, preset, (v, h) => {
    el.style.transform = h.done && v === degrees ? '' : `rotate(${v.toFixed(2)}deg)`;
  }, { eps: 0.05, delay }).finished.then(() => {
    el.style.transform = '';
  });
};

/** A small scale pulse (avatar rings changing state): 1 → 1.12 → 1 on snappy. */
export const pulse = (el: HTMLElement | null | undefined, delay = 0, peak = 1.12): Promise<void> => {
  if (!el || isReducedMotion()) return Promise.resolve();
  let to = peak;
  const h = spring(1, peak, 'micro', (v) => {
    el.style.transform = Math.abs(v - 1) < 0.0005 && to === 1 ? '' : `scale(${v.toFixed(4)})`;
  }, { eps: 0.002, delay });
  return h.finished.then(() => {
    to = 1;
    return spring(peak, 1, 'snappy', (v) => {
      el.style.transform = Math.abs(v - 1) < 0.0005 ? '' : `scale(${v.toFixed(4)})`;
    }, { eps: 0.001 }).finished;
  });
};

/**
 * A picked chip (§10.6): the primary gradient grows from the press point (a clip-path circle on
 * `snappy`); then the chip's own picked style takes over. Navy never fades to blue.
 */
export const bloom = (el: HTMLElement | null | undefined, clientX?: number, clientY?: number): Promise<void> => {
  if (!el || isReducedMotion()) return Promise.resolve();
  const r = el.getBoundingClientRect();
  const x = clientX !== undefined && r.width ? ((clientX - r.left) / r.width) * 100 : 50;
  const y = clientY !== undefined && r.height ? ((clientY - r.top) / r.height) * 100 : 50;
  const radius = Math.hypot(Math.max(r.width, 1), Math.max(r.height, 1));
  const blob = document.createElement('span');
  blob.className = 'kel-bloom';
  blob.setAttribute('aria-hidden', 'true');
  blob.style.clipPath = `circle(0px at ${x.toFixed(1)}% ${y.toFixed(1)}%)`;
  el.appendChild(blob);
  return spring(0, radius, 'snappy', (v) => {
    blob.style.clipPath = `circle(${v.toFixed(1)}px at ${x.toFixed(1)}% ${y.toFixed(1)}%)`;
  }, { eps: 0.5 }).finished.then(() => blob.remove());
};
