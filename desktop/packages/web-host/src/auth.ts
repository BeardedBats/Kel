/**
 * D3 — browser-facing authentication for the Kel WebUI.
 *
 * The web-host is the only path from a browser to the Kel engine: the engine itself stays bound to
 * 127.0.0.1 and requires a per-process bearer token that never leaves the main process. This module
 * owns the browser credential (scrypt hash + admin username, stored in `webui.config.json` under the
 * Kel data root) and the in-memory session / QR-token / login-throttle stores that the static
 * server consults before proxying anything.
 *
 * Security posture:
 *  - passwords are scrypt-hashed (salted, constant-time compare); plaintext is never persisted;
 *  - sessions are opaque 128-bit ids in an HttpOnly SameSite=Lax cookie with a sliding 7-day TTL;
 *  - login attempts are throttled per client key (8 failures / 5 minutes);
 *  - QR tokens are single-use, 5-minute, and only readable inside this process.
 */
import { randomBytes, randomUUID, scryptSync, timingSafeEqual } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export const AUTH_CONFIG_FILE = 'webui.config.json';
export const SESSION_COOKIE = 'kel_webui_session';

export type WebUiAuthFile = {
  port?: number;
  allowRemote?: boolean;
  adminUsername?: string;
  passwordHash?: string;
  passwordUpdatedAt?: string;
};

export function authConfigPath(userDataPath: string): string {
  return path.join(userDataPath, AUTH_CONFIG_FILE);
}

export function readAuthFile(userDataPath: string): WebUiAuthFile {
  try {
    const raw = fs.readFileSync(authConfigPath(userDataPath), 'utf-8');
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === 'object' ? (parsed as WebUiAuthFile) : {};
  } catch {
    return {};
  }
}

