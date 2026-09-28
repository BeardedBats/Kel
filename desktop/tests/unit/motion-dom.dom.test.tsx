/**
 * Motion language stage 2 — the DOM helpers (MOTION.md §3, §4, §6, §7, §8).
 *
 * jsdom has no layout, so each element's box is set by hand; frames run on a manual clock. What is
 * pinned: FLIP plays only when its key changes (a polling re-render never replays it); the indicator
 * leads with the edge toward its new place; the morph keeps B hidden until the hand-over and then
 * leaves nothing behind; reduced motion skips movement.
 */
import React, { useRef } from 'react';
import { act, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { createManualScheduler, setFrameScheduler } from '@renderer/motion/frameLoop';
import { useFlip } from '@renderer/motion/flip';
import { EdgeIndicator, edgeClipPath } from '@renderer/motion/EdgeIndicator';
import { createMorph } from '@renderer/motion/morph';
import { useSharedMorph } from '@renderer/motion/useSharedMorph';
import { prefersReducedMotion } from '@renderer/motion/reducedMotion';

let clock: ReturnType<typeof createManualScheduler>;
let reduced = false;

function setBox(el: Element, box: { left: number; top: number; width?: number; height?: number }): void {
  const width = box.width ?? 100;
  const height = box.height ?? 20;
  (el as HTMLElement).getBoundingClientRect = () =>
    ({
      left: box.left,
      top: box.top,
      width,
      height,
      right: box.left + width,
      bottom: box.top + height,
      x: box.left,
      y: box.top,
      toJSON: () => ({}),
    }) as DOMRect;
}

beforeEach(() => {
  clock = createManualScheduler();
  setFrameScheduler(clock);
  reduced = false;
  window.matchMedia = ((query: string) => ({
    matches: query.includes('reduce') && reduced,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia;
});

afterEach(() => {
  setFrameScheduler();
  document.body.innerHTML = '';
});

describe('reduced motion', () => {
  it('follows the OS setting', () => {
    expect(prefersReducedMotion()).toBe(false);
    reduced = true;
    expect(prefersReducedMotion()).toBe(true);
  });
});

describe('useFlip', () => {
  const List: React.FC<{ ids: string[]; flipKey: string; tick?: number }> = ({ ids, flipKey }) => {
    const ref = useRef<HTMLDivElement>(null);
    useFlip(ref, flipKey);
    return (
      <div ref={ref}>
        {ids.map((id) => (
          <div key={id} data-flip-id={id} data-testid={id} />
        ))}
      </div>
    );
  };

  it('slides a moved row from its old place when the key changes, then settles', () => {
    const view = render(<List ids={['a', 'b']} flipKey='1' />);
    setBox(view.getByTestId('a'), { left: 0, top: 0 });
    setBox(view.getByTestId('b'), { left: 0, top: 20 });
    view.rerender(<List ids={['a', 'b']} flipKey='1' tick={1} />);

    // A new row lands on top; "a" and "b" are pushed down by 20 px.
    view.rerender(<List ids={['new', 'a', 'b']} flipKey='2' />);
    setBox(view.getByTestId('a'), { left: 0, top: 20 });
    setBox(view.getByTestId('b'), { left: 0, top: 40 });
    view.rerender(<List ids={['new', 'a', 'b']} flipKey='3' />);
    expect(view.getByTestId('a').style.transform).toBe('translate(0px, -20px)');
    act(() => clock.advance(32));
    const mid = view.getByTestId('a').style.transform;
    expect(mid).toMatch(/translate\(0px, -\d/);
    act(() => clock.advance(1000));
    expect(view.getByTestId('a').style.transform).toBe('');
  });

  it('does not replay on a polling re-render with the same key', () => {
    const view = render(<List ids={['a']} flipKey='1' />);
    setBox(view.getByTestId('a'), { left: 0, top: 0 });
    view.rerender(<List ids={['a']} flipKey='1' tick={1} />);
    setBox(view.getByTestId('a'), { left: 0, top: 50 });
    view.rerender(<List ids={['a']} flipKey='1' tick={2} />);
    expect(view.getByTestId('a').style.transform).toBe('');
  });

  it('skips the slide under reduced motion', () => {
    const view = render(<List ids={['a']} flipKey='1' />);
    setBox(view.getByTestId('a'), { left: 0, top: 0 });
    view.rerender(<List ids={['a']} flipKey='1' tick={1} />);
    reduced = true;
    setBox(view.getByTestId('a'), { left: 0, top: 50 });
    view.rerender(<List ids={['a']} flipKey='2' />);
    expect(view.getByTestId('a').style.transform).toBe('');
  });
});

describe('EdgeIndicator', () => {
  it('draws with clip-path on one element', () => {
    expect(edgeClipPath('x', 10, 60, 8)).toBe('inset(0 calc(100% - 60px) 0 10px round 8px)');
    expect(edgeClipPath('y', 36, 72, 0)).toBe('inset(36px 0 calc(100% - 72px) 0)');
  });

  it('appears in place, then the leading edge moves first and the tail catches up', () => {
    const view = render(<EdgeIndicator start={0} end={100} className='ind' />);
    const el = view.container.querySelector('.ind') as HTMLElement;
    expect(el.style.clipPath).toBe(edgeClipPath('x', 0, 100, 0));

    view.rerender(<EdgeIndicator start={200} end={300} className='ind' />);
    act(() => clock.advance(16));
    const match = /inset\(0 calc\(100% - ([\d.]+)px\) 0 ([\d.]+)px\)/.exec(el.style.clipPath);
    expect(match).not.toBeNull();
    const end = Number(match![1]);
    const start = Number(match![2]);
    // Moving right: the right edge leads, the left edge has not left yet (33 ms trail).
    expect(end).toBeGreaterThan(100);
    expect(start).toBe(0);

    act(() => clock.advance(1000));
    expect(el.style.clipPath).toBe(edgeClipPath('x', 200, 300, 0));
  });

  it('hides when nothing is selected', () => {
    const view = render(<EdgeIndicator start={null} end={null} className='ind' />);
    expect((view.container.querySelector('.ind') as HTMLElement).style.visibility).toBe('hidden');
  });
});

describe('shared-element morph', () => {
  function boxes() {
    const source = document.createElement('div');
    const target = document.createElement('div');
    document.body.append(source, target);
    setBox(source, { left: 10, top: 10, width: 200, height: 60 });
    setBox(target, { left: 300, top: 100, width: 400, height: 500 });
    return { source, target };
  }

  it('flies one surface from A to B, keeps B hidden until the hand-over, then cleans up', async () => {
    const { source, target } = boxes();
    const handle = createMorph({ source, target, presets: { height: 'gentle' } });
    expect(target.style.visibility).toBe('hidden');
    const done = handle.start();

    const surface = document.querySelector('.kel-motion-overlay > div') as HTMLElement;
    expect(surface).not.toBeNull();
    expect(source.style.visibility).toBe('hidden');
    expect(surface.style.transform).toBe('translate(10px, 10px)');

    act(() => clock.advance(64));
    expect(target.style.visibility).toBe('hidden');
    expect(surface.style.transform).not.toBe('translate(10px, 10px)');

    act(() => clock.advance(2000));
    await done;
    expect(target.style.visibility).toBe('');
    expect(document.querySelector('.kel-motion-overlay')).toBeNull();
    // A has become B; it stays hidden until asked back.
    expect(source.style.visibility).toBe('hidden');
    handle.restoreSource();
    expect(source.style.visibility).toBe('');
  });

  it('under reduced motion cross-fades in place with no surface', async () => {
    reduced = true;
    const { source, target } = boxes();
    await createMorph({ source, target }).start();
    expect(document.querySelector('.kel-motion-overlay')).toBeNull();
    expect(target.style.visibility).toBe('');
  });

  it('useSharedMorph renders B’s content into the travelling surface', async () => {
    const { source, target } = boxes();
    let run: ReturnType<typeof useSharedMorph>['run'] | null = null;
    const Host: React.FC = () => {
      const shared = useSharedMorph();
      run = shared.run;
      return <>{shared.portal}</>;
    };
    render(<Host />);
    let done: Promise<void> = Promise.resolve();
    act(() => {
      done = run!({ source, target, enter: <p data-testid='body'>Panel body</p> });
    });
    const body = document.querySelector('.kel-motion-overlay [data-testid="body"]');
    expect(body?.textContent).toBe('Panel body');
    await act(async () => {
      clock.advance(2000);
      await done;
    });
    expect(document.querySelector('.kel-motion-overlay')).toBeNull();
  });
});
