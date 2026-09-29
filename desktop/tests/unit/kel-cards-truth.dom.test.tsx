/**
 * The card and truth fixes from the visual and live audits (D-73, D-74), as behaviour: the row follows
 * the open chat's project (VIS-1 / LIVE-4), plain verification and team words (VIS-3..VIS-6, LIVE-10),
 * Undo truth (LIVE-12), the change report's new home and Vetting's (KelWorkPanel retirement), and the
 * Scoping card taking Nick to its questions (LIVE-7). Engine calls are faked at `kelAPI.request`.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow, mergeOfficeLists, revealScopingQuestions } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { KelOfficeDetail, reportFileName } from '@renderer/components/kel/workCards/KelOfficeDetail';
import { KelDoneCard } from '@renderer/components/kel/workCards/KelDoneCard';
import { KelWorkLine } from '@renderer/components/kel/workCards/KelWorkLine';
import { KelScopingCard, vettingPrompt } from '@renderer/components/kel/workCards/KelScopingCard';
import { openWorkCard, takePendingWorkCard } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { emitter } from '@/renderer/utils/emitter';
import type { OfficeItem, OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';
import { AT, MIC, MIC_DETAIL, RECEIPTS, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

type Handler = (route: string, body?: unknown) => unknown;

let extra: Handler | null = null;
let chatProject: { project: unknown; pending: boolean } = { project: null, pending: false };
let projectItems: Record<string, OfficeItem[]> = {};
let chatItems: Record<string, OfficeItem[]> = {};
let details: Record<string, OfficeItemDetail> = {};

const install = () => {
  const request = vi.fn(async (route: string, body?: unknown) => {
    const custom = extra?.(route, body);
    if (custom !== undefined) {
      if (custom instanceof Error) throw custom;
      return custom;
    }
    if (route === '/api/project') {
      const action = (body as { action?: string } | undefined)?.action;
      if (action === 'of') return chatProject;
      return {
        projects: [
          { id: 'personal', name: 'Personal', kind: 'user' },
          { id: 'calc', name: 'Calc demo', kind: 'user' },
        ],
        active: 'personal',
      };
    }
    if (route.startsWith('/api/office?project=')) {
      const project = decodeURIComponent(route.split('=')[1]);
      return { generated: 1, project, items: projectItems[project] ?? [] };
    }
    if (route.startsWith('/api/office?conversation=')) {
      const cid = decodeURIComponent(route.split('=')[1]);
      return { generated: 1, items: chatItems[cid] ?? [] };
    }
    if (route.startsWith('/api/office/item?job=')) {
      const job = decodeURIComponent(route.split('=')[1]);
      if (details[job]) return details[job];
      throw new Error('That work has no live team to show.');
    }
    if (route.startsWith('/api/handoff')) return { application: null };
    return { ok: true };
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request,
    conversation: vi.fn(async (id: string) => (id.startsWith('app-') ? `engine-${id.slice(4)}` : id)),
    openEngineConversation: vi.fn(async (cid: string) => `app-${cid.replace('engine-', '')}`),
  };
  return request;
};

const Chat: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { id } = useParams();
  return (
    <div>
      <div data-testid='route'>{id}</div>
      <KelWorkCardRow conversationId={id} availableWidth={920} pollActiveMs={40} pollIdleMs={80} openFolder={async () => undefined} />
      <div className='sendbox-panel'>
        <textarea aria-label='Message Kel' />
      </div>
      {children}
    </div>
  );
};

const renderChat = (at = '/conversation/app-calc', children?: React.ReactNode) =>
  render(
    <MemoryRouter initialEntries={[at]}>
      <Routes>
        <Route path='/conversation/:id' element={<Chat>{children}</Chat>} />
      </Routes>
    </MemoryRouter>
  );

const officeReads = (request: ReturnType<typeof install>) =>
  request.mock.calls.map(([route]) => String(route)).filter((route) => route.startsWith('/api/office?'));

const detailProps = { pollMs: 60000, onClose: vi.fn(), onRemove: vi.fn(), onTalk: vi.fn(), onChanged: vi.fn(), openFolder: vi.fn(async () => undefined) };

beforeEach(() => {
  extra = null;
  chatProject = { project: null, pending: false };
  projectItems = {};
  chatItems = {};
  details = { [MIC.job_id]: MIC_DETAIL, [RECEIPTS.job_id]: RECEIPTS_DETAIL };
  takePendingWorkCard();
  resetProjectsForTests();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

/* ─── VIS-1 / LIVE-4 / D-73.4 ─────────────────────────────────────────────────────────────── */

