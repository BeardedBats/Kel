import React from 'react';
import { act, cleanup, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { animateString, graphemes, motionClock, RollText, setReducedMotionOverride, setSceneSettledForTests, STRING_MOTION, stringProgress, useStreamFade } from '@renderer/motion';

let highlights: Map<string, Set<Range>>;
beforeEach(() => {
  motionClock.setManual(true);
  setReducedMotionOverride(false);
  setSceneSettledForTests(false);
  highlights = new Map();
  vi.stubGlobal('CSS', { highlights });
  vi.stubGlobal('Highlight', class extends Set<Range> {});
  Object.defineProperty(Range.prototype, 'getBoundingClientRect', { configurable: true, value: function (this: Range) {
    return { x: this.startOffset * 8, y: 20, left: this.startOffset * 8, top: 20, right: this.endOffset * 8, bottom: 40, width: (this.endOffset - this.startOffset) * 8, height: 20 } as DOMRect;
  } });
});
afterEach(() => {
  cleanup();
  motionClock.reset();
  motionClock.setManual(false);
  setReducedMotionOverride(null);
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  delete (Range.prototype as Partial<Range>).getBoundingClientRect;
  document.body.innerHTML = '';
});

const source = (html: string) => {
  const el = document.createElement('div');
  el.innerHTML = html;
  document.body.appendChild(el);
  return el;
};
const glyphs = () => Array.from(document.querySelectorAll<HTMLElement>('.kel-string-glyph'));
const Reply = ({ body }: { body: HTMLElement }) => { useStreamFade(body, true); return null; };

describe('String motion', () => {
  it('keeps graphemes whole, uses the requested physical spring, and caps a large burst', () => {
    expect(graphemes('A👨‍👩‍👧‍👦e\u0301').map((part) => part.text)).toEqual(['A', '👨‍👩‍👧‍👦', 'e\u0301']);
    expect(STRING_MOTION).toMatchObject({ damping: 16, stiffness: 240, mass: 1.2, staggerMs: 15 });
    expect(stringProgress(0)).toBe(0);
    expect(stringProgress(250)).toBeGreaterThan(1); // The supplied spring deliberately overshoots.
    const el = source(`<p>${'a'.repeat(100000)}</p>`);
    const original = el.innerHTML;
    const handle = animateString(el);
    expect(glyphs()).toHaveLength(24);
    expect(glyphs()[0].style.transform).toBe('translateY(8px) rotateX(80deg)');
    expect(glyphs()[0].style.filter).toBe('blur(3px)');
    expect(el.innerHTML).toBe(original);
    motionClock.advance(10);
    expect(Number(glyphs()[0].style.opacity)).toBeGreaterThan(0);
    expect(glyphs()[1].style.opacity).toBe('0');
    motionClock.advance(1500);
    expect(highlights.size).toBe(0);
    expect(glyphs()).toHaveLength(0);
    handle.stop();
  });

  it('preserves Markdown and native selection, and does not clear another reply’s highlights', () => {
    const a = source('<p>Hello <strong>world</strong> <code>code</code></p>');
    const b = source('<p>Second</p>');
    const markup = a.innerHTML;
    const first = animateString(a);
    const second = animateString(b);
    expect(highlights.size).toBe(2);
    expect(a.innerHTML).toBe(markup);
    expect(glyphs().map((el) => el.textContent).join('')).not.toContain('code');
    const range = document.createRange();
    range.selectNodeContents(a);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    expect(selection.toString()).toBe('Hello world code');
    selection.removeAllRanges();
    first.stop();
    expect(highlights.size).toBe(1);
    expect(glyphs().map((el) => el.textContent).join('')).toBe('Second');
    second.stop();
  });

  it('shows history immediately, animates only stream additions, and restores text on a Markdown rewrite', async () => {
    const body = source('<p>Existing</p>');
    const view = render(<Reply body={body} />);
    expect(glyphs()).toHaveLength(0);
    await act(async () => { body.firstChild!.textContent = 'Existing new'; });
    expect(glyphs().map((el) => el.textContent).join('')).toBe('new');
    act(() => motionClock.advance(100));
    await act(async () => { body.firstChild!.textContent = 'Existing new next'; });
    expect(glyphs().map((el) => el.textContent).join('')).toBe('next');
    await act(async () => { body.innerHTML = '<p><strong>Existing new next</strong></p>'; });
    expect(glyphs()).toHaveLength(0);
    expect(highlights.size).toBe(0);
    await act(async () => { body.innerHTML = '<p><strong>Edited</strong></p>'; });
    expect(glyphs()).toHaveLength(0);
    expect(highlights.size).toBe(0);
    view.unmount();
  });

  it('reveals a newly arriving nonempty reply, stops on reduced motion, and never replays it on toggle', () => {
    setSceneSettledForTests(true);
    const body = source('<p>New reply</p>');
    const view = render(<Reply body={body} />);
    expect(glyphs().length).toBeGreaterThan(0);
    act(() => setReducedMotionOverride(true));
    expect(glyphs()).toHaveLength(0);
    expect(highlights.size).toBe(0);
    act(() => setReducedMotionOverride(false));
    expect(glyphs()).toHaveLength(0);
    view.unmount();
  });

  it('finishes an interrupted label before the next swap and removes every overlay on unmount', () => {
    const view = render(<RollText value='Working' />);
    expect(glyphs()).toHaveLength(0);
    view.rerender(<RollText value='Checking' />);
    act(() => motionClock.advance(90));
    view.rerender(<RollText value='Done' />);
    expect(document.querySelectorAll('.kel-roll__old')).toHaveLength(1);
    expect(glyphs().length).toBeLessThanOrEqual(24 * 2);
    view.unmount();
    expect(highlights.size).toBe(0);
    expect(glyphs()).toHaveLength(0);
    expect(motionClock.active()).toBe(0);
  });

  it('restores original ink when the user moves or selects the content, and has a safe fallback', () => {
    const body = source('<p>Read me</p>');
    animateString(body);
    document.dispatchEvent(new Event('scroll'));
    expect(highlights.size).toBe(0);
    expect(glyphs()).toHaveLength(0);
    vi.stubGlobal('CSS', {});
    animateString(body);
    expect(glyphs()).toHaveLength(0);
    expect(body.textContent).toBe('Read me');
  });
});
