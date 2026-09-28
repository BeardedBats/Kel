/**
 * D-75.3: one key flow for Muse (Ramble's transcription).
 *
 * The Muse key lives in the same credential custody as every other key (Settings → Providers, OS-
 * backed, main process only). The engine receives it the way it receives the other providers' keys —
 * at spawn, through its environment (`MUSE_CUSTODY_KEY`, which the engine takes out of its
 * environment at once) — and, when it changes while Kel runs, through one in-memory `supply` call.
 *
 * Ramble used to keep its own paste box, which saved the key as plain text in the engine's settings.
 * That key keeps working without being entered again: at start-up it is moved into custody once and
 * its plaintext copy is dropped. The Transcriptions app's own key (Windows Credential Manager) is
 * only ever read by the engine and is left alone.
 */

export const MUSE_PROVIDER = 'muse';
export const MUSE_FIELD = 'api_key';
/** The spawn-time environment name the engine reads (and removes) for the custody key. */
export const MUSE_ENV = 'MUSE_CUSTODY_KEY';

type Request = (route: string, body?: unknown) => Promise<unknown>;

export interface MuseCustodyDeps {
  get: (provider: string, field: string) => string | null;
  set: (provider: string, field: string, value: string) => unknown;
}

/** The body that hands the engine the key (memory only) and drops Ramble's older plaintext copy. */
export const museSupply = (key: string): Record<string, unknown> => ({
  action: 'supply',
  key,
  drop_legacy: true,
});

export const museClear = (): Record<string, unknown> => ({ action: 'supply', clear: true });

/**
 * At start-up: move the key Ramble saved before into custody (once), and make sure the running
 * engine holds the custody key. Returns what happened, for the boot log (never the key).
 */
export async function syncMuseCustody(
  request: Request,
  deps: MuseCustodyDeps
): Promise<'custody' | 'moved' | 'none'> {
  let key = deps.get(MUSE_PROVIDER, MUSE_FIELD);
  let moved = false;
  if (!key) {
    const legacy = (await request('/api/transcription', { action: 'legacy_key' })) as { key?: unknown } | null;
    const value = typeof legacy?.key === 'string' ? legacy.key.trim() : '';
    if (!value) return 'none';
    deps.set(MUSE_PROVIDER, MUSE_FIELD, value);
    key = deps.get(MUSE_PROVIDER, MUSE_FIELD);
    if (key !== value) return 'none'; // custody could not hold it: leave the older copy in place
    moved = true;
  }
  await request('/api/transcription', museSupply(key));
  return moved ? 'moved' : 'custody';
}
