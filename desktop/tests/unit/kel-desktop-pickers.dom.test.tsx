import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KelDesktopModelMenu } from '@renderer/components/kel/KelDesktopModelMenu';
import { KelDesktopProjectMenu } from '@renderer/components/kel/KelDesktopProjectMenu';

const state = { default: { provider: 'a', model: 'one' }, conversation: null,
  providers: [{ id: 'a', label: 'Provider', available: true, options: [{ id: 'one', label: 'Model One', available: true }] }] };

describe('Desktop model picker scopes', () => {
  it('writes the chosen scope and closes only after the write finishes', async () => {
    let finish!: () => void;
    const onChoose = vi.fn(() => new Promise<void>(resolve => { finish = resolve; }));
    const onClose = vi.fn();
    render(<KelDesktopModelMenu state={state} hasConversation onChoose={onChoose} onClose={onClose} onAdd={vi.fn()} onSettings={vi.fn()} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Default for new chats' }));
    fireEvent.click(screen.getByRole('button', { name: /^Automatic/ }));
    expect(onChoose).toHaveBeenCalledWith(null, 'default');
    expect(onClose).not.toHaveBeenCalled();
    expect((screen.getByRole('button', { name: 'Model One' }) as HTMLButtonElement).disabled).toBe(true);
    finish();
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });
  it('keeps chat selection distinct from the new-chat default', async () => {
    const onChoose = vi.fn(async () => {});
    render(<KelDesktopModelMenu state={state} hasConversation onChoose={onChoose} onClose={vi.fn()} onAdd={vi.fn()} onSettings={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Model One' }));
    await waitFor(() => expect(onChoose).toHaveBeenCalledWith({ provider: 'a', model: 'one' }, 'conversation'));
  });
  it('disables chat scope before a chat exists and keeps Add Model separate from settings', () => {
    const onAdd = vi.fn(), onSettings = vi.fn(), onClose = vi.fn();
    render(<KelDesktopModelMenu state={state} hasConversation={false} onChoose={vi.fn()} onClose={onClose} onAdd={onAdd} onSettings={onSettings} />);
    expect((screen.getByRole('tab', { name: 'This chat' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Add Model' }));
    fireEvent.click(screen.getByRole('button', { name: 'Open model settings' }));
    fireEvent.keyDown(screen.getByTestId('kel-desktop-model-menu'), { key: 'Escape' });
    expect(onAdd).toHaveBeenCalledTimes(1);
    expect(onSettings).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe('Desktop project picker', () => {
  it('deduplicates folders, includes the current folder, and returns the full selected path', () => {
    const onSelect = vi.fn();
    render(<KelDesktopProjectMenu paths={['C:\\fixtures\\Kel', 'C:\\fixtures\\Kel']} selected={'C:\\fixtures\\Website Redesign'} onSelect={onSelect} onClear={vi.fn()} onBrowse={vi.fn()} />);
    expect(screen.getAllByRole('button', { name: 'Kel' })).toHaveLength(1);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search projects' }), { target: { value: ' WEBSITE ' } });
    expect(screen.queryByRole('button', { name: 'Kel' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Website Redesign' }));
    expect(onSelect).toHaveBeenCalledWith('C:\\fixtures\\Website Redesign');
  });
  it('keeps clear and browse available when search has no matches', () => {
    const onClear = vi.fn(), onBrowse = vi.fn();
    render(<KelDesktopProjectMenu paths={[]} selected='' onSelect={vi.fn()} onClear={onClear} onBrowse={onBrowse} />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search projects' }), { target: { value: 'Missing' } });
    expect(screen.getByText('No matching projects.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'No project' }));
    fireEvent.click(screen.getByRole('button', { name: 'Choose a different folder' }));
    expect(onClear).toHaveBeenCalledTimes(1);
    expect(onBrowse).toHaveBeenCalledTimes(1);
  });
});
