import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { WorkImport } from '@renderer/components/kel/WorkHubControls';

const references = vi.hoisted(() => ({ list: vi.fn(), extract: vi.fn(), discard: vi.fn() }));
vi.mock('@renderer/components/kel/kelApi', () => ({ kelReferences: references, kelWorkImports: { preview: vi.fn() } }));
vi.mock('@renderer/components/kel/activeProject', () => ({ ALL_PROJECTS: '*', useProjects: () => ({ active: 'p', loaded: true }) }));
vi.mock('@renderer/components/kel/ShellSourceCardHeader', () => ({ default: () => null, sourceCard: () => null }));
vi.mock('@renderer/motion', () => ({ EdgePill: () => null }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it('stops later extractions after Project change and discards the completed old receipt', async () => {
  references.list.mockResolvedValue({ entries: [] });
  references.discard.mockResolvedValue({ discarded: true });
  let resolve!: (value: unknown) => void;
  references.extract.mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  const view = render(<MemoryRouter><WorkImport projectId="p" /></MemoryRouter>);
  fireEvent.click(screen.getByText('Import a transcript'));
  const files = ['first.pdf', 'later.pdf'].map(name => {
    const file = new File(['%PDF-inert'], name, { type: 'application/pdf' });
    Object.defineProperty(file, 'arrayBuffer', { value: async () => new TextEncoder().encode('%PDF-inert').buffer });
    return file;
  });
  fireEvent.change(screen.getByLabelText('Reference files'), { target: { files } });
  await waitFor(() => expect(references.extract).toHaveBeenCalledTimes(1));
  view.rerender(<MemoryRouter><WorkImport projectId="other" /></MemoryRouter>);
  await act(async () => { resolve({ id: 'old-receipt', name: 'first.pdf', text_chars: 10 }); });
  await waitFor(() => expect(references.discard).toHaveBeenCalledWith('p', 'old-receipt'));
  expect(references.extract).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(/first.pdf/)).toBeNull();
  expect(screen.queryByText(/later.pdf/)).toBeNull();
});

it('shows the full extracted text for review beyond the metadata excerpt', async () => {
  references.list.mockResolvedValue({ entries: [] });
  const text = 'Page text. '.repeat(90) + 'Last-page detail to review.';
  references.extract.mockResolvedValue({ id: 'source', name: 'review.pdf', kind: 'pdf', text_chars: text.length,
    snippet: text.slice(0, 600), text });
  render(<MemoryRouter><WorkImport projectId="p" /></MemoryRouter>);
  fireEvent.click(screen.getByText('Import a transcript'));
  const file = new File(['%PDF-inert'], 'review.pdf', { type: 'application/pdf' });
  Object.defineProperty(file, 'arrayBuffer', { value: async () => new TextEncoder().encode('%PDF-inert').buffer });
  fireEvent.change(screen.getByLabelText('Reference files'), { target: { files: [file] } });
  fireEvent.click(await screen.findByText('Review all extracted text'));
  expect(screen.getByText(text).textContent).toBe(text);
  expect(screen.getByText(text).textContent).toContain('Last-page detail to review.');
});
