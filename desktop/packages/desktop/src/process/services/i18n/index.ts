/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import i18n from 'i18next';
import { DEFAULT_LANGUAGE } from '@/common/config/i18n';

// D-61: Kel ships in English (en-US) only. Static import so Vite bundles the strings into the
// main-process output (the JSON files do not exist on disk in production).
import enUS from '@renderer/services/i18n/locales/en-US/index';

/** Resolves when the main-process strings (tray menu, dialogs) are loaded. */
export const i18nReady = (async (): Promise<void> => {
  await i18n.init({
    resources: { [DEFAULT_LANGUAGE]: { translation: enUS as Record<string, unknown> } },
    lng: DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    debug: false,
    interpolation: { escapeValue: false },
  });
})().catch((error) => {
  console.error('[Main Process] Failed to initialize i18n:', error);
});

export default i18n;
