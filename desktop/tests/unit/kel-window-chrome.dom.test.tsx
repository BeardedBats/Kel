/**
 * Window chrome (Nick, 2026-09-29):
 * - the Kel mark + wordmark is one real button, "Kel home", that goes to the start page (#/guid) from
 *   anywhere and is never a drag region;
 * - a thin full-width strip along the top edge drags the window, rendered before every other control so
 *   the controls that reach into it (marked no-drag) stay clickable;
 * - the Pinned / Recent labels in the sidebar sit on the sidebar surface with no band behind them.
 * Drag regions and the sidebar paint are CSS the jsdom cascade cannot evaluate, so those halves read the
 * rules themselves.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { KelBrandHome, KelWindowDragStrip } from '@renderer/components/layout/KelBrandHome';

const here = path.dirname(fileURLToPath(import.meta.url));
const renderer = path.resolve(here, '..', '..', 'packages', 'desktop', 'src', 'renderer');
const read = (relative: string) => readFileSync(path.join(renderer, relative), 'utf8');
const css = read('styles/kel-shell.css');

const Where: React.FC = () => <span data-testid='where'>{useLocation().pathname}</span>;

describe('the Kel mark goes home', () => {
  it('is a focusable button named "Kel home" that opens the start page', () => {
    const pressed = vi.fn();
    render(
      <MemoryRouter initialEntries={['/settings/model']}>
        <KelBrandHome onPress={pressed} />
        <Routes>
          <Route path='*' element={<Where />} />
        </Routes>
      </MemoryRouter>
    );
    const home = screen.getByRole('button', { name: 'Kel home' });
    expect(home.tagName).toBe('BUTTON');
    expect(home.textContent).toBe('Kel');
    home.focus();
    expect(document.activeElement).toBe(home);
    fireEvent.click(home);
    expect(screen.getByTestId('where').textContent).toBe('/guid');
    expect(pressed).toHaveBeenCalledTimes(1);
  });

  it('works from a chat too, not only from Settings', () => {
    render(
      <MemoryRouter initialEntries={['/conversation/abc']}>
        <KelBrandHome />
        <Routes>
          <Route path='*' element={<Where />} />
        </Routes>
      </MemoryRouter>
    );
    fireEvent.click(screen.getByRole('button', { name: 'Kel home' }));
    expect(screen.getByTestId('where').textContent).toBe('/guid');
  });
});

describe('the window drags from its top edge', () => {
  it('renders a hidden, non-focusable strip', () => {
    render(<KelWindowDragStrip />);
    const strip = screen.getByTestId('kel-window-drag-strip');
    expect(strip.getAttribute('aria-hidden')).toBe('true');
    expect(strip.tabIndex).toBeLessThan(0);
  });

  it('is a thin full-width drag region, and the controls in or near it are no-drag', () => {
    const rule = /\.kel-window-drag-strip \{([^}]*)\}/.exec(css)?.[1] ?? '';
    expect(rule).toMatch(/position: fixed/);
    expect(rule).toMatch(/left: 0; right: 0/);
    expect(rule).toMatch(/-webkit-app-region: drag/);
    const height = Number(/height: (\d+)px/.exec(rule)?.[1]);
    expect(height).toBeGreaterThanOrEqual(8);
    expect(height).toBeLessThanOrEqual(12);
    const noDrag = /\.kel-v2-shell :is\(([^)]*)\) \{ -webkit-app-region: no-drag; \}/.exec(css)?.[1] ?? '';
    for (const control of ['.kel-brand-home', '.layout-sider-header button', '.app-titlebar__button', '.kel-shell-workspace-link']) {
      expect(noDrag).toContain(control);
    }
    expect(/\.kel-brand-home \{[^}]*-webkit-app-region: no-drag/.test(css)).toBe(true);
    // The window's own minimise / maximise / close stay clickable too.
    expect(read('components/layout/Titlebar/titlebar.css')).toMatch(/-webkit-app-region: no-drag/);
  });

  it('comes before every other control in the shell, so their no-drag wins', () => {
    const layout = read('components/layout/Layout.tsx');
    const strip = layout.indexOf('<KelWindowDragStrip');
    expect(strip).toBeGreaterThan(0);
    for (const later of ["className='kel-skip'", '<Titlebar', '<KelBrandHome']) {
      expect(layout.indexOf(later)).toBeGreaterThan(strip);
    }
  });
});

describe('the sidebar section labels', () => {
  it('have no band behind them and scroll with their rows', () => {
    const rules = [...css.matchAll(/([^{}]*\.sider-section-label[^{}]*)\{([^}]*)\}/g)].map(([, selector, body]) => ({ selector, body }));
    const painted = rules.filter(({ body }) => /background(-color)?:/.test(body) && !/background(-color)?: transparent/.test(body));
    expect(painted.map(({ selector }) => selector.trim())).toEqual([]);
    expect(rules.some(({ body }) => /position: static !important/.test(body))).toBe(true);
    expect(rules.some(({ body }) => /backdrop-filter: blur/.test(body))).toBe(false);
  });
});
