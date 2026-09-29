/**
 * V2-01 — Connections through the real page (jsdom).
 *
 * The engine and the OS credential store are stubbed; the page is not. This is the central
 * management surface, so what it must prove is: what a person sees is what is true (state in words),
 * a credential goes to the shell's custody and never comes back into the page, and a removal removes
 * both halves.
 *
 * The custody stub emulates the shipped main-process contract exactly: it stores the value, and it
 * posts the metadata (field names and a pointer) to the engine — the same two things
 * `kelCredentialIpc` does, on the other side of the process boundary. `syncFails` drives the case
 * where that metadata write does not land.
 */
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Connections from '@renderer/pages/kel/connections';

type Row = {
  id: string;
  name: string;
  kind: 'api_key' | 'oauth' | 'bot';
  kind_label: string;
  base_url: string;
  auth_method: 'header' | 'bearer' | 'query' | 'basic';
  auth_header: string;
  docs_url: string;
  test_endpoint: string;
  notes: string;
  credential_ref: string | null;
  credential_fields: string[];
  has_credentials: boolean;
  state: 'ready' | 'needs_credentials';
  auth_prefix: string | null;
  can_test: boolean;
  last_test_at: number | null;
  last_test_state: string | null;
  last_test_status: number | null;
  last_test_ms: number | null;
  last_test_note: string;
  created: number;
  updated: number;
};

type Call = { route: string; body: Record<string, unknown> };

const row = (id: string, name: string, over: Partial<Row> = {}): Row => ({
  id,
  name,
  kind: 'api_key',
  kind_label: 'API key',
  base_url: '',
  auth_method: 'header',
  auth_header: '',
  auth_prefix: null,
  docs_url: '',
  test_endpoint: '',
  notes: '',
  credential_ref: null,
  credential_fields: [],
  has_credentials: false,
  state: 'needs_credentials',
  can_test: false,
  last_test_at: null,
  last_test_state: null,
  last_test_status: null,
  last_test_ms: null,
  last_test_note: '',
  created: 1760000000,
  updated: 1760000000,
  ...over,
});

let rows: Row[] = [];
let calls: Call[] = [];
/** What the OS store really received, so the value can be proven never to reach the engine. */
let stored: string[] = [];
let syncFails = false;

/** The framework's three templates, as the engine sends them (V2-04). */
const TEMPLATES = [
  {
    id: 'api_key',
    label: 'API key',
    hint: 'a key Kel sends with its requests',
    credential_field: 'api_key',
    credential_label: 'API key',
    check: 'One authenticated GET.',
  },
  {
    id: 'oauth',
    label: 'Account authorization',
    hint: 'you sign in and Kel keeps the token',
    credential_field: 'access_token',
    credential_label: 'Access token',
    check: 'One authenticated GET.',
  },
  {
    id: 'bot',
    label: 'Bot or webhook',
    hint: 'a bot token or a webhook address',
    credential_field: 'token',
    credential_label: 'Bot token',
    check: 'One authenticated GET.',
  },
];

/** One read action and one that changes something, as the engine sends them (V2-04). */
const ACTIONS = [
  {
    id: 'github-whoami',
    service: 'github',
    name: 'See which account the token belongs to',
    description: 'Asks GitHub who the stored token is.',
    method: 'GET',
    path: '/user',
    params: [],
    returns: 'Your login name.',
    mutating: false,
    source: 'documented',
  },
  {
    id: 'github-comment',
    service: 'github',
    name: 'Comment on an issue',
    description: 'Writes a comment.',
    method: 'POST',
    path: '/repos/o/r/issues/1/comments',
    params: [],
    returns: 'The comment.',
    mutating: true,
    source: 'documented',
  },
];

