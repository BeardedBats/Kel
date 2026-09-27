import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import KelToolsControl from '@renderer/components/kel/KelToolsControl';

vi.mock('@arco-design/web-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@arco-design/web-react')>();
  return { ...actual, Message: { success: vi.fn(), error: vi.fn() } };
});

const row = (override: 'default' | 'on' | 'off') => ({
  id: 'web', label: 'Web', description: 'Search the web', availability: 'available', availability_reason: '',
  global: 'on', override, effective: override === 'off' ? 'off' : 'on', usable: true,
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Tools crumb', () => {
  it('re-reads the rows after a change instead of trusting the engine reply (no window crash)', async () => {
    let override: 'default' | 'on' | 'off' = 'default';
    const request = vi.fn(async (_route: string, body: { action: string; state?: 'default' | 'on' | 'off' }) => {
      if (body.action === 'set') {
        override = body.state ?? 'default';
        return override; // the engine answers with the new state string, not the rows
      }
      return [row(override)];
    });
    (window as unknown as { kelAPI: unknown }).kelAPI = { request, conversation: async () => 'c1' };
    render(
      <MemoryRouter>
        <KelToolsControl conversationId='c1' />
      </MemoryRouter>
    );
    const pill = await screen.findByTestId('kel-tools-pill');
    expect(pill.className).toContain('kel-shell-crumb');
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/capabilities', expect.objectContaining({ action: 'get' })));
    await act(async () => {
      fireEvent.click(pill);
    });
    const enable = await screen.findByTestId('kel-tool-web-on');
    await act(async () => {
      fireEvent.click(enable);
    });
    await waitFor(() => expect(screen.getByTestId('kel-tools-pill').textContent).toContain('Tools · 1'));
    expect(request).toHaveBeenCalledWith('/api/capabilities', expect.objectContaining({ action: 'set', state: 'on' }));
  });
});
