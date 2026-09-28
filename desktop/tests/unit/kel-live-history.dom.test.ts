/**
 * LIVE-7: a message with details (a scoping card, a result) reaches an open chat at once. The main
 * process watches the engine for such messages and tells the windows which app chats changed; the
 * renderer subscribes through `onKelHistoryUpdated`.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { donorsForMessages } from '@/process/services/kel/reconcileHistory';
import { onKelHistoryUpdated } from '@/renderer/components/kel/kelApi';

describe('donorsForMessages', () => {
  it('names every app chat whose engine conversation gained a detailed message', () => {
    const mapping = { donorA: 'conv-1', donorB: 'conv-2', donorC: 'conv-1' };
    expect(donorsForMessages(mapping, [{ conversation_id: 'conv-1' }]).toSorted()).toEqual(['donorA', 'donorC']);
    expect(donorsForMessages(mapping, [{ conversation_id: 'conv-9' }, { conversation_id: 42 }])).toEqual([]);
    expect(donorsForMessages(mapping, undefined)).toEqual([]);
  });
});

describe('onKelHistoryUpdated', () => {
  afterEach(() => {
    delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  });

  it('passes the app conversation id through and unsubscribes', () => {
    let emit: ((update: { conversationId: string }) => void) | undefined;
    const off = vi.fn();
    (window as unknown as { kelAPI: unknown }).kelAPI = {
      onHistoryUpdated: (callback: (update: { conversationId: string }) => void) => {
        emit = callback;
        return off;
      },
    };
    const seen: string[] = [];
    const stop = onKelHistoryUpdated((id) => seen.push(id));
    emit?.({ conversationId: 'donorA' });
    emit?.({ conversationId: 7 as unknown as string });
    expect(seen).toEqual(['donorA']);
    stop();
    expect(off).toHaveBeenCalledOnce();
  });

  it('is a no-op without the desktop bridge', () => {
    expect(onKelHistoryUpdated(() => undefined)()).toBeUndefined();
  });
});