/** Two known services: one Kel is sure about, one whose address Nick has to paste in. */
const KNOWN = [
  {
    id: 'github',
    name: 'GitHub',
    kind: 'api_key',
    base_url: 'https://api.github.com',
    auth_method: 'header',
    auth_header: 'Authorization',
    auth_prefix: 'Bearer ',
    docs_url: 'https://docs.github.com/rest',
    test_endpoint: 'https://api.github.com/user',
    credential: 'a personal access token with the scopes you want Kel to have',
    fields: [{ name: 'api_key', label: 'Personal access token', secret: true }],
    where: 'GitHub → Settings → Developer settings → Personal access tokens',
    source: 'documented',
  },
  {
    id: 'google-drive',
    name: 'Google Drive',
    kind: 'oauth',
    base_url: 'https://www.googleapis.com/drive/v3',
    auth_method: 'header',
    auth_header: 'Authorization',
    auth_prefix: 'Bearer ',
    docs_url: 'https://developers.google.com/drive/api/reference/rest/v3',
    test_endpoint: 'https://www.googleapis.com/drive/v3/about?fields=user',
    credential: 'your own Google sign-in app',
    fields: [
      { name: 'client_id', label: 'OAuth client ID', secret: false },
      { name: 'client_secret', label: 'Client secret', secret: true },
    ],
    where: 'Google Cloud Console → APIs & Services → Credentials → OAuth client (Desktop app)',
    connect_label: 'Connect with Google',
    source: 'documented',
    note: 'Kel can see the names and types of your Drive files — never their contents — and changes nothing.',
  },
  {
    id: 'pitcher-list',
    name: 'Pitcher List',
    kind: 'api_key',
    base_url: 'https://pitcherlist.com/wp-json',
    auth_method: 'basic',
    auth_header: '',
    auth_prefix: '',
    docs_url: 'https://developer.wordpress.org/rest-api/',
    test_endpoint: 'https://pitcherlist.com/wp-json/wp/v2/users/me',
    credential: 'your Pitcher List username and a WordPress application password',
    fields: [
      { name: 'username', label: 'Username', secret: false },
      { name: 'password', label: 'Application password', secret: true },
    ],
    source: 'assumed',
  },
  {
    id: 'raptive',
    name: 'Raptive',
    kind: 'api_key',
    base_url: '',
    auth_method: 'header',
    auth_header: 'Authorization',
    auth_prefix: '',
    docs_url: '',
    test_endpoint: '',
    credential: 'the API credential from your Raptive account',
    fields: [{ name: 'api_key', label: 'API key', secret: true }],
    source: 'to-confirm',
    note: "Raptive's API address comes with your credential — paste it here and Kel will check it.",
  },
];

/** The engine, as the page's requests see it. */
const answer = (body: Record<string, unknown>): unknown => {
  switch (body.action) {
    case 'catalogue':
      return { services: KNOWN };
    case 'actions':
      return { connection: body.id, actions: ACTIONS };
    case 'list':
      return {
        connections: rows,
        counts: {
          ready: rows.filter((item) => item.has_credentials).length,
          needs_credentials: rows.filter((item) => !item.has_credentials).length,
        },
        states: ['ready', 'needs_credentials'],
        kinds: ['api_key', 'oauth', 'bot'],
        templates: TEMPLATES,
      };
    case 'get':
      return rows.find((item) => item.id === body.id);
    case 'save': {
      const name = String(body.name ?? '').trim();
      if (!name) throw new Error('Kel needs a name for the service.');
      const address = String(body.base_url ?? '').trim();
      if (address && !/^https?:\/\//.test(address)) {
        throw new Error('The API address must start with http:// or https://.');
      }
      const existing = rows.find((item) => item.id === body.id);
      if (existing) {
        Object.assign(existing, body, { name });
        return existing;
      }
      const saved = row(String(body.id ?? name.toLowerCase().replace(/\s+/g, '-')), name, {
        kind: (body.kind as Row['kind']) ?? 'api_key',
        base_url: String(body.base_url ?? ''),
      });
      rows = [...rows, saved];
      return saved;
    }
    case 'remove':
      rows = rows.filter((item) => item.id !== body.id);
      return { id: body.id, removed: true };
    case 'set_credential': {
      const item = rows.find((entry) => entry.id === body.id);
      if (!item) throw new Error('Unknown connection');
      item.has_credentials = true;
      item.state = 'ready';
      item.credential_ref = String(body.credential_ref ?? '');
      item.credential_fields = (body.fields as string[]) ?? [];
      return item;
    }
    case 'delete_credential': {
      const item = rows.find((entry) => entry.id === body.id);
      if (!item) throw new Error('Unknown connection');
      item.has_credentials = false;
      item.state = 'needs_credentials';
      item.credential_ref = null;
      item.credential_fields = [];
      return item;
    }
    default:
      throw new Error(`unexpected connection action ${String(body.action)}`);
  }
};

