import { describe, expect, it } from 'vitest';
import {
  detailStateLabel,
  fitCards,
  initials,
  modelLine,
  orderItems,
  overflowWidth,
  progressFraction,
  ringTone,
  stepCount,
} from '@renderer/components/kel/workCards/workCardModel';
import type { OfficeItem, OfficeStaff } from '@renderer/components/kel/workCards/officeApi';

const item = (job: string, state: OfficeItem['state'], order?: number): OfficeItem => ({ job_id: job, title: job, state, ...(order === undefined ? {} : { order }) });

describe('work card rules (D-68)', () => {
  it('fits every card when they fit, otherwise as many as fit beside "+N more"', () => {
    // Figma 4a: 920 wide holds four 198px cards and the 88px control.
    expect(fitCards(920, 4)).toBe(4);
    expect(fitCards(920, 6)).toBe(4);
    expect(fitCards(1022, 5)).toBe(5);
    expect(fitCards(1021, 5)).toBe(4);
    expect(fitCards(300, 3)).toBe(1);
    expect(fitCards(80, 3)).toBe(0);
    expect(fitCards(0, 3)).toBe(0);
    expect(fitCards(920, 0)).toBe(0);
  });

  it('grows the overflow control with its dots and caps them', () => {
    expect(overflowWidth(2)).toBe(88);
    expect(overflowWidth(5)).toBe(18 + 5 * 16 + 4 * 2);
    expect(overflowWidth(40)).toBe(overflowWidth(8));
  });

  it('orders running and needs-you work first, finished last, keeping the engine order within each', () => {
    const ordered = orderItems([item('a', 'done'), item('b', 'working'), item('c', 'failed'), item('d', 'needs_you'), item('e', 'stopped'), item('f', 'in_review')]);
    expect(ordered.map((row) => row.job_id)).toEqual(['b', 'd', 'f', 'a', 'c', 'e']);
    const explicit = orderItems([item('a', 'working', 2), item('b', 'done', 0), item('c', 'working', 1)]);
    expect(explicit.map((row) => row.job_id)).toEqual(['b', 'c', 'a']);
  });

  it('never invents progress', () => {
    expect(stepCount({ progress: { done: 3, total: 5 } })).toBe('3 of 5');
    expect(stepCount({ progress: { done: 0, total: 0 } })).toBeNull();
    expect(stepCount({ progress: null })).toBeNull();
    expect(progressFraction({ progress: { done: 3, total: 5 } })).toBe(0.6);
    expect(progressFraction({ progress: null })).toBe(0);
  });

  it('says what model ran, and plainly when it differs from what was asked or is unconfirmed', () => {
    const base: OfficeStaff = { id: '1', role: 'builder', model_label: 'Claude Opus 5.5', model_confirmed: true, reasoning: 'high' };
    expect(modelLine(base)).toBe('Claude Opus 5.5 · High');
    expect(modelLine({ ...base, version: '2.1.215' })).toBe('Claude Opus 5.5 2.1.215 · High');
    expect(modelLine({ ...base, model_label: 'Claude Opus 4.8', asked: { model_label: 'Claude Opus 5.5' } })).toBe(
      'Asked for Claude Opus 5.5 · ran Claude Opus 4.8 · High'
    );
    expect(modelLine({ ...base, model_confirmed: false, asked: { model_label: 'Claude Opus 5.5', reasoning: 'xhigh' } })).toBe(
      'Asked for Claude Opus 5.5 · Extra high · not confirmed yet'
    );
    expect(modelLine({ id: '2', role: 'utility' })).toBe('Model not reported yet');
  });

  it('gives each member initials and a ring that follows its state', () => {
    expect(initials({ role: 'builder', role_label: 'Builder' })).toBe('Bu');
    expect(initials({ role: 'oracle' })).toBe('Or');
    expect(ringTone({ role: 'builder', state: 'working' }, 'working')).toBe('working');
    expect(ringTone({ role: 'verifier', state: 'working' }, 'working')).toBe('review');
    expect(ringTone({ role: 'discovery', state: 'waiting' }, 'needs_you')).toBe('needs');
    expect(ringTone({ role: 'builder', state: 'done' }, 'working')).toBe('done');
    expect(ringTone({ role: 'builder', state: 'failed' }, 'failed')).toBe('failed');
  });

  it('says "Done and checked" only when the checks passed', () => {
    expect(detailStateLabel({ state: 'done', verification: { result: 'passed' } })).toBe('Done and checked');
    expect(detailStateLabel({ state: 'done', review: { verdict: 'VERIFIED' } })).toBe('Done and checked');
    expect(detailStateLabel({ state: 'done', verification: { result: 'not_run' } })).toBe('Done');
    expect(detailStateLabel({ state: 'failed' })).toBe('Failed');
  });
});
