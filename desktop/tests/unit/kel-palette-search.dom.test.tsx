/**
 * FN-08: the command palette finds a chat by a word anywhere in a message (the hint shows the
 * words around it), and a vetting hit opens the chat it belongs to.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

const longText = `${'We talked about the garden beds and the watering schedule for the spring. '.repeat(3)}The code word is periwinkle.`;
vi.mock('@renderer/utils/chat/kelHistorySearch', () => ({
  searchKelConversationMessages: vi.fn(async ({ keyword }: { keyword: string }) => ({
    items: longText.toLowerCase().includes(keyword.toLowerCase())
      ? [{ conversation: { id: 'donor-9', name: 'Garden chat' }, message_id: 'm1', message_type: 'text', message_created_at: 1, preview_text: longText }]
      : [],
    total: 1,
    has_more: false,
  })),
}));

import KelCommandPalette, { snippetAround } from '@renderer/components/kel/KelCommandPalette';

const Where = () => <div data-testid='where'>{useLocation().pathname}</div>;

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const openPalette = async (kelAPI: Record<string, unknown>) => {
  (window as unknown as { kelAPI: unknown }).kelAPI = kelAPI;
  render(
    <MemoryRouter initialEntries={['/guid']}>
      <KelCommandPalette />
      <Routes>
        <Route path='*' element={<Where />} />
      </Routes>
    </MemoryRouter>
  );
  await act(async () => {
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
  });
};

describe('palette search', () => {
  it('finds a chat by a word far past the first 80 characters', async () => {
    const request = vi.fn(async (route: string) =>
      route === '/api/search' ? { transcripts: [], vetting: [], conversations: [] } : { jobs: [], projects: [] });
    await openPalette({ request });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'periwinkle' } });
    const option = await screen.findByRole('option', { name: /Garden chat/ }, { timeout: 3000 });
    expect(option.getAttribute('title')).toMatch(/periwinkle/); // the words around the match, on hover
    fireEvent.click(option);
    expect(screen.getByTestId('where').textContent).toBe('/conversation/donor-9');
  });

  it('opens the chat a vetting session lives in', async () => {
    const request = vi.fn(async (route: string) =>
      route === '/api/search'
        ? { transcripts: [], conversations: [], vetting: [{ id: 's1', title: 'Trellis layout', snippet: 'Matches a question in this session', conversation_id: 'engine-3' }] }
        : { jobs: [], projects: [] });
    const openEngineConversation = vi.fn(async () => 'donor-3');
    await openPalette({ request, openEngineConversation });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'spacing' } });
    const option = await screen.findByRole('option', { name: /Trellis layout/ }, { timeout: 3000 });
    fireEvent.click(option);
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/conversation/donor-3'));
    expect(openEngineConversation).toHaveBeenCalledWith('engine-3');
  });
});

describe('snippetAround', () => {
  it('keeps short text whole and centres long text on the match', () => {
    expect(snippetAround('short note', 'note')).toBe('short note');
    const out = snippetAround(longText, 'periwinkle');
    expect(out).toMatch(/periwinkle/);
    expect(out.startsWith('…')).toBe(true);
    expect(out.length).toBeLessThanOrEqual(82);
  });
});
