/**
 * D-87.3 — soft scroll edges. The fade classes follow the real scroll position: a bottom fade only while
 * content continues below, a top fade only once scrolled, and nothing at all when the content fits.
 * jsdom has no layout, so the element's scroll metrics are set by hand.
 */
import React, { useRef } from 'react';
import { act, render, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { scrollFadeState, useScrollFade } from '@renderer/components/kel/useScrollFade';

const Panel: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  useScrollFade(ref);
  return (
    <div ref={ref} data-testid='panel'>
      <p>content</p>
    </div>
  );
};

const metrics = (element: HTMLElement, values: { scrollHeight: number; clientHeight: number; scrollTop?: number }) => {
  Object.defineProperty(element, 'scrollHeight', { configurable: true, value: values.scrollHeight });
  Object.defineProperty(element, 'clientHeight', { configurable: true, value: values.clientHeight });
  element.scrollTop = values.scrollTop ?? 0;
};

const scroll = (element: HTMLElement, scrollTop: number) =>
  act(() => {
    element.scrollTop = scrollTop;
    element.dispatchEvent(new Event('scroll'));
  });

describe('D-87.3 soft scroll edges', () => {
  it('knows the edges from the scroll metrics', () => {
    expect(scrollFadeState({ scrollTop: 0, scrollHeight: 400, clientHeight: 400 })).toEqual({ above: false, below: false });
    expect(scrollFadeState({ scrollTop: 0, scrollHeight: 900, clientHeight: 400 })).toEqual({ above: false, below: true });
    expect(scrollFadeState({ scrollTop: 250, scrollHeight: 900, clientHeight: 400 })).toEqual({ above: true, below: true });
    expect(scrollFadeState({ scrollTop: 500, scrollHeight: 900, clientHeight: 400 })).toEqual({ above: true, below: false });
    // Sub-pixel leftovers at the end do not keep a faint fade over the last item.
    expect(scrollFadeState({ scrollTop: 499.5, scrollHeight: 900, clientHeight: 400 }).below).toBe(false);
  });

  it('fades the bottom only while the content overflows, and the top only once scrolled', async () => {
    const { getByTestId } = render(<Panel />);
    const panel = getByTestId('panel');
    expect(panel.classList.contains('kel-scroll-fade')).toBe(true);

    // Content that fits: no fade at either edge.
    metrics(panel, { scrollHeight: 400, clientHeight: 400 });
    scroll(panel, 0);
    await waitFor(() => expect(panel.classList.contains('kel-scroll-fade--below')).toBe(false));
    expect(panel.classList.contains('kel-scroll-fade--above')).toBe(false);

    // More below: the bottom edge fades, the top does not.
    metrics(panel, { scrollHeight: 1200, clientHeight: 400 });
    scroll(panel, 0);
    await waitFor(() => expect(panel.classList.contains('kel-scroll-fade--below')).toBe(true));
    expect(panel.classList.contains('kel-scroll-fade--above')).toBe(false);

    // In the middle: both edges fade.
    scroll(panel, 400);
    await waitFor(() => expect(panel.classList.contains('kel-scroll-fade--above')).toBe(true));
    expect(panel.classList.contains('kel-scroll-fade--below')).toBe(true);

    // At the end: the last item is not faded.
    scroll(panel, 800);
    await waitFor(() => expect(panel.classList.contains('kel-scroll-fade--below')).toBe(false));
    expect(panel.classList.contains('kel-scroll-fade--above')).toBe(true);
  });

  it('removes its classes when the panel goes away', () => {
    const { getByTestId, unmount } = render(<Panel />);
    const panel = getByTestId('panel');
    unmount();
    expect(panel.className).toBe('');
  });
});
