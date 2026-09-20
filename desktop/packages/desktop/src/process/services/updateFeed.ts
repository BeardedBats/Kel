/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { CdnGenericProvider } from './cdnGenericProvider';
import type { CdnGenericProviderConfiguration } from './cdnGenericProvider';

/**
 * Kel ships without an update CDN. The donor CDN is never consulted: the manual GitHub release
 * check in `updateBridge.ts` (repo `BeardedBats/Kel`) is the single source of truth and fails
 * closed until Kel publishes release assets there.
 *
 * Set this to a Kel-owned feed URL to re-enable the electron-updater channel; while it is empty,
 * `buildCdnFeedOptions()` returns null and the auto-updater skips checks entirely.
 */
export const CDN_UPDATE_BASE_URL = '';

export type CdnFeedOptions = CdnGenericProviderConfiguration & {
  updateProvider: typeof CdnGenericProvider;
};

export function buildCdnFeedOptions(): CdnFeedOptions | null {
  if (!CDN_UPDATE_BASE_URL) return null;
  return {
    provider: 'custom',
    url: CDN_UPDATE_BASE_URL,
    updateProvider: CdnGenericProvider,
  };
}
