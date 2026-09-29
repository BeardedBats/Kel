/**
 * The renderer on the engine fields from the live audit (06ac92d: LIVE-3, LIVE-8, LIVE-10, LIVE-12,
 * FN-03, FN-06), as behaviour: the row card reads the list's `verdict` ("Never ran", not
 * "Failed") and `undone`; the detail uses the engine's own independence words, the Oracle's conclusion
 * and coverage, and marks an interrupted step; the new needs-you kinds answer "Try again" and open
 * Staff & models without sending anything; the Home brief says each `wait` plainly; Staff & models
 * offers per-role options, shows each role's purpose and which model is in effect; and "Not now"
 * cancels a scoping card. Engine calls are faked at `kelAPI.request`.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { KelOfficeCard } from '@renderer/components/kel/workCards/KelOfficeCard';
import { KelOfficeDetail } from '@renderer/components/kel/workCards/KelOfficeDetail';
import { KelDoneCard } from '@renderer/components/kel/workCards/KelDoneCard';
import { KelNeedsAnswer } from '@renderer/components/kel/workCards/KelNeedsAnswer';
import { KelScopingCard } from '@renderer/components/kel/workCards/KelScopingCard';
import { takePendingWorkCard } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { buildResumptionBrief } from '@renderer/components/kel/resumptionBrief';
import KelResumptionBrief from '@renderer/pages/guid/components/KelResumptionBrief';
import StaffModelsSettings from '@renderer/pages/settings/StaffModelsSettings';
import type { OfficeItem, OfficeItemDetail, OfficeQuestion } from '@renderer/components/kel/workCards/officeApi';
import type { KelWorkJob } from '@renderer/components/kel/kelApi';
import { AT, BACKUP, MIC, MIC_DETAIL, RECEIPTS, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key }) }));

type Handler = (route: string, body?: Record<string, unknown>) => unknown;

let extra: Handler | null = null;
let items: OfficeItem[] = [];
let details: Record<string, OfficeItemDetail> = {};

const install = () => {
  const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
    const custom = extra?.(route, body);
    if (custom !== undefined) {
      if (custom instanceof Error) throw custom;
      return custom;
    }
    if (route === '/api/project') {
      if (body?.action === 'of') return { project: { id: 'personal', name: 'Personal' }, pending: false };
      return { projects: [{ id: 'personal', name: 'Personal', kind: 'user' }], active: 'personal' };
    }
    if (route.startsWith('/api/office?')) return { generated: 1, items };
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

const Where: React.FC = () => {
  const location = useLocation();
  return <div data-testid='where'>{`${location.pathname}${location.search}`}</div>;
};

const Chat: React.FC = () => {
  const { id } = useParams();
  return (
    <div>
      <KelWorkCardRow conversationId={id} availableWidth={920} pollActiveMs={40} pollIdleMs={80} openFolder={async () => undefined} />
      <Where />
    </div>
  );
};

const renderChat = () =>
  render(
    <MemoryRouter initialEntries={['/conversation/app-morning']}>
      <Routes>
        <Route path='/conversation/:id' element={<Chat />} />
        <Route path='/settings/staff' element={<Where />} />
      </Routes>
    </MemoryRouter>
  );

const detailProps = { pollMs: 60000, onClose: vi.fn(), onRemove: vi.fn(), onTalk: vi.fn(), onChanged: vi.fn(), openFolder: vi.fn(async () => undefined) };

const renderDetail = (detail: OfficeItemDetail, props: Partial<React.ComponentProps<typeof KelOfficeDetail>> = {}) => {
  details = { [detail.job_id]: detail };
  const request = install();
  render(<KelOfficeDetail item={detail as unknown as OfficeItem} {...detailProps} {...props} />);
  return request;
};

const sends = (request: ReturnType<typeof install>) => request.mock.calls.filter(([route]) => route === '/api/send');

beforeEach(() => {
  extra = null;
  items = [];
  details = {};
  takePendingWorkCard();
  resetProjectsForTests();
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

/* ─── 1. The row card reads the list's verdict ─────────────────────────────────────────────── */

