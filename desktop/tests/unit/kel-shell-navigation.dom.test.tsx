import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { LayoutContext } from '@renderer/hooks/context/LayoutContext';
import KelToolsSection from '@renderer/components/kel/KelToolsSection';
import KelNavEntries from '@renderer/components/layout/Sider/SiderNav/KelNavEntries';
import SiderToolbar from '@renderer/components/layout/Sider/SiderNav/SiderToolbar';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
const Location = () => <output data-testid='route'>{useLocation().pathname}</output>;
afterEach(cleanup);

describe('Kel shell navigation', () => {
  it.each([['Ramble', '/transcription'], ['Kibble', '/dogfood']])('opens %s through the real route and closes the phone drawer', (label, path) => {
    const close = vi.fn();
    render(<MemoryRouter initialEntries={['/guid']}><LayoutContext.Provider value={{ isMobile: true, siderCollapsed: false, setSiderCollapsed: close }}>
      <KelToolsSection /><Location />
    </LayoutContext.Provider></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: label }));
    expect(screen.getByTestId('route').textContent).toBe(path);
    expect(screen.getByRole('button', { name: label }).getAttribute('aria-current')).toBe('page');
    expect(close).toHaveBeenCalledWith(true);
  });
  it('keeps desktop navigation open and exposes Tools by its section name', () => {
    const close = vi.fn();
    render(<MemoryRouter><LayoutContext.Provider value={{ isMobile: false, siderCollapsed: false, setSiderCollapsed: close }}><KelToolsSection /><Location /></LayoutContext.Provider></MemoryRouter>);
    expect(screen.getByRole('navigation', { name: 'Tools' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Ramble' }));
    expect(close).not.toHaveBeenCalled();
    expect(screen.queryByText(/Dogfood|Transcription/)).toBeNull();
  });
  it('keeps nested project routes selected and closes mobile navigation on a primary action', () => {
    const close = vi.fn();
    render(<MemoryRouter initialEntries={['/projects/knowledge']}><LayoutContext.Provider value={{ isMobile: true, siderCollapsed: false, setSiderCollapsed: close }}>
      <KelNavEntries collapsed={false} isMobile siderTooltipProps={{ disabled: true }} /><Location />
    </LayoutContext.Provider></MemoryRouter>);
    expect(screen.getByRole('button', { name: 'Projects' }).getAttribute('aria-current')).toBe('page');
    fireEvent.click(screen.getByRole('button', { name: 'Activity' }));
    expect(screen.getByTestId('route').textContent).toBe('/activity');
    expect(close).toHaveBeenCalledWith(true);
  });
  it('keeps New Chat and removes the three-dot batch action', () => {
    const newChat = vi.fn(); const batch = vi.fn();
    render(<SiderToolbar collapsed={false} isMobile={false} isBatchMode={false} siderTooltipProps={{ disabled: true }} onNewChat={newChat} onToggleBatchMode={batch} />);
    fireEvent.click(screen.getByRole('button', { name: 'New Chat' }));
    expect(newChat).toHaveBeenCalledTimes(1);
    expect(batch).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'conversation.history.batchManage' })).toBeNull();
    expect(screen.getAllByRole('button')).toHaveLength(1);
  });
});

// D-54: Projects replace Workspaces. The sidebar keeps no "Workspaces" slot, the Projects card nav
// gains "All projects", and "Set up Kel" lives with the Settings pages.
vi.mock('@/common/config/configService', () => ({ configService: { initialize: async () => undefined, get: () => true } }));

describe('Kel projects navigation (D-54)', () => {
  it('drops the Workspaces slot and keeps Projects and Settings selected on their pages', async () => {
    const { default: KelBottomNav } = await import('@renderer/components/kel/KelBottomNav');
    const view = render(<MemoryRouter initialEntries={['/projects/list']}><KelBottomNav /><Location /></MemoryRouter>);
    expect(screen.queryByRole('button', { name: /Workspaces?/ })).toBeNull();
    expect(screen.getByRole('button', { name: 'Projects' }).getAttribute('aria-current')).toBe('page');
    view.unmount();
    render(<MemoryRouter initialEntries={['/onboarding']}><KelBottomNav /></MemoryRouter>);
    expect(screen.getByRole('button', { name: 'Settings' }).getAttribute('aria-current')).toBe('page');
  });
  it('lists All projects with the project pages and Set up Kel with the settings', async () => {
    const request = vi.fn(async () => ({ projects: [{ id: 'default', name: 'General', kind: 'general' }], active: 'default' }));
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    const { default: KelInChatFrame } = await import('@renderer/components/kel/KelInChatFrame');
    const view = render(<MemoryRouter initialEntries={['/activity']}><LayoutContext.Provider value={{ isMobile: false, siderCollapsed: true, setSiderCollapsed: vi.fn() }}>
      <KelInChatFrame><p>page</p></KelInChatFrame><Location />
    </LayoutContext.Provider></MemoryRouter>);
    const projectsNav = screen.getByRole('navigation', { name: 'Projects pages' });
    expect(projectsNav.textContent).not.toMatch(/Workspace|Set up Kel/);
    fireEvent.click(within(projectsNav).getByRole('button', { name: 'All projects' }));
    expect(screen.getByTestId('route').textContent).toBe('/projects/list');
    expect(document.querySelector('.kel-in-chat-frame__header h1')?.textContent).toBe('Projects');
    view.unmount();
    render(<MemoryRouter initialEntries={['/onboarding']}><LayoutContext.Provider value={{ isMobile: false, siderCollapsed: true, setSiderCollapsed: vi.fn() }}>
      <KelInChatFrame><p>setup</p></KelInChatFrame>
    </LayoutContext.Provider></MemoryRouter>);
    expect(document.querySelector('.kel-in-chat-frame__header h1')?.textContent).toBe('Set up Kel');
    const settingsNav = screen.getByRole('navigation', { name: 'Set up Kel pages' });
    expect(settingsNav.textContent).toContain('Appearance');
    // D-60: Kel is the only assistant; there is no catalog and no extension group.
    expect(settingsNav.textContent).not.toMatch(/Assistants|Extensions/);
    expect(within(settingsNav).getByRole('button', { name: 'Set up Kel' }).getAttribute('aria-current')).toBe('page');
    delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  });
});
