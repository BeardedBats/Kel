/**
 * D-57: a chat menu's "Create scheduled task" opens the scheduled-task editor filled in from that
 * chat — a name, the chat's request as the instructions, and the chat's project — instead of the
 * retired donor behaviour (a canned "every day at 10am…" prompt dropped into the chat's composer).
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TChatConversation } from '@/common/config/storage';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { resetSchedulesForTest } from '@renderer/pages/cron/useSchedules';

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }));
vi.mock('@arco-design/web-react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@arco-design/web-react')>()),
  Message: toast,
}));
vi.mock('@/renderer/hooks/context/ThemeContext', () => ({ useThemeContext: () => ({ theme: 'dark' }) }));

type Msg = { id: string; type: string; position: string; content: { content: string } };
const history = vi.hoisted(() => ({ pages: [] as Array<{ items: Msg[]; before?: string }>, calls: [] as Array<Record<string, unknown>> }));
vi.mock('@/renderer/utils/chat/messagePagination', () => ({
  loadConversationMessagePage: vi.fn(async (_id: string, options: { before?: string }) => {
    history.calls.push(options);
    const index = options.before ? Number(options.before) : 0;
    const page = history.pages[index] ?? { items: [] };
    const more = index + 1 < history.pages.length;
    return { items: page.items, has_more_before: more, oldest_cursor: more ? String(index + 1) : null };
  }),
  loadAllConversationMessagesPaged: vi.fn(async () => []),
}));

const text = (id: string, position: 'left' | 'right', content: string): Msg => ({ id, type: 'text', position, content: { content } });

type Body = Record<string, unknown>;
const engine = { chatProject: 'site' as string | null, calls: [] as Array<{ route: string; body?: Body }> };
const request = vi.fn(async (route: string, body?: Body) => {
  engine.calls.push({ route, body });
  if (route === '/api/project') {
    if (body?.action === 'of') return { project: engine.chatProject, pending: false };
    return { projects: [{ id: 'default', name: 'General', kind: 'general' }, { id: 'site', name: 'Website', kind: 'user' }], active: '*' };
  }
  if (route === '/api/model') return { default: null, conversation: null, providers: [] };
  if (route !== '/api/schedules') return {};
  if (body?.action === 'list') return { schedules: [], needs_attention: 0 };
  if (body?.action === 'preview') return { valid: true, description: 'Every day at 9:00 AM', next: [1790000000] };
  if (body?.action === 'create') return { schedule: { id: 'sched-new', name: body.name } };
  return {};
});

const Where = () => {
  const location = useLocation();
  return <output data-testid='route'>{location.pathname}</output>;
};

const chat = (overrides: Partial<TChatConversation> = {}) =>
  ({ id: 'chat-7', name: 'Weekly competitor digest', type: 'acp', extra: {}, createTime: 1, modifyTime: 1, ...overrides }) as unknown as TChatConversation;

const renderFromChat = async (conversation: TChatConversation) => {
  const { useConversationActions } = await import('@renderer/pages/conversation/GroupedHistory/hooks/useConversationActions');
  const { default: ScheduledTasksPage } = await import('@renderer/pages/cron/ScheduledTasksPage');
  const MenuEntry = () => {
    const actions = useConversationActions({
      batchMode: false,
      selectedConversationIds: new Set(),
      setSelectedConversationIds: () => undefined,
      toggleSelectedConversation: () => undefined,
      markManualUnread: () => undefined,
      clearManualUnread: () => undefined,
      isManualUnread: () => false,
    });
    return <button type='button' onClick={() => actions.handleCreateCronTask(conversation)}>Create scheduled task</button>;
  };
  render(
    <MemoryRouter initialEntries={[`/conversation/${conversation.id}`]}>
      <Routes>
        <Route path='/conversation/:id' element={<MenuEntry />} />
        <Route path='/scheduled' element={<><ScheduledTasksPage /><Where /></>} />
      </Routes>
    </MemoryRouter>
  );
  fireEvent.click(screen.getByRole('button', { name: 'Create scheduled task' }));
  return screen.findByRole('dialog');
};

beforeEach(() => {
  engine.chatProject = 'site';
  engine.calls = [];
  history.calls = [];
  history.pages = [{ items: [text('m1', 'right', 'Every Monday, compare our prices with the three main competitors and list what changed.'), text('m2', 'left', 'On it.'), text('m3', 'right', 'Thanks!')] }];
  for (const fn of Object.values(toast)) fn.mockClear();
  if (!window.matchMedia) {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: (query: string) => ({ matches: false, media: query, onchange: null, addListener: () => undefined, removeListener: () => undefined, addEventListener: () => undefined, removeEventListener: () => undefined, dispatchEvent: () => false }),
    });
  }
  (window as unknown as { kelAPI: unknown }).kelAPI = { request, schedulesChanged: vi.fn(async () => ({ ok: true })), conversation: async () => 'eng-7' };
  resetProjectsForTests();
  resetSchedulesForTest();
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Create scheduled task from a chat (D-57)', () => {
  it('opens the editor on Scheduled tasks with the chat’s name, request and project', async () => {
    const dialog = await renderFromChat(chat());
    expect(screen.getByTestId('route').textContent).toBe('/scheduled');
    await waitFor(() => expect((within(dialog).getByPlaceholderText('Morning brief') as HTMLInputElement).value).toBe('Weekly competitor digest'));
    expect((within(dialog).getByPlaceholderText(/Summarize yesterday/) as HTMLTextAreaElement).value).toBe(
      'Every Monday, compare our prices with the three main competitors and list what changed.'
    );
    // The chat's project is not General, so the project picker is shown with it chosen.
    const advanced = await within(dialog).findByTestId('scheduled-task-advanced');
    expect(within(advanced).getByText('Website')).toBeTruthy();
    // The chat can be kept as the place each run posts to.
    await waitFor(() => expect(within(dialog).getByText('Adds to the same chat')).toBeTruthy());
    expect(engine.calls.some((call) => call.body?.action === 'of' && call.body?.donor === 'chat-7')).toBe(true);

    await act(async () => {
      fireEvent.click(within(dialog).getByRole('button', { name: 'Create task' }));
    });
    await waitFor(() => expect(engine.calls.some((call) => call.body?.action === 'create')).toBe(true));
    expect(engine.calls.find((call) => call.body?.action === 'create')!.body).toMatchObject({
      name: 'Weekly competitor digest',
      project_id: 'site',
      target: { kind: 'instruction', text: 'Every Monday, compare our prices with the three main competitors and list what changed.' },
    });
  });

  it('names an untitled chat after its request, and reads back to the chat’s first request', async () => {
    history.pages = [
      { items: [text('m9', 'right', 'Also include shipping costs.'), text('m10', 'left', 'Sure.')] },
      { items: [text('m1', 'right', 'Summarize the support inbox every evening'), text('m2', 'left', 'Done.')] },
    ];
    engine.chatProject = 'default';
    const dialog = await renderFromChat(chat({ name: 'New Chat' }));
    await waitFor(() => expect((within(dialog).getByPlaceholderText('Morning brief') as HTMLInputElement).value).toBe('Summarize the support inbox every evening'));
    expect((within(dialog).getByPlaceholderText(/Summarize yesterday/) as HTMLTextAreaElement).value).toBe('Summarize the support inbox every evening');
    expect(history.calls).toHaveLength(2);
    // General is the default: Advanced settings stay closed.
    expect(within(dialog).queryByTestId('scheduled-task-advanced')).toBeNull();
  });

  it('never drops a canned prompt into the chat, and a blank New task is not filled in', async () => {
    const dialog = await renderFromChat(chat());
    await waitFor(() => expect((within(dialog).getByPlaceholderText('Morning brief') as HTMLInputElement).value).toBe('Weekly competitor digest'));
    expect(document.body.textContent).not.toMatch(/latest AI news/);
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    fireEvent.click(screen.getAllByRole('button', { name: 'New task' })[0]);
    const blank = await screen.findByRole('dialog');
    expect((within(blank).getByPlaceholderText('Morning brief') as HTMLInputElement).value).toBe('');
  });
});
