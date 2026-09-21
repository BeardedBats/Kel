/**
 * Campaign C AUD-MAJOR-002: per-channel sender refusals on the privileged IPC surface.
 *
 * Campaign B found the surface non-uniform: the Kel credential trio, the feedback pair, the
 * backend-startup sendSync handlers, the recovery channel, and the generic adapter dispatcher
 * accepted any sender (subframes run the preload). These tests pin the refusal for every one of
 * those channels - and the legitimate main-frame path - so a regression re-opens no channel.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

type FakeEvent = {
  senderFrame?: { url?: string | null } | null;
  sender?: { mainFrame?: unknown } | null;
  returnValue?: unknown;
};

const { handlers, listeners, bridgeCapture } = vi.hoisted(() => {
  const handlers = new Map<string, (event: unknown, ...args: unknown[]) => unknown>();
  const listeners = new Map<string, (event: unknown, ...args: unknown[]) => unknown>();
  const bridgeCapture: { config: { on: (emitter: unknown) => unknown } | null } = { config: null };
  return { handlers, listeners, bridgeCapture };
});

vi.mock('electron', () => ({
  app: {
    getPath: () => 'C:/fake/logs',
    getVersion: () => '0.0.0-test',
  },
  ipcMain: {
    handle: (channel: string, fn: (event: unknown, ...args: unknown[]) => unknown) => {
      handlers.set(channel, fn);
    },
    on: (channel: string, fn: (event: unknown, ...args: unknown[]) => unknown) => {
      listeners.set(channel, fn);
    },
    removeHandler: () => undefined,
    removeAllListeners: () => undefined,
  },
  BrowserWindow: {
    fromWebContents: () => null,
  },
}));

vi.mock('@/common/platform/bridge', () => ({
  bridge: {
    adapter: (config: { on: (emitter: unknown) => unknown }) => {
      bridgeCapture.config = config;
    },
  },
}));

vi.mock('@/process/feedback/logs', () => ({
  collectFeedbackLogAttachment: () => null,
}));

import { registerBackendStartupIpc } from '@process/startup/backendStartupIpc';
import { registerKelCredentialIpc } from '@/process/services/kel/kelCredentialIpc';
import { ADAPTER_BRIDGE_EVENT_KEY } from '@/common/adapter/constant';
import '@/process/bridge/feedbackBridge';
import '@/common/adapter/main';

const REFUSAL = 'Unknown Kel window';

const mainFrame = { url: 'file:///C:/kel/apps/renderer/index.html' };
const subframe = { url: 'file:///C:/kel/apps/renderer/artifact-preview.html' };
const foreignFrame = { url: 'https://evil.example/login' };
const devFrame = { url: 'http://localhost:5173/index.html' };

const legitEvent = (): FakeEvent => ({ senderFrame: mainFrame, sender: { mainFrame } });
const legitDevEvent = (): FakeEvent => ({ senderFrame: devFrame, sender: { mainFrame: devFrame } });

const refusalEvents: Array<[string, () => FakeEvent]> = [
  ['an untrusted subframe', () => ({ senderFrame: subframe, sender: { mainFrame } })],
  ['a foreign origin', () => ({ senderFrame: foreignFrame, sender: { mainFrame: foreignFrame } })],
  ['missing senderFrame', () => ({ sender: { mainFrame } })],
  ['missing sender.mainFrame', () => ({ senderFrame: mainFrame })],
  ['a frame without url', () => {
    const noUrl = {};
    return { senderFrame: noUrl, sender: { mainFrame: noUrl } };
  }],
  ['mismatched frame identity', () => ({
    senderFrame: { url: mainFrame.url },
    sender: { mainFrame: { url: mainFrame.url } },
  })],
];

const handleAt = (channel: string) => {
  const handler = handlers.get(channel);
  expect(handler, `handler for ${channel} is registered`).toBeTruthy();
  return handler as (event: unknown, ...args: unknown[]) => Promise<unknown>;
};

describe('privileged IPC sender refusals (Campaign C AUD-MAJOR-002)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('backend-startup channels', () => {
    const deps = {
      getPort: vi.fn(() => 5199),
      getInitialLanguage: vi.fn(() => 'en'),
      getStartupFailed: vi.fn(() => true),
      getStartupFailureInfo: vi.fn(() => ({ code: 'x' })),
      recoverCorruptedDatabase: vi.fn(async () => undefined),
    };

    beforeEach(() => {
      deps.getPort.mockClear();
      deps.getInitialLanguage.mockClear();
      deps.getStartupFailed.mockClear();
      deps.getStartupFailureInfo.mockClear();
      deps.recoverCorruptedDatabase.mockClear();
      registerBackendStartupIpc(deps);
    });

    const syncChannels: Array<[string, keyof typeof deps, unknown]> = [
      ['get-backend-port', 'getPort', 5199],
      ['get-initial-language', 'getInitialLanguage', 'en'],
      ['get-backend-startup-failed', 'getStartupFailed', true],
      ['get-backend-startup-failure', 'getStartupFailureInfo', { code: 'x' }],
    ];

    for (const [channel, depKey, legitValue] of syncChannels) {
      it(`${channel}: refuses spoofed senders and answers null`, () => {
        for (const [label, makeEvent] of refusalEvents) {
          const event: FakeEvent = makeEvent();
          const listener = listeners.get(channel);
          expect(listener, `${channel} listener registered`).toBeTruthy();
          listener!(event);
          expect(event.returnValue, `${channel} refused ${label}`).toBeNull();
        }
        expect(deps[depKey]).not.toHaveBeenCalled();
      });

      it(`${channel}: serves the legitimate main frame`, () => {
        const event: FakeEvent = legitEvent();
        listeners.get(channel)!(event);
        expect(event.returnValue).toEqual(legitValue);
        expect(deps[depKey]).toHaveBeenCalledTimes(1);
      });
    }

    it('get-backend-port: serves the dev-server main frame', () => {
      const event: FakeEvent = legitDevEvent();
      listeners.get('get-backend-port')!(event);
      expect(event.returnValue).toEqual(5199);
    });

    it('backend:recover-corrupted-database: refuses spoofed senders and runs for the main frame', async () => {
      const recovery = handleAt('backend:recover-corrupted-database');
      for (const [label, makeEvent] of refusalEvents) {
        await expect(recovery(makeEvent()), `${label} refused`).rejects.toThrow(REFUSAL);
      }
      expect(deps.recoverCorruptedDatabase).not.toHaveBeenCalled();
      await expect(recovery(legitEvent())).resolves.toBeUndefined();
      expect(deps.recoverCorruptedDatabase).toHaveBeenCalledTimes(1);
    });
  });

  describe('Kel credential channels', () => {
    const deps = {
      status: vi.fn(() => ({ available: true, providers: { anthropic: ['api_key'] } })),
      connectionStatus: vi.fn(() => ({ stripe: ['api_key'] })),
      set: vi.fn(() => ({ provider: 'anthropic', fields: ['api_key'] })),
      remove: vi.fn(() => ({ provider: 'anthropic', removed: 1 })),
      sync: vi.fn(async () => undefined),
    };

    beforeEach(() => {
      deps.status.mockClear();
      deps.connectionStatus.mockClear();
      deps.set.mockClear();
      deps.remove.mockClear();
      deps.sync.mockClear();
      registerKelCredentialIpc(deps);
    });

    it('kel:credential-status refuses spoofed senders', async () => {
      const status = handleAt('kel:credential-status');
      for (const [label, makeEvent] of refusalEvents) {
        // The status handler answers synchronously; the guard must throw before any work.
        expect(() => status(makeEvent()), label).toThrow(REFUSAL);
      }
      expect(deps.status).not.toHaveBeenCalled();
      expect(status(legitEvent())).toEqual({ available: true, providers: { anthropic: ['api_key'] } });
    });

    it('kel:credential-connection-status refuses spoofed senders', async () => {
      const status = handleAt('kel:credential-connection-status');
      for (const [label, makeEvent] of refusalEvents) {
        expect(() => status(makeEvent()), label).toThrow(REFUSAL);
      }
      expect(deps.connectionStatus).not.toHaveBeenCalled();
      expect(status(legitEvent())).toEqual({ stripe: ['api_key'] });
    });

    it('kel:credential-set refuses spoofed senders before any custody action', async () => {
      const set = handleAt('kel:credential-set');
      for (const [label, makeEvent] of refusalEvents) {
        await expect(set(makeEvent(), 'anthropic', 'api_key', 'sk-test'), label).rejects.toThrow(REFUSAL);
      }
      expect(deps.set).not.toHaveBeenCalled();
      expect(deps.sync).not.toHaveBeenCalled();
      await expect(set(legitEvent(), 'anthropic', 'api_key', 'sk-test')).resolves.toEqual({
        provider: 'anthropic',
        fields: ['api_key'],
      });
      expect(deps.sync).toHaveBeenCalledWith('/api/providers', {
        action: 'set_credential',
        provider: 'anthropic',
        fields: ['api_key'],
        credential_ref: 'kel:provider:anthropic:api_key',
      });
    });

    it('kel:credential-delete refuses spoofed senders before any custody action', async () => {
      const remove = handleAt('kel:credential-delete');
      for (const [label, makeEvent] of refusalEvents) {
        await expect(remove(makeEvent(), 'anthropic'), label).rejects.toThrow(REFUSAL);
      }
      expect(deps.remove).not.toHaveBeenCalled();
      await expect(remove(legitEvent(), 'anthropic')).resolves.toEqual({ provider: 'anthropic', removed: 1 });
      expect(deps.sync).toHaveBeenCalledWith('/api/providers', {
        action: 'delete_credential',
        provider: 'anthropic',
      });
    });

    it('a failing provider sync never fails the custody action', async () => {
      deps.sync.mockRejectedValueOnce(new Error('engine offline'));
      await expect(handleAt('kel:credential-set')(legitEvent(), 'anthropic', 'api_key', 'sk-test')).resolves.toEqual({
        provider: 'anthropic',
        fields: ['api_key'],
      });
    });
  });

  describe('feedback channels', () => {
    it('feedback:collect-logs refuses spoofed senders', async () => {
      const collect = handleAt('feedback:collect-logs');
      for (const [label, makeEvent] of refusalEvents) {
        await expect(collect(makeEvent()), label).rejects.toThrow(REFUSAL);
      }
      await expect(collect(legitEvent())).resolves.toBeNull();
    });

    it('feedback:capture-screenshot refuses spoofed senders', async () => {
      const capture = handleAt('feedback:capture-screenshot');
      for (const [label, makeEvent] of refusalEvents) {
        await expect(capture(makeEvent()), label).rejects.toThrow(REFUSAL);
      }
      await expect(capture(legitEvent())).resolves.toBeNull();
    });

    it('feedback:renderer-log silently drops spoofed senders', () => {
      const info = vi.spyOn(console, 'info').mockImplementation(() => undefined);
      const listener = listeners.get('feedback:renderer-log');
      expect(listener).toBeTruthy();
      listener!({ ...refusalEvents[0][1](), }, { level: 'info', message: 'hostile' });
      expect(info).not.toHaveBeenCalled();
      listener!(legitEvent(), { level: 'info', message: 'legitimate' });
      expect(info).toHaveBeenCalledWith('[FeedbackReport:renderer] legitimate');
      info.mockRestore();
    });
  });

  describe('adapter bridge dispatcher', () => {
    it('refuses spoofed senders before any donor bridge method runs', async () => {
      const emitter = { emit: vi.fn(() => 'emitted') };
      expect(bridgeCapture.config, 'adapter config captured at import').toBeTruthy();
      bridgeCapture.config!.on(emitter);
      const dispatch = handleAt(ADAPTER_BRIDGE_EVENT_KEY);
      const payload = JSON.stringify({ name: 'app.set-zoom-factor', data: { factor: 1 } });
      for (const [label, makeEvent] of refusalEvents) {
        // The dispatcher checks the guard before parsing; the refusal is synchronous.
        expect(() => dispatch(makeEvent(), payload), label).toThrow(REFUSAL);
      }
      expect(emitter.emit).not.toHaveBeenCalled();
      await expect(dispatch(legitEvent(), payload)).resolves.toBe('emitted');
      expect(emitter.emit).toHaveBeenCalledWith('app.set-zoom-factor', { factor: 1 });
    });
  });
});
