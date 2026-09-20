/**
 * D5 — desktop notifications for the "Needs your attention" surface (transitions only).
 *
 * Desktop-only. Polls the same authoritative reads the surface uses, diffs against the previous
 * snapshot with the pure core, and hands events to the EXISTING notification bridge
 * (`ipcBridge.notification.show`) — the main process still skips when the window is focused and
 * respects `system.notificationEnabled`, so restraint lives in one place. Failures stay silent:
 * the surface itself reports when state cannot be read, and notifications never invent.
 */
import { useEffect, useRef } from 'react';
import { ipcBridge } from '@/common';
import { isElectronDesktop } from '@/renderer/utils/platform';
import { collectAttention, type AttentionItem } from '@renderer/components/kel/needsAttention';
import { kelAutonomy, kelProviders, kelState, type KelWorkJob } from '@renderer/components/kel/kelApi';
import {
  diffAttentionEvents,
  diffFinishedEvents,
  emptyAttentionNotificationState,
  type AttentionNotificationState,
  type FinishedWork,
} from './attentionNotificationCore';

const POLL_MS = 20_000;

/** Work that ended cleanly (engine CLOSED + VERIFIED) — the good outcome still deserves one word. */
const cleanlyFinished = (jobs: KelWorkJob[]): FinishedWork[] =>
  jobs
    .filter((job) => job.state === 'CLOSED' && (job.verdict || '').toUpperCase() === 'VERIFIED')
    .map((job) => ({
      id: job.id,
      title: job.contract?.request?.trim() || 'Work finished',
      conversation_id: job.conversation,
    }));

export const useKelAttentionNotification = (): void => {
  const stateRef = useRef<AttentionNotificationState>(emptyAttentionNotificationState());

  useEffect(() => {
    if (!isElectronDesktop()) return;
    let disposed = false;

    const tick = async (): Promise<void> => {
      try {
        const [state, boundary, providers] = await Promise.all([
          kelState(),
          kelAutonomy.requests(),
          kelProviders.list().catch((): null => null),
        ]);
        if (disposed) return;
        const items: AttentionItem[] = collectAttention({
          jobs: state.jobs ?? [],
          continuation: state.continuation ?? [],
          boundaryRequests: boundary.requests ?? [],
          providers: (providers?.providers ?? []).map((entry) => ({
            id: entry.provider,
            label: entry.label,
            status: entry.status,
          })),
        });
        const now = Date.now();
        const attention = diffAttentionEvents(stateRef.current, items, now);
        const finished = diffFinishedEvents(attention.state, cleanlyFinished(state.jobs ?? []), now);
        stateRef.current = finished.state;
        for (const event of [...attention.events, ...finished.events]) {
          void ipcBridge.notification.show.invoke({
            title: 'Kel',
            body: event.body,
            conversation_id: event.conversation_id,
          });
        }
      } catch {
        // Honest silence — see the module doc.
      }
    };

    void tick();
    const timer = window.setInterval((): void => void tick(), POLL_MS);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, []);
};
