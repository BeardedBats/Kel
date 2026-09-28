import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import type { OfficeItem, OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';
import {
  BACKUP,
  FIGMA_ORDER,
  KITCHEN,
  LAPTOP,
  MIC,
  MIC_DETAIL,
  PITCHER,
  RECEIPTS,
  RECEIPTS_DETAIL,
} from './fixtures/kelOfficeFixtures';

type Handler = (route: string, body?: unknown) => unknown;

let list: OfficeItem[] | Error = [];
let details: Record<string, OfficeItemDetail> = {};
let extra: Handler | null = null;

const install = () => {
  const request = vi.fn(async (route: string, body?: unknown) => {
    const custom = extra?.(route, body);
    if (custom !== undefined) {
      if (custom instanceof Error) throw custom;
      return custom;
    }
    if (route === '/api/project') return { projects: [{ id: 'personal', name: 'Personal', kind: 'user' }], active: '*' };
    if (route.startsWith('/api/office?project=')) {
      if (list instanceof Error) throw list;
      return { generated: 1, project: '*', items: list };
    }
    if (route.startsWith('/api/office/item?job=')) {
      const job = decodeURIComponent(route.split('=')[1]);
      if (details[job]) return details[job];
      throw new Error('unknown job');
    }
    if (route === '/api/office') return { ok: true };
    if (route === '/api/control') return { ok: true };
    if (route === '/api/apply') return { ok: true };
    if (route.startsWith('/api/handoff')) return { application: null };
    throw new Error(`unexpected ${route}`);
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request,
    conversation: vi.fn(async (id: string) => (id === 'app-morning' ? 'engine-morning' : id)),
    openEngineConversation: vi.fn(async (cid: string) => `app-${cid.replace('engine-', '')}`),
  };
  return request;
};

const ChatProbe: React.FC<{ width: number }> = ({ width }) => {
  const { id } = useParams();
  return (
    <div>
      <div data-testid='route'>{id}</div>
      <KelWorkCardRow conversationId={id} availableWidth={width} pollActiveMs={40} pollIdleMs={80} openFolder={openFolder} />
      <div className='sendbox-panel'>
        <textarea aria-label='Message Kel' />
      </div>
      <button type='button'>Sidebar chat</button>
    </div>
  );
};

const openFolder = vi.fn(async () => undefined);

const renderRow = (width = 920, at = '/conversation/app-morning') =>
  render(
    <MemoryRouter initialEntries={[at]}>
      <Routes>
        <Route path='/conversation/:id' element={<ChatProbe width={width} />} />
      </Routes>
    </MemoryRouter>
  );

const titles = () => screen.queryAllByTestId('kel-office-card').map((card) => card.getAttribute('data-job'));

beforeEach(() => {
  list = [];
  details = { [MIC.job_id]: MIC_DETAIL, [RECEIPTS.job_id]: RECEIPTS_DETAIL };
  extra = null;
  resetProjectsForTests();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  openFolder.mockClear();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('work card row (D-68)', () => {
  it('renders nothing at all when there is no work, so the chat keeps its height', async () => {
    const request = install();
    renderRow();
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/office?project=*', undefined));
    expect(screen.queryByTestId('kel-work-card-row')).toBeNull();
  });

  it('shows one card per item with its title, real step count, state words and team initials', async () => {
    list = [MIC, LAPTOP, PITCHER, RECEIPTS];
    install();
    renderRow();
    const card = (await screen.findAllByTestId('kel-office-card'))[0];
    expect(card.textContent).toContain('Mic mute toggle app');
    expect(card.textContent).toContain('Working');
    expect(card.textContent).toContain('2 of 5');
    // Kel himself is not in the card's stack; the staff are.
    expect(within(card).getAllByTitle(/Builder|Verifier/).map((node) => node.textContent)).toEqual(['Bu', 'Bu', 'Ve']);
    const fill = card.querySelector<HTMLElement>('.kel-wc-progress__fill');
    expect(fill?.style.width).toBe('40%');
    // States are announced in words, not colour alone.
    const states = screen.getAllByTestId('kel-office-card-state').map((node) => node.textContent);
    expect(states).toEqual(['Working', 'Needs you', 'In review', 'Done']);
    expect(screen.getByRole('button', { name: /Laptop research, Needs you, 2 of 4 steps/ })).toBeTruthy();
  });

  it('puts running and needs-you work first and finished work last, unless the engine orders it', async () => {
    list = [RECEIPTS, MIC, BACKUP, LAPTOP];
    install();
    const view = renderRow(2000);
    await screen.findAllByTestId('kel-office-card');
    expect(titles()).toEqual(['job-mic', 'job-laptop', 'job-receipts', 'job-backup']);
    view.unmount();

    list = FIGMA_ORDER;
    renderRow(2000);
    await waitFor(() => expect(titles()).toEqual(['job-mic', 'job-laptop', 'job-pitcher', 'job-receipts', 'job-kitchen', 'job-backup']));
  });

  it('measures what fits: four cards and "+2 more" with a dot per hidden card, recomputed on resize', async () => {
    list = FIGMA_ORDER;
    install();
    const view = renderRow(920);
    await screen.findAllByTestId('kel-office-card');
    expect(titles()).toEqual(['job-mic', 'job-laptop', 'job-pitcher', 'job-receipts']);
    const chip = screen.getByTestId('kel-office-overflow');
    expect(chip.textContent).toContain('+2 more');
    expect(chip.querySelectorAll('.kel-wc-dot')).toHaveLength(2);
    expect(chip.getAttribute('aria-label')).toBe('2 more: Kitchen reno quotes (working), Backup check (failed)');

    view.rerender(
      <MemoryRouter initialEntries={['/conversation/app-morning']}>
        <Routes>
          <Route path='/conversation/:id' element={<ChatProbe width={620} />} />
        </Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(titles()).toHaveLength(2));
    expect(screen.getByTestId('kel-office-overflow').textContent).toContain('+4 more');
  });

  it('opens the overflow menu split into Running and Finished, and closes it on Escape', async () => {
    list = FIGMA_ORDER;
    install();
    renderRow(920);
    fireEvent.click(await screen.findByTestId('kel-office-overflow'));
    const menu = screen.getByTestId('kel-office-menu');
    const sections = Array.from(menu.querySelectorAll('.kel-wc-menu__section')).map((node) => node.textContent);
    expect(sections).toEqual(['Running', 'Finished']);
    const entries = within(menu).getAllByTestId('kel-office-card').map((card) => card.getAttribute('data-job'));
    expect(entries).toEqual(['job-kitchen', 'job-backup']);
    // Only the finished entry can be removed.
    expect(within(menu).getAllByTestId('kel-office-card-remove')).toHaveLength(1);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByTestId('kel-office-menu')).toBeNull();
  });

  it('removes a finished card through the engine; running cards have no remove control', async () => {
    list = [MIC, RECEIPTS];
    const request = install();
    renderRow();
    await screen.findAllByTestId('kel-office-card');
    const removes = screen.getAllByTestId('kel-office-card-remove');
    expect(removes).toHaveLength(1);
    expect(removes[0].getAttribute('aria-label')).toBe('Remove Receipts tidy-up');
    list = [MIC];
    fireEvent.click(removes[0]);
    expect(titles()).toEqual(['job-mic']);
    expect(request).toHaveBeenCalledWith('/api/office', { action: 'dismiss', id: 'job-receipts' });
    // The remove button does not open the detail.
    expect(screen.queryByTestId('kel-office-detail')).toBeNull();
  });

  it('hides a removed card only until the engine’s next list, which stays the truth', async () => {
    list = [RECEIPTS];
    install();
    renderRow();
    fireEvent.click(await screen.findByTestId('kel-office-card-remove'));
    expect(titles()).toEqual([]);
    // This engine still lists it after the dismiss: the card comes back instead of being hidden forever.
    await waitFor(() => expect(titles()).toEqual(['job-receipts']));
  });

  it('brings a card back when the engine refuses to remove it', async () => {
    list = [RECEIPTS];
    install();
    extra = (route, body) => (route === '/api/office' && body ? new Error('refused') : undefined);
    renderRow();
    fireEvent.click(await screen.findByTestId('kel-office-card-remove'));
    await waitFor(() => expect(titles()).toEqual(['job-receipts']));
  });

  it('opens the detail as a dialog over a dimmed chat and closes it on Escape, returning focus', async () => {
    list = [MIC, RECEIPTS];
    install();
    renderRow();
    const open = (await screen.findAllByRole('button', { name: /^Mic mute toggle app,/ }))[0];
    fireEvent.click(open);
    const dialog = await screen.findByRole('dialog', { name: 'Mic mute toggle app' });
    expect(screen.getByTestId('kel-office-backdrop')).toBeTruthy();
    expect(open.getAttribute('aria-expanded')).toBe('true');
    expect(dialog.contains(document.activeElement)).toBe(true);
    expect(within(dialog).getByTestId('kel-office-stop')).toBeTruthy();
    expect(within(dialog).queryByTestId('kel-office-remove')).toBeNull();
    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(open);
  });

  it('closes the detail on a click outside it (the dimmed chat or the sidebar), not on a click inside', async () => {
    list = [MIC];
    install();
    renderRow();
    fireEvent.click(await screen.findByRole('button', { name: /^Mic mute toggle app,/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.mouseDown(within(dialog).getByRole('heading', { name: 'Mic mute toggle app' }));
    expect(screen.queryByRole('dialog')).not.toBeNull();
    fireEvent.mouseDown(screen.getByTestId('kel-office-backdrop'));
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /^Mic mute toggle app,/ }));
    await screen.findByRole('dialog');
    fireEvent.mouseDown(screen.getByRole('button', { name: 'Sidebar chat' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('keeps Tab inside the open detail', async () => {
    list = [MIC];
    install();
    renderRow();
    fireEvent.click(await screen.findByRole('button', { name: /^Mic mute toggle app,/ }));
    const dialog = await screen.findByRole('dialog');
    expect(document.activeElement).toBe(dialog);
    const buttons = within(dialog).getAllByRole('button');
    fireEvent.keyDown(dialog, { key: 'Tab' });
    expect(document.activeElement).toBe(buttons[0]);
    buttons[buttons.length - 1].focus();
    fireEvent.keyDown(dialog, { key: 'Tab' });
    expect(document.activeElement).toBe(buttons[0]);
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(buttons[buttons.length - 1]);
  });

  it('shows the team as role · model · reasoning, honest about the model that actually ran', async () => {
    list = [MIC];
    install();
    renderRow();
    fireEvent.click(await screen.findByRole('button', { name: /^Mic mute toggle app,/ }));
    const dialog = await screen.findByRole('dialog');
    await within(dialog).findAllByTestId('kel-office-member');
    const models = within(dialog).getAllByTestId('kel-office-model').map((node) => node.textContent);
    expect(models).toEqual([
      'ChatGPT Luna · Auto',
      'Claude Opus 5.5 · High',
      'Asked for Claude Opus 5.5 · ran Claude Opus 4.8 · High',
      'Asked for GPT-6 Astra · Medium · not confirmed yet',
    ]);
    const members = within(dialog).getAllByTestId('kel-office-member');
    expect(members[0].textContent).toContain('Kel, Commander');
    expect(members[1].textContent).toContain('Writing the global hotkey listener');
    expect(dialog.textContent).toContain('Kel + 3 on it');
    expect(dialog.textContent).toContain('Step 3 of 5');
    expect(dialog.textContent).toContain('Personal');
    const steps = within(dialog).getAllByTestId('kel-office-step').map((node) => node.querySelector('.kel-wd-step__when')?.textContent);
    expect(steps).toEqual(['9:13 AM', '9:16 AM', 'Now', 'Next', '']);
    expect(within(dialog).getByTestId('kel-office-review').textContent).toContain('1 to fix');
    expect(within(dialog).getByTestId('kel-office-oracle').textContent).toContain('Second opinion before hand-over.');
    expect(within(dialog).getByTestId('kel-office-verification').textContent).toBe('VerificationIn progress · 2 of 4 passed');
    expect(dialog.textContent).toContain('src/hotkey.ts');
  });

  it('asks before Stop and then cancels through the existing work-card path', async () => {
    list = [MIC];
    const request = install();
    renderRow();
    fireEvent.click(await screen.findByRole('button', { name: /^Mic mute toggle app,/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByTestId('kel-office-stop'));
    expect(within(dialog).getByTestId('kel-office-stop-confirm').textContent).toContain('Stop this work?');
    fireEvent.click(within(dialog).getByTestId('kel-office-stop-yes'));
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/control', { job: 'job-mic', action: 'cancel' }));
  });

  it('shows a finished result with Remove, Undo and Open folder when the applied change allows it', async () => {
    list = [RECEIPTS];
    const request = install();
    renderRow();
    fireEvent.click(await screen.findByRole('button', { name: /^Receipts tidy-up,/ }));
    const dialog = await screen.findByRole('dialog');
    await within(dialog).findByTestId('kel-office-undo');
    expect(within(dialog).getByTestId('kel-office-detail-state').textContent).toBe('Done and checked');
    expect(within(dialog).getByTestId('kel-office-result').textContent).toContain('Sorted 64 receipts');
    expect(within(dialog).getByTestId('kel-office-result').textContent).toContain('Applied automatically to C:\\Users\\Nick\\Documents\\Receipts\\2026 (65 files)');
    expect(within(dialog).queryByTestId('kel-office-stop')).toBeNull();
    expect(dialog.textContent).toContain('Kel + 3, all done');
    expect(dialog.textContent).toContain('Took 22 min');
    expect(within(dialog).getAllByTestId('kel-office-model').map((node) => node.textContent)[1]).toBe(
      'Asked for DeepSeek Flash · ran Claude Sonnet · Low'
    );
    expect(within(dialog).getByTestId('kel-office-oracle').textContent).toContain('Not asked for this work.');

    fireEvent.click(within(dialog).getByTestId('kel-office-open-folder'));
    await waitFor(() => expect(openFolder).toHaveBeenCalledWith('C:\\Users\\Nick\\Documents\\Receipts\\2026'));
    fireEvent.click(within(dialog).getByTestId('kel-office-undo'));
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/apply', { job: 'job-receipts', action: 'undo' }));

    list = [];
    fireEvent.click(within(dialog).getByTestId('kel-office-remove'));
    expect(request).toHaveBeenCalledWith('/api/office', { action: 'dismiss', id: 'job-receipts' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('never says "checked" for finished work whose checks did not pass', async () => {
    list = [RECEIPTS];
    details[RECEIPTS.job_id] = { ...RECEIPTS_DETAIL, review: { verdict: 'UNCERTAIN', findings: [] }, verification: { result: 'not_run', summary: [] } };
    install();
    renderRow();
    fireEvent.click(await screen.findByRole('button', { name: /^Receipts tidy-up,/ }));
    const dialog = await screen.findByRole('dialog');
    await within(dialog).findAllByTestId('kel-office-member');
    expect(within(dialog).getByTestId('kel-office-detail-state').textContent).toBe('Done');
  });

  it('"Talk to Kel about this" focuses the composer here, or opens that work’s chat first', async () => {
    list = [MIC, KITCHEN];
    install();
    renderRow(2000);
    fireEvent.click(await screen.findByRole('button', { name: /^Mic mute toggle app,/ }));
    fireEvent.click(await screen.findByTestId('kel-office-talk'));
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Message Kel')));
    expect(screen.getByTestId('route').textContent).toBe('app-morning');
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /^Kitchen reno quotes,/ }));
    fireEvent.click(await screen.findByTestId('kel-office-talk'));
    await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('app-kitchen'));
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Message Kel')));
  });

  it('reads the team from the item detail when the list does not carry it', async () => {
    list = [{ ...MIC, team: undefined }];
    install();
    renderRow();
    await waitFor(() => expect(screen.getAllByTitle(/Builder|Verifier/).map((node) => node.textContent)).toEqual(['Bu', 'Bu', 'Ve']));
  });

  it('keeps the last good cards when a later read fails, and polls fast only while work runs', async () => {
    list = [MIC];
    const request = install();
    renderRow();
    await screen.findAllByTestId('kel-office-card');
    list = new Error('engine away');
    const before = request.mock.calls.filter(([route]) => String(route).startsWith('/api/office?')).length;
    await waitFor(() =>
      expect(request.mock.calls.filter(([route]) => String(route).startsWith('/api/office?')).length).toBeGreaterThan(before + 1)
    );
    expect(titles()).toEqual(['job-mic']);
  });
});

describe('work card row polling cadence', () => {
  it('reads every 4 s while work runs, every 30 s when idle, and pauses while the window is hidden', async () => {
    vi.useFakeTimers();
    list = [MIC];
    const request = install();
    render(
      <MemoryRouter initialEntries={['/conversation/app-morning']}>
        <Routes>
          <Route path='/conversation/:id' element={<KelWorkCardRow conversationId='app-morning' availableWidth={920} />} />
        </Routes>
      </MemoryRouter>
    );
    const reads = () => request.mock.calls.filter(([route]) => String(route).startsWith('/api/office?')).length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(reads()).toBe(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(reads()).toBe(2);

    list = [RECEIPTS];
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(reads()).toBe(3);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(29000);
    });
    expect(reads()).toBe(3);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1100);
    });
    expect(reads()).toBe(4);

    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
    document.dispatchEvent(new Event('visibilitychange'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(120000);
    });
    expect(reads()).toBe(4);
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
    document.dispatchEvent(new Event('visibilitychange'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(reads()).toBe(5);
  });
});
