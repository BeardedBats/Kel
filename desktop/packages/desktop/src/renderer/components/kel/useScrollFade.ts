/**
 * D-87.3 — soft scroll edges. A scrolling panel fades its content out at the bottom edge while there is
 * more below, and at the top edge once it has scrolled, so text never sits hard against a border and it is
 * clear there is more. The fade is a CSS mask on the scroll container itself (kel-shell.css,
 * `.kel-scroll-fade`), not an overlay, so there is no seam and it blends over the glass behind it.
 *
 * This hook only keeps two classes true to the element's scroll position: `kel-scroll-fade--below` while
 * content continues past the bottom, `kel-scroll-fade--above` once scrolled down. Fully scrolled to the
 * end there is no bottom fade, so the last item stays readable.
 */
import { useEffect, type RefObject } from 'react';

/** How close to an edge still counts as "at" it, so sub-pixel scroll positions never leave a faint fade. */
const EDGE_SLACK = 2;

export const scrollFadeState = (
  element: Pick<HTMLElement, 'scrollTop' | 'scrollHeight' | 'clientHeight'>
): { above: boolean; below: boolean } => ({
  above: element.scrollTop > EDGE_SLACK,
  below: element.scrollHeight - element.clientHeight - element.scrollTop > EDGE_SLACK,
});

export function useScrollFade(ref: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    element.classList.add('kel-scroll-fade');
    let frame = 0;
    const update = () => {
      frame = 0;
      const { above, below } = scrollFadeState(element);
      element.classList.toggle('kel-scroll-fade--above', above);
      element.classList.toggle('kel-scroll-fade--below', below);
    };
    const schedule = () => {
      if (frame) return;
      frame = typeof requestAnimationFrame === 'function' ? requestAnimationFrame(update) : (setTimeout(update, 16) as unknown as number);
    };
    update();
    element.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    // The content's height changes without the container resizing (a page swaps, a card expands, rows
    // load), so watch the children's size and the subtree, not just the element.
    const resize = typeof ResizeObserver === 'function' ? new ResizeObserver(schedule) : null;
    const watchChildren = () => {
      if (!resize) return;
      resize.disconnect();
      resize.observe(element);
      for (const child of Array.from(element.children)) resize.observe(child);
    };
    watchChildren();
    const mutations =
      typeof MutationObserver === 'function'
        ? new MutationObserver(() => {
            watchChildren();
            schedule();
          })
        : null;
    mutations?.observe(element, { childList: true, subtree: true });
    return () => {
      element.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      resize?.disconnect();
      mutations?.disconnect();
      if (frame && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(frame);
      element.classList.remove('kel-scroll-fade', 'kel-scroll-fade--above', 'kel-scroll-fade--below');
    };
  }, [ref]);
}
