/**
 * V2-05 — the installability contract for Kel on a phone.
 *
 * The donor line already ships the PWA machinery (manifest, icons, a careful service worker). These
 * pins exist so that machinery stays true while V2-05 does its real work on the phone surface: the
 * manifest must keep the fields a home-screen install needs, its icons must actually be on disk, and
 * the service worker must keep never caching the engine or the app's own API — a remote phone replaying
 * a stale Kel state after going offline would be worse than showing nothing.
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

// tests/unit → desktop → kel-v2 (the repository root), so the paths below read like the tree does.
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');
const manifestPath = 'desktop/public/manifest.webmanifest';
const manifest = JSON.parse(read(manifestPath)) as {
  name: string;
  short_name: string;
  description: string;
  start_url: string;
  scope: string;
  display: string;
  background_color: string;
  theme_color: string;
  icons: Array<{ src: string; sizes: string; type: string }>;
};

describe('Kel as an installable app (V2-05)', () => {
  it('has everything a home screen needs', () => {
    expect(manifest.name).toBe('Kel');
    expect(manifest.short_name).toBe('Kel');
    expect(manifest.display).toBe('standalone');
    expect(manifest.start_url).toBe('./');
    expect(manifest.scope).toBe('./');
    expect(manifest.theme_color).toMatch(/^#[0-9a-f]{6}$/i);
    expect(manifest.background_color).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it('names the app in Kel words rather than the donor line words', () => {
    // The phrase this replaced ("Kel WebUI for mobile and desktop browsers") described the donor's
    // project, not what Nick installs. Keep the description about the app he is installing.
    expect(manifest.description).not.toMatch(/webui/i);
    expect(manifest.description).toMatch(/phone|work|conversation/i);
  });

  it('ships the icons it promises, including the two sizes an install picks between', () => {
    expect(manifest.icons).toHaveLength(2);
    const sizes = manifest.icons.map((icon) => icon.sizes);
    expect(sizes).toContain('192x192');
    expect(sizes).toContain('512x512');
    for (const icon of manifest.icons) {
      expect(icon.type).toBe('image/png');
      const onDisk = path.join(repoRoot, 'desktop/public', icon.src.replace('./', ''));
      expect(existsSync(onDisk), onDisk).toBe(true);
    }
    // iOS ignores the manifest's icons and uses this one, so it has to exist too.
    expect(existsSync(path.join(repoRoot, 'desktop/public/pwa/icon-180.png'))).toBe(true);
  });

  it('links the manifest and the iOS tags from the shell the phone loads', () => {
    const shell = read('desktop/packages/desktop/src/renderer/index.html');
    expect(shell).toContain('rel="manifest"');
    expect(shell).toContain('name="apple-mobile-web-app-capable"');
    expect(shell).toContain('apple-touch-icon');
    expect(shell).toContain('viewport-fit=cover');
  });

  it('never caches the engine or the app API on the phone', () => {
    const worker = read('desktop/public/sw.js');
    expect(worker).toContain("url.pathname.startsWith('/api/')");
    // The engine gateway the remote client uses is /kel/…; the test above is the app API. Both are
    // gated data, and neither may be replayed from a cache.
    const renderer = read('desktop/packages/desktop/src/renderer/services/registerPwa.ts');
    expect(renderer).toContain("navigator.serviceWorker.register(SERVICE_WORKER_URL, { scope: './' })");
    // The worker is only for a browser origin: never inside the desktop shell.
    expect(renderer).toContain('isElectronDesktop()');
  });
});
