/**
 * D-68 on the phone (inferred; docs/v2/FIGMA_GAPS.md "Work cards on the phone"): the cards are a
 * compact strip under the header that scrolls sideways, and a tapped card opens its detail as a
 * bottom sheet — team, steps, checks, the Needs-you answer box, Apply / Leave it, Undo, Stop and
 * "Talk to Kel about this" — with the actions in a foot above the home indicator. Engine calls are
 * faked at the `kelAPI.request` seam, as in the desktop card tests.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { takePendingWorkCard } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import type { OfficeItem, OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';
import { FIGMA_ORDER, LAPTOP, MIC, MIC_DETAIL, RECEIPTS, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

let list: OfficeItem[] = [];
let details: Record<string, OfficeItemDetail> = {};

const install = () => {
  const request = vi.fn(async (route: string, body?: unknown) => {
    if (route === '/api/project') return { projects: [{ id: 'personal', name: 'Personal', kind: 'user' }], active: '*' };
    if (route.startsWith('/api/office?project=')) return { generated: 1, project: '*', items: list };
    if (route.startsWith('/api/office/item?job=')) {
      const job = decodeURIComponent(route.split('=')[1]);
      if (details[job]) return details[job];
      throw new Error('That work has no live team to show.');
    }
    if (route.startsWith('/api/handoff')) return { application: null };
    void body;
    return { ok: true };
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request,
    conversation: vi.fn(async (id: string) => (id === 'app-morning' ? 'engine-morning' : id)),
    openEngineConversation: vi.fn(async (cid: string) => `app-${cid.replace('engine-', '')}`),
  };
  return request;
};

const posts = (request: ReturnType<typeof install>, route: string) =>
  request.mock.calls.filter(([called, body]) => called === route && body !== undefined).map(([, body]) => body);

const Chat: React.FC = () => {
  const { id } = useParams();
  return (
    <div>
      <KelWorkCardRow conversationId={id} phone pollActiveMs={40} pollIdleMs={80} />
      <div className='sendbox-panel'>
        <textarea aria-label='Message Kel' />
      </div>
    </div>
  );
};

const renderPhone = () =>
  render(
    <MemoryRouter initialEntries={['/conversation/app-morning']}>
      <Routes>
        <Route path='/conversation/:id' element={<Chat />} />
      </Routes>
    </MemoryRouter>
  );

const LAPTOP_DETAIL: OfficeItemDetail = {
  ...LAPTOP,
  team: undefined,
  staff: [],
  steps: [],
  question: {
    kind: 'second_opinion',
    text: 'An independent second opinion raised a problem. Apply the change anyway?',
    detail: 'An independent second opinion found a problem: Any password is accepted.',
    options: [
      { id: 'apply_anyway', label: 'Apply anyway' },
      { id: 'leave', label: 'Leave it' },
    ],
    answer_box: true,
    conversation_id: 'engine-laptop',
    ref: { job: 'job-laptop' },
  },
};

const openCard = async (name: RegExp) => {
  fireEvent.click(await screen.findByRole('button', { name }));
  const sheet = await screen.findByTestId('kel-work-sheet');
  return { sheet, dialog: within(sheet).getByRole('dialog') };
};

beforeEach(() => {
  list = [];
  details = {};
  resetProjectsForTests();
  takePendingWorkCard();
  document.body.style.overflow = '';
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('the phone strip', () => {
  it('puts every card in one sideways strip: no "+N more", no tiny remove ×', async () => {
    list = FIGMA_ORDER;
    install();
    renderPhone();
    const row = await screen.findByTestId('kel-work-card-row');
    await waitFor(() => expect(within(row).getAllByTestId('kel-office-card')).toHaveLength(FIGMA_ORDER.length));
    expect(row.getAttribute('data-layout')).toBe('phone');
    expect(row.classList.contains('kel-wc-host--phone')).toBe(true);
    expect(within(row).getByRole('list', { name: 'Work in progress' }).classList.contains('kel-wc-row--phone')).toBe(true);
    expect(screen.queryByTestId('kel-office-overflow')).toBeNull();
    // The compact card keeps its team (up to two) beside the title so the state words fit at 164px.
    const mic = within(row).getAllByTestId('kel-office-card').find((card) => card.getAttribute('data-job') === MIC.job_id)!;
    expect(mic.classList.contains('kel-wc--strip')).toBe(true);
    const stack = mic.querySelector('.kel-wc__title-row .kel-wc-agents');
    expect(stack).toBeTruthy();
    expect(stack!.querySelectorAll('.kel-wc-avatar').length).toBeLessThanOrEqual(2);
    expect(mic.querySelector('.kel-wc__state-row .kel-wc-agents')).toBeNull();
    // Finished work is removed from its sheet on the phone (a 44pt Remove), never from a 12px ×.
    expect(screen.queryByTestId('kel-office-card-remove')).toBeNull();
    // No desktop backdrop until a card is open, and then the sheet brings its own scrim.
    expect(screen.queryByTestId('kel-office-backdrop')).toBeNull();
  });

  it('renders nothing with no work, so the chat keeps its height', async () => {
    const request = install();
    renderPhone();
    await waitFor(() => expect(request.mock.calls.some(([route]) => String(route).startsWith('/api/office?project='))).toBe(true));
    expect(screen.queryByTestId('kel-work-card-row')).toBeNull();
  });
});

describe('the bottom sheet', () => {
  it('opens over the page with the team, steps and checks in one column, and the actions in its foot', async () => {
    list = [MIC];
    details = { [MIC.job_id]: MIC_DETAIL };
    install();
    renderPhone();
    const { sheet, dialog } = await openCard(/Mic mute toggle app/);
    // Portalled to the body so it covers the phone header and the composer, not just the chat column.
    expect(sheet.parentElement).toBe(document.body);
    expect(dialog.classList.contains('kel-wd--sheet')).toBe(true);
    expect(dialog.querySelector('.kel-wd-sheet__handle')).toBeTruthy();
    await within(dialog).findAllByTestId('kel-office-member');
    const body = within(dialog).getByTestId('kel-office-sheet-body');
    // D-79: the same simplified parts as the desktop panel.
    expect(within(body).getByRole('heading', { name: /^Team · \d+ agents?$/ })).toBeTruthy();
    expect(within(body).getByRole('heading', { name: 'Steps' })).toBeTruthy();
    expect(within(body).getByRole('heading', { name: 'Review Team' })).toBeTruthy();
    expect(within(body).getAllByTestId('kel-office-step').length).toBeGreaterThan(0);
    const foot = within(dialog).getByTestId('kel-office-sheet-foot');
    expect(within(foot).getByTestId('kel-office-talk').textContent).toBe('Talk to Kel about this');
    expect(within(foot).getByTestId('kel-office-stop')).toBeTruthy();
    // The head carries no actions on the phone (they would be out of thumb reach).
    expect(dialog.querySelector('.kel-wd-head .kel-wd-actions')).toBeNull();
    // D-79: no footer text.
    expect(dialog.querySelector('.kel-wd-footer')).toBeNull();
    // The page behind stays still while the sheet is open.
    expect(document.body.style.overflow).toBe('hidden');
  });

  it('closes on the scrim and on Escape, and lets the page scroll again', async () => {
    list = [MIC];
    details = { [MIC.job_id]: MIC_DETAIL };
    install();
    renderPhone();
    let opened = await openCard(/Mic mute toggle app/);
    fireEvent.click(within(opened.sheet).getByRole('button', { name: 'Close work details' }));
    await waitFor(() => expect(screen.queryByTestId('kel-work-sheet')).toBeNull());
    expect(document.body.style.overflow).toBe('');
    opened = await openCard(/Mic mute toggle app/);
    fireEvent.keyDown(opened.dialog, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('kel-work-sheet')).toBeNull());
  });

  it('Stop asks first, then cancels the work', async () => {
    list = [MIC];
    details = { [MIC.job_id]: MIC_DETAIL };
    const request = install();
    renderPhone();
    const { dialog } = await openCard(/Mic mute toggle app/);
    fireEvent.click(within(dialog).getByTestId('kel-office-stop'));
    const confirm = within(dialog).getByTestId('kel-office-stop-confirm');
    expect(confirm.closest('[data-testid="kel-office-sheet-foot"]')).toBeTruthy();
    expect(confirm.textContent).toContain('Stop this work? Anything already checked is kept.');
    fireEvent.click(within(confirm).getByTestId('kel-office-stop-yes'));
    await waitFor(() => expect(posts(request, '/api/control')).toEqual([{ job: MIC.job_id, action: 'cancel' }]));
  });

  it('Needs you: the question, Apply anyway / Leave it and the answer box, answered from the sheet', async () => {
    list = [{ ...LAPTOP, kind: 'code' }];
    details = { [LAPTOP.job_id]: { ...LAPTOP_DETAIL, kind: 'code' } };
    const request = install();
    renderPhone();
    const { dialog } = await openCard(/Laptop research/);
    const question = await within(dialog).findByTestId('kel-needs-question');
    expect(question.closest('[data-testid="kel-office-sheet-body"]')).toBeTruthy();
    expect(within(question).getByText(/Any password is accepted/)).toBeTruthy();
    expect(within(question).getByRole('radio', { name: 'Apply anyway' })).toBeTruthy();
    expect(within(question).getByPlaceholderText('Or type your answer…')).toBeTruthy();
    fireEvent.click(within(question).getByRole('radio', { name: 'Leave it' }));
    expect((await within(dialog).findByTestId('kel-needs-answered')).textContent).toContain('Kel left it as it is');
    expect(posts(request, '/api/apply')).toEqual([{ job: 'job-laptop', action: 'leave' }]);
  });

  it('D-79: finished work offers Remove — no Undo (Nick asks Kel) and no Open (that folder is on the PC)', async () => {
    list = [RECEIPTS];
    details = { [RECEIPTS.job_id]: RECEIPTS_DETAIL };
    const request = install();
    renderPhone();
    const { dialog } = await openCard(/Receipts tidy-up/);
    const foot = within(dialog).getByTestId('kel-office-sheet-foot');
    expect(await within(foot).findByTestId('kel-office-remove')).toBeTruthy();
    expect(within(dialog).queryByTestId('kel-office-undo')).toBeNull();
    expect(within(dialog).queryByTestId('kel-office-open-folder')).toBeNull();
    expect(within(dialog).getByTestId('kel-office-detail-state').textContent).toBe('Complete');
    fireEvent.click(within(foot).getByTestId('kel-office-remove'));
    await waitFor(() => expect(screen.queryByTestId('kel-work-sheet')).toBeNull());
    await waitFor(() => expect(posts(request, '/api/office')).toEqual([{ action: 'dismiss', id: RECEIPTS.job_id }]));
  });

  it('"Talk to Kel about this" closes the sheet and goes to the work’s own chat', async () => {
    list = [MIC];
    details = { [MIC.job_id]: MIC_DETAIL };
    install();
    renderPhone();
    const { dialog } = await openCard(/Mic mute toggle app/);
    fireEvent.click(within(dialog).getByTestId('kel-office-talk'));
    await waitFor(() => expect(screen.queryByTestId('kel-work-sheet')).toBeNull());
  });
});

describe('safe areas and touch (the phone CSS)', () => {
  const css = fs.readFileSync(
    path.resolve(__dirname, '../../packages/desktop/src/renderer/components/kel/workCards/KelWorkCardsPhone.css'),
    'utf8'
  );
  it('keeps the strip inside the side insets and the sheet foot above the home indicator', () => {
    expect(css).toMatch(/\.kel-wc-row\.kel-wc-row--phone \{[^}]*env\(safe-area-inset-left\)[^}]*\}/);
    expect(css).toMatch(/\.kel-wc-row\.kel-wc-row--phone \{[^}]*env\(safe-area-inset-right\)[^}]*\}/);
    expect(css).toMatch(/\.kel-wd-sheet__foot \{[^}]*env\(safe-area-inset-bottom\)[^}]*\}/);
    expect(css).toMatch(/\.kel-wd\.kel-wd--sheet \{[^}]*env\(safe-area-inset-top\)[^}]*\}/);
  });
  it('gives the answer box 16px text (no iOS zoom) and 44px actions', () => {
    expect(css).toMatch(/\.kel-wd--sheet \.kel-answer__box \{[^}]*font-size: 16px/);
    expect(css).toMatch(/\.kel-wd-sheet__foot \.kel-wd-button \{[^}]*height: 44px/);
  });
});
