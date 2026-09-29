/**
 * MOTION.md §3 — the shared-element morph. When one thing becomes another, one surface travels: it
 * starts on A with A's fill, border and radius, and its geometry (translate plus width, height and
 * radius, each on its own spring) moves to B while A's content leaves and B's content enters. The
 * surface is out of flow with `contain: strict`, so writing its size lays out nothing else. All
 * measuring happens before the move starts; the per-frame loop only writes.
 */
import { drawOn, enter, exit, prepareEnter, settleIn, setFx } from './fx';
import { isReducedMotion } from './reduced';
import { frameWrite, spring, tween, waitMotion, type PresetName } from './spring';
import { MOTION } from './tokens';

export type Box = { x: number; y: number; w: number; h: number };
export type Rgba = [number, number, number, number];

export const boxOf = (el: Element): Box => {
  const r = el.getBoundingClientRect();
  return { x: r.left, y: r.top, w: r.width, h: r.height };
};

/** Composite translucent layers (bottom first) into one rgba, exactly. */
export const composite = (layers: Rgba[]): Rgba => {
  let a = 0;
  let r = 0;
  let g = 0;
  let b = 0;
  for (const [lr, lg, lb, la] of layers) {
    // premultiplied "over"
    r = lr * la + r * (1 - la);
    g = lg * la + g * (1 - la);
    b = lb * la + b * (1 - la);
    a = la + a * (1 - la);
  }
  return a > 0 ? [r / a, g / a, b / a, a] : [0, 0, 0, 0];
};

export type Look = { bg: Rgba; bd: Rgba; bw: number; r: number; shadow: number };

const look = (layers: Rgba[], bd: Rgba, r: number, extra: Partial<Look> = {}): Look => ({ bg: composite(layers), bd, bw: 1, r, shadow: 0, ...extra });

/** The surfaces Kel's moments travel between (fills from the real CSS, composited). */
export const LOOKS = {
  card: look([[15, 45, 100, 0.55], [47, 107, 224, 0.14]], [191, 216, 255, 0.16], 10),
  cardSelected: look([[15, 45, 100, 0.7], [47, 107, 224, 0.3]], [127, 160, 255, 0.8], 10, { bw: 1.5 }),
  panel: look([[11, 26, 61, 0.97], [47, 107, 224, 0.08]], [221, 233, 255, 0.5], 12, { shadow: 1 }),
  menu: look([[11, 26, 61, 0.97], [47, 107, 224, 0.08]], [221, 233, 255, 0.5], 10, { shadow: 1 }),
  line: look([[47, 107, 224, 0.08]], [191, 216, 255, 0.14], 8),
  section: look([[15, 45, 100, 0.35], [47, 107, 224, 0.12]], [191, 216, 255, 0.14], 10),
  needs: look([[15, 45, 100, 0.35], [47, 107, 224, 0.12]], [252, 172, 81, 0.35], 10),
  scoping: look([[15, 45, 100, 0.35], [47, 107, 224, 0.12]], [191, 216, 255, 0.14], 12),
  collapsed: look([[15, 45, 100, 0.35], [47, 107, 224, 0.12]], [191, 216, 255, 0.14], 8),
  tile: look([[47, 107, 224, 0.1]], [191, 216, 255, 0.16], 10),
  tileOpen: look([[47, 107, 224, 0.3]], [127, 160, 255, 0.8], 10, { bw: 1.5 }),
} satisfies Record<string, Look>;

export type LookName = keyof typeof LOOKS;

/* ─────────────────────────────── the overlay layer ─────────────────────────────── */

let layerEl: HTMLDivElement | null = null;

/** One fixed layer over the window for surfaces and flights (viewport coordinates). */
export const motionLayer = (): HTMLDivElement => {
  if (layerEl && layerEl.isConnected) return layerEl;
  layerEl = document.createElement('div');
  layerEl.className = 'kel-motion-layer';
  layerEl.setAttribute('aria-hidden', 'true');
  layerEl.dataset.testid = 'kel-motion-layer';
  document.body.appendChild(layerEl);
  return layerEl;
};

