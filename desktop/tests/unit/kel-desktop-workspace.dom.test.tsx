import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KelDesktopWorkspaceHeader } from '@renderer/components/kel/KelDesktopWorkspaceHeader';

describe('Desktop Files panel controls', () => {
  it('retains folder actions and closes their menu after selection', async () => {
    const onAddFolder = vi.fn();
    render(<KelDesktopWorkspaceHeader tab='files' searching={false} refreshing={false}
      onTab={vi.fn()} onSearch={vi.fn()} onRefresh={vi.fn()} onClose={vi.fn()} onAddFolder={onAddFolder} onCollapseAll={vi.fn()} />);
    // D-54: the chat's file panel is "Files", never "Workspace".
    expect(screen.getByRole('button', { name: 'Files actions' }).textContent).toBe('Files');
    expect(screen.getByRole('tablist', { name: 'Files view' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Files actions' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Add folder', exact: true }));
    expect(onAddFolder).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Add folder', exact: true })).toBeNull());
  });
  it('selects the requested view and shows the real change count', () => {
    const onTab = vi.fn();
    render(<KelDesktopWorkspaceHeader tab='files' changeCount={3} searching={false} refreshing={false}
      onTab={onTab} onSearch={vi.fn()} onRefresh={vi.fn()} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Changes · 3' }));
    expect(onTab).toHaveBeenCalledWith('changes');
    expect(screen.getByRole('tab', { name: 'Files' }).getAttribute('aria-selected')).toBe('true');
  });
  it('keeps an unknown count distinct from an empty repository', () => {
    const props = { tab: 'changes' as const, searching: false, refreshing: false,
      onTab: vi.fn(), onSearch: vi.fn(), onRefresh: vi.fn(), onClose: vi.fn() };
    const view = render(<KelDesktopWorkspaceHeader {...props} />);
    expect(screen.getByRole('tab', { name: 'Changes' })).toBeTruthy();
    view.rerender(<KelDesktopWorkspaceHeader {...props} changeCount={0} />);
    expect(screen.getByRole('tab', { name: 'Changes · 0' })).toBeTruthy();
  });
  it('blocks refresh while busy and keeps search and close available', () => {
    const onRefresh = vi.fn(), onSearch = vi.fn(), onClose = vi.fn();
    render(<KelDesktopWorkspaceHeader tab='files' searching refreshing
      onTab={vi.fn()} onSearch={onSearch} onRefresh={onRefresh} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Refresh files' }));
    expect(onRefresh).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Search files' }));
    fireEvent.click(screen.getByRole('button', { name: 'Close files' }));
    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