describe('the row card reads the list’s own verdict (LIVE-10)', () => {
  const card = (item: OfficeItem) => {
    render(<KelOfficeCard item={item} team={[]} onOpen={vi.fn()} onRemove={vi.fn()} />);
    return screen.getByTestId('kel-office-card');
  };

  it('says "Never ran" for unconfirmed work, in the amber caution — never "Failed"', () => {
    const shown = card({ ...BACKUP, finished_at: AT(8, 15), verdict: 'UNCERTAIN' });
    expect(within(shown).getByTestId('kel-office-card-state').textContent).toBe('Never ran');
    expect(shown.className).toContain('is-uncertain');
    expect(shown.textContent).not.toContain('Failed');
    expect(within(shown).getByRole('button', { name: /^Backup check, Never ran/ })).toBeTruthy();
  });

  it('still says "Failed" when the checks failed', () => {
    const shown = card({ ...BACKUP, verdict: 'FAILED' });
    expect(within(shown).getByTestId('kel-office-card-state').textContent).toBe('Failed');
    expect(shown.className).not.toContain('is-uncertain');
  });

  it('marks unconfirmed work amber behind "+N more" too', async () => {
    items = [MIC, { ...MIC, job_id: 'b', title: 'B' }, { ...MIC, job_id: 'c', title: 'C' }, { ...MIC, job_id: 'd', title: 'D' }, { ...BACKUP, verdict: 'UNCERTAIN' }].map(
      (item, order) => ({ ...item, order })
    );
    install();
    renderChat();
    const overflow = await screen.findByTestId('kel-office-overflow');
    expect(overflow.getAttribute('aria-label')).toContain('Backup check (never ran)');
  });
});

/* ─── 2. The engine's own words in the detail ─────────────────────────────────────────────── */

describe('the detail uses the engine’s own words (LIVE-10)', () => {
  const FINISHED: OfficeItemDetail = {
    ...RECEIPTS_DETAIL,
    review: {
      verdict: 'VERIFIED',
      checked_by: 'GPT-6 Astra',
      independence: 'different',
      independence_label: 'A different model family from the one that did the work',
      findings: [],
    },
    oracle: {
      state: 'done',
      why: 'it changes more than 10 files',
      independence: 'reduced',
      independence_label: 'The same model family as the one that did the work, so less independent',
      model_label: 'GPT-6 Astra',
      findings: [],
      conclusion: 'It found nothing that should stop this, and left one note.',
      coverage: 'Read every renamed file and the summary sheet; could not open the spreadsheet formulas',
    },
  };

  it('D-79: the Review Team keeps one status; independence, conclusions and coverage are gone', async () => {
    renderDetail(FINISHED);
    const review = await screen.findByTestId('kel-office-review');
    expect(review.textContent).not.toMatch(/model family|What it looked at|It found nothing/);
    expect(screen.queryByTestId('kel-office-oracle')).toBeNull();
  });

  it('marks the step a restart stopped as "Interrupted", not "Now"', async () => {
    renderDetail({
      ...MIC_DETAIL,
      state: 'needs_you',
      steps: [
        { id: 'm1', label: 'Plan the app', state: 'done', at: AT(9, 13) },
        { id: 'm2', label: 'Build the hotkey', state: 'in_review', at: null, interrupted: true },
        { id: 'm3', label: 'Check it', state: 'waiting', at: null },
      ],
    });
    const steps = await screen.findAllByTestId('kel-office-step');
    expect(steps[1].className).toContain('kel-wd-step--interrupted');
    expect(steps[1].textContent).toContain('Interrupted');
    expect(steps[1].textContent).not.toContain('Now');
    // Nothing is "Next" while the interrupted step waits to be started again.
    expect(steps[2].textContent).not.toContain('Next');
  });

  it('names the model Kel’s own turn ran on, beside its standard plan', async () => {
    renderDetail({
      ...RECEIPTS_DETAIL,
      staff: [
        {
          id: 'kel',
          role: 'kel',
          role_label: 'Kel',
          state: 'done',
          model: 'gpt-6-luna',
          model_label: 'ChatGPT Luna',
          model_confirmed: true,
          standard_plan: true,
          note: 'Kel used its standard plan for this kind of work.',
        },
      ],
    });
    const kel = (await screen.findAllByTestId('kel-office-member'))[0];
    expect(within(kel).getByTestId('kel-office-model').textContent).toBe('ChatGPT Luna');
    // D-79: no line under the row; its note is in the row's tooltip.
    expect(kel.textContent).not.toContain('Kel used its standard plan for this kind of work.');
    expect(kel.getAttribute('title')).toContain('Kel used its standard plan for this kind of work.');
  });
});

