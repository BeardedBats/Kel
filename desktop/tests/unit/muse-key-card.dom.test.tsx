/**
 * D-75.3: Settings → Providers manages the Muse key with the other keys. The value goes to the
 * main process's custody (credentials.set) and never to the engine from the page.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

const kelRequest = vi.fn();
vi.mock('@renderer/components/kel/kelApi', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  kelRequest: (...args: unknown[]) => kelRequest(...args),
}));

import MuseKeyCard, { museSourceLine } from '@renderer/pages/kel/providers/MuseKeyCard';

const credentials = { set: vi.fn(async () => ({})), remove: vi.fn(async () => ({})) };
beforeEach(() => {
  kelRequest.mockReset();
  credentials.set.mockClear();
  credentials.remove.mockClear();
  (window as unknown as { kelAPI: unknown }).kelAPI = { credentials };
});
afterEach(cleanup);

it('saves the key into custody and re-reads the status', async () => {
  kelRequest.mockResolvedValue({ mode: 'unavailable', has_key: false });
  const changed = vi.fn();
  render(<MemoryRouter initialEntries={['/settings/providers?provider=muse']}>
    <MuseKeyCard secureAvailable stored={false} onChanged={changed} />
  </MemoryRouter>);
  expect((await screen.findByTestId('muse-key-source')).textContent).toMatch(/No Muse key yet/);
  const input = screen.getByLabelText('Muse API key');  // opened by the link from Ramble
  fireEvent.change(input, { target: { value: 'synthetic-muse-key' } });
  kelRequest.mockResolvedValue({ mode: 'muse', has_key: true, source: 'kel' });
  fireEvent.click(screen.getByText('Save'));
  await waitFor(() => expect(credentials.set).toHaveBeenCalledWith('muse', 'api_key', 'synthetic-muse-key'));
  await waitFor(() => expect(screen.getByTestId('muse-key-source').textContent).toMatch(/saved in the OS-backed store/));
  expect(changed).toHaveBeenCalled();
  expect(JSON.stringify(kelRequest.mock.calls)).not.toContain('synthetic-muse-key');
});

it('says plainly when the Transcriptions app key is the one in use', () => {
  expect(museSourceLine({ mode: 'muse', has_key: true, source: 'transcriptions-app' }, false)).toMatch(/Transcriptions app/);
  expect(museSourceLine({ mode: 'fixture', has_key: false }, false)).toMatch(/Practice mode/);
});

it('removes the key from custody', async () => {
  kelRequest.mockResolvedValue({ mode: 'muse', has_key: true, source: 'kel' });
  render(<MemoryRouter><MuseKeyCard secureAvailable stored onChanged={() => undefined} /></MemoryRouter>);
  await screen.findByTestId('muse-key-source');
  fireEvent.click(screen.getByText('Remove key'));
  await waitFor(() => expect(credentials.remove).toHaveBeenCalledWith('muse'));
});
