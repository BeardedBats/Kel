/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * D-61: Kel ships in English (en-US) only, so the document is always left-to-right and tagged
 * `lang="en-US"` (which drives spell-check and assistive technology).
 */

import { DEFAULT_LANGUAGE } from '@/common/config/i18n';

export function applyDocumentDirection(_language?: string | null): void {
  if (typeof document === 'undefined') return;
  document.documentElement.dir = 'ltr';
  document.documentElement.lang = DEFAULT_LANGUAGE;
}