/* ─── 3. The new needs-you kinds ──────────────────────────────────────────────────────────── */

const NO_MODEL: OfficeQuestion = {
  kind: 'no_model',
  wait: 'No model can run it',
  text: 'No model here can run this work. Change the model, then try again?',
  detail: 'GPT-6 Astra can’t run here: Codex is not signed in.',
  options: [
    { id: 'continue', label: 'Try again' },
    { id: 'open_staff', label: 'Change the model in Staff & models', action: 'open_settings', target: 'staff' },
  ],
  answer_box: true,
  conversation_id: 'engine-morning',
  job_id: 'job-mic',
  ref: { job: 'job-mic' },
};

describe('needs-you: no model, out of tries, interrupted (LIVE-3)', () => {
  it('offers Try again as an answer and Staff & models as a place to go', () => {
    install();
    render(<KelNeedsAnswer question={NO_MODEL} onAnswered={vi.fn()} />);
    const chips = screen.getByTestId('kel-needs-chips');
    expect(within(chips).getAllByRole('radio').map((chip) => chip.textContent)).toEqual(['Try again']);
    expect(screen.getByTestId('kel-needs-place-open_staff').textContent).toBe('Change the model in Staff & models');
    expect(screen.getByText('GPT-6 Astra can’t run here: Codex is not signed in.')).toBeTruthy();
  });

  it('opens Settings → Staff & models for this chat and sends nothing to Kel', () => {
    const request = install();
    const open = vi.fn();
    const answered = vi.fn();
    render(<KelNeedsAnswer question={NO_MODEL} onAnswered={answered} onOpenSettings={open} />);
    fireEvent.click(screen.getByTestId('kel-needs-place-open_staff'));
    expect(open).toHaveBeenCalledWith('/settings/staff?conversation=engine-morning');
    expect(request).not.toHaveBeenCalled();
    expect(answered).not.toHaveBeenCalled();
  });

  it.each([
    ['no_model', NO_MODEL],
    ['out_of_tries', { ...NO_MODEL, kind: 'out_of_tries', text: 'This work ran out of tries before it passed its checks. Give it more tries?', options: [{ id: 'continue', label: 'Try again' }] }],
    ['interrupted', { ...NO_MODEL, kind: 'interrupted', text: 'Kel’s worker stopped unexpectedly (the app restarted). Start that step again?', options: [{ id: 'continue', label: 'Try again' }] }],
  ] as const)('Try again on %s is a "continue" message for the job', async (_kind, question) => {
    const request = install();
    const answered = vi.fn();
    render(<KelNeedsAnswer question={question as OfficeQuestion} onAnswered={answered} />);
    await act(async () => {
      fireEvent.click(within(screen.getByTestId('kel-needs-chips')).getByRole('radio', { name: 'Try again' }));
    });
    expect(sends(request)).toEqual([['/api/send', { conversation: 'engine-morning', text: 'continue', job_id: 'job-mic' }]]);
    expect(answered).toHaveBeenCalledWith(expect.objectContaining({ words: 'Try again' }));
  });

  it('says Kel is trying again once Try again is on its way', async () => {
    items = [{ ...MIC, state: 'needs_you', needs_you: true }];
    details = { [MIC.job_id]: { ...MIC_DETAIL, state: 'needs_you', question: NO_MODEL } };
    install();
    renderChat();
    fireEvent.click((await screen.findAllByTestId('kel-office-card'))[0].querySelector('.kel-wc__open') as HTMLElement);
    await screen.findByTestId('kel-needs-question');
    await act(async () => {
      fireEvent.click(within(screen.getByTestId('kel-needs-chips')).getByRole('radio', { name: 'Try again' }));
    });
    expect((await screen.findByTestId('kel-needs-answered')).textContent).toContain('Kel is trying again');
  });

  it('from the top card, "Change the model in Staff & models" goes to that page', async () => {
    items = [{ ...MIC, state: 'needs_you', needs_you: true }];
    details = { [MIC.job_id]: { ...MIC_DETAIL, state: 'needs_you', question: NO_MODEL } };
    const request = install();
    renderChat();
    fireEvent.click((await screen.findAllByTestId('kel-office-card'))[0].querySelector('.kel-wc__open') as HTMLElement);
    fireEvent.click(await screen.findByTestId('kel-needs-place-open_staff'));
    expect((await screen.findByTestId('where')).textContent).toBe('/settings/staff?conversation=engine-morning');
    expect(sends(request)).toEqual([]);
  });
});

