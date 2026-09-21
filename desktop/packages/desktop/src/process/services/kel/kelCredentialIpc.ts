/**
 * Kel credential-custody IPC registration (Campaign C AUD-MAJOR-002).
 *
 * The trio is privileged: each channel applies the shared sender guard, and the provider
 * sync into the engine stays best-effort exactly as before (a sync failure never fails the
 * custody action itself).
 *
 * Since V2-01 two kinds of credential share this custody: a model provider's key (`anthropic`) and a
 * Connection's (`connection:<id>`, V2.0). Each kind has its own engine store for metadata —
 * `/api/providers` and `/api/connections` — so the sync is routed by namespace here, and the pointer
 * the engine records says which kind it is (`kel:provider:…` / `kel:connection:…`). Values stay in
 * this process; only field names and the pointer travel.
 *
 * V2-04a adds one deliberate exception: after a connection credential changes (and at engine boot, in
 * KelService), the decrypted values are handed to the engine's in-memory custody (`supply` on
 * `/api/connections`) so the assistant runtime's calls can use them. They live in the engine's memory
 * only — never a column, never a file, never a log — and a renderer still never receives a value.
 */
import { ipcMain } from 'electron';
import { assertTrustedSender } from '../../../common/senderGuard';
import { CONNECTION_NAMESPACE } from './kelCredentials';

export interface KelCredentialIpcDeps {
  status: () => unknown;
  /** Connection id -> stored field names (the shell's own view; still no values). */
  connectionStatus: () => unknown;
  set: (provider: string, field: string, value: string) => { provider: string; fields: string[] };
  remove: (provider: string) => { provider: string; removed: number };
  /** Best-effort metadata sync into the engine store that owns this kind of credential. */
  sync: (
    route: '/api/providers' | '/api/connections',
    body: Record<string, unknown>
  ) => Promise<unknown>;
  /** Which field names the shell holds for a connection (names only). */
  fieldsFor: (connectionId: string) => string[];
  /** The decrypted value of one field. Main process only — it is never handed to a renderer. */
  read: (connectionId: string, field: string) => string | null;
  /** Ask the engine to check a connection, with these values for this one request. */
  test: (body: Record<string, unknown>) => Promise<unknown>;
  /** Ask the engine to do something with a connection, with these values for this one request. */
  run: (body: Record<string, unknown>) => Promise<unknown>;
  /** V2-04b: open a sign-in address in the system browser (the main process owns this). */
  openExternal?: (url: string) => void;
  /** Test seam: how often the sign-in wait checks the engine, in milliseconds. */
  oauthPollMs?: number;
  /** Test seam: how many checks the sign-in wait makes before giving up. */
  oauthAttempts?: number;
}

const isConnection = (provider: string): boolean => provider.startsWith(`${CONNECTION_NAMESPACE}:`);

const connectionId = (provider: string): string => provider.slice(CONNECTION_NAMESPACE.length + 1);

/** Where the engine records that a credential exists — a pointer, never the value. */
const metadataFor = (
  provider: string,
  fields: string[],
  field: string
): { route: '/api/providers' | '/api/connections'; body: Record<string, unknown> } =>
  isConnection(provider)
    ? {
        route: '/api/connections',
        body: {
          action: 'set_credential',
          id: connectionId(provider),
          fields,
          credential_ref: `kel:connection:${connectionId(provider)}`,
        },
      }
    : {
        route: '/api/providers',
        body: {
          action: 'set_credential',
          provider,
          fields,
          credential_ref: `kel:provider:${provider}:${field}`,
        },
      };

