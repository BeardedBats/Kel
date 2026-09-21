// Modified for Kel: restricted work-control IPC.
/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

// Hook Sentry IPC so the renderer SDK uses ipcRenderer.send instead of falling
// back to fetch('sentry-ipc://...'), which floods the DevTools Network panel.
// Bundled into this preload via `externalizeDepsPlugin({ exclude: [...] })` so
// Electron's sandbox-mode preload doesn't try to resolve it from node_modules.
import '@sentry/electron/preload';
import { contextBridge, ipcRenderer, webUtils } from 'electron';
import { ADAPTER_BRIDGE_EVENT_KEY } from '../common/adapter/constant';

/**
 * @description 注入到renderer进程中, 用于与main进程通信
 * */
contextBridge.exposeInMainWorld('electronAPI', {
  emit: (name: string, data: unknown) => {
    return ipcRenderer
      .invoke(
        ADAPTER_BRIDGE_EVENT_KEY,
        JSON.stringify({
          name: name,
          data: data,
        })
      )
      .catch((error) => {
        console.error('IPC invoke error:', error);
        throw error;
      });
  },
  on: (callback: (payload: { event: unknown; value: unknown }) => void) => {
    const handler = (event: unknown, value: unknown) => {
      callback({ event, value });
    };
    ipcRenderer.on(ADAPTER_BRIDGE_EVENT_KEY, handler);
    return () => {
      ipcRenderer.off(ADAPTER_BRIDGE_EVENT_KEY, handler);
    };
  },
  // 获取拖拽文件/目录的绝对路径 / Get absolute path for dragged file/directory
  getPathForFile: (file: File) => webUtils.getPathForFile(file),
  // Feedback: collect and compress recent log files
  collectFeedbackLogs: () => ipcRenderer.invoke('feedback:collect-logs'),
  // Feedback: capture a screenshot of the current window
  captureFeedbackScreenshot: () => ipcRenderer.invoke('feedback:capture-screenshot'),
  // Feedback: forward diagnostics logs to the main process console
  logFeedbackEvent: (payload: { details?: unknown; level: 'info' | 'warn' | 'error'; message: string }) =>
    ipcRenderer.send('feedback:renderer-log', payload),
  recoverCorruptedDatabase: () => ipcRenderer.invoke('backend:recover-corrupted-database'),
});

// Synchronously fetch the aioncore port and expose it to the renderer
// via contextBridge (direct window assignment is invisible under contextIsolation).
const backendPort = ipcRenderer.sendSync('get-backend-port') as number;
const initialLanguage = ipcRenderer.sendSync('get-initial-language') as string | null;
const backendStartupFailed = ipcRenderer.sendSync('get-backend-startup-failed') as boolean;
const backendStartupFailure = ipcRenderer.sendSync('get-backend-startup-failure') as unknown;
contextBridge.exposeInMainWorld('__backendPort', backendPort > 0 ? backendPort : 0);
contextBridge.exposeInMainWorld('__initialLanguage', initialLanguage ?? null);
contextBridge.exposeInMainWorld('__aionuiE2ETest', process.env.AIONUI_E2E_TEST === '1');
contextBridge.exposeInMainWorld('__backendStartupFailed', backendStartupFailed === true);
contextBridge.exposeInMainWorld('__backendStartupFailure', backendStartupFailure ?? null);

// Backend startup state bridge: `getState` re-reads the current failure info on
// mount (resolves the "READY arrived before the renderer subscribed" race), and
// `subscribe` receives subsequent ready/exit pushes on the backend-startup-state
// channel. All communication stays behind the preload contextBridge.
contextBridge.exposeInMainWorld('__backendStartupBridge', {
  getState: () => ipcRenderer.sendSync('get-backend-startup-failure'),
  subscribe: (callback: (state: unknown) => void) => {
    const handler = (_event: unknown, value: unknown) => callback(value);
    ipcRenderer.on('backend-startup-state', handler);
    return () => {
      ipcRenderer.off('backend-startup-state', handler);
    };
  },
});

