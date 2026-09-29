/**
 * D-78 — the work-card row's choreography (docs/v2/design/MOTION.md §10.2, §10.3, §10.10): the card
 * growing into its detail panel and shrinking back, the in-thread line lifting into a new top card,
 * a card that no longer fits morphing into "+N more", and the "+N more" tile opening into its menu.
 *
 * Surfaces live inside the row's stack (`.kel-wc-stack`), between the cards and the detail panel, so a
 * travelling surface covers its card but never the panel's own content. The real panel is used (not a
 * copy): it is clipped to the surface while the surface grows, so data that arrives mid-flight shows
 * at once and the surface simply retargets to the panel's new height (final layout first).
 */
import {
  LOOKS,
  boxOf,
  crossFade,
  morphInto,
  drawOn,
  settleIn,
  enter,
  exit,
  exitGhostAt,
  fly,
  frameWrite,
  ghostOf,
  isReducedMotion,
  motionLayer,
  prepareEnter,
  spring,
  surface,
  tween,
  waitMotion,
  type Box,
  type Look,
  type Snapshot,
  type Surface,
} from '@renderer/motion';
import { MOTION } from '@renderer/motion/tokens';

const PANEL_PARTS = [
  ':scope > .kel-wd-head',
  ':scope > .kel-wd-notice',
  ':scope > .kel-na',
  ':scope > .kel-na-answered',
  ':scope > .kel-wd-result',
  ':scope > .kel-budget-stop',
  ':scope > .kel-wd-progress',
  ':scope > .kel-wd-loading',
  ':scope > .kel-wd-columns > .kel-wd-col--team',
  ':scope > .kel-wd-columns > .kel-wd-col--steps',
  ':scope > .kel-wd-columns > .kel-wd-col--review',
  ':scope > .kel-wd-footer',
];

const partsOf = (root: HTMLElement, selectors: string[]): HTMLElement[] => {
  const seen = new Set<HTMLElement>();
  const out: HTMLElement[] = [];
  for (const sel of selectors) {
    for (const el of Array.from(root.querySelectorAll<HTMLElement>(sel))) {
      if (!seen.has(el)) {
        seen.add(el);
        out.push(el);
      }
    }
  }
  return out;
};

const rel = (box: Box, origin: Box): Box => ({ x: box.x - origin.x, y: box.y - origin.y, w: box.w, h: box.h });

/** A surface inside the stack (stack-relative coordinates). */
const stackSurface = (stack: HTMLElement, from: Box, look: Look): { sf: Surface; origin: Box } => {
  const origin = boxOf(stack);
  const sf = surface(stack, { ...rel(from, origin), ...look });
  sf.el.classList.add('kel-wc-surface');
  // Above the cards, below the detail panel: right after the row in paint order.
  const row = stack.querySelector(':scope > .kel-wc-row');
  if (row) stack.insertBefore(sf.el, row.nextSibling);
  return { sf, origin };
};

const fitCopy = (sf: Surface, copy: HTMLElement, box: Box, look: Look) => {
  copy.classList.add('kel-motion-content');
  copy.style.width = `${box.w}px`;
  copy.style.height = `${box.h}px`;
  copy.style.left = `${-look.bw}px`;
  copy.style.top = `${-look.bw}px`;
  sf.el.appendChild(copy);
};

/* ─────────────────────────────── backdrop ─────────────────────────────── */

export const backdropIn = (backdrop: HTMLElement | null): void => {
  if (!backdrop) return;
  const ms = isReducedMotion() ? MOTION.reducedInMs : MOTION.backdropMs;
  backdrop.style.opacity = '0';
  void tween(0, 1, ms, isReducedMotion() ? 'linear' : 'out', (v) => {
    backdrop.style.opacity = v >= 1 ? '' : v.toFixed(3);
  });
};

/** The backdrop leaves from a copy in its own place (the real one has already unmounted). */
export const backdropOut = (host: HTMLElement | null, before: Element | null): void => {
  if (!host) return;
  const copy = document.createElement('div');
  copy.className = 'kel-wc-backdrop kel-motion-ghost';
  copy.setAttribute('aria-hidden', 'true');
  copy.style.pointerEvents = 'none';
  host.insertBefore(copy, before && before.parentElement === host ? before : host.firstChild);
  const reduced = isReducedMotion();
  void tween(1, 0, reduced ? MOTION.reducedOutMs : MOTION.backdropMs, reduced ? 'linear' : 'in', (v) => {
    copy.style.opacity = v.toFixed(3);
  }, { delay: reduced ? 0 : MOTION.backdropOutDelayMs }).finished.then(() => copy.remove());
};

