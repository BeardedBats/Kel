/**
 * Backend-startup IPC registration (Campaign C AUD-MAJOR-002).
 *
 * The four synchronous lookups and the corrupted-database recovery action are privileged:
 * the shared sender guard applies to each one, and refusals fail closed (sync lookups answer
 * `null`, the recovery action rejects).
 */
import { ipcMain, type IpcMainEvent } from 'electron';
import { assertTrustedSender, isTrustedSender } from '../../common/senderGuard';

export interface BackendStartupIpcDeps {
  getPort: () => unknown;
  getInitialLanguage: () => unknown;
  getStartupFailed: () => unknown;
  getStartupFailureInfo: () => unknown;
  recoverCorruptedDatabase: () => Promise<void>;
}

const guardSyncEvent = (event: IpcMainEvent): boolean => {
  if (!isTrustedSender(event, { allowDevServer: true })) {
    // A refused synchronous caller must not learn anything; it gets the safe default.
    event.returnValue = null;
    return false;
  }
  return true;
};

export const registerBackendStartupIpc = (deps: BackendStartupIpcDeps): void => {
  ipcMain.on('get-backend-port', (event) => {
    if (guardSyncEvent(event)) event.returnValue = deps.getPort();
  });

  ipcMain.on('get-initial-language', (event) => {
    if (guardSyncEvent(event)) event.returnValue = deps.getInitialLanguage();
  });

  ipcMain.on('get-backend-startup-failed', (event) => {
    if (guardSyncEvent(event)) event.returnValue = deps.getStartupFailed();
  });

  ipcMain.on('get-backend-startup-failure', (event) => {
    if (guardSyncEvent(event)) event.returnValue = deps.getStartupFailureInfo();
  });

  ipcMain.handle('backend:recover-corrupted-database', async (event) => {
    assertTrustedSender(event, { allowDevServer: true });
    await deps.recoverCorruptedDatabase();
  });
};
