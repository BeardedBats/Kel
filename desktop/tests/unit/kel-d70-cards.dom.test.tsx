/**
 * D-70 items 1, 2 and 4 (Figma "Office — D-66 explorations", row 5), as behaviour:
 * 5a/5b answering "Needs you" inside the card, 5c/5d the one live view in the thread (the slim line
 * and the done card), 5e/5f the scoping card and the "Scoping" top card. Engine calls are faked at
 * the `kelAPI.request` seam; every answer is checked for the route it takes.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { KelWorkCard } from '@renderer/components/kel/KelWorkCard';
import { KelDoneCard, checksLine, resultSentence } from '@renderer/components/kel/workCards/KelDoneCard';
import { KelScopingCard } from '@renderer/components/kel/workCards/KelScopingCard';
import { KelMessageCard } from '@renderer/components/kel/workCards/KelMessageCard';
import { OPEN_WORK_CARD_EVENT, refreshWorkCards, takePendingWorkCard } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import type { OfficeItem, OfficeItemDetail, ScopingView } from '@renderer/components/kel/workCards/officeApi';
import { AT, LAPTOP, MIC, MIC_DETAIL, RECEIPTS, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

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
    if (route.startsWith('/api/handoff')) return { application: null };
    return { ok: true };
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request,
    conversation: vi.fn(async (id: string) => (id === 'app-morning' ? 'engine-morning' : id)),
    openEngineConversation: vi.fn(async (cid: string) => `app-${cid.replace('engine-', '')}`),
  };
  return request;
};

const Chat: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { id } = useParams();
  return (
    <div>
      <KelWorkCardRow conversationId={id} availableWidth={920} pollActiveMs={40} pollIdleMs={80} openFolder={async () => undefined} />
      <div className='sendbox-panel'>
        <textarea aria-label='Message Kel' />
      </div>
      {children}
    </div>
  );
};

const renderChat = (children?: React.ReactNode) =>
  render(
    <MemoryRouter initialEntries={['/conversation/app-morning']}>
      <Routes>
        <Route path='/conversation/:id' element={<Chat>{children}</Chat>} />
      </Routes>
    </MemoryRouter>
  );

const posts = (request: ReturnType<typeof install>, route: string) =>
  request.mock.calls.filter(([called, body]) => called === route && body !== undefined).map(([, body]) => body);

beforeEach(() => {
  list = [];
  details = {};
  extra = null;
  resetProjectsForTests();
  takePendingWorkCard(); // no card request carries over from another test
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

/* ─── 5a / 5b ─────────────────────────────────────────────────────────────────────────────── */

const LAPTOP_DETAIL: OfficeItemDetail = {
  ...LAPTOP,
  team: undefined,
  staff: [],
  steps: [],
  question: {
    kind: 'clarification',
    wait: 'Waiting for your answer',
    text: 'What’s your budget? The shortlist changes a lot above $1,500.',
    options: [
      { id: 'a', label: 'Under $1,000' },
      { id: 'b', label: '$1,000–1,500' },
      { id: 'c', label: 'No limit' },
    ],
    answer_box: true,
    conversation_id: 'engine-laptop',
    job_id: 'job-laptop',
    ref: { job: 'job-laptop' },
  },
};

const openLaptop = async () => {
  fireEvent.click(await screen.findByRole('button', { name: /Laptop research/ }));
  return screen.findByTestId('kel-needs-question');
};

