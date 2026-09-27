/**
 * D-60 — Skills shows only what Kel has: the skills it ships and the ones the person added. No hub,
 * store, "install from" flow or assistant language.
 */
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SWRConfig } from 'swr';

const listAvailableSkills = vi.fn();
vi.mock('@/common', () => ({ ipcBridge: { fs: { listAvailableSkills: { invoke: () => listAvailableSkills() } } } }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key }) }));

import SkillsOverviewSettings from '@renderer/pages/settings/SkillsOverviewSettings';

afterEach(cleanup);

const renderPage = () =>
  render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <MemoryRouter initialEntries={['/settings/skills']}>
        <SkillsOverviewSettings />
      </MemoryRouter>
    </SWRConfig>
  );

describe('Skills settings (D-60)', () => {
  it('lists the skills Kel ships and the ones the person added, and nothing else', async () => {
    listAvailableSkills.mockResolvedValue([
      { name: 'pdf', description: 'Read and make PDFs', location: '', is_auto_inject: false, is_custom: false, source: 'builtin' },
      { name: 'garden-notes', description: 'My garden notes', location: '', is_auto_inject: false, is_custom: true, source: 'custom' },
      { name: 'from-extension', description: '', location: '', is_auto_inject: false, is_custom: false, source: 'extension' },
    ]);
    renderPage();
    const builtIn = await screen.findByTestId('kel-settings-skills-builtin');
    expect(within(builtIn).getByText('pdf')).toBeTruthy();
    expect(within(screen.getByTestId('kel-settings-skills-custom')).getByText('garden-notes')).toBeTruthy();
    expect(screen.queryByText('from-extension')).toBeNull();
    const page = screen.getByTestId('kel-settings-skills').textContent ?? '';
    expect(page).not.toMatch(/Hub|market|store|install|assistant/i);
  });

  it('says plainly when the person has added none', async () => {
    listAvailableSkills.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText('You haven’t added any skills')).toBeTruthy();
  });
});