/* ─── 4. The Home brief says each wait plainly ────────────────────────────────────────────── */

const waitingJob = (id: string, request: string, over: Partial<KelWorkJob> = {}): KelWorkJob =>
  ({
    id,
    state: 'WAITING_RESOURCE',
    conversation: `engine-${id}`,
    updated: 100,
    contract: { request, staffing: { schema: 1 } } as never,
    milestones: { m1: { state: 'READY', attempts: 1 } },
    ...over,
  }) as KelWorkJob;

describe('the Home brief names each wait (FN-03, LIVE-3)', () => {
  const lineFor = (job: KelWorkJob) => {
    const result = buildResumptionBrief({ jobs: [job], now: 1 });
    expect(result.lines).toHaveLength(1);
    return result.lines[0];
  };

  it('interrupted: the worker stopped, Try again on its card', () => {
    const line = lineFor(waitingJob('i', 'Tidy the notes', { milestones: { m1: { state: 'UNCERTAIN', attempts: 1, interrupted: true } as never } }));
    expect(line.detail).toBe(
      'Interrupted — Kel’s worker stopped unexpectedly (the app restarted) before a step finished, and Kel won’t repeat it on its own. Choose Try again on its card to start that step again.'
    );
    expect(line.action?.card).toBe('i');
  });

  it('stuck: out of tries, give it more', () => {
    const line = lineFor(waitingJob('s', 'Fix the parser', { route_block: 'Out of tries: Every model it may use failed this step 3 times.' }));
    expect(line.detail).toBe(
      'Out of tries — It ran out of tries before it passed its checks (Every model it may use failed this step 3 times). Choose Try again on its card to give it more tries, or stop it.'
    );
  });

  it('fixed: the Fixed model can’t run, change it in Staff & models', () => {
    const line = lineFor(waitingJob('f', 'Write the post', { route_block: 'Fixed model not available: GPT-6 Astra can’t run here: Codex is not signed in.' }));
    expect(line.detail).toBe(
      'No model can run it — GPT-6 Astra can’t run here: Codex is not signed in. Change the model in Settings → Staff & models, then choose Try again on its card.'
    );
  });

  it('no_route: nothing here can do it, change or set one up', () => {
    const line = lineFor(waitingJob('n', 'Research laptops', { route_block: 'No model can do this: No model here can search the web.' }));
    expect(line.detail).toBe(
      'No model can run it — No model here can search the web. Change the model in Settings → Staff & models (or set one up), then choose Try again on its card.'
    );
  });

  it('budget: raise it on its card', () => {
    const line = lineFor(waitingJob('b', 'Big refactor', { route_block: 'Budget reached: It used its 2M-token standard budget.' }));
    expect(line.detail).toBe('Stopped at its budget — It used its 2M-token standard budget. Raise its budget on its card to let it continue, or stop it.');
    expect(line.action?.label).toBe('Open its card');
  });

  it('takes the engine’s own `wait` when the payload carries it', () => {
    const line = lineFor(waitingJob('w', 'Write the post', { route_block: 'Something new the engine says', wait: 'stuck' } as never));
    expect(line.detail.startsWith('Out of tries — ')).toBe(true);
  });

  it('keeps a job that only waits for a free model out of the brief', () => {
    expect(buildResumptionBrief({ jobs: [waitingJob('q', 'Later', { route_block: 'No model is free right now' })] }).lines).toEqual([]);
  });

  it('shows the words on the Home card', async () => {
    const jobs = [
      waitingJob('f', 'Write the post', { route_block: 'Fixed model not available: GPT-6 Astra can’t run here: Codex is not signed in.' }),
      waitingJob('s', 'Fix the parser', { route_block: 'Out of tries: Every model it may use failed this step 3 times.' }),
    ];
    const request = vi.fn(async (route: string) => {
      if (route.startsWith('/api/state')) return { jobs, continuation: [], providers: [], projects: [], routes: {} };
      if (route === '/api/autonomy') return { requests: [] };
      if (route === '/api/providers') return { providers: [] };
      return {};
    });
    (window as unknown as { kelAPI: unknown }).kelAPI = { request, conversation: vi.fn(async (id: string) => id) };
    render(
      <MemoryRouter initialEntries={['/guid']}>
        <KelResumptionBrief />
      </MemoryRouter>
    );
    const card = await screen.findByTestId('resumption-brief');
    expect(card.textContent).toContain('Write the post — No model can run it — GPT-6 Astra can’t run here');
    expect(card.textContent).toContain('Fix the parser — Out of tries — ');
  });
});

