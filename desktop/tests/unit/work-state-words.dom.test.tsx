/**
 * WK-4 / CH-15 — one job, one story.
 *
 * The same engine facts must read the same way on every surface (Work, Activity, the Home "Needs
 * you" card, the in-chat work card, status chips), and each job sits in exactly one Activity
 * section. These tests render the real surfaces against one engine payload served through the
 * desktop bridge (window.kelAPI), so they catch a surface that drifts from the shared table.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Activity from '@renderer/pages/kel/activity';
import KelResumptionBrief from '@renderer/pages/guid/components/KelResumptionBrief';
import { KelWorkChip } from '@renderer/components/kel/KelPrimitives';
import { workHeadline } from '@renderer/components/kel/KelWorkCard';
import { WORK_WORDS, workWords } from '@renderer/components/kel/workLanguage';
import type { KelWorkJob } from '@renderer/components/kel/kelApi';

const job = (id: string, state: string, request: string, extra: Partial<KelWorkJob> = {}): KelWorkJob => ({
  id,
  state,
  conversation: `engine-${id}`,
  updated: 1_700_000_000,
  contract: { request, milestones: [{ id: 'm1', objective: `Step for ${request}` }] },
  milestones: { m1: { state: state === 'CLOSED' ? 'ACCEPTED' : 'RUNNING', attempts: 1 } },
  ...extra,
});

const JOBS: KelWorkJob[] = [
  job('run', 'RUNNING', 'Summarize the meeting notes'),
  job('paused', 'PAUSED', 'Rename the holiday photos'),
  job('ask', 'AWAITING_USER', 'Book the dentist'),
  job('orphan', 'WAITING_RESOURCE', 'Tidy the downloads folder'),
  job('model', 'WAITING_RESOURCE', 'Translate the letter', { route_block: 'No model is free right now' }),
  job('ok', 'CLOSED', 'Write the weekly summary', { verdict: 'VERIFIED' }),
  job('meh', 'CLOSED', 'Draft the garden plan', { verdict: 'UNCERTAIN' }),
  job('bad', 'CLOSED', 'Fix the budget sheet', { verdict: 'FAILED' }),
  job('stop', 'CANCELLED', 'Sort the inbox'),
];

let request: ReturnType<typeof vi.fn>;

const install = (jobs: KelWorkJob[] = JOBS) => {
  request = vi.fn(async (route: string, body?: { action?: string; job?: string }) => {
    if (route.startsWith('/api/state')) {
      // Continuation candidates repeat the same jobs — no surface may list them twice.
      return { jobs, routes: {}, providers: [], projects: [], continuation: jobs.map((entry) => ({ job_id: entry.id, state: entry.state })) };
    }
    if (route.startsWith('/api/work')) return { work: { jobs: [] } };
    if (route === '/api/providers') return { providers: [] };
    if (route === '/api/autonomy') return { requests: [] };
    if (route === '/api/control') return { ok: true, action: body?.action };
    return {};
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = { request, conversation: vi.fn(async (id: string) => id) };
};

beforeEach(() => install());
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const Where = () => {
  const location = useLocation();
  return <div data-testid='where'>{`${location.pathname}${location.search}`}</div>;
};

const renderAt = (path: string, element: React.ReactElement) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={path.split('?')[0]} element={<>{element}<Where /></>} />
        <Route path='*' element={<Where />} />
      </Routes>
    </MemoryRouter>
  );

describe('the shared state words', () => {
  it('covers every state with plain words, and only a VERIFIED verdict says "checked"', () => {
    expect(workWords({ state: 'QUEUED' }).label).toBe('Queued');
    expect(workWords({ state: 'RUNNING' }).label).toBe('Working on it');
    expect(workWords({ state: 'VERIFYING' }).label).toBe('Checking the result');
    expect(workWords({ state: 'PAUSED' }).label).toBe('Paused');
    expect(workWords({ state: 'AWAITING_USER' }).label).toBe('Waiting for your OK');
    expect(workWords({ state: 'WAITING_RESOURCE', route_block: 'x' }).label).toBe('Waiting for a model');
    expect(workWords({ state: 'WAITING_RESOURCE' }).label).toBe('Interrupted');
    expect(workWords({ state: 'ORPHANED' }).label).toBe('Interrupted');
    expect(workWords({ state: 'INTERRUPTED' }).label).toBe('Interrupted');
    expect(workWords({ state: 'BLOCKED' }).label).toBe('Blocked — needs your OK');
    expect(workWords({ state: 'CLOSED', verdict: 'VERIFIED' }).label).toBe('Done and checked');
    expect(workWords({ state: 'CLOSED', verdict: 'UNCERTAIN' }).label).toBe('Finished — not fully checked');
    expect(workWords({ state: 'CLOSED' }).label).toBe('Finished — not fully checked');
    expect(workWords({ state: 'CLOSED', verdict: 'FAILED' }).label).toBe("Didn't pass its checks");
    expect(workWords({ state: 'CANCELLED' }).label).toBe('Stopped');
    expect(workWords({ state: 'SOMETHING_NEW' }).label).toBe('Something new');
    const labels = Object.values(WORK_WORDS).map((entry) => entry.label);
    expect(labels.filter((label) => /checked/i.test(label) && !/not fully/i.test(label))).toEqual(['Done and checked']);
  });

  it('gives the status chip and the in-chat card the same words', () => {
    render(<KelWorkChip job={{ state: 'BLOCKED' }} />);
    expect(screen.getByText('Blocked — needs your OK')).toBeTruthy();
    expect(workHeadline({ phase: 'done', accepted: 1, total: 1, verdict: 'VERIFIED' })).toBe(WORK_WORDS.VERIFIED.label);
    expect(workHeadline({ phase: 'done', accepted: 1, total: 1, verdict: 'UNCERTAIN' })).toBe(WORK_WORDS.UNCHECKED.label);
    expect(workHeadline({ phase: 'needs_you', accepted: 0, total: 1, verdict: null })).toBe(WORK_WORDS.AWAITING_USER.label);
    expect(workHeadline({ phase: 'stopped', accepted: 0, total: 1, verdict: null })).toBe(WORK_WORDS.CANCELLED.label);
  });
});

describe('Activity — each job in exactly one section', () => {
  it('places every job once, paused only under "Waiting on you", unchecked under "Recently finished"', async () => {
    renderAt('/activity', <Activity />);
    await screen.findByText('Summarize the meeting notes');
    const section = (title: string) => screen.getByRole('heading', { name: title }).closest('section') as HTMLElement;
    const now = section('Happening now');
    const waiting = section('Waiting on you');
    const finished = section('Recently finished');

    for (const entry of JOBS) {
      const rows = document.querySelectorAll(`[data-job-id="${entry.id}"]`);
      expect(rows, entry.id).toHaveLength(1);
    }
    expect(within(now).getByText('Summarize the meeting notes')).toBeTruthy();
    expect(within(now).getByText('Translate the letter')).toBeTruthy();
    expect(within(waiting).getByText('Rename the holiday photos')).toBeTruthy();
    expect(within(waiting).getByText('Book the dentist')).toBeTruthy();
    expect(within(waiting).getByText('Tidy the downloads folder')).toBeTruthy();
    expect(within(now).queryByText('Rename the holiday photos')).toBeNull();
    expect(within(finished).getByText('Draft the garden plan')).toBeTruthy();
    expect(within(waiting).queryByText('Draft the garden plan')).toBeNull();

    const words = (id: string) =>
      (document.querySelector(`[data-job-id="${id}"] [data-testid="activity-state"]`) as HTMLElement).textContent;
    expect(words('ok')).toMatch(/^Done and checked — /);
    expect(words('meh')).toMatch(/^Finished — not fully checked — /);
    expect(words('bad')).toMatch(/^Didn't pass its checks — /);
    expect(words('paused')).toMatch(/^Paused — /);
  });

  it('highlights the job a work card pointed at', async () => {
    renderAt('/activity?job=meh', <Activity />);
    await screen.findByText('Draft the garden plan');
    const row = document.querySelector('[data-job-id="meh"]') as HTMLElement;
    expect(row.getAttribute('aria-current')).toBe('true');
    expect(row.className).toContain('kel-work-focus');
  });

  it('highlights a waiting job on Activity when its chat is not on this device', async () => {
    renderAt('/activity', <Activity />);
    await screen.findByText('Book the dentist');
    fireEvent.click(screen.getByRole('button', { name: 'Open the chat for Book the dentist' }));
    expect((await screen.findByTestId('where')).textContent).toBe('/activity?job=ask');
  });
});

describe('Home "Needs you" — same words, named jobs', () => {
  it('names every job by its title in the shared words and never says "a paused task"', async () => {
    renderAt('/guid', <KelResumptionBrief />);
    const card = await screen.findByTestId('resumption-brief');
    const text = card.textContent ?? '';
    expect(text).not.toMatch(/a paused task/i);
    expect(text).toContain('Book the dentist — Waiting for your OK');
    expect(text).toContain('Rename the holiday photos — Paused');
    expect(text).toContain('Draft the garden plan — Finished — not fully checked');
    expect(text).toContain('Write the weekly summary — Done and checked');
    // Unchecked or failed results are not "waiting on you".
    expect(text).not.toContain('needs a human eye');
    fireEvent.click(within(card).getByText(/Book the dentist/));
    expect((await screen.findByTestId('where')).textContent).toBe('/activity?job=ask');
  });
});

describe('Activity keeps what the retired Work page offered (D-70)', () => {
  it('pauses running work right away without a reload, and resumes paused work', async () => {
    renderAt('/activity', <Activity />);
    await screen.findByText('Summarize the meeting notes');
    // Stop stays on the work card (confirmed there); Activity offers no unconfirmed Stop.
    expect(screen.queryByRole('button', { name: /^Stop/ })).toBeNull();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Pause Summarize the meeting notes' }));
    });
    expect(request).toHaveBeenCalledWith('/api/control', { job: 'run', action: 'pause' });
    expect(await screen.findByText('Kel is pausing this.')).toBeTruthy();
    const section = (title: string) => screen.getByRole('heading', { name: title }).closest('section') as HTMLElement;
    await waitFor(() => expect(within(section('Waiting on you')).getByText('Summarize the meeting notes')).toBeTruthy());

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Resume Rename the holiday photos' }));
    });
    expect(request).toHaveBeenCalledWith('/api/control', { job: 'paused', action: 'resume' });
  });

  it('drafts a recipe from finished work and saves it only on confirmation', async () => {
    request.mockImplementation(async (route: string, body?: { action?: string }) => {
      if (route.startsWith('/api/state')) return { jobs: JOBS, routes: {}, providers: [], projects: [] };
      if (route === '/api/recipes' && body?.action === 'propose_from_job') {
        return { recipe: { name: 'Weekly summary' }, preview: { steps: ['Gather notes', 'Write summary'], kind: 'writing', milestones: 2 } };
      }
      if (route === '/api/recipes' && body?.action === 'save') return { saved: true, digest: 'x' };
      return {};
    });
    renderAt('/activity', <Activity />);
    await screen.findByText('Write the weekly summary');
    // One "Save as a recipe" per finished, closed job (JR-29), never on running work.
    expect(screen.queryByRole('button', { name: 'Save Summarize the meeting notes as a recipe' })).toBeNull();
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Save Write the weekly summary as a recipe' }));
    });
    const draft = await screen.findByRole('group', { name: 'Save Write the weekly summary as a recipe' });
    expect(draft.textContent).toContain('It is saved only when you confirm.');
    expect(draft.textContent).toContain('Gather notes · Write summary');
    expect(request.mock.calls.some(([route, body]) => route === '/api/recipes' && body?.action === 'save')).toBe(false);
    await act(async () => {
      fireEvent.click(within(draft).getByRole('button', { name: 'Save recipe' }));
    });
    expect(request).toHaveBeenCalledWith('/api/recipes', expect.objectContaining({ action: 'save', confirm: true, conversation: 'engine-ok' }));
    expect(await screen.findByText('Saved as a recipe. It is in Recipes.')).toBeTruthy();
  });

  it('says what happened when a pause fails, and changes nothing', async () => {
    request.mockImplementation(async (route: string) => {
      if (route.startsWith('/api/state')) return { jobs: JOBS, routes: {}, providers: [], projects: [] };
      if (route === '/api/control') throw new Error('That work already finished.');
      return {};
    });
    renderAt('/activity', <Activity />);
    await screen.findByText('Summarize the meeting notes');
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Pause Summarize the meeting notes' }));
    });
    expect(await screen.findByText("Pause didn't go through, so nothing changed. That work already finished.")).toBeTruthy();
    const section = (title: string) => screen.getByRole('heading', { name: title }).closest('section') as HTMLElement;
    expect(within(section('Happening now')).getByText('Summarize the meeting notes')).toBeTruthy();
  });
});
