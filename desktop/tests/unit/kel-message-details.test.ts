/**
 * CH-2/CP-14: the engine's message details (`meta` on /api/state messages) reach the chat rows the
 * desktop reconciles — on recovered rows directly, and on streamed rows through an overlay that
 * stands in for them — so the chat can show them behind "Details".
 */
import { describe, expect, it } from 'vitest';
import { historyRow, recoverHistory, type HistoryMessage } from '@process/services/kel/reconcileHistory';
import { loadKelHistoryPage } from '@renderer/utils/chat/kelHistory';
import { shownKelMeta } from '@/common/chat/kelMessageMeta';
import type { TMessage } from '@/common/chat/chatLib';

const result = {
  kind: 'result',
  verdict: 'VERIFIED',
  checks: [{ kind: 'min_chars', verdict: 'VERIFIED' }],
  executed_by: [{ provider: 'claude-code', model: null, label: 'Claude Code' }],
  reviewed_by: [],
  summary: ['Verified'],
};
const stopped = { kind: 'stopped', submission: 'acp-2' };
const answered = { answered_by: { provider: 'claude-code', label: 'Claude', model: null } };
const fellBack = {
  ...answered,
  fallback_from: { provider: 'deepseek', label: 'DeepSeek', model: null, note: 'Not supported for chat yet' },
};

const nativeText = (id: string, text: string, position = 'left'): HistoryMessage => ({
  id,
  msg_id: id,
  type: 'text',
  position,
  conversation_id: 'donor',
  created_at: 1,
  content: { content: text },
});

describe('shownKelMeta', () => {
  it('keeps results, fallbacks and notes, and nothing else', () => {
    expect(shownKelMeta(result)).toEqual(result);
    expect(shownKelMeta(stopped)).toEqual(stopped);
    expect(shownKelMeta(fellBack)).toEqual(fellBack);
    expect(shownKelMeta(answered)).toBeNull();
    expect(shownKelMeta(null)).toBeNull();
    expect(shownKelMeta('text')).toBeNull();
  });
});

describe('recoverHistory with message details', () => {
  it('puts the details on a recovered result row', () => {
    const rows = recoverHistory('donor', [], [{ seq: 5, at: 10, role: 'assistant', text: "Here's your garden plan.", meta: result }], []);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ id: 'kel-history-5', content: { content: "Here's your garden plan.", kel_meta: result } });
  });

  it('leaves ordinary replies without details', () => {
    const row = historyRow('donor', { seq: 6, at: 1, role: 'assistant', text: 'Sure.', meta: answered });
    expect(row.content).toEqual({ content: 'Sure.' });
  });

  it('adds details to a row recovered before the engine recorded them', () => {
    const before = recoverHistory('donor', [], [{ seq: 5, at: 10, role: 'assistant', text: 'Done.' }], []);
    const after = recoverHistory('donor', before, [{ seq: 5, at: 10, role: 'assistant', text: 'Done.', meta: result }], []);
    expect(after).toHaveLength(1);
    expect(after[0].content.kel_meta).toEqual(result);
  });

  it('overlays a streamed row with its details, once, however often it reconciles', () => {
    const native = [nativeText('n-1', 'Write a plan', 'right'), nativeText('n-2', "Here's your garden plan.\n\n")];
    const messages = [
      { seq: 1, at: 1, role: 'user', text: 'Write a plan' },
      { seq: 2, at: 2, role: 'assistant', text: "Here's your garden plan.", meta: result },
    ];
    const once = recoverHistory('donor', [], messages, native);
    expect(once).toHaveLength(1);
    expect(once[0]).toMatchObject({ id: 'n-2', kel_overlay: true, content: { content: "Here's your garden plan.\n\n", kel_meta: result } });
    const twice = recoverHistory('donor', once, messages, native);
    expect(twice).toEqual(once);
  });

  it('drops an overlay whose streamed row is gone', () => {
    const messages = [{ seq: 2, at: 2, role: 'assistant', text: 'Done.', meta: result }];
    const once = recoverHistory('donor', [], messages, [nativeText('n-2', 'Done.')]);
    const later = recoverHistory('donor', once, messages, []);
    expect(later.some((row) => row.kel_overlay)).toBe(false);
    expect(later).toHaveLength(1);
    expect(later[0].id).toBe('kel-history-2');
  });

  it('marks a streamed stop note as a note only when the row is exactly that note', () => {
    const note = { seq: 3, at: 3, role: 'assistant', text: 'You stopped this reply.', meta: stopped };
    const alone = recoverHistory('donor', [], [note], [nativeText('n-3', 'You stopped this reply.\n\n')]);
    expect(alone[0]).toMatchObject({ id: 'n-3', content: { kel_meta: stopped } });
    const shared = recoverHistory(
      'donor',
      [],
      [{ seq: 2, at: 2, role: 'assistant', text: 'Thinking about it' }, note],
      [nativeText('n-2', 'Thinking about it\n\nYou stopped this reply.')]
    );
    expect(shared).toEqual([]);
  });

  it('prefers the result when one streamed row carries a reply and a result', () => {
    const rows = recoverHistory(
      'donor',
      [],
      [
        { seq: 2, at: 2, role: 'assistant', text: 'Used Claude.', meta: fellBack },
        { seq: 3, at: 3, role: 'assistant', text: 'Here it is.', meta: result },
      ],
      [nativeText('n-2', 'Used Claude.\n\nHere it is.')]
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].content.kel_meta).toEqual(result);
  });
});

describe('chat history page', () => {
  it('shows the overlay in place of the streamed row', async () => {
    const native = nativeText('n-2', 'Done.') as unknown as TMessage;
    const overlay = { ...native, kel_overlay: true, content: { content: 'Done.', kel_meta: result } } as unknown as TMessage;
    const page = await loadKelHistoryPage([overlay], {}, async () => ({
      items: [native],
      oldest_cursor: null,
      newest_cursor: null,
      has_more_before: false,
      has_more_after: false,
    }));
    expect(page.items).toHaveLength(1);
    expect((page.items[0].content as { kel_meta?: unknown }).kel_meta).toEqual(result);
  });
});