/* ─── 5. Staff & models ───────────────────────────────────────────────────────────────────── */

const staffEngine = (kelModel: Record<string, unknown>, chatModel?: Record<string, unknown>) => {
  const models = [
    { id: 'claude-opus-5-5', label: 'Claude Opus 5.5', available: true, reasoning_options: ['auto', 'high'] },
    { id: 'gpt-6-astra', label: 'GPT-6 Astra', available: true, reasoning_options: ['auto', 'high'] },
    { id: 'deepseek-flash', label: 'DeepSeek Flash', available: true, reasoning_options: ['auto'] },
  ];
  const row = (role: string, label: string, purpose: string, model: string | null, options: Array<Record<string, unknown>>) => ({
    role,
    label,
    mode: model ? 'PREFERRED' : 'AUTOMATIC',
    model,
    model_label: models.find((entry) => entry.id === model)?.label ?? null,
    reasoning: 'auto',
    reasoning_options: ['auto', 'high'],
    available: true,
    is_default: true,
    purpose,
    model_options: options,
    default: { mode: model ? 'PREFERRED' : 'AUTOMATIC', model, reasoning: 'auto' },
  });
  const builderOptions = [
    { id: 'claude-opus-5-5', label: 'Claude Opus 5.5', available: true, note: null },
    { id: 'gpt-6-astra', label: 'GPT-6 Astra', available: true, note: null },
    { id: 'deepseek-flash', label: 'DeepSeek Flash', available: false, note: "DeepSeek Flash can't change code, so it can't do the Builder's code work" },
  ];
  const textOptions = builderOptions.map((option) => ({ ...option, available: true, note: null }));
  const listing = {
    roles: [
      row('kel', 'Kel', 'text', 'gpt-6-astra', textOptions),
      row('discovery', 'Discovery (research)', 'web', null, textOptions),
      row('builder', 'Builder', 'code', 'claude-opus-5-5', builderOptions),
    ],
    models,
    kel_model: kelModel,
  };
  return vi.fn(async (route: string, body?: Record<string, unknown>) => {
    if (route !== '/api/model') return {};
    if (body?.action === 'get') return { conversation: null, default: null, kel_model: chatModel ?? kelModel };
    if (body?.action === 'ranking') return { classes: [] };
    return listing;
  });
};

const KEL_MODEL = { kel: { source: 'staff_role', mode: 'PREFERRED', model: 'gpt-6-astra', reasoning: 'auto', label: 'GPT-6 Astra' }, conversation_override: null, in_effect: 'kel' };

const renderStaff = (at = '/settings/staff') =>
  render(
    <MemoryRouter initialEntries={[at]}>
      <StaffModelsSettings />
    </MemoryRouter>
  );

