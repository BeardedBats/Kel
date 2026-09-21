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
    const credentials: Record<string, string> = {};
    for (const field of deps.fieldsFor(id)) {
      const value = deps.read(id, field);
      if (value) credentials[field] = value;
    }
    return deps.test({ action: 'test', id, credentials });
  });
};
