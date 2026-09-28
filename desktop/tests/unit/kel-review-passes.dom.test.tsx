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

describe('Sentinel and the Red Team in Review and checks', () => {
  it('lists Sentinel → Oracle → Red Team, conclusion first, then what it looked at', async () => {
    list = [{ ...MIC, state: 'in_review' }];
    details = { [MIC.job_id]: withPasses({ sentinel: SENTINEL_DONE, red_team: RED_TEAM_RUNNING }) };
    install();
    renderRow();
    const dialog = await openMic();
    const order = Array.from(dialog.querySelectorAll('[data-pass]')).map((node) => node.getAttribute('data-pass'));
    expect(order).toEqual(['sentinel', 'oracle', 'red_team']);

    const sentinel = within(dialog).getByTestId('kel-office-sentinel');
    expect(within(sentinel).getByText('Sentinel')).toBeTruthy();
    expect(within(sentinel).getByText('GPT-6 Astra · High')).toBeTruthy();
    expect(within(sentinel).getByTestId('kel-office-sentinel-line').textContent).toBe('No security or data-safety problems found.');
    expect(within(sentinel).getByTestId('kel-office-sentinel-coverage').textContent).toBe(
      'What it looked at: the password hashing and the settings form; not the network layer.'
    );
    expect(within(sentinel).getByTestId('kel-office-sentinel-why').textContent).toBe(
      'Asked because: the change touches how passwords are stored. Given by a different model family from the one that did the work.'
    );
    // The line comes before the coverage in reading order.
    const line = within(sentinel).getByTestId('kel-office-sentinel-line');
    const coverage = within(sentinel).getByTestId('kel-office-sentinel-coverage');
    expect(line.compareDocumentPosition(coverage) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const red = within(dialog).getByTestId('kel-office-red-team');
    expect(within(red).getByText('Red Team')).toBeTruthy();
    expect(within(red).getByTestId('kel-office-red-team-line').textContent).toBe('Trying to break the accepted result now.');
    expect(within(red).queryByTestId('kel-office-red-team-coverage')).toBeNull();
  });

  it('leaves out a pass the engine did not need and gave no reason for; a skipped one says why, compactly', async () => {
    list = [{ ...MIC, state: 'in_review' }];
    details = {
      [MIC.job_id]: withPasses({
        sentinel: { state: 'not_needed', why: null, findings: [] },
        red_team: { state: 'not_needed', why: 'An earlier review already stands', conclusion: 'An earlier review already stands', findings: [] },
      }),
    };
    install();
    renderRow();
    const dialog = await openMic();
    expect(within(dialog).queryByTestId('kel-office-sentinel')).toBeNull();
    expect(within(dialog).getByTestId('kel-office-oracle')).toBeTruthy();
    expect(within(dialog).getByTestId('kel-office-red-team-line').textContent).toBe('Not needed: an earlier review already stands.');
  });

  it('an older engine without the blocks shows the Oracle alone, as before', async () => {
    list = [MIC];
    details = { [MIC.job_id]: MIC_DETAIL };
    install();
    renderRow();
    const dialog = await openMic();
    expect(Array.from(dialog.querySelectorAll('[data-pass]')).map((node) => node.getAttribute('data-pass'))).toEqual(['oracle']);
  });

  it('names the new staff rows: Sentinel and Red Team', async () => {
    expect(roleName({ role: 'red_team', role_label: null })).toBe('Red Team');
    expect(roleName({ role: 'sentinel', role_label: null })).toBe('Sentinel');
    expect(initials({ role: 'red_team', role_label: 'Red Team' })).toBe('Re');
    list = [{ ...MIC, state: 'in_review' }];
    details = { [MIC.job_id]: withPasses({ sentinel: SENTINEL_DONE, red_team: RED_TEAM_RUNNING }) };
    install();
    renderRow();
    const dialog = await openMic();
    const names = within(dialog).getAllByTestId('kel-office-member').map((row) => row.querySelector('strong')?.textContent);
    expect(names).toContain('Sentinel');
    expect(names).toContain('Red Team');
  });

  it('a Sentinel blocker is Needs you in Sentinel’s words, with Apply anyway / Leave it', async () => {
    list = [{ ...MIC, state: 'needs_you' }];
    details = {
      [MIC.job_id]: withPasses({
        state: 'needs_you',
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
    expect(within(dialog).getByTestId('kel-office-sentinel-line').textContent).toBe('Found: any password is accepted.');
  });

  it('shows the same passes in the phone sheet', async () => {
    list = [{ ...MIC, state: 'in_review' }];
    details = { [MIC.job_id]: withPasses({ sentinel: SENTINEL_DONE, red_team: RED_TEAM_RUNNING }) };
    install();
    renderRow(true);
    fireEvent.click(await screen.findByRole('button', { name: /Mic mute toggle app/ }));
    const sheet = await screen.findByTestId('kel-work-sheet');
    const body = within(sheet).getByTestId('kel-office-sheet-body');
    await waitFor(() => expect(within(body).getByTestId('kel-office-sentinel')).toBeTruthy());
    expect(Array.from(body.querySelectorAll('[data-pass]')).map((node) => node.getAttribute('data-pass'))).toEqual(['sentinel', 'oracle', 'red_team']);
    expect(within(body).getByTestId('kel-office-red-team-line').textContent).toBe('Trying to break the accepted result now.');
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
