import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Kibble from '@renderer/pages/kel/dogfood';

const config = vi.hoisted(() => ({ mission: undefined as string | undefined, save: vi.fn() }));
vi.mock('@/common/config/configService', () => ({ configService: { whenReady: async () => {}, get: () => config.mission, set: config.save } }));

vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
vi.mock('@renderer/components/kel/KelFailureCard', () => ({ KelFailureCard: ({ onRetry }: { onRetry: () => void }) => <button onClick={onRetry}>Retry load</button> }));
afterEach(() => { config.mission = undefined; config.save.mockReset(); cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

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

it('restores a reviewed update without starting or assembling work', async () => {
  config.mission = 'kbm_saved';
  const { requests } = transport(); const original = fetch;
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const body = JSON.parse(init?.body as string || '{}');
    if (body.action === 'build_update') {
      requests.push(body);
      return { ok: true, json: async () => ({ mission: { id: 'kbm_saved', source_root: 'C:/saved-workspace' }, job: { id: 'saved-job', state: 'CLOSED' }, candidate: { id: 'saved-candidate', review_state: 'APPROVED', limitations: [] } }) };
    }
    return original(url, init);
  }));
  open(); await screen.findByText('Reviewed: approved.');
  expect((screen.getByTestId('build-source-root') as HTMLInputElement).value).toBe('C:/saved-workspace');
  expect(requests.filter(r => r.action === 'build_update')).toEqual([{ action: 'build_update', op: 'status', mission: 'kbm_saved' }]);
  expect(config.save).not.toHaveBeenCalled();
});
it('keeps fixes available when previous-update recovery fails', async () => {
  config.mission = 'kbm_offline'; transport(); const original = fetch;
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const body = JSON.parse(init?.body as string || '{}');
    if (body.action === 'build_update') throw new Error('Offline');
    return original(url, init);
  }));
  open(); await screen.findByText('Kel could not load the previous update. Refresh to try again.');
  expect(screen.getByTestId('fix-list')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Refresh', exact: true })).toBeTruthy();
});

it('keeps a started update visible when saving its resume pointer fails', async () => {
  const { requests } = transport(); const original = fetch;
  config.save.mockRejectedValue(new Error('Settings unavailable'));
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const body = JSON.parse(init?.body as string || '{}');
    if (body.action === 'build_update') {
      requests.push(body);
      return { ok: true, json: async () => ({ mission: { id: 'kbm_started' }, job: 'started-job' }) };
    }
    return original(url, init);
  }));
  open(); await screen.findByTestId('fix-list');
  fireEvent.change(screen.getByTestId('build-source-root'), { target: { value: 'C:/fixture-workspace' } });
  const start = screen.getByRole('button', { name: 'Start update (2)' });
  await waitFor(() => expect((start as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(start);
  await screen.findByText('The update started, but Kel could not save its place. Keep this page open.');
  expect(config.save).toHaveBeenCalledWith('kel.kibbleLastMission', 'kbm_started');
  expect(requests.filter(r => r.action === 'build_update')).toHaveLength(1);
  expect(requests.find(r => r.action === 'build_update')?.op).toBe('start');
  expect(screen.getByRole('button', { name: 'Refresh', exact: true })).toBeTruthy();
});
