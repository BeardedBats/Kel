/**
 * LIVE-1 — under "Ask first" (D-64's switch) a checked coding change waits for Nick, and every place
 * that shows the work offers to apply it: the top card is "Needs you" and its panel asks
 * "Apply" / "Leave it", the result's done card in the thread has the same two buttons, a card from
 * before the work cards has them too, and the Home "Needs you" box lists it. Every answer takes the
 * existing apply route with Nick as the actor (`/api/apply`, action `apply_anyway` / `leave`).
 * Engine calls are faked at the `kelAPI.request` seam.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { KelWorkCard } from '@renderer/components/kel/KelWorkCard';
import { KelDoneCard } from '@renderer/components/kel/workCards/KelDoneCard';
import { takePendingWorkCard } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { applicationLine } from '@renderer/components/kel/changeApplication';
import { buildResumptionBrief } from '@renderer/components/kel/resumptionBrief';
import { workWords } from '@renderer/components/kel/workLanguage';
import type { KelChangeApplication, KelWorkJob } from '@renderer/components/kel/kelApi';
import type { OfficeItem, OfficeItemDetail, OfficeQuestion } from '@renderer/components/kel/workCards/officeApi';
import { AT } from './fixtures/kelOfficeFixtures';

type Handler = (route: string, body?: unknown) => unknown;

let list: OfficeItem[] = [];
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
    if (route.startsWith('/api/office?project=')) return { generated: 1, project: '*', items: list };
    if (route.startsWith('/api/office/item?job=')) {
      const job = decodeURIComponent(route.split('=')[1]);
      if (details[job]) return details[job];
      throw new Error('That work has no live team to show.');
    }
    return { ok: true };
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request,
    conversation: vi.fn(async (id: string) => (id === 'app-calc' ? 'engine-calc' : id)),
    openEngineConversation: vi.fn(async (cid: string) => `app-${cid.replace('engine-', '')}`),
  };
  return request;
};

const posts = (request: ReturnType<typeof install>, route: string) =>
  request.mock.calls.filter(([called, body]) => called === route && body !== undefined).map(([, body]) => body);

const WAITING: KelChangeApplication = {
  state: null,
  auto: false,
  decision: 'waiting',
  root: null,
  files: null,
  waiting_reason: 'Ask first is on',
  ask_first: true,
};

const QUESTION: OfficeQuestion = {
  kind: 'apply',
  wait: 'Waiting for you to apply it',
  text: 'The change passed its checks. Apply it to Calc demo (folder R6Proj)?',
  detail: 'Ask first is on, so Kel waits for you before it changes your project. Kel checks for conflicts and saves a backup first, so you can undo it.',
  options: [
    { id: 'apply_anyway', label: 'Apply' },
    { id: 'leave', label: 'Leave it' },
  ],
  answer_box: true,
  conversation_id: 'engine-calc',
  job_id: 'job-calc',
  ref: { job: 'job-calc' },
};

const ITEM: OfficeItem = {
  job_id: 'job-calc',
  title: 'Add a power function',
  project_id: 'personal',
  conversation_id: 'engine-calc',
  kind: 'code',
  state: 'needs_you',
  finished: false,
  status_line: 'Checked and ready. Ask first is on, so it waits for you to apply it.',
  needs_you: true,
  progress: { done: 1, total: 1, label: 'Waiting for you' },
  team: [
    { role: 'kel', role_label: 'Kel', state: 'done' },
    { role: 'builder', role_label: 'Builder', state: 'done' },
    { role: 'verifier', role_label: 'Verifier', state: 'done' },
  ],
  started_at: AT(10, 1),
  updated_at: AT(10, 9),
};

const DETAIL: OfficeItemDetail = {
  ...ITEM,
  team: undefined,
  staff: [],
  steps: [],
  question: QUESTION,
  application: WAITING,
  verification: { result: 'passed', summary: [] },
  result:
    'The change passed its tests and a separate review. Ask first is on, so Kel has not changed Calc demo (folder R6Proj) yet. Choose Apply on its work card at the top of this chat to write it in, or Leave it.',
};

const APPLIED_DETAIL: OfficeItemDetail = {
  ...DETAIL,
  state: 'done',
  finished: true,
  needs_you: false,
  status_line: 'Checked, and applied at your request.',
  question: null,
  finished_at: AT(10, 12),
  application: { state: 'APPLIED', auto: false, decision: 'manual', root: 'C:\\Users\\Nick\\R6Proj', files: 2, waiting_reason: null, ask_first: false, project_name: 'Calc demo', folder: 'R6Proj' },
};

const Chat: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { id } = useParams();
  return (
    <div>
      <KelWorkCardRow conversationId={id} availableWidth={920} pollActiveMs={40} pollIdleMs={80} openFolder={async () => undefined} />
      {children}
    </div>
  );
};

const renderChat = () =>
  render(
    <MemoryRouter initialEntries={['/conversation/app-calc']}>
      <Routes>
        <Route path='/conversation/:id' element={<Chat />} />
      </Routes>
    </MemoryRouter>
  );

beforeEach(() => {
  list = [];
  details = {};
  extra = null;
  resetProjectsForTests();
  takePendingWorkCard();
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Ask first — the top card asks Apply / Leave it', () => {
  it('is an amber "Needs you" card whose panel asks to apply, and Apply takes the apply route', async () => {
    list = [ITEM];
    details = { 'job-calc': DETAIL };
    const request = install();
    renderChat();
    const card = await screen.findByTestId('kel-office-card');
    expect(card.getAttribute('data-state')).toBe('needs_you');
    expect(card.className).toContain('kel-wc--needs_you');
    expect(within(card).getByTestId('kel-office-card-state').textContent).toBe('Needs you');
    fireEvent.click(await screen.findByRole('button', { name: /Add a power function/ }));
    const block = await screen.findByTestId('kel-needs-question');
    expect(within(block).getByTestId('kel-needs-question-text').textContent).toBe(QUESTION.text);
    expect(within(block).getByText(/Ask first is on, so Kel waits for you/)).toBeTruthy();
    expect(within(block).getAllByTestId('kel-chip').map((chip) => chip.textContent)).toEqual(['Apply', 'Leave it']);
    fireEvent.click(within(block).getByRole('radio', { name: 'Apply' }));
    const answered = await screen.findByTestId('kel-needs-answered');
    expect(answered.textContent).toContain('You answered: Apply');
    expect(answered.textContent).toContain('Kel applied the change');
    expect(posts(request, '/api/apply')).toEqual([{ job: 'job-calc', action: 'apply_anyway' }]);
  });
});

describe('Ask first — the result card in the thread offers Apply too', () => {
  it('shows Needs you, where it would go, and Apply / Leave it; Apply writes it and the card turns into Undo', async () => {
    details = { 'job-calc': DETAIL };
    const request = install();
    extra = (route, body) => {
      if (route === '/api/apply' && body) {
        details = { 'job-calc': APPLIED_DETAIL };
        return { job_id: 'job-calc', choice: 'apply_anyway', already: false };
      }
      return undefined;
    };
    render(<KelDoneCard job='job-calc' meta={null} openFolder={async () => undefined} />);
    const card = await screen.findByTestId('kel-done-card');
    expect(card.getAttribute('data-state')).toBe('needs_you');
    expect(screen.getByTestId('kel-done-card-state').textContent).toBe('Needs you');
    expect(screen.getByTestId('kel-done-card-applied').textContent).toBe('Waiting for you to apply it — Ask first is on.');
    expect(screen.getByTestId('kel-done-card-answer-apply_anyway').textContent).toBe('Apply');
    expect(screen.getByTestId('kel-done-card-answer-leave').textContent).toBe('Leave it');
    expect(screen.queryByTestId('kel-done-card-undo')).toBeNull();
    fireEvent.click(screen.getByTestId('kel-done-card-answer-apply_anyway'));
    await waitFor(() => expect(screen.getByTestId('kel-done-card-state').textContent).toBe('Done and checked'));
    expect(posts(request, '/api/apply')).toEqual([{ job: 'job-calc', action: 'apply_anyway' }]);
    expect(screen.queryByTestId('kel-done-card-answer-apply_anyway')).toBeNull();
    expect(screen.getByTestId('kel-done-card-undo')).toBeTruthy();
    expect(screen.getByTestId('kel-done-card-applied').textContent).toContain('Applied to Calc demo (folder R6Proj)');
  });

  it('Leave it takes the same route and changes nothing else', async () => {
    details = { 'job-calc': DETAIL };
    const request = install();
    render(<KelDoneCard job='job-calc' meta={null} openFolder={async () => undefined} />);
    fireEvent.click(await screen.findByTestId('kel-done-card-answer-leave'));
    await waitFor(() => expect(posts(request, '/api/apply')).toEqual([{ job: 'job-calc', action: 'leave' }]));
  });

  it('finished, applied work shows no Apply', async () => {
    details = { 'job-calc': APPLIED_DETAIL };
    install();
    render(<KelDoneCard job='job-calc' meta={null} openFolder={async () => undefined} />);
    await screen.findByTestId('kel-done-card');
    expect(screen.queryByTestId('kel-done-card-answer-apply_anyway')).toBeNull();
  });
});

describe('Ask first — a card from before the work cards', () => {
  it('offers Apply / Leave it while the change waits', async () => {
    const request = install();
    extra = (route) =>
      route.startsWith('/api/handoff')
        ? {
            submission_id: 'sub-calc',
            conversation: 'engine-calc',
            submission_state: 'DISPATCHED',
            title: 'Add a power function',
            ack_seq: 2,
            job_id: 'job-calc',
            state: 'CLOSED',
            verdict: 'VERIFIED',
            accepted: 1,
            total: 1,
            why: 'Checked and ready. Ask first is on, so it waits for you to apply it.',
            next: 'Choose Apply on its card when you are ready, or Leave it.',
            error: null,
            phase: 'needs_you',
            can_stop: false,
            can_retry: false,
            application: WAITING,
          }
        : undefined;
    render(
      <MemoryRouter>
        <KelWorkCard submissionId='sub-calc' conversationId='app-calc' pollMs={30} />
      </MemoryRouter>
    );
    expect((await screen.findByTestId('kel-work-why')).textContent).toContain('Ask first is on');
    expect(screen.getByTestId('kel-work-apply').textContent).toBe('Apply');
    fireEvent.click(screen.getByTestId('kel-work-apply'));
    await waitFor(() => expect(posts(request, '/api/apply')).toEqual([{ job: 'job-calc', action: 'apply_anyway' }]));
  });
});

describe('Ask first — plain words and the Home "Needs you" box', () => {
  const job = (application: KelChangeApplication | null): KelWorkJob =>
    ({
      id: 'job-calc',
      state: 'CLOSED',
      verdict: 'VERIFIED',
      conversation: 'engine-calc',
      updated: 200,
      contract: { request: 'Add a power function', project_id: 'personal', staffing: { schema: 1 } },
      application,
    }) as KelWorkJob;

  it('names the wait without claiming it was applied', () => {
    expect(applicationLine(WAITING)).toBe('Waiting for you to apply it — Ask first is on.');
    expect(applicationLine({ ...WAITING, ask_first: false, waiting_reason: 'it would change your credentials folder' })).toBe(
      'Waiting for you: Kel did not apply it on its own — it would change your credentials folder.'
    );
    expect(workWords(job(WAITING))).toMatchObject({ label: 'Waiting for you to apply it', needsYou: true, section: 'waiting' });
    expect(workWords(job(null)).label).toBe('Done and checked');
  });

  it('lists the waiting change under Needs you, answered on its card', () => {
    const brief = buildResumptionBrief({ jobs: [job(WAITING)], now: 1_800_000_000_000 });
    expect(brief.quiet).toBe(false);
    expect(brief.summary).toBe('1 needs you');
    const [line] = brief.lines;
    expect(line.title).toBe('Add a power function');
    expect(line.detail).toContain('Waiting for you to apply it');
    expect(line.action).toMatchObject({ label: 'Answer on its card', card: 'job-calc' });
    expect(buildResumptionBrief({ jobs: [job({ ...WAITING, waiting_reason: null, ask_first: false })] }).quiet).toBe(true);
  });
});