/* ─────────────────────────────── card → panel ─────────────────────────────── */

export type OpenHandle = { cancel: () => void };

/**
 * §10.3 open: a surface starts on the card with the card's look and grows into the panel — x, y and
 * width on `morph`, height on `gentle`, radius 10 → 12, fill and border to the panel's. The card's
 * content leaves at once; from 120 ms the panel's blocks enter in reading order, 40 ms apart. The
 * real panel is clipped to the surface until it lands.
 */
export const openDetailMorph = (stack: HTMLElement, source: HTMLElement, panel: HTMLElement): OpenHandle => {
  if (isReducedMotion()) {
    void crossFade(null, panel);
    return { cancel: () => undefined };
  }
  const fromBox = boxOf(source);
  let toBox = boxOf(panel);
  if (fromBox.w <= 0 || toBox.w <= 0) return { cancel: () => undefined };
  const fromLook = source.classList.contains('kel-wc-overflow') ? LOOKS.tile : LOOKS.card;
  const { sf, origin } = stackSurface(stack, fromBox, fromLook);
  const copy = ghostOf(source);
  fitCopy(sf, copy, fromBox, fromLook);
  void exit(copy, { ms: 110 });

  const target = rel(toBox, origin);
  const panelOrigin = rel(toBox, origin);
  panel.classList.add('kel-motion-bare');
  const clip = () =>
    frameWrite(panel, () => {
      const s = sf.state;
      const top = Math.max(0, s.y - panelOrigin.y);
      const left = Math.max(0, s.x - panelOrigin.x);
      const right = Math.max(0, panelOrigin.x + toBox.w - (s.x + s.w));
      const bottom = Math.max(0, panelOrigin.y + toBox.h - (s.y + s.h));
      panel.style.clipPath = `inset(${top.toFixed(2)}px ${right.toFixed(2)}px ${bottom.toFixed(2)}px ${left.toFixed(2)}px round ${s.r.toFixed(2)}px)`;
    });
  clip();
  const parts = partsOf(panel, PANEL_PARTS);
  prepareEnter(parts);

  const springs = {
    x: spring(sf.state.x, target.x, 'morph', (v) => {
      sf.state.x = v;
      sf.set({});
      clip();
    }, { eps: 0.3 }),
    y: spring(sf.state.y, target.y, 'morph', (v) => {
      sf.state.y = v;
      sf.set({});
      clip();
    }, { eps: 0.3 }),
    w: spring(sf.state.w, target.w, 'morph', (v) => {
      sf.state.w = v;
      sf.set({});
      clip();
    }, { eps: 0.3 }),
    h: spring(sf.state.h, target.h, 'gentle', (v) => {
      sf.state.h = v;
      sf.set({});
      clip();
    }, { eps: 0.3 }),
    r: spring(sf.state.r, LOOKS.panel.r, 'morph', (v) => {
      sf.state.r = v;
      sf.set({});
      clip();
    }, { eps: 0.05 }),
  };
  const look = sf.to({ bg: LOOKS.panel.bg, bd: LOOKS.panel.bd, shadow: LOOKS.panel.shadow, bw: LOOKS.panel.bw });

  // Data that lands mid-flight changes the panel's height: the surface retargets (never a jump).
  let observer: ResizeObserver | null = null;
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => {
      const next = boxOf(panel);
      if (Math.abs(next.h - toBox.h) < 0.5 && Math.abs(next.w - toBox.w) < 0.5) return;
      toBox = next;
      const t = rel(next, origin);
      springs.w.retarget(t.w);
      springs.h.retarget(t.h);
    });
    observer.observe(panel);
  }
  // Blocks that mount after the panel opened (the columns, once read) enter too.
  let mutations: MutationObserver | null = null;
  if (typeof MutationObserver !== 'undefined') {
    mutations = new MutationObserver((records) => {
      const added: HTMLElement[] = [];
      for (const record of records) for (const node of Array.from(record.addedNodes)) if (node instanceof HTMLElement && node.parentElement === panel) added.push(node);
      if (added.length) {
        prepareEnter(added);
        void enter(added, { stagger: 40 });
      }
    });
    mutations.observe(panel, { childList: true });
  }

  let cancelled = false;
  const finish = () => {
    observer?.disconnect();
    mutations?.disconnect();
    panel.classList.remove('kel-motion-bare');
    panel.style.clipPath = '';
    sf.remove();
  };
  void waitMotion(120).then(() => {
    if (!cancelled) void enter(parts, { stagger: 40 });
  });
  void Promise.all([springs.x.finished, springs.y.finished, springs.w.finished, springs.h.finished, springs.r.finished, look]).then(() => {
    if (!cancelled) finish();
  });
  return {
    cancel: () => {
      if (cancelled) return;
      cancelled = true;
      Object.values(springs).forEach((h) => h.stop());
      finish();
      for (const part of parts) {
        part.style.opacity = '';
        part.style.filter = '';
        part.style.transform = '';
      }
    },
  };
};

