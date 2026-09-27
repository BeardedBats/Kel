import { describe, expect, it } from 'vitest';
import { KEL_POLL_ACTIVE_MS, KEL_POLL_IDLE_MS, nextPollDelay } from '@/common/chat/kelWork';

describe('Kel durable-work poll cadence', () => {
  it('polls quickly while any job is open', () => {
    expect(nextPollDelay({ jobs: [{ state: 'CLOSED' }, { state: 'RUNNING' }], submissions: [] })).toBe(
      KEL_POLL_ACTIVE_MS);
    expect(nextPollDelay({ jobs: [{ state: 'WAITING_RESOURCE' }] })).toBe(2500);
  });

  it('polls quickly while a hand-off is still being started', () => {
    expect(nextPollDelay({ jobs: [{ state: 'CLOSED' }], submissions: [{ state: 'PLANNING' }] })).toBe(2500);
  });

  it('slows down, but never stops, once everything has settled', () => {
    expect(nextPollDelay({ jobs: [{ state: 'CLOSED' }, { state: 'CANCELLED' }],
      submissions: [{ state: 'SETTLED' }, { state: 'DISPATCHED' }] })).toBe(KEL_POLL_IDLE_MS);
    expect(nextPollDelay({ jobs: [], submissions: [] })).toBe(10000);
    expect(nextPollDelay(undefined)).toBe(10000);
    expect(nextPollDelay({ jobs: null, submissions: null })).toBe(10000);
  });
});
