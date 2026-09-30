import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Kibble from '@renderer/pages/kel/dogfood';

vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
vi.mock('@renderer/components/kel/KelFailureCard', () => ({
  KelFailureCard: ({ onRetry }: { onRetry: () => void }) => <button onClick={onRetry}>Retry load</button>,
}));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function transport(failFirst = false) {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  const fixes = [1, 2].map((n) => ({
    id: `FIX-${n}`,
    transcript: `Synthetic finding ${n}`,
    status: 'OPEN',
    created: 1,
    updated: 1,
    route: '/guid',
    has_screenshot: false,
  }));
  const requests: Array<Record<string, unknown>> = [];
  let failed = false;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url, init) => {
      const body = JSON.parse(init?.body || '{}');
      requests.push(body);
      if (failFirst && !failed) {
        failed = true;
        throw new Error('Unavailable');
      }
      let result: unknown;
      if (body.action === 'set_status') fixes.find((f) => f.id === body.id)!.status = body.status;
      if (body.action === 'prepare_prompt') {
        fixes
          .filter((f) => body.fix_ids.includes(f.id))
          .forEach((f) => {
            f.status = 'BATCHED';
          });
        result = { prompt: 'Synthetic prompt', path: 'fixture/prompt.md', fix_ids: body.fix_ids };
      } else
        result = {
          fixes: [...fixes],
          counts: Object.fromEntries(
            ['OPEN', 'BATCHED', 'FIXED', 'DISMISSED'].map((s) => [s, fixes.filter((f) => f.status === s).length])
          ),
        };
      return { ok: true, json: async () => result };
    })
  );
  return { fixes, requests };
}
const open = () =>
  render(
    <MemoryRouter>
      <Kibble />
    </MemoryRouter>
  );

it('prepares only selected fixes, moves them to Batched, and does not start a build', async () => {
  const { requests } = transport();
  open();
  await screen.findByRole('button', { name: 'Prepare prompt (2)' });
  fireEvent.click(screen.getByTestId('fix-pick-FIX-2'));
  fireEvent.click(screen.getByRole('button', { name: 'Prepare prompt (1)' }));
  expect((await screen.findByTestId('fix-prompt')).textContent).toBe('Synthetic prompt');
  expect(requests.find((r) => r.action === 'prepare_prompt')?.fix_ids).toEqual(['FIX-1']);
  expect(requests.some((r) => String(r.action).includes('build'))).toBe(false);
  expect(screen.getByRole('tab', { name: 'Batched · 1' })).toBeTruthy();
});

it('offers status actions without expanding a fix and preserves Reopen', async () => {
  const { fixes } = transport();
  open();
  await screen.findByTestId('fix-list');
  const row = screen.getByRole('button', { name: /FIX-1.*Synthetic finding 1/ }).closest('li')!;
  fireEvent.click(within(row).getByRole('button', { name: '✓ Mark fixed' }));
  await waitFor(() => expect(fixes[0].status).toBe('FIXED'));
  fireEvent.click(screen.getByRole('tab', { name: 'Fixed · 1' }));
  fireEvent.click(screen.getByRole('button', { name: 'Reopen' }));
  await waitFor(() => expect(fixes[0].status).toBe('OPEN'));
});

it('recovers a failed initial load without changing hook order', async () => {
  transport(true);
  open();
  fireEvent.click(await screen.findByRole('button', { name: 'Retry load' }));
  expect(await screen.findByTestId('fix-list')).toBeTruthy();
});

// Sending work requires a deliberate action. Merely opening Kibble never starts development.
it('does not start work on load and keeps prompt export available', async () => {
  const { requests } = transport();
  open();
  await screen.findByTestId('fix-list');
  expect(screen.queryByText(/Build an update|Build Update/)).toBeNull();
  expect(screen.queryByTestId('build-source-root')).toBeNull();
  expect(screen.queryByRole('button', { name: /Start update/ })).toBeNull();
  expect(screen.getByRole('button', { name: 'Prepare prompt (2)' })).toBeTruthy();
  expect(requests.some((r) => String(r.action).includes('build'))).toBe(false);
  expect(requests.some((r) => r.action === 'send_to_kel')).toBe(false);
  expect(screen.getAllByRole('button', { name: 'Send to Kel' })).toHaveLength(2);
});

it('sends one finding, shows durable activity, and keeps completed work distinct from an install', async () => {
  const { fixes, requests } = transport();
  const baselineFetch = globalThis.fetch;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url, init) => {
      const body = JSON.parse(String(init?.body || '{}'));
      if (body.action !== 'send_to_kel') return baselineFetch(url, init);
      requests.push(body);
      Object.assign(fixes[0], {
        status: 'BATCHED',
        work: {
          submission_id: 'submission-1',
          conversation: 'work-chat',
          job_id: 'job-1',
          state: 'COMPLETED',
          error: null,
          updated: 2,
          verification: 'PASS',
          application: null,
          installed: false,
          milestones: [{ id: 'build', state: 'completed' }],
          events: [],
          activity: [{ seq: 1, at: 2, kind: 'fileChange', text: 'Changing files', state: 'completed' }],
          messages: [{ seq: 2, at: 2, role: 'assistant', text: 'Checked the composer change.' }],
        },
      });
      return { ok: true, json: async () => fixes[0] } as Response;
    })
  );
  open();
  await screen.findByTestId('fix-list');
  const row = screen.getByRole('button', { name: /FIX-1.*Synthetic finding 1/ }).closest('li')!;
  fireEvent.click(within(row).getByRole('button', { name: 'Send to Kel' }));
  const panel = await screen.findByTestId('kibble-work');
  expect(requests.filter((r) => r.action === 'send_to_kel')).toEqual([{ action: 'send_to_kel', id: 'FIX-1' }]);
  expect(within(panel).getByText('Work finished')).toBeTruthy();
  expect(within(panel).getByText(/Update: Not installed/)).toBeTruthy();
  expect(within(panel).getByText('Checked the composer change.')).toBeTruthy();
  expect(within(panel).getByText(/Changing files/)).toBeTruthy();
  cleanup();
  open();
  expect(await screen.findByTestId('kibble-work')).toBeTruthy();
  expect(requests.filter((r) => r.action === 'send_to_kel')).toHaveLength(1);
});

