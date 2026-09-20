/**
 * D5 — attention notification core: transitions only, meaningful kinds, cooldown, per-tick cap.
 */
import { describe, expect, it } from 'vitest';
import {
  diffAttentionEvents,
  diffFinishedEvents,
  emptyAttentionNotificationState,
  MAX_EVENTS_PER_TICK,
  NOTIFICATION_COOLDOWN_MS,
  type AttentionNotificationState,
} from '@renderer/hooks/system/notification/attentionNotificationCore';
import type { AttentionItem } from '@renderer/components/kel/needsAttention';

const item = (over: Partial<AttentionItem> & { id: string; kind: AttentionItem['kind'] }): AttentionItem => ({
  title: 'An approval is waiting',
  detail: 'Tidy the notes — Kel is holding until you decide.',
  action: { label: 'Open the chat', to: '/conversation/conv-a' },
  at: 100,
  ...over,
});

const baseline = (state: AttentionNotificationState, items: AttentionItem[], now: number): AttentionNotificationState =>
  diffAttentionEvents(state, items, now).state;

describe('diffAttentionEvents', () => {
  it('stays silent for the first snapshot (baseline only)', () => {
    const first = diffAttentionEvents(emptyAttentionNotificationState(), [item({ id: 'approval-j1', kind: 'approval' })], 1000);
    expect(first.events).toEqual([]);
    expect(first.state.initialized).toBe(true);
  });

  it('notifies only for NEW meaningful kinds, never continuation/stale chatter', () => {
    const state = baseline(emptyAttentionNotificationState(), [item({ id: 'approval-j1', kind: 'approval' })], 1000);
    const next = diffAttentionEvents(
      state,
      [
        item({ id: 'approval-j1', kind: 'approval' }),
        item({ id: 'failure-j2', kind: 'failure', at: 2000 }),
        item({ id: 'continuation-j3', kind: 'continuation' }),
        item({ id: 'stale-continuation-j9', kind: 'stale' }),
      ],
      2000
    );
    expect(next.events.map((event) => event.key)).toEqual(['failure-j2']);
    expect(next.events[0].conversation_id).toBe('conv-a');
  });

  it('re-notifies the same key only after the cooldown (resolved then back)', () => {
    let state = baseline(emptyAttentionNotificationState(), [], 0);
    const first = diffAttentionEvents(state, [item({ id: 'failure-j2', kind: 'failure' })], 1000);
    expect(first.events.map((event) => event.key)).toEqual(['failure-j2']);
    state = first.state;
    state = baseline(state, [], 1500); // resolved
    const early = diffAttentionEvents(state, [item({ id: 'failure-j2', kind: 'failure' })], 2000);
    expect(early.events).toEqual([]);
    const late = diffAttentionEvents(state, [item({ id: 'failure-j2', kind: 'failure' })], 1000 + NOTIFICATION_COOLDOWN_MS + 1);
    expect(late.events.map((event) => event.key)).toEqual(['failure-j2']);
  });

  it('caps events per tick; extras still live on the surface', () => {
    const state = baseline(emptyAttentionNotificationState(), [], 0);
    const many = Array.from({ length: MAX_EVENTS_PER_TICK + 2 }, (_, index) =>
      item({ id: `failure-j${index}`, kind: 'failure' })
    );
    const diff = diffAttentionEvents(state, many, 5000);
    expect(diff.events).toHaveLength(MAX_EVENTS_PER_TICK);
  });

  it('truncates the body to a sane notification length', () => {
    const state = baseline(emptyAttentionNotificationState(), [], 0);
    const diff = diffAttentionEvents(
      state,
      [item({ id: 'failure-long', kind: 'failure', detail: 'x'.repeat(500) })],
      5000
    );
    expect(diff.events[0].body.length).toBeLessThanOrEqual(180);
  });
});

describe('diffFinishedEvents', () => {
  it('is silent on the first snapshot and fires once for new clean finishes', () => {
    const first = diffFinishedEvents(emptyAttentionNotificationState(), [{ id: 'job-1', title: 'Tidy the notes' }], 1000);
    expect(first.events).toEqual([]);
    const next = diffFinishedEvents(first.state, [{ id: 'job-1', title: 'Tidy the notes' }, { id: 'job-2', title: 'Ship the summary', conversation_id: 'conv-b' }], 2000);
    expect(next.events.map((event) => event.key)).toEqual(['finished-job-2']);
    expect(next.events[0].conversation_id).toBe('conv-b');
    expect(next.events[0].body).toContain('Work finished');
  });
});
