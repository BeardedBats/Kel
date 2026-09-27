/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * 系统设置桥接模块
 * System Settings Bridge Module
 *
 * 负责���理系统级设置的读写操作（如关闭到托盘）
 * Handles read/write operations for system-level settings (e.g. close to tray)
 */

import { ipcBridge } from '@/common';
import { ProcessConfig } from '@process/utils/initStorage';
import { createOrUpdateTray, destroyTray, setCloseToTrayEnabled } from '@process/utils/tray';
import { readCloseToTraySetting, writeCloseToTraySetting } from '@process/utils/closeToTraySetting';
import {
  applyKeepAwake,
  isKeepAwakeActive,
  readKeepAwakeSetting,
  writeKeepAwakeSetting,
} from '@process/utils/keepAwake';

export function initSystemSettingsBridge(): void {
  ipcBridge.systemSettings.getCloseToTray.provider(async () => readCloseToTraySetting());

  ipcBridge.systemSettings.setCloseToTray.provider(async ({ enabled }) => {
    await writeCloseToTraySetting(enabled);
    setCloseToTrayEnabled(enabled);
    if (enabled) {
      createOrUpdateTray();
    } else {
      destroyTray();
    }
  });

  // Keep the computer awake: the stored choice and the live inhibition travel together, so the
  // surface can say "active" truthfully instead of guessing from the switch position.
  ipcBridge.systemSettings.getKeepAwake.provider(async () => ({
    enabled: await readKeepAwakeSetting(),
    active: isKeepAwakeActive(),
  }));

  ipcBridge.systemSettings.setKeepAwake.provider(async ({ enabled }) => {
    await writeKeepAwakeSetting(enabled);
    return { enabled, active: applyKeepAwake(enabled) };
  });
}
