/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-57: the scheduled-task list, read from the engine. One shared read serves the Scheduled page,
 * the sidebar marks and the chat header, and it refreshes on mount, when the window regains
 * focus or becomes visible, every 15 s while visible, and after every action taken here.
 */

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import {
  kelSchedules,
  type KelSchedule,
  type KelScheduleDraft,
  type KelScheduleRun,
} from '@renderer/components/kel/kelApi';
import { getRouteConversationIdForKelId } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';
import { emitter } from '@/renderer/utils/emitter';
import { scheduleStatus, type ScheduleStatus } from './cronUtils';

const REFRESH_MS = 15_000;

type ListState = { schedules: KelSchedule[] | null; error: string | null; loading: boolean };

let state: ListState = { schedules: null, error: null, loading: false };
const listeners = new Set<() => void>();
let inFlight: Promise<void> | null = null;

const emit = () => listeners.forEach((listener) => listener());

const errorText = (error: unknown): string =>
  String((error as Error)?.message || '').trim() || 'Kel could not read the scheduled tasks just now.';

/** Read the list again (one read at a time; callers share it). */
export function refreshSchedules(): Promise<void> {
  if (inFlight) return inFlight;
  state = { ...state, loading: true };
  emit();
  inFlight = kelSchedules
    .list()
    .then((schedules) => {
      state = { schedules, error: null, loading: false };
    })
    .catch((error: unknown) => {
      // Keep what was last read: a failed refresh never empties a list the person is looking at.
      state = { ...state, error: errorText(error), loading: false };
    })
    .finally(() => {
      inFlight = null;
      emit();
    });
  return inFlight;
}

/** Test hook: forget the shared list. */
export function resetSchedulesForTest(): void {
  state = { schedules: null, error: null, loading: false };
  inFlight = null;
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

/** Refresh on focus / visibility, and every 15 s while the window is visible. */
export function useVisibleRefresh(refresh: () => void, enabled = true): void {
  const latest = useRef(refresh);
  latest.current = refresh;
  useEffect(() => {
    if (!enabled) return;
    const run = () => {
      if (typeof document === 'undefined' || document.visibilityState !== 'hidden') latest.current();
    };
    const timer = setInterval(run, REFRESH_MS);
    window.addEventListener('focus', run);
    document.addEventListener('visibilitychange', run);
    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', run);
      document.removeEventListener('visibilitychange', run);
    };
  }, [enabled]);
}

export function useSchedules() {
  const snapshot = useSyncExternalStore(subscribe, () => state);
  useEffect(() => {
    void refreshSchedules();
  }, []);
  useVisibleRefresh(() => void refreshSchedules());
  return {
    schedules: snapshot.schedules ?? [],
    loaded: snapshot.schedules !== null,
    loading: snapshot.schedules === null && (snapshot.loading || !snapshot.error),
    error: snapshot.error,
    refresh: refreshSchedules,
  };
}

/** After a change: re-read, and let the main process bring the chat list in step. */
const afterChange = async (hidden: string[] = []) => {
  await refreshSchedules();
  try {
    await window.kelAPI?.schedulesChanged?.({ hidden });
  } catch {
    // The 20 s sweep catches up on its own.
  }
  emitter.emit('chat.history.refresh');
};

export const scheduleActions = {
  create: async (draft: KelScheduleDraft) => {
    const created = await kelSchedules.create(draft);
    await afterChange();
    return created;
  },
  update: async (id: string, changes: Partial<KelScheduleDraft>) => {
    const updated = await kelSchedules.update(id, changes);
    await afterChange();
    return updated;
  },
  pause: async (id: string) => {
    await kelSchedules.pause(id);
    await afterChange();
  },
  resume: async (id: string) => {
    await kelSchedules.resume(id);
    await afterChange();
  },
  remove: async (id: string, conversations: 'keep' | 'delete') => {
    const answer = await kelSchedules.remove(id, conversations);
    // The engine hid the chats of its finished runs; their app chats leave the list too.
    await afterChange(Array.isArray(answer?.hidden) ? answer.hidden.filter((cid) => typeof cid === 'string') : []);
  },
  runNow: async (id: string) => {
    const answer = await kelSchedules.runNow(id);
    await afterChange();
    return answer;
  },
  /** A team or chat that goes away takes its migrated task with it; never blocks the removal. */
  removeByOrigin: async (origin: string) => {
    try {
      const schedule = await kelSchedules.get({ origin });
      if (schedule) await scheduleActions.remove(schedule.id, 'keep');
    } catch {
      // The task stays on the Scheduled page, where it can be deleted by hand.
    }
  },
};