const STRIP = ['id', 'data-testid', 'data-job', 'data-done-card', 'data-scoping-card', 'role', 'aria-live', 'aria-label', 'aria-labelledby', 'tabindex', 'data-flip-id'];

/** A static, inert copy of an element for a transition (never queried, never focusable). */
export const ghostOf = (el: Element): HTMLElement => {
  const copy = el.cloneNode(true) as HTMLElement;
  const all = [copy, ...Array.from(copy.querySelectorAll('*'))];
  for (const node of all) for (const name of STRIP) node.removeAttribute(name);
  copy.setAttribute('aria-hidden', 'true');
  copy.setAttribute('inert', '');
  copy.classList.add('kel-motion-ghost');
  for (const control of Array.from(copy.querySelectorAll('button, input, textarea, select, a'))) control.setAttribute('tabindex', '-1');
  return copy;
};

/* ─────────────────────────────── the surface ─────────────────────────────── */

const css = (c: Rgba) => `rgba(${c[0].toFixed(1)},${c[1].toFixed(1)},${c[2].toFixed(1)},${c[3].toFixed(3)})`;

export type SurfaceState = Box & { r: number; bg: Rgba; bd: Rgba; bw: number; shadow: number };

export type Surface = {
  el: HTMLDivElement;
  state: SurfaceState;
  set: (next: Partial<SurfaceState>) => void;
  to: (target: Partial<SurfaceState>, opts?: { preset?: PresetName; presets?: Partial<Record<'x' | 'y' | 'w' | 'h' | 'r', PresetName>>; delays?: Partial<Record<'x' | 'y' | 'w' | 'h' | 'r', number>> }) => Promise<void>;
  remove: () => void;
};

export const surface = (layer: HTMLElement, start: Box & Look): Surface => {
  const el = document.createElement('div');
  el.className = 'kel-motion-surface';
  layer.appendChild(el);
  const state: SurfaceState = { x: start.x, y: start.y, w: start.w, h: start.h, r: start.r, bg: [...start.bg] as Rgba, bd: [...start.bd] as Rgba, bw: start.bw, shadow: start.shadow };
  const render = () => {
    el.style.transform = `translate(${state.x.toFixed(2)}px, ${state.y.toFixed(2)}px)`;
    el.style.width = `${Math.max(0, state.w).toFixed(2)}px`;
    el.style.height = `${Math.max(0, state.h).toFixed(2)}px`;
    el.style.borderRadius = `${Math.max(0, state.r).toFixed(2)}px`;
    el.style.backgroundColor = css(state.bg);
    el.style.borderColor = css(state.bd);
    el.style.borderWidth = `${state.bw}px`;
    el.style.boxShadow =
      state.shadow > 0.001
        ? `0 20px 48px -16px rgba(0,0,0,${(0.35 * state.shadow).toFixed(3)}), inset 0 1px 0 rgba(191,216,255,${(0.18 * state.shadow).toFixed(3)})`
        : '';
  };
  render();
  const draw = () => frameWrite(el, render);
  const api: Surface = {
    el,
    state,
    set(next) {
      Object.assign(state, next);
      render();
    },
    to(target, opts = {}) {
      const jobs: Promise<void>[] = [];
      for (const key of ['x', 'y', 'w', 'h', 'r'] as const) {
        const value = target[key];
        if (value === undefined) continue;
        const preset = opts.presets?.[key] ?? opts.preset ?? 'morph';
        jobs.push(
          spring(state[key], value, preset, (v) => {
            state[key] = v;
            draw();
          }, { eps: key === 'r' ? 0.05 : 0.3, delay: opts.delays?.[key] ?? 0 }).finished
        );
      }
      for (const key of ['bg', 'bd'] as const) {
        const value = target[key];
        if (!value) continue;
        const from = [...state[key]] as Rgba;
        jobs.push(
          tween(0, 1, MOTION.surfaceColorMs, 'out', (p) => {
            state[key] = from.map((v, i) => v + (value[i] - v) * p) as Rgba;
            draw();
          }, { delay: MOTION.surfaceColorDelayMs }).finished
        );
      }
      if (target.shadow !== undefined) {
        const from = state.shadow;
        const to = target.shadow;
        jobs.push(tween(from, to, 220, 'out', (v) => {
          state.shadow = v;
          draw();
        }).finished);
      }
      if (target.bw !== undefined) state.bw = target.bw;
      return Promise.all(jobs).then((): void => undefined);
    },
    remove() {
      el.remove();
    },
  };
  return api;
};

