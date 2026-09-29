/**
 * MOTION.md §6 — indicators that stretch. A selection highlight is ONE element whose two edges ride
 * two springs: the leading edge (toward the target) on `micro`, the trailing edge on `snappy`
 * starting ~35 ms later, so it stretches toward its new place and the tail catches up. The selected
 * row's own background and border are switched off while the indicator draws them (one highlight,
 * never a second fading one). The indicator measures once per move and only writes per frame.
 */
import { useLayoutEffect, useRef, type RefObject } from 'react';
import { isReducedMotion } from './reduced';
import { frameWrite, spring, tween, type PresetName, type SpringHandle } from './spring';

export type Axis = 'x' | 'y';
export type Span = { a: number; b: number; cross: number; crossSize: number };

type State = { a: number; b: number; cross: number; crossSize: number; ha: SpringHandle | null; hb: SpringHandle | null; placed: boolean };

export type EdgeIndicator = {
  /** Jump to a span (first paint, resize). */
  place: (span: Span) => void;
  /** Stretch to a span. */
  to: (span: Span, opts?: { lead?: PresetName; trail?: PresetName; trailDelay?: number }) => Promise<void>;
  hide: () => void;
  readonly state: Readonly<State>;
};

export const edgeIndicator = (pill: HTMLElement, axis: Axis): EdgeIndicator => {
  const st: State = { a: 0, b: 0, cross: 0, crossSize: 0, ha: null, hb: null, placed: false };
  const draw = () =>
    frameWrite(pill, () => {
      const size = Math.max(0, st.b - st.a);
      if (axis === 'y') {
        pill.style.transform = `translate(${st.cross.toFixed(2)}px, ${st.a.toFixed(2)}px)`;
        pill.style.height = `${size.toFixed(2)}px`;
        pill.style.width = `${st.crossSize.toFixed(2)}px`;
      } else {
        pill.style.transform = `translate(${st.a.toFixed(2)}px, ${st.cross.toFixed(2)}px)`;
        pill.style.width = `${size.toFixed(2)}px`;
        pill.style.height = `${st.crossSize.toFixed(2)}px`;
      }
    });
  const api: EdgeIndicator = {
    get state() {
      return st;
    },
    place(span) {
      st.ha?.stop();
      st.hb?.stop();
      st.ha = null;
      st.hb = null;
      Object.assign(st, { a: span.a, b: span.b, cross: span.cross, crossSize: span.crossSize, placed: true });
      pill.style.opacity = '';
      pill.style.visibility = 'visible';
      draw();
    },
    to(span, opts = {}) {
      if (!st.placed) {
        api.place(span);
        return Promise.resolve();
      }
      st.cross = span.cross;
      st.crossSize = span.crossSize;
      if (isReducedMotion()) {
        // Blink across: out at the old place, in at the new.
        return tween(1, 0, 70, 'linear', (v) => (pill.style.opacity = v.toFixed(3))).finished.then(() => {
          api.place(span);
          pill.style.opacity = '0';
          return tween(0, 1, 110, 'linear', (v) => (pill.style.opacity = v >= 1 ? '' : v.toFixed(3))).finished;
        });
      }
      const forward = span.b >= st.b;
      const lead = opts.lead ?? 'micro';
      const trail = opts.trail ?? 'snappy';
      const delay = opts.trailDelay ?? 35;
      const pa = forward ? trail : lead;
      const pb = forward ? lead : trail;
      if (st.ha && !st.ha.done) st.ha.retarget(span.a, pa);
      else st.ha = spring(st.a, span.a, pa, (v) => {
        st.a = v;
        draw();
      }, { delay: forward ? delay : 0, eps: 0.05 });
      if (st.hb && !st.hb.done) st.hb.retarget(span.b, pb);
      else st.hb = spring(st.b, span.b, pb, (v) => {
        st.b = v;
        draw();
      }, { delay: forward ? 0 : delay, eps: 0.05 });
      draw();
      return Promise.all([st.ha.finished, st.hb.finished]).then((): void => undefined);
    },
    hide() {
      st.placed = false;
      pill.style.visibility = 'hidden';
    },
  };
  return api;
};

/**
 * A target's span inside its container, in layout pixels: offsets walked up to the container, so a
 * popover that is still scaling in (or any transform) never skews the pill.
 */
export const spanIn = (target: Element, container: HTMLElement, axis: Axis): Span => {
  const el = target as HTMLElement;
  let left = 0;
  let top = 0;
  let node: HTMLElement | null = el;
  while (node && node !== container) {
    left += node.offsetLeft;
    top += node.offsetTop;
    const parent = node.offsetParent as HTMLElement | null;
    if (parent && parent !== container && !container.contains(parent)) {
      node = null;
      break;
    }
    // Scrolling ancestors between the row and the track move it too.
    let walk = node.parentElement;
    while (walk && walk !== parent && walk !== container) {
      left -= walk.scrollLeft;
      top -= walk.scrollTop;
      walk = walk.parentElement;
    }
    node = parent;
  }
  if (node !== container) {
    const t = el.getBoundingClientRect();
    const c = container.getBoundingClientRect();
    left = t.left - c.left - container.clientLeft + container.scrollLeft;
    top = t.top - c.top - container.clientTop + container.scrollTop;
  }
  const width = el.offsetWidth;
  const height = el.offsetHeight;
  return axis === 'y' ? { a: top, b: top + height, cross: left, crossSize: width } : { a: left, b: left + width, cross: top, crossSize: height };
};

/**
 * Drive a pill (rendered by the component, absolutely positioned at 0,0 in `containerRef`) to the
 * element matching `activeSelector`. `trigger` is the real selection (pathname, tab id); it moves
 * only when that changes, never on a re-render. Resizes snap.
 */
export const useEdgeIndicator = (
  containerRef: RefObject<HTMLElement | null>,
  pillRef: RefObject<HTMLElement | null>,
  activeSelector: string,
  trigger: unknown,
  opts: { axis?: Axis; enabled?: boolean } = {}
): void => {
  const axis = opts.axis ?? 'y';
  const enabled = opts.enabled !== false;
  const indicator = useRef<EdgeIndicator | null>(null);

  useLayoutEffect(() => {
    const pill = pillRef.current;
    // The pill lives in its track; the track's own ref may not be attached yet when this runs (child
    // effects run before the parent's ref is set), so the pill's parent is the track.
    const container = (pill?.parentElement as HTMLElement | null) ?? containerRef.current;
    if (!container || !pill || !enabled) return;
    if (!indicator.current) indicator.current = edgeIndicator(pill, axis);
    container.classList.add('kel-edge-host');
    const target = container.querySelector(activeSelector);
    if (!target) {
      indicator.current.hide();
      return;
    }
    void indicator.current.to(spanIn(target, container, axis));
  }, [trigger, enabled, activeSelector]);

  useLayoutEffect(() => {
    const container = (pillRef.current?.parentElement as HTMLElement | null) ?? containerRef.current;
    if (!container || !enabled || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      const target = container.querySelector(activeSelector);
      if (target && indicator.current) indicator.current.place(spanIn(target, container, axis));
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [enabled, activeSelector]);
};
