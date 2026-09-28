/**
 * D-73.1: the Notifications switch in Settings → System reaches the main-process gate.
 *
 * The switch, the renderer hooks and the main-process gate are wired together here the way they
 * are in the app: the System page calls the main process's set provider (which writes the backend
 * and ProcessConfig), and both notification hooks hand their events to the real showNotification(),
 * which reads ProcessConfig. Turning the switch off must stop both the turn notifications and the
 * attention notifications; turning it back on must let them through again. VIS-20 rides along: the
 * Keep computer awake row is back on the page.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const h = vi.hoisted(() => {
  const processConfig = new Map<string, unknown>();
  const backend = new Map<string, unknown>();
  const created: Array<{ title: string; body: string }> = [];
  const stream: { handler: ((message: unknown) => void) | null } = { handler: null };
  const attention: { items: Array<Record<string, unknown>> } = { items: [] };
  return { processConfig, backend, created, stream, attention };
});

// Main-process pieces: its config file and the backend's client settings.
vi.mock('@process/utils/initStorage', () => ({
  ProcessConfig: {
    get: async (key: string) => h.processConfig.get(key),
    set: async (key: string, value: unknown) => void h.processConfig.set(key, value),
  },
}));
vi.mock('@/common/adapter/httpBridge', () => ({
  getBaseUrl: () => '',
  httpRequest: async (method: string, route: string, body?: Record<string, unknown>) => {
    if (method === 'PUT') {
      for (const [key, value] of Object.entries(body ?? {})) h.backend.set(key, value);
      return undefined;
    }
    const key = decodeURIComponent(route.split('keys=')[1] ?? '');
    return h.backend.has(key) ? { [key]: h.backend.get(key) } : {};
  },
}));
vi.mock('@/common/electronSafe', () => ({
  electronNotification: class {
    private options: { title: string; body: string };
    constructor(options: { title: string; body: string }) {
      this.options = options;
    }
    on() {}
    show() {
      h.created.push(this.options);
    }
    static isSupported() {
      return true;
    }
  },
}));
vi.mock('@/common/platform', () => ({
  getPlatformServices: () => ({ paths: { isPackaged: () => false }, notification: { send: vi.fn() } }),
}));

// The IPC bridge, routed straight to the main-process implementations.
vi.mock('@/common', () => ({
  ipcBridge: {
    notification: {
      clicked: { emit: vi.fn() },
      show: {
        provider: vi.fn(),
        invoke: async (payload: { title: string; body: string; conversation_id?: string }) =>
          (await import('@process/bridge/notificationBridge')).showNotification(payload),
      },
    },
    conversation: {
      responseStream: {
        on: (handler: (message: unknown) => void) => {
          h.stream.handler = handler;
          return () => (h.stream.handler = null);
        },
      },
    },
    systemSettings: {
      getCloseToTray: { invoke: async () => false },
      setCloseToTray: { invoke: vi.fn(async () => undefined) },
      getNotificationEnabled: {
        invoke: async () => (await import('@process/utils/notificationSetting')).readNotificationSetting(),
      },
      setNotificationEnabled: {
        invoke: async ({ enabled }: { enabled: boolean }) =>
          (await import('@process/utils/notificationSetting')).writeNotificationSetting(enabled),
      },
      getKeepAwake: { invoke: async () => ({ enabled: false, active: false }) },
      setKeepAwake: { invoke: vi.fn() },
    },
    application: {
      getStartOnBootStatus: { invoke: async () => ({ success: false }) },
      getGpuStatus: { invoke: async () => ({ success: false }) },
      systemInfo: { invoke: async () => ({ workDir: 'C:/w', logDir: 'C:/l', cacheDir: 'C:/c' }) },
    },
  },
}));

vi.mock('@/renderer/utils/platform', () => ({ isElectronDesktop: () => true }));
vi.mock('@/renderer/services/clientBusinessSettings', () => ({
  getClientBusinessSetting: async () => undefined,
  setClientBusinessSetting: async () => undefined,
}));
vi.mock('@/renderer/hooks/chat/useCrossSessionMessageEnabled', () => ({
  useCrossSessionMessageEnabled: () => ({ enabled: true, setEnabled: vi.fn(async () => undefined) }),
}));
vi.mock('@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync', () => ({
  getSnapshotConversationName: () => undefined,
}));
vi.mock('@renderer/components/kel/kelApi', () => ({
  KEL_ALL_CONVERSATIONS: '*',
  kelState: async () => ({ jobs: [], continuation: [] }),
  kelAutonomy: { requests: async () => ({ requests: [] }) },
  kelProviders: { list: async () => ({ providers: [] }) },
}));
vi.mock('@renderer/components/kel/needsAttention', () => ({ collectAttention: () => h.attention.items }));
const i18n = vi.hoisted(() => {
  const t = (key: string) => key;
  return { t, i18n: { language: 'en-US' } };
});
vi.mock('react-i18next', () => ({ useTranslation: () => i18n }));
vi.mock('@/renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));

import SystemModalContent from '@renderer/components/settings/SettingsModal/contents/SystemModalContent';
import { SettingsViewModeProvider } from '@renderer/components/settings/SettingsModal/settingsViewContext';
import { useDesktopTurnNotification } from '@renderer/hooks/system/notification/useDesktopTurnNotification';
import { useKelAttentionNotification } from '@renderer/hooks/system/notification/useKelAttentionNotification';
import { readNotificationSetting } from '@process/utils/notificationSetting';

const Hooks: React.FC = () => {
  useDesktopTurnNotification();
  useKelAttentionNotification();
  return null;
};

let turn = 0;
const finishTurn = () => act(() => h.stream.handler?.({ type: 'finish', conversation_id: 'c1', turn_id: `t${++turn}` }));
let attentionId = 0;
const raiseAttention = async () => {
  h.attention.items = [{ id: `a${++attentionId}`, kind: 'input', title: 'Kel needs an answer', detail: '' }];
  await act(async () => {
    await vi.advanceTimersByTimeAsync(20_000);
  });
};
const flush = () => act(async () => void (await vi.advanceTimersByTimeAsync(0)));

describe('D-73.1 Notifications switch', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    h.processConfig.clear();
    h.backend.clear();
    h.created.length = 0;
    h.attention.items = [];
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('turning it off stops turn and attention notifications; turning it on lets them through', async () => {
    render(
      <SettingsViewModeProvider value='page'>
        <SystemModalContent />
        <Hooks />
      </SettingsViewModeProvider>
    );
    await flush(); // the attention hook's first (silent) snapshot

    const toggle = await screen.findByRole('switch', { name: 'Notifications' });
    expect(toggle.getAttribute('aria-checked')).toBe('true');
    expect(screen.getByText('Keep computer awake')).toBeTruthy();

    // On: both kinds reach the desktop.
    await finishTurn();
    await raiseAttention();
    await waitFor(() => expect(h.created).toHaveLength(2));

    // Off: the value reaches the backend and the main process's config, and nothing is shown.
    fireEvent.click(toggle);
    await waitFor(() => expect(h.processConfig.get('system.notificationEnabled')).toBe(false));
    expect(h.backend.get('system.notificationEnabled')).toBe(false);
    h.created.length = 0;
    await finishTurn();
    await raiseAttention();
    await flush();
    expect(h.created).toHaveLength(0);

    // On again.
    fireEvent.click(toggle);
    await waitFor(() => expect(h.processConfig.get('system.notificationEnabled')).toBe(true));
    await finishTurn();
    await raiseAttention();
    await waitFor(() => expect(h.created).toHaveLength(2));
  });

  it('copies the saved choice into the main process at start-up, so the gate holds before Settings opens', async () => {
    h.backend.set('system.notificationEnabled', false);
    h.processConfig.set('system.notificationEnabled', true);
    await expect(readNotificationSetting()).resolves.toBe(false);
    expect(h.processConfig.get('system.notificationEnabled')).toBe(false);
    const { showNotification } = await import('@process/bridge/notificationBridge');
    await showNotification({ title: 'Kel', body: 'Work finished' });
    expect(h.created).toHaveLength(0);
  });

  it('keeps the cached value when the backend has none, and defaults to on', async () => {
    h.processConfig.set('system.notificationEnabled', false);
    await expect(readNotificationSetting()).resolves.toBe(false);
    h.processConfig.clear();
    await expect(readNotificationSetting()).resolves.toBe(true);
  });
});
