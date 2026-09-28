/**
 * VIS-8: restarting Kel's chat connection is offered on the error card that shows a connection
 * failed, not as a permanent icon in the title area.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const h = vi.hoisted(() => ({ restartRuntime: vi.fn(async () => ({ runtime: null })) }));

vi.mock('@/common', () => ({
  ipcBridge: {
    conversation: { restartRuntime: { invoke: h.restartRuntime } },
  },
}));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock('@arco-design/web-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@arco-design/web-react')>();
  return { ...actual, Message: { ...actual.Message, success: toast.success, error: toast.error } };
});
vi.mock('@/renderer/hooks/context/ConversationContext', () => ({
  useConversationContextSafe: () => ({ type: 'acp', assistantId: 'kel', conversation_id: 'c1', hideSendBox: false }),
}));
vi.mock('@/renderer/hooks/file/useWorkspaceSelector', () => ({ useWorkspaceSelector: () => vi.fn() }));
vi.mock('@/renderer/pages/conversation/Messages/hooks', () => ({ useMessageList: () => [] }));
vi.mock('@renderer/pages/conversation/Messages/hooks', () => ({ useMessageList: () => [] }));
vi.mock('@/renderer/hooks/agent/useAcpConfigOptions', () => ({ revalidateAcpConfigOptions: vi.fn(async () => undefined) }));
vi.mock('@/renderer/pages/conversation/utils/conversationCache', () => ({ getConversationOrNull: async () => null }));
vi.mock('@renderer/components/base/FeedbackButton', () => ({ default: () => null }));
vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key }),
}));

import MessageTips from '@renderer/pages/conversation/Messages/components/MessageTips';
import type { IMessageTips } from '@/common/chat/chatLib';

afterEach(cleanup);

const errorTip = (code: string): IMessageTips =>
  ({
    id: 'm1',
    msg_id: 'm1',
    conversation_id: 'c1',
    type: 'tips',
    position: 'center',
    content: {
      type: 'error',
      content: 'The agent process exited.',
      error: { code, message: 'The agent process exited.', retryable: false },
    },
  }) as unknown as IMessageTips;

describe('Reconnect on the error card (VIS-8)', () => {
  it('restarts the chat connection from the card', async () => {
    render(<MessageTips message={errorTip('AGENT_PROCESS_EXITED')} />);
    fireEvent.click(screen.getByRole('button', { name: 'Reconnect' }));
    await waitFor(() => expect(h.restartRuntime).toHaveBeenCalledWith({ conversation_id: 'c1' }));
  });

  it('does not offer it when the fix is choosing a folder', () => {
    render(<MessageTips message={errorTip('WORKSPACE_PATH_RUNTIME_UNAVAILABLE')} />);
    expect(screen.queryByRole('button', { name: 'Reconnect' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Choose a folder' })).toBeTruthy();
  });
});
