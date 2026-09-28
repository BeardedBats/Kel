/**
 * LIVE-7: when the main process says an open chat's Kel history changed (a scoping card or a result
 * arrived), the chat re-reads its messages at once — not only on the next poll or reopen.
 */
import React from 'react';
import { cleanup, render, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';

const loadLatest = vi.fn(async () => ({ items: [], oldest_cursor: null, newest_cursor: null, has_more_before: false, has_more_after: false }));
vi.mock('@/renderer/utils/chat/messagePagination', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  loadLatestConversationMessages: (...args: unknown[]) => loadLatest(...(args as [])),
}));
vi.mock('@/common', async (importOriginal) => {
  const actual = await importOriginal<Record<string, any>>();
  const on = () => () => undefined;
  return {
    ...actual,
    ipcBridge: {
      ...actual.ipcBridge,
      conversation: { ...actual.ipcBridge?.conversation, userCreated: { on }, messageConsumed: { on }, turnCompleted: { on } },
    },
  };
});

import {
  MessageListLoadingProvider,
  MessageListProvider,
  MessagePaginationProvider,
  useMessageLstCache,
} from '@renderer/pages/conversation/Messages/hooks';

const Probe: React.FC<{ id: string }> = ({ id }) => {
  useMessageLstCache(id);
  return null;
};

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

it('re-reads the open chat when its Kel history is updated, and only that chat', async () => {
  let emit: ((update: { conversationId: string }) => void) | undefined;
  const off = vi.fn();
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    conversation: async () => null,
    onHistoryUpdated: (callback: (update: { conversationId: string }) => void) => {
      emit = callback;
      return off;
    },
  };
  const { unmount } = render(
    <MessageListProvider value={[]}>
      <MessageListLoadingProvider value={false}>
        <MessagePaginationProvider value={{ hasMoreBefore: false, hasMoreAfter: false, isLoadingBefore: false, isLoadingAnchor: false }}>
          <Probe id='donor-open' />
        </MessagePaginationProvider>
      </MessageListLoadingProvider>
    </MessageListProvider>
  );
  await waitFor(() => expect(loadLatest).toHaveBeenCalled());
  const initial = loadLatest.mock.calls.length;
  emit?.({ conversationId: 'another-chat' });
  expect(loadLatest.mock.calls.length).toBe(initial);
  emit?.({ conversationId: 'donor-open' });
  await waitFor(() => expect(loadLatest.mock.calls.length).toBe(initial + 1));
  expect(loadLatest).toHaveBeenLastCalledWith('donor-open', expect.anything());
  unmount();
  expect(off).toHaveBeenCalled();
});
