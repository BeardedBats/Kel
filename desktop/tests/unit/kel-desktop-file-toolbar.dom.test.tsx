import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KelDesktopFileStatus, KelDesktopFileToolbar } from '@renderer/components/kel/KelDesktopFileToolbar';
import PreviewTabs from '@renderer/pages/conversation/Preview/components/PreviewPanel/PreviewTabs';

describe('Desktop file actions', () => {
  it('supports file-tab keyboard navigation without closing another tab', () => {
    const onSwitchTab = vi.fn(), onCloseTab = vi.fn();
    render(<PreviewTabs desktopStyle tabs={[{ id: 'hero', title: 'hero.tsx' }, { id: 'style', title: 'styles.css' }]}
      activeTabId='hero' tabFadeState={{ left: false, right: false }} tabsContainerRef={React.createRef<HTMLDivElement>() as React.RefObject<HTMLDivElement>}
      onSwitchTab={onSwitchTab} onCloseTab={onCloseTab} onContextMenu={vi.fn()} />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'hero.tsx', exact: true }), { key: 'ArrowRight' });
    expect(onSwitchTab).toHaveBeenCalledWith('style');
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'styles.css', exact: true }));
    onSwitchTab.mockClear();
    fireEvent.keyDown(screen.getByRole('button', { name: 'Close styles.css', exact: true }), { key: ' ' });
    expect(onCloseTab).toHaveBeenCalledWith('style');
    expect(onSwitchTab).not.toHaveBeenCalled();
  });
  it('blocks unavailable actions and closes the menu after a completed action', async () => {
    const save = vi.fn(), reload = vi.fn();
    render(<KelDesktopFileToolbar viewMode='source' split={false} onViewMode={vi.fn()} onSplit={vi.fn()} onAddToChat={vi.fn()}
      actions={[{ label: 'Save', onClick: save, disabled: true }, { label: 'Reload', onClick: reload }]} />);
    fireEvent.click(screen.getByRole('button', { name: 'More file actions' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Save', exact: true }));
    expect(save).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Reload', exact: true }));
    expect(reload).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Reload', exact: true })).toBeNull());
  });
  it('counts mixed line endings and reports only known edit state', () => {
    const view = render(<KelDesktopFileStatus path='src/hero.tsx' content={'one\r\ntwo\nthree\rfour'} dirty onReveal={vi.fn()} />);
    expect(screen.getByText('src/hero.tsx · 4 lines · unsaved changes')).toBeTruthy();
    expect(screen.queryByText(/edited by Kel/)).toBeNull();
    view.rerender(<KelDesktopFileStatus path='src/hero.tsx' content='' dirty={false} />);
    expect(screen.getByText('src/hero.tsx · 0 lines')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Show in folder' })).toBeNull();
  });
});