/**
 * §10.3 close: the panel's content leaves together (100 ms); the surface shrinks back into the card
 * (width on `snappy`, height on `morph`) carrying the card's content in; the card stays hidden until
 * the surface lands. The panel has already unmounted; its snapshot stands in for it.
 */
export const closeDetailMorph = async (stack: HTMLElement, panel: Snapshot | null, card: HTMLElement | null): Promise<void> => {
  if (!panel) return;
  if (isReducedMotion() || !card || !card.isConnected) {
    await exitGhostAt(panel, { ms: MOTION.reducedOutMs, scale: 1, blur: 0 });
    return;
  }
  const toBox = boxOf(card);
  const toLook = card.classList.contains('kel-wc-overflow') ? LOOKS.tile : LOOKS.card;
  const { sf, origin } = stackSurface(stack, panel.box, LOOKS.panel);
  fitCopy(sf, panel.ghost, panel.box, LOOKS.panel);
  const inner = Array.from(panel.ghost.children) as HTMLElement[];
  const out = exit(inner.length ? inner : panel.ghost, { ms: 100 });
  const cardCopy = ghostOf(card);
  cardCopy.classList.remove('is-selected');
  fitCopy(sf, cardCopy, toBox, toLook);
  prepareEnter(cardCopy);
  card.classList.add('kel-motion-hidden');
  await out;
  panel.ghost.remove();
  const t = rel(toBox, origin);
  const move = sf.to({ x: t.x, y: t.y, w: t.w, h: t.h, r: toLook.r, bg: toLook.bg, bd: toLook.bd, shadow: 0, bw: toLook.bw }, { presets: { w: 'snappy', h: 'morph' } });
  const inP = waitMotion(50).then(() => enter(cardCopy, { stagger: 25 }));
  await Promise.all([move, inP]);
  card.classList.remove('kel-motion-hidden');
  sf.remove();
};

/* ─────────────────────────────── the hand-off ─────────────────────────────── */

/**
 * §10.2: after a beat (D-78: ~0.4 s after the line appeared) the card lifts out of the in-thread
 * line: a surface with the line's look flies up (`gentle` x, `morph` y) and becomes the new card; the
 * blue working dot flies separately (`gentle` x, `snappy` y) and lands as the card's status dot. The
 * line's content leaves, the card's enters mid-flight, and the line re-forms 160 ms after the card
 * has left it.
 */