describe('Staff & models: per-role options, purpose, the model in effect (LIVE-3, FN-06)', () => {
  it('offers only what each role can use; the rest are disabled with the engine’s reason', async () => {
    (window as unknown as { kelAPI: unknown }).kelAPI = { request: staffEngine(KEL_MODEL) };
    renderStaff();
    const builder = await screen.findByTestId('staff-row-builder');
    const select = within(builder).getByRole('combobox', { name: 'Builder: model' }) as HTMLSelectElement;
    const flash = Array.from(select.options).find((option) => option.value === 'deepseek-flash') as HTMLOptionElement;
    expect(flash.disabled).toBe(true);
    expect(flash.textContent).toBe("DeepSeek Flash (can't change code, so it can't do the Builder's code work)");
    const astra = Array.from(select.options).find((option) => option.value === 'gpt-6-astra') as HTMLOptionElement;
    expect(astra.disabled).toBe(false);
    // The same model is fine for a writing role.
    const kelSelect = within(screen.getByTestId('staff-row-kel')).getByRole('combobox', { name: 'Kel: model' }) as HTMLSelectElement;
    expect((Array.from(kelSelect.options).find((option) => option.value === 'deepseek-flash') as HTMLOptionElement).disabled).toBe(false);
  });

  it('says what each role’s work needs of its model', async () => {
    (window as unknown as { kelAPI: unknown }).kelAPI = { request: staffEngine(KEL_MODEL) };
    renderStaff();
    expect((await screen.findByTestId('staff-purpose-builder')).textContent).toBe('Needs a model that can change code');
    expect(screen.getByTestId('staff-purpose-discovery').textContent).toBe('Needs a model that can search the web');
    expect(screen.getByTestId('staff-purpose-kel').textContent).toBe('Any model that writes well');
  });

  it('says Kel’s model plainly when opened from Settings', async () => {
    (window as unknown as { kelAPI: unknown }).kelAPI = { request: staffEngine(KEL_MODEL) };
    renderStaff();
    expect((await screen.findByTestId('staff-kel-in-effect')).textContent).toBe(
      'Kel’s model: GPT-6 Astra. Every chat uses it unless you pick another model in that chat.'
    );
  });

  it('says "This chat uses its own model: X" when opened for a chat that has one', async () => {
    const request = staffEngine(KEL_MODEL, {
      ...KEL_MODEL,
      conversation_override: { provider: 'catalog', model: 'claude-opus-5-5', label: 'Claude Opus 5.5' },
      in_effect: 'conversation',
    });
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    renderStaff('/settings/staff?conversation=engine-morning');
    await waitFor(() =>
      expect(screen.getByTestId('staff-kel-in-effect').textContent).toBe(
        'This chat uses its own model: Claude Opus 5.5. Kel’s model (the Kel row below) is GPT-6 Astra.'
      )
    );
    expect(request).toHaveBeenCalledWith('/api/model', { action: 'get', conversation: 'engine-morning' });
  });

  it('says a chat without its own model uses Kel’s', async () => {
    (window as unknown as { kelAPI: unknown }).kelAPI = { request: staffEngine(KEL_MODEL) };
    renderStaff('/settings/staff?conversation=engine-morning');
    await waitFor(() => expect(screen.getByTestId('staff-kel-in-effect').textContent).toBe('This chat uses Kel’s model: GPT-6 Astra.'));
  });
});

/* ─── 6. "Not now" on scoping ─────────────────────────────────────────────────────────────── */

const SCOPING = {
  id: 'scope-1',
  title: 'Plumbing website',
  state: 'open',
  conversation_id: 'engine-morning',
  questions: [{ id: 'q1', question: 'How finished?', options: [{ code: 'a', label: 'Quick' }] }],
  summary: 'I’ll build: a plumbing website.',
};

