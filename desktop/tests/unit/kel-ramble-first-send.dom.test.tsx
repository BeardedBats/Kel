import React from 'react';
import { cleanup, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useAcpInitialMessage, type InitialDraft } from '@renderer/pages/conversation/platforms/acp/useAcpInitialMessage';
const mocks = vi.hoisted(() => ({ send: vi.fn(), translate: (key: string) => key }));
vi.mock('@/common', () => ({ ipcBridge: { acpConversation: { sendMessage: { invoke: mocks.send } } } }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: mocks.translate }) }));
vi.mock('@/renderer/utils/emitter', () => ({ emitter: { emit: vi.fn() } }));
const no = () => {};
const Probe = ({ restore }: { restore: (draft: InitialDraft) => void }) => {
  useAcpInitialMessage({ conversation_id: 'chat', backend: 'kel', restoreInitialDraft: restore, setAiProcessing: no, resetState: no, checkAndUpdateTitle: no, addOrUpdateMessage: no });
  return null;
};
beforeEach(() => { sessionStorage.clear(); mocks.send.mockReset(); });
afterEach(cleanup);
it('keeps failed Ramble input, files, and origin as a draft without replaying after remount', async () => {
  const draft = { input: 'Edited voice note', files: [], transcriptOrigin: { id: 'transcript', name: 'Voice note', project_id: 'project' } };
  sessionStorage.setItem('acp_initial_message_chat', JSON.stringify(draft));
  mocks.send.mockRejectedValue(new Error('Origin could not be recorded'));
  const restore = vi.fn(); const view = render(<Probe restore={restore} />);
  await waitFor(() => expect(restore).toHaveBeenCalledWith(draft));
  expect(mocks.send).toHaveBeenCalledWith(expect.objectContaining({ transcriptOrigin: draft.transcriptOrigin }));
  expect(JSON.parse(sessionStorage.getItem('acp_initial_draft_chat')!)).toEqual(draft);
  view.unmount(); render(<Probe restore={restore} />);
  await waitFor(() => expect(restore).toHaveBeenCalledTimes(2));
  expect(mocks.send).toHaveBeenCalledTimes(1);
});