export const handoffFlight = async (line: HTMLElement, card: HTMLElement, waitMs: number): Promise<void> => {
  if (isReducedMotion()) {
    await crossFade(null, card);
    return;
  }
  card.classList.add('kel-motion-hidden');
  await waitMotion(Math.max(0, waitMs));
  if (!line.isConnected || !card.isConnected) {
    card.classList.remove('kel-motion-hidden');
    return;
  }
  const layer = motionLayer();
  const fromBox = boxOf(line);
  const toBox = boxOf(card);
  const sf = surface(layer, { ...fromBox, ...LOOKS.line });
  const lineCopy = ghostOf(line);
  fitCopy(sf, lineCopy, fromBox, LOOKS.line);
  const cardCopy = ghostOf(card);
  fitCopy(sf, cardCopy, toBox, LOOKS.card);
  const cardParts = partsOf(cardCopy, [':scope .kel-wc__title-row', ':scope .kel-wc-progress', ':scope .kel-wc__state-row']);
  prepareEnter(cardParts);
  // The accent moves: the dot flies on its own.
  const lineDot = line.querySelector<HTMLElement>('.kel-wl__lead .kel-wc-dot');
  const cardDot = card.querySelector<HTMLElement>('.kel-wc__state-row .kel-wc-dot');
  const copyDot = cardCopy.querySelector<HTMLElement>('.kel-wc-dot');
  if (copyDot) copyDot.style.visibility = 'hidden';
  let dotFlight: Promise<void> = Promise.resolve();
  if (lineDot && cardDot) {
    const node = ghostOf(lineDot);
    dotFlight = waitMotion(20).then(() => fly(node, boxOf(lineDot), boxOf(cardDot), { px: 'gentle', py: 'snappy' }));
  }
  line.style.visibility = 'hidden';
  void exit(lineCopy, { ms: 110 });
  const move = sf.to({ ...toBox, r: LOOKS.card.r, bg: LOOKS.card.bg, bd: LOOKS.card.bd, bw: LOOKS.card.bw }, { presets: { x: 'gentle', y: 'morph', w: 'morph', h: 'morph' } });
  const contentIn = waitMotion(140).then(() => enter(cardParts, { stagger: 35 }));
  const lineBack = waitMotion(160).then(() => {
    line.style.visibility = '';
    prepareEnter(line, { y: 0, blur: 4 });
    return enter(line, { y: 0, blur: 4, ms: 200 });
  });
  await Promise.all([move, contentIn, dotFlight, lineBack]);
  card.classList.remove('kel-motion-hidden');
  sf.remove();
};

/** A card that arrives with no line to lift from: it reveals from its top edge, content following. */
export const revealCard = (card: HTMLElement): void => {
  const parts = partsOf(card, [':scope .kel-wc__title-row', ':scope .kel-wc-progress', ':scope .kel-wc__state-row']);
  if (isReducedMotion()) {
    void crossFade(null, card);
    return;
  }
  prepareEnter(parts);
  card.style.clipPath = 'inset(0 0 100% 0 round 10px)';
  void spring(0, 1, 'morph', (v) => {
    frameWrite(card, () => {
      card.style.clipPath = v >= 0.999 ? '' : `inset(0 0 ${((1 - v) * 100).toFixed(2)}% 0 round 10px)`;
    });
  }, { eps: 0.001 }).finished.then(() => {
    card.style.clipPath = '';
  });
  void waitMotion(90).then(() => enter(parts, { stagger: 35 }));
};

/** §10.2 step 4: a card that no longer fits morphs into the "+N more" tile (card surface → tile). */
export const cardIntoTile = async (stack: HTMLElement, card: Snapshot, tile: HTMLElement): Promise<void> => {
  if (isReducedMotion()) {
    await exitGhostAt(card, { ms: MOTION.reducedOutMs, scale: 1, blur: 0 });
    return;
  }
  const toBox = boxOf(tile);
  const { sf, origin } = stackSurface(stack, card.box, LOOKS.card);
  fitCopy(sf, card.ghost, card.box, LOOKS.card);
  const tileCopy = ghostOf(tile);
  fitCopy(sf, tileCopy, toBox, LOOKS.tile);
  const tileParts = partsOf(tileCopy, [':scope .kel-wc-overflow__label', ':scope .kel-wc-overflow__dots']);
  prepareEnter(tileParts);
  tile.classList.add('kel-motion-hidden');
  void exit(card.ghost, { ms: 110 });
  const t = rel(toBox, origin);
  const move = sf.to({ ...t, r: LOOKS.tile.r, bg: LOOKS.tile.bg, bd: LOOKS.tile.bd }, { presets: { w: 'snappy' } });
  const inP = waitMotion(90).then(() => enter(tileParts, { stagger: 30 }));
  await Promise.all([move, inP]);
  tile.classList.remove('kel-motion-hidden');
  sf.remove();
};

/* ─────────────────────────────── "+N more" ─────────────────────────────── */

