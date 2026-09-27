/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Shared i18n values used by both main process and renderer.
 *
 * D-61: Kel ships in English (en-US) only. Every language hint — a stored preference, the OS
 * language, a browser header — resolves to en-US.
 */

import i18nConfig from '@/common/config/i18n-config.json';

export const SUPPORTED_LANGUAGES = i18nConfig.supportedLanguages;
export const DEFAULT_LANGUAGE = i18nConfig.fallbackLanguage;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

/** Every language hint resolves to the one language Kel ships. */
export function normalizeLanguageCode(_language?: string | null): SupportedLanguage {
  return DEFAULT_LANGUAGE;
}