/**
 * One schedule and its runs, by id — or by the old task id a link from before the move carries
 * (`?origin=`). `schedule` is null once read and not found.
 */
export function useSchedule(ref: { id?: string; origin?: string }) {
  const [schedule, setSchedule] = useState<KelSchedule | null | undefined>(undefined);
  const [runs, setRuns] = useState<KelScheduleRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const key = ref.id ? `id:${ref.id}` : ref.origin ? `origin:${ref.origin}` : '';
  const seq = useRef(0);

  const load = useCallback(async () => {
    if (!key) {
      setSchedule(null);
      return;
    }
    const mine = ++seq.current;
    try {
      const found = await kelSchedules.get(ref.id ? { id: ref.id } : { origin: ref.origin! });
      if (mine !== seq.current) return;
      setSchedule(found && !found.deleted ? found : null);
      setError(null);
      if (found && !found.deleted) {
        try {
          const history = await kelSchedules.history(found.id);
          if (mine === seq.current) {
            setRuns(history);
            setHistoryError(null);
          }
        } catch (historyFailure) {
          if (mine === seq.current) setHistoryError(errorText(historyFailure));
        }
      }
    } catch (failure) {
      if (mine !== seq.current) return;
      const text = errorText(failure);
      // An engine that answers "not found" means gone; anything else is a read failure.
      if (/not found|no such|unknown schedule|does not exist/i.test(text)) setSchedule(null);
      else setError(text);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    setSchedule(undefined);
    setRuns(null);
    setError(null);
    void load();
  }, [load]);
  useVisibleRefresh(() => void load(), Boolean(key));

  return { schedule, runs, error, historyError, reload: load };
}

// ---------------------------------------------------------------------------------------------
// Sidebar marks: which chats a schedule belongs to (its own chat, and its latest run's chat).
// ---------------------------------------------------------------------------------------------

const RANK: Record<ScheduleStatus, number> = { error: 3, active: 2, paused: 1 };

/** Chats → the strongest status among the schedules that use them (keyed by engine id). */
export function scheduleStatusByConversation(schedules: KelSchedule[]): Map<string, ScheduleStatus> {
  const byConversation = new Map<string, ScheduleStatus>();
  const put = (cid: string | null | undefined, status: ScheduleStatus) => {
    if (!cid) return;
    const current = byConversation.get(cid);
    if (!current || RANK[status] > RANK[current]) byConversation.set(cid, status);
  };
  for (const schedule of schedules) {
    const status = scheduleStatus(schedule);
    if (schedule.start_mode === 'existing') put(schedule.conversation_id, status);
    put(schedule.last_run?.conversation, status);
  }
  return byConversation;
}

/** App chat id for an engine conversation id, cached; resolved through the main process once. */
const donorIds = new Map<string, string | null>();
const donorLookups = new Map<string, Promise<void>>();

export function useScheduleStatusMap() {
  const { schedules } = useSchedules();
  const byConversation = useMemo(() => scheduleStatusByConversation(schedules), [schedules]);
  const [resolved, setResolved] = useState(0);

  useEffect(() => {
    for (const cid of byConversation.keys()) {
      if (donorIds.has(cid) || donorLookups.has(cid)) continue;
      const known = getRouteConversationIdForKelId(cid);
      if (known) {
        donorIds.set(cid, known);
        continue;
      }
      const open = window.kelAPI?.openEngineConversation;
      if (!open) continue;
      donorLookups.set(
        cid,
        open(cid)
          .then((donor) => {
            donorIds.set(cid, donor ?? null);
            setResolved((n) => n + 1);
          })
          .catch((): undefined => undefined)
          .finally(() => donorLookups.delete(cid))
      );
    }
  }, [byConversation]);

  const byDonor = useMemo(() => {
    const map = new Map<string, ScheduleStatus>();
    for (const [cid, status] of byConversation) {
      const donor = donorIds.get(cid) ?? getRouteConversationIdForKelId(cid);
      if (donor) map.set(donor, status);
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [byConversation, resolved]);

  /** The status for a chat by its app id or its engine id; 'none' when no schedule uses it. */
  const getJobStatus = useCallback(
    (conversationId: string): 'none' | ScheduleStatus =>
      byDonor.get(conversationId) ?? byConversation.get(conversationId) ?? 'none',
    [byDonor, byConversation]
  );
  return { getJobStatus };
}
