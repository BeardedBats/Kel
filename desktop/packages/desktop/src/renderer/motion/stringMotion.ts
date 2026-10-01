/** String motion animates decorative ink copies, leaving source text, layout and selection intact. */
import { isReducedMotion } from './reduced';
import { addTask, motionNow, solveSpring, type SpringParams } from './spring';

export const STRING_MOTION = { staggerMs: 15, damping: 16, stiffness: 240, mass: 1.2, maxGlyphs: 24, maxMs: 1400 } as const;
const w = Math.sqrt(STRING_MOTION.stiffness / STRING_MOTION.mass);
const z = STRING_MOTION.damping / (2 * Math.sqrt(STRING_MOTION.stiffness * STRING_MOTION.mass));
const physics: SpringParams = { w, z, a: z * w, wd: w * Math.sqrt(1 - z * z), k: STRING_MOTION.stiffness, c: STRING_MOTION.damping };
export const stringProgress = (ms: number): number => 1 - solveSpring(physics, 1, 0, Math.max(0, ms) / 1000)[0];

export const graphemes = (text: string): Array<{ text: string; start: number; end: number }> => {
  const out: Array<{ text: string; start: number; end: number }> = [];
  if (Intl.Segmenter) {
    for (const part of new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(text)) out.push({ text: part.segment, start: part.index, end: part.index + part.segment.length });
  } else {
    let start = 0;
    for (const part of Array.from(text)) { out.push({ text: part, start, end: start + part.length }); start += part.length; }
  }
  return out;
};

type Registry = { set: (name: string, value: unknown) => void; delete: (name: string) => boolean };
type Highlight = { add: (range: Range) => void; delete: (range: Range) => void };
export type StringMotionHandle = { finished: Promise<void>; stop: () => void };
let serial = 0;

