/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Sibling FLIP keyed to real ids (MOTION.md §4, §8). Children of the list carrying `data-flip-id`
 * slide from where they were to where layout put them. It only plays when `key` changes — a new id,
 * state or step — so a polling re-render never replays it. Layout is read once per commit; frames
 * only write transforms.
 */

import { useEffect, useLayoutEffect, useRef, type RefObject } from 'react';

import { prefersReducedMotion } from './reducedMotion';
import { Spring, type SpringName, type SpringPreset } from './spring';

type Point = { x: number; y: number };

type Tracked = {
  el: HTMLElement;
  layout: Point;
  x: Spring;
  y: Spring;
  written: Point;
};

export type FlipOptions = {
  preset?: SpringPreset | SpringName;
  /** Which children move. Defaults to `[data-flip-id]`; the id is that attribute's value. */
  selector?: string;
  idAttribute?: string;
};

function write(item: Tracked): void {
  const x = item.x.value;
  const y = item.y.value;
  item.written = { x, y };
  item.el.style.transform = x === 0 && y === 0 ? '' : `translate(${x}px, ${y}px)`;
}

export function useFlip(listRef: RefObject<HTMLElement | null>, key: unknown, options: FlipOptions = {}): void {
  const tracked = useRef(new Map<string, Tracked>());
  const lastKey = useRef<unknown>(key);
  const preset = options.preset ?? 'snappy';
  const selector = options.selector ?? '[data-flip-id]';
  const idAttribute = options.idAttribute ?? 'data-flip-id';

  const measure = (animate: boolean): void => {
    const list = listRef.current;
    if (!list) return;
    const reduced = prefersReducedMotion();
    const seen = new Set<string>();
    const elements = Array.from(list.querySelectorAll<HTMLElement>(selector));
    // Read every box first, then write, so the commit forces at most one layout.
    const boxes = elements.map((el) => el.getBoundingClientRect());
    elements.forEach((el, index) => {
      const id = el.getAttribute(idAttribute);
      if (!id) return;
      seen.add(id);
      const box = boxes[index];
      const previous = tracked.current.get(id);
      const offset = previous && previous.el === el ? previous.written : { x: 0, y: 0 };
      const layout = { x: box.left - offset.x, y: box.top - offset.y };
      if (!previous) {
        const item: Tracked = {
          el,
          layout,
          written: { x: 0, y: 0 },
          x: new Spring(0, { preset, onUpdate: () => write(item) }),
          y: new Spring(0, { preset, onUpdate: () => write(item) }),
        };
        tracked.current.set(id, item);
        return;
      }
      if (previous.el !== el) {
        previous.el.style.transform = '';
        previous.el = el;
      }
      const dx = previous.layout.x - layout.x;
      const dy = previous.layout.y - layout.y;
      previous.layout = layout;
      if (dx === 0 && dy === 0) return;
      if (!animate || reduced) {
        previous.x.jump(0);
        previous.y.jump(0);
        return;
      }
      previous.x.shift(dx);
      previous.y.shift(dy);
      previous.x.set(0);
      previous.y.set(0);
      write(previous);
    });
    for (const [id, item] of tracked.current) {
      if (seen.has(id)) continue;
      item.x.stop();
      item.y.stop();
      tracked.current.delete(id);
    }
  };

  // Every commit re-reads layout so stored boxes never go stale; only a new key animates.
  useLayoutEffect(() => {
    const changed = !Object.is(lastKey.current, key);
    lastKey.current = key;
    measure(changed);
  });

  useEffect(() => {
    // Resize snaps (MOTION.md §9); remember the new boxes so the next change starts from them.
    const onResize = () => measure(false);
    window.addEventListener('resize', onResize);
    const items = tracked.current;
    return () => {
      window.removeEventListener('resize', onResize);
      for (const item of items.values()) {
        item.x.stop();
        item.y.stop();
      }
    };
    // measure reads refs only; binding it once is intended.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
