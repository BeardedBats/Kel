/**
 * Keep-awake: the switch is only honest when it holds a real power-save inhibition.
 *
 * The blocker id lives in the main process, so turning the setting off - or losing the process -
 * releases it; these tests pin that behaviour plus the stored-setting fallback for older installs.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { powerSaveBlocker, started, store, backend } = vi.hoisted(() => {
  const startedIds = new Map<number, string>();
  const memory = new Map<string, unknown>();
  const backendValue: { current: unknown } = { current: undefined };
  let nextId = 1;
  return {
    started: startedIds,
    store: memory,
    backend: backendValue,
    powerSaveBlocker: {
      start: (type: string) => {
        const id = nextId++;
        startedIds.set(id, type);
        return id;
      },
      stop: (id: number) => {
        startedIds.delete(id);
      },
      isStarted: (id: number) => startedIds.has(id),
    },
  };
});

vi.mock('electron', () => ({ powerSaveBlocker }));

vi.mock('@process/utils/initStorage', () => ({
  ProcessConfig: {
    get: async (key: string) => store.get(key),
    set: async (key: string, value: unknown) => {
      store.set(key, value);
    },
  },
}));

vi.mock('@/common/adapter/httpBridge', () => ({
  httpRequest: async () => (backend.current === undefined ? {} : { keepAwake: backend.current }),
}));

import { applyKeepAwake, isKeepAwakeActive, readKeepAwakeSetting } from '@process/utils/keepAwake';

describe('keep-awake', () => {
  beforeEach(() => {
    started.clear();
    store.clear();
    backend.current = undefined;
    applyKeepAwake(false);
  });

  it('starts sleep-only prevention when enabled, once', () => {
    expect(isKeepAwakeActive()).toBe(false);
    expect(applyKeepAwake(true)).toBe(true);
    expect([...started.values()]).toEqual(['prevent-app-suspension']);
    // Applying the same value again must not stack a second inhibition.
    expect(applyKeepAwake(true)).toBe(true);
    expect(started.size).toBe(1);
    expect(isKeepAwakeActive()).toBe(true);
  });

  it('releases the inhibition when disabled', () => {
    applyKeepAwake(true);
    expect(applyKeepAwake(false)).toBe(false);
    expect(started.size).toBe(0);
    expect(isKeepAwakeActive()).toBe(false);
    // Nothing left to release; still safe to call.
    expect(applyKeepAwake(false)).toBe(false);
  });

  it('reads the local choice first and falls back to the older backend value', async () => {
    backend.current = true;
    expect(await readKeepAwakeSetting()).toBe(true);
    expect(store.get('system.keepAwake')).toBe(true);

    store.set('system.keepAwake', false);
    backend.current = true;
    expect(await readKeepAwakeSetting()).toBe(false);
  });

  it('reports off when nothing was ever stored', async () => {
    expect(await readKeepAwakeSetting()).toBe(false);
  });
});
