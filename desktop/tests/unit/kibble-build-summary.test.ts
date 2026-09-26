import { expect, it } from 'vitest';
import { kibbleBuildSummary } from '@renderer/components/kel/kibbleBuildSummary';
it('shows the reported running step rather than a completed first step', () => {
 expect(kibbleBuildSummary({ state: 'RUNNING', milestones: { prepare: { state: 'DONE' }, build: { state: 'RUNNING' }, test: { state: 'QUEUED' }, review: { state: 'QUEUED' } } })).toEqual({ text: 'Running · step 2 of 4', running: true, stage: 'Building' });
});
it('does not invent step counts when a running job has no milestone evidence', () => {
 expect(kibbleBuildSummary({ state: 'RUNNING' })).toEqual({ text: 'Running', running: true, stage: 'Building' });
});
it('reports cancellation even when stale milestone data still says Running', () => {
 expect(kibbleBuildSummary({ state: 'CANCELLED', milestones: { build: { state: 'RUNNING' } } })).toEqual({ text: 'Cancelled', running: false, stage: null });
});
it('keeps route and user waits distinct and reports a finished job plainly', () => {
 for (const [state, text] of [['WAITING_RESOURCE', 'Waiting for a model'], ['AWAITING_USER', 'Waiting on you'], ['CLOSED', 'Finished']]) expect(kibbleBuildSummary({ state }).text).toBe(text);
});