/* ─────────────────────────────── the morph ─────────────────────────────── */

export type MorphOptions = {
  from: Box;
  to: Box;
  fromLook: Look;
  toLook: Look;
  /** A static copy of A's content, carried in the surface and exited first. */
  fromContent?: HTMLElement | null;
  /** A static copy of B's content, anchored at B's final size and entered mid-flight. */
  toContent?: HTMLElement | null;
  /** Selectors inside toContent that enter in reading order (default: the whole copy). */
  toParts?: string[];
  presets?: Partial<Record<'x' | 'y' | 'w' | 'h' | 'r', PresetName>>;
  preset?: PresetName;
  contentDelay?: number;
  stagger?: number;
  /** Runs when the surface lands (the real B shows in the same pixels). */
  onLand?: () => void;
  layer?: HTMLElement;
};

export type MorphHandle = { finished: Promise<void>; cancel: () => void };

/**
 * One surface travels from A's box to B's box. The real A and B are the caller's to hide and show:
 * B stays hidden until onLand. Reduced motion is the caller's cross-fade (see crossFade()).
 */
export const morph = (o: MorphOptions): MorphHandle => {
  let cancelled = false;
  let landed = false;
  const land = () => {
    if (landed) return;
    landed = true;
    o.onLand?.();
  };
  if (isReducedMotion()) {
    land();
    return { finished: Promise.resolve(), cancel: () => undefined };
  }
  const layer = o.layer ?? motionLayer();
  const sf = surface(layer, { ...o.from, ...o.fromLook });
  const fit = (node: HTMLElement, box: Box, look: Look) => {
    node.classList.add('kel-motion-content');
    node.style.width = `${box.w}px`;
    node.style.height = `${box.h}px`;
    node.style.left = `${-look.bw}px`;
    node.style.top = `${-look.bw}px`;
    sf.el.appendChild(node);
  };
  if (o.fromContent) fit(o.fromContent, o.from, o.fromLook);
  let parts: HTMLElement[] = [];
  if (o.toContent) {
    fit(o.toContent, o.to, o.toLook);
    parts = o.toParts?.length
      ? o.toParts.flatMap((sel) => Array.from(o.toContent!.querySelectorAll<HTMLElement>(sel)))
      : [o.toContent];
    prepareEnter(parts);
  }
  const exitP = o.fromContent ? exit(o.fromContent, { ms: 110 }) : Promise.resolve();
  const moveP = sf.to(
    { x: o.to.x, y: o.to.y, w: o.to.w, h: o.to.h, r: o.toLook.r, bg: o.toLook.bg, bd: o.toLook.bd, bw: o.toLook.bw, shadow: o.toLook.shadow },
    { preset: o.preset ?? 'morph', presets: o.presets }
  );
  const enterP = waitMotion(o.contentDelay ?? 110).then(() => (cancelled ? undefined : enter(parts, { stagger: o.stagger ?? 35 })));
  const finished = Promise.all([moveP, enterP, exitP]).then(() => {
    if (cancelled) return;
    land();
    sf.remove();
  });
  return {
    finished,
    cancel: () => {
      cancelled = true;
      land();
      sf.remove();
    },
  };
};

