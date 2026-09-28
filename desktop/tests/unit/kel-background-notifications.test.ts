/**
 * Off-screen test and audit runs (KEL_BACKGROUND_WINDOW=1) must never put a desktop notification on
 * Nick's screen, whatever the saved notification setting says.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const created = vi.fn();
vi.mock('@/common/electronSafe', () => ({
  electronNotification: class {
    constructor(options: unknown) {
      created(options);
    }
    on() {}
    show() {}
    static isSupported() {
      return true;
    }
  },
}));
vi.mock('@/common/platform', () => ({
  getPlatformServices: () => ({ paths: { isPackaged: () => false }, notification: { send: vi.fn() } }),
}));
vi.mock('@/common', () => ({ ipcBridge: { notification: { clicked: { emit: vi.fn() }, show: { provider: vi.fn() } } } }));
vi.mock('@process/utils/initStorage', () => ({ ProcessConfig: { get: async () => true } }));

import { showNotification } from '@process/bridge/notificationBridge';

describe('desktop notifications in background test runs', () => {
  afterEach(() => {
    delete process.env.KEL_BACKGROUND_WINDOW;
    created.mockClear();
  });

  it('shows a notification in normal use', async () => {
    await showNotification({ title: 'Kel', body: 'Done' });
    expect(created).toHaveBeenCalledTimes(1);
  });

  it('never shows one when the window is an off-screen test window', async () => {
    process.env.KEL_BACKGROUND_WINDOW = '1';
    await showNotification({ title: 'Kel', body: 'Done' });
    expect(created).not.toHaveBeenCalled();
  });
});
