/**
 * D-70 item 4 — answers typed in the chat while a scoping card is open. The engine understands them
 * (the same vetting ingestion as the card) and records them; the card, which keeps reading while it
 * is open, shows them picked with one line saying where they came from, and Start sends them.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelScopingCard, picksWithRecorded } from '@renderer/components/kel/workCards/KelScopingCard';
import type { ScopingView } from '@renderer/components/kel/workCards/officeApi';
import { refreshWorkCards } from '@renderer/components/kel/workCards/workCardEvents';

afterEach(() => cleanup());

const SCOPING: ScopingView = {
  id: 'scope-1',
  title: 'Garden plan',
  state: 'open',
  conversation_id: 'engine-morning',
  questions: [
    { id: 'Q1', question: 'Who is it for?', options: [{ code: 'A', label: 'Just me' }, { code: 'B', label: 'My team' }, { code: 'C', label: 'The public' }], best: 'B' },
    { id: 'Q2', question: 'How long?', options: [{ code: 'A', label: 'One page' }, { code: 'B', label: 'Two or three pages' }], best: 'A' },
  ],
  summary: 'I’ll write: a one-page spring garden plan',
  recorded: {},
};

const install = (answer: () => ScopingView) => {
  const request = vi.fn(async (route: string, body?: unknown) => {
    if (route.startsWith('/api/scoping?id=')) return answer();
    if (route === '/api/scoping' && body) return { ...answer(), state: 'started', started_at: 1, answer_line: 'The public · a single index card' };
    return {};
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = { request, conversation: vi.fn(async () => 'engine-morning') };
  return request;
};

describe('picks from the chat', () => {
  it('fill in what Nick has not picked on the card', () => {
    expect(
      picksWithRecorded({ Q2: { option: 'B' } }, { Q1: { option: 'C', label: 'The public' }, Q2: { text: 'a postcard', label: 'a postcard' } })
    ).toEqual({ Q1: { option: 'C' }, Q2: { option: 'B' } });
    expect(picksWithRecorded({}, { Q2: { text: 'a postcard' } })).toEqual({ Q2: { other: true, text: 'a postcard' } });
  });
});

describe('the scoping card with typed answers', () => {
  it('shows answers typed in the chat once the engine has them, and Start sends them', async () => {
    let current: ScopingView = SCOPING;
    const request = install(() => current);
    render(<KelScopingCard scopingId='scope-1' conversationId='app-morning' />);
    const card = await screen.findByTestId('kel-scoping-card');
    expect(within(card).queryByTestId('kel-scoping-typed')).toBeNull();
    // Nick types "1: the public / 2: a single index card" in the chat; the engine records them.
    current = {
      ...SCOPING,
      recorded: { Q1: { option: 'C', label: 'The public' }, Q2: { text: 'a single index card', label: 'a single index card' } },
    };
    act(() => refreshWorkCards());
    await waitFor(() => expect(within(card).getByTestId('kel-scoping-typed').textContent).toContain('Filled in from your message (2 of 2)'), { timeout: 4500 });
    const [first, second] = within(card).getAllByTestId('kel-scoping-question');
    expect(within(first).getByRole('radio', { name: 'The public' }).getAttribute('aria-checked')).toBe('true');
    expect((within(second).getByTestId('kel-answer-input') as HTMLInputElement).value).toBe('a single index card');
    fireEvent.click(within(card).getByTestId('kel-scoping-start'));
    await screen.findByTestId('kel-scoping-collapsed');
    const starts = request.mock.calls.filter(([route, body]) => route === '/api/scoping' && body).map(([, body]) => body);
    expect(starts).toEqual([
      { action: 'start', id: 'scope-1', answers: { Q1: { option: 'C' }, Q2: { text: 'a single index card' } }, conversation: 'engine-morning' },
    ]);
  });

  it('collapses when "start" typed in the chat started the work', async () => {
    let current: ScopingView = SCOPING;
    install(() => current);
    render(<KelScopingCard scopingId='scope-1' conversationId='app-morning' />);
    await screen.findByTestId('kel-scoping-card');
    current = { ...SCOPING, state: 'started', started_at: 1, answer_line: 'The public · One page', recorded: {} };
    act(() => refreshWorkCards());
    expect((await screen.findByTestId('kel-scoping-collapsed', {}, { timeout: 4500 })).textContent).toContain('The public · One page');
  });
});
