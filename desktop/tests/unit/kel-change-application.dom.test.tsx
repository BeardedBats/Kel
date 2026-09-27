/**
 * D-65 — in Full access a verified coding change is applied on its own: the work card says
 * "Applied automatically" and offers Undo. A change left for Nick keeps "Apply checked changes"
 * (in Work) and the card says why it waited.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCard } from '@renderer/components/kel/KelWorkCard';
import type { KelChangeApplication, KelHandoff } from '@renderer/components/kel/kelApi';
import { applicationLine, canApplyChange, canUndoChange } from '@renderer/components/kel/changeApplication';

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const applied: KelChangeApplication = {
  state: 'APPLIED',
  auto: true,
  decision: 'applied',
  root: 'C:\\Users\\Nick\\Projects\\garden',
  files: 3,
  waiting_reason: null,
};

const done: KelHandoff = {
  submission_id: 'acp-1',
  conversation: 'engine-conversation',
  submission_state: 'DISPATCHED',
  title: 'Fix the watering schedule',
  ack_seq: 4,
  job_id: 'job-1',
  state: 'CLOSED',
  verdict: 'VERIFIED',
  accepted: 1,
  total: 1,
  why: null,
  next: null,
  error: null,
  phase: 'done',
  can_stop: false,
  can_retry: false,
  application: applied,
};

const install = (request: (route: string, body?: unknown) => Promise<unknown>) => {
  const spy = vi.fn(request);
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    conversation: vi.fn(async () => 'engine-conversation'),
    request: spy,
  };
  return spy;
};

const renderCard = () =>
  render(
    <MemoryRouter>
      <KelWorkCard submissionId='acp-1' conversationId='host-conversation' pollMs={20} />
    </MemoryRouter>
  );

describe('an automatically applied change on the work card (D-65)', () => {
  it('says it was applied, where, and offers Undo that calls the engine', async () => {
    let view: KelHandoff = done;
    const request = install(async (route, body) => {
      if (route === '/api/apply') {
        view = { ...done, application: { ...applied, state: 'UNDONE' } };
        return { state: 'UNDONE', files: 3, body };
      }
      return view;
    });
    renderCard();
    const line = await screen.findByTestId('kel-work-application');
    expect(line.textContent).toBe(
      'Applied automatically to C:\\Users\\Nick\\Projects\\garden (3 files). The earlier files are saved.'
    );
    expect(screen.getByText('Done and checked')).toBeTruthy();
    fireEvent.click(screen.getByTestId('kel-work-undo'));
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/apply', { job: 'job-1', action: 'undo' }));
    await waitFor(() =>
      expect(screen.getByTestId('kel-work-application').textContent).toBe('Undone — the earlier files are back.')
    );
    expect(screen.queryByTestId('kel-work-undo')).toBeNull();
  });

  it('shows why a change waited in Full access, with no Undo', async () => {
    install(async () => ({
      ...done,
      application: { state: null, auto: false, decision: 'waiting', root: null, files: null,
        waiting_reason: 'it would change your credentials folder' },
    }));
    renderCard();
    const line = await screen.findByTestId('kel-work-application');
    expect(line.textContent).toBe(
      'Waiting for you: Kel did not apply it on its own — it would change your credentials folder.'
    );
    expect(screen.queryByTestId('kel-work-undo')).toBeNull();
  });

  it('says nothing extra under Ask first (the Apply button in Work is the way)', async () => {
    install(async () => ({
      ...done,
      application: { state: null, auto: false, decision: 'waiting', root: null, files: null, waiting_reason: null },
    }));
    renderCard();
    expect(await screen.findByText('Done and checked')).toBeTruthy();
    expect(screen.queryByTestId('kel-work-application')).toBeNull();
    expect(screen.queryByTestId('kel-work-undo')).toBeNull();
  });

  it('never offers Undo before the work is done', async () => {
    install(async () => ({ ...done, phase: 'running', state: 'CLOSED' }));
    renderCard();
    expect(await screen.findByText('Working on it · 1 of 1 parts checked')).toBeTruthy();
    expect(screen.queryByTestId('kel-work-undo')).toBeNull();
  });
});

describe('Apply or Undo in Work (D-65)', () => {
  const coding = { verdict: 'VERIFIED', contract: { kind: 'coding' } };

  it('keeps Apply for a verified change that is not in the project, and swaps it for Undo once applied', () => {
    expect(canApplyChange({ ...coding, application: null })).toBe(true);
    expect(canUndoChange({ ...coding, application: null })).toBe(false);
    expect(canApplyChange({ ...coding, application: applied })).toBe(false);
    expect(canUndoChange({ ...coding, application: applied })).toBe(true);
    // Undone: it can be applied again.
    expect(canApplyChange({ ...coding, application: { ...applied, state: 'UNDONE' } })).toBe(true);
  });

  it('never offers Apply for a change that failed or skipped its checks', () => {
    expect(canApplyChange({ verdict: 'FAILED', contract: { kind: 'coding' } })).toBe(false);
    expect(canApplyChange({ verdict: 'UNCERTAIN', contract: { kind: 'coding' } })).toBe(false);
    expect(canApplyChange({ verdict: 'VERIFIED', contract: { kind: 'writing' } })).toBe(false);
  });

  it('names a change you applied yourself without calling it automatic', () => {
    expect(applicationLine({ ...applied, auto: false, files: 1 })).toBe(
      'Applied to C:\\Users\\Nick\\Projects\\garden (1 file). The earlier files are saved.'
    );
  });
});