/** Reduced motion's morph: A fades out (100 ms) while B fades in, in place (150 ms, 60 ms later). */
export const crossFade = (a: HTMLElement | null, b: HTMLElement | null): Promise<void> => {
  const jobs: Promise<void>[] = [];
  if (a) jobs.push(tween(1, 0, MOTION.reducedOutMs, 'linear', (v) => setFx(a, { o: v })).finished);
  if (b) {
    setFx(b, { o: 0 });
    jobs.push(tween(0, 1, MOTION.reducedInMs, 'linear', (v) => setFx(b, { o: v }), { delay: 60 }).finished.then(() => setFx(b, {})));
  }
  return Promise.all(jobs).then((): void => undefined);
};

/** A small element flying between two boxes (the accent moves; it never fades between states). */
export const fly = (node: HTMLElement, a: Box, b: Box, opts: { px?: PresetName; py?: PresetName; delay?: number; layer?: HTMLElement } = {}): Promise<void> => {
  if (isReducedMotion()) return Promise.resolve();
  const holder = document.createElement('div');
  holder.className = 'kel-motion-fly';
  holder.appendChild(node);
  (opts.layer ?? motionLayer()).appendChild(holder);
  const st = { x: a.x, y: a.y, s: 1 };
  const scale = a.w > 0 ? b.w / a.w : 1;
  const render = () => {
    holder.style.transform = `translate(${st.x.toFixed(2)}px, ${st.y.toFixed(2)}px) scale(${st.s.toFixed(4)})`;
  };
  render();
  const draw = () => frameWrite(holder, render);
  return Promise.all([
    spring(a.x, b.x, opts.px ?? 'gentle', (v) => {
      st.x = v;
      draw();
    }, { eps: 0.05, delay: opts.delay }).finished,
    spring(a.y, b.y, opts.py ?? 'morph', (v) => {
      st.y = v;
      draw();
    }, { eps: 0.05, delay: opts.delay }).finished,
    spring(1, scale, 'morph', (v) => {
      st.s = v;
      draw();
    }, { eps: 0.001, delay: opts.delay }).finished,
  ]).then(() => holder.remove());
};

/**
 * A static copy of an element fading out where it was (an unmounted menu, a removed row). Placed in
 * the overlay at the element's last box; never delays the real UI, which has already moved on.
 */
export type Snapshot = { ghost: HTMLElement; box: Box };

/** Copy an element and its box now (e.g. during render, before React removes it). */
export const snapshotGhost = (el: Element | null | undefined): Snapshot | null => {
  if (!el || !el.isConnected) return null;
  const box = boxOf(el);
  if (box.w <= 0 || box.h <= 0) return null;
  return { ghost: ghostOf(el), box };
};

/** Show a snapshot where its element was and let it leave (exit fx), then remove it. */
export const exitGhostAt = (snap: Snapshot | null, opts: { ms?: number; scale?: number; blur?: number; y?: number } = {}): Promise<void> => {
  if (!snap) return Promise.resolve();
  const { ghost, box } = snap;
  ghost.classList.add('kel-motion-exit');
  ghost.style.width = `${box.w}px`;
  ghost.style.height = `${box.h}px`;
  ghost.style.left = `${box.x}px`;
  ghost.style.top = `${box.y}px`;
  motionLayer().appendChild(ghost);
  return exit(ghost, { ms: opts.ms ?? 120, scale: opts.scale ?? 0.97, blur: opts.blur ?? 3, y: opts.y ?? 0 }).then(() => ghost.remove());
};

/**
 * A static copy of an element fading out where it was (an unmounted menu, a removed row). Placed in
 * the overlay at the element's last box; never delays the real UI, which has already moved on.
 */
export const exitGhost = (el: Element | null | undefined, opts: { ms?: number; scale?: number; blur?: number; y?: number } = {}): Promise<void> =>
  exitGhostAt(snapshotGhost(el), opts);

/* ─────────────────────────────── shared elements between components ─────────────────────────────── */

