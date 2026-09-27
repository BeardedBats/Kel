/**
 * Small chat and navigation fixes from the 2026-09-26 audit:
 *   WK-8/JR-28  scheduled-task rows open their own page; the empty list teaches;
 *   CH-6/JR-43  the Home (new chat) draft survives navigation and restart, and clears on send;
 *   CH-11       a sidebar row shows live background work (hand-offs) as working;
 *   CH-13       the model menu's "This chat" row names the default it falls back to;
 *   WK-15       the palette reaches Diagnostics and Set up, finds a job by its full request, and
 *               opens Work with that job selected.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

const cron = vi.hoisted(() => ({
  jobs: [] as Array<Record<string, unknown>>,
}));

vi.mock('@renderer/pages/cron/useSchedules', () => ({
  useSchedules: () => ({ schedules: cron.jobs, loading: false, loaded: true, error: null, refresh: async () => undefined }),
}));
vi.mock('@renderer/pages/cron/ScheduledTasksPage/CreateTaskDialog', () => ({
  default: ({ visible }: { visible: boolean }) => (visible ? <div data-testid='create-task-dialog' /> : null),
}));

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const Where = () => {
  const location = useLocation();
  return <div data-testid='where'>{`${location.pathname}${location.search}`}</div>;
};

describe('Scheduled tasks list (WK-8, JR-28)', () => {
  it('opens a task’s own page from its row', async () => {
    cron.jobs = [
      { id: 'cron-1', name: 'Morning inbox summary', project_id: 'default', enabled: true, next_due_at: 1, cadence: { kind: 'cron', expr: '0 9 * * 1-5' }, description: 'Every weekday at 9:00 AM' },
    ];
    const { default: ScheduledTasksPage } = await import('@renderer/pages/cron/ScheduledTasksPage');
    render(
      <MemoryRouter initialEntries={['/scheduled']}>
        <Routes>
          <Route path='/scheduled' element={<ScheduledTasksPage />} />
          <Route path='/scheduled/:id' element={<Where />} />
        </Routes>
      </MemoryRouter>
    );
    fireEvent.click(screen.getByTestId('scheduled-row-cron-1'));
    expect(screen.getByTestId('where').textContent).toBe('/scheduled/cron-1');
  });

  it('teaches when there are no tasks, with one way to make one', async () => {
    cron.jobs = [];
    const { default: ScheduledTasksPage } = await import('@renderer/pages/cron/ScheduledTasksPage');
    render(
      <MemoryRouter>
        <ScheduledTasksPage />
      </MemoryRouter>
    );
    expect(screen.getByText('No scheduled tasks yet.')).toBeTruthy();
    expect(screen.getByText(/on a schedule/)).toBeTruthy();
    const create = screen.getAllByRole('button', { name: 'New task' });
    fireEvent.click(create[create.length - 1]);
    expect(screen.getByTestId('create-task-dialog')).toBeTruthy();
  });
});

describe('Home draft (CH-6, JR-43)', () => {
  it('keeps unsent Home text across unmount and a fresh module load, and clears it when emptied', async () => {
    const { useGuidInput, HOME_DRAFT_ID } = await import('@renderer/pages/guid/hooks/useGuidInput');
    const first = renderHook(() => useGuidInput({ locationState: null }));
    act(() => first.result.current.setInput('Plan a trip to Lisbon'));
    first.unmount();

    // Navigation: a new Home mounts with the same text.
    const second = renderHook(() => useGuidInput({ locationState: null }));
    expect(second.result.current.input).toBe('Plan a trip to Lisbon');
    second.unmount();

    // Restart: the draft is in the same persisted draft store conversation drafts use.
    const stored = JSON.parse(window.localStorage.getItem('kel.sendbox.drafts.v1') ?? '{}');
    expect(stored.acp[HOME_DRAFT_ID].content).toBe('Plan a trip to Lisbon');
    vi.resetModules();
    const reloaded = await import('@renderer/pages/guid/hooks/useGuidInput');
    const third = renderHook(() => reloaded.useGuidInput({ locationState: null }));
    expect(third.result.current.input).toBe('Plan a trip to Lisbon');

    // Sending clears the input, which clears the stored draft.
    act(() => third.result.current.setInput(''));
    const after = JSON.parse(window.localStorage.getItem('kel.sendbox.drafts.v1') ?? '{}');
    expect(after.acp[HOME_DRAFT_ID]).toBeUndefined();
    third.unmount();
  });
});

describe('Sidebar live work (CH-11)', () => {
  it('marks a chat working while its handed-off work runs, and waiting when it needs an OK', async () => {
    const live = await import('@renderer/components/kel/useKelLiveWork');
    const map = live.liveWorkByConversation([
      { id: 'a', state: 'RUNNING', conversation: 'c1' },
      { id: 'b', state: 'WAITING_RESOURCE', route_block: 'busy', conversation: 'c2' },
      { id: 'c', state: 'AWAITING_USER', conversation: 'c3' },
      { id: 'd', state: 'RUNNING', conversation: 'c3' },
      { id: 'e', state: 'CLOSED', verdict: 'VERIFIED', conversation: 'c4' },
      { id: 'f', state: 'PAUSED', conversation: 'c5' },
    ]);
    expect(Object.fromEntries(map)).toEqual({ c1: 'working', c2: 'working', c3: 'waiting' });

    live.resetLiveWork();
    const { result } = renderHook(() => live.useKelLiveWork('engine-9'));
    expect(result.current).toBeNull();
    act(() => live.announceHandoffLive('engine-9', 'sub-1', true));
    expect(result.current).toBe('working');
    act(() => live.announceHandoffLive('engine-9', 'sub-1', false));
    expect(result.current).toBeNull();
  });
});

describe('Model menu (CH-13)', () => {
  it('names the default a chat falls back to', async () => {
    const { KelDesktopModelMenu } = await import('@renderer/components/kel/KelDesktopModelMenu');
    const state = {
      default: { provider: 'a', model: 'one' },
      conversation: { provider: 'a', model: 'one' },
      providers: [{ id: 'a', label: 'Provider', available: true, options: [{ id: 'one', label: 'Model One', available: true }] }],
    };
    const onChoose = vi.fn(async () => {});
    render(<KelDesktopModelMenu state={state} hasConversation onChoose={onChoose} onClose={vi.fn()} onAdd={vi.fn()} onSettings={vi.fn()} />);
    expect(screen.queryByText(/Uses default/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Use default (Model One)' }));
    await waitFor(() => expect(onChoose).toHaveBeenCalledWith(null, 'conversation'));
  });
});

describe('Command palette (WK-15)', () => {
  const openPalette = async (request: ReturnType<typeof vi.fn>) => {
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    const { default: KelCommandPalette } = await import('@renderer/components/kel/KelCommandPalette');
    render(
      <MemoryRouter initialEntries={['/guid']}>
        <KelCommandPalette />
        <Routes>
          <Route path='*' element={<Where />} />
        </Routes>
      </MemoryRouter>
    );
    await act(async () => {
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    });
  };

  it('reaches Diagnostics and Set up, finds a job by its full request, and opens it selected on Work', async () => {
    let jobs = [{ id: 'job-7', state: 'PAUSED', contract: { request: 'Collect receipts from the shared folder and total them by month for the tax return' } }];
    const request = vi.fn(async (route: string) => {
      if (route.startsWith('/api/state')) return { jobs, providers: [], projects: [] };
      return {};
    });
    await openPalette(request);
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'diagnostics' } });
    expect(screen.getByRole('option', { name: /Diagnostics/ })).toBeTruthy();
    fireEvent.change(input, { target: { value: 'set up' } });
    expect(screen.getByRole('option', { name: /Set up Kel/ })).toBeTruthy();

    // Words from past the 60-character label still find the job.
    fireEvent.change(input, { target: { value: 'tax return' } });
    const option = await screen.findByRole('option', { name: /Collect receipts/ });
    fireEvent.click(option);
    expect(screen.getByTestId('where').textContent).toBe('/work?job=job-7');

    // Reopening re-reads the jobs, so work started since the last open is findable.
    jobs = [...jobs, { id: 'job-8', state: 'RUNNING', contract: { request: 'Water the plants reminder' } }];
    await act(async () => {
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'water the plants' } });
    expect(await screen.findByRole('option', { name: /Water the plants/ })).toBeTruthy();
  });
});
