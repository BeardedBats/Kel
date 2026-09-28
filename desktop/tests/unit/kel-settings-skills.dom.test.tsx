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
  it('lists the skills the person added and none of the donor skills aioncore unpacks (VIS-21)', async () => {
    listAvailableSkills.mockResolvedValue([
      { name: 'pdf', description: 'Read and make PDFs', location: '', is_auto_inject: false, is_custom: false, source: 'builtin' },
      { name: 'xiaohongshu-recruiter', description: '招聘', location: '', is_auto_inject: false, is_custom: false, source: 'builtin' },
      { name: 'cron', description: 'Scheduled task management', location: '', is_auto_inject: true, is_custom: false, source: 'builtin' },
      { name: 'garden-notes', description: 'My garden notes', location: '', is_auto_inject: false, is_custom: true, source: 'custom' },
      { name: 'from-extension', description: '', location: '', is_auto_inject: false, is_custom: false, source: 'extension' },
    ]);
    renderPage();
    expect(await within(await screen.findByTestId('kel-settings-skills-custom')).findByText('garden-notes')).toBeTruthy();
    // Kel ships no skill of its own yet, so there is no "Built into Kel" list of donor skills.
    expect(screen.queryByTestId('kel-settings-skills-builtin')).toBeNull();
    for (const donor of ['pdf', 'xiaohongshu-recruiter', 'cron', 'from-extension']) expect(screen.queryByText(donor)).toBeNull();
    const page = screen.getByTestId('kel-settings-skills').textContent ?? '';
    expect(page).not.toMatch(/Hub|market|store|install|assistant/i);
  });

  it('keeps every donor auto-inject skill out of a new chat', async () => {
    const { donorAutoInjectSkills, kelVisibleSkills } = await import('@renderer/components/kel/kelSkills');
    const skills = [
      { name: 'cron', source: 'builtin', is_auto_inject: true },
      { name: 'aionui-config', source: 'builtin', is_auto_inject: true },
      { name: 'pdf', source: 'builtin', is_auto_inject: false },
      { name: 'mine', source: 'custom', is_auto_inject: false },
    ];
    expect(donorAutoInjectSkills(skills)).toEqual(['cron', 'aionui-config']);
    expect(kelVisibleSkills(skills).map((skill) => skill.name)).toEqual(['mine']);
  });

  it('says plainly when the person has added none', async () => {
    listAvailableSkills.mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText('You haven’t added any skills')).toBeTruthy();
  });
});
