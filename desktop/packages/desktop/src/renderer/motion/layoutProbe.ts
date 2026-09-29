/**
 * The no-layout-shift rule, checked mechanically (Nick, 2026-09-29; MOTION.md §8.1). A capture records
 * the boxes (and words) of key elements on every frame of a moment. After the transition ends nothing
 * may move by more than 1 px or change its words; during it, positions change only along a smooth
 * path — a frame-to-frame jump far larger than its neighbours is a snap (an icon drawn on the wrong
 * line and corrected, a header that re-lays out once the card is full size).
 */
export type ProbeBox = { x: number; y: number; w: number; h: number };
export type ProbeFrame = { t: number; boxes: Record<string, ProbeBox | null>; text?: Record<string, string | null> };

export type Violation = { key: string; t: number; kind: 'moved-after-settle' | 'text-after-settle' | 'jump'; detail: string };

export type ProbeOptions = {
  /** Time (ms) from which everything must stay put. */
  settledAfter: number;
  /** Allowed drift after settling (px). */
  tolerance?: number;
  /** A per-frame move is a jump when it exceeds this many px AND jumpRatio × the neighbouring moves. */
  jumpMinPx?: number;
  jumpRatio?: number;
};

const dist = (a: ProbeBox, b: ProbeBox) =>
  Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y), Math.abs(a.x + a.w - (b.x + b.w)), Math.abs(a.y + a.h - (b.y + b.h)));

export const layoutViolations = (frames: ProbeFrame[], opts: ProbeOptions): Violation[] => {
  const tolerance = opts.tolerance ?? 1;
  const jumpMin = opts.jumpMinPx ?? 12;
  const ratio = opts.jumpRatio ?? 4;
  const out: Violation[] = [];
  const keys = new Set<string>();
  for (const frame of frames) for (const key of Object.keys(frame.boxes)) keys.add(key);

  for (const key of keys) {
    const series = frames.map((f) => ({ t: f.t, box: f.boxes[key] ?? null, text: f.text?.[key] ?? null }));
    // After settling: nothing moves, nothing re-words.
    const settled = series.filter((s) => s.t >= opts.settledAfter);
    const anchor = settled.find((s) => s.box);
    if (anchor?.box) {
      for (const s of settled) {
        if (!s.box) continue;
        const d = dist(anchor.box, s.box);
        if (d > tolerance) {
          out.push({ key, t: s.t, kind: 'moved-after-settle', detail: `${d.toFixed(1)} px from its settled box` });
          break;
        }
      }
      const words = settled.find((s) => s.text !== null)?.text ?? null;
      for (const s of settled) {
        if (s.text !== null && words !== null && s.text !== words) {
          out.push({ key, t: s.t, kind: 'text-after-settle', detail: `"${words}" → "${s.text}"` });
          break;
        }
      }
    }
    // During: no discontinuity.
    const moves: Array<{ t: number; d: number }> = [];
    for (let i = 1; i < series.length; i++) {
      const a = series[i - 1].box;
      const b = series[i].box;
      moves.push({ t: series[i].t, d: a && b ? dist(a, b) : 0 });
    }
    for (let i = 0; i < moves.length; i++) {
      const d = moves[i].d;
      if (d < jumpMin) continue;
      const before = i > 0 ? moves[i - 1].d : 0;
      const after = i + 1 < moves.length ? moves[i + 1].d : 0;
      if (d > ratio * Math.max(before, after, 1)) {
        out.push({ key, t: moves[i].t, kind: 'jump', detail: `${d.toFixed(1)} px in one frame (neighbours ${before.toFixed(1)} / ${after.toFixed(1)})` });
      }
    }
  }
  return out;
};

/** In-page sampler (the capture script evaluates this): boxes and words of each selector. */
export const sampleBoxes = (selectors: Record<string, string>): Pick<ProbeFrame, 'boxes' | 'text'> => {
  const boxes: Record<string, ProbeBox | null> = {};
  const text: Record<string, string | null> = {};
  for (const [key, selector] of Object.entries(selectors)) {
    const el = document.querySelector(selector);
    if (!el) {
      boxes[key] = null;
      text[key] = null;
      continue;
    }
    const r = el.getBoundingClientRect();
    boxes[key] = r.width || r.height ? { x: r.left, y: r.top, w: r.width, h: r.height } : null;
    text[key] = (el.textContent ?? '').trim();
  }
  return { boxes, text };
};
