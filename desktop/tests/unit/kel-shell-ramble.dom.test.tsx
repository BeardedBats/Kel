import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Ramble from '@renderer/pages/kel/transcription';
import { Message } from '@arco-design/web-react';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function libraryTransport() {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  const requests: Array<{ url: string; body: Record<string, unknown> }> = [];
  const folders: Array<{ id: string; name: string; created: number }> = [];
  let failRename = false;
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const body = JSON.parse(init?.body || '{}');
    requests.push({ url: String(url), body });
    let result: unknown = { folders: [...folders], transcripts: [] };
    if (body.action === 'status') result = { mode: 'practice', label: 'Muse', has_key: false };
    if (body.action === 'folder_create') {
      const folder = { id: `folder-${folders.length}`, name: body.name, created: 1 };
      folders.push(folder);
      result = folder;
    }
    if (body.action === 'folder_rename') {
      if (failRename) throw new Error('Network request failed');
      folders.find(folder => folder.id === body.id)!.name = body.name;
    }
    return { ok: true, json: async () => result };
  }));
  return { requests, folders, failRename: () => { failRename = true; } };
}

it('creates a persisted New Folder with its name selected, then saves one inline rename', async () => {
  const { requests, folders } = libraryTransport();
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  await waitFor(() => expect(requests.some(r => r.url === '/kel/api/transcription')).toBe(true));
  expect(screen.queryByText('Muse')).toBeNull();
  expect(screen.getByRole('heading', { name: 'Ramble' }).closest('main')).not.toBeNull();
  fireEvent.click(screen.getByTestId('folder-create'));
  const input = await screen.findByRole('textbox', { name: 'Folder name' }) as HTMLInputElement;
  expect(input.value).toBe('New Folder');
  expect(document.activeElement).toBe(input);
  expect([input.selectionStart, input.selectionEnd]).toEqual([0, 10]);
  fireEvent.change(input, { target: { value: 'Notes' } });
  fireEvent.keyDown(input, { key: 'Enter' });
  await waitFor(() => expect(screen.queryByTestId('folder-rename')).toBeNull());
  expect(folders[0].name).toBe('Notes');
  expect(requests.filter(r => r.body.action === 'folder_rename')).toHaveLength(1);
});

it('Escape and blank names keep New Folder; failed renames preserve the draft', async () => {
  const transport = libraryTransport();
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  await waitFor(() => expect(transport.requests.some(r => r.body.action === 'library')).toBe(true));
  fireEvent.click(screen.getByTestId('folder-create'));
  let input = await screen.findByTestId('folder-rename');
  fireEvent.change(input, { target: { value: 'Discard' } });
  fireEvent.keyDown(input, { key: 'Escape' });
  expect(screen.queryByTestId('folder-rename')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Rename New Folder' }));
  input = screen.getByTestId('folder-rename');
  fireEvent.change(input, { target: { value: '   ' } });
  fireEvent.keyDown(input, { key: 'Enter' });
  expect(screen.queryByTestId('folder-rename')).toBeNull();
  expect(transport.requests.filter(r => r.body.action === 'folder_rename')).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: 'Rename New Folder' }));
  const notify = vi.spyOn(Message, 'error').mockImplementation(() => 0);
  transport.failRename();
  input = screen.getByTestId('folder-rename');
  fireEvent.change(input, { target: { value: 'Keep draft' } });
  fireEvent.keyDown(input, { key: 'Enter' });
  await waitFor(() => expect(transport.requests.some(r => r.body.action === 'folder_rename')).toBe(true));
  await waitFor(() => expect(notify).toHaveBeenCalled());
  expect((screen.getByTestId('folder-rename') as HTMLInputElement).value).toBe('Keep draft');
  expect(transport.folders[0].name).toBe('New Folder');
});
