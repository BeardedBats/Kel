/**
 * D2 — Kel's update path never touches donor infrastructure and fails closed on its own releases.
 *
 * The electron-updater feed is disabled (no CDN configured); the manual check in updateBridge.ts
 * targets the Kel repository and fails closed until Kel publishes release assets there.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoDesktop = path.resolve(here, '..', '..');
const read = (relative: string) => readFileSync(path.join(repoDesktop, relative), 'utf8');

describe('update infrastructure policy (D2)', () => {
  it('the auto-update feed never points at donor infrastructure', () => {
    const feed = read('packages/desktop/src/process/services/updateFeed.ts');
    expect(feed).not.toMatch(/static\.aionui\.com/);
    expect(feed).toContain("CDN_UPDATE_BASE_URL = ''");
    expect(feed).toContain('buildCdnFeedOptions');
  });

  it('the auto-updater skips checks when no feed is configured', () => {
    const service = read('packages/desktop/src/process/services/autoUpdaterService.ts');
    expect(service).toContain('_feedConfigured');
    expect(service).not.toContain('static.aionui.com');
    expect(service).toContain('No update feed configured');
  });

  it('the manual update check targets the Kel repository and no donor CDN', () => {
    const bridge = read('packages/desktop/src/process/bridge/updateBridge.ts');
    expect(bridge).toContain("DEFAULT_REPO = 'BeardedBats/Kel'");
    expect(bridge).toContain("CDN_BASE_URL = 'https://github.com/BeardedBats/Kel/releases/download'");
    expect(bridge).not.toMatch(/static\.aionui\.com/);
  });
});
