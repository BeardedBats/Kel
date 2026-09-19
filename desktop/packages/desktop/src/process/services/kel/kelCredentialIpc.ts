/**
 * Kel credential-custody IPC registration (Campaign C AUD-MAJOR-002).
 *
 * The trio is privileged: each channel applies the shared sender guard, and the provider
 * sync into the engine stays best-effort exactly as before (a sync failure never fails the
 * custody action itself).
 */
import { ipcMain } from 'electron';
import { assertTrustedSender } from '../../../common/senderGuard';

export interface KelCredentialIpcDeps {
  status: () => unknown;
  set: (provider: string, field: string, value: string) => { provider: string; fields: string[] };
  remove: (provider: string) => { provider: string; removed: number };
  syncProviders: (body: Record<string, unknown>) => Promise<unknown>;
}

export const registerKelCredentialIpc = (deps: KelCredentialIpcDeps): void => {
  ipcMain.handle('kel:credential-status', (event) => {
    assertTrustedSender(event, { allowDevServer: true });
    return deps.status();
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
      await deps
        .syncProviders({
          action: 'set_credential',
          provider,
          fields: stored.fields,
          credential_ref: `kel:provider:${provider}:${field}`,
        })
        .catch((): undefined => undefined);
      return { provider: stored.provider, fields: stored.fields };
    }
  );

  ipcMain.handle(
    'kel:credential-delete',
    async (event, provider: string): Promise<{ provider: string; removed: number }> => {
      assertTrustedSender(event, { allowDevServer: true });
      const removed = deps.remove(provider);
      await deps.syncProviders({ action: 'delete_credential', provider }).catch((): undefined => undefined);
      return removed;
    }
  );
};