/** §10.10 open: the menu grows out of the tile (height on `gentle`); sections and cards enter 30 ms apart. */
export const openMenuMorph = (stack: HTMLElement, tile: HTMLElement, menu: HTMLElement): void => {
  if (isReducedMotion()) {
    void crossFade(null, menu);
    return;
  }
  const fromBox = boxOf(tile);
  const toBox = boxOf(menu);
  const { sf, origin } = stackSurface(stack, fromBox, LOOKS.tileOpen);
  const copy = ghostOf(menu);
  fitCopy(sf, copy, toBox, LOOKS.menu);
  const parts = partsOf(copy, [':scope > .kel-wc-menu__section, :scope > .kel-wc--menu']);
  prepareEnter(parts);
  menu.classList.add('kel-motion-hidden');
  const t = rel(toBox, origin);
  const move = sf.to({ ...t, r: LOOKS.menu.r, bg: LOOKS.menu.bg, bd: LOOKS.menu.bd, shadow: 1, bw: 1 }, { presets: { x: 'morph', w: 'morph', h: 'gentle' } });
  const inP = waitMotion(90).then(() => enter(parts, { stagger: 30 }));
  void Promise.all([move, inP]).then(() => {
    menu.classList.remove('kel-motion-hidden');
    sf.remove();
  });
};

/** §10.10 close: the menu's content leaves, and the surface folds back into the tile, carrying its label and dots in. */
export const closeMenuMorph = async (stack: HTMLElement, menu: Snapshot | null, tile: HTMLElement | null): Promise<void> => {
  if (!menu) return;
  if (isReducedMotion() || !tile || !tile.isConnected) {
    await exitGhostAt(menu, { ms: MOTION.reducedOutMs, scale: 1, blur: 0 });
    return;
  }
  const toBox = boxOf(tile);
  const { sf, origin } = stackSurface(stack, menu.box, LOOKS.menu);
  fitCopy(sf, menu.ghost, menu.box, LOOKS.menu);
  const out = exit(Array.from(menu.ghost.children) as HTMLElement[], { ms: 90 });
  const tileCopy = ghostOf(tile);
  fitCopy(sf, tileCopy, toBox, LOOKS.tile);
  const parts = partsOf(tileCopy, [':scope .kel-wc-overflow__label', ':scope .kel-wc-overflow__dots']);
  prepareEnter(parts);
  tile.classList.add('kel-motion-hidden');
  await out;
  const t = rel(toBox, origin);
  const move = sf.to({ ...t, r: LOOKS.tile.r, bg: LOOKS.tile.bg, bd: LOOKS.tile.bd, shadow: 0, bw: 1 }, { presets: { w: 'snappy', h: 'morph' } });
  const inP = waitMotion(120).then(() => enter(parts, { stagger: 30 }));
  await Promise.all([move, inP]);
  tile.classList.remove('kel-motion-hidden');
  sf.remove();
};

/* ─────────────────────────────── inside the panel ─────────────────────────────── */

/**
 * The panel's own height eases to its new size (§10.6) while its blocks FLIP: the panel takes its
 * final height at once and goes bare; a surface with its look, behind it in the stack, springs from
 * the old height to the new one.
 */
export const panelHeightEase = (panel: HTMLElement, oldHeight: number): void => {
  if (isReducedMotion()) return;
  const stack = panel.closest<HTMLElement>('.kel-wc-stack');
  if (!stack) return;
  const box = boxOf(panel);
  if (Math.abs(box.h - oldHeight) < 1) return;
  const { sf } = stackSurface(stack, { ...box, h: oldHeight }, LOOKS.panel);
  panel.classList.add('kel-motion-bare');
  // Blocks FLIPping up from below the panel's new edge stay visible over the surface meanwhile.
  const overflow = panel.style.overflow;
  panel.style.overflow = 'visible';
  void sf.to({ h: box.h }, { preset: 'morph' }).then(() => {
    panel.classList.remove('kel-motion-bare');
    panel.style.overflow = overflow;
    sf.remove();
  });
};

/**
 * §10.6 step 2: the question section's surface morphs into the "You answered" line (height on
 * `morph`, amber border → neutral). The line is the resting end of the question: it settles in.
 */
export const answeredMorph = (question: Snapshot | null, line: HTMLElement): void => {
  void morphInto({ from: question, to: line, fromLook: LOOKS.needs, toLook: LOOKS.section, settle: true, draw: '.kel-na-answered__check' });
};
