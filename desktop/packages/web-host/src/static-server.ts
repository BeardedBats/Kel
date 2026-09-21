/**
 * WebUI static server.
 *
 * Serves out/renderer/ as the SPA and reverse-proxies /api/*, /ws, /api/stt/stream,
 * /login and /logout to aioncore. All auth goes to backend's aionui-auth crate;
 * /login and /logout are aionui-auth's top-level paths, the rest live under
 * /api/auth/*. /ws and /api/stt/stream are WebSocket/stream upgrades spliced at
 * TCP level; /api/stt/stream is the STT streaming endpoint.
 *
 * Design: Node native http + serve-handler. No Express. No business routes.
 */

import http, { type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { networkInterfaces } from 'node:os';
import net, { type Socket } from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import serveHandler from 'serve-handler';

export type StaticServerOptions = {
  staticDir: string;
  backendPort: number;
  port?: number;
  allowRemote?: boolean;
  /**
   * D3 — gateway session enforcement: refuse proxied requests without a live backend session
   * (anonymous allowlist: /login, /logout, /qr-login, /api/auth/*). The shipping entry points
   * set this; the library default stays false so unit tests can exercise raw proxying.
   */
  requireAuth?: boolean;
  /**
   * D11 — the Kel gateway: when set, `/kel/*` is proxied to the Kel engine whose descriptor
   * (`desktop-session.json`) lives in this directory. The engine's bearer token is read
   * server-side per request and never reaches the browser; the route is session-gated exactly
   * like the rest of the gateway. Without this option `/kel/*` falls through to the SPA.
   */
  kelDataDir?: string;
};

export type StaticServerHandle = {
  port: number;
  url: string;
  localUrl: string;
  networkUrl?: string;
  lanIP?: string;
  stop: () => Promise<void>;
};

const DEFAULT_PORT = 25808;

const AUTH_VALIDATION_TTL_MS = 5_000;
const AUTH_VALIDATION_NEGATIVE_TTL_MS = 2_000;
const AUTH_VALIDATION_CACHE_LIMIT = 128;

// D3 — anonymous allowlist: exactly what the SPA's boot flow needs. Everything else — business
// APIs, /api/webui/* administration, internal /api/auth/* helpers — requires a live session.
const ANONYMOUS_ROUTES = new Set([
  '/login',
  '/logout',
  '/qr-login',
  '/api/auth/user',
  '/api/auth/status',
  '/api/auth/refresh',
]);

const isProxyRoute = (url: string): boolean =>
  url.startsWith('/api/') ||
  url.startsWith('/api?') ||
  url === '/login' ||
  url === '/logout' ||
  url === '/qr-login' ||
  url.startsWith('/qr-login?');

const replyJson = (res: ServerResponse, status: number, body: Record<string, unknown>): void => {
  const raw = Buffer.from(JSON.stringify(body));
  res.writeHead(status, { 'content-type': 'application/json', 'content-length': String(raw.length) });
  res.end(raw);
};

/**
 * Session enforcement for the remote gateway.
 *
 * The backend (aioncore) keeps sessions, but it runs in local mode and does not gate business
 * routes; only its own /api/auth/user answers truthfully about a session. The gateway asks that
 * authority and caches the verdict briefly per cookie value. Positives live 5s, negatives 2s
 * (credential-spam damping); transport errors fail closed without caching. Logout drops the
 * cached verdict so a revoked cookie is re-checked on its very next use.
 */
function createSessionValidator(backendPort: number): {
  validate: (cookie: string | undefined) => Promise<boolean>;
  invalidate: (cookie: string | undefined) => void;
} {
  const cache = new Map<string, { valid: boolean; until: number }>();
  const remember = (cookie: string, valid: boolean): void => {
    cache.set(cookie, {
      valid,
      until: Date.now() + (valid ? AUTH_VALIDATION_TTL_MS : AUTH_VALIDATION_NEGATIVE_TTL_MS),
    });
    while (cache.size > AUTH_VALIDATION_CACHE_LIMIT) {
      const oldest = cache.keys().next().value;
      if (oldest === undefined) break;
      cache.delete(oldest);
    }
  };
  return {
    validate: async (cookie) => {
      if (!cookie) return false;
      const cached = cache.get(cookie);
      if (cached && cached.until > Date.now()) return cached.valid;
      try {
        const response = await fetch(`http://127.0.0.1:${backendPort}/api/auth/user`, { headers: { cookie } });
        if (response.ok) {
          remember(cookie, true);
          return true;
        }
        if (response.status === 401 || response.status === 403) {
          remember(cookie, false);
          return false;
        }
        return false;
      } catch {
        return false;
      }
    },
    invalidate: (cookie) => {
      if (cookie) cache.delete(cookie);
    },
  };
}

// Ranges that are non-internal IPv4 yet never a reachable LAN address, so we
// must never advertise them as the WebUI access URL even when they are the only
// non-loopback interface present:
//   169.254.0.0/16  link-local / APIPA (host got no DHCP lease)
//   198.18.0.0/15   RFC 2544 benchmarking range — handed out by utility tunnels
//                   such as Cloudflare WARP; this is the address that showed up
//                   on a multi-NIC machine instead of the real LAN IP.
const isUnreachableLanRange = (addr: string): boolean => addr.startsWith('169.254.') || /^198\.(18|19)\./.test(addr);

// Rank candidate LAN addresses by how likely they are the network the user
// actually reaches the desktop on. Lower is better. Private (RFC 1918) home /
// office ranges win over anything else; 192.168/16 is the most common LAN, then
// the 172.16/12 block, then 10/8 (frequently carved up by VPNs / corp routing).
const rankLanCandidate = (addr: string): number => {
  if (addr.startsWith('192.168.')) return 0;
  if (/^172\.(1[6-9]|2\d|3[01])\./.test(addr)) return 1;
  if (addr.startsWith('10.')) return 2;
  return 3;
};

// Pick the best LAN IPv4 to advertise. Pure over the interface map so it can be
// unit-tested against real multi-NIC layouts. Iterating and returning the first
// non-internal hit (the old behavior) picks whatever the OS lists first, which
// on a multi-NIC box can be a VPN / benchmark adapter rather than the LAN.
export function pickLanIP(nets: ReturnType<typeof networkInterfaces>): string | null {
  const candidates: string[] = [];
  for (const name of Object.keys(nets)) {
    for (const iface of nets[name] || []) {
      if (iface.family !== 'IPv4' || iface.internal) continue;
      if (isUnreachableLanRange(iface.address)) continue;
      candidates.push(iface.address);
    }
  }
  // Stable sort keeps OS interface order among equally-ranked addresses (e.g. a
  // physical NIC listed before a VPN when both are 10/8).
  candidates.sort((a, b) => rankLanCandidate(a) - rankLanCandidate(b));
  return candidates[0] ?? null;
}

function getLanIP(): string | null {
  return pickLanIP(networkInterfaces());
}

function forwardToBackend(req: IncomingMessage, res: ServerResponse, backendPort: number): void {
  const options: http.RequestOptions = {
    hostname: '127.0.0.1',
    port: backendPort,
    path: req.url,
    method: req.method,
    headers: { ...req.headers, host: `127.0.0.1:${backendPort}` },
  };
  const proxy = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxy.on('error', () => {
    if (!res.headersSent) {
      res.writeHead(502, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ error: 'BACKEND_UNREACHABLE' }));
    } else {
      res.destroy();
    }
  });
  req.pipe(proxy);
}

