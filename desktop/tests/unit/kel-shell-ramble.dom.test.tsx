import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Ramble from '@renderer/pages/kel/transcription';
import { Message } from '@arco-design/web-react';

// Ramble's shared modal reads theme context; persisted theme IO belongs to its own tests.
vi.mock('@renderer/hooks/context/ThemeContext', () => ({ useThemeContext: () => ({ theme: 'dark' }) }));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function libraryTransport(transcripts: unknown[] = [], hasKey = false) {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  const requests: Array<{ url: string; body: Record<string, unknown> }> = [];
  const folders: Array<{ id: string; name: string; created: number }> = [];
  let failRename = false;
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const body = JSON.parse(init?.body || '{}');
    requests.push({ url: String(url), body });
    let result: unknown = { folders: [...folders], transcripts };
    if (body.action === 'status') result = { mode: 'practice', label: 'Muse', has_key: hasKey };
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

it('ST-20: the old library route opens the one Ramble screen with its library', async () => {
  libraryTransport([
    { id: 'newer', name: 'Latest note', text: 'A: Current note', created: 2, updated: 2, folder_id: null, source_type: 'upload', source_filename: null, duration_ms: 1000, status: 'complete', has_audio: true },
  ]);
  render(<MemoryRouter initialEntries={['/transcription/library']}><Ramble /></MemoryRouter>);
  expect(await screen.findByRole('heading', { name: 'Ramble' })).toBeTruthy();
  expect(screen.getByRole('complementary', { name: 'Transcript library' })).toBeTruthy();
  expect((await screen.findAllByText('Latest note')).length).toBeGreaterThan(0);
  expect(screen.queryByRole('heading', { name: 'Transcriptions' })).toBeNull();
});

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

it('ST-18: Escape cancels naming a new folder; blank names keep New Folder; failed renames preserve the draft', async () => {
  const transport = libraryTransport();
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  await waitFor(() => expect(transport.requests.some(r => r.body.action === 'library')).toBe(true));
  fireEvent.click(screen.getByTestId('folder-create'));
  let input = await screen.findByTestId('folder-rename');
  fireEvent.change(input, { target: { value: 'Discard' } });
  fireEvent.keyDown(input, { key: 'Escape' });
  expect(screen.queryByTestId('folder-rename')).toBeNull();
  // The folder "+" made is gone again, in the view and in the engine.
  expect(screen.queryByRole('button', { name: 'Rename New Folder' })).toBeNull();
  await waitFor(() => expect(transport.requests.filter(r => r.body.action === 'folder_delete')).toHaveLength(1));
  transport.folders.splice(0);
  fireEvent.click(screen.getByTestId('folder-create'));
  input = await screen.findByTestId('folder-rename');
  fireEvent.keyDown(input, { key: 'Enter' });
  await waitFor(() => expect(screen.queryByTestId('folder-rename')).toBeNull());
  // Escape while renaming an existing folder only stops editing.
  fireEvent.click(screen.getByRole('button', { name: 'Rename New Folder' }));
  input = screen.getByTestId('folder-rename');
  fireEvent.keyDown(input, { key: 'Escape' });
  expect(screen.getByRole('button', { name: 'Rename New Folder' })).toBeTruthy();
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


it('lets a connected desktop key be replaced without saving a canceled draft', async () => {
  const { requests } = libraryTransport([], true);
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  await waitFor(() => expect(requests.some(r => r.body.action === 'status')).toBe(true));
  fireEvent.click(screen.getByTestId('transcription-settings'));
  const input = await screen.findByTestId('key-input');
  fireEvent.change(input, { target: { value: 'synthetic-unsaved-key' } });
  expect((screen.getByTestId('key-save') as HTMLButtonElement).disabled).toBe(false);
  expect(screen.getByTestId('key-clear')).not.toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }));
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  fireEvent.click(screen.getByTestId('transcription-settings'));
  expect((await screen.findByTestId('key-input') as HTMLInputElement).value).toBe('');
  expect(requests.some(r => r.body.action === 'set_key')).toBe(false);
});

it('VIS-19: with recordings saved, opens on the library (not the empty state) with one Upload button', async () => {
  libraryTransport([
    { id: 'a', name: 'Standup notes', text: 'A: notes', created: 3, updated: 3, folder_id: null, source_type: 'record', source_filename: null, duration_ms: 21000, status: 'complete', has_audio: true },
    { id: 'b', name: 'Groceries', text: 'B: milk', created: 2, updated: 2, folder_id: null, source_type: 'record', source_filename: null, duration_ms: 14000, status: 'complete', has_audio: true },
  ]);
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  const library = await screen.findByTestId('ramble-library');
  expect(screen.queryByText('Your transcripts live here')).toBeNull();
  expect(screen.getAllByTestId('ramble-library-row').map((row) => row.textContent)).toEqual([
    expect.stringContaining('Standup notes'),
    expect.stringContaining('Groceries'),
  ]);
  expect(screen.getAllByRole('button', { name: /upload audio/i })).toHaveLength(1);
  fireEvent.click(screen.getAllByTestId('ramble-library-row')[1]);
  expect(await screen.findByTestId('transcript-name')).toBeTruthy();
  expect(screen.getByTestId('transcript-name').textContent).toBe('Groceries');
  expect(library.isConnected).toBe(false);
});

it('VIS-19: with no recordings, the empty state explains without a second Upload button', async () => {
  libraryTransport([]);
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  expect(await screen.findByText('Your transcripts live here')).toBeTruthy();
  expect(screen.getAllByRole('button', { name: /upload audio/i })).toHaveLength(1);
});
