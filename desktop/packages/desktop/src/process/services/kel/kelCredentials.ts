/**
 * OS-backed credential custody for Kel (V1.4 Gate 6).
 *
 * Values are encrypted with Electron's `safeStorage` — DPAPI on Windows — and written to a
 * per-user file inside the Kel data root. Only the main process can decrypt; the engine receives
 * per-run environment values and stores metadata only; the renderer can store, list (field names)
 * and delete, but there is deliberately **no IPC that returns a value**.
 */
import { app, safeStorage } from 'electron';
import fs from 'fs';
import path from 'path';

const storePath = () =>
  path.join(process.env.KEL_DATA_DIR || app.getPath('appData'), 'kel-credentials.json');

type Store = Record<string, string>; // 'provider:field' -> base64 ciphertext

function read(): Store {
  try {
    return JSON.parse(fs.readFileSync(storePath(), 'utf8')) as Store;
  } catch {
    return {};
  }
}

function write(store: Store): void {
  fs.mkdirSync(path.dirname(storePath()), { recursive: true });
  fs.writeFileSync(storePath(), JSON.stringify(store, null, 2), { mode: 0o600 });
}

export function credentialsAvailable(): boolean {
  try {
    return safeStorage.isEncryptionAvailable();
  } catch {
    return false;
  }
}

/** Which providers have stored fields — names only, never values. */
export function credentialStatus(): { available: boolean; providers: Record<string, string[]> } {
  const providers: Record<string, string[]> = {};
  for (const key of Object.keys(read())) {
    const separator = key.indexOf(':');
    if (separator <= 0) continue;
    const provider = key.slice(0, separator);
    const field = key.slice(separator + 1);
    if (!provider || !field) continue;
    providers[provider] = [...(providers[provider] ?? []), field];
  }
  return { available: credentialsAvailable(), providers };
}

export function setCredential(
  provider: string,
  field: string,
  value: string
): { provider: string; fields: string[] } {
  if (!credentialsAvailable()) {
    throw new Error('OS-backed credential storage is unavailable on this system');
  }
  if (!provider || !field || !value) {
    throw new Error('Provider, field and value are required');
  }
  const store = read();
  store[`${provider}:${field}`] = safeStorage.encryptString(value).toString('base64');
  write(store);
  return { provider, fields: credentialStatus().providers[provider] ?? [field] };
}

export function removeCredential(provider: string): { provider: string; removed: number } {
  const store = read();
  let removed = 0;
  for (const key of Object.keys(store)) {
    if (key.startsWith(`${provider}:`)) {
      delete store[key];
      removed += 1;
    }
  }
  write(store);
  return { provider, removed };
}

/** Main-process only, reserved for the V1.5 injection path; no caller in V1.4.1 (docs/v1.4.1/06_V1_5_DEFERRED_WORK.md). */
export function getCredential(provider: string, field: string): string | null {
  const blob = read()[`${provider}:${field}`];
  if (!blob || !credentialsAvailable()) return null;
  try {
    return safeStorage.decryptString(Buffer.from(blob, 'base64'));
  } catch {
    return null;
  }
}
