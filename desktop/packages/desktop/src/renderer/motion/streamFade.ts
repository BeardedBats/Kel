/**
 * MOTION.md §10.1 — a streamed reply's words arrive out of a light blur. Each new chunk (~150 ms of
 * text) fades in over 180 ms; words already shown never re-animate (§8). The text belongs to React
 * (inside the markdown's shadow root), so nothing is wrapped or moved: the new characters are painted
 * through the CSS Custom Highlight API in a few steps from transparent-and-blurred to sharp, so the
 * lines never jiggle. Where the API is missing the words simply appear.
 */
import { useEffect } from 'react';
import { isReducedMotion } from './reduced';
import { addTask, motionNow } from './spring';

type HighlightLike = { clear: () => void; add: (range: Range) => void };
type HighlightRegistry = { set: (name: string, highlight: HighlightLike) => void; get: (name: string) => HighlightLike | undefined };

const LEVELS = 4;
const FADE_MS = 180;
const NAME = (level: number) => `kel-stream-${level}`;

const registry = (): HighlightRegistry | null => {
  const css = (globalThis as unknown as { CSS?: { highlights?: HighlightRegistry } }).CSS;
  const Ctor = (globalThis as unknown as { Highlight?: new () => HighlightLike }).Highlight;
  if (!css?.highlights || !Ctor) return null;
  for (let level = 0; level < LEVELS; level++) if (!css.highlights.get(NAME(level))) css.highlights.set(NAME(level), new Ctor());
  return css.highlights;
};

const styled = new WeakSet<Node>();

const ensureStyle = (body: HTMLElement) => {
  const root = body.getRootNode() as ShadowRoot | Document;
  if (styled.has(root)) return;
  styled.add(root);
  const color = getComputedStyle(body).color || 'rgb(237, 242, 250)';
  const rgb = color.match(/\d+(\.\d+)?/g)?.slice(0, 3).join(', ') ?? '237, 242, 250';
  const style = document.createElement('style');
  style.dataset.kelStream = '';
  style.textContent = Array.from({ length: LEVELS }, (_, level) => {
    const p = (level + 0.5) / LEVELS; // 0 → 1
    const blur = (3 * (1 - p)).toFixed(2);
    return `::highlight(${NAME(level)}) { color: rgba(${rgb}, ${(p * 0.85).toFixed(3)}); text-shadow: 0 0 ${blur}px rgba(${rgb}, ${(0.35 + 0.4 * p).toFixed(3)}); }`;
  }).join('\n');
  (root instanceof Document ? root.head : root).appendChild(style);
};

type Chunk = { start: number; end: number; t0: number };

/** Map text offsets to a DOM Range inside `body` (text nodes in document order). */
const rangeFor = (body: HTMLElement, start: number, end: number): Range | null => {
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
  let pos = 0;
  let startNode: Text | null = null;
  let startOffset = 0;
  let node = walker.nextNode() as Text | null;
  while (node) {
    const len = node.data.length;
    if (!startNode && start < pos + len) {
      startNode = node;
      startOffset = start - pos;
    }
    if (startNode && end <= pos + len) {
      const range = document.createRange();
      range.setStart(startNode, startOffset);
      range.setEnd(node, end - pos);
      return range;
    }
    pos += len;
    node = walker.nextNode() as Text | null;
  }
  return null;
};

const commonPrefix = (a: string, b: string) => {
  const n = Math.min(a.length, b.length);
  let i = 0;
  while (i < n && a.charCodeAt(i) === b.charCodeAt(i)) i++;
  return i;
};

/**
 * Fade in whatever text is added to `body` after it first rendered (the reply streaming in). The
 * first content never animates (first paint).
 */
export const useStreamFade = (body: HTMLElement | null, enabled: boolean): void => {
  useEffect(() => {
    if (!body || !enabled || typeof MutationObserver === 'undefined') return;
    const highlights = registry();
    if (!highlights) return;
    let shown = body.textContent ?? '';
    let chunks: Chunk[] = [];
    let job: ReturnType<typeof addTask> | null = null;

    const paint = () => {
      const now = motionNow();
      chunks = chunks.filter((chunk) => now - chunk.t0 < FADE_MS);
      const byLevel: Range[][] = Array.from({ length: LEVELS }, (): Range[] => []);
      for (const chunk of chunks) {
        const level = Math.min(LEVELS - 1, Math.floor(((now - chunk.t0) / FADE_MS) * LEVELS));
        const range = rangeFor(body, chunk.start, chunk.end);
        if (range) byLevel[level].push(range);
      }
      for (let level = 0; level < LEVELS; level++) {
        const highlight = highlights.get(NAME(level));
        if (!highlight) continue;
        highlight.clear();
        for (const range of byLevel[level]) highlight.add(range);
      }
      return chunks.length === 0;
    };

    const observer = new MutationObserver(() => {
      if (isReducedMotion()) {
        shown = body.textContent ?? '';
        return;
      }
      const text = body.textContent ?? '';
      const keep = commonPrefix(shown, text);
      chunks = chunks.filter((chunk) => chunk.end <= keep);
      if (text.length > keep) {
        ensureStyle(body);
        chunks.push({ start: keep, end: text.length, t0: motionNow() });
      }
      shown = text;
      paint();
      if (!job || job.task.done) job = addTask(() => paint());
    });
    observer.observe(body, { subtree: true, childList: true, characterData: true });
    return () => {
      observer.disconnect();
      job?.cancel();
      chunks = [];
      paint();
    };
  }, [body, enabled]);
};