/**
 * D11 — resolve the running Kel engine from the desktop's own descriptor. Read per request so a
 * restarted engine (new port/token) is picked up immediately; failures fail closed.
 */
async function readKelEngine(kelDataDir: string): Promise<{ url: string; token: string } | null> {
  try {
    const raw = await fs.promises.readFile(path.join(kelDataDir, 'desktop-session.json'), 'utf8');
    const parsed = JSON.parse(raw) as { url?: string; token?: string };
    if (!parsed.url || !parsed.token) return null;
    return { url: parsed.url, token: parsed.token };
  } catch {
    return null;
  }
}

/**
 * D11 — forward a browser request to the Kel engine with the process-held bearer token. The
 * browser's own session cookie is dropped: the engine authenticates on the bearer alone and never
 * sees aionui session material.
 *
 * The browser's `Origin`/`Referer` are dropped for the same reason. The engine accepts a request only
 * when `Host` is its own and `Origin` is absent or its own origin (`runtime/kel/service.py`), which is
 * how the desktop — a local client holding the token — reaches it. A phone browser always sends the
 * gateway's origin, so forwarding it verbatim made every mutating Kel route answer 403 and the shell
 * could only report "Kel is not answering right now". The gateway already stands in for the desktop
 * here: it holds the token, it is session-gated, and it must present itself as that local client.
 */