describe('the card row follows the open chat (D-73.4)', () => {
  it("shows the open chat's project's work, not the active project's", async () => {
    chatProject = { project: { id: 'calc', name: 'Calc demo' }, pending: false };
    const calcJob: OfficeItem = { ...MIC, job_id: 'job-calc', title: 'Add power()', project_id: 'calc', conversation_id: 'engine-calc' };
    projectItems = { calc: [calcJob], personal: [RECEIPTS] };
    const request = install();
    renderChat();
    expect((await screen.findAllByTestId('kel-office-card')).map((card) => card.getAttribute('data-job'))).toEqual(['job-calc']);
    expect(officeReads(request)).toContain('/api/office?project=calc');
    expect(officeReads(request)).not.toContain('/api/office?project=personal');
    // It also reads this chat's own work, so its in-thread line always has its card.
    expect(officeReads(request)).toContain('/api/office?conversation=engine-calc');
  });

  it('follows the active project in a chat Kel has not seen yet', async () => {
    chatProject = { project: { id: 'personal', name: 'Personal' }, pending: true };
    projectItems = { personal: [RECEIPTS] };
    const request = install();
    renderChat('/conversation/app-new');
    expect((await screen.findAllByTestId('kel-office-card')).map((card) => card.getAttribute('data-job'))).toEqual(['job-receipts']);
    expect(officeReads(request)).toContain('/api/office?project=personal');
    expect(officeReads(request).some((route) => route.startsWith('/api/office?conversation='))).toBe(false);
  });

  it("keeps this chat's own work on the row when it landed in another project", async () => {
    chatProject = { project: { id: 'calc', name: 'Calc demo' }, pending: false };
    const elsewhere: OfficeItem = { ...MIC, project_id: 'new-app', conversation_id: 'engine-calc' };
    projectItems = { calc: [] };
    chatItems = { 'engine-calc': [elsewhere] };
    install();
    renderChat();
    expect((await screen.findAllByTestId('kel-office-card')).map((card) => card.getAttribute('data-job'))).toEqual(['job-mic']);
  });

  it('opens the card a line asks for even when the row did not list it', async () => {
    chatProject = { project: { id: 'calc', name: 'Calc demo' }, pending: false };
    projectItems = { calc: [{ ...MIC, job_id: 'job-calc', title: 'Add power()' }] };
    install();
    renderChat();
    await screen.findAllByTestId('kel-office-card');
    act(() => openWorkCard(RECEIPTS.job_id));
    const dialog = await screen.findByTestId('kel-office-detail');
    expect(dialog.textContent).toContain('Receipts tidy-up');
    expect(screen.getAllByTestId('kel-office-card').map((card) => card.getAttribute('data-job'))).toContain('job-receipts');
  });

  it('merges without doubling and drops orders that cannot be compared', () => {
    const a = { ...MIC, order: 0 };
    const b = { ...RECEIPTS, order: 1 };
    expect(mergeOfficeLists([a, b], [{ ...a }])).toEqual([a, b]);
    const merged = mergeOfficeLists([a], [b]);
    expect(merged.map((item) => item.job_id)).toEqual(['job-mic', 'job-receipts']);
    expect(merged.every((item) => item.order === undefined)).toBe(true);
  });
});

/* ─── VIS-3..VIS-6, LIVE-10, LIVE-12 in the detail ─────────────────────────────────────────── */

const renderDetail = (detail: OfficeItemDetail) => {
  details = { [detail.job_id]: detail };
  const request = install();
  render(<KelOfficeDetail item={detail as unknown as OfficeItem} {...detailProps} />);
  return request;
};