// 托盘事件监听 - 将 IPC 事件转换为 DOM 事件
// Tray event listeners - convert IPC events to DOM events
const trayEvents = [
  'tray:navigate-to-guid',
  'tray:navigate-to-conversation',
  'tray:open-about',
  'tray:pause-all-tasks',
  'tray:check-update',
];

for (const channel of trayEvents) {
  ipcRenderer.on(channel, (_event, ...args) => {
    window.dispatchEvent(new CustomEvent(channel, { detail: args[0] }));
  });
}

contextBridge.exposeInMainWorld('kelAPI', {
  request: async (route: string, body?: unknown) => {
    try {
      return await ipcRenderer.invoke('kel:request', route, body);
    } catch (error) {
      // Electron wraps handler failures as "Error invoking remote method '…': Error: <message>".
      // The engine already writes user-facing sentences; never leak the transport envelope.
      const raw = String((error as Error)?.message || error);
      const message = raw.replace(/^Error invoking remote method '[^']*':\s*/, '').replace(/^Error:\s*/, '');
      throw new Error(message || 'Kel request failed');
    }
  },
  history: (id: string) => ipcRenderer.invoke('kel:history', id),
  conversation: (id: string) => ipcRenderer.invoke('kel:conversation', id),
  historySearch: (query: string) => ipcRenderer.invoke('kel:history-search', query),
  // Batch 6 (findings 16/17): the engine-link state for the shell's reconnecting / recovered /
  // could-not-recover surfaces, the manual retry action, and the diagnostics bundle the failure
  // card copies. Presentation support only — no durable state is owned here.
  engineState: () => ipcRenderer.invoke('kel:engine-state'),
  engineRetry: () => ipcRenderer.invoke('kel:engine-retry'),
  diagnostics: () => ipcRenderer.invoke('kel:diagnostics'),
  onEngineState: (callback: (frame: unknown) => void) => {
    const handler = (_event: unknown, frame: unknown) => callback(frame);
    ipcRenderer.on('kel:engine-state', handler);
    return () => {
      ipcRenderer.off('kel:engine-state', handler);
    };
  },
  // Artifact lineage: reveal a produced artifact (store-relative path) in the OS file manager.
  revealArtifact: (relpath: string) => ipcRenderer.invoke('kel:artifact-reveal', relpath),
  // Credential custody: store, list field names, delete. Deliberately no value getter, so a secret
  // cannot reach the renderer even by mistake.
  credentials: {
    status: () => ipcRenderer.invoke('kel:credential-status'),
    // V2-01: what the OS store holds for Connections, so the Connections surface never claims a
    // credential is missing while it is still stored. Names only — still no value getter.
    connectionStatus: () => ipcRenderer.invoke('kel:credential-connection-status'),
    set: (provider: string, field: string, value: string) =>
      ipcRenderer.invoke('kel:credential-set', provider, field, value),
    remove: (provider: string) => ipcRenderer.invoke('kel:credential-delete', provider),
    // V2-02: use a connection's stored credential for one check. The value is decrypted in the main
    // process and never comes back here — only the result of the check does.
    testConnection: (connectionId: string) =>
      ipcRenderer.invoke('kel:connection-test', connectionId),
    // V2-04: do one thing with a connection. Same rule as the check — the value is decrypted in the main
    // process for that one request and the service's answer comes back, never a credential.
    runConnection: (
      connectionId: string,
      actionId: string,
      params?: Record<string, unknown>,
      confirmed?: boolean
    ) => ipcRenderer.invoke('kel:connection-run', connectionId, actionId, params, confirmed),
  },
  // Fix Capture (V2.0 preflight): the window screenshot + metrics come from the main process, and
  // the path handed back is relative to the engine data root. The view can read one saved screenshot
  // back for display. Absent on the remote surface (a plain browser cannot read Kel's window), where
  // Fix Capture says so honestly instead of guessing.
  dogfood: {
    capture: () => ipcRenderer.invoke('kel:dogfood-capture'),
    screenshot: (relpath: string) => ipcRenderer.invoke('kel:dogfood-screenshot', relpath),
  },
});
