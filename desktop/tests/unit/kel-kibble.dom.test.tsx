import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Kibble from '@renderer/pages/kel/dogfood';

vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
vi.mock('@renderer/components/kel/KelFailureCard', () => ({ KelFailureCard: ({ onRetry }: { onRetry: () => void }) => <button onClick={onRetry}>Retry load</button> }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function transport(failFirst = false) {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  const fixes = [1, 2].map(n => ({ id: `FIX-${n}`, transcript: `Synthetic finding ${n}`, status: 'OPEN', created: 1, updated: 1, route: '/guid', has_screenshot: false }));
  const requests: Array<Record<string, unknown>> = [];
  let failed = false;
  vi.stubGlobal('fetch', vi.fn(async (_url, init) => {
    const body = JSON.parse(init?.body || '{}'); requests.push(body);
    if (failFirst && !failed) { failed = true; throw new Error('Unavailable'); }
    let result: unknown;
    if (body.action === 'set_status') fixes.find(f => f.id === body.id)!.status = body.status;
    if (body.action === 'prepare_prompt') {
      fixes.filter(f => body.fix_ids.includes(f.id)).forEach(f => { f.status = 'BATCHED'; });
      result = { prompt: 'Synthetic prompt', path: 'fixture/prompt.md', fix_ids: body.fix_ids };
    } else result = { fixes: [...fixes], counts: Object.fromEntries(['OPEN', 'BATCHED', 'FIXED', 'DISMISSED'].map(s => [s, fixes.filter(f => f.status === s).length])) };
    return { ok: true, json: async () => result };
  }));
  return { fixes, requests };
}
const open = () => render(<MemoryRouter><Kibble /></MemoryRouter>);

it('prepares only selected fixes, moves them to Batched, and does not start a build', async () => {
  const { requests } = transport(); open();
  await screen.findByRole('button', { name: 'Prepare prompt (2)' });
  fireEvent.click(screen.getByTestId('fix-pick-FIX-2'));
  fireEvent.click(screen.getByRole('button', { name: 'Prepare prompt (1)' }));
  expect((await screen.findByTestId('fix-prompt')).textContent).toBe('Synthetic prompt');
  expect(requests.find(r => r.action === 'prepare_prompt')?.fix_ids).toEqual(['FIX-1']);
  expect(requests.some(r => String(r.action).includes('build'))).toBe(false);
  expect(screen.getByRole('tab', { name: 'Batched · 1' })).toBeTruthy();
});

it('offers status actions without expanding a fix and preserves Reopen', async () => {
  const { fixes } = transport(); open(); await screen.findByTestId('fix-list');
  const row = screen.getByRole('button', { name: /FIX-1.*Synthetic finding 1/ }).closest('li')!;
  fireEvent.click(within(row).getByRole('button', { name: '✓ Mark fixed' }));
  await waitFor(() => expect(fixes[0].status).toBe('FIXED'));
  fireEvent.click(screen.getByRole('tab', { name: 'Fixed · 1' }));
  fireEvent.click(screen.getByRole('button', { name: 'Reopen' }));
  await waitFor(() => expect(fixes[0].status).toBe('OPEN'));
});

it('recovers a failed initial load without changing hook order', async () => {
  transport(true); open();
  fireEvent.click(await screen.findByRole('button', { name: 'Retry load' }));
  expect(await screen.findByTestId('fix-list')).toBeTruthy();
});
