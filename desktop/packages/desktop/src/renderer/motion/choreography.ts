/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Enter and exit (MOTION.md §4–§5). Content enters out of a 6 px blur, staggered in reading order;
 * content leaves into a 4 px blur, all at once. Timed tweens on the Web Animations API, so they touch
 * only opacity, filter and transform. Under reduced motion both are plain fades.
 */

import { TWEEN, staggerDelay } from './easing';
import { prefersReducedMotion } from './reducedMotion';

function animate(el: Element, keyframes: Keyframe[], options: KeyframeAnimationOptions): Animation | null {
  if (typeof (el as HTMLElement).animate !== 'function') return null;
  return (el as HTMLElement).animate(keyframes, options);
}

function finished(animations: Array<Animation | null>): Promise<void> {
  return Promise.all(animations.map((animation) => animation?.finished.catch((): void => undefined))).then(
    (): void => undefined
  );
}

/** Bring `elements` in, staggered in the given order, after `delay` ms. */
export function enter(elements: Iterable<Element>, options: { delay?: number } = {}): Promise<void> {
  const list = Array.from(elements);
  const base = options.delay ?? 0;
  if (prefersReducedMotion()) {
    return finished(
      list.map((el) =>
        animate(el, [{ opacity: 0 }, { opacity: 1 }], {
          duration: TWEEN.reducedInMs,
          delay: base,
          easing: 'linear',
          fill: 'backwards',
        })
      )
    );
  }
  return finished(
    list.map((el, index) =>
      animate(
        el,
        [
          { opacity: 0, filter: 'blur(6px)', transform: 'translateY(6px)' },
          { opacity: 1, filter: 'blur(0px)', transform: 'translateY(0px)' },
        ],
        {
          duration: TWEEN.enterMs,
          delay: base + staggerDelay(index, list.length),
          easing: TWEEN.easeOut,
          fill: 'backwards',
        }
      )
    )
  );
}

/** Take `elements` out, together. They stay invisible afterwards until the caller removes them. */
export function exit(elements: Iterable<Element>): Promise<void> {
  const list = Array.from(elements);
  if (prefersReducedMotion()) {
    return finished(
      list.map((el) =>
        animate(el, [{ opacity: 1 }, { opacity: 0 }], {
          duration: TWEEN.reducedOutMs,
          easing: 'linear',
          fill: 'forwards',
        })
      )
    );
  }
  return finished(
    list.map((el) =>
      animate(
        el,
        [
          { opacity: 1, filter: 'blur(0px)', transform: 'translateY(0px)' },
          { opacity: 0, filter: 'blur(4px)', transform: 'translateY(-4px)' },
        ],
        { duration: TWEEN.exitMs, easing: TWEEN.easeIn, fill: 'forwards' }
      )
    )
  );
}

/**
 * Roll a label: the old words leave upward and the new ones arrive from below (7 px, 3 px blur).
 * Under reduced motion it is a 140 ms fade.
 */
export function rollLabel(outgoing: Element | null, incoming: Element): Promise<void> {
  if (prefersReducedMotion()) {
    return finished([
      outgoing && animate(outgoing, [{ opacity: 1 }, { opacity: 0 }], { duration: 140, fill: 'forwards' }),
      animate(incoming, [{ opacity: 0 }, { opacity: 1 }], { duration: 140, fill: 'backwards' }),
    ]);
  }
  return finished([
    outgoing &&
      animate(
        outgoing,
        [
          { opacity: 1, filter: 'blur(0px)', transform: 'translateY(0px)' },
          { opacity: 0, filter: 'blur(3px)', transform: 'translateY(-7px)' },
        ],
        { duration: TWEEN.exitMs, easing: TWEEN.easeIn, fill: 'forwards' }
      ),
    animate(
      incoming,
      [
        { opacity: 0, filter: 'blur(3px)', transform: 'translateY(7px)' },
        { opacity: 1, filter: 'blur(0px)', transform: 'translateY(0px)' },
      ],
      { duration: TWEEN.enterMs, easing: TWEEN.easeOut, fill: 'backwards' }
    ),
  ]);
}
