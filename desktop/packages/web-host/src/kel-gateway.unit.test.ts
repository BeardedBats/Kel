/**
 * D11 — the Kel gateway: the remote browser reaches Kel's own engine through the session-gated
 * `/kel/*` proxy. Pins: anonymous is refused; a live session is forwarded to the engine with the
 * process-held bearer (and the browser's cookie is stripped); a missing descriptor and a dead
 * engine both fail closed; the bearer never appears in a response body.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { startStaticServer, type StaticServerHandle } from './static-server.js';

const VALID_COOKIE = 'aionui-session=good';
const ENGINE_TOKEN = 'kel-engine-secret-token';

type SeenRequest = { method: string; url: string; authorization: string | undefined; cookie: string | undefined };

async function startMockAuth(): Promise<{ port: number; close: () => Promise<void> }> {
  const server = http.createServer((req, res) => {
    if ((req.url || '').startsWith('/api/auth/user')) {
      if (req.headers.cookie === VALID_COOKIE) {
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ success: true, user: { id: 'admin', username: 'admin' } }));
      } else {
        res.writeHead(401, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ success: false }));
      }
      return;
    }
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('mock auth failed to listen');
  return { port: address.port, close: () => new Promise<void>((resolve) => server.close(() => resolve())) };
}

async function startMockEngine(): Promise<{ url: string; port: number; seen: SeenRequest[]; close: () => Promise<void> }> {
  const seen: SeenRequest[] = [];
  const server = http.createServer((req, res) => {
    seen.push({
      method: req.method || 'GET',
      url: req.url || '/',
      authorization: req.headers.authorization,
      cookie: req.headers.cookie,
    });
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ answer: 'from the engine' }));
  });
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('mock engine failed to listen');
  return {
    url: `http://127.0.0.1:${address.port}`,
    port: address.port,
    seen,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

describe('Kel gateway (D11)', () => {
  let dir: string;
  let auth: { port: number; close: () => Promise<void> };
  let engine: Awaited<ReturnType<typeof startMockEngine>>;
  let handle: StaticServerHandle;

  const url = (pathname: string) => `http://127.0.0.1:${handle.port}${pathname}`;

  beforeEach(async () => {
    dir = await fs.mkdtemp(path.join(os.tmpdir(), 'kel-gateway-'));
    auth = await startMockAuth();
    engine = await startMockEngine();
    await fs.writeFile(
      path.join(dir, 'desktop-session.json'),
      JSON.stringify({ url: engine.url, token: ENGINE_TOKEN, pid: 1234 })
    );
    handle = await startStaticServer({
      staticDir: dir, // a static dir is required but never hit for /kel/*
      backendPort: auth.port,
      requireAuth: true,
      kelDataDir: dir,
    });
  });

  afterEach(async () => {
    await handle.stop();
    await engine.close();
    await auth.close();
    await fs.rm(dir, { recursive: true, force: true });
  });

  it('refuses anonymous access to the engine', async () => {
    const response = await fetch(url('/kel/api/state'), { method: 'POST' });
    expect(response.status).toBe(401);
    expect(engine.seen).toHaveLength(0); // the engine is never even contacted
  });

  it('forwards a live session to the engine with the process-held bearer, stripping the cookie', async () => {
    const response = await fetch(url('/kel/api/state'), {
      method: 'POST',
      headers: { cookie: VALID_COOKIE, 'content-type': 'application/json' },
      body: JSON.stringify({ conversation: 'main' }),
    });
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toEqual({ answer: 'from the engine' });
    expect(engine.seen).toHaveLength(1);
    expect(engine.seen[0].authorization).toBe(`Bearer ${ENGINE_TOKEN}`);
    expect(engine.seen[0].url).toBe('/api/state');
    expect(engine.seen[0].cookie).toBeUndefined();
    expect(JSON.stringify(body)).not.toContain(ENGINE_TOKEN);
  });

  it('fails closed with 503 when no engine descriptor exists', async () => {
    await fs.rm(path.join(dir, 'desktop-session.json'));
    const response = await fetch(url('/kel/api/state'), {
      method: 'POST',
      headers: { cookie: VALID_COOKIE },
    });
    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ error: 'KEL_ENGINE_UNAVAILABLE' });
  });

  it('fails closed with 502 when the engine is not listening', async () => {
    await engine.close();
    const response = await fetch(url('/kel/api/state'), {
      method: 'POST',
      headers: { cookie: VALID_COOKIE },
    });
    expect(response.status).toBe(502);
    expect(await response.json()).toMatchObject({ error: 'KEL_ENGINE_UNREACHABLE' });
  });
});