const syncMetadata = (action: 'set_credential' | 'delete_credential', provider: string): void => {
  const id = provider.replace(/^connection:/, '');
  const body: Record<string, unknown> =
    action === 'set_credential'
      ? { action, id, fields: ['api_key'], credential_ref: `kel:connection:${id}` }
      : { action, id };
  calls.push({ route: '/api/connections', body });
  answer(body);
};

const custody = {
  connectionStatus: vi.fn(async () => ({})),
  set: vi.fn(async (provider: string, field: string, value: string) => {
    stored.push(`${provider}:${field}=${value}`);
    if (!syncFails) syncMetadata('set_credential', provider);
    return { provider, fields: [field] };
  }),
  remove: vi.fn(async (provider: string) => {
    stored = stored.filter((entry) => !entry.startsWith(`${provider}:`));
    if (!syncFails) syncMetadata('delete_credential', provider);
    return { provider, removed: 1 };
  }),
  /**
   * V2-04: the shipped contract is "the shell uses the values it holds for one request and returns the
   * engine's answer". This stands in for the main process: the engine is asked, the credential goes with
   * it, and what comes back is the record — the page never sees a value.
   */
  runConnection: vi.fn(
    async (connectionId: string, actionId: string, params: unknown, confirmed: boolean) => {
      const action = ACTIONS.find((item) => item.id === actionId);
      if (!action) throw new Error('Kel does not know that action.');
      if (action.mutating && !confirmed) throw new Error(`${action.name} changes something, so Kel asks first.`);
      calls.push({
        route: '/api/connections',
        body: { action: 'run', id: connectionId, action_id: actionId, params, confirmed },
      });
      return {
        connection: connectionId,
        action: actionId,
        name: action.name,
        state: 'ok',
        status: 200,
        attempts: 1,
        ms: 12,
        note: 'The service answered 200.',
        result: { login: 'nick' },
        at: 1760000900,
      };
    }
  ),
  /**
   * V2-02: the shipped contract is "the shell uses the values it holds for one check and returns the
   * record". This stands in for the main process: it hands the engine what it holds, nothing more.
   */
  /** V2-04b: the browser sign-in runs in the main process; the page only hears the outcome. */
  oauthConnect: vi.fn(async (connectionId: string) => ({ id: connectionId, state: 'connected' })),
  oauthRevoke: vi.fn(async (connectionId: string) => ({ id: connectionId, state: 'signed_out' })),
  testConnection: vi.fn(async (connectionId: string) => {
    const prefix = `connection:${connectionId}:`;
    const credentials: Record<string, string> = {};
    for (const entry of stored.filter((line) => line.startsWith(prefix))) {
      const [field, value] = entry.slice(prefix.length).split('=');
      credentials[field] = value;
    }
    calls.push({
      route: '/api/connections',
      body: { action: 'test', id: connectionId, credentials },
    });
    const item = rows.find((entry) => entry.id === connectionId);
    if (!item) throw new Error('That connection was not found.');
    if (!item.can_test)
      throw new Error('Kel needs a test address or an API address before it can check this connection.');
    item.last_test_at = 1760000900;
    item.last_test_state = 'ok';
    item.last_test_status = 200;
    item.last_test_ms = 42;
    item.last_test_note = 'The service answered 200.';
    return item;
  }),
};

beforeEach(() => {
  rows = [];
  calls = [];
  stored = [];
  syncFails = false;
  custody.connectionStatus.mockClear();
  custody.connectionStatus.mockResolvedValue({});
  custody.set.mockClear();
  custody.remove.mockClear();
  custody.testConnection.mockClear();
  custody.runConnection.mockClear();
  custody.oauthConnect.mockClear();
  custody.oauthRevoke.mockClear();
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request: (route: string, body?: Record<string, unknown>) => {
      calls.push({ route, body: body ?? {} });
      if (route !== '/api/connections') {
        return Promise.reject(new Error(`the Connections surface must not call ${route}`));
      }
      try {
        return Promise.resolve(answer(body ?? {}));
      } catch (err) {
        return Promise.reject(err);
      }
    },
    credentials: custody,
  };
});