function forwardToKel(req: IncomingMessage, res: ServerResponse, engine: { url: string; token: string }): void {
  const target = new URL(engine.url);
  const headers: http.OutgoingHttpHeaders = { ...req.headers, host: target.host, authorization: `Bearer ${engine.token}` };
  delete headers.cookie;
  delete headers.origin;
  delete headers.referer;
  const options: http.RequestOptions = {
    hostname: target.hostname,
    port: target.port,
    path: (req.url ?? '/').replace(/^\/kel/, '') || '/',
    method: req.method,
    headers,
  };
  const proxy = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxy.on('error', () => {
    if (!res.headersSent) {
      replyJson(res, 502, { error: 'KEL_ENGINE_UNREACHABLE' });
    } else {
      res.destroy();
    }
  });
  req.pipe(proxy);
}

// Max bytes we peek before forcing a routing decision. An HTTP request-line
// on its own is typically < 100 bytes; a full header block is < 2 KB. If we
// haven't seen a newline after 4 KB the client is sending something weird —
// hand it to the internal HTTP server and let it return 400.
const PEEK_LIMIT_BYTES = 4096;

/**
 * Splice `client` to a TCP endpoint on `targetPort`. Any bytes already read
 * from `client` during peek are replayed to the upstream as the first write,
 * so the endpoint sees the full HTTP request as-sent.
 */
function spliceToTcpEndpoint(client: Socket, targetPort: number, initialBytes: Buffer): void {
  client.setNoDelay(true);
  client.setKeepAlive(true);
  client.setTimeout(0);
  // The peek phase left `client` in flowing mode (it had a 'data' listener),
  // but that listener is now removed and the real consumer — `client.pipe(upstream)`
  // — is only wired inside the async 'connect' handler below. Pause here so any
  // body bytes arriving in the gap are buffered by the socket instead of being
  // dropped for lack of a consumer; `pipe()` resumes the socket once connected.
  // Without this, large/buffered uploads (e.g. reverse-proxied POST bodies that
  // span multiple TCP segments) lose their tail bytes and the backend hangs
  // forever waiting for the missing Content-Length (issue #4058).
  client.pause();
  const upstream = net.connect({ host: '127.0.0.1', port: targetPort });
  upstream.setNoDelay(true);
  upstream.setKeepAlive(true);
  upstream.once('connect', () => {
    if (initialBytes.length > 0) upstream.write(initialBytes);
    upstream.pipe(client);
    client.pipe(upstream);
  });
  const tearDown = (): void => {
    client.destroy();
    upstream.destroy();
  };
  upstream.on('error', tearDown);
  client.on('error', tearDown);
  upstream.on('close', tearDown);
  client.on('close', tearDown);
}

/**
 * Decide routing from the first chunk of an incoming HTTP connection:
 *  - `true`  → `GET /ws[...] HTTP/1.x` or `GET /api/stt/stream[...] HTTP/1.x` (WebSocket/stream upgrades), splice to backend
 *  - `false` → any other HTTP method / path, hand to internal HTTP server
 *  - `null`  → need more bytes (no CRLF yet)
 *
 * We only check the request-line; `Upgrade: websocket` is not strictly
 * required — the backend will reject a non-upgrade GET on these paths on its own.
 * Keeping the rule simple means we can decide after the first ~50 bytes
 * instead of waiting for the full header block.
 */
