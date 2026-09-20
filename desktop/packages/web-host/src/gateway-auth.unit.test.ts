/**
 * D3 — gateway integration tests: browser login/session lifecycle and engine-token injection.
 *
 * The static server is the only browser path to the engine. These tests pin:
 *  - unauthenticated API access is refused (401),
 *  - login issues a session cookie; refresh renews it; logout kills it,
 *  - proxied requests carry `Authorization: Bearer <engine token>` and never the browser's
 *    origin/cookies,
 *  - login throttling and the LAN-without-auth refusal.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import type { AddressInfo } from 'node:net';
import { startStaticServer, type StaticServerHandle } from './static-server.js';
import { ensureInitialPassword, generateWebUiQrToken, SESSION_COOKIE } from './auth.js';

const ENGINE_TOKEN = 'engine-token-for-tests';

type Captured = { url?: string; headers: http.IncomingHttpHeaders; body: string };

async function mkRendererFixture(): Promise<string> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'kel-gw-'));
  await fs.writeFile(path.join(dir, 'index.html'), '<!doctype html><title>kel</title>');
  return dir;
}

async function startMockBackend(): Promise<{
  port: number;
  captured: Captured[];
  close: () => Promise<void>;
}> {
  const captured: Captured[] = [];
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (chunk: Buffer) => (body += chunk.toString()));
    req.on('end', () => {
      captured.push({ url: req.url, headers: req.headers, body });
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: true, path: req.url }));
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', () => resolve()));
  const port = (server.address() as AddressInfo).port;
  return { port, captured, close: () => new Promise<void>((r) => server.close(() => r())) };
}

function cookieFrom(response: Response): string {
  const setCookie = response.headers.get('set-cookie') || '';
  const match = new RegExp(`${SESSION_COOKIE}=([^;]+)`).exec(setCookie);
  return match ? `${SESSION_COOKIE}=${match[1]}` : '';
}

describe('gateway auth (D3)', () => {
  let handle: StaticServerHandle | null = null;
  let stopBackend: (() => Promise<void>) | null = null;
  let staticDir = '';
  let userDataPath = '';
  let backend: Awaited<ReturnType<typeof startMockBackend>>;

  beforeEach(async () => {
    staticDir = await mkRendererFixture();
    userDataPath = await fs.mkdtemp(path.join(os.tmpdir(), 'kel-data-'));
    backend = await startMockBackend();
    stopBackend = backend.close;
    handle = await startStaticServer({
      staticDir,
      backendPort: backend.port,
      port: 0,
      auth: { userDataPath, bearerToken: ENGINE_TOKEN },
    });
  });

  afterEach(async () => {
    if (handle) {
      await handle.stop();
      handle = null;
    }
    if (stopBackend) {
      await stopBackend();
      stopBackend = null;
    }
    await fs.rm(staticDir, { recursive: true, force: true });
    await fs.rm(userDataPath, { recursive: true, force: true });
  });

  it('refuses API calls without a session', async () => {
    const res = await fetch(`${handle!.localUrl}/api/state`);
    expect(res.status).toBe(401);
    expect(backend.captured.length).toBe(0);
  });

  it('serves the login page assets without auth', async () => {
    const res = await fetch(`${handle!.localUrl}/login`);
    expect(res.status).toBe(200);
    expect(await res.text()).toContain('<title>kel</title>');
  });

  it('reports needs_setup until a password exists', async () => {
    const before = await (await fetch(`${handle!.localUrl}/api/auth/status`)).json();
    expect(before.needs_setup).toBe(true);
    ensureInitialPassword(userDataPath);
    const after = await (await fetch(`${handle!.localUrl}/api/auth/status`)).json();
    expect(after.needs_setup).toBe(false);
  });

  it('logs in, proxies with the engine token injected, and logs out', async () => {
    const { password } = ensureInitialPassword(userDataPath);
    const bad = await fetch(`${handle!.localUrl}/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'nope' }),
    });
    expect(bad.status).toBe(401);

    const login = await fetch(`${handle!.localUrl}/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', origin: 'http://evil.example' },
      body: JSON.stringify({ username: 'admin', password }),
    });
    expect(login.status).toBe(200);
    const payload = await login.json();
    expect(payload.success).toBe(true);
    expect(payload.user.username).toBe('admin');
    const cookie = cookieFrom(login);
    expect(cookie).not.toBe('');

    const user = await fetch(`${handle!.localUrl}/api/auth/user`, { headers: { cookie } });
    expect(user.status).toBe(200);
    expect((await user.json()).user.username).toBe('admin');

    const proxied = await fetch(`${handle!.localUrl}/api/state?conversation=main`, {
      headers: { cookie, origin: 'http://evil.example' },
    });
    expect(proxied.status).toBe(200);
    const captured = backend.captured.at(-1)!;
    expect(captured.url).toBe('/api/state?conversation=main');
    expect(captured.headers.authorization).toBe(`Bearer ${ENGINE_TOKEN}`);
    expect(captured.headers.origin).toBeUndefined();
    expect(captured.headers.cookie).toBeUndefined();

    const refresh = await fetch(`${handle!.localUrl}/api/auth/refresh`, { method: 'POST', headers: { cookie } });
    expect(refresh.status).toBe(200);
    expect(cookieFrom(refresh)).not.toBe('');

    const logout = await fetch(`${handle!.localUrl}/logout`, { method: 'POST', headers: { cookie } });
    expect(logout.status).toBe(200);
    const afterLogout = await fetch(`${handle!.localUrl}/api/state`, { headers: { cookie } });
    expect(afterLogout.status).toBe(401);
  });

  it('throttles repeated login failures', async () => {
    ensureInitialPassword(userDataPath);
    for (let attempt = 0; attempt < 8; attempt += 1) {
      const res = await fetch(`${handle!.localUrl}/login`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ username: 'admin', password: 'wrong' }),
      });
      expect(res.status).toBe(401);
    }
    const throttled = await fetch(`${handle!.localUrl}/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'wrong' }),
    });
    expect(throttled.status).toBe(429);
    expect((await throttled.json()).code).toBe('tooManyAttempts');
  });

  it('accepts a QR login token exactly once', async () => {
    ensureInitialPassword(userDataPath);
    const { token } = generateWebUiQrToken();
    const first = await fetch(`${handle!.localUrl}/qr-login?token=${token}`, { redirect: 'manual' });
    expect(first.status).toBe(302);
    const cookie = cookieFrom(first);
    expect(cookie).not.toBe('');
    const api = await fetch(`${handle!.localUrl}/api/state`, { headers: { cookie } });
    expect(api.status).toBe(200);

    const second = await fetch(`${handle!.localUrl}/qr-login?token=${token}`, { redirect: 'manual' });
    expect(second.status).toBe(302);
    expect(second.headers.get('location')).toBe('/login?error=qr');
  });

  it('refuses LAN binding without authentication', async () => {
    await expect(
      startStaticServer({ staticDir, backendPort: backend.port, port: 0, allowRemote: true })
    ).rejects.toThrow(/without authentication/);
  });

  it('keeps the legacy pass-through when no auth is configured', async () => {
    const legacy = await startStaticServer({ staticDir, backendPort: backend.port, port: 0 });
    try {
      const res = await fetch(`${legacy.localUrl}/api/anything`);
      expect(res.status).toBe(200);
      expect(backend.captured.at(-1)!.headers.authorization).toBeUndefined();
    } finally {
      await legacy.stop();
    }
  });
});
