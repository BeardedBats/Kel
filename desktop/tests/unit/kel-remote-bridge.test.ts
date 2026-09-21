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

  it('the gateway reaches the engine the way the desktop does, not the way a browser does', () => {
    // Kel's engine authorizes a request only when Host is its own and Origin is absent or its own
    // (`runtime/kel/service.py`). A phone browser always sends the gateway's own Origin, so forwarding
    // it made every mutating Kel route answer 403 — Kel on a phone could read /api/state and nothing
    // else. The gateway holds the token and is the trusted local client, so it must look like one.
    expect(staticServer).toContain("delete headers.origin;");
    expect(staticServer).toContain("delete headers.referer;");
  });

  it('both launchers hand the gateway the engine data root', () => {
    expect(webuiConfig).toContain('kelDataDir: kelEngineDataRoot()');
    expect(webui).toContain('const kelDataDir = process.env.KEL_DATA_DIR?.trim() || undefined');
    // The same root seeds the browser profile's Kel assistant — the phone's send gate (V2-05).
    expect(webui).toContain('dataRoot: kelDataDir,');
  });
});

describe('remote failure language (D13)', () => {
  it('turns gateway codes into sentences and never shows the raw code', () => {
    expect(kelApi).toContain('const GATEWAY_FAILURE_TEXT: Record<string, string> = {');
    expect(kelApi).toContain('KEL_ENGINE_UNAVAILABLE:');
    expect(kelApi).toContain('KEL_ENGINE_UNREACHABLE:');
    expect(kelApi).toContain("Kel isn't running on the computer that serves this page right now.");
    expect(kelApi).toContain('Kel stopped answering on that computer. Your work is kept — try again in a moment.');
    // The message is looked up by code; the raw code is never thrown as the message itself.
    expect(kelApi).toContain('GATEWAY_FAILURE_TEXT[code] ??');
    expect(kelApi).not.toContain("throw new Error(message);");
  });

  it('treats a browser-level network drop as a device problem, not a Kel fault', () => {
    expect(kelApi).toContain("This device can't reach Kel right now — check the connection and try again.");
    expect(kelApi).toContain('let response: Response;');
  });
});
