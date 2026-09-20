/**
 * D11 — cross-device continuity pins: the same renderer works away from the desktop. Without the
 * preload bridge it talks to Kel's engine through the web-host's session-gated /kel gateway; the
 * desktop app wires its engine data root into that gateway; the dev CLI exposes it via KEL_DATA_DIR.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const kelApi = read('desktop/packages/desktop/src/renderer/components/kel/kelApi.ts');
const staticServer = read('desktop/packages/web-host/src/static-server.ts');
const webuiConfig = read('desktop/packages/desktop/src/process/utils/webuiConfig.ts');
const webui = read('desktop/scripts/webui.ts');

describe('remote Kel bridge (D11)', () => {
  it('the renderer falls back to the gateway instead of failing without the preload bridge', () => {
    expect(kelApi).toContain('if (api) return (await api.request(route, body)) as T;');
    expect(kelApi).toContain('fetch(`/kel${route}`');
    expect(kelApi).not.toContain('Kel bridge unavailable');
  });

  it('the gateway is session-gated, server-side, and fails closed', () => {
    expect(staticServer).toContain("if (opts.kelDataDir && req.url.startsWith('/kel/'))");
    expect(staticServer).toContain("readKelEngine");
    expect(staticServer).toContain("`Bearer ${engine.token}`");
    expect(staticServer).toContain("delete headers.cookie;");
    expect(staticServer).toContain("KEL_ENGINE_UNAVAILABLE");
  });

  it('both launchers hand the gateway the engine data root', () => {
    expect(webuiConfig).toContain('kelDataDir: kelEngineDataRoot()');
    expect(webui).toContain('kelDataDir: process.env.KEL_DATA_DIR?.trim() || undefined');
  });
});
