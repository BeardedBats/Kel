/**
 * D-57: the Scheduled surface renders from the engine's `/api/schedules` payloads (the shapes
 * pinned in the design's "Contract changes"), degrades in place when fields are missing (JR-47),
 * shows no machinery nouns, and sends the engine the actions it names.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { resetSchedulesForTest } from '@renderer/pages/cron/useSchedules';

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }));
vi.mock('@arco-design/web-react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@arco-design/web-react')>()),
  Message: toast,
}));
vi.mock('@/renderer/hooks/context/ThemeContext', () => ({ useThemeContext: () => ({ theme: 'dark' }) }));

type Body = Record<string, unknown>;

const MACHINERY = /\b(cron|cadence|origin|slot|submission|schedule_id|next_due_at|start_mode|interval)\b/i;

const brief = {
  id: 'sched-1',
  name: 'Morning brief',
  project_id: 'site',
  project_name: 'Website',
  target: { kind: 'instruction', text: 'Summarize yesterday.' },
  cadence: { kind: 'cron', expr: '0 9 * * MON-FRI' },
  timezone: null,
  timezone_label: 'This computer’s time',
  start_mode: 'new_conversation',
  conversation_id: null,
  model: null,
  model_label: 'Automatic',
  skip_if_running: true,
  enabled: true,
  status: 'active',
  description: 'Every weekday at 9:00 AM',
  next_due_at: 1790000000,
  running: false,
  last_run: null,
  problem: null,
  origin: 'donor-7',
  created: 1780000000,
  updated: 1780000000,
};

const engine = {
  schedules: [] as unknown[],
  history: [] as unknown[],
  calls: [] as Array<{ route: string; body?: Body }>,
  refuseCreate: null as string | null,
  failList: false,
  preview: { valid: true, message: null, description: 'Every weekday at 9:00 AM', next: [1790000000], timezone_label: 'This computer’s time' } as Record<string, unknown>,
};

const request = vi.fn(async (route: string, body?: Body) => {
  engine.calls.push({ route, body });
  if (route === '/api/project') return { projects: [{ id: 'default', name: 'General', kind: 'general' }, { id: 'site', name: 'Website', kind: 'user' }], active: '*' };
  if (route === '/api/model') return { default: null, conversation: null, providers: [{ id: 'anthropic', label: 'Claude', available: true, options: [{ id: 'sonnet', label: 'Claude Sonnet', available: true }, { id: 'opus', label: 'Claude Opus', available: false, note: 'Needs setup' }] }] };
  if (route !== '/api/schedules') return {};
  switch (body?.action) {
    case 'list':
      if (engine.failList) throw new Error('Kel is not answering right now.');
      return { schedules: engine.schedules, needs_attention: 0 };
    case 'get': {
      const found = engine.schedules.find((row) => row && typeof row === 'object' && ((row as Body).id === body.id || (body.origin && (row as Body).origin === body.origin)));
      if (!found) throw new Error('That scheduled task is not found.');
      return { schedule: found, conversations: { created: 2, open: 0 } };
    }
    case 'history':
      return { rows: engine.history };
    case 'preview':
      return engine.preview;
    case 'create':
      if (engine.refuseCreate) throw new Error(engine.refuseCreate);
      return { schedule: { ...brief, id: 'sched-new', name: body.name } };
    case 'run_now':
      return { submission: 'sched-1-manual', conversation: 'cid-run-9' };
    case 'delete':
      return { ok: true, id: body.id, hidden: ['cid-run-1'], kept_open: [] };
    default:
      return { schedule: brief };
  }
});
const openEngineConversation = vi.fn(async (cid: string) => `donor-${cid}`);
const schedulesChanged = vi.fn(async () => ({ ok: true }));

const Where = () => {
  const location = useLocation();
  return <output data-testid='route'>{`${location.pathname}${location.search}`}</output>;
};

const renderAt = async (entry: string) => {
  const { default: ScheduledTasksPage } = await import('@renderer/pages/cron/ScheduledTasksPage');
  const { default: TaskDetailPage } = await import('@renderer/pages/cron/ScheduledTasksPage/TaskDetailPage');
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path='/scheduled' element={<><ScheduledTasksPage /><Where /></>} />
        <Route path='/scheduled/:id' element={<><TaskDetailPage /><Where /></>} />
        <Route path='*' element={<Where />} />
      </Routes>
    </MemoryRouter>
  );
};

beforeEach(() => {
  engine.schedules = [brief];
  engine.history = [];
  engine.calls = [];
  engine.refuseCreate = null;
  engine.failList = false;
  for (const fn of Object.values(toast)) fn.mockClear();
  if (!window.matchMedia) {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: (query: string) => ({ matches: false, media: query, onchange: null, addListener: () => undefined, removeListener: () => undefined, addEventListener: () => undefined, removeEventListener: () => undefined, dispatchEvent: () => false }),
    });
  }
  engine.preview = { valid: true, message: null, description: 'Every weekday at 9:00 AM', next: [1790000000], timezone_label: 'This computer’s time' };
  request.mockClear();
  openEngineConversation.mockClear();
  schedulesChanged.mockClear();
  (window as unknown as { kelAPI: unknown }).kelAPI = { request, openEngineConversation, schedulesChanged, conversation: async () => null };
  resetProjectsForTests();
  resetSchedulesForTest();
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Scheduled tasks list (D-57)', () => {
  it('renders the engine’s schedules with their own words and status', async () => {
    engine.schedules = [
      brief,
      { ...brief, id: 'sched-2', name: 'Inbox triage', enabled: false, status: 'paused', description: 'Every 2 hours' },
      { ...brief, id: 'sched-3', name: 'Rankings refresh', enabled: false, status: 'needs_attention', problem: 'Its recipe was deleted.' },
    ];
    await renderAt('/scheduled');
    const first = await screen.findByTestId('scheduled-row-sched-1');
    expect(within(first).getByText(/Every weekday at 9:00 AM · next/)).toBeTruthy();
    expect(within(first).getByText('Active')).toBeTruthy();
    expect(within(screen.getByTestId('scheduled-row-sched-2')).getByText('Paused')).toBeTruthy();
    expect(within(screen.getByTestId('scheduled-row-sched-3')).getByText('Needs attention')).toBeTruthy();
    expect(screen.getByText('Scheduled tasks run while Kel is open on this computer.')).toBeTruthy();
    expect(document.body.textContent).not.toMatch(MACHINERY);
  });

  it('degrades a row with missing fields in place and drops what is not a schedule (JR-47)', async () => {
    engine.schedules = [{ id: 'bare' }, 'nonsense', { name: 'no id' }, null];
    await renderAt('/scheduled');
    const row = await screen.findByTestId('scheduled-row-bare');
    expect(within(row).getByText('Untitled task')).toBeTruthy();
    expect(within(row).getByText('Schedule unavailable')).toBeTruthy();
    expect(screen.getByText('1 task')).toBeTruthy();
  });

  it('says so in place when the engine cannot answer, and the page stays usable', async () => {
    engine.failList = true;
    await renderAt('/scheduled');
    expect(await screen.findByText('Scheduled tasks are unavailable right now.')).toBeTruthy();
    expect(screen.getAllByRole('button', { name: 'New task' }).length).toBeGreaterThan(0);
  });

  it('opens the task a pre-move link names (`?origin=`)', async () => {
    await renderAt('/scheduled?origin=donor-7');
    await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('/scheduled/sched-1'));
  });

  it('says a pre-move link’s task is gone instead of guessing', async () => {
    await renderAt('/scheduled?origin=donor-missing');
    expect(await screen.findByText('That scheduled task is no longer here. It may have been deleted.')).toBeTruthy();
  });
});

describe('Scheduled task page (D-57)', () => {
  it('shows the details and the engine’s history, and opens a run’s chat', async () => {
    engine.history = [
      { at: 1789990000, slot: 1789990000, late_by: 0, conversation: 'cid-run-1', job_id: 'job-1', submission_id: 's-1', status: 'success', label: 'Success', cause: null },
      { at: 1789900000, slot: 1789900000, late_by: 0, conversation: null, job_id: null, submission_id: null, status: 'missed', label: 'Missed 3 runs while Kel was closed', cause: null },
    ];
    await renderAt('/scheduled/sched-1');
    expect(await screen.findByRole('heading', { name: 'Morning brief' })).toBeTruthy();
    expect(screen.getByText('Summarize yesterday.')).toBeTruthy();
    expect(screen.getByText('Website')).toBeTruthy();
    expect(screen.getByText('Automatic')).toBeTruthy();
    expect(await screen.findByText('Missed 3 runs while Kel was closed')).toBeTruthy();
    expect(screen.getByText('Success')).toBeTruthy();
    expect(document.body.textContent).not.toMatch(MACHINERY);
    const openButtons = screen.getAllByRole('button', { name: 'Open' });
    expect(openButtons).toHaveLength(1);
    fireEvent.click(openButtons[0]);
    await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('/conversation/donor-cid-run-1'));
    expect(openEngineConversation).toHaveBeenCalledWith('cid-run-1');
  });

  it('shows a paused task’s problem, and a task with missing fields still renders (JR-47)', async () => {
    engine.schedules = [{ id: 'sched-1', name: 'Broken', problem: 'Its project was archived.', enabled: false }];
    engine.history = [{ label: null }];
    await renderAt('/scheduled/sched-1');
    expect(await screen.findByText('Its project was archived.')).toBeTruthy();
    expect(screen.getAllByText('Needs attention').length).toBeGreaterThan(0);
    expect(screen.getByText('Unavailable right now.')).toBeTruthy();
    expect(screen.getByText('Schedule unavailable')).toBeTruthy();
    expect(await screen.findByText('Time unavailable')).toBeTruthy();
  });

  it('runs now and opens the run’s conversation', async () => {
    await renderAt('/scheduled/sched-1');
    fireEvent.click(await screen.findByRole('button', { name: 'Run now' }));
    await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('/conversation/donor-cid-run-9'));
    expect(engine.calls.some((call) => call.body?.action === 'run_now' && call.body.id === 'sched-1')).toBe(true);
  });

  it('pauses through the engine', async () => {
    await renderAt('/scheduled/sched-1');
    fireEvent.click(await screen.findByRole('button', { name: 'Pause' }));
    await waitFor(() => expect(engine.calls.some((call) => call.body?.action === 'pause' && call.body.id === 'sched-1')).toBe(true));
  });

  it('deletes, hiding the finished runs’ chats by default, and tells the main process which', async () => {
    await renderAt('/scheduled/sched-1');
    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Delete task' }));
    await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('/scheduled'));
    expect(engine.calls.find((call) => call.body?.action === 'delete')?.body).toEqual({ action: 'delete', id: 'sched-1', conversations: 'delete' });
    expect(schedulesChanged).toHaveBeenCalledWith({ hidden: ['cid-run-1'] });
  });

  it('says a task that is gone is gone', async () => {
    await renderAt('/scheduled/nope');
    expect(await screen.findByText('This scheduled task is no longer here. It may have been deleted.')).toBeTruthy();
  });
});

describe('New scheduled task dialog (D-57)', () => {
  const openDialog = async () => {
    engine.schedules = [];
    await renderAt('/scheduled');
    const buttons = await screen.findAllByRole('button', { name: 'New task' });
    fireEvent.click(buttons[0]);
    return screen.findByRole('dialog');
  };

  it('fixes the assistant to Kel and creates through the engine with the draft it describes', async () => {
    const dialog = await openDialog();
    expect(within(dialog).getByText('Kel')).toBeTruthy();
    fireEvent.change(within(dialog).getByPlaceholderText('Morning brief'), { target: { value: 'Evening wrap' } });
    fireEvent.change(within(dialog).getByPlaceholderText(/Summarize yesterday/), { target: { value: 'Wrap up the day.' } });
    fireEvent.click(within(dialog).getAllByText('Weekdays')[0]);
    expect(await within(dialog).findByTestId('scheduled-task-preview')).toBeTruthy();
    await waitFor(() => expect(within(dialog).getByTestId('scheduled-task-preview').textContent).toMatch(/Every weekday at 9:00 AM\. Next:/));
    await act(async () => {
      fireEvent.click(within(dialog).getByRole('button', { name: 'Create task' }));
    });
    await waitFor(() => expect(engine.calls.some((call) => call.body?.action === 'create')).toBe(true));
    const created = engine.calls.find((call) => call.body?.action === 'create')!.body!;
    expect(created).toMatchObject({
      name: 'Evening wrap',
      project_id: 'default',
      target: { kind: 'instruction', text: 'Wrap up the day.' },
      cadence: { kind: 'cron', expr: '0 9 * * MON-FRI' },
      timezone: null,
      start_mode: 'new_conversation',
      model: null,
      skip_if_running: true,
    });
  });

  it('shows the engine’s refusal in its own words', async () => {
    engine.refuseCreate = 'That project is archived. Pick another project.';
    const dialog = await openDialog();
    fireEvent.change(within(dialog).getByPlaceholderText('Morning brief'), { target: { value: 'X' } });
    fireEvent.change(within(dialog).getByPlaceholderText(/Summarize yesterday/), { target: { value: 'Y' } });
    await act(async () => {
      fireEvent.click(within(dialog).getByRole('button', { name: 'Create task' }));
    });
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('That project is archived. Pick another project.'));
  });

  it('shows the engine’s reason when it cannot use a timing', async () => {
    engine.preview = { valid: false, message: 'Kel runs a task at most every 5 minutes.', description: '', next: [] };
    const dialog = await openDialog();
    fireEvent.click(within(dialog).getAllByText('Hourly')[0]);
    await waitFor(() => expect(within(dialog).getByTestId('scheduled-task-preview').textContent).toBe('Kel runs a task at most every 5 minutes.'));
    expect(within(dialog).getByTestId('scheduled-task-preview').getAttribute('data-tone')).toBe('error');
  });

  it('keeps the recipe picker and project under Advanced settings', async () => {
    const dialog = await openDialog();
    expect(within(dialog).queryByTestId('scheduled-task-advanced')).toBeNull();
    fireEvent.click(within(dialog).getByRole('button', { name: /Advanced settings/ }));
    const advanced = within(dialog).getByTestId('scheduled-task-advanced');
    expect(within(advanced).getByText('Project')).toBeTruthy();
    expect(within(advanced).getByText('Run a recipe instead')).toBeTruthy();
  });
});

describe('Empty Scheduled (VIS-17)', () => {
  it('has one "New task" primary and an example that needs no connection Kel lacks', async () => {
    engine.schedules = [];
    await renderAt('/scheduled');
    expect(await screen.findByText('No scheduled tasks yet.')).toBeTruthy();
    expect(Array.from(document.querySelectorAll('.kel-btn--primary')).map((button) => button.textContent)).toEqual(['New task']);
    expect(document.body.textContent).not.toMatch(/inbox|email|gmail/i);
  });
});
