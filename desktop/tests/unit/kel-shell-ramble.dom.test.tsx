import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Ramble from '@renderer/pages/kel/transcription';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
it('Ramble reads and edits its library over authenticated browser transport without a desktop bridge', async () => {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  const requests: Array<{ url: string; body: Record<string, unknown> }> = [];
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const body = JSON.parse(init?.body || '{}');
    requests.push({ url: String(url), body });
    const result = body.action === 'status' ? { mode: 'practice', label: 'Practice mode', has_key: false } : { folders: [], transcripts: [] };
    return { ok: true, json: async () => result };
  }));
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  await waitFor(() => expect(requests.some(r => r.url === '/kel/api/transcription')).toBe(true));
  expect(screen.queryByText('Kel is not connected')).toBeNull();
  fireEvent.change(screen.getByPlaceholderText('New folder'), { target: { value: 'Notes' } });
  fireEvent.click(screen.getByTestId('folder-create'));
  await waitFor(() => expect(requests.some(r => r.body.action === 'folder_create' && r.body.name === 'Notes')).toBe(true));
});
