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
import Work from '@renderer/pages/kel/work';
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

  it('opens a waiting job on Work with it selected when its chat is not on this device', async () => {
    renderAt('/activity', <Activity />);
    await screen.findByText('Book the dentist');
    fireEvent.click(screen.getByRole('button', { name: 'Open the chat for Book the dentist' }));
    expect((await screen.findByTestId('where')).textContent).toBe('/work?job=ask');
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
    expect((await screen.findByTestId('where')).textContent).toBe('/work?job=ask');
  });
});

describe('Work — plain words, one next step, machinery behind Details', () => {
  it('selects the job from ?job=, keeps steps behind a closed Details, and shows no machinery words', async () => {
    renderAt('/work?job=meh', <Work />);
    const summary = await screen.findByTestId('work-selected-summary');
    expect(summary.textContent).toContain('Kel finished, but could not fully check the result.');
    const selected = screen.getByRole('button', { name: 'Draft the garden plan', pressed: true });
    expect(selected).toBeTruthy();
    const details = screen.getByTestId('work-details') as HTMLDetailsElement;
    expect(details.open).toBe(false);
    const page = document.body.textContent ?? '';
    for (const banned of ['Milestone', 'Worker state', 'Attempts', 'Receipt', 'Team assignments', 'sent to the engine', 'Verification —']) {
      expect(page).not.toContain(banned);
    }
    // One "Save as a recipe" on the surface (JR-29).
    expect(screen.getAllByRole('button', { name: 'Save as a recipe' })).toHaveLength(1);
  });

  it('asks before stopping, and shows a pause right away without a reload', async () => {
    renderAt('/work?job=run', <Work />);
    await screen.findByTestId('work-selected-summary');
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }));
    expect(screen.getByTestId('work-stop-confirm').textContent).toContain('Anything already checked is kept.');
    expect(request.mock.calls.some(([route]) => route === '/api/control')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Keep going' }));
    expect(screen.queryByTestId('work-stop-confirm')).toBeNull();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Pause' }));
    });
    expect(request).toHaveBeenCalledWith('/api/control', { job: 'run', action: 'pause' });
    expect(await screen.findByText('Kel is pausing this.')).toBeTruthy();
    const row = document.querySelector('[data-job-id="run"]') as HTMLElement;
    await waitFor(() => expect(within(row).getByText('Paused')).toBeTruthy());
  });
});
