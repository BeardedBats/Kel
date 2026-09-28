/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * The shared-element morph (MOTION.md §3). When A becomes B, one surface travels: it starts on A with
 * A's fill, border and radius and springs to B's box, while A's content leaves and B's content
 * enters inside it. Within 0.3 px of B it removes itself and the real B shows in the same pixels.
 * A stays hidden afterwards (it has become B); `restoreSource()` shows it again, e.g. when a tile
 * stays in place under its open menu and the menu closes back into it.
 *
 * Measure once, then only write: both boxes and A's and B's styles are read when the morph is
 * created. The surface sits in an overlay with `contain: strict`, so writing its size lays out
 * nothing else.
 */

import { TWEEN } from './easing';
import { enter, exit } from './choreography';
import { onFrame } from './frameLoop';
import { prefersReducedMotion } from './reducedMotion';
import { Spring, type SpringName, type SpringPreset } from './spring';

type Preset = SpringPreset | SpringName;

export type MorphPresets = { x: Preset; y: Preset; width: Preset; height: Preset; radius: Preset };

export type MorphOptions = {
  source: HTMLElement;
  target: HTMLElement;
  /** Per-edge presets. Different presets let the shape stretch (e.g. height on `gentle`). */
  presets?: Partial<MorphPresets>;
};

export type MorphHandle = {
  /** Anchored at A's size. Content placed here leaves as the move starts. */
  exitHost: HTMLElement;
  /** Anchored at B's size. Content placed here enters, staggered, while the surface travels. */
  enterHost: HTMLElement;
  /** Run the morph. Resolves at the hand-over, when the real B is showing. */
  start: () => Promise<void>;
  /** Stop at once and show B. */
  cancel: () => void;
  /** Show A again after the morph. */
  restoreSource: () => void;
};

const HANDOVER_PX = 0.3;
const OVERLAY_CLASS = 'kel-motion-overlay';

type Box = { x: number; y: number; width: number; height: number; radius: number };
type Paint = { fill: string; border: string; borderWidth: string; shadow: string };

function readBox(el: HTMLElement): Box {
  const rect = el.getBoundingClientRect();
  const radius = parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0;
  return { x: rect.left, y: rect.top, width: rect.width, height: rect.height, radius };
}

function readPaint(el: HTMLElement): Paint {
  const style = getComputedStyle(el);
  return {
    fill: style.backgroundColor,
    border: style.borderTopColor,
    borderWidth: style.borderTopWidth || '0px',
    shadow: style.boxShadow,
  };
}

function overlay(): HTMLElement {
  const existing = document.querySelector<HTMLElement>(`body > .${OVERLAY_CLASS}`);
  if (existing) return existing;
  const layer = document.createElement('div');
  layer.className = OVERLAY_CLASS;
  layer.setAttribute('aria-hidden', 'true');
  Object.assign(layer.style, {
    position: 'fixed',
    inset: '0',
    pointerEvents: 'none',
    zIndex: '2000',
    contain: 'strict',
  });
  document.body.appendChild(layer);
  return layer;
}

function host(box: Box, borderWidth: string): HTMLElement {
  const el = document.createElement('div');
  Object.assign(el.style, {
    position: 'absolute',
    top: `-${borderWidth}`,
    left: `-${borderWidth}`,
    width: `${box.width}px`,
    height: `${box.height}px`,
  });
  return el;
}

/** The blocks that enter or exit: `[data-motion-block]` in reading order, else the host's children. */
function blocks(root: HTMLElement): Element[] {
  const marked = root.querySelectorAll('[data-motion-block]');
  return marked.length > 0 ? Array.from(marked) : Array.from(root.children);
}

function animateOpacity(el: HTMLElement, from: number, to: number, duration: number, delay = 0): Promise<void> {
  if (typeof el.animate !== 'function') return Promise.resolve();
  return el
    .animate([{ opacity: from }, { opacity: to }], { duration, delay, easing: 'linear', fill: 'backwards' })
    .finished.then(
      (): void => undefined,
      (): void => undefined
    );
}

