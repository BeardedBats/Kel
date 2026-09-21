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
};
