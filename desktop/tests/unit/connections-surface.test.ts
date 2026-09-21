/**
 * V2-01 — Connections: the model, the central management surface, and the one thing that must never
 * happen (a credential value travelling to the engine).
 *
 * The behavioural half runs the real credential-custody IPC against fake `electron` handles: it pins
 * that a connection's metadata is routed to /api/connections while a model provider's still goes to
 * /api/providers, that only field names and a pointer ever leave this process, and that a failed sync
 * never fails the custody action itself. The wiring half reads the files that make the surface
 * reachable, so a route or a palette entry cannot quietly disappear.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { handlers } = vi.hoisted(() => ({
  handlers: new Map<string, (event: unknown, ...args: unknown[]) => unknown>(),
}));

vi.mock('electron', () => ({
  app: { getPath: () => 'C:/fake/appdata', getVersion: () => '0.0.0-test' },
  safeStorage: {
    isEncryptionAvailable: () => true,
    encryptString: (value: string) => Buffer.from(`enc:${value}`, 'utf8'),
    decryptString: (buffer: Buffer) => buffer.toString('utf8').replace(/^enc:/, ''),
  },
  ipcMain: {
    handle: (channel: string, fn: (event: unknown, ...args: unknown[]) => unknown) => {
      handlers.set(channel, fn);
    },
    removeHandler: () => undefined,
  },
}));

import { registerKelCredentialIpc } from '@process/services/kel/kelCredentialIpc';
import {
  connectionCredentialField,
  connectionCustodyKey,
  connectionTemplate,
  kelConnections,
} from '@renderer/components/kel/kelApi';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const mainFrame = { url: 'file:///C:/kel/apps/renderer/index.html' };
const subframe = { url: 'file:///C:/kel/apps/renderer/artifact-preview.html' };
const legitEvent = () => ({ senderFrame: mainFrame, sender: { mainFrame } });

const handlerAt = (channel: string) => {
  const handler = handlers.get(channel);
  expect(handler, `handler for ${channel} is registered`).toBeTruthy();
  return handler as (event: unknown, ...args: unknown[]) => Promise<unknown>;
};

describe('connection credential custody (V2-01)', () => {
  const deps = {
    status: vi.fn(() => ({ available: true, providers: {} })),
    connectionStatus: vi.fn(() => ({ stripe: ['api_key'] })),
    set: vi.fn(() => ({ provider: 'connection:stripe', fields: ['api_key'] })),
    remove: vi.fn(() => ({ provider: 'connection:stripe', removed: 1 })),
    sync: vi.fn(async () => ({ ok: true })),
    fieldsFor: vi.fn(() => ['api_key']),
    read: vi.fn(() => 'the-stored-value'),
    test: vi.fn(async () => ({ id: 'stripe', last_test_state: 'ok' })),
  };

  beforeEach(() => {
    handlers.clear();
    for (const fn of Object.values(deps)) fn.mockClear();
    registerKelCredentialIpc(deps);
  });

  it('records a connection credential as the connection store, never as a model provider', async () => {
    await handlerAt('kel:credential-set')(legitEvent(), 'connection:stripe', 'api_key', 'sk_live_x');
    expect(deps.sync).toHaveBeenCalledTimes(2);
    const [route, body] = deps.sync.mock.calls[0] as unknown as [string, Record<string, unknown>];
    expect(route).toBe('/api/connections');
    expect(body).toEqual({
      action: 'set_credential',
      id: 'stripe',
      fields: ['api_key'],
      credential_ref: 'kel:connection:stripe',
    });
    // The metadata sync carries no value (the V2-01 rule, unchanged)…
    expect(JSON.stringify(body)).not.toContain('sk_live_x');
    // …while V2-04a's custody push does — in transit only, into the engine's memory, so the
    // assistant runtime's calls can use a value the runtime itself never receives.
    expect(deps.sync.mock.calls[1]).toEqual([
      '/api/connections',
      { action: 'supply', id: 'stripe', credentials: { api_key: 'the-stored-value' } },
    ]);
  });

  it('leaves a model provider credential on the provider store', async () => {
    deps.set.mockReturnValueOnce({ provider: 'deepseek', fields: ['api_key'] });
    await handlerAt('kel:credential-set')(legitEvent(), 'deepseek', 'api_key', 'sk-x');
    const [route, body] = deps.sync.mock.calls[0] as unknown as [string, Record<string, unknown>];
    expect(route).toBe('/api/providers');
    expect(body).toEqual({
      action: 'set_credential',
      provider: 'deepseek',
      fields: ['api_key'],
      credential_ref: 'kel:provider:deepseek:api_key',
    });
  });

  it('deletes from the store that owns the credential', async () => {
    await handlerAt('kel:credential-delete')(legitEvent(), 'connection:stripe');
    expect(deps.sync.mock.calls[0]).toEqual([
      '/api/connections',
      { action: 'delete_credential', id: 'stripe' },
    ]);
    // V2-04a: the engine's in-memory custody is cleared at the same moment.
    expect(deps.sync.mock.calls[1]).toEqual([
      '/api/connections',
      { action: 'supply', id: 'stripe', clear: true },
    ]);
    deps.sync.mockClear();
    await handlerAt('kel:credential-delete')(legitEvent(), 'deepseek');
    expect(deps.sync.mock.calls[0]).toEqual([
      '/api/providers',
      { action: 'delete_credential', provider: 'deepseek' },
    ]);
  });

  it('answers the shell-side view of a connection credential and refuses a subframe', async () => {
    expect(await handlerAt('kel:credential-connection-status')(legitEvent())).toEqual({
      stripe: ['api_key'],
    });
    expect(() =>
      handlerAt('kel:credential-connection-status')({ senderFrame: subframe, sender: { mainFrame } })
    ).toThrow();
  });

  it('a failed metadata sync never fails the custody action itself', async () => {
    deps.sync.mockRejectedValueOnce(new Error('engine is not answering'));
    await expect(
      handlerAt('kel:credential-set')(legitEvent(), 'connection:stripe', 'api_key', 'sk_live_x')
    ).resolves.toEqual({ provider: 'connection:stripe', fields: ['api_key'] });
    expect(deps.set).toHaveBeenCalledWith('connection:stripe', 'api_key', 'sk_live_x');
  });
});

describe('connection vocabulary and custody keys (V2-01 / V2-04)', () => {
  const TEMPLATES = [
    { id: 'api_key', label: 'API key', hint: 'a key Kel sends with its requests',
      credential_field: 'api_key', credential_label: 'API key', check: 'One authenticated GET.' },
    { id: 'oauth', label: 'Account authorization', hint: 'you sign in and Kel keeps the token',
      credential_field: 'access_token', credential_label: 'Access token', check: 'One authenticated GET.' },
    { id: 'bot', label: 'Bot or webhook', hint: 'a bot token or a webhook address',
      credential_field: 'token', credential_label: 'Bot token', check: 'One authenticated GET.' },
  ] as never;

  it('takes the words from the framework rather than keeping its own copy', () => {
    // V2-04: the renderer has no kind vocabulary. If it grew one back, the engine's words and the
    // engine's credential fields would drift apart silently.
    const api = read('desktop/packages/desktop/src/renderer/components/kel/kelApi.ts');
    expect(api).not.toContain('CONNECTION_KIND_LABELS');
    expect(api).not.toContain("'Account authorization'");
    expect(connectionTemplate({ templates: TEMPLATES }, 'oauth')?.credential_field).toBe('access_token');
    expect(connectionTemplate({ templates: TEMPLATES }, 'nope' as never)).toBeUndefined();
  });

  it('asks for the field name the framework gives the kind of service', () => {
    expect(connectionCredentialField({ templates: TEMPLATES }, 'api_key')).toBe('api_key');
    expect(connectionCredentialField({ templates: TEMPLATES }, 'oauth')).toBe('access_token');
    expect(connectionCredentialField({ templates: TEMPLATES }, 'bot')).toBe('token');
    // With no list (the engine did not answer), it falls back rather than inventing a field name.
    expect(connectionCredentialField(null, 'oauth')).toBe('api_key');
  });

  it('keeps a connection credential in its own custody namespace', () => {
    expect(connectionCustodyKey('stripe')).toBe('connection:stripe');
    // Distinct from any model provider id — a service named "internal" cannot collide.
    expect(connectionCustodyKey('internal')).not.toBe('internal');
  });
});

describe('the Connections surface is wired and reachable (V2-01)', () => {
  const kelApi = read('desktop/packages/desktop/src/renderer/components/kel/kelApi.ts');
  const page = read('desktop/packages/desktop/src/renderer/pages/kel/connections/index.tsx');
  const service = read('runtime/kel/service.py');
  const engine = read('runtime/kel/connections.py');
  const router = read('desktop/packages/desktop/src/renderer/components/layout/Router.tsx');
  const palette = read('desktop/packages/desktop/src/renderer/components/kel/KelCommandPalette.tsx');
  const kelService = read('desktop/packages/desktop/src/process/services/kel/KelService.ts');
  const custody = read('desktop/packages/desktop/src/process/services/kel/kelCredentials.ts');
  const preload = read('desktop/packages/desktop/src/preload/main.ts');

  it('has one engine store and one route for every service', () => {
    expect(engine).toContain('CREATE TABLE IF NOT EXISTS connections');
    expect(service).toContain("if path=='/api/connections':return self._connections_action(data)");
    expect(service).toContain('def _connections_dispatch(self,data):');
    expect(kelApi).toContain("call<KelConnectionList>('/api/connections', { action: 'list' })");
    expect(kelApi).toContain('export const kelConnections');
  });

  it('reaches the surface from the router and the command palette', () => {
    expect(router).toContain("import('@renderer/pages/kel/connections')");
    expect(router).toContain("path='/connections'");
    expect(palette).toContain("path: '/connections'");
  });

  it('names the custody entry for a connection the same way in both processes', () => {
    // The renderer and the main process each build this key. If either side changes the shape, the
    // credential the shell stored stops being the credential the engine is told about — so pin both.
    // The exact template on each side, and the namespace constant they must agree on.
    expect(custody).toContain("CONNECTION_NAMESPACE = 'connection'");
    expect(custody).toContain('`${CONNECTION_NAMESPACE}:${connectionId}`');
    expect(kelApi).toContain('`connection:${id}`');
  });

  it('lets the shell ask the engine about connections', () => {
    // One alternation added to the existing allowlist — nothing else about the route surface moved.
    expect(kelService).toMatch(/\|capabilities\|connections\|data-path\|/);
    expect(preload).toContain("ipcRenderer.invoke('kel:credential-connection-status')");
    // The providers view stays about model providers: connection fields are excluded there.
    expect(custody).toContain('provider === CONNECTION_NAMESPACE) continue');
  });

  it('never shows a saved credential value again', () => {
    // The value is typed once, into a password field, and never rendered back from state: the page
    // does not even read the pointer the engine keeps.
    expect(page).toContain('type="password"');
    expect(page).not.toContain('credential_ref');
    expect(page).not.toContain("/api/providers");
    expect(page).toContain('connectionCustodyKey(');
  });
});

describe('the account sign-in (V2-04b)', () => {
  const deps = {
    status: vi.fn(() => ({ available: true, providers: {} })),
    connectionStatus: vi.fn(() => ({ stripe: ['client_id', 'access_token', 'refresh_token'] })),
    set: vi.fn(() => ({
      provider: 'connection:stripe',
      fields: ['client_id', 'access_token', 'refresh_token'],
    })),
    remove: vi.fn(() => ({ provider: 'connection:stripe', removed: 1 })),
    sync: vi.fn(async () => ({ ok: true })),
    fieldsFor: vi.fn(() => ['client_id']),
    read: vi.fn(() => 'the-stored-value'),
    test: vi.fn(async () => ({ id: 'stripe' })),
    run: vi.fn(async () => ({ ok: true })),
    openExternal: vi.fn(),
    oauthPollMs: 1,
    oauthAttempts: 40,
  };

  beforeEach(() => {
    handlers.clear();
    for (const fn of Object.values(deps)) {
      if (typeof (fn as { mockClear?: unknown }).mockClear === 'function')
        (fn as { mockClear: () => void }).mockClear();
    }
    registerKelCredentialIpc(deps);
  });

  it('finishes a sign-in: opens the browser, claims once into custody, pushes to the engine', async () => {
    const calls: Array<{ route: string; body: Record<string, unknown> }> = [];
    let polls = 0;
    deps.sync.mockImplementation(async (route: string, body: Record<string, unknown>) => {
      calls.push({ route, body });
      if (body.action === 'oauth-initiate')
        return { authorize_url: 'https://provider.example/auth?state=xyz' };
      if (body.action === 'get') {
        polls += 1;
        return { auth_state: polls > 1 ? 'connected' : 'pending' };
      }
      if (body.action === 'oauth-claim')
        return { claimed: true, credentials: { access_token: 'at-1', refresh_token: 'rt-1' } };
      return { ok: true };
    });
    const outcome = (await handlerAt('kel:connection-oauth-connect')(
      legitEvent(),
      'stripe'
    )) as Record<string, unknown>;
    expect(outcome.state).toBe('connected');
    expect(deps.openExternal).toHaveBeenCalledWith('https://provider.example/auth?state=xyz');
    // The finished sign-in lands in the OS-backed custody, field by field…
    expect(deps.set).toHaveBeenCalledWith('connection:stripe', 'access_token', 'at-1');
    expect(deps.set).toHaveBeenCalledWith('connection:stripe', 'refresh_token', 'rt-1');
    // …the engine records only the pointer and the field names…
    const metadata = calls.find((call) => call.body.action === 'set_credential');
    expect(metadata?.body.credential_ref).toBe('kel:connection:stripe');
    // …and the engine's memory receives the values the way every other connection value arrives.
    expect(calls.some((call) => call.body.action === 'supply' && call.body.stored !== false)).toBe(true);
    // The outcome the renderer receives never carries a token.
    expect(JSON.stringify(outcome)).not.toContain('at-1');
  });

  it('stops honestly when the person does not finish the sign-in', async () => {
    deps.sync.mockImplementation(async (_route: string, body: Record<string, unknown>) => {
      if (body.action === 'oauth-initiate') return { authorize_url: 'https://provider.example/auth' };
      if (body.action === 'get') return { auth_state: 'disconnected' };
      return { ok: true };
    });
    const outcome = (await handlerAt('kel:connection-oauth-connect')(
      legitEvent(),
      'stripe'
    )) as Record<string, unknown>;
    expect(outcome.state).toBe('disconnected');
    expect(deps.set).not.toHaveBeenCalled();
  });

  it('gives up waiting when the sign-in never lands', async () => {
    deps.sync.mockImplementation(async (_route: string, body: Record<string, unknown>) => {
      if (body.action === 'oauth-initiate') return { authorize_url: 'https://provider.example/auth' };
      if (body.action === 'get') return { auth_state: 'pending' };
      return { ok: true };
    });
    const outcome = (await handlerAt('kel:connection-oauth-connect')(
      legitEvent(),
      'stripe'
    )) as Record<string, unknown>;
    expect(outcome.state).toBe('timeout');
  });

  it('signs out: the provider is told, custody and engine memory are cleared', async () => {
    const calls: Array<Record<string, unknown>> = [];
    deps.sync.mockImplementation(async (_route: string, body: Record<string, unknown>) => {
      calls.push(body);
      return { state: 'disconnected', note: 'stripe is signed out on this computer.' };
    });
    const outcome = (await handlerAt('kel:connection-oauth-revoke')(
      legitEvent(),
      'stripe'
    )) as Record<string, unknown>;
    expect(outcome.state).toBe('disconnected');
    expect(deps.remove).toHaveBeenCalledWith('connection:stripe');
    expect(calls.some((body) => body.action === 'oauth-revoke')).toBe(true);
    expect(calls.some((body) => body.action === 'supply' && body.clear === true)).toBe(true);
    expect(calls.some((body) => body.action === 'delete_credential')).toBe(true);
  });

  it('refuses a spoofed sender before anything else happens', async () => {
    await expect(
      handlerAt('kel:connection-oauth-connect')(
        { senderFrame: subframe, sender: { mainFrame } },
        'stripe'
      )
    ).rejects.toThrow();
    expect(deps.sync).not.toHaveBeenCalled();
    expect(deps.openExternal).not.toHaveBeenCalled();
  });
});