/** A burst animates at most 24 glyphs; its remainder stays readable immediately. */
export const animateString = (body: HTMLElement, start = 0, end = body.textContent?.length ?? 0, direction: 'enter' | 'exit' = 'enter'): StringMotionHandle => {
  const noop: StringMotionHandle = { finished: Promise.resolve(), stop: () => undefined };
  const globals = globalThis as unknown as { CSS?: { highlights?: Registry }; Highlight?: new () => Highlight };
  const registry = globals.CSS?.highlights;
  if (isReducedMotion() || !registry || !globals.Highlight || !Intl.Segmenter || !body.isConnected || end <= start) return noop;
  const doc = body.ownerDocument;
  const name = `kel-string-${++serial}`;
  const highlight = new globals.Highlight();
  const style = doc.createElement('style');
  style.textContent = `::highlight(${name}) { color: transparent; text-shadow: none; }`;
  const root = body.getRootNode() as Document | ShadowRoot;
  (root instanceof Document ? root.head : root).appendChild(style);
  const layer = doc.createElement('div');
  layer.className = 'kel-string-layer';
  layer.setAttribute('aria-hidden', 'true');
  layer.setAttribute('inert', '');
  layer.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2400;contain:strict;overflow:hidden;';
  doc.body.appendChild(layer);
  type Glyph = { ink: HTMLSpanElement; range: Range; delay: number; done: boolean };
  const glyphs: Glyph[] = [];
  // Keep decorative ink inside every scroll/clipping ancestor. Partially clipped glyphs use native
  // ink instead, so a top row cannot paint across the header or composer.
  const clip = { left: 0, top: 0, right: doc.defaultView!.innerWidth, bottom: doc.defaultView!.innerHeight };
  let ancestor: HTMLElement | null = body;
  while (ancestor) {
    const cs = getComputedStyle(ancestor);
    const box = ancestor.getBoundingClientRect();
    if (box.width && box.height) {
      if (/(auto|scroll|hidden|clip)/.test(cs.overflowX || cs.overflow)) { clip.left = Math.max(clip.left, box.left); clip.right = Math.min(clip.right, box.right); }
      if (/(auto|scroll|hidden|clip)/.test(cs.overflowY || cs.overflow)) { clip.top = Math.max(clip.top, box.top); clip.bottom = Math.min(clip.bottom, box.bottom); }
    }
    const parent = ancestor.parentElement;
    const ancestorRoot = ancestor.getRootNode();
    ancestor = parent ?? (ancestorRoot instanceof ShadowRoot ? ancestorRoot.host as HTMLElement : null);
  }
  const walker = doc.createTreeWalker(body, NodeFilter.SHOW_TEXT);
  let offset = 0;
  let node = walker.nextNode() as Text | null;
  while (node && glyphs.length < STRING_MOTION.maxGlyphs) {
    const parent = node.parentElement;
    const length = node.data.length;
    if (parent && offset + length > start && offset < end && !parent.closest('pre, code, .katex, svg, button, textarea')) {
      const from = Math.max(0, start - offset);
      const to = Math.min(length, end - offset);
      // Joining scripts need their full shaping context; keep their native ink.
      // Bound segmentation work even for a pasted book or a very large buffered response.
      const contextStart = Math.max(0, from - 32);
      const sample = node.data.slice(contextStart, Math.min(to, from + 512));
      if (!/[\u0600-\u0dff]/u.test(sample)) for (const segment of graphemes(sample)) {
        const part = { ...segment, start: segment.start + contextStart, end: segment.end + contextStart };
        if (glyphs.length >= STRING_MOTION.maxGlyphs) break;
        if (part.start < from || part.end > to || /^\s+$/u.test(part.text)) continue;
        const range = doc.createRange();
        range.setStart(node, part.start);
        range.setEnd(node, part.end);
        if (typeof range.getBoundingClientRect !== 'function') continue;
        const box = range.getBoundingClientRect();
        if (!box.width || !box.height || box.left < clip.left || box.right > clip.right || box.top < clip.top || box.bottom > clip.bottom) continue;
        const cs = getComputedStyle(parent);
        const ink = doc.createElement('span');
        ink.textContent = part.text;
        ink.className = 'kel-string-glyph';
        ink.style.cssText = `position:absolute;left:${box.left}px;top:${box.top}px;white-space:pre;pointer-events:none;user-select:none;transform-origin:50% 50%;will-change:transform,opacity;`;
        ink.style.font = cs.font;
        ink.style.fontSize = cs.fontSize;
        ink.style.fontFamily = cs.fontFamily;
        ink.style.fontWeight = cs.fontWeight;
        ink.style.fontStyle = cs.fontStyle;
        ink.style.letterSpacing = cs.letterSpacing;
        ink.style.color = cs.color;
        ink.style.lineHeight = `${box.height}px`;
        layer.appendChild(ink);
        highlight.add(range);
        glyphs.push({ ink, range, delay: glyphs.length * STRING_MOTION.staggerMs, done: false });
      }
    }
    offset += length;
    node = walker.nextNode() as Text | null;
  }
  if (direction === 'exit' && glyphs.length) {
    // Old-value ghosts may exceed the animation cap. Hide their remainder immediately; it must
    // never overlap the new label while these first glyphs leave.
    const whole = doc.createRange();
    whole.selectNodeContents(body);
    highlight.add(whole);
  }
  registry.set(name, highlight);
  let job: ReturnType<typeof addTask> | null = null;
  let stopped = false;
  const stopSelection = () => { if (doc.getSelection()?.type === 'Range') stop(); };
  const stop = () => {
    if (stopped) return;
    stopped = true;
    job?.cancel();
    registry.delete(name);
    style.remove();
    layer.remove();
    doc.removeEventListener('scroll', stop, true);
    doc.removeEventListener('pointerdown', stop, true);
    doc.removeEventListener('keydown', stop, true);
    doc.removeEventListener('selectionchange', stopSelection);
    doc.defaultView?.removeEventListener('resize', stop);
  };
  if (!glyphs.length) { stop(); return noop; }
  doc.addEventListener('scroll', stop, true);
  doc.addEventListener('pointerdown', stop, true);
  doc.addEventListener('keydown', stop, true);
  doc.addEventListener('selectionchange', stopSelection);
  doc.defaultView?.addEventListener('resize', stop);
  const t0 = motionNow();
  const paint = (now: number) => {
    if (isReducedMotion() || !body.isConnected) { stop(); return true; }
    let active = false;
    for (const glyph of glyphs) {
      if (glyph.done) continue;
      const elapsed = now - t0 - glyph.delay;
      const p = stringProgress(elapsed);
      const amount = direction === 'enter' ? 1 - p : p;
      glyph.ink.style.opacity = String(Math.min(1, Math.max(0, direction === 'enter' ? p : 1 - p)));
      glyph.ink.style.transform = `translateY(${(direction === 'enter' ? 8 : -8) * amount}px) rotateX(${(direction === 'enter' ? 80 : -80) * amount}deg)`;
      glyph.ink.style.filter = `blur(${Math.max(0, 3 * amount)}px)`;
      if (elapsed > 900 || now - t0 >= STRING_MOTION.maxMs) {
        glyph.done = true;
        glyph.ink.remove();
        if (direction === 'enter') highlight.delete(glyph.range);
      } else active = true;
    }
    if (!active) stop();
    return !active;
  };
  paint(t0);
  job = addTask(paint);
  return { finished: job.finished, stop };
};