afterEach(() => {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <Connections />
    </MemoryRouter>
  );

describe('Connections — the central management surface', () => {
  it('lists what Kel can use, with the state said in words', async () => {
    rows = [
      row('stripe', 'Stripe', { has_credentials: true, state: 'ready', credential_fields: ['api_key'] }),
      row('pitcher-list', 'Pitcher List', { base_url: 'https://api.pitcherlist.com' }),
    ];
    renderPage();
    // The name can appear twice now — once as the service, once as where an action lives.
    expect((await screen.findAllByText('Stripe')).length).toBeGreaterThan(0);
    expect(screen.getByText('Pitcher List')).toBeTruthy();
    // ST-07: the row states the recorded check, so an untested credential says so.
    expect(screen.getByText('Ready — not tested')).toBeTruthy();
    expect(screen.getByText(/Needs a credential/)).toBeTruthy();
  });

  it('D-87: starts with one Connect button per known service and a quiet Other service', async () => {
    renderPage();
    const grid = (await screen.findByRole('button', { name: 'GitHub' })).closest('.kel-connect-grid');
    expect(grid).toBeTruthy();
    expect(Array.from(grid!.querySelectorAll('button')).map((button) => button.textContent)).toEqual([
      'GitHub',
      'Google Drive',
      'Pitcher List',
      'Raptive',
    ]);
    expect(screen.getByRole('button', { name: 'Other service' })).toBeTruthy();
    // The old expanding list and its explanations are gone.
    expect(screen.queryByText('Start with a known service')).toBeNull();
    expect(screen.queryByText('No connections yet.')).toBeNull();
  });

  it('D-87: a connected known service leaves the Connect buttons', async () => {
    rows = [row('github', 'GitHub', { has_credentials: true, state: 'ready' })];
    renderPage();
    expect(await screen.findByText('Connect another service')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'GitHub' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Raptive' })).toBeTruthy();
  });

  it('says so when this computer holds a credential the engine has no record of', async () => {
    rows = [row('stripe', 'Stripe')];
    custody.connectionStatus.mockResolvedValue({ stripe: ['api_key'] });
    renderPage();
    expect(await screen.findByText('Stripe')).toBeTruthy();
    expect(
      screen.getByText(/This computer still holds a credential for it that Kel has no record of/)
    ).toBeTruthy();
  });

  it('adds a service through the form', async () => {
    renderPage();
    fireEvent.click(await screen.findByText('Other service'));
    fireEvent.change(screen.getByLabelText('Service name'), { target: { value: 'Figma' } });
    fireEvent.change(screen.getByLabelText('API address'), {
      target: { value: 'https://api.figma.com' },
    });
    fireEvent.click(screen.getByText('Add connection'));
    await waitFor(() =>
      expect(calls.some((call) => call.body.action === 'save' && call.body.name === 'Figma')).toBe(true)
    );
    expect(await screen.findByText(/Figma is saved\./)).toBeTruthy();
    expect(await screen.findByText('Figma')).toBeTruthy();
  });

  it('repeats the engine sentence when it refuses a connection', async () => {
    renderPage();
    fireEvent.click(await screen.findByText('Other service'));
    fireEvent.change(screen.getByLabelText('Service name'), { target: { value: 'Figma' } });
    fireEvent.change(screen.getByLabelText('API address'), { target: { value: 'api.figma.com' } });
    fireEvent.click(screen.getByText('Add connection'));
    // The engine's own sentence, word for word — not a generic "something went wrong".
    expect(
      await screen.findByText(/The API address must start with http:\/\/ or https:\/\//)
    ).toBeTruthy();
  });

  it('will not even ask the engine to save an unnamed service', async () => {
    renderPage();
    fireEvent.click(await screen.findByText('Other service'));
    fireEvent.change(screen.getByLabelText('Service name'), { target: { value: '  ' } });
    expect((screen.getByText('Add connection') as HTMLButtonElement).disabled).toBe(true);
    expect(calls.some((call) => call.body.action === 'save')).toBe(false);
  });

  it('stores a credential in the OS store and never shows the value again', async () => {
    rows = [row('stripe', 'Stripe')];
    renderPage();
    fireEvent.click(await screen.findByText('Add credential'));
    const field = (await screen.findByLabelText('Header name')) as HTMLInputElement;
    expect(field.value).toBe('Authorization');
    expect(field.closest('.kel-connection-configured-row')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Credential'), { target: { value: 'sk_live_4242' } });
    fireEvent.click(screen.getByText('Save credential'));
    await waitFor(() => expect(custody.set).toHaveBeenCalledTimes(1));
    expect(calls.some((call) => call.body.action === 'save' && call.body.auth_header === 'Authorization')).toBe(true);
    // The value goes to the shell's custody under the connection namespace, and nowhere else.
    expect(stored).toEqual(['connection:stripe:api_key=sk_live_4242']);
    expect(calls.every((call) => call.route === '/api/connections')).toBe(true);
    expect(JSON.stringify(calls)).not.toContain('sk_live_4242');
    expect(await screen.findByText('Stripe is connected.')).toBeTruthy();
    // The proof that matters: it is not in the page any more, in state or in the DOM.
    expect(document.body.innerHTML).not.toContain('sk_live_4242');
    expect(document.querySelectorAll('input[type="password"]').length).toBe(0);
  });

  it('says so instead of claiming success when the engine did not record the credential', async () => {
    rows = [row('stripe', 'Stripe')];
    syncFails = true; // the metadata write does not land; the value is still in the OS store
    renderPage();
    fireEvent.click(await screen.findByText('Add credential'));
    fireEvent.change(await screen.findByLabelText('Credential'), { target: { value: 'sk_live_4242' } });
    fireEvent.click(screen.getByText('Save credential'));
    await waitFor(() => expect(custody.set).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/Kel did not record it back/)).toBeTruthy();
    expect(screen.queryByText('Stripe is connected.')).toBeNull();
  });

  it('keeps the fixed Authorization header read-only for bearer credentials', async () => {
    rows = [row('notion', 'Notion', { auth_method: 'bearer', auth_header: '' })];
    renderPage();
    fireEvent.click(await screen.findByText('Add credential'));
    const header = screen.getByLabelText('Header name') as HTMLInputElement;
    expect(header.value).toBe('Authorization');
    expect(header.readOnly).toBe(true);
    fireEvent.change(screen.getByLabelText('Credential'), { target: { value: 'synthetic-token' } });
    fireEvent.click(screen.getByText('Save credential'));
    await waitFor(() => expect(custody.set).toHaveBeenCalledTimes(1));
    expect(calls.some((call) => call.body.action === 'save')).toBe(false);
  });

  it('asks before disconnecting, then removes the value and the record', async () => {
    rows = [
      row('stripe', 'Stripe', { has_credentials: true, state: 'ready', credential_fields: ['api_key'] }),
    ];
    renderPage();
    fireEvent.click(await screen.findByText('Disconnect'));
    expect(custody.remove).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByText('Confirm disconnect'));
    await waitFor(() => expect(custody.remove).toHaveBeenCalledWith('connection:stripe'));
    await waitFor(() =>
      expect(calls.some((call) => call.body.action === 'remove' && call.body.id === 'stripe')).toBe(true)
    );
    expect(await screen.findByText('Stripe is disconnected.')).toBeTruthy();
    expect(await screen.findByText('Connect a service')).toBeTruthy();
  });

  it('checks a connection with the stored credential and reports what came back', async () => {
    rows = [
      row('stripe', 'Stripe', {
        has_credentials: true,
        state: 'ready',
        credential_fields: ['api_key'],
        can_test: true,
        test_endpoint: 'https://api.stripe.com/v1/account',
      }),
    ];
    stored = ['connection:stripe:api_key=sk_live_4242'];
    renderPage();
    fireEvent.click(await screen.findByText('Test'));
    await waitFor(() => expect(custody.testConnection).toHaveBeenCalledWith('stripe'));
    // The shell used the value it holds for this one check, and the engine got the value — but the
    // page only ever sees the record, and it says what happened in words.
    const check = calls.find((call) => call.body.action === 'test');
    expect(check?.body.credentials).toEqual({ api_key: 'sk_live_4242' });
    await waitFor(() => expect(screen.getByTestId('connection-row-status').textContent).toBe('Working'));
    expect(screen.getByTestId('connection-row-status').getAttribute('title')).toMatch(
      /Working — checked .*The service answered 200\./
    );
    expect(document.body.innerHTML).not.toContain('sk_live_4242');
  });

  it('ST-07: shows the recorded result on the row and keeps Test off until a credential exists', async () => {
    rows = [
      row('stripe', 'Stripe', { has_credentials: true, state: 'ready', credential_fields: ['api_key'], can_test: true, test_endpoint: 'https://api.stripe.com/v1/account' }),
      row('github', 'GitHub', { has_credentials: false, can_test: true, test_endpoint: 'https://api.github.com/user' }),
    ];
    stored = ['connection:stripe:api_key=sk_live_4242'];
    renderPage();
    const tests = await screen.findAllByText('Test');
    expect(tests.map((button) => (button.closest('button') as HTMLButtonElement).disabled)).toEqual([false, true]);
    fireEvent.click(tests[0]);
    await waitFor(() => expect(screen.getAllByTestId('connection-row-status')[0].textContent).toBe('Working'));
  });

  it('offers no check for a connection with no address to call', async () => {
    rows = [row('stripe', 'Stripe', { has_credentials: true, state: 'ready' })];
    renderPage();
    expect((await screen.findAllByText('Stripe')).length).toBeGreaterThan(0);
    expect(screen.queryByText('Test')).toBeNull();
  });

  it('asks for the credential field the framework names for that kind', async () => {
    rows = [row('figma', 'Figma', { kind: 'oauth', has_credentials: false })];
    renderPage();
    fireEvent.click(await screen.findByText('Other service'));
    // The kind a person picks comes from the engine's templates rather than from a copy kept in the
    // renderer — so the two cannot drift apart.
    const select = screen.getByLabelText('Credential type') as HTMLSelectElement;
    expect(Array.from(select.options).map((option) => option.textContent)).toEqual([
      'API key',
      'Account authorization',
      'Bot or webhook',
    ]);
  });

  it('D-87: Connect to GitHub fills in what Kel knows and asks only for the token', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'GitHub' }));
    expect(await screen.findByText('Connect to GitHub')).toBeTruthy();
    // Only the value Nick supplies, under GitHub's own name for it — no address, header or test fields.
    const token = screen.getByLabelText('Personal access token') as HTMLInputElement;
    expect(token.type).toBe('password');
    expect(screen.queryByLabelText('Service name')).toBeNull();
    expect(screen.queryByLabelText('API address')).toBeNull();
    expect(screen.queryByLabelText('Header name')).toBeNull();
    expect(screen.getByTestId('connect-where').textContent).toBe(
      'GitHub → Settings → Developer settings → Personal access tokens'
    );
    const connect = screen.getByRole('button', { name: 'Connect' }) as HTMLButtonElement;
    expect(connect.disabled).toBe(true);
    fireEvent.change(token, { target: { value: 'ghp_synthetic' } });
    fireEvent.click(connect);
    await waitFor(() => expect(custody.set).toHaveBeenCalledWith('connection:github', 'api_key', 'ghp_synthetic'));
    // The catalogue's row is what gets saved: address, header, presentation, test address, docs.
    expect(calls.find((call) => call.body.action === 'save')?.body).toMatchObject({
      name: 'GitHub',
      kind: 'api_key',
      base_url: 'https://api.github.com',
      auth_method: 'header',
      auth_header: 'Authorization',
      auth_prefix: 'Bearer ',
      test_endpoint: 'https://api.github.com/user',
      docs_url: 'https://docs.github.com/rest',
    });
    expect(await screen.findByText('GitHub is connected.')).toBeTruthy();
    // The value went to custody only — never to the engine, never back into the page.
    expect(JSON.stringify(calls)).not.toContain('ghp_synthetic');
    expect(document.body.innerHTML).not.toContain('ghp_synthetic');
    expect(document.querySelectorAll('input[type="password"]').length).toBe(0);
  });

  it('D-87: Google Drive asks for the OAuth client ID and secret, then connects with Google', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Google Drive' }));
    const clientId = (await screen.findByLabelText('OAuth client ID')) as HTMLInputElement;
    const secret = screen.getByLabelText('Client secret') as HTMLInputElement;
    expect(clientId.type).toBe('text');
    expect(secret.type).toBe('password');
    fireEvent.change(clientId, { target: { value: 'synthetic-id' } });
    fireEvent.change(secret, { target: { value: 'synthetic-secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Connect with Google' }));
    await waitFor(() => expect(custody.oauthConnect).toHaveBeenCalledWith('google-drive'));
    expect(custody.set).toHaveBeenCalledWith('connection:google-drive', 'client_id', 'synthetic-id');
    expect(custody.set).toHaveBeenCalledWith('connection:google-drive', 'client_secret', 'synthetic-secret');
    expect(await screen.findByText('Google Drive is connected.')).toBeTruthy();
    // The service's own explanation of what Kel can see is not repeated on the page.
    expect(screen.queryByText(/never their contents/)).toBeNull();
  });

  it('D-87: Pitcher List asks for a username and an application password', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Pitcher List' }));
    expect(((await screen.findByLabelText('Username')) as HTMLInputElement).type).toBe('text');
    expect((screen.getByLabelText('Application password') as HTMLInputElement).type).toBe('password');
    expect(screen.queryByTestId('connect-where')).toBeNull();
  });

  it('D-87: Raptive has no known address, so the address is a field', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Raptive' }));
    const address = (await screen.findByLabelText('API address')) as HTMLInputElement;
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'synthetic-key' } });
    const connect = screen.getByRole('button', { name: 'Connect' }) as HTMLButtonElement;
    expect(connect.disabled).toBe(true);
    fireEvent.change(address, { target: { value: 'https://api.raptive.example' } });
    fireEvent.click(connect);
    await waitFor(() =>
      expect(calls.find((call) => call.body.action === 'save')?.body).toMatchObject({
        name: 'Raptive',
        base_url: 'https://api.raptive.example',
      })
    );
  });

  it('D-87: a known service without its credential reopens its Connect form', async () => {
    rows = [row('github', 'GitHub')];
    renderPage();
    fireEvent.click(await screen.findByText('Add credential'));
    expect(await screen.findByText('Connect to GitHub')).toBeTruthy();
    expect(screen.getByLabelText('Personal access token')).toBeTruthy();
  });

  it('D-87: says nothing about how Kel uses a service', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: 'Raptive' }));
    await screen.findByText('Connect to Raptive');
    const text = document.body.textContent ?? '';
    for (const meta of [
      'what Kel needs to reach the service',
      'Kel calls this to check the credential',
      'The services Kel can use. You keep the credential.',
      'Kel knows this address',
      'Kel does not know this address',
      'Kel needs',
      "Raptive's API address comes with your credential",
    ]) {
      expect(text).not.toContain(meta);
    }
  });

  it('does one thing with a service when Nick asks', async () => {
    rows = [row('github', 'GitHub', { has_credentials: true, state: 'ready', can_test: true })];
    stored = ['connection:github:api_key=ghp_token'];
    renderPage();
    fireEvent.click((await screen.findAllByText('Run'))[0]);
    await waitFor(() =>
      expect(custody.runConnection).toHaveBeenCalledWith('github', 'github-whoami', {}, false)
    );
    // The answer is shown once, where it arrived, and the confirmation is plain.
    expect(await screen.findByText('See which account the token belongs to — done.')).toBeTruthy();
    expect(await screen.findByText(/The service answered 200\./)).toBeTruthy();
    expect(document.body.innerHTML).toContain('"login"');
    expect(document.body.innerHTML).not.toContain('ghp_token');
  });

  it('asks before doing something that changes anything', async () => {
    rows = [row('github', 'GitHub', { has_credentials: true, state: 'ready', can_test: true })];
    renderPage();
    fireEvent.click((await screen.findAllByText('Run'))[1]);
    // Nothing is sent yet: the question comes first.
    expect(custody.runConnection).not.toHaveBeenCalled();
    expect(screen.getByText(/This changes something in GitHub\./)).toBeTruthy();
    expect(screen.queryByText(/Kel asks before it changes anything/)).toBeNull();
    fireEvent.click(screen.getByText('Yes, run it'));
    await waitFor(() =>
      expect(custody.runConnection).toHaveBeenCalledWith('github', 'github-comment', {}, true)
    );
  });

  it('never talks to the model-provider route', async () => {
    rows = [row('stripe', 'Stripe')];
    renderPage();
    fireEvent.click(await screen.findByText('Add credential'));
    fireEvent.change(await screen.findByLabelText('Credential'), { target: { value: 'sk_live_4242' } });
    fireEvent.click(screen.getByText('Save credential'));
    await waitFor(() => expect(custody.set).toHaveBeenCalledTimes(1));
    expect(calls.some((call) => call.route === '/api/providers')).toBe(false);
  });
});
