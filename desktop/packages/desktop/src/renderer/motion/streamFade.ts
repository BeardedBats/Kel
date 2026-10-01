/** Reveal only newly arriving reply text. Source layout and old text remain untouched. */
import { useLayoutEffect, useRef } from 'react';
import { useArrival } from './arrival';
import { useReducedMotion } from './reduced';
import { animateString, type StringMotionHandle } from './stringMotion';

export const commonTextPrefix = (a: string, b: string): number => {
  let i = 0;
  while (i < Math.min(a.length, b.length) && a.charCodeAt(i) === b.charCodeAt(i)) i++;
  return i;
};

export const useStreamFade = (body: HTMLElement | null, enabled: boolean): void => {
  const arrived = useArrival();
  const reduced = useReducedMotion();
  const firstBody = useRef<HTMLElement | null>(null);
  useLayoutEffect(() => {
    if (!body || !enabled || typeof MutationObserver === 'undefined') return;
    const first = firstBody.current !== body;
    firstBody.current = body;
    if (reduced) return;
    let shown = body.textContent ?? '';
    let motion: StringMotionHandle | null = null;
    // Opening a chat shows history immediately. A new reply arriving later can reveal at mount.
    if (first && arrived) motion = animateString(body);
    const observer = new MutationObserver((records) => {
      const text = body.textContent ?? '';
      const keep = commonTextPrefix(shown, text);
      if (text === shown && records.some((record) => record.type === 'childList')) motion?.stop();
      if (text !== shown) {
        motion?.stop();
        // Markdown rewrites may change old text. Animate only append-only content.
        if (keep === shown.length && text.length > keep) motion = animateString(body, keep, text.length);
        shown = text;
      }
    });
    observer.observe(body, { subtree: true, childList: true, characterData: true });
    return () => { observer.disconnect(); motion?.stop(); };
  }, [body, enabled, reduced, arrived]);
};
