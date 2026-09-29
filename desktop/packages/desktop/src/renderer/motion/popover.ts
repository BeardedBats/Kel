/**
 * MOTION.md §10.12 — every Kel popover moves alike. It grows from its trigger's corner (scale
 * 0.94 → 1 on `snappy`, a 140 ms fade, 4 px of blur clearing) with its rows entering 18 ms apart,
 * and closes in 120 ms (opacity, scale 0.97, 3 px blur) from a static copy, so the real menu can
 * unmount at once.
 */
import { useLayoutEffect, type RefObject } from 'react';
import { enter, prepareEnter, setFx } from './fx';
import { exitGhost } from './morph';
import { isReducedMotion } from './reduced';
import { frameWrite, spring, tween, waitMotion } from './spring';

export type Origin = 'top left' | 'top right' | 'bottom left' | 'bottom right';

export const popIn = async (menu: HTMLElement, origin: Origin = 'top left', rowsSelector = ':scope > *'): Promise<void> => {
  // The stretching pill is positioned by its own transform; it is never one of the rows that enter.
  const rows = Array.from(menu.querySelectorAll<HTMLElement>(rowsSelector)).filter((el) => !el.classList.contains('kel-edge-pill')).slice(0, 14);
  if (isReducedMotion()) {
    setFx(menu, { o: 0 });
    await tween(0, 1, 140, 'linear', (v) => setFx(menu, { o: v })).finished;
    setFx(menu, {});
    return;
  }
  menu.style.transformOrigin = origin;
  const up = origin.startsWith('bottom') ? 1 : -1;
  const st = { s: 0.94, o: 0 };
  const draw = () =>
    frameWrite(menu, () => {
      menu.style.transform = st.s >= 0.9995 ? '' : `scale(${st.s.toFixed(4)})`;
      menu.style.opacity = st.o >= 0.999 ? '' : st.o.toFixed(3);
      menu.style.filter = st.o >= 0.999 ? '' : `blur(${((1 - st.o) * 4).toFixed(2)}px)`;
    });
  draw();
  prepareEnter(rows, { y: 4 * -up, blur: 4 });
  const scale = spring(0.94, 1, 'snappy', (v) => {
    st.s = v;
    draw();
  }, { eps: 0.0005 }).finished;
  const fade = tween(0, 1, 140, 'out', (v) => {
    st.o = v;
    draw();
  }).finished;
  await waitMotion(40);
  await Promise.all([scale, fade, enter(rows, { stagger: 18, ms: 180, y: 4 * -up, blur: 4 })]);
  menu.style.transform = '';
  menu.style.filter = '';
  menu.style.opacity = '';
};

/** Grow in on mount; leave as a fading copy on unmount. */
export const usePopover = (ref: RefObject<HTMLElement | null>, origin: Origin = 'top left', rowsSelector?: string): void => {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    void popIn(el, origin, rowsSelector);
    return () => {
      void exitGhost(el, { ms: 120, scale: 0.97, blur: 3 });
    };
  }, []);
};
