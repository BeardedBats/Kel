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
    source: 'documented',
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
    expect(screen.getByText(/Ready — Kel has a credential/)).toBeTruthy();
    expect(screen.getByText(/Needs a credential/)).toBeTruthy();
    expect(screen.getByText('1 ready · 1 needing a credential')).toBeTruthy();
  });

  it('starts empty and says what a connection buys you', async () => {
    renderPage();
    expect(await screen.findByText('No connections yet.')).toBeTruthy();
    expect(screen.getByText(/Kel can work with it directly/)).toBeTruthy();
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
    // The empty state offers the same action as the card header, so take the first of the two.
    fireEvent.click((await screen.findAllByText('Add a service'))[0]);
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
    fireEvent.click((await screen.findAllByText('Add a service'))[0]);
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
    fireEvent.click((await screen.findAllByText('Add a service'))[0]);
    fireEvent.change(screen.getByLabelText('Service name'), { target: { value: '  ' } });
    expect((screen.getByText('Add connection') as HTMLButtonElement).disabled).toBe(true);
    expect(calls.some((call) => call.body.action === 'save')).toBe(false);
  });

  it('stores a credential in the OS store and never shows the value again', async () => {
    rows = [row('stripe', 'Stripe')];
    renderPage();
    fireEvent.click(await screen.findByText('Add credential'));
    const field = (await screen.findByLabelText('Field name')) as HTMLInputElement;
    expect(field.value).toBe('api_key');
    fireEvent.change(screen.getByLabelText('Credential'), { target: { value: 'sk_live_4242' } });
    fireEvent.click(screen.getByText('Save credential'));
    await waitFor(() => expect(custody.set).toHaveBeenCalledTimes(1));
    // The value goes to the shell's custody under the connection namespace, and nowhere else.
    expect(stored).toEqual(['connection:stripe:api_key=sk_live_4242']);
    expect(calls.every((call) => call.route === '/api/connections')).toBe(true);
    expect(JSON.stringify(calls)).not.toContain('sk_live_4242');
    expect(
      await screen.findByText(/is ready — the credential is in this computer's secure store/)
    ).toBeTruthy();
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
    expect(screen.queryByText(/Kel has recorded it/)).toBeNull();
  });

  it('removes a stored credential and clears the engine record with it', async () => {
    rows = [
      row('stripe', 'Stripe', { has_credentials: true, state: 'ready', credential_fields: ['api_key'] }),
    ];
    renderPage();
    fireEvent.click(await screen.findByText('Remove credential'));
    await waitFor(() => expect(custody.remove).toHaveBeenCalledWith('connection:stripe'));
    expect(
      calls.filter((call) => call.body.action === 'delete_credential' && call.body.id === 'stripe')
    ).toHaveLength(1); // the shell routes the metadata once; the page does not double-post it
    expect(await screen.findByText(/The stored credential for Stripe is gone/)).toBeTruthy();
    expect(await screen.findByText(/Needs a credential/)).toBeTruthy();
  });

  it('asks before removing a connection, then removes the value and the record', async () => {
    rows = [
      row('stripe', 'Stripe', { has_credentials: true, state: 'ready', credential_fields: ['api_key'] }),
    ];
    renderPage();
    fireEvent.click(await screen.findByText('Remove'));
    expect(await screen.findByText('Confirm remove')).toBeTruthy();
    fireEvent.click(screen.getByText('Confirm remove'));
    await waitFor(() => expect(custody.remove).toHaveBeenCalledWith('connection:stripe'));
    await waitFor(() =>
      expect(calls.some((call) => call.body.action === 'remove' && call.body.id === 'stripe')).toBe(true)
    );
    expect(await screen.findByText(/Stripe is removed\./)).toBeTruthy();
    expect(await screen.findByText('No connections yet.')).toBeTruthy();
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
    fireEvent.click(await screen.findByText('Test connection'));
    await waitFor(() => expect(custody.testConnection).toHaveBeenCalledWith('stripe'));
    // The shell used the value it holds for this one check, and the engine got the value — but the
    // page only ever sees the record, and it says what happened in words.
    const check = calls.find((call) => call.body.action === 'test');
    expect(check?.body.credentials).toEqual({ api_key: 'sk_live_4242' });
    expect(await screen.findByText(/Working — checked/)).toBeTruthy();
    expect(await screen.findByText(/The service answered 200\./)).toBeTruthy();
    expect(document.body.innerHTML).not.toContain('sk_live_4242');
  });

  it('offers no check for a connection with no address to call', async () => {
    rows = [row('stripe', 'Stripe', { has_credentials: true, state: 'ready' })];
    renderPage();
    expect((await screen.findAllByText('Stripe')).length).toBeGreaterThan(0);
    expect(screen.queryByText('Test connection')).toBeNull();
  });

  it('asks for the credential field the framework names for that kind', async () => {
    rows = [row('figma', 'Figma', { kind: 'oauth', has_credentials: false })];
    renderPage();
    fireEvent.click(await screen.findByText('Add a service'));
    // The kind a person picks, and the words for it, come from the engine's templates rather than from a
    // copy kept in the renderer — so the two cannot drift apart.
    const select = screen.getByLabelText('How Kel signs in') as HTMLSelectElement;
    expect(Array.from(select.options).map((option) => option.textContent)).toEqual([
      'API key — a key Kel sends with its requests',
      'Account authorization — you sign in and Kel keeps the token',
      'Bot or webhook — a bot token or a webhook address',
    ]);
  });

  it('sets up a known service in one step', async () => {
    renderPage();
    fireEvent.click(await screen.findByText('Set up GitHub'));
    // The form arrives filled in: the address, the header, and how GitHub wants the token presented.
    expect((screen.getByLabelText('Service name') as HTMLInputElement).value).toBe('GitHub');
    expect((screen.getByLabelText('API address') as HTMLInputElement).value).toBe(
      'https://api.github.com'
    );
    expect((screen.getByLabelText('Header name') as HTMLInputElement).value).toBe('Authorization');
    expect(
      (screen.getByLabelText('How the credential is presented') as HTMLSelectElement).value
    ).toBe('custom');
    expect((screen.getByLabelText('The word before the credential') as HTMLInputElement).value).toBe(
      'Bearer '
    );
    fireEvent.click(screen.getByText('Add connection'));
    await waitFor(() => expect(calls.some((call) => call.body.action === 'save')).toBe(true));
    expect(calls.find((call) => call.body.action === 'save')?.body).toMatchObject({
      name: 'GitHub',
      base_url: 'https://api.github.com',
      auth_header: 'Authorization',
      auth_prefix: 'Bearer ',
    });
  });

  it('says what to fetch and how sure Kel is about the address', async () => {
    renderPage();
    expect(await screen.findByText(/Kel needs a personal access token/)).toBeTruthy();
    expect(
      await screen.findByText(/Kel knows this address from the service’s own documentation\./)
    ).toBeTruthy();
    // Raptive publishes no API address: Kel says so instead of inventing one.
    expect(await screen.findByText(/Kel does not know this address/)).toBeTruthy();
  });

  it('does one thing with a service when Nick asks', async () => {
    rows = [row('github', 'GitHub', { has_credentials: true, state: 'ready', can_test: true })];
    stored = ['connection:github:api_key=ghp_token'];
    renderPage();
    fireEvent.click(await screen.findByText('Do it'));
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
    fireEvent.click(await screen.findByText('Do it…'));
    // Nothing is sent yet: the question comes first.
    expect(custody.runConnection).not.toHaveBeenCalled();
    expect(screen.getByText(/This changes something in GitHub, so Kel asks first\./)).toBeTruthy();
    fireEvent.click(screen.getByText('Yes, do it'));
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