export function createMorph(options: MorphOptions): MorphHandle {
  const { source, target } = options;
  const presets: MorphPresets = {
    x: 'morph',
    y: 'morph',
    width: 'morph',
    height: 'morph',
    radius: 'morph',
    ...options.presets,
  };
  const from = readBox(source);
  const to = readBox(target);
  const fromPaint = readPaint(source);
  const toPaint = readPaint(target);

  const sourceVisibility = source.style.visibility;
  const targetVisibility = target.style.visibility;
  // B stays hidden until the hand-over, even when it already exists.
  target.style.visibility = 'hidden';

  const surface = document.createElement('div');
  Object.assign(surface.style, {
    position: 'absolute',
    top: '0',
    left: '0',
    boxSizing: 'border-box',
    overflow: 'hidden',
    borderStyle: 'solid',
    borderWidth: fromPaint.borderWidth,
    borderColor: fromPaint.border,
    background: fromPaint.fill,
    boxShadow: fromPaint.shadow,
    width: `${from.width}px`,
    height: `${from.height}px`,
    borderRadius: `${from.radius}px`,
    transform: `translate(${from.x}px, ${from.y}px)`,
    willChange: 'transform',
  });
  const exitHost = host(from, fromPaint.borderWidth);
  const enterHost = host(to, toPaint.borderWidth);
  surface.append(exitHost, enterHost);

  let done = false;
  let stopFrame: (() => void) | null = null;
  let colorTimer: ReturnType<typeof setTimeout> | null = null;
  let springs: Spring[] = [];
  let resolveStart: (() => void) | null = null;

  const finish = () => {
    if (done) return;
    done = true;
    stopFrame?.();
    if (colorTimer) clearTimeout(colorTimer);
    for (const spring of springs) spring.stop();
    const layer = surface.parentElement;
    surface.remove();
    if (layer && layer.childElementCount === 0) layer.remove();
    target.style.visibility = targetVisibility;
    source.style.visibility = 'hidden';
    resolveStart?.();
  };

  const start = (): Promise<void> => {
    if (done) return Promise.resolve();
    if (prefersReducedMotion()) {
      // A fades out while B fades in, in place (MOTION.md §7).
      target.style.visibility = targetVisibility;
      return Promise.all([
        animateOpacity(source, 1, 0, TWEEN.reducedOutMs),
        animateOpacity(target, 0, 1, TWEEN.reducedInMs, TWEEN.reducedInDelayMs),
      ]).then(() => finish());
    }

    overlay().appendChild(surface);
    source.style.visibility = 'hidden';

    const x = new Spring(from.x, { preset: presets.x });
    const y = new Spring(from.y, { preset: presets.y });
    const width = new Spring(from.width, { preset: presets.width });
    const height = new Spring(from.height, { preset: presets.height });
    const radius = new Spring(from.radius, { preset: presets.radius });
    springs = [x, y, width, height, radius];

    void exit(blocks(exitHost));
    void enter(blocks(enterHost), { delay: TWEEN.enterDelayMs });
    colorTimer = setTimeout(() => {
      surface.style.transition = [
        `background-color ${TWEEN.surfaceColorMs}ms ${TWEEN.easeOut}`,
        `border-color ${TWEEN.surfaceColorMs}ms ${TWEEN.easeOut}`,
        `box-shadow ${TWEEN.surfaceColorMs}ms ${TWEEN.easeOut}`,
      ].join(', ');
      surface.style.background = toPaint.fill;
      surface.style.borderColor = toPaint.border;
      surface.style.borderWidth = toPaint.borderWidth;
      surface.style.boxShadow = toPaint.shadow;
    }, TWEEN.surfaceColorDelayMs);

    x.set(to.x);
    y.set(to.y);
    width.set(to.width);
    height.set(to.height);
    radius.set(to.radius);

    return new Promise<void>((resolve) => {
      resolveStart = resolve;
      stopFrame = onFrame(() => {
        const box = { x: x.value, y: y.value, width: width.value, height: height.value, radius: radius.value };
        surface.style.transform = `translate(${box.x}px, ${box.y}px)`;
        surface.style.width = `${box.width}px`;
        surface.style.height = `${box.height}px`;
        surface.style.borderRadius = `${box.radius}px`;
        const near =
          Math.abs(box.x - to.x) < HANDOVER_PX &&
          Math.abs(box.y - to.y) < HANDOVER_PX &&
          Math.abs(box.width - to.width) < HANDOVER_PX &&
          Math.abs(box.height - to.height) < HANDOVER_PX;
        const resting = springs.every((spring) => !spring.isAnimating);
        if ((near && Math.abs(box.radius - to.radius) < HANDOVER_PX) || resting) {
          stopFrame = null;
          finish();
          return false;
        }
        return true;
      });
    });
  };

  const restoreSource = () => {
    source.style.visibility = sourceVisibility;
  };

  return { exitHost, enterHost, start, cancel: finish, restoreSource };
}

/** Morph A into B with no content carried in the surface. */
export function morph(options: MorphOptions): Promise<void> {
  return createMorph(options).start();
}
