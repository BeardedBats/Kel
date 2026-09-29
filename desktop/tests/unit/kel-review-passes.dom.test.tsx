/**
 * bc873da: the engine's independent passes after the checks — Sentinel (security / data safety), the
 * Oracle (second opinion) and the Red Team (tries to break the accepted result) — each in the Oracle's
 * shape on /api/office/item. The detail's Review and checks column shows them in that order, what each
 * concluded first and what it looked at second; Sentinel and the Red Team only when the engine has
 * something to say. Same on the desktop panel and the phone sheet.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { takePendingWorkCard } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { initials, oracleLines, roleName, showReviewPass } from '@renderer/components/kel/workCards/workCardModel';
import type { OfficeItem, OfficeItemDetail, OfficeOracle } from '@renderer/components/kel/workCards/officeApi';
import { MIC, MIC_DETAIL } from './fixtures/kelOfficeFixtures';

let list: OfficeItem[] = [];
let details: Record<string, OfficeItemDetail> = {};

const install = () => {
  const request = vi.fn(async (route: string) => {
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

const Chat: React.FC<{ phone: boolean }> = ({ phone }) => {
  const { id } = useParams();
  return <KelWorkCardRow conversationId={id} phone={phone} availableWidth={phone ? undefined : 920} pollActiveMs={40} pollIdleMs={80} openFolder={async () => undefined} />;
};

const renderRow = (phone = false) =>
  render(
    <MemoryRouter initialEntries={['/conversation/app-morning']}>
      <Routes>
        <Route path='/conversation/:id' element={<Chat phone={phone} />} />
      </Routes>
    </MemoryRouter>
  );

const SENTINEL_DONE: OfficeOracle = {
  state: 'done',
  why: 'the change touches how passwords are stored',
  conclusion: 'No security or data-safety problems found.',
  coverage: 'The password hashing and the settings form; not the network layer',
  independence: 'different',
  independence_label: 'a different model family from the one that did the work',
  model_label: 'GPT-6 Astra',
  reasoning: 'high',
  findings: [],
};
const RED_TEAM_RUNNING: OfficeOracle = { state: 'running', why: 'a security change over 150 lines', model_label: 'Claude Opus 5.5', reasoning: 'high', findings: [] };

const withPasses = (over: Partial<OfficeItemDetail>): OfficeItemDetail => ({
  ...MIC_DETAIL,
  state: 'in_review',
  staff: [
    ...(MIC_DETAIL.staff ?? []),
    { id: 's1', role: 'sentinel', role_label: 'Sentinel', doing: 'Security check: no problems found', state: 'done', model_label: 'GPT-6 Astra', model_confirmed: true, reasoning: 'high' },
    { id: 'r1', role: 'red_team', doing: 'Trying to break the accepted result', state: 'working', model_label: 'Claude Opus 5.5', model_confirmed: true, reasoning: 'high' },
  ],
  oracle: { state: 'done', conclusion: 'No problems found.', findings: [] },
  ...over,
});

const openMic = async () => {
  fireEvent.click(await screen.findByRole('button', { name: /Mic mute toggle app/ }));
  const dialog = await screen.findByTestId('kel-office-detail');
  await within(dialog).findAllByTestId('kel-office-member');
  return dialog;
};

beforeEach(() => {
  list = [];
  details = {};
  resetProjectsForTests();
  takePendingWorkCard();
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('D-79: the Review Team replaces Review and checks', () => {
  it('one status while the passes run, and none of the old per-pass blocks', async () => {
    list = [{ ...MIC, state: 'in_review' }];
    details = { [MIC.job_id]: withPasses({ sentinel: SENTINEL_DONE, red_team: RED_TEAM_RUNNING }) };
    install();
    renderRow();
    const dialog = await openMic();
    const review = await within(dialog).findByTestId('kel-office-review');
    expect(within(review).getByTestId('kel-office-review-state').textContent).toBe('In progress');
    expect(dialog.querySelector('[data-pass]')).toBeNull();
    expect(within(dialog).queryByTestId('kel-office-sentinel')).toBeNull();
    expect(review.textContent).not.toMatch(/What it looked at|Asked because|different model family/);
    expect(dialog.querySelector('.kel-wd-col--review h3')?.textContent).toBe('Review Team');
  });

  it('names the new staff rows: Sentinel and Red Team, each in its own role colour', async () => {
    expect(roleName({ role: 'red_team', role_label: null })).toBe('Red Team');
    expect(roleName({ role: 'sentinel', role_label: null })).toBe('Sentinel');
    expect(initials({ role: 'red_team', role_label: 'Red Team' })).toBe('Re');
    list = [{ ...MIC, state: 'in_review' }];
    details = { [MIC.job_id]: withPasses({ sentinel: SENTINEL_DONE, red_team: RED_TEAM_RUNNING }) };
    install();
    renderRow();
    const dialog = await openMic();
    const rows = within(dialog).getAllByTestId('kel-office-member');
    const names = rows.map((row) => row.querySelector('strong')?.textContent);
    expect(names).toContain('Sentinel');
    expect(names).toContain('Red Team');
    expect(rows.find((row) => row.textContent?.includes('Sentinel'))?.className).toContain('kel-role--sentinel');
    expect(rows.find((row) => row.textContent?.includes('Red Team'))?.className).toContain('kel-role--red-team');
  });

  it('a Sentinel blocker is Needs you in Sentinel’s words, with Apply anyway / Leave it, and one problem line', async () => {
    list = [{ ...MIC, state: 'needs_you' }];
    details = {
      [MIC.job_id]: withPasses({
        state: 'needs_you',
        review: { verdict: null, findings: [] },
        sentinel: { ...SENTINEL_DONE, conclusion: 'Found: any password is accepted.', findings: [{ summary: 'Any password is accepted', status: 'open', severity: 'blocker' }] },
        question: {
          kind: 'second_opinion',
          source: 'sentinel',
          text: 'Sentinel’s security check raised a problem. Apply the change anyway?',
          detail: 'Kel had this checked by Sentinel. Any password is accepted.',
          options: [
            { id: 'apply_anyway', label: 'Apply anyway' },
            { id: 'leave', label: 'Leave it' },
          ],
          conversation_id: 'engine-morning',
          ref: { job: MIC.job_id },
        },
      }),
    };
    install();
    renderRow();
    const dialog = await openMic();
    const question = await within(dialog).findByTestId('kel-needs-question');
    expect(within(question).getByTestId('kel-needs-question-text').textContent).toBe('Sentinel’s security check raised a problem. Apply the change anyway?');
    expect(within(question).getByRole('radio', { name: 'Apply anyway' })).toBeTruthy();
    expect(within(question).getByRole('radio', { name: 'Leave it' })).toBeTruthy();
    expect(within(dialog).getByTestId('kel-office-review-problem').textContent).toMatch(/^Sentinel found any password is accepted/);
  });

  it('shows the same Review Team in the phone sheet', async () => {
    list = [{ ...MIC, state: 'in_review' }];
    details = { [MIC.job_id]: withPasses({ sentinel: SENTINEL_DONE, red_team: RED_TEAM_RUNNING }) };
    install();
    renderRow(true);
    fireEvent.click(await screen.findByRole('button', { name: /Mic mute toggle app/ }));
    const sheet = await screen.findByTestId('kel-work-sheet');
    const body = within(sheet).getByTestId('kel-office-sheet-body');
    await waitFor(() => expect(within(body).getByTestId('kel-office-review-state').textContent).toBe('In progress'));
    expect(body.querySelector('[data-pass]')).toBeNull();
  });
});

describe('the pass wording', () => {
  it('says what each pass is doing while it waits and runs', () => {
    expect(oracleLines({ state: 'waiting' }, 'sentinel').line).toBe('Security and data-safety check before hand-over.');
    expect(oracleLines({ state: 'running' }, 'sentinel').line).toBe('Checking it for security and data safety now.');
    expect(oracleLines({ state: 'waiting' }, 'red_team').line).toBe('Will try to break the accepted result before hand-over.');
    expect(oracleLines({ state: 'waiting' }).line).toBe('Second opinion before hand-over.');
    expect(oracleLines({ state: 'could_not_run', conclusion: "It couldn't run: no model could", why: 'no model could' }, 'red_team').line).toBe(
      "It couldn't run: no model could."
    );
  });
  it('shows the Oracle always and the others only with something to say', () => {
    expect(showReviewPass('oracle', null)).toBe(true);
    expect(showReviewPass('sentinel', null)).toBe(false);
    expect(showReviewPass('sentinel', { state: 'not_needed' })).toBe(false);
    expect(showReviewPass('sentinel', { state: 'not_needed', why: 'Writing only mentions passwords.' })).toBe(true);
    expect(showReviewPass('red_team', { state: 'waiting' })).toBe(true);
  });
});