describe('"Not now" cancels a scoping card (D-74.3, LIVE-8)', () => {
  it('on the card in the thread: nothing starts, and it settles into one line', async () => {
    let state = 'open';
    extra = (route, body) => {
      if (route.startsWith('/api/scoping?id=')) return { ...SCOPING, state };
      if (route === '/api/scoping' && body?.action === 'not_now') {
        state = 'dismissed';
        return { ...SCOPING, state, dismissed: true };
      }
      return undefined;
    };
    const request = install();
    render(<KelScopingCard scopingId='scope-1' conversationId='app-morning' />);
    const notNow = await screen.findByTestId('kel-scoping-not-now');
    await act(async () => {
      fireEvent.click(notNow);
    });
    expect(request).toHaveBeenCalledWith('/api/scoping', { action: 'not_now', id: 'scope-1', conversation: 'engine-morning' });
    const line = await screen.findByTestId('kel-scoping-dismissed');
    expect(line.textContent).toContain('Not now');
    expect(line.textContent).toContain('Nothing started.');
    expect(request.mock.calls.some(([route, body]) => route === '/api/scoping' && ['start', 'best_guess'].includes(String((body as { action?: string })?.action)))).toBe(false);
  });

  it('on the top card: the card goes and the engine cancels the questions', async () => {
    items = [{ job_id: 'scope-1', scoping_id: 'scope-1', title: 'Plumbing website', state: 'scoping', questions: 2, conversation_id: 'engine-morning', order: 0 }];
    const request = install();
    extra = (route, body) => {
      if (route === '/api/scoping' && body?.action === 'not_now') {
        items = [];
        return { ...SCOPING, state: 'dismissed', dismissed: true };
      }
      return undefined;
    };
    renderChat();
    const button = await screen.findByRole('button', { name: 'Not now: Plumbing website' });
    await act(async () => {
      fireEvent.click(button);
    });
    expect(request).toHaveBeenCalledWith('/api/scoping', { action: 'not_now', id: 'scope-1' });
    await waitFor(() => expect(screen.queryByTestId('kel-office-card')).toBeNull());
    // It never opened the questions or a detail on the way.
    expect(screen.queryByTestId('kel-office-detail')).toBeNull();
  });

  it('comes back when the engine keeps it', async () => {
    items = [{ job_id: 'scope-1', scoping_id: 'scope-1', title: 'Plumbing website', state: 'scoping', questions: 2, conversation_id: 'engine-morning', order: 0 }];
    const request = install();
    extra = (route, body) => (route === '/api/scoping' && body?.action === 'not_now' ? new Error('This work has already started.') : undefined);
    renderChat();
    const button = await screen.findByRole('button', { name: 'Not now: Plumbing website' });
    await act(async () => {
      fireEvent.click(button);
    });
    expect(request).toHaveBeenCalledWith('/api/scoping', { action: 'not_now', id: 'scope-1' });
    await waitFor(() => expect(screen.getAllByTestId('kel-office-card')).toHaveLength(1));
  });

  it('is never offered on running or finished work', () => {
    render(<KelOfficeCard item={MIC} team={[]} onOpen={vi.fn()} onNotNow={vi.fn()} />);
    render(<KelOfficeCard item={RECEIPTS} team={[]} onOpen={vi.fn()} onNotNow={vi.fn()} />);
    expect(screen.queryByTestId('kel-office-card-not-now')).toBeNull();
  });
});

/* ─── 7. Undone work ──────────────────────────────────────────────────────────────────────── */

describe('undone work says so from the engine’s record (LIVE-12)', () => {
  const UNDONE = { at: AT(10, 42), files: 3, folders: 1 };

  it('the row card reads "Undone"', () => {
    render(<KelOfficeCard item={{ ...RECEIPTS, undone: UNDONE, application: { state: 'UNDONE' } }} team={[]} onOpen={vi.fn()} />);
    expect(screen.getByTestId('kel-office-card-state').textContent).toBe('Undone');
  });

  it('reads "Undone" from the application state alone', () => {
    render(<KelOfficeCard item={{ ...RECEIPTS, application: { state: 'UNDONE' } }} team={[]} onOpen={vi.fn()} />);
    expect(screen.getByTestId('kel-office-card-state').textContent).toBe('Undone');
  });

  it('the detail says when it was undone and what came back, with no Undo', async () => {
    renderDetail({ ...RECEIPTS_DETAIL, undone: UNDONE, application: { ...RECEIPTS_DETAIL.application!, state: 'UNDONE' } });
    const applied = await screen.findByTestId('kel-office-applied');
    expect(applied.textContent).toBe('Undone at 10:42 AM — 3 files are back as they were; 1 empty folder removed.');
    expect(screen.queryByTestId('kel-office-undo')).toBeNull();
  });

  it('the done card says the same', async () => {
    details = { [RECEIPTS.job_id]: { ...RECEIPTS_DETAIL, undone: { at: AT(10, 42), files: 1, folders: 0 }, application: { ...RECEIPTS_DETAIL.application!, state: 'UNDONE' } } };
    install();
    render(<KelDoneCard job={RECEIPTS.job_id} openFolder={async () => undefined} />);
    expect((await screen.findByTestId('kel-done-card-applied')).textContent).toBe('Undone at 10:42 AM — the file is back as it was.');
    expect(screen.queryByTestId('kel-done-card-undo')).toBeNull();
  });

  it('D-79: an applied change says where it went, with no Undo in the panel (Nick asks Kel)', async () => {
    renderDetail(RECEIPTS_DETAIL);
    expect((await screen.findByTestId('kel-office-applied')).textContent).toContain('Applied automatically');
    expect(screen.queryByTestId('kel-office-undo')).toBeNull();
  });
});