it('shows failed send errors beside the saved reports and permits a retry', async () => {
  transport();
  const baselineFetch = globalThis.fetch;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url, init) => {
      if (JSON.parse(String(init?.body || '{}')).action === 'send_to_kel') throw new Error('Offline');
      return baselineFetch(url, init);
    })
  );
  open();
  await screen.findByTestId('fix-list');
  fireEvent.click(screen.getAllByRole('button', { name: 'Send to Kel' })[0]);
  expect((await screen.findByRole('alert')).textContent).toContain("can't reach Kel");
  expect(screen.getByTestId('fix-list')).toBeTruthy();
  await waitFor(() =>
    expect((screen.getAllByRole('button', { name: 'Send to Kel' })[0] as HTMLButtonElement).disabled).toBe(false)
  );
});

it('offers reviewed source Apply and candidate Build only after each real gate', async () => {
  const { fixes, requests } = transport();
  const work = {
    submission_id: 's',
    conversation: 'engine-chat',
    job_id: 'job',
    state: 'COMPLETED',
    error: null,
    updated: 1,
    verification: 'VERIFIED',
    application: null as null | { state: string },
    installed: false,
    activity: [],
    messages: [],
    events: [],
    milestones: [],
  };
  Object.assign(fixes[0], { status: 'BATCHED', work });
  const baselineFetch = globalThis.fetch;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url, init) => {
      const body = JSON.parse(String(init?.body || '{}'));
      if (body.action === 'apply_work') {
        requests.push(body);
        work.application = { state: 'APPLIED' };
        return { ok: true, json: async () => fixes[0] } as Response;
      }
      if (body.action === 'build_update') {
        requests.push(body);
        return { ok: true, json: async () => fixes[0] } as Response;
      }
      return baselineFetch(url, init);
    })
  );
  open();
  await screen.findByTestId('kibble-work');
  expect(screen.queryByRole('button', { name: 'Build update' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Apply source changes' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Build update' }));
  await waitFor(() => expect(requests.some((r) => r.action === 'build_update' && r.id === 'FIX-1')).toBe(true));
  expect(requests.filter((r) => r.action === 'apply_work')).toEqual([{ action: 'apply_work', id: 'FIX-1' }]);
  expect(screen.queryByRole('button', { name: 'Install update' })).toBeNull();
});

it('opens the adopted work conversation and passes only a finding id to the installer bridge', async () => {
  const { fixes } = transport();
  Object.assign(fixes[0], {
    status: 'BATCHED',
    work: {
      submission_id: 's',
      conversation: 'engine-chat',
      job_id: 'job',
      state: 'COMPLETED',
      error: null,
      updated: 1,
      verification: 'VERIFIED',
      application: { state: 'APPLIED' },
      installed: false,
      activity: [],
      messages: [],
      events: [],
      milestones: [],
      release: {
        state: 'READY',
        stage: 'Update installer ready',
        error: null,
        installer_path: 'ignored/renderer/path.exe',
        candidate_path: 'ignored',
        log: [],
        installed: false,
      },
    },
  });
  const adopt = vi.fn(async () => 'app-chat');
  const installer = vi.fn(async () => ({ opened: true, installed: false }));
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    openEngineConversation: adopt,
    kibbleInstaller: installer,
    request: async (route: string, body?: unknown) => (await fetch(route, { body: JSON.stringify(body ?? {}) })).json(),
  };
  open();
  await screen.findByTestId('kibble-work');
  fireEvent.click(screen.getByRole('button', { name: 'Open work chat' }));
  await waitFor(() => expect(adopt).toHaveBeenCalledWith('engine-chat'));
  fireEvent.click(screen.getByRole('button', { name: 'Install update' }));
  await waitFor(() => expect(installer).toHaveBeenCalledWith('FIX-1', false));
  expect(screen.getByText(/Update: Source changes applied; app install pending/)).toBeTruthy();
});

it('recovers a voice-only capture with no words before offering Send', async () => {
  const { fixes } = transport();
  Object.assign(fixes[0], { transcript: '' });
  const baselineFetch = globalThis.fetch;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url, init) => {
      const body = JSON.parse(String(init?.body || '{}'));
      if (body.action === 'set_note') {
        fixes[0].transcript = body.transcript;
        return { ok: true, json: async () => fixes[0] } as Response;
      }
      return baselineFetch(url, init);
    })
  );
  open();
  await screen.findByTestId('fix-list');
  fireEvent.click(screen.getByRole('button', { name: 'Add note' }));
  fireEvent.change(screen.getByLabelText('What went wrong?'), { target: { value: 'The button does nothing.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save note' }));
  await waitFor(() => expect(fixes[0].transcript).toBe('The button does nothing.'));
  await waitFor(() => expect(screen.getAllByRole('button', { name: 'Send to Kel' })).toHaveLength(2));
});

it('shows a plain line for a finding whose voice did not come through (FIX-0019)', async () => {
  const { fixes } = transport();
  Object.assign(fixes[0], { transcript: '', diagnostics: { voice: 'none' } });
  open();
  await screen.findByTestId('fix-list');
  expect(
    screen.getAllByText(/No words came through — the screenshot and the spot you clicked were saved\./).length
  ).toBeGreaterThan(0);
});
