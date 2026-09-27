/**
 * CH-9: renaming a chat (sidebar Rename dialog or the chat header) also gives the name to Kel's
 * engine through `/api/conversation-title`, resolved from the donor id. The engine's copy is
 * secondary: its failure never fails the rename.
 */
import React from 'react';
import { act, cleanup, renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';

const bridge = vi.hoisted(() => ({ update: vi.fn() }));

vi.mock('@/common', () => ({
  ipcBridge: {
    conversation: { update: { invoke: bridge.update }, remove: { invoke: vi.fn() } },
    sidebar: { archive: { invoke: vi.fn() } },
  },
}));
vi.mock('@arco-design/web-react', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  Message: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));
vi.mock('@/renderer/pages/conversation/utils/conversationCache', () => ({
  refreshConversationCache: vi.fn(async () => undefined),
}));

type KelStub = { request: ReturnType<typeof vi.fn>; conversation: ReturnType<typeof vi.fn> };
const installKel = (resolved: string | null, request = vi.fn(async () => ({ id: resolved, title: 'x' }))): KelStub => {
  const stub = { request, conversation: vi.fn(async () => resolved) };
  (window as unknown as { kelAPI: unknown }).kelAPI = stub;
  return stub;
};

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

beforeEach(() => {
  bridge.update.mockReset();
  bridge.update.mockResolvedValue(true);
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('kelRequestGuard (CH-9)', () => {
  it('lets the renderer name a chat in the engine', () => {
    expect(rendererKelRequestRefusal('/api/conversation-title', { conversation: 'c1', title: 'Taxes' })).toBeNull();
  });
});

describe('syncEngineConversationTitle', () => {
  it('passes the trimmed name for the engine conversation the donor id resolves to', async () => {
    const kel = installKel('engine-1');
    const { syncEngineConversationTitle } = await import('@/renderer/pages/conversation/utils/engineConversationTitle');
    expect(await syncEngineConversationTitle('donor-1', '  Spring garden ')).toBe(true);
    expect(kel.conversation).toHaveBeenCalledWith('donor-1');
    expect(kel.request).toHaveBeenCalledWith('/api/conversation-title', { conversation: 'engine-1', title: 'Spring garden' });
  });

  it('does nothing when the chat has no engine conversation', async () => {
    const kel = installKel(null);
    const { syncEngineConversationTitle } = await import('@/renderer/pages/conversation/utils/engineConversationTitle');
    expect(await syncEngineConversationTitle('donor-1', 'Taxes')).toBe(false);
    expect(kel.request).not.toHaveBeenCalled();
  });

  it('logs and reports false when the engine refuses, never throwing', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    installKel('engine-1', vi.fn(async () => { throw new Error('A chat name must be 1 to 120 characters.'); }));
    const { syncEngineConversationTitle } = await import('@/renderer/pages/conversation/utils/engineConversationTitle');
    await expect(syncEngineConversationTitle('donor-1', 'Taxes')).resolves.toBe(false);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });
});

const wrapper = ({ children }: { children: React.ReactNode }) => <MemoryRouter>{children}</MemoryRouter>;

describe('sidebar Rename dialog (useConversationActions)', () => {
  const params = () => ({
    batchMode: false,
    selectedConversationIds: new Set<string>(),
    setSelectedConversationIds: vi.fn(),
    toggleSelectedConversation: vi.fn(),
    markAsRead: vi.fn(),
    markManualUnread: vi.fn(),
    clearManualUnread: vi.fn(),
    isManualUnread: () => false,
  });

  it('renames the chat and then gives Kel the same name', async () => {
    const kel = installKel('engine-7');
    const { useConversationActions } = await import('@/renderer/pages/conversation/GroupedHistory/hooks/useConversationActions');
    const { result } = renderHook(() => useConversationActions(params()), { wrapper });
    act(() => result.current.handleEditStart({ id: 'donor-7', name: 'Old name' } as never));
    act(() => result.current.setRenameModalName(' Taxes 2026 '));
    await act(async () => {
      await result.current.handleRenameConfirm();
      await flush();
    });
    expect(bridge.update).toHaveBeenCalledWith({ id: 'donor-7', updates: { name: 'Taxes 2026' } });
    expect(kel.request).toHaveBeenCalledWith('/api/conversation-title', { conversation: 'engine-7', title: 'Taxes 2026' });
    expect(result.current.renameModalVisible).toBe(false);
  });

  it('never tells Kel about a rename that did not happen', async () => {
    bridge.update.mockResolvedValue(false);
    const kel = installKel('engine-7');
    const { useConversationActions } = await import('@/renderer/pages/conversation/GroupedHistory/hooks/useConversationActions');
    const { result } = renderHook(() => useConversationActions(params()), { wrapper });
    act(() => result.current.handleEditStart({ id: 'donor-7', name: 'Old name' } as never));
    act(() => result.current.setRenameModalName('Taxes'));
    await act(async () => {
      await result.current.handleRenameConfirm();
      await flush();
    });
    expect(kel.request).not.toHaveBeenCalled();
  });

  it('keeps the rename when Kel cannot store the name', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    installKel('engine-7', vi.fn(async () => { throw new Error('engine down'); }));
    const { useConversationActions } = await import('@/renderer/pages/conversation/GroupedHistory/hooks/useConversationActions');
    const { result } = renderHook(() => useConversationActions(params()), { wrapper });
    act(() => result.current.handleEditStart({ id: 'donor-7', name: 'Old name' } as never));
    act(() => result.current.setRenameModalName('Taxes'));
    await act(async () => {
      await result.current.handleRenameConfirm();
      await flush();
    });
    expect(bridge.update).toHaveBeenCalled();
    expect(result.current.renameModalVisible).toBe(false);
    warn.mockRestore();
  });
});

describe('chat header rename (useTitleRename)', () => {
  it('gives Kel the new name after the chat is renamed', async () => {
    const kel = installKel('engine-9');
    const { useTitleRename } = await import('@/renderer/pages/conversation/hooks/useTitleRename');
    const { result } = renderHook(() => useTitleRename({ title: 'New chat', conversation_id: 'donor-9' }));
    act(() => result.current.setTitleDraft('Lisbon trip'));
    await act(async () => {
      await result.current.submitTitleRename();
      await flush();
    });
    expect(bridge.update).toHaveBeenCalledWith({ id: 'donor-9', updates: { name: 'Lisbon trip' } });
    expect(kel.request).toHaveBeenCalledWith('/api/conversation-title', { conversation: 'engine-9', title: 'Lisbon trip' });
  });

  it('leaves a custom rename (a team) to its own handler', async () => {
    const kel = installKel('engine-9');
    const onRename = vi.fn(async () => true);
    const { useTitleRename } = await import('@/renderer/pages/conversation/hooks/useTitleRename');
    const { result } = renderHook(() => useTitleRename({ title: 'Team', conversation_id: 'donor-9', onRename }));
    act(() => result.current.setTitleDraft('Renamed team'));
    await act(async () => {
      await result.current.submitTitleRename();
      await flush();
    });
    expect(onRename).toHaveBeenCalledWith('Renamed team');
    expect(kel.request).not.toHaveBeenCalled();
  });
});
