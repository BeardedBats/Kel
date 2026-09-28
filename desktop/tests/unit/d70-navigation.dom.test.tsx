/**
 * D-70 item 5 — navigation clean-up. The Work page is retired (the work cards replace it), so any
 * `/work` route lands on the chat home; Permissions, Providers and Diagnostics moved into Settings and
 * keep their old routes as redirects (query included); Recipes has one entry (the sidebar), and
 * Projects keeps its chats and folder, Knowledge, Scheduled tasks and Activity. Every Settings and
 * Projects entry opens a real page — no dead ends.
 */
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Outlet, useLocation } from 'react-router-dom';
import { LayoutContext } from '@renderer/hooks/context/LayoutContext';

vi.mock('@renderer/hooks/context/AuthContext', () => ({ useAuth: () => ({ status: 'authenticated' }) }));
vi.mock('@renderer/components/layout/DocumentTitle', () => ({ default: () => null }));
vi.mock('@renderer/components/layout/AppLoader', () => ({ default: () => null }));
vi.mock('@/renderer/hooks/system/useCrossSessionRateLimitNotice', () => ({ useCrossSessionRateLimitNotice: () => undefined }));
vi.mock('@/common/config/configService', () => ({ configService: { initialize: async () => undefined, get: () => true } }));
vi.mock('@renderer/pages/guid', () => ({ default: () => <h1>Home page</h1> }));
vi.mock('@renderer/pages/kel/autonomy', () => ({ default: () => <h1>Permissions page</h1> }));
vi.mock('@renderer/pages/kel/providers', () => ({ default: () => <h1>Providers page</h1> }));
vi.mock('@renderer/pages/kel/diagnostics', () => ({ default: () => <h1>Diagnostics page</h1> }));
vi.mock('@renderer/pages/kel/activity', () => ({ default: () => <h1>Activity page</h1> }));
vi.mock('@renderer/pages/settings/StaffModelsSettings', () => ({ default: () => <h1>Staff page</h1> }));

import PanelRoute from '@renderer/components/layout/Router';
import KelInChatFrame from '@renderer/components/kel/KelInChatFrame';
import KelBottomNav from '@renderer/components/kel/KelBottomNav';

const Where = () => {
  const location = useLocation();
  return <output data-testid='where'>{`${location.pathname}${location.search}`}</output>;
};

