/**
 * D-75.2: Nick can edit a message he sent and ask Kel to answer its last reply again.
 * The message row offers Edit (his messages) and "Answer again" (Kel's last reply); the list
 * handler asks the engine to rewind, hides the rows that showed rewound messages (never work cards
 * or the rows of handed-off work) and sends the request again with its own files.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/renderer/pages/conversation/Preview/hooks/useLocalFilePreview', () => ({ useLocalFilePreview: () => undefined }));
vi.mock('@/renderer/hooks/chat/useForkConversation', () => ({ useForkConversation: () => vi.fn() }));
vi.mock('@/renderer/utils/model/agentLogo', () => ({ useAgentLogos: () => ({}), resolveAgentLogo: () => null }));
vi.mock('@renderer/components/Markdown', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
const kelRequest = vi.fn();
vi.mock('@renderer/components/kel/kelApi', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  kelRequest: (...args: unknown[]) => kelRequest(...args),
}));

import MessageText from '@renderer/pages/conversation/Messages/components/MessageText';
import { occurrenceFromEnd, rowsToHide, runRewrite } from '@renderer/pages/conversation/Messages/components/kelRewrite';
import { withoutHiddenRows } from '@/renderer/utils/chat/kelHiddenRows';
import { ConversationProvider } from '@/renderer/hooks/context/ConversationContext';
import { emitter } from '@/renderer/utils/emitter';
import type { IMessageText, TMessage } from '@/common/chat/chatLib';

const row = (id: string, position: 'left' | 'right', content: string, type = 'text'): TMessage =>
  ({ id, msg_id: id, type, position, conversation_id: 'donor', created_at: 1, content: { content } }) as unknown as TMessage;

afterEach(() => {
  cleanup();
  emitter.removeAllListeners();
});
beforeEach(() => {
  kelRequest.mockReset();
  (window as unknown as { kelAPI: unknown }).kelAPI = { conversation: vi.fn(async () => 'engine-1') };
});

const renderRow = (message: IMessageText, isLastMessage = false) =>
  render(
    <MemoryRouter>
      <ConversationProvider value={{ conversation_id: 'donor', type: 'acp' } as never}>
        <MessageText message={message} isLastMessage={isLastMessage} />
      </ConversationProvider>
    </MemoryRouter>
  );

describe('message row actions', () => {
  it('edits a sent message in place and asks the list to rewind from it', () => {
    const asked = vi.fn();
    emitter.on('kel.message.rewrite', asked);
    renderRow(row('u1', 'right', 'What is basil?\n\n[[AION_FILES]]\nC:\\tmp\\note.txt') as IMessageText);
    fireEvent.click(screen.getByTestId('message-edit-button'));
    const box = screen.getByLabelText('Edit your message') as HTMLTextAreaElement;
    expect(box.value).toBe('What is basil?');
    fireEvent.change(box, { target: { value: 'What is sage?' } });
    fireEvent.click(screen.getByText('Send'));
    expect(asked).toHaveBeenCalledWith({
      kind: 'edit', conversationId: 'donor', messageId: 'u1', text: 'What is basil?', newText: 'What is sage?',
      files: ['C:\\tmp\\note.txt'],
    });
    expect(screen.queryByTestId('message-edit-form')).toBeNull();
  });

  it('cancelling or sending the same text changes nothing', () => {
    const asked = vi.fn();
    emitter.on('kel.message.rewrite', asked);
    renderRow(row('u1', 'right', 'Hello') as IMessageText);
    fireEvent.click(screen.getByTestId('message-edit-button'));
    expect((screen.getByText('Send') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByText('Cancel'));
    expect(asked).not.toHaveBeenCalled();
  });

  it('offers "Answer again" on Kel\'s last reply only', () => {
    const asked = vi.fn();
    emitter.on('kel.message.rewrite', asked);
    const { unmount } = renderRow(row('a1', 'left', 'An earlier answer') as IMessageText, false);
    expect(screen.queryByTestId('message-regenerate-button')).toBeNull();
    unmount();
    renderRow(row('a2', 'left', 'The last answer') as IMessageText, true);
    fireEvent.click(screen.getByTestId('message-regenerate-button'));
    expect(asked).toHaveBeenCalledWith({ kind: 'regenerate', conversationId: 'donor', messageId: 'a2' });
  });
});

describe('rewinding the chat rows', () => {
  const list = [
    row('u1', 'right', 'what is basil'),
    row('a1', 'left', 'Basil is a herb.'),
    row('u2', 'right', 'write me a garden plan'),
    row('a2', 'left', "I'm starting on that now in the background."),
    row('card', 'left', '', 'acp_tool_call'),
    row('u3', 'right', 'what is basil'),
    row('a3', 'left', 'Still a herb.'),
    row('kel-history-12', 'left', 'Here is your garden plan.'),
  ];

  it('hides text rows from the edited one on, but keeps handed-off work and cards', () => {
    const kept = [
      { seq: 3, role: 'user', text: 'write me a garden plan' },
      { seq: 4, role: 'assistant', text: "I'm starting on that now in the background." },
      { seq: 12, role: 'assistant', text: 'Here is your garden plan.' },
    ];
    expect(rowsToHide(list, 'u1', kept)).toEqual(['u1', 'a1', 'u3', 'a3']);
  });

  it('counts which of two identical messages was picked', () => {
    expect(occurrenceFromEnd(list, 'u1', 'what is basil')).toBe(1);
    expect(occurrenceFromEnd(list, 'u3', 'what is basil')).toBe(0);
  });

  it('regenerates: rewinds, hides the question and reply, and resends the question with its files', async () => {
    const chat = [row('u1', 'right', 'what is thyme\n\n[[AION_FILES]]\nC:\\tmp\\a.txt'), row('a1', 'left', 'Answer 1')];
    kelRequest.mockImplementation(async (_route: string, body: { action: string }) =>
      body.action === 'regenerate'
        ? { mode: 'rewind', text: 'what is thyme', rewound: [], kept: [] }
        : { rows: [] });
    const resent = vi.fn();
    emitter.on('kel.message.resend', resent);
    const hidden: string[][] = [];
    const out = await runRewrite({ kind: 'regenerate', conversationId: 'donor', messageId: 'a1' }, chat, (ids) => hidden.push(ids));
    expect(out?.hidden).toEqual(['u1', 'a1']);
    expect(hidden).toEqual([['u1', 'a1']]);
    expect(kelRequest).toHaveBeenCalledWith('/api/rewind', { action: 'hide', conversation: 'engine-1', rows: ['u1', 'a1'] });
    expect(resent).toHaveBeenCalledWith('what is thyme', 'donor', ['C:\\tmp\\a.txt']);
  });

  it('an edit of a message that started work hides nothing and sends the change', async () => {
    kelRequest.mockResolvedValue({ mode: 'amend', submission: 's1', rewound: [], kept: [] });
    const resent = vi.fn();
    emitter.on('kel.message.resend', resent);
    const hide = vi.fn();
    await runRewrite({ kind: 'edit', conversationId: 'donor', messageId: 'u2', text: 'write me a garden plan',
      newText: 'write me a garden plan for shade', files: [] }, list, hide);
    expect(hide).not.toHaveBeenCalled();
    expect(kelRequest).toHaveBeenCalledWith('/api/rewind', expect.objectContaining({ action: 'edit', occurrence: 0 }));
    expect(resent).toHaveBeenCalledWith('write me a garden plan for shade', 'donor', []);
  });

  it('a reload hides the rows the engine remembers', async () => {
    kelRequest.mockResolvedValue({ rows: ['a1'] });
    const items = await withoutHiddenRows('donor-reload', [{ id: 'u1' }, { id: 'a1' }]);
    expect(items).toEqual([{ id: 'u1' }]);
  });
});