/** Read-modify-write the shared config file atomically (0600), preserving unknown fields. */
export function writeAuthFile(userDataPath: string, patch: Partial<WebUiAuthFile>): WebUiAuthFile {
  const next = { ...readAuthFile(userDataPath), ...patch };
  const target = authConfigPath(userDataPath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const tmp = `${target}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(next, null, 2) + '\n', { encoding: 'utf-8', mode: 0o600 });
  fs.renameSync(tmp, target);
  return next;
}

const SCRYPT_KEYLEN = 64;

export function hashPassword(password: string): string {
  const salt = randomBytes(16);
  const hash = scryptSync(password, salt, SCRYPT_KEYLEN);
  return `scrypt:${salt.toString('base64')}:${hash.toString('base64')}`;
}

export function verifyPasswordStored(stored: string | null | undefined, password: string): boolean {
  if (!stored) return false;
  const parts = stored.split(':');
  if (parts.length !== 3 || parts[0] !== 'scrypt') return false;
  try {
    const salt = Buffer.from(parts[1], 'base64');
    const expected = Buffer.from(parts[2], 'base64');
    const actual = scryptSync(password, salt, expected.length || SCRYPT_KEYLEN);
    return expected.length === actual.length && timingSafeEqual(expected, actual);
  } catch {
    return false;
  }
}

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

export function passwordPolicyCode(password: string): 'PASSWORD_TOO_SHORT' | 'PASSWORD_TOO_LONG' | null {
  if (password.length < PASSWORD_MIN_LENGTH) return 'PASSWORD_TOO_SHORT';
  if (password.length > PASSWORD_MAX_LENGTH) return 'PASSWORD_TOO_LONG';
  return null;
}

/** A random, paste-once password: 4 groups of 5 unambiguous characters. */
export function generateReadablePassword(): string {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
  return Array.from({ length: 4 }, () =>
    Array.from(randomBytes(5), (byte) => alphabet[byte % alphabet.length]).join('')
  ).join('-');
}

/**
 * First-use credential bootstrap. Returns the generated plaintext exactly once (for the desktop
 * Settings card); later calls return no password because one is already stored.
 */
export function ensureInitialPassword(userDataPath: string): { password?: string; username: string } {
  const config = readAuthFile(userDataPath);
  const username = config.adminUsername || 'admin';
  if (config.passwordHash) return { username };
  const password = generateReadablePassword();
  writeAuthFile(userDataPath, {
    passwordHash: hashPassword(password),
    passwordUpdatedAt: new Date().toISOString(),
    adminUsername: username,
  });
  return { password, username };
}

export function setWebUiPassword(userDataPath: string, newPassword: string): { ok: boolean; code?: string } {
  const code = passwordPolicyCode(newPassword);
  if (code) return { ok: false, code };
  writeAuthFile(userDataPath, {
    passwordHash: hashPassword(newPassword),
    passwordUpdatedAt: new Date().toISOString(),
  });
  return { ok: true };
}

export function setWebUiUsername(
  userDataPath: string,
  newUsername: string
): { ok: boolean; username?: string; code?: string } {
  const trimmed = newUsername.trim();
  if (trimmed.length < 3) return { ok: false, code: 'USERNAME_TOO_SHORT' };
  if (trimmed.length > 32) return { ok: false, code: 'USERNAME_TOO_LONG' };
  if (!/^[a-zA-Z0-9_-]+$/.test(trimmed) || /^[_-]|[_-]$/.test(trimmed)) {
    return { ok: false, code: 'USERNAME_FORMAT' };
  }
  writeAuthFile(userDataPath, { adminUsername: trimmed });
  return { ok: true, username: trimmed };
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export type WebUiSession = {
  id: string;
  username: string;
  createdAt: number;
  lastSeenAt: number;
  expiresAt: number;
};

export const SESSION_TTL_MS = 1000 * 60 * 60 * 24 * 7;

const LOGIN_WINDOW_MS = 5 * 60_000;
const LOGIN_MAX_FAILURES = 8;

export class WebUiAuth {
  private readonly sessions = new Map<string, WebUiSession>();
  private readonly failures = new Map<string, { count: number; firstAt: number }>();

  constructor(readonly userDataPath: string) {}

  get username(): string {
    return readAuthFile(this.userDataPath).adminUsername || 'admin';
  }

  hasPassword(): boolean {
    return Boolean(readAuthFile(this.userDataPath).passwordHash);
  }

  verifyLogin(username: string, password: string): boolean {
    const config = readAuthFile(this.userDataPath);
    if (!config.passwordHash) return false;
    const expectedUser = config.adminUsername || 'admin';
    const passwordOk = verifyPasswordStored(config.passwordHash, password);
    // Compare the username without an early exit so both checks always run.
    const usernameOk = username === expectedUser;
    return usernameOk && passwordOk;
  }

  isThrottled(key: string, now = Date.now()): boolean {
    const entry = this.failures.get(key);
    if (!entry) return false;
    if (now - entry.firstAt > LOGIN_WINDOW_MS) {
      this.failures.delete(key);
      return false;
    }
    return entry.count >= LOGIN_MAX_FAILURES;
  }

  recordFailure(key: string, now = Date.now()): void {
    const entry = this.failures.get(key);
    if (!entry || now - entry.firstAt > LOGIN_WINDOW_MS) {
      this.failures.set(key, { count: 1, firstAt: now });
      return;
    }
    entry.count += 1;
  }

  clearFailures(key: string): void {
    this.failures.delete(key);
  }

  createSession(): WebUiSession {
    const now = Date.now();
    const session: WebUiSession = {
      id: randomUUID().replaceAll('-', '') + randomBytes(16).toString('hex'),
      username: this.username,
      createdAt: now,
      lastSeenAt: now,
      expiresAt: now + SESSION_TTL_MS,
    };
    this.sessions.set(session.id, session);
    return session;
  }

  getSession(id: string | undefined): WebUiSession | null {
    if (!id) return null;
    const session = this.sessions.get(id);
    if (!session) return null;
    const now = Date.now();
    if (session.expiresAt <= now) {
      this.sessions.delete(id);
      return null;
    }
    session.lastSeenAt = now;
    session.expiresAt = now + SESSION_TTL_MS;
    return session;
  }

  destroySession(id: string | undefined): void {
    if (id) this.sessions.delete(id);
  }

  sessionCount(): number {
    return this.sessions.size;
  }
}

// ---------------------------------------------------------------------------
// QR login tokens — module-level so the desktop main process (which generates
// them for the Settings card) and the in-process static server share one store.
// ---------------------------------------------------------------------------

const qrTokens = new Map<string, { expiresAt: number }>();
export const QR_TOKEN_TTL_MS = 5 * 60_000;

export function generateWebUiQrToken(now = Date.now()): { token: string; expires_at_ms: number } {
  for (const [key, value] of qrTokens) {
    if (value.expiresAt <= now) qrTokens.delete(key);
  }
  const token = randomBytes(24).toString('base64url');
  const expires_at_ms = now + QR_TOKEN_TTL_MS;
  qrTokens.set(token, { expiresAt: expires_at_ms });
  return { token, expires_at_ms };
}

export function consumeWebUiQrToken(token: string, now = Date.now()): boolean {
  const entry = qrTokens.get(token);
  if (!entry) return false;
  qrTokens.delete(token);
  return entry.expiresAt > now;
}