afterEach(() => {
  cleanup();
  window.location.hash = '';
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('retired and moved routes (D-70)', () => {
  it.each([
    ['#/work', '#/guid', 'Home page'],
    ['#/work?job=job-1', '#/guid', 'Home page'],
    ['#/work/anything', '#/guid', 'Home page'],
    ['#/autonomy', '#/settings/permissions', 'Permissions page'],
    ['#/providers', '#/settings/providers', 'Providers page'],
    ['#/diagnostics', '#/settings/diagnostics', 'Diagnostics page'],
    ['#/providers?focus=codex', '#/settings/providers?focus=codex', 'Providers page'],
    ['#/settings/permissions', '#/settings/permissions', 'Permissions page'],
    ['#/settings/staff', '#/settings/staff', 'Staff page'],
    ['#/activity?job=job-1', '#/activity?job=job-1', 'Activity page'],
  ])('%s lands on %s', async (from, to, heading) => {
    window.location.hash = from;
    const view = render(<PanelRoute layout={<Outlet />} />);
    await waitFor(() => expect(window.location.hash).toBe(to));
    expect(await view.findByText(heading)).toBeTruthy();
  });
});

const frameAt = (path: string, isMobile = false) => {
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request: vi.fn(async () => ({ projects: [{ id: 'default', name: 'General', kind: 'general' }], active: 'default' })),
  };
  return render(
    <MemoryRouter initialEntries={[path]}>
      <LayoutContext.Provider value={{ isMobile, siderCollapsed: true, setSiderCollapsed: vi.fn() }}>
        <KelInChatFrame><p>page</p></KelInChatFrame>
        <Where />
      </LayoutContext.Provider>
    </MemoryRouter>
  );
};

const labels = (nav: HTMLElement) => within(nav).getAllByRole('button').map((button) => button.textContent?.trim());

describe('Projects and Settings navigation (D-70)', () => {
  it('Projects keeps chats and folder, Knowledge, Scheduled tasks and Activity — nothing that moved', () => {
    frameAt('/projects/knowledge');
    const nav = screen.getByRole('navigation', { name: 'Projects pages' });
    expect(labels(nav)).toEqual(['All projects', 'Activity', 'Knowledge', 'Scheduled tasks']);
    expect(nav.textContent).not.toMatch(/Work|Permissions|Providers|Diagnostics|Recipes/);
  });

  it('Settings lists Staff & models next to Model, and Permissions, Providers and Diagnostics', () => {
    frameAt('/settings/staff');
    const nav = screen.getByRole('navigation', { name: 'Settings pages' });
    const items = labels(nav);
    expect(items.slice(0, 4)).toEqual(['Model', 'Staff & models', 'Permissions', 'Providers']);
    expect(items).toContain('Diagnostics');
    expect(within(nav).getByRole('button', { name: 'Staff & models' }).getAttribute('aria-current')).toBe('page');
  });

  it.each([
    ['/settings/appearance', 'Settings pages'],
    ['/projects/knowledge', 'Projects pages'],
  ])('every entry on %s opens a route the router serves (no dead ends)', (start, name) => {
    const served = /^\/(settings\/(model|staff|permissions|providers|tools|skills|appearance|system|diagnostics|webui|archived|about)|connections|onboarding|transcription|projects\/(list|knowledge)|activity|scheduled)$/;
    const first = frameAt(start);
    const entries = labels(screen.getByRole('navigation', { name }));
    first.unmount();
    expect(entries.length).toBeGreaterThan(3);
    for (const label of entries) {
      const view = frameAt(start);
      fireEvent.click(within(screen.getByRole('navigation', { name })).getByRole('button', { name: label }));
      const where = screen.getByTestId('where').textContent ?? '';
      expect(where, label).toMatch(served);
      // Pages that stay in this frame mark their own entry (Transcriptions opens Ramble itself).
      if (where !== '/transcription') {
        const current = document.querySelector('.kel-in-chat-frame__nav [aria-current="page"]');
        expect(current?.textContent?.trim(), label).toBe(label);
      }
      view.unmount();
    }
  });

  it('the moved pages show the Settings frame, and Recipes is not a Projects page', () => {
    const view = frameAt('/settings/permissions');
    expect(document.querySelector('.kel-in-chat-frame__header h1')?.textContent).toBe('Settings');
    expect(within(screen.getByRole('navigation', { name: 'Settings pages' })).getByRole('button', { name: 'Permissions' }).getAttribute('aria-current')).toBe('page');
    view.unmount();
    frameAt('/projects/recipes');
    expect(document.querySelector('.kel-in-chat-frame__header h1')?.textContent).toBe('Recipes');
  });

  it('the phone index lists the moved pages under Settings, not the project', () => {
    const view = frameAt('/projects', true);
    const projectIndex = document.querySelector('.kel-in-chat-frame__mobile-index') as HTMLElement;
    expect(projectIndex.textContent).not.toMatch(/Work|Permissions|Providers|Diagnostics|Recipes/);
    view.unmount();
    frameAt('/settings', true);
    const settingsIndex = document.querySelector('.kel-in-chat-frame__mobile-index') as HTMLElement;
    expect(settingsIndex.textContent).toMatch(/Staff & models/);
    expect(settingsIndex.textContent).toMatch(/Permissions/);
    expect(settingsIndex.textContent).toMatch(/Providers/);
    expect(settingsIndex.textContent).toMatch(/Diagnostics/);
  });

  it('the sidebar keeps one Recipes entry and marks Settings for the moved pages', () => {
    const view = render(<MemoryRouter initialEntries={['/settings/providers']}><KelBottomNav /></MemoryRouter>);
    expect(screen.getAllByRole('button', { name: 'Recipes' })).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Settings' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('button', { name: 'Projects' }).getAttribute('aria-current')).toBeNull();
    view.unmount();
    render(<MemoryRouter initialEntries={['/scheduled']}><KelBottomNav /></MemoryRouter>);
    expect(screen.getByRole('button', { name: 'Projects' }).getAttribute('aria-current')).toBe('page');
  });
});
