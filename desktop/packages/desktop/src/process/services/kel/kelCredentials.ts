/**
 * OS-backed credential custody for Kel (V1.4 Gate 6).
 *
 * Values are encrypted with Electron's `safeStorage` — DPAPI on Windows — and written to a
 * per-user file inside the Kel data root. Only the main process can decrypt; the engine receives
 * per-run environment values and stores metadata only; the renderer can store, list (field names)
 * and delete, but there is deliberately **no IPC that returns a value**.
 *
 * Two kinds of credential share this one file, separated by namespace: model providers use their
 * plain provider id (`anthropic`), Connections (V2.0) use `connection:<id>`. A connection named
 * "internal" therefore cannot collide with the model provider `internal`, and the provider surfaces
 * never list a connection's fields.
 */
import { app, safeStorage } from 'electron';
import fs from 'fs';
import path from 'path';

const storePath = () =>
  path.join(process.env.KEL_DATA_DIR || app.getPath('appData'), 'kel-credentials.json');

type Store = Record<string, string>; // 'provider:field' -> base64 ciphertext

/** Connections keep their credentials in this namespace inside the same custody file. */
export const CONNECTION_NAMESPACE = 'connection';
export const connectionCredentialKey = (connectionId: string): string =>
  `${CONNECTION_NAMESPACE}:${connectionId}`;

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

/** The field names stored under one custody entry — names only, never values. */
function storedFields(provider: string): string[] {
  const prefix = `${provider}:`;
  return Object.keys(read())
    .filter((key) => key.startsWith(prefix) && key.length > prefix.length)
    .map((key) => key.slice(prefix.length));
}

/**
 * Which model providers have stored fields — names only, never values. Connection credentials are
 * a different kind of thing (the Connections surface lists those), so they are excluded here.
 */
export function credentialStatus(): { available: boolean; providers: Record<string, string[]> } {
  const providers: Record<string, string[]> = {};
  for (const key of Object.keys(read())) {
    const separator = key.indexOf(':');
    if (separator <= 0) continue;
    const provider = key.slice(0, separator);
    const field = key.slice(separator + 1);
    if (!provider || !field || provider === CONNECTION_NAMESPACE) continue;
    providers[provider] = [...(providers[provider] ?? []), field];
  }
  return { available: credentialsAvailable(), providers };
}

/** Connection id -> the field names the shell holds for it. Names only, never values. */
export function connectionCredentialStatus(): Record<string, string[]> {
  const connections: Record<string, string[]> = {};
  for (const entry of storedFields(CONNECTION_NAMESPACE)) {
    const separator = entry.indexOf(':');
    if (separator <= 0) continue;
    const id = entry.slice(0, separator);
    const field = entry.slice(separator + 1);
    if (!id || !field) continue;
    connections[id] = [...(connections[id] ?? []), field];
  }
  return connections;
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
  return { provider, fields: storedFields(provider) };
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

/** Main-process only; since V1.5 this reads the OS-backed value for spawn-time injection in
 * KelService. No other caller — values never return to the renderer or the engine database. */
export function getCredential(provider: string, field: string): string | null {
  const blob = read()[`${provider}:${field}`];
  if (!blob || !credentialsAvailable()) return null;
  try {
    return safeStorage.decryptString(Buffer.from(blob, 'base64'));
  } catch {
    return null;
  }
}
