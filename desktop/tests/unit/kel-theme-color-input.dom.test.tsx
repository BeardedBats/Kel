/**
 * Theme colors — the hex field (D1 in docs/v2/evidence/v2-19/UI_ACCEPTANCE_R21.md).
 *
 * Found by clicking the packaged r21: typing `#7a1f1f` saved `#77aa11`, because `#7a1` already
 * parsed as shorthand and the save remounted the row mid-word. Typing now saves only a complete
 * six-digit code; shorthand is accepted on Enter or blur; paste and Reset behave as before.
 * The save helper is stubbed (it is covered by kel-shell-theme.dom.test.ts); the row is not.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const store = vi.hoisted(() => ({ overrides: {} as Record<string, Record<string, string>> }));
const setThemeOverride = vi.hoisted(() =>
  vi.fn(async (themeId: string, token: string, value: string | null) => {
    const current = { ...(store.overrides[themeId] ?? {}) };
    if (value) current[token] = value;
    else delete current[token];
    store.overrides = { ...store.overrides, [themeId]: current };
  })
);

vi.mock('@/common/config/configService', () => ({
  configService: { get: (key: string) => (key === 'theme.activeId' ? 'dark' : undefined) },
}));
vi.mock('@renderer/utils/theme/applyTheme', () => ({
  setThemeOverride,
  clearThemeOverrides: vi.fn(async () => undefined),
  themeOverrides: (themeId: string) => store.overrides[themeId] ?? {},
}));

import ThemeColorsSection from '@renderer/components/kel/ThemeColorsSection';

const field = () => screen.getByLabelText('App background hex value') as HTMLInputElement;
const savedValues = () => setThemeOverride.mock.calls.map((call) => call[2]);

describe('theme color hex field', () => {
  beforeEach(() => {
    store.overrides = {};
    setThemeOverride.mockClear();
  });

  it('typing a six-digit code saves it once, complete — never its shorthand prefix', async () => {
    render(<ThemeColorsSection />);
    const user = userEvent.setup();
    await user.tripleClick(field());
    await user.keyboard('#7a1f1f');
    await waitFor(() => expect(savedValues()).toEqual(['#7a1f1f']));
    expect(store.overrides.dark['--bg-base']).toBe('#7a1f1f');
  });

  it('accepts a three-digit code on Enter', async () => {
    render(<ThemeColorsSection />);
    const user = userEvent.setup();
    await user.tripleClick(field());
    await user.keyboard('#abc');
    expect(savedValues()).toEqual([]);
    // Arco reads the legacy keyCode, which Chromium sets and user-event does not.
    fireEvent.keyDown(field(), { key: 'Enter', code: 'Enter', keyCode: 13, which: 13 });
    await waitFor(() => expect(savedValues()).toEqual(['#aabbcc']));
  });

  it('accepts a three-digit code on blur, and reverts an unparseable draft without saving', async () => {
    render(<ThemeColorsSection />);
    const user = userEvent.setup();
    await user.tripleClick(field());
    await user.keyboard('#abc');
    fireEvent.blur(field());
    await waitFor(() => expect(savedValues()).toEqual(['#aabbcc']));

    setThemeOverride.mockClear();
    await user.tripleClick(field());
    await user.keyboard('#zz');
    fireEvent.blur(field());
    expect(savedValues()).toEqual([]);
    await waitFor(() => expect(field().value).toBe('#aabbcc'));
  });

  it('a paste of a full code saves it in one step, and Reset removes it', async () => {
    render(<ThemeColorsSection />);
    const user = userEvent.setup();
    await user.tripleClick(field());
    await user.paste('#7a1f1f');
    await waitFor(() => expect(savedValues()).toEqual(['#7a1f1f']));

    await user.click(await screen.findByTestId('theme-reset-bg-base'));
    await waitFor(() => expect(savedValues()).toEqual(['#7a1f1f', null]));
    expect(store.overrides.dark['--bg-base']).toBeUndefined();
  });

  it('keeps the native picker mounted through repeated color changes', async () => {
    render(<ThemeColorsSection />);
    const picker = screen.getByTestId('theme-color-bg-base') as HTMLInputElement;
    fireEvent.change(picker, { target: { value: '#123456' } });
    await waitFor(() => expect(savedValues()).toEqual(['#123456']));
    expect(screen.getByTestId('theme-color-bg-base')).toBe(picker);

    fireEvent.change(picker, { target: { value: '#234567' } });
    await waitFor(() => expect(savedValues()).toEqual(['#123456', '#234567']));
    expect(screen.getByTestId('theme-color-bg-base')).toBe(picker);
    expect(field().value).toBe('#234567');
  });
});

describe('command palette surface (D2)', () => {
  it('is opaque in Dark: its own class carries the Elevated surfaces token, not the page-card glass', () => {
    const renderer = resolve(__dirname, '../../packages/desktop/src/renderer');
    const palette = readFileSync(resolve(renderer, 'components/kel/KelCommandPalette.tsx'), 'utf8');
    const css = readFileSync(resolve(renderer, 'styles/kel-shell.css'), 'utf8');
    expect(palette).toContain("className='kel-card kel-palette'");
    expect(css).toMatch(
      /html:not\(\[data-theme='light'\]\) \.kel-v2-shell \.kel-palette\[role='dialog'\] \{ background: var\(--bg-2, #1b3568\) !important; \}/
    );
  });
});
