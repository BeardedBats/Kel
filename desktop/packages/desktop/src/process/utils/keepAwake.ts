/**
 * Keep the computer awake during long work (Kel system setting `system.keepAwake`).
 *
 * The user-visible switch is only honest if something actually inhibits sleep, so this module owns
 * Electron's power-save blocker: `prevent-app-suspension` keeps the machine working while the
 * display may still dim (a long job does not need the screen lit). The blocker id lives in this
 * process, so quitting - or crashing - releases the inhibition with it; there is no on-disk state
 * that could leave a machine awake after Kel is gone.
 */
import { powerSaveBlocker } from 'electron';
import { httpRequest } from '@/common/adapter/httpBridge';
import { ProcessConfig } from './initStorage';

const KEEP_AWAKE_CONFIG_KEY = 'system.keepAwake';
const BACKEND_KEEP_AWAKE_KEY = 'keepAwake';

let blockerId: number | null = null;

/** True while Kel is holding the sleep inhibition. */
export const isKeepAwakeActive = (): boolean => blockerId !== null && powerSaveBlocker.isStarted(blockerId);

/** Start or stop the inhibition; idempotent, so the current value can be applied at any time. */
export const applyKeepAwake = (enabled: boolean): boolean => {
  if (enabled) {
    if (blockerId === null || !powerSaveBlocker.isStarted(blockerId)) {
      blockerId = powerSaveBlocker.start('prevent-app-suspension');
    }
  } else if (blockerId !== null) {
    if (powerSaveBlocker.isStarted(blockerId)) {
      powerSaveBlocker.stop(blockerId);
    }
    blockerId = null;
  }
  return isKeepAwakeActive();
};

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

/** The setting as the user left it: local config first, older backend KV as the fallback. */
export const readKeepAwakeSetting = async (): Promise<boolean> => {
  const localValue = await ProcessConfig.get(KEEP_AWAKE_CONFIG_KEY);
  if (typeof localValue === 'boolean') {
    return localValue;
  }
  const backendValue = await readBackendBoolean(BACKEND_KEEP_AWAKE_KEY);
  if (typeof backendValue === 'boolean') {
    await writeKeepAwakeSetting(backendValue);
    return backendValue;
  }
  return false;
};

export const writeKeepAwakeSetting = async (enabled: boolean): Promise<void> => {
  await ProcessConfig.set(KEEP_AWAKE_CONFIG_KEY, enabled);
};

/** Apply the persisted setting once at startup (before the first window is useful). */
export const initKeepAwake = async (): Promise<void> => {
  try {
    applyKeepAwake(await readKeepAwakeSetting());
  } catch (error) {
    console.error('[Kel] Failed to restore the keep-awake setting:', error);
    applyKeepAwake(false);
  }
};