function peekWsRoute(buf: Buffer): boolean | null {
  const newlineIdx = buf.indexOf(0x0a); // \n
  if (newlineIdx < 0) return null;
  const firstLine = buf.slice(0, newlineIdx).toString('ascii');
  return /^GET\s+\/(?:ws|api\/stt\/stream)(?:\?[^\s]*)?\s+HTTP\/1\.[01]\r?$/.test(firstLine);
}

export async function startStaticServer(opts: StaticServerOptions): Promise<StaticServerHandle> {
  const port = opts.port ?? DEFAULT_PORT;
  const allowRemote = opts.allowRemote === true;
  const host = allowRemote ? '0.0.0.0' : '127.0.0.1';
  const validateSession = opts.requireAuth === true ? createSessionValidator(opts.backendPort) : null;

  // The HTTP server listens only on loopback — user traffic hits the outer
  // net.Server first. We route to this server for everything except WS
  // upgrades and STT stream upgrades, which go straight to the backend via a raw TCP splice.
  //
  // Why two listeners instead of using `http.Server`'s native `upgrade` event:
  // bun 1.3's http-compat layer does not faithfully forward writes on the
  // socket delivered to the `upgrade` handler, so the backend's 101 response
  // never reaches the browser (see #2824). Making the outer listener pure
  // TCP avoids touching that code path on both bun and node.
  const http_server: Server = http.createServer(async (req, res) => {
    try {
      if (!req.url || !req.method) {
        res.writeHead(400).end();
        return;
      }

      // /api/* — reverse proxy to backend (includes /api/auth/*).
      // /login, /logout and /qr-login are aionui-auth's top-level endpoints: proxy them too so
      // WebUI browser clients reach the backend without a path-rewrite.
      if (isProxyRoute(req.url)) {
        // D3: the backend runs in local mode and does not enforce sessions on business routes, so
        // the gateway (the only network boundary) enforces here: everything outside the anonymous
        // allowlist needs a session the backend auth authority still accepts.
        if (validateSession) {
          const pathname = req.url.split('?')[0];
          if (pathname === '/logout' && req.method === 'POST') {
            // Drop the cached verdict so a logged-out cookie is re-checked on its next use.
            validateSession.invalidate(req.headers.cookie);
          } else if (!ANONYMOUS_ROUTES.has(pathname)) {
            const allowed = await validateSession.validate(req.headers.cookie);
            if (!allowed) {
              replyJson(res, 401, { success: false, error: 'Authentication required', code: 'UNAUTHORIZED' });
              return;
            }
          }
        }
        forwardToBackend(req, res, opts.backendPort);
        return;
      }

      // D11 — the Kel gateway: the remote browser reaches Kel's own engine here. Same session
      // authority as every other gated route; the engine bearer stays server-side; when the
      // engine is not running the caller gets an honest 503 instead of a broken page.
      if (opts.kelDataDir && req.url.startsWith('/kel/')) {
        if (validateSession) {
          const allowed = await validateSession.validate(req.headers.cookie);
          if (!allowed) {
            replyJson(res, 401, { success: false, error: 'Authentication required', code: 'UNAUTHORIZED' });
            return;
          }
        }
        const engine = await readKelEngine(opts.kelDataDir);
        if (!engine) {
          replyJson(res, 503, {
            error: 'KEL_ENGINE_UNAVAILABLE',
            message: 'Kel is not running on this machine right now.',
          });
          return;
        }
        forwardToKel(req, res, engine);
        return;
      }

      // static files + SPA fallback
      await serveHandler(req, res, {
        public: opts.staticDir,
        rewrites: [{ source: '**', destination: '/index.html' }],
      });
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(500, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ error: 'INTERNAL_ERROR' }));
      } else {
        res.destroy();
      }
    }
  });

  // Internal HTTP server — 127.0.0.1 ephemeral port, never visible to the user.
  await new Promise<void>((resolve, reject) => {
    http_server.once('error', reject);
    http_server.listen(0, '127.0.0.1', () => {
      http_server.off('error', reject);
      resolve();
    });
  });
  const internalPort = (http_server.address() as { port: number } | null)?.port;
  if (!internalPort) {
    throw new Error('internal HTTP server failed to bind to a port');
  }

  // User-facing listener: inspect the first line of every TCP connection and
  // route to either the backend (for /ws and /api/stt/stream upgrades) or the internal HTTP
  // server (everything else). Both routes use raw TCP splice — no reliance
  // on http.Server's upgrade event.
  const tcp_server = net.createServer((client: Socket) => {
    let peeked = Buffer.alloc(0);
    let settled = false;
    let upgradePending = false;
    const cleanup = (): void => {
      if (settled) return;
      settled = true;
      client.removeListener('data', onData);
      // Keep the error listener through rejection/close: a browser can reset
      // after a denied upgrade, when no splice owns this socket.
      client.removeListener('end', onEarlyEnd);
    };
    const onData = (chunk: Buffer): void => {
      peeked = Buffer.concat([peeked, chunk]);
      if (upgradePending) return; // keep collecting while the session check runs
      const decision = peekWsRoute(peeked);
      if (decision === null && peeked.length < PEEK_LIMIT_BYTES) return;
      if (decision === true && validateSession) {
        // Upgrades carry the session cookie in their header block; wait for it and validate the
        // session before splicing. Anonymous upgrades never reach the backend. The peek listener
        // stays attached while the check is in flight — bytes keep collecting into `peeked` — so
        // cleanup() and the splice still happen back-to-back in one tick, exactly like the
        // unauthenticated path this splice code was written for.
        const headerEnd = peeked.indexOf('\r\n\r\n');
        if (headerEnd < 0 && peeked.length < PEEK_LIMIT_BYTES) return;
        if (headerEnd < 0) {
          cleanup();
          spliceToTcpEndpoint(client, internalPort, peeked);
          return;
        }
        const headerText = peeked.slice(0, headerEnd).toString('latin1');
        const cookieLine = /^cookie:\s*(.+)$/im.exec(headerText);
        upgradePending = true;
        void validateSession.validate(cookieLine?.[1]).then((allowed) => {
          upgradePending = false;
          cleanup();
          if (allowed) {
            spliceToTcpEndpoint(client, opts.backendPort, peeked);
          } else {
            client.end('HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\nConnection: close\r\n\r\n');
          }
        });
        return;
      }
      cleanup();
      const target = decision === true ? opts.backendPort : internalPort;
      spliceToTcpEndpoint(client, target, peeked);
    };
    const onEarlyError = (): void => {
      cleanup();
      client.destroy();
    };
    const onEarlyEnd = (): void => {
      // Client closed before we saw a request line — nothing to route.
      cleanup();
      client.destroy();
    };
    client.on('data', onData);
    client.on('error', onEarlyError);
    client.on('end', onEarlyEnd);
  });

  await new Promise<void>((resolve, reject) => {
    tcp_server.once('error', reject);
    tcp_server.listen(port, host, () => {
      tcp_server.off('error', reject);
      resolve();
    });
  });

  const actualPort = (tcp_server.address() as { port: number } | null)?.port ?? port;
  const lanIP = allowRemote ? (getLanIP() ?? undefined) : undefined;
  const localUrl = `http://127.0.0.1:${actualPort}`;
  const networkUrl = lanIP ? `http://${lanIP}:${actualPort}` : undefined;

  return {
    port: actualPort,
    url: networkUrl ?? localUrl,
    localUrl,
    networkUrl,
    lanIP,
    stop: () =>
      new Promise<void>((resolve) => {
        tcp_server.close(() => {
          http_server.close(() => resolve());
        });
      }),
  };
}

export async function stopStaticServer(handle: StaticServerHandle): Promise<void> {
  await handle.stop();
}
