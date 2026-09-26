import type { KelWorkJob } from './kelApi';

/** Keep an explicit choice; otherwise show work that still needs attention. */
export function selectedWorkJob(jobs: KelWorkJob[], selected: string | null): KelWorkJob | null {
  return jobs.find(job => job.id === selected)
    ?? jobs.find(job => job.state === 'RUNNING')
    ?? jobs.find(job => !['CLOSED', 'CANCELLED'].includes(job.state))
    ?? jobs[0]
    ?? null;
}

/** Read the runtime step instead of always repeating the first contract step. */
export function currentWorkStep(job: KelWorkJob): string {
  const steps = job.contract?.milestones ?? [];
  const running = steps.find(step => job.milestones?.[step.id]?.state === 'RUNNING');
  const unfinished = steps.find(step => !['ACCEPTED', 'CANCELLED'].includes(job.milestones?.[step.id]?.state ?? ''));
  return (running ?? unfinished ?? steps.at(-1))?.objective ?? '—';
}

export function workContinuationInstruction(job?: KelWorkJob): string {
  if (job?.state === 'RUNNING') return 'This work is still running.';
  if (job?.state === 'AWAITING_USER') return 'Answer the permission request above to continue.';
  if (job?.state === 'WAITING_RESOURCE' && job.route_block) return 'Kel will continue when a model is available.';
  return 'To continue, reply “continue” (or pick a number) in the chat — Kel never resumes on its own.';
}
