import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useSearchParams } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCard, workHeadline } from '@renderer/components/kel/KelWorkCard';
import type { KelHandoff } from '@renderer/components/kel/kelApi';

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const base: KelHandoff = {
  submission_id: 'acp-1',
  conversation: 'engine-conversation',
  submission_state: 'DISPATCHED',
  title: 'Garden plan for spring',
  ack_seq: 4,
  job_id: 'job-1',
  state: 'RUNNING',
  verdict: null,
  accepted: 1,
  total: 3,
  why: null,
  next: null,
  error: null,
  phase: 'running',
  can_stop: true,
  can_retry: false,
};

type Request = (route: string, body?: unknown) => Promise<unknown>;

const install = (request: Request) => {
  const spy = vi.fn(request);
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    conversation: vi.fn(async () => 'engine-conversation'),
    request: spy,
  };
  return spy;
};

const ActivityProbe = () => {
  const [params] = useSearchParams();
  return <div data-testid='activity-page'>{`Activity ${params.get('job') ?? ''}`}</div>;
};

const renderCard = (pollMs = 20) =>
  render(
    <MemoryRouter initialEntries={['/conversation/host']}>
      <Routes>
        <Route
          path='/conversation/host'
          element={<KelWorkCard submissionId='acp-1' conversationId='host-conversation' pollMs={pollMs} />}
        />
        <Route path='/activity' element={<ActivityProbe />} />
      </Routes>
    </MemoryRouter>
  );

describe('Kel work card', () => {
  it('reads the engine hand-off for its own conversation and shows progress', async () => {
    const request = install(async () => base);
    renderCard();
    expect((await screen.findByText('Working on it · 1 of 3 parts checked')).textContent).toBeTruthy();
    expect(screen.getByTestId('kel-work-title').textContent).toBe('Garden plan for spring');
    expect(request).toHaveBeenCalledWith('/api/handoff?conversation=engine-conversation&submission=acp-1', undefined);
  });

  it('keeps polling until the work settles, and only a VERIFIED result is "Done and checked"', async () => {
    const views: KelHandoff[] = [
      { ...base, phase: 'starting', job_id: null, state: null, submission_state: 'PLANNING', accepted: 0, total: 0 },
      base,
      { ...base, phase: 'done', state: 'CLOSED', verdict: 'VERIFIED', accepted: 3, can_stop: false },
    ];
    let index = 0;
    const request = install(async () => views[Math.min(index++, views.length - 1)]);
    renderCard();
    expect(await screen.findByText('Getting started…')).toBeTruthy();
    expect(await screen.findByText('Done and checked')).toBeTruthy();
    const calls = request.mock.calls.length;
    await new Promise((done) => setTimeout(done, 80));
    expect(request.mock.calls.length).toBe(calls);
    expect(screen.queryByTestId('kel-work-stop')).toBeNull();
    expect(screen.getByTestId('kel-work-card').getAttribute('data-phase')).toBe('done');
  });

  it('never claims done for an unverified finish, and names what needs attention', async () => {
    install(async () => ({ ...base, phase: 'needs_look', state: 'CLOSED', verdict: 'UNCERTAIN', can_stop: false,
      why: 'Kel could not fully verify the result.' }));
    renderCard();
    expect(await screen.findByText('Finished — not fully checked')).toBeTruthy();
    expect(screen.getByTestId('kel-work-why').textContent).toBe('Kel could not fully verify the result.');
    expect(screen.queryByText('Done and checked')).toBeNull();
    expect(workHeadline({ phase: 'done', accepted: 1, total: 1, verdict: 'UNCERTAIN' })).toBe(
      'Finished — not fully checked');
    expect(workHeadline({ phase: 'done', accepted: 0, total: 1, verdict: 'FAILED' })).toBe("Didn't pass its checks");
    expect(workHeadline({ phase: 'needs_you', accepted: 0, total: 1, verdict: null })).toBe('Waiting for your OK');
    expect(workHeadline({ phase: 'stopped', accepted: 0, total: 1, verdict: null })).toBe('Stopped');
  });

  it('asks before stopping and then cancels through the engine control route', async () => {
    let stopped = false;
    const request = install(async (route) => {
      if (route === '/api/control') {
        stopped = true;
        return { ok: true };
      }
      return stopped ? { ...base, phase: 'stopped', state: 'CANCELLED', can_stop: false } : base;
    });
    renderCard(10000);
    fireEvent.click(await screen.findByTestId('kel-work-stop'));
    expect(screen.getByTestId('kel-work-confirm').textContent).toContain('Stop this work?');
    expect(request.mock.calls.some(([route]) => route === '/api/control')).toBe(false);
    fireEvent.click(screen.getByTestId('kel-work-stop-confirm'));
    await waitFor(() => expect(screen.getByText('Stopped')).toBeTruthy());
    expect(request).toHaveBeenCalledWith('/api/control', { job: 'job-1', action: 'cancel' });
  });

  it('keeps going when the stop is not confirmed', async () => {
    const request = install(async () => base);
    renderCard(10000);
    fireEvent.click(await screen.findByTestId('kel-work-stop'));
    fireEvent.click(screen.getByTestId('kel-work-keep'));
    expect(screen.getByTestId('kel-work-stop')).toBeTruthy();
    expect(request.mock.calls.some(([route]) => route === '/api/control')).toBe(false);
  });

  it('offers Retry after a start failure and starts polling again', async () => {
    let retried = false;
    const request = install(async (route) => {
      if (route === '/api/retry') {
        retried = true;
        return { id: 'acp-1' };
      }
      return retried
        ? base
        : { ...base, phase: 'failed_to_start', job_id: null, state: null, submission_state: 'FAILED',
            error: 'No planner is available right now', can_stop: false, can_retry: true };
    });
    renderCard();
    expect(await screen.findByText('Couldn’t get started')).toBeTruthy();
    expect(screen.getByTestId('kel-work-why').textContent).toBe('No planner is available right now');
    fireEvent.click(screen.getByTestId('kel-work-retry'));
    expect(await screen.findByText('Working on it · 1 of 3 parts checked')).toBeTruthy();
    expect(request).toHaveBeenCalledWith('/api/retry', { id: 'acp-1' });
  });

  it('opens Activity focused on this job', async () => {
    install(async () => base);
    renderCard(10000);
    await screen.findByText('Working on it · 1 of 3 parts checked');
    fireEvent.click(await screen.findByTestId('kel-work-activity'));
    expect((await screen.findByTestId('activity-page')).textContent).toBe('Activity job-1');
  });
});