type Shared = { el: HTMLElement; at: number; data?: Record<string, unknown> };
const shared = new Map<string, Shared>();

/** Offer an element for a shared-element transition (the in-thread line for its top card). */
export const offerShared = (key: string, el: HTMLElement, data?: Record<string, unknown>): void => {
  shared.set(key, { el, at: Date.now(), data });
};

/** Take an offered element (once), if it is still on screen and fresh. */
export const claimShared = (key: string, maxAgeMs = 12000): Shared | null => {
  const found = shared.get(key);
  if (!found) return null;
  shared.delete(key);
  if (!found.el.isConnected || Date.now() - found.at > maxAgeMs) return null;
  return found;
};

export const peekShared = (key: string): Shared | null => shared.get(key) ?? null;

/**
 * One section becomes another in place (the question → "You answered", the scoping card → its
 * one-line summary): a surface starts on A's snapshot with A's look and morphs to B's box while A's
 * content leaves; B is laid out from the first frame and hidden, a copy of its parts arrives inside
 * the surface (the settling fade when B is a resting end state), and B shows when the surface lands.
 */
export const morphInto = (o: {
  from: Snapshot | null;
  to: HTMLElement;
  fromLook: Look;
  toLook: Look;
  settle?: boolean;
  /** A selector inside B whose icon draws on (a check). */
  draw?: string;
  presets?: Partial<Record<'x' | 'y' | 'w' | 'h' | 'r', PresetName>>;
}): Promise<void> => {
  const parts = Array.from(o.to.children) as HTMLElement[];
  if (!o.from || isReducedMotion()) {
    prepareEnter(parts);
    return (o.settle ? settleIn(parts) : enter(parts)).then((): void => undefined);
  }
  const toBox = boxOf(o.to);
  const sf = surface(motionLayer(), { ...o.from.box, ...o.fromLook });
  const place = (node: HTMLElement, box: Box, look: Look) => {
    node.classList.add('kel-motion-content');
    node.style.width = `${box.w}px`;
    node.style.height = `${box.h}px`;
    node.style.left = `${-look.bw}px`;
    node.style.top = `${-look.bw}px`;
    sf.el.appendChild(node);
  };
  place(o.from.ghost, o.from.box, o.fromLook);
  void exit(o.from.ghost, { ms: 110 });
  o.to.classList.add('kel-motion-hidden');
  const copy = ghostOf(o.to);
  copy.classList.remove('kel-motion-hidden');
  place(copy, toBox, o.toLook);
  const copyParts = Array.from(copy.children) as HTMLElement[];
  prepareEnter(copyParts, o.settle ? { y: 0, blur: MOTION.settleBlurPx } : {});
  const arrive = waitMotion(110).then(() => {
    const check = o.draw ? copy.querySelector<HTMLElement>(o.draw) : null;
    if (check) void drawOn(check, { delay: 60 });
    return o.settle ? settleIn(copyParts, { stagger: 25 }) : enter(copyParts, { stagger: 25 });
  });
  const move = sf.to({ ...toBox, r: o.toLook.r, bg: o.toLook.bg, bd: o.toLook.bd, bw: o.toLook.bw, shadow: o.toLook.shadow }, { presets: o.presets ?? { h: 'morph', w: 'snappy' } });
  return Promise.all([move, arrive]).then(() => {
    o.to.classList.remove('kel-motion-hidden');
    sf.remove();
  });
};

const stashed = new Map<string, { snap: Snapshot; at: number }>();

/** Keep a copy of something that is leaving, for whatever arrives next to fly out of it. */
export const stashSnapshot = (key: string, snap: Snapshot | null): void => {
  if (snap) stashed.set(key, { snap, at: Date.now() });
};

/** Take a stashed copy (once), if it is fresh. */
export const takeSnapshot = (key: string, maxAgeMs = 1500): Snapshot | null => {
  const found = stashed.get(key);
  stashed.delete(key);
  return found && Date.now() - found.at <= maxAgeMs ? found.snap : null;
};