describe('5a — Kel is asking you, inside the card', () => {
  it('shows the question, quick picks, an answer box and who the answer goes to', async () => {
    list = [LAPTOP];
    details = { [LAPTOP.job_id]: LAPTOP_DETAIL };
    install();
    renderChat();
    const block = await openLaptop();
    expect(within(block).getByText('Kel is asking you')).toBeTruthy();
    expect(block.querySelector('.kel-na__meta')?.textContent).toBe('·  This work is paused until you answer');
    expect(within(block).getByTestId('kel-needs-question-text').textContent).toBe(LAPTOP_DETAIL.question!.text);
    expect(within(block).getAllByTestId('kel-chip').map((chip) => chip.textContent)).toEqual([
      'Under $1,000',
      '$1,000–1,500',
      'No limit',
    ]);
    expect(within(block).getByPlaceholderText('Or type your answer…')).toBeTruthy();
    expect(within(block).getByText('Your answer goes to Kel, not to an agent. Kel will pass it on and continue.')).toBeTruthy();
  });

  it('a quick pick goes to Kel as a message in that work’s conversation, then 5b says so', async () => {
    list = [LAPTOP];
    details = { [LAPTOP.job_id]: LAPTOP_DETAIL };
    const request = install();
    renderChat();
    const block = await openLaptop();
    fireEvent.click(within(block).getByRole('radio', { name: '$1,000–1,500' }));
    const answered = await screen.findByTestId('kel-needs-answered');
    expect(answered.textContent).toContain('You answered: $1,000–1,500');
    expect(answered.textContent).toContain('Kel is continuing');
    expect(posts(request, '/api/send')).toEqual([{ conversation: 'engine-laptop', text: '$1,000–1,500' }]);
    expect(screen.queryByTestId('kel-needs-question')).toBeNull();
  });

  it('a typed answer is a normal message too (the D-55 restart rule applies to it)', async () => {
    list = [LAPTOP];
    details = { [LAPTOP.job_id]: LAPTOP_DETAIL };
    const request = install();
    renderChat();
    const block = await openLaptop();
    const input = within(block).getByPlaceholderText('Or type your answer…');
    expect((within(block).getByTestId('kel-answer-send') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(input, { target: { value: 'About $1,200, and it must be light' } });
    fireEvent.click(within(block).getByTestId('kel-answer-send'));
    await screen.findByTestId('kel-needs-answered');
    expect(posts(request, '/api/send')).toEqual([{ conversation: 'engine-laptop', text: 'About $1,200, and it must be light' }]);
  });

  it('an approval wait uses the approval’s own approve/deny route', async () => {
    list = [LAPTOP];
    details = {
      [LAPTOP.job_id]: {
        ...LAPTOP_DETAIL,
        question: {
          kind: 'approval',
          text: 'Kel needs your OK to continue?',
          options: [
            { id: 'allow', label: 'Allow' },
            { id: 'deny', label: 'Don’t allow' },
          ],
          conversation_id: 'engine-laptop',
          ref: { approval_kind: 'action', approval_id: 'ap-1' },
        },
      },
    };
    const request = install();
    renderChat();
    const block = await openLaptop();
    fireEvent.click(within(block).getByRole('radio', { name: 'Don’t allow' }));
    expect((await screen.findByTestId('kel-needs-answered')).textContent).toContain('Kel won’t take that step');
    expect(posts(request, '/api/approvals')).toEqual([
      { action: 'resolve', kind: 'action', id: 'ap-1', allow: false, conversation: 'engine-laptop' },
    ]);
    expect(posts(request, '/api/send')).toEqual([]);
  });

  it('an Oracle blocker offers Apply anyway / Leave it on the apply route', async () => {
    list = [{ ...LAPTOP, kind: 'code' }];
    details = {
      [LAPTOP.job_id]: {
        ...LAPTOP_DETAIL,
        kind: 'code',
        question: {
          kind: 'second_opinion',
          text: 'An independent second opinion raised a problem. Apply the change anyway?',
          detail: 'An independent second opinion found a problem: Any password is accepted.',
          options: [
            { id: 'apply_anyway', label: 'Apply anyway' },
            { id: 'leave', label: 'Leave it' },
          ],
          conversation_id: 'engine-laptop',
          ref: { job: 'job-laptop' },
        },
      },
    };
    const request = install();
    renderChat();
    const block = await openLaptop();
    expect(within(block).getByText(/Any password is accepted/)).toBeTruthy();
    fireEvent.click(within(block).getByRole('radio', { name: 'Leave it' }));
    expect((await screen.findByTestId('kel-needs-answered')).textContent).toContain('Kel left it as it is');
    expect(posts(request, '/api/apply')).toEqual([{ job: 'job-laptop', action: 'leave' }]);
  });

  it('a refused answer says why and keeps the question', async () => {
    list = [LAPTOP];
    details = { [LAPTOP.job_id]: LAPTOP_DETAIL };
    install();
    extra = (route, body) => (route === '/api/send' && body ? new Error('That message is not part of this conversation') : undefined);
    renderChat();
    const block = await openLaptop();
    fireEvent.click(within(block).getByRole('radio', { name: 'No limit' }));
    expect((await within(block).findByRole('alert')).textContent).toBe('That message is not part of this conversation');
    expect(screen.queryByTestId('kel-needs-answered')).toBeNull();
  });
});

/* ─── 5c / 5d ─────────────────────────────────────────────────────────────────────────────── */

const handoff = (over: Record<string, unknown> = {}) => ({
  submission_id: 'sub-mic',
  conversation: 'engine-morning',
  submission_state: 'DISPATCHED',
  title: 'Mic mute toggle app',
  ack_seq: 4,
  job_id: 'job-mic',
  state: 'RUNNING',
  verdict: null,
  accepted: 2,
  total: 5,
  why: null,
  next: null,
  error: null,
  phase: 'running',
  can_stop: true,
  can_retry: false,
  staffed: true,
  office_state: 'working',
  ...over,
});

describe('5c — one live view in the thread', () => {
  it('is one line naming the top card’s state, and opens that card’s panel', async () => {
    list = [MIC];
    details = { [MIC.job_id]: MIC_DETAIL };
    install();
    extra = (route) => (route.startsWith('/api/handoff') ? handoff() : undefined);
    renderChat(<KelWorkCard submissionId='sub-mic' conversationId='app-morning' pollMs={30} />);
    const line = await screen.findByTestId('kel-work-line');
    expect(line.textContent).toBe('Handed to the team·Mic mute toggle appWorking · 2 of 5— follow it above');
    expect(screen.queryByTestId('kel-work-card')).toBeNull();
    expect(screen.queryByTestId('kel-office-detail')).toBeNull();
    fireEvent.click(line);
    expect(await screen.findByTestId('kel-office-detail')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Mic mute toggle app' })).toBeTruthy();
  });

  it('finished work points down to the result; failed, stopped and needs-you use the same line', async () => {
    install();
    const states: Array<[Record<string, unknown>, string, string]> = [
      [{ phase: 'done', state: 'CLOSED', verdict: 'VERIFIED', office_state: 'done', accepted: 5 }, 'Done and checked', '— result below'],
      [{ phase: 'needs_look', state: 'CLOSED', verdict: 'FAILED', office_state: 'failed' }, 'Didn’t pass its checks', '— result below'],
      [{ phase: 'stopped', state: 'CANCELLED', office_state: 'stopped' }, 'Stopped', '— see it above'],
      [{ phase: 'needs_you', office_state: 'needs_you' }, 'Needs you', '— follow it above'],
    ];
    for (const [index, [over, words, pointer]] of states.entries()) {
      extra = (route) => (route.startsWith('/api/handoff') ? handoff(over) : undefined);
      // A separate hand-off each time: a re-mounted card starts from what it last showed (FIX-0025).
      const view = render(
        <MemoryRouter>
          <KelWorkCard submissionId={`sub-mic-${index}`} conversationId='app-morning' pollMs={30} />
        </MemoryRouter>
      );
      const state = await view.findByTestId('kel-work-line-state');
      expect(state.textContent).toBe(words);
      expect(view.getByTestId('kel-work-line').textContent).toContain(pointer);
      view.unmount();
    }
  });

  it('a card the thread re-renders comes back as it was — no "Getting started…" flash (FIX-0025)', async () => {
    install();
    extra = (route) => (route.startsWith('/api/handoff') ? handoff({ phase: 'done', state: 'CLOSED', verdict: 'VERIFIED', office_state: 'done', accepted: 5 }) : undefined);
    const first = render(
      <MemoryRouter>
        <KelWorkCard submissionId='sub-remount' conversationId='app-morning' pollMs={30} />
      </MemoryRouter>
    );
    expect((await first.findByTestId('kel-work-line-state')).textContent).toBe('Done and checked');
    first.unmount();
    extra = (route) => (route.startsWith('/api/handoff') ? new Promise(() => undefined) : undefined);
    const again = render(
      <MemoryRouter>
        <KelWorkCard submissionId='sub-remount' conversationId='app-morning' pollMs={30} />
      </MemoryRouter>
    );
    expect(again.getByTestId('kel-work-line-state').textContent).toBe('Done and checked');
    expect(again.queryByText('Getting started…')).toBeNull();
  });

  it('old work without a card keeps today’s work card', async () => {
    install();
    extra = (route) => (route.startsWith('/api/handoff') ? handoff({ staffed: undefined, office_state: undefined }) : undefined);
    render(
      <MemoryRouter>
        <KelWorkCard submissionId='sub-mic' conversationId='app-morning' pollMs={30} />
      </MemoryRouter>
    );
    expect(await screen.findByTestId('kel-work-card')).toBeTruthy();
    expect(screen.queryByTestId('kel-work-line')).toBeNull();
  });
});

const DONE_DETAIL: OfficeItemDetail = {
  ...RECEIPTS_DETAIL,
  job_id: 'job-mic',
  title: 'Mic mute toggle app',
  kind: 'code',
  finished_at: AT(10, 31),
  result:
    "Here's your mic mute toggle app — it passed its checks.\n\nA tray app that mutes your mic with one hotkey and shows the state, even when you mute from Windows settings. It also remembers the hotkey.",
  application: { state: 'APPLIED', auto: true, root: 'Projects › mic-mute', files: 4, waiting_reason: null },
};
const RESULT_META = {
  kind: 'result',
  verdict: 'VERIFIED',
  job: 'job-mic',
  checks: [
    { kind: 'min_chars', verdict: 'PASSED' },
    { kind: 'repository_evidence', verdict: 'PASSED' },
    { kind: 'tests', verdict: 'PASSED' },
    { kind: 'manual_review', verdict: 'VERIFIED' },
  ],
};

describe('5d — the result carries the compact done card', () => {
  it('D-79: title, "Complete" (its when in the tooltip), checks, one sentence, where it was applied, Open / Details, no Undo', async () => {
    details = { 'job-mic': DONE_DETAIL };
    const request = install();
    const opened: string[] = [];
    const listen = (event: Event) => opened.push((event as CustomEvent<{ job: string }>).detail.job);
    window.addEventListener(OPEN_WORK_CARD_EVENT, listen);
    const openFolder = vi.fn(async () => undefined);
    render(<KelDoneCard job='job-mic' meta={RESULT_META} openFolder={openFolder} />);
    const card = await screen.findByTestId('kel-done-card');
    expect(within(card).getByText('Mic mute toggle app')).toBeTruthy();
    expect(within(card).getByTestId('kel-done-card-state').textContent).toBe('Complete');
    expect(card.querySelector('.kel-dc__state-word')?.getAttribute('title')).toMatch(/^\d{2}\/\d{2}\/\d{2} \d{2}:\d{2} (AM|PM)$/);
    expect(within(card).getByText('4 of 4 checks passed')).toBeTruthy();
    expect(
      within(card).getByText('A tray app that mutes your mic with one hotkey and shows the state, even when you mute from Windows settings.')
    ).toBeTruthy();
    expect(within(card).getByTestId('kel-done-card-applied').textContent).toMatch(/^Applied to Projects › mic-mute at 10:31 AM · you can undo it$/);
    expect(within(card).queryByTestId('kel-done-card-undo')).toBeNull();
    const open = within(card).getByTestId('kel-done-card-folder');
    expect(open.textContent).toBe('Open');
    expect(open.getAttribute('aria-label')).toBe('Open the project folder');
    fireEvent.click(open);
    await waitFor(() => expect(openFolder).toHaveBeenCalledWith('Projects › mic-mute'));
    fireEvent.click(within(card).getByTestId('kel-done-card-details'));
    expect(opened).toEqual(['job-mic']);
    // Nick asked Kel to undo it: the card reads the engine again and says the files are back.
    details = { 'job-mic': { ...DONE_DETAIL, application: { ...DONE_DETAIL.application!, state: 'UNDONE' } } };
    act(() => refreshWorkCards());
    await waitFor(() => expect(within(card).getByTestId('kel-done-card-applied').textContent).toBe('Undone — the earlier files are back.'));
    expect(posts(request, '/api/apply')).toEqual([]);
    window.removeEventListener(OPEN_WORK_CARD_EVENT, listen);
  });

  it('only a passed result says "checked"; a failed one says it did not pass', async () => {
    details = { 'job-mic': { ...DONE_DETAIL, state: 'failed', review: { verdict: 'failed' }, verification: { result: 'failed' }, application: null } };
    install();
    render(<KelDoneCard job='job-mic' meta={{ ...RESULT_META, verdict: 'FAILED', checks: [{ kind: 'tests', verdict: 'FAILED' }] }} />);
    const card = await screen.findByTestId('kel-done-card');
    expect(within(card).getByTestId('kel-done-card-state').textContent).toBe('Didn’t pass its checks');
    expect(within(card).getByText('0 of 1 check passed')).toBeTruthy();
    expect(within(card).queryByTestId('kel-done-card-undo')).toBeNull();
  });

  it('a result from work without a card keeps today’s details', async () => {
    install();
    render(<KelMessageCard meta={{ ...RESULT_META, job: 'job-old', summary: ['Verified'] }} />);
    expect(await screen.findByTestId('kel-message-details')).toBeTruthy();
    expect(screen.queryByTestId('kel-done-card')).toBeNull();
  });

  it('pure helpers: the checks line and the one sentence', () => {
    expect(checksLine({ checks: [] })).toBeNull();
    expect(resultSentence("Here's your plan — it passed its checks.")).toBeNull();
    expect(resultSentence('First sentence. Second one.')).toBe('First sentence.');
  });
});

/* ─── 5e / 5f ─────────────────────────────────────────────────────────────────────────────── */

const SCOPING: ScopingView = {
  id: 'scope-1',
  title: 'Plumbing website',
  state: 'open',
  conversation_id: 'engine-morning',
  questions: [
    { id: 'Q1', question: 'Where should it live?', options: [{ code: 'A', label: 'A new web address' }, { code: 'B', label: 'His existing site' }, { code: 'C', label: 'A preview link for now' }], best: 'A' },
    { id: 'Q2', question: 'How should bookings reach him?', options: [{ code: 'A', label: 'Email' }, { code: 'B', label: 'Text message' }, { code: 'C', label: 'Google Calendar' }], best: 'A' },
    { id: 'Q3', question: 'Which look?', options: [{ code: 'A', label: 'Clean and simple' }, { code: 'B', label: 'Bold, trade-style' }, { code: 'C', label: 'Match his van logo' }], best: 'A' },
  ],
  summary: 'I’ll build: a 4-page site (home, services and prices, reviews, book a visit) with a booking form.',
};

describe('5e — scoping before big work', () => {
  it('asks its questions with quick picks and "Something else…"; nothing starts until Start', async () => {
    const request = install();
    extra = (route, body) => {
      if (route.startsWith('/api/scoping?id=scope-1')) return SCOPING;
      if (route === '/api/scoping' && body)
        return { ...SCOPING, state: 'started', started_at: AT(10, 4), answer_line: 'A new web address · Email · Match his van logo' };
      return undefined;
    };
    render(<KelScopingCard scopingId='scope-1' conversationId='app-morning' />);
    const card = await screen.findByTestId('kel-scoping-card');
    expect(within(card).getByRole('heading').textContent).toBe('Before I start · 3 quick questions');
    expect(within(card).getByText('Scoping')).toBeTruthy();
    expect(within(card).getAllByTestId('kel-scoping-question').map((q) => q.querySelector('p')?.textContent)).toEqual([
      'Where should it live?',
      'How should bookings reach him?',
      'Which look?',
    ]);
    expect(within(card).getAllByTestId('kel-chip-other')).toHaveLength(3);
    expect(within(card).getByTestId('kel-scoping-summary').textContent).toMatch(/^I’ll build: /);
    expect(within(card).getByText('Nothing starts until you choose.')).toBeTruthy();
    expect(posts(request, '/api/scoping')).toEqual([]);

    const [first, second, third] = within(card).getAllByTestId('kel-scoping-question');
    fireEvent.click(within(first).getByRole('radio', { name: 'A new web address' }));
    expect(within(first).getByRole('radio', { name: 'A new web address' }).getAttribute('aria-checked')).toBe('true');
    fireEvent.click(within(second).getByTestId('kel-chip-other'));
    fireEvent.change(within(second).getByTestId('kel-answer-input'), { target: { value: 'Email and a text' } });
    fireEvent.click(within(third).getByRole('radio', { name: 'Match his van logo' }));
    fireEvent.click(within(card).getByTestId('kel-scoping-start'));
    const collapsed = await screen.findByTestId('kel-scoping-collapsed');
    expect(posts(request, '/api/scoping')).toEqual([
      { action: 'start', id: 'scope-1', answers: { Q1: { option: 'A' }, Q2: { text: 'Email and a text' }, Q3: { option: 'C' } }, conversation: 'engine-morning' },
    ]);
    // 5f: the card collapses to one line.
    expect(collapsed.textContent).toBe('ScopedA new web address · Email · Match his van logoStarted 10:04 AM');
    expect(request).toHaveBeenCalledWith('/api/scoping?id=scope-1&conversation=engine-morning', undefined);
  });

  it('"Just start with your best guess" starts at once', async () => {
    const request = install();
    extra = (route, body) => {
      if (route.startsWith('/api/scoping?id=')) return SCOPING;
      if (route === '/api/scoping' && body) return { ...SCOPING, state: 'best_guess', started_at: AT(10, 5), answer_line: 'A new web address · Email · Clean and simple' };
      return undefined;
    };
    render(<KelScopingCard scopingId='scope-1' conversationId='app-morning' />);
    fireEvent.click(await screen.findByTestId('kel-scoping-best-guess'));
    expect((await screen.findByTestId('kel-scoping-collapsed')).textContent).toContain('Scoped · best guess');
    expect(posts(request, '/api/scoping')).toEqual([{ action: 'best_guess', id: 'scope-1', conversation: 'engine-morning' }]);
  });

  it('the top card shows "Scoping" with its colour, a chat icon, no bar and "N questions"', async () => {
    list = [
      { job_id: 'scope-1', scoping_id: 'scope-1', title: 'Plumbing website', state: 'scoping', questions: 3, progress: null, team: [], conversation_id: 'engine-morning', order: 0 },
      { ...MIC, order: 1 },
    ];
    details = { [MIC.job_id]: MIC_DETAIL };
    install();
    extra = (route) => (route.startsWith('/api/scoping?id=') ? SCOPING : undefined);
    renderChat(<KelScopingCard scopingId='scope-1' conversationId='app-morning' />);
    const card = (await screen.findAllByTestId('kel-office-card'))[0];
    expect(card.getAttribute('data-state')).toBe('scoping');
    expect(card.className).toContain('kel-wc--scoping');
    expect(within(card).getByTestId('kel-office-card-state').textContent).toBe('Scoping');
    expect(within(card).getByText('3 questions')).toBeTruthy();
    expect(card.querySelector('.kel-wc-progress__fill')).toBeNull();
    expect(card.querySelector('.kel-wc-agents')).toBeNull();
    // Clicking it goes to the questions in the thread, never to a detail panel.
    const scroll = vi.fn();
    const thread = await screen.findByTestId('kel-scoping-card');
    thread.scrollIntoView = scroll;
    fireEvent.click(within(card).getByRole('button', { name: /^Plumbing website,/ }));
    expect(scroll).toHaveBeenCalled();
    expect(screen.queryByTestId('kel-office-detail')).toBeNull();
  });
});

describe('one live view — Needs you defers to the card', () => {
  it('a card asked for before the row appears opens when it does', async () => {
    list = [RECEIPTS];
    details = { [RECEIPTS.job_id]: RECEIPTS_DETAIL };
    install();
    const { openWorkCard } = await import('@renderer/components/kel/workCards/workCardEvents');
    act(() => openWorkCard(RECEIPTS.job_id));
    renderChat();
    expect(await screen.findByTestId('kel-office-detail')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Receipts tidy-up' })).toBeTruthy();
  });
});

describe('the chat keeps the engine’s message details', () => {
  it('normalising a stored text message keeps kel_meta (the done and scoping cards read it)', async () => {
    const { normalizeTextMessageContent } = await import('@/common/chat/chatLib');
    const meta = { kind: 'result', verdict: 'VERIFIED', job: 'job-mic' };
    expect(normalizeTextMessageContent({ content: 'Here it is', kel_meta: meta }).kel_meta).toEqual(meta);
    expect(normalizeTextMessageContent(JSON.stringify({ content: 'x', kel_meta: { kind: 'scoping', scoping: 's-1' } })).kel_meta).toEqual({
      kind: 'scoping',
      scoping: 's-1',
    });
    expect(normalizeTextMessageContent({ content: 'plain' }).kel_meta).toBeUndefined();
  });
});