describe('the detail says it plainly', () => {
  it('D-79: the Review Team says "Not started" when nothing has been checked (VIS-3)', async () => {
    renderDetail({ ...MIC_DETAIL, state: 'working', verification: { result: null, summary: [] }, review: null });
    expect((await screen.findByTestId('kel-office-review-state')).textContent).toBe('Not started');
  });

  it('D-79: the Review Team shows one status and none of the old blocks (VIS-4 lines are gone)', async () => {
    renderDetail({
      ...RECEIPTS_DETAIL,
      verification: { result: 'passed', summary: ['Verified', '• Your existing tests still pass'] },
      oracle: { state: 'done', why: 'The change touches 26 files', independence: 'different', model_label: 'GPT-6 Astra', findings: [] },
    });
    const review = await screen.findByTestId('kel-office-review');
    expect(within(review).getByTestId('kel-office-review-state').textContent).toBe('Passed');
    expect(review.textContent).not.toMatch(/Verifier|Oracle|Verification|different model family|Asked because|existing tests/);
    expect(screen.queryByTestId('kel-office-verification')).toBeNull();
    expect(screen.queryByTestId('kel-office-oracle')).toBeNull();
  });

  it('D-79: the team heading counts agents ("Team · 1 agent"), and stopped work says its result once (VIS-5)', async () => {
    renderDetail({
      ...RECEIPTS_DETAIL,
      state: 'stopped',
      result: null,
      status_line: 'You stopped this work.',
      why: 'You stopped this work.',
      next: 'Its saved request is kept in this conversation.',
      staff: [{ id: 'kel', role: 'kel', role_label: 'Kel', state: 'done', note: 'Kel used its standard coding plan.' }],
    });
    const dialog = await screen.findByTestId('kel-office-detail');
    await within(dialog).findAllByTestId('kel-office-member');
    expect(dialog.textContent).not.toMatch(/Kel \+ 0|all done/);
    expect(dialog.querySelector('.kel-wd-col--team h3')?.textContent).toBe('Team · 1 agent');
    // "You stopped this work." once, not twice.
    const result = within(dialog).getByTestId('kel-office-result');
    expect(result.textContent?.match(/You stopped this work\./g)?.length).toBe(1);
  });

  it('marks the step paused work stopped at with "Paused" (VIS-6)', async () => {
    renderDetail({
      ...MIC_DETAIL,
      state: 'needs_you',
      question: { kind: 'paused', text: 'This work is paused.', options: [{ id: 'resume', label: 'Continue' }] },
    });
    const steps = await screen.findAllByTestId('kel-office-step');
    expect(steps[2].className).toContain('kel-wd-step--paused');
    expect(steps[2].querySelector('.kel-wd-step__when')?.textContent).toBe('Paused');
    expect(steps.map((step) => step.querySelector('.kel-wd-step__when')?.textContent)).not.toContain('Next');
    expect(screen.getByTestId('kel-office-detail').textContent).toContain('Paused at step 3 of 5');
  });

  it("uses the engine's own paused step when it sends one (VIS-6)", async () => {
    renderDetail({
      ...MIC_DETAIL,
      steps: MIC_DETAIL.steps?.map((step) => (step.id === 'm4' ? { ...step, state: 'paused' } : step)) ?? null,
    });
    const steps = await screen.findAllByTestId('kel-office-step');
    expect(steps[3].className).toContain('kel-wd-step--paused');
  });

  it("shows Kel's standard plan instead of an unreported model (LIVE-10)", async () => {
    renderDetail({
      ...RECEIPTS_DETAIL,
      staff: [
        { id: 'kel', role: 'kel', role_label: 'Kel', state: 'done', model: null, model_confirmed: false, note: 'Kel used its standard coding plan.' },
        ...(RECEIPTS_DETAIL.staff ?? []).slice(1),
      ],
    });
    const models = await screen.findAllByTestId('kel-office-model');
    expect(models[0].textContent).toBe('Planned with Kel’s standard plan');
    expect(screen.getByTestId('kel-office-detail').textContent).not.toContain('Model not reported yet');
    expect(screen.getByTestId('kel-office-detail').textContent).not.toContain('Kel used its standard coding plan.');
  });

  it("uses the engine's own words when it sends them: paused, standard plan", async () => {
    renderDetail({
      ...MIC_DETAIL,
      paused: true,
      staff: [{ id: 'kel', role: 'kel', role_label: 'Kel', state: 'done', model: null, standard_plan: true, note: 'Kel used its standard coding plan.' }],
    });
    const steps = await screen.findAllByTestId('kel-office-step');
    expect(steps[2].querySelector('.kel-wd-step__when')?.textContent).toBe('Paused');
    expect(screen.getAllByTestId('kel-office-model')[0].textContent).toBe('Planned with Kel’s standard plan');
  });

  it('D-79: an open finding is one line — what it is and who is on it', async () => {
    renderDetail({
      ...MIC_DETAIL,
      state: 'in_review',
      review: { verdict: null, findings: [] },
      staff: [{ id: 'b1', role: 'builder', role_label: 'Builder', state: 'working', model_label: 'Claude Opus 5.5' }],
      sentinel: { state: 'done', findings: [{ severity: 'blocker', summary: 'A password stored in plain text', status: 'open' }] },
    } as OfficeItemDetail);
    expect((await screen.findByTestId('kel-office-review-state')).textContent).toBe('In progress');
    expect(screen.getByTestId('kel-office-review-problem').textContent).toBe('Sentinel found a password stored in plain text · Builder is fixing it');
  });

  it('labels an uncertain verdict "Never ran", not "Didn’t pass" (LIVE-10)', async () => {
    renderDetail({ ...RECEIPTS_DETAIL, state: 'failed', review: { verdict: 'uncertain', findings: [] }, verification: { result: 'not_confirmed', summary: [] } });
    const dialog = await screen.findByTestId('kel-office-detail');
    await within(dialog).findByTestId('kel-office-review');
    expect(within(dialog).getByTestId('kel-office-detail-state').textContent).toBe('Never ran');
    expect(within(dialog).getByTestId('kel-office-review-state').textContent).toBe('Never ran');
    expect(dialog.textContent).not.toContain('Didn’t pass');
    // A caution, not a failure: the uncertain tone replaces the red failed one.
    expect(dialog.className).toContain('is-uncertain');
  });

  it('shows commands without backticks and the place only once (LIVE-10)', async () => {
    renderDetail({
      ...RECEIPTS_DETAIL,
      result:
        'Applied to C:\\Users\\Nick\\Calc: changed calc.py (1 file).\n\nHow it was checked: `python -m pytest -q` passed in a separate copy of the project.\n\nThe earlier files are saved — Undo on the result card puts them back.',
      application: { state: 'APPLIED', auto: true, root: 'C:\\Users\\Nick\\Calc', files: 1, waiting_reason: null, project_name: 'Calc demo', folder: 'Calc' },
    });
    const result = await screen.findByTestId('kel-office-result');
    expect(result.textContent).toContain('python -m pytest -q');
    expect(result.textContent).not.toContain('`');
    expect(result.textContent).not.toContain('C:\\Users\\Nick\\Calc:');
    expect(result.textContent).toContain('Changed calc.py (1 file).');
  });

  it('after Undo the card says the earlier files are back, not "Applied to" (LIVE-12)', async () => {
    renderDetail({
      ...RECEIPTS_DETAIL,
      result:
        'Applied to C:\\Users\\Nick\\Calc: changed calc.py (1 file).\n\nThe earlier files are saved — Undo on the result card puts them back.',
      application: { state: 'UNDONE', auto: true, root: 'C:\\Users\\Nick\\Calc', files: 1, waiting_reason: null },
    });
    const result = await screen.findByTestId('kel-office-result');
    expect(result.textContent).toContain('Undone — the earlier files are back.');
    expect(result.textContent).not.toMatch(/Applied to|Undo on the result card/);
    expect(screen.queryByTestId('kel-office-undo')).toBeNull();
  });
});

