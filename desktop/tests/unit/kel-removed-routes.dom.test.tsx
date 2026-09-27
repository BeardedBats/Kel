/**
 * D-56 — retired routes land somewhere real instead of rendering a removed page.
 */
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, waitFor } from '@testing-library/react';
import { Outlet } from 'react-router-dom';

vi.mock('@renderer/hooks/context/AuthContext', () => ({ useAuth: () => ({ status: 'authenticated' }) }));
vi.mock('@renderer/components/layout/DocumentTitle', () => ({ default: () => null }));
vi.mock('@renderer/components/layout/AppLoader', () => ({ default: () => null }));
vi.mock('@/renderer/hooks/system/useCrossSessionRateLimitNotice', () => ({ useCrossSessionRateLimitNotice: () => undefined }));
vi.mock('@renderer/pages/settings/AppearanceSettings', () => ({ default: () => <h1>Appearance page</h1> }));
vi.mock('@renderer/pages/settings/ModeSettings', () => ({ default: () => <h1>Model page</h1> }));
vi.mock('@renderer/pages/settings/SkillsOverviewSettings', () => ({ default: () => <h1>Skills page</h1> }));
vi.mock('@renderer/pages/settings/SystemSettings', () => ({ default: () => <h1>System page</h1> }));
vi.mock('@renderer/pages/guid', () => ({ default: () => <h1>Home page</h1> }));

import PanelRoute from '@renderer/components/layout/Router';

afterEach(() => {
  cleanup();
  window.location.hash = '';
});

describe('retired settings routes', () => {
  it('sends the old Desktop Pet route to Appearance', async () => {
    window.location.hash = '#/settings/pet';
    const view = render(<PanelRoute layout={<Outlet />} />);
    await waitFor(() => expect(window.location.hash).toBe('#/settings/appearance'));
    expect(await view.findByText('Appearance page')).toBeTruthy();
  });

  // D-60: Kel is the only assistant and has no marketplace or extensions.
  it.each([
    ['#/settings/assistants', '#/settings/model', 'Model page'],
    ['#/settings/agent', '#/settings/model', 'Model page'],
    ['#/settings/agent/claude/repair', '#/settings/model', 'Model page'],
    ['#/assistants', '#/guid', 'Home page'],
    ['#/team/abc', '#/guid', 'Home page'],
    ['#/settings/skills-hub', '#/settings/skills', 'Skills page'],
    ['#/settings/skills/detail/pdf', '#/settings/skills', 'Skills page'],
    ['#/settings/ext/some-extension', '#/settings/system', 'System page'],
  ])('sends %s to %s', async (from, to, heading) => {
    window.location.hash = from;
    const view = render(<PanelRoute layout={<Outlet />} />);
    await waitFor(() => expect(window.location.hash).toBe(to));
    expect(await view.findByText(heading)).toBeTruthy();
  });
});
