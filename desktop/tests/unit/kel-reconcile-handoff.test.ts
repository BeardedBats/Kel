import { describe, expect, it } from 'vitest';
import { ensureWorkCards, type HistoryMessage } from '@process/services/kel/reconcileHistory';

const messages = [
  { seq: 1, at: 100, role: 'user', text: 'Write a garden plan' },
  { seq: 2, at: 101, role: 'assistant', text: 'On it.' },
];
const submission = { id: 'acp-1', state: 'DISPATCHED', ack_seq: 2, title: 'Garden plan' };

const nativeCard = (id: string): HistoryMessage => ({
  id: 'native-row',
  msg_id: 'native-row',
  type: 'acp_tool_call',
  position: 'left',
  conversation_id: 'donor',
  created_at: 101500,
  content: { update: { tool_call_id: id, status: 'pending', title: 'Working on it in the background' } },
});

describe('ensureWorkCards', () => {
  it('adds one card right after the acknowledgement when none was streamed', () => {
    const out = ensureWorkCards([], [submission], [], 'donor', messages);
    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({
      id: 'kel-work-acp-1',
      type: 'acp_tool_call',
      position: 'left',
      conversation_id: 'donor',
      created_at: 101001,
      content: { update: { tool_call_id: 'kel-work:acp-1', status: 'pending' } },
    });
  });

  it('adds it exactly once across repeated reconciles', () => {
    const once = ensureWorkCards([], [submission], [], 'donor', messages);
    const twice = ensureWorkCards(once, [submission], [], 'donor', messages);
    expect(twice).toHaveLength(1);
    expect(ensureWorkCards([], [submission, submission], [], 'donor', messages)).toHaveLength(1);
  });

  it('never duplicates a card the live stream already stored', () => {
    expect(ensureWorkCards([], [submission], [nativeCard('kel-work:acp-1')], 'donor', messages)).toEqual([]);
  });

  it('ignores submissions that were not handed off and other tool calls', () => {
    const plain = { id: 'acp-2', state: 'SETTLED', ack_seq: null, title: null };
    const out = ensureWorkCards([], [plain, submission], [nativeCard('job-123')], 'donor', messages);
    expect(out.map((row) => row.id)).toEqual(['kel-work-acp-1']);
  });

  it('keeps the rows it was given', () => {
    const text: HistoryMessage = {
      id: 'kel-history-3', msg_id: 'kel-history-3', type: 'text', position: 'left',
      conversation_id: 'donor', created_at: 200000, content: { content: 'Here is the result' },
    };
    const out = ensureWorkCards([text], [submission], [], 'donor', messages);
    expect(out[0]).toBe(text);
    expect(out).toHaveLength(2);
  });
});
