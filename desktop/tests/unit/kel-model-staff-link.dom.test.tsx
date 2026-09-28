/**
 * The composer's model menu opens Settings → Staff & models for the open chat
 * (`?conversation=<the engine's conversation id>`), so that page can say "This chat uses its own
 * model: …"; without a chat it opens the page plainly.
 */
import React from 'react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelModelPill, staffModelsPath } from '@renderer/components/kel/KelModelControl';

const state = {
  default: null,
  conversation: null,
  providers: [{ id: 'claude-code', label: 'Claude', available: true, note: null, options: [{ id: 'claude-native', label: 'Claude', available: true, note: null }] }],
};

const Where = () => {
  const { pathname, search } = useLocation();
  return <output data-testid='where'>{pathname + search}</output>;
};

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Staff & models from the composer', () => {
  it('names the open chat', async () => {
    (window as unknown as { kelAPI: unknown }).kelAPI = {
      request: vi.fn(async (_route: string, body?: Record<string, unknown>) => (body?.action === 'get' ? state : {})),
      conversation: vi.fn(async () => 'engine-7'),
    };
    render(
      <MemoryRouter initialEntries={['/conversation/donor-7']}>
        <Routes>
          <Route path='*' element={<><KelModelPill conversationId='donor-7' /><Where /></>} />
        </Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect((screen.getByTestId('kel-model-pill') as HTMLButtonElement).disabled).toBe(false));
    await act(async () => {
      fireEvent.click(screen.getByTestId('kel-model-pill'));
    });
    fireEvent.click(await screen.findByRole('button', { name: 'Staff & models' }));
    expect(screen.getByTestId('where').textContent).toBe('/settings/staff?conversation=engine-7');
  });

  it('opens the page plainly without a chat', () => {
    expect(staffModelsPath(null)).toBe('/settings/staff');
    expect(staffModelsPath('a b')).toBe('/settings/staff?conversation=a%20b');
  });
});
