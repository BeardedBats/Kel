import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { WorkImport } from '@renderer/components/kel/WorkHubControls';

const api = vi.hoisted(() => ({ preview: vi.fn(), confirm: vi.fn() }));
const references = vi.hoisted(() => ({ list: vi.fn() }));
vi.mock('@renderer/components/kel/kelApi', () => ({ kelWorkImports: api, kelReferences: references }));
vi.mock('@renderer/components/kel/activeProject', () => ({ ALL_PROJECTS: '*', useProjects: () => ({ active: 'p', loaded: true }) }));
vi.mock('@renderer/components/kel/ShellSourceCardHeader', () => ({ default: () => null, sourceCard: () => null }));
vi.mock('@renderer/motion', () => ({ EdgePill: () => null }));
beforeEach(() => {
  vi.resetAllMocks();
  references.list.mockResolvedValue({ entries: [] });
  api.preview.mockResolvedValue({ preview_id: 'preview', digest: 'digest', title: 'Imported note', message_count: 1,
    snippet: 'Original text', omissions: [{ name: 'image.png', reason: 'Attachment contents were not imported' }],
    reference_files: [{ name: 'notes.md', chars: 11, sha256: 'hash', status: 'included-reference', snippet: 'Extra facts' }] });
});
afterEach(cleanup);
const file = (name: string, text: string) => {
  const value = new File([text], name, { type: 'text/plain' });
  Object.defineProperty(value, 'arrayBuffer', { value: async () => new TextEncoder().encode(text).buffer });
  return value;
};
const open = () => {
  const view = render(<MemoryRouter><WorkImport projectId="p" /></MemoryRouter>);
  fireEvent.click(screen.getByText('Import a transcript'));
  fireEvent.change(screen.getByLabelText('Transcript'), { target: { value: 'Original text' } });
  return view;
};

it('reviews selected text with original missing attachments and requires confirmation', async () => {
  open();
  fireEvent.change(screen.getByLabelText('Reference files'), { target: { files: [file('notes.md', 'Extra facts')] } });
  await screen.findByRole('button', { name: 'Remove notes.md' });
  fireEvent.click(screen.getByRole('button', { name: 'Review import' }));
  await screen.findByRole('region', { name: 'Included reference files' });
  expect(api.preview).toHaveBeenCalledWith('p', expect.objectContaining({ reference_files: [{ name: 'notes.md', text: 'Extra facts' }] }));
  expect(screen.getByText('image.png: Attachment contents were not imported')).toBeTruthy();
  expect(screen.getByText('Extra facts')).toBeTruthy();
  expect(api.confirm).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Remove notes.md' }));
  expect(screen.queryByRole('region', { name: 'Import review' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Confirm import and open chat' })).toBeNull();
});

it('rejects binary and duplicate selections without dropping earlier text', async () => {
  open();
  fireEvent.change(screen.getByLabelText('Reference files'), { target: { files: [file('notes.md', 'Extra facts')] } });
  await screen.findByRole('button', { name: 'Remove notes.md' });
  fireEvent.change(screen.getByLabelText('Reference files'), { target: { files: [file('Notes.MD', 'Changed')] } });
  await screen.findByRole('alert');
  expect(screen.getByText('Each reference file needs a different name.')).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Reference files'), { target: { files: [file('bad.txt', 'bad\u0000bytes')] } });
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('readable text files'));
  expect(screen.getByRole('button', { name: 'Remove notes.md' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Remove bad.txt' })).toBeNull();
});

it('discards a file read completed after switching Projects', async () => {
  const view = open();
  let resolve!: (value: ArrayBuffer) => void;
  const pending = new File(['Later'], 'later.txt', { type: 'text/plain' });
  Object.defineProperty(pending, 'arrayBuffer', { value: () => new Promise<ArrayBuffer>(done => { resolve = done; }) });
  fireEvent.change(screen.getByLabelText('Reference files'), { target: { files: [pending] } });
  view.rerender(<MemoryRouter><WorkImport projectId="other" /></MemoryRouter>);
  resolve(new TextEncoder().encode('Later').buffer as ArrayBuffer);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Review import' })).toBeTruthy());
  expect(screen.queryByRole('button', { name: 'Remove later.txt' })).toBeNull();
  expect((screen.getByLabelText('Transcript') as HTMLTextAreaElement).value).toBe('');
  expect((screen.getByRole('button', { name: 'Review import' }) as HTMLButtonElement).disabled).toBe(true);
  expect(api.preview).not.toHaveBeenCalled();
});

it('loads a selected transcript without guessing its source or format', async () => {
  open();
  fireEvent.change(screen.getByLabelText('Transcript file'), { target: { files: [file('saved.json', 'Selected transcript text')] } });
  await waitFor(() => expect((screen.getByLabelText('Transcript') as HTMLTextAreaElement).value).toBe('Selected transcript text'));
  fireEvent.click(screen.getByRole('button', { name: 'Review import' }));
  await waitFor(() => expect(api.preview).toHaveBeenCalledWith('p', expect.objectContaining({
    content: 'Selected transcript text', title: 'saved.json', format: 'text', source: 'other', reference_files: [] } )));
  expect(api.confirm).not.toHaveBeenCalled();
});

it('retains transcript text if a selected file is invalid or finishes in another Project', async () => {
  const view = open();
  fireEvent.change(screen.getByLabelText('Transcript file'), { target: { files: [file('bad.txt', 'bad\u0000bytes')] } });
  await screen.findByRole('alert');
  expect((screen.getByLabelText('Transcript') as HTMLTextAreaElement).value).toBe('Original text');
  let resolve!: (value: ArrayBuffer) => void;
  const pending = new File(['Later'], 'later.txt');
  Object.defineProperty(pending, 'arrayBuffer', { value: () => new Promise<ArrayBuffer>(done => { resolve = done; }) });
  fireEvent.change(screen.getByLabelText('Transcript file'), { target: { files: [pending] } });
  view.rerender(<MemoryRouter><WorkImport projectId="other" /></MemoryRouter>);
  resolve(new TextEncoder().encode('Later').buffer as ArrayBuffer);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Review import' })).toBeTruthy());
  expect((screen.getByLabelText('Transcript') as HTMLTextAreaElement).value).toBe('');
  expect((screen.getByRole('button', { name: 'Review import' }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.queryByText(/later.txt/)).toBeNull();
});