export const registerKelCredentialIpc = (deps: KelCredentialIpcDeps): void => {
  /** Only the fields the shell holds, only for this one request. Never a value back to a renderer. */
  const valuesFor = (id: string): Record<string, string> => {
    const values: Record<string, string> = {};
    for (const field of deps.fieldsFor(id)) {
      const value = deps.read(id, field);
      if (value) values[field] = value;
    }
    return values;
  };

  /** V2-04a: keep the engine's in-memory custody current for one connection (values in transit only). */
  const pushCustody = async (id: string): Promise<void> => {
    const values = valuesFor(id);
    if (Object.keys(values).length === 0) return;
    await deps
      .sync('/api/connections', { action: 'supply', id, credentials: values })
      .catch((): undefined => undefined);
  };

  const oauthCall = (body: Record<string, unknown>): Promise<Record<string, unknown>> =>
    deps.sync('/api/connections', body) as Promise<Record<string, unknown>>;
  const pause = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

  ipcMain.handle('kel:credential-status', (event) => {
    assertTrustedSender(event, { allowDevServer: true });
    return deps.status();
  });

  // The Connections surface asks the shell (not the engine) what it holds for a service, so a
  // credential can never be reported as missing while the OS store still has it.
  ipcMain.handle('kel:credential-connection-status', (event) => {
    assertTrustedSender(event, { allowDevServer: true });
    return deps.connectionStatus();
  });

  ipcMain.handle(
    'kel:credential-set',
    async (
      event,
      provider: string,
      field: string,
      value: string
    ): Promise<{ provider: string; fields: string[] }> => {
      assertTrustedSender(event, { allowDevServer: true });
      const stored = deps.set(provider, field, value);
      const target = metadataFor(provider, stored.fields, field);
      await deps.sync(target.route, target.body).catch((): undefined => undefined);
      if (isConnection(provider)) await pushCustody(connectionId(provider));
      return { provider: stored.provider, fields: stored.fields };
    }
  );

  ipcMain.handle(
    'kel:credential-delete',
    async (event, provider: string): Promise<{ provider: string; removed: number }> => {
      assertTrustedSender(event, { allowDevServer: true });
      const removed = deps.remove(provider);
      const body = isConnection(provider)
        ? { action: 'delete_credential', id: connectionId(provider) }
        : { action: 'delete_credential', provider };
      await deps
        .sync(isConnection(provider) ? '/api/connections' : '/api/providers', body)
        .catch((): undefined => undefined);
      if (isConnection(provider)) {
        await deps
          .sync('/api/connections', { action: 'supply', id: connectionId(provider), clear: true })
          .catch((): undefined => undefined);
      }
      return removed;
    }
  );

  /**
   * V2-02 Test Connection: the one place a stored value is *used* — decrypted in the main process,
   * handed to the engine for this single request, and never returned to the renderer. The renderer
   * asks for the check and gets the result; it cannot ask for the value.
   */
  ipcMain.handle('kel:connection-test', async (event, connectionId: string): Promise<unknown> => {
    assertTrustedSender(event, { allowDevServer: true });
    const id = String(connectionId ?? '');
    return deps.test({ action: 'test', id, credentials: valuesFor(id) });
  });

  /**
   * V2-04: do something with a connection. Same rule as the check — the value is decrypted here and
   * used for this one request; the renderer asks for the action and receives the service's answer.
   * `confirmed` is Nick's answer to the question the surface asked, and the engine refuses anything that
   * changes something in his account without it.
   */
  ipcMain.handle(
    'kel:connection-run',
    async (
      event,
      connectionId: string,
      actionId: string,
      params?: Record<string, unknown>,
      confirmed?: boolean
    ): Promise<unknown> => {
      assertTrustedSender(event, { allowDevServer: true });
      const id = String(connectionId ?? '');
      return deps.run({
        action: 'run',
        id,
        action_id: String(actionId ?? ''),
        params: params ?? {},
        confirmed: Boolean(confirmed),
        credentials: valuesFor(id),
      });
    }
  );

  /**
   * V2-04b: the account sign-in. The engine builds the authorization address (state + PKCE stay with
   * it), the system browser opens it, and this process waits — bounded — for the sign-in to finish.
   * A finished authorization is claimed ONCE into the OS-backed custody and pushed into engine memory
   * the way every other connection value is; the renderer sees only the outcome, never a token.
   */
  ipcMain.handle(
    'kel:connection-oauth-connect',
    async (event, connectionIdValue: string): Promise<Record<string, unknown>> => {
      assertTrustedSender(event, { allowDevServer: true });
      const id = String(connectionIdValue ?? '');
      const started = await oauthCall({ action: 'oauth-initiate', id });
      const authorizeUrl = String(started.authorize_url ?? '');
      if (!authorizeUrl) throw new Error('Kel could not build the sign-in address.');
      deps.openExternal?.(authorizeUrl);
      const attempts = Math.max(1, Number(deps.oauthAttempts ?? 150));
      const interval = Math.max(1, Number(deps.oauthPollMs ?? 2000));
      for (let waited = 0; waited < attempts; waited += 1) {
        await pause(interval);
        const row = await oauthCall({ action: 'get', id }).catch((): undefined => undefined);
        const state = String(row?.auth_state ?? '');
        if (state === 'connected') {
          const claimed = await oauthCall({ action: 'oauth-claim', id });
          const values = (claimed.credentials ?? {}) as Record<string, unknown>;
          let fields: string[] = deps.fieldsFor(id);
          for (const [field, value] of Object.entries(values)) {
            if (typeof value === 'string' && value) {
              fields = deps.set(`${CONNECTION_NAMESPACE}:${id}`, field, value).fields;
            }
          }
          await deps
            .sync('/api/connections', {
              action: 'set_credential',
              id,
              fields,
              credential_ref: `kel:connection:${id}`,
            })
            .catch((): undefined => undefined);
          await pushCustody(id);
          return { state: 'connected', fields };
        }
        // `oauth-initiate` leaves the connection `pending`, so a `disconnected` answer here is the
        // person not finishing on the provider page — say so instead of waiting out the clock.
        if (state === 'disconnected') {
          return { state: 'disconnected', note: 'The sign-in was not finished on the provider page.' };
        }
      }
      return {
        state: 'timeout',
        note: 'The sign-in did not finish; the browser tab may still be open.',
      };
    }
  );

  /** V2-04b: sign out — the provider, then this shell's custody, then the engine's memory. */
  ipcMain.handle(
    'kel:connection-oauth-revoke',
    async (event, connectionIdValue: string): Promise<unknown> => {
      assertTrustedSender(event, { allowDevServer: true });
      const id = String(connectionIdValue ?? '');
      const outcome = await oauthCall({ action: 'oauth-revoke', id });
      deps.remove(`${CONNECTION_NAMESPACE}:${id}`);
      await deps
        .sync('/api/connections', { action: 'supply', id, clear: true })
        .catch((): undefined => undefined);
      await deps
        .sync('/api/connections', { action: 'delete_credential', id })
        .catch((): undefined => undefined);
      return outcome;
    }
  );
};
