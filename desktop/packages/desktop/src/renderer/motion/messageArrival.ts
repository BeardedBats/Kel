/**
 * MOTION.md §10.1 — a message arriving while Nick watches.
 * - His own message: the sent words fly from the composer to their place (`gentle` x, `morph` y). The
 *   copy is laid out at the message's final width, so it never re-wraps on landing; the time enters.
 * - Kel's reply: its mark and time fade in, in place (no flight, no vertical move — FIX-0025, Nick:
 *   the mark flying up from the Thinking row read as a jump). The Thinking row fades out where it was,
 *   and the thread glides to make room (useAutoScroll).
 * First paint never animates.
 */
import { useLayoutEffect, useRef, type RefObject } from 'react';
import { useArrival } from './arrival';
import { enter, prepareEnter } from './fx';
import { boxOf, fly, ghostOf } from './morph';
import { isReducedMotion } from './reduced';

export const useMessageArrival = (turnRef: RefObject<HTMLElement | null>, kind: 'user' | 'kel' | 'other'): void => {
  const arrived = useArrival();
  const done = useRef(false);
  useLayoutEffect(() => {
    if (done.current) return;
    done.current = true;
    const turn = turnRef.current;
    if (!arrived || !turn || kind === 'other') return;
    if (kind === 'kel') {
      // The mark and the time arrive together, in their own places: opacity and a light blur only.
      const parts = Array.from(turn.querySelectorAll<HTMLElement>(':scope > .kel-shell-message-meta :is(.kel-shell-message-avatar, time), :scope > .kel-shell-message-meta > img'));
      prepareEnter(parts, { y: 0, blur: 4 });
      void enter(parts, { y: 0, blur: 4, ms: 220 });
      return;
    }
    const time = turn.querySelector<HTMLElement>(':scope > .kel-shell-message-meta time');
    if (time) {
      prepareEnter(time, { y: 4, blur: 4 });
      void enter(time, { y: 4, blur: 4, delay: 180 });
    }
    if (isReducedMotion()) return;
    // Nick's message: the words leave the composer and land as his message.
    const text = turn.querySelector<HTMLElement>('[data-testid="message-text-content"]');
    const composer = document.querySelector<HTMLTextAreaElement>('.sendbox-panel textarea');
    if (!text || !composer) return;
    const to = boxOf(text);
    const from = boxOf(composer);
    if (to.w <= 0 || from.w <= 0) return;
    const copy = ghostOf(text);
    copy.style.width = `${to.w}px`;
    const cs = getComputedStyle(text);
    copy.style.whiteSpace = cs.whiteSpace;
    copy.style.font = cs.font;
    copy.style.color = cs.color;
    text.style.visibility = 'hidden';
    const start = { x: from.x + 4, y: from.y + 4, w: to.w, h: to.h };
    void fly(copy, start, to, { px: 'gentle', py: 'morph' }).then(() => {
      text.style.visibility = '';
    });
  }, []);
};
