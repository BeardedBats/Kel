/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Desktop IPC bridge for WebUI lifecycle (start/stop/getStatus) + browser credentials.
 *
 * D3 (Kel): the browser login is owned by the web-host gateway — a scrypt password stored in
 * `<Kel data>/webui.config.json` plus in-memory sessions; the engine's per-process bearer token
 * is injected by the gateway and never reaches a browser. This bridge exposes the lifecycle and
 * the credential operations as IPC so they work with the server stopped and without the donor
 * aioncore HTTP routes.
 */

import { ipcBridge } from '@/common';
import {
  ensureInitialPassword,
  generateReadablePassword,
  generateWebUiQrToken,
  readAuthFile,
  setWebUiPassword,
  setWebUiUsername,
} from '@aionui/web-host';
import { getDataPath } from '../utils/utils';
import {
  startDesktopWebUI,
  stopDesktopWebUI,
  getDesktopWebUIStatus,
  setDesktopWebUIInitialPassword,
} from '@process/utils/webuiConfig';

const currentAdminUsername = (): string => readAuthFile(getDataPath()).adminUsername || 'admin';

export function initWebuiBridge(): void {
  ipcBridge.webui.getStatus.provider(async () => {
    const snapshot = getDesktopWebUIStatus();
    return { ...snapshot, adminUsername: currentAdminUsername() };
  });

  ipcBridge.webui.start.provider(async (params) => {
    // First enable after a fresh install generates the one-time password shown once in Settings.
    const { password } = ensureInitialPassword(getDataPath());
    setDesktopWebUIInitialPassword(password);
    const handle = await startDesktopWebUI({
      port: params?.port,
      allowRemote: params?.allowRemote,
    });
    ipcBridge.webui.statusChanged.emit({
      running: true,
      port: handle.port,
      localUrl: handle.localUrl,
      networkUrl: handle.networkUrl,
      lanIP: handle.lanIP,
      initialPassword: handle.initialPassword,
    });
    return handle;
  });

  ipcBridge.webui.stop.provider(async () => {
    await stopDesktopWebUI();
    ipcBridge.webui.statusChanged.emit({ running: false });
  });

  // Credential operations (desktop-side). The gateway's login checks the same store; a new
  // password applies to the next login, existing sessions keep their own lifetime.
  ipcBridge.webui.changePassword.provider(async (params) =>
    setWebUiPassword(getDataPath(), params?.newPassword ?? '')
  );

  ipcBridge.webui.changeUsername.provider(async (params) => setWebUiUsername(getDataPath(), params?.newUsername ?? ''));

  ipcBridge.webui.resetPassword.provider(async () => {
    const password = generateReadablePassword();
    const result = setWebUiPassword(getDataPath(), password);
    if (!result.ok) return { ok: false, code: result.code };
    // Surface the new password once, exactly like the first-enable flow.
    setDesktopWebUIInitialPassword(password);
    return { ok: true, new_password: password };
  });

  ipcBridge.webui.generateQRToken.provider(async () => {
    const status = getDesktopWebUIStatus();
    if (!status.running) return { ok: false, code: 'WEBUI_NOT_RUNNING' };
    const token = generateWebUiQrToken();
    return { ok: true, token: token.token, expires_at_ms: token.expires_at_ms };
  });
}