describe('D-79: no Files changed section and no change report in the panel', () => {
  it('shows no files, no report and no footer text', async () => {
    renderDetail({ ...RECEIPTS_DETAIL, kind: 'code', files_changed: ['calc.py'], steps: [{ id: 'm1', label: 'The change', state: 'done', at: AT(9, 40) }] });
    const dialog = await screen.findByTestId('kel-office-detail');
    await within(dialog).findAllByTestId('kel-office-step');
    expect(screen.queryByTestId('kel-office-report')).toBeNull();
    expect(dialog.textContent).not.toMatch(/Files changed|calc\.py|Finished work stays at the top/);
    expect(reportFileName('Add power() to calc!')).toBe('add-power-to-calc-change-report.md');
  });
});

/* ─── Done card and in-thread line ─────────────────────────────────────────────────────────── */

describe('the in-thread pieces', () => {
  it('an uncertain done card says "Never ran" and shows commands without backticks', async () => {
    details = {
      [RECEIPTS.job_id]: {
        ...RECEIPTS_DETAIL,
        state: 'failed',
        verification: { result: 'not_confirmed', summary: [] },
        review: { verdict: 'uncertain' },
        result: 'Ran `python -m pytest -q` but the review could not finish.',
      },
    };
    install();
    render(<KelDoneCard job={RECEIPTS.job_id} />);
    expect((await screen.findByTestId('kel-done-card-state')).textContent).toBe('Never ran');
    expect(screen.getByTestId('kel-done-card').textContent).not.toContain('`');
  });

  it('the line says "Never ran" for an uncertain verdict', () => {
    render(
      <KelWorkLine view={{ job_id: 'job-1', title: 'Add power()', phase: 'done', verdict: 'UNCERTAIN', accepted: 1, total: 1 } as never} />
    );
    expect(screen.getByTestId('kel-work-line-state').textContent).toBe('Never ran');
  });
});

