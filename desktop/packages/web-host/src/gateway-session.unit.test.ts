/**
 * D3 — gateway session enforcement tests.
 *
 * Pins the security boundary of the remote WebUI: without a session the backend's auth authority
 * accepts, the gateway refuses proxied API calls (including the anonymous password-reset takeover
 * that shipped before D3) while keeping the SPA's login boot flow working.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { startStaticServer, type StaticServerHandle } from './static-server.js';

const VALID_COOKIE = 'aionui-session=good';

type BackendRequest = { method: string; url: string; cookie: string | undefined };
type MockBackend = { port: number; requests: BackendRequest[]; close: () => Promise<void> };

async function startMockBackend(): Promise<MockBackend> {
  const requests: BackendRequest[] = [];
  let sessionRevoked = false;
  const server = http.createServer((req, res) => {
    requests.push({ method: req.method || 'GET', url: req.url || '/', cookie: req.headers.cookie });
    if ((req.url || '').startsWith('/api/auth/user')) {
      if (req.headers.cookie === VALID_COOKIE && !sessionRevoked) {
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ success: true, user: { id: 'admin', username: 'admin' } }));
      } else {
        res.writeHead(401, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ success: false }));
      }
      return;
    }
    if ((req.url || '').startsWith('/api/webui/reset-password')) {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ data: { new_password: 'should-never-be-reachable-anonymously' } }));
      return;
    }
    if ((req.url || '').startsWith('/logout')) {
      sessionRevoked = true;
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ success: true }));
      return;
    }
    if ((req.url || '').startsWith('/login')) {
      res.writeHead(200, { 'content-type': 'application/json', 'set-cookie': VALID_COOKIE + '; Path=/' });
      res.end(JSON.stringify({ success: true, user: { id: 'admin', username: 'admin' } }));
      return;
    }
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ items: [], sawCookie: req.headers.cookie || null }));
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('mock backend failed to listen');
  return {
    port: address.port,
    requests,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

async function startMockWsBackend(): Promise<{ port: number; close: () => Promise<void> }> {
  // Net-level dual-protocol fixture (the pattern the other WS tests use): answers the session
  // validation with a plain HTTP 200 and any other HTTP request with an upgrade 101.
  const server = net.createServer((socket) => {
    let buffered = '';
    socket.on('data', (chunk) => {
      buffered += chunk.toString('latin1');
      if (!buffered.includes('\r\n\r\n')) return;
      if (/^GET \/api\/auth\/user/.test(buffered)) {
        const allowed = /cookie:\s*aionui-session=good/i.test(buffered);
        const body = allowed ? '{"success":true}' : '{"success":false}';
        socket.end(
          `HTTP/1.1 ${allowed ? 200 : 401} ${allowed ? 'OK' : 'Unauthorized'}\r\nContent-Type: application/json\r\nContent-Length: ${body.length}\r\nConnection: close\r\n\r\n${body}`
        );
        return;
      }
      socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n');
    });
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('mock ws backend failed to listen');
  return { port: address.port, close: () => new Promise<void>((resolve) => server.close(() => resolve())) };
}

describe('D3 gateway session enforcement', () => {
  let staticDir = '';
  let backend: MockBackend;
  let handle: StaticServerHandle | null = null;

  beforeEach(async () => {
    staticDir = await fs.mkdtemp(path.join(os.tmpdir(), 'kel-gw-'));
    await fs.writeFile(path.join(staticDir, 'index.html'), '<!doctype html><html><body>Kel</body></html>');
    backend = await startMockBackend();
  });

  afterEach(async () => {
    if (handle) await handle.stop();
    handle = null;
    await backend.close();
    await fs.rm(staticDir, { recursive: true, force: true });
  });

  const start = async (extra: Record<string, unknown> = {}) => {
    handle = await startStaticServer({
      staticDir,
      backendPort: backend.port,
      port: 0,
      requireAuth: true,
      ...extra,
    });
    return handle;
  };

  it('refuses anonymous business API calls without touching the backend', async () => {
    const server = await start();
    const response = await fetch(`${server.localUrl}/api/conversations?page_size=1`);
    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body.code).toBe('UNAUTHORIZED');
    expect(backend.requests).toHaveLength(0);
  });

  it('refuses anonymous password reset (the shipped takeover) without touching the backend', async () => {
    const server = await start();
    const response = await fetch(`${server.localUrl}/api/webui/reset-password`, { method: 'POST' });
    expect(response.status).toBe(401);
    expect(backend.requests).toHaveLength(0);
  });

  it('keeps the SPA boot flow anonymous: /api/auth/user, /login, /qr-login', async () => {
    const server = await start();
    const user = await fetch(`${server.localUrl}/api/auth/user`);
    expect(user.status).toBe(401); // the backend's own answer, forwarded
    const login = await fetch(`${server.localUrl}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'x' }),
    });
    expect(login.status).toBe(200);
    const qr = await fetch(`${server.localUrl}/qr-login?token=abc`, { redirect: 'manual' });
    expect([200, 302, 303].includes(qr.status) || qr.status === 404).toBe(true);
    expect(backend.requests.map((r) => r.url.split('?')[0])).toEqual([
      '/api/auth/user',
      '/login',
      '/qr-login',
    ]);
  });

  it('allows a session the backend authority accepts and forwards it untouched', async () => {
    const server = await start();
    const response = await fetch(`${server.localUrl}/api/conversations?page_size=1`, {
      headers: { cookie: VALID_COOKIE },
    });
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.sawCookie).toBe(VALID_COOKIE);
    // one validation call + one proxied call
    expect(backend.requests.map((r) => r.url.split('?')[0])).toEqual(['/api/auth/user', '/api/conversations']);
  });

  it('caches the validation verdict per cookie', async () => {
    const server = await start();
    await fetch(`${server.localUrl}/api/conversations`, { headers: { cookie: VALID_COOKIE } });
    await fetch(`${server.localUrl}/api/assistants`, { headers: { cookie: VALID_COOKIE } });
    const authChecks = backend.requests.filter((r) => r.url.startsWith('/api/auth/user'));
    expect(authChecks).toHaveLength(1);
  });

  it('rejects a session the backend authority does not accept', async () => {
    const server = await start();
    const response = await fetch(`${server.localUrl}/api/conversations`, {
      headers: { cookie: 'aionui-session=stale' },
    });
    expect(response.status).toBe(401);
    // validation attempted, business route never forwarded
    expect(backend.requests.every((r) => r.url.startsWith('/api/auth/user'))).toBe(true);
  });

  it('drops the cached verdict when the session logs out', async () => {
    const server = await start();
    const first = await fetch(`${server.localUrl}/api/conversations`, { headers: { cookie: VALID_COOKIE } });
    expect(first.status).toBe(200); // warms the 5s validation cache
    const logout = await fetch(`${server.localUrl}/logout`, { method: 'POST', headers: { cookie: VALID_COOKIE } });
    expect(logout.status).toBe(200);
    const after = await fetch(`${server.localUrl}/api/conversations`, { headers: { cookie: VALID_COOKIE } });
    expect(after.status).toBe(401); // cache invalidated on logout; authority now rejects
  });

  it('gates WebSocket upgrades: anonymous refused, valid session spliced', async () => {
    const wsBackend = await startMockWsBackend();
    handle = await startStaticServer({
      staticDir,
      backendPort: wsBackend.port,
      port: 0,
      requireAuth: true,
    });
    const port = handle.port;

    const anonymous = await new Promise<{ status: string }>((resolve, reject) => {
      const socket = net.connect(port, '127.0.0.1', () => {
        socket.write(
          'GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n'
        );
      });
      socket.once('data', (data) => {
        resolve({ status: data.toString('latin1').split('\r\n')[0] });
        socket.destroy();
      });
      socket.once('error', reject);
    });
    expect(anonymous.status).toContain('401');
    await wsBackend.close();
  });

  it('gates WebSocket upgrades with a valid session through to the backend', async () => {
    const wsBackend = await startMockWsBackend();
    handle = await startStaticServer({
      staticDir,
      backendPort: wsBackend.port,
      port: 0,
      requireAuth: true,
    });
    const port = handle.port;

    const upgraded = await new Promise<string>((resolve, reject) => {
      const socket = net.connect(port, '127.0.0.1', () => {
        socket.write(
          `GET /ws HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nCookie: ${VALID_COOKIE}\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n`
        );
      });
      socket.once('data', (data) => {
        resolve(data.toString('latin1').split('\r\n')[0]);
        socket.destroy();
      });
      socket.once('error', reject);
    });
    expect(upgraded).toContain('101');
    await wsBackend.close();
  });

  it('keeps raw pass-through when requireAuth is off (library default)', async () => {
    handle = await startStaticServer({ staticDir, backendPort: backend.port, port: 0 });
    const response = await fetch(`${handle.localUrl}/api/conversations`);
    expect(response.status).toBe(200);
  });
});
