/**
 * MOTION.md §10.1 — a message arriving while Nick watches.
 * - His own message: the sent words fly from the composer to their place (`gentle` x, `morph` y). The
 *   copy is laid out at the message's final width, so it never re-wraps on landing; the time enters.
 * - Kel's reply: the Kel mark flies from the Thinking row (which just left) to the reply's avatar slot
 *   (`morph` x, `gentle` y) and stops pulsing; the time enters. With no Thinking row, they just enter.
 * First paint never animates.
 */
import { useLayoutEffect, useRef, type RefObject } from 'react';
import { useArrival } from './arrival';
import { enter, prepareEnter } from './fx';
import { boxOf, fly, ghostOf, takeSnapshot } from './morph';
import { isReducedMotion } from './reduced';

export const THINKING_MARK = 'kel:thinking-mark';

export const useMessageArrival = (turnRef: RefObject<HTMLElement | null>, kind: 'user' | 'kel' | 'other'): void => {
  const arrived = useArrival();
  const done = useRef(false);
  useLayoutEffect(() => {
    if (done.current) return;
    done.current = true;
    const turn = turnRef.current;
    if (!arrived || !turn || kind === 'other') return;
    const time = turn.querySelector<HTMLElement>(':scope > .kel-shell-message-meta time');
    if (time) {
      prepareEnter(time, { y: 4, blur: 4 });
      void enter(time, { y: 4, blur: 4, delay: kind === 'user' ? 180 : 120 });
    }
    if (isReducedMotion()) return;
    if (kind === 'kel') {
      const avatar = turn.querySelector<HTMLElement>(':scope > .kel-shell-message-meta .kel-shell-message-avatar img, :scope > .kel-shell-message-meta > img');
      const mark = takeSnapshot(THINKING_MARK);
      if (!avatar) return;
      if (!mark) {
        prepareEnter(avatar, { y: 0, blur: 4, scale: 0.8 });
        void enter(avatar, { y: 0, blur: 4, scale: 0.8 });
        return;
      }
      avatar.style.visibility = 'hidden';
      void fly(mark.ghost, mark.box, boxOf(avatar), { px: 'morph', py: 'gentle' }).then(() => {
        avatar.style.visibility = '';
      });
      return;
    }
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