/* ─── LIVE-7 and Vetting on the scoping card ───────────────────────────────────────────────── */

describe('the Scoping card takes you to its questions (LIVE-7)', () => {
  it('scrolls to and highlights the questions instead of opening "Talk to Kel"', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    chatProject = { project: { id: 'calc', name: 'Calc demo' }, pending: false };
    projectItems = {
      calc: [{ job_id: 'scope-1', scoping_id: 'scope-1', title: 'Contact form', state: 'scoping', questions: 3, conversation_id: 'engine-calc' }],
    };
    install();
    const scroll = vi.fn();
    renderChat(
      '/conversation/app-calc',
      <section data-scoping-card='scope-1' ref={(node) => node && (node.scrollIntoView = scroll)}>
        <button type='button'>A new web address</button>
      </section>
    );
    fireEvent.click(await screen.findByRole('button', { name: /^Contact form,/ }));
    await waitFor(() => expect(scroll).toHaveBeenCalled());
    const card = document.querySelector('[data-scoping-card="scope-1"]') as HTMLElement;
    expect(card.classList.contains('is-highlighted')).toBe(true);
    expect(document.activeElement?.textContent).toBe('A new web address');
    expect(screen.queryByTestId('kel-office-detail')).toBeNull();
    expect(screen.getByTestId('route').textContent).toBe('app-calc');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(card.classList.contains('is-highlighted')).toBe(false);
  });

  it('waits a moment for questions still arriving, then shows them', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const scroll = vi.fn();
    revealScopingQuestions('late', 10, 50);
    const late = document.createElement('section');
    late.setAttribute('data-scoping-card', 'late');
    late.scrollIntoView = scroll;
    document.body.appendChild(late);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(120);
    });
    expect(scroll).toHaveBeenCalled();
    late.remove();
  });

  it('opens the chat the questions were asked in', async () => {
    chatProject = { project: { id: 'calc', name: 'Calc demo' }, pending: false };
    projectItems = {
      calc: [{ job_id: 'scope-2', scoping_id: 'scope-2', title: 'Signup page', state: 'scoping', questions: 2, conversation_id: 'engine-other' }],
    };
    install();
    renderChat();
    fireEvent.click(await screen.findByRole('button', { name: /^Signup page,/ }));
    await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('app-other'));
  });
});

describe('Vetting is reachable from the scoping card', () => {
  it('puts the vetting start in the composer', async () => {
    extra = (route) =>
      route.startsWith('/api/scoping?id=')
        ? {
            id: 'scope-1',
            title: 'Contact form',
            state: 'open',
            conversation_id: 'engine-calc',
            questions: [{ id: 'q1', question: 'Where?', options: [{ code: 'a', label: 'Here' }] }],
            summary: 'I’ll build: a contact form.',
          }
        : undefined;
    install();
    const fill = vi.fn();
    emitter.on('sendbox.fill', fill);
    try {
      render(<KelScopingCard scopingId='scope-1' conversationId='app-calc' />);
      fireEvent.click(await screen.findByTestId('kel-scoping-vetting'));
      expect(fill).toHaveBeenCalledWith('start design vetting: Contact form');
    } finally {
      emitter.off('sendbox.fill', fill);
    }
    expect(vettingPrompt('')).toBe('start design vetting: this work');
  });
});
