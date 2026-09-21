import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
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
  it('keeps New Chat and batch management as separate native button actions', () => {
    const newChat = vi.fn(); const batch = vi.fn();
    render(<SiderToolbar collapsed={false} isMobile={false} isBatchMode={false} siderTooltipProps={{ disabled: true }} onNewChat={newChat} onToggleBatchMode={batch} />);
    fireEvent.click(screen.getByRole('button', { name: 'New Chat' }));
    expect(newChat).toHaveBeenCalledTimes(1);
    expect(batch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'conversation.history.batchManage' }));
    expect(batch).toHaveBeenCalledTimes(1);
  });
});
