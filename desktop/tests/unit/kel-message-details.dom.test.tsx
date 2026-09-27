/**
 * CH-2/CP-14/CH-3/D-55 in the chat: a checked result shows nothing extra until the person opens its
 * "Details" link; stop and restart notes read as quiet system lines, not as Kel replies.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// The message row's surroundings (file preview, fork, agent logos, Markdown) are not under test.
vi.mock('@/renderer/pages/conversation/Preview/hooks/useLocalFilePreview', () => ({ useLocalFilePreview: () => undefined }));
vi.mock('@/renderer/hooks/chat/useForkConversation', () => ({ useForkConversation: () => vi.fn() }));
vi.mock('@/renderer/utils/model/agentLogo', () => ({ useAgentLogos: () => ({}), resolveAgentLogo: () => null }));
vi.mock('@renderer/components/Markdown', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import MessageText from '@renderer/pages/conversation/Messages/components/MessageText';
import { kelDetailRows } from '@renderer/pages/conversation/Messages/components/KelMessageDetails';
import type { IMessageText } from '@/common/chat/chatLib';
import type { KelMessageMeta } from '@/common/chat/kelMessageMeta';

afterEach(cleanup);

const text = (content: string, kel_meta?: KelMessageMeta, position: 'left' | 'right' = 'left'): IMessageText =>
  ({
    id: 'm-1',
    msg_id: 'm-1',
    type: 'text',
    position,
    conversation_id: 'donor',
    created_at: Date.now(),
    content: kel_meta ? { content, kel_meta } : { content },
  }) as IMessageText;

const result: KelMessageMeta = {
  kind: 'result',
  verdict: 'VERIFIED',
  checks: [
    { kind: 'repository_evidence', verdict: 'VERIFIED' },
    { kind: 'manual_review', verdict: 'VERIFIED' },
    { kind: 'min_chars', verdict: 'VERIFIED' },
    { kind: 'min_chars', verdict: 'FAILED' },
  ],
  executed_by: [{ provider: 'claude-code', label: 'Claude Code' }],
  reviewed_by: [{ provider: 'codex', label: 'Codex' }],
  summary: ['Verified', '• Tests: passed', '• Limitation: Could not open one source'],
};

const renderText = (message: IMessageText) =>
  render(
    <MemoryRouter>
      <MessageText message={message} />
    </MemoryRouter>
  );

describe('kelDetailRows', () => {
  it('names a result, who did it, who checked it and what the checks found, in plain words', () => {
    expect(kelDetailRows(result)).toEqual([
      { label: 'Result', lines: ['Passed its checks'] },
      { label: 'Answered by', lines: ['Claude Code'] },
      { label: 'Checked by', lines: ['Codex'] },
      { label: 'Checks', lines: ['Tests: passed', 'Review: passed', 'Length: 1 of 2 passed'] },
      { label: 'Limits', lines: ['Could not open one source'] },
    ]);
  });

  it('says a failed result did not pass, and never shows raw engine names', () => {
    const rows = kelDetailRows({ kind: 'result', verdict: 'FAILED', checks: [{ kind: 'repository_evidence', verdict: 'FAILED' }] });
    expect(rows).toEqual([
      { label: 'Result', lines: ["Didn't pass its checks"] },
      { label: 'Checks', lines: ['Tests: failed'] },
    ]);
    expect(JSON.stringify(rows)).not.toMatch(/repository_evidence|VERIFIED|FAILED/);
  });

  it('shows who answered a reply that fell back from the chosen model', () => {
    expect(
      kelDetailRows({
        answered_by: { provider: 'claude-code', label: 'Claude' },
        fallback_from: { provider: 'deepseek', label: 'DeepSeek', note: 'Not supported for chat yet' },
      })
    ).toEqual([
      { label: 'Answered by', lines: ['Claude'] },
      { label: 'You chose', lines: ['DeepSeek (Not supported for chat yet)'] },
    ]);
  });
});

describe('Kel messages in the chat', () => {
  it('keeps a result’s details closed behind a Details link', () => {
    renderText(text("Here's your garden plan. It passed its checks.", result));
    const details = screen.getByTestId('kel-message-details') as HTMLDetailsElement;
    expect(details.open).toBe(false);
    expect(screen.getByText('Details').tagName).toBe('SUMMARY');
    fireEvent.click(screen.getByText('Details'));
    expect(details.open).toBe(true);
    expect(details.textContent).toContain('Checked by');
    expect(details.textContent).toContain('Codex');
    expect(screen.getByTestId('message-text-content').textContent).not.toContain('Codex');
  });

  it('shows no Details for an ordinary reply', () => {
    renderText(text('Sure — here is a quick answer.'));
    expect(screen.queryByTestId('kel-message-details')).toBeNull();
    expect(screen.getByTestId('message-text-content').textContent).toContain('quick answer');
  });

  it('shows a stopped reply as a quiet line without reply actions', () => {
    renderText(text('You stopped this reply.', { kind: 'stopped', submission: 'acp-1' }));
    expect(screen.getByTestId('kel-message-note').textContent).toBe('You stopped this reply.');
    expect(screen.queryByTestId('message-text-content')).toBeNull();
    expect(screen.queryByLabelText('More reply actions')).toBeNull();
    expect(screen.queryByTestId('kel-message-details')).toBeNull();
  });

  it('shows a restart with a change as a quiet line', () => {
    renderText(text('Restarting the garden plan with that change.', { kind: 'amendment', submission: 'acp-1', replaced_job: 'job-1' }));
    expect(screen.getByTestId('kel-message-note').textContent).toBe('Restarting the garden plan with that change.');
  });

  it('never treats a person’s own message as a note or shows it Details', () => {
    renderText(text('You stopped this reply.', { kind: 'stopped' }, 'right'));
    expect(screen.queryByTestId('kel-message-note')).toBeNull();
    expect(screen.queryByTestId('kel-message-details')).toBeNull();
  });
});
