/**
 * The Notifications switch (D-73.1), kept in step between the renderer and the main process.
 *
 * The switch is stored with the other client settings in the backend (`/api/settings/client`), which
 * is what the renderer reads. The main process gates every desktop notification on its own cached
 * config (ProcessConfig) instead, so the two are synced here the same way Close to tray is
 * (closeToTraySetting.ts): the backend value wins and is copied into ProcessConfig, at start-up and
 * whenever the switch changes.
 */

import { httpRequest } from '@/common/adapter/httpBridge';
import { ProcessConfig } from './initStorage';

const NOTIFICATION_CONFIG_KEY = 'system.notificationEnabled';

const readBackendBoolean = async (key: string): Promise<boolean | undefined> => {
  try {
    const value = await httpRequest<Record<string, unknown>>(
      'GET',
      `/api/settings/client?keys=${encodeURIComponent(key)}`,
      undefined,
      { silentStatuses: [404] }
    );
    const entry = value?.[key];
    return typeof entry === 'boolean' ? entry : undefined;
  } catch {
    return undefined;
  }
};

/**
 * Read the switch, copying the backend value into ProcessConfig when the two disagree. Falls back
 * to the cached value when the backend has none (or is unreachable), and to "on" when neither has
 * one, matching the renderer's default.
 */
export const readNotificationSetting = async (): Promise<boolean> => {
  const backendValue = await readBackendBoolean(NOTIFICATION_CONFIG_KEY);
  let localValue: boolean | undefined;
  try {
    localValue = await ProcessConfig.get(NOTIFICATION_CONFIG_KEY);
  } catch {
    localValue = undefined;
  }
  if (typeof backendValue === 'boolean') {
    if (localValue !== backendValue) {
      try {
        await ProcessConfig.set(NOTIFICATION_CONFIG_KEY, backendValue);
      } catch {
        // The gate then keeps its previous value until the next sync; nothing else to do.
      }
    }
    return backendValue;
  }
  return typeof localValue === 'boolean' ? localValue : true;
};

export const writeNotificationSetting = async (enabled: boolean): Promise<void> => {
  await httpRequest<void>('PUT', '/api/settings/client', { [NOTIFICATION_CONFIG_KEY]: enabled });
  await ProcessConfig.set(NOTIFICATION_CONFIG_KEY, enabled);
};
