import { describe, expect, it } from 'vitest';
import { selectedWorkJob, currentWorkStep, workContinuationInstruction } from '@renderer/components/kel/workViewState';
import type { KelWorkJob } from '@renderer/components/kel/kelApi';

describe('Work detail selection', () => {
  const jobs: KelWorkJob[] = [{ id: 'old', state: 'CANCELLED' }, { id: 'waiting', state: 'AWAITING_USER' }, { id: 'active', state: 'RUNNING' }];
  it('shows active work despite older stopped rows', () => expect(selectedWorkJob(jobs, null)?.id).toBe('active'));
  it('keeps an explicit waiting or stopped selection', () => {
    expect(selectedWorkJob(jobs, 'waiting')?.id).toBe('waiting');
    expect(selectedWorkJob(jobs, 'old')?.id).toBe('old');
  });
  it('recovers from a removed selection and empty results', () => {
    expect(selectedWorkJob(jobs, 'removed')?.id).toBe('active');
    expect(selectedWorkJob([], 'removed')).toBeNull();
    expect(selectedWorkJob(jobs.slice(0, 2), null)?.id).toBe('waiting');
  });
  it('reads the running step after an accepted earlier step', () => {
    const job: KelWorkJob = { id: 'active', state: 'RUNNING', contract: { milestones: [{ id: 'first', objective: 'Inspect' }, { id: 'second', objective: 'Draft' }] }, milestones: { first: { state: 'ACCEPTED' }, second: { state: 'RUNNING' } } };
    expect(currentWorkStep(job)).toBe('Draft');
    expect(currentWorkStep({ id: 'empty', state: 'QUEUED' })).toBe('—');
  });
  it('does not ask someone to restart running work or bypass an approval', () => {
    expect(workContinuationInstruction(jobs[2])).toBe('This work is still running.');
    expect(workContinuationInstruction(jobs[1])).toBe('Answer the permission request above to continue.');
  });
  it('distinguishes model routing from an interrupted run', () => {
    expect(workContinuationInstruction({ id: 'route', state: 'WAITING_RESOURCE', route_block: 'unavailable' })).toBe('Kel will continue when a model is available.');
    expect(workContinuationInstruction({ id: 'interrupted', state: 'WAITING_RESOURCE' })).toContain('reply “continue”');
  });
});
