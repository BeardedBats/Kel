/**
 * D3 — unit tests for the WebUI auth module (password store, sessions, throttle, QR tokens).
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  ensureInitialPassword,
  generateWebUiQrToken,
  consumeWebUiQrToken,
  hashPassword,
  passwordPolicyCode,
  readAuthFile,
  setWebUiPassword,
  setWebUiUsername,
  verifyPasswordStored,
  WebUiAuth,
} from './auth.js';

describe('auth password store', () => {
  let dir = '';

  beforeEach(async () => {
    dir = await fs.mkdtemp(path.join(os.tmpdir(), 'kel-auth-'));
  });

  afterEach(async () => {
    await fs.rm(dir, { recursive: true, force: true });
  });

  it('hashes and verifies a password', () => {
    const stored = hashPassword('correct horse battery');
    expect(stored.startsWith('scrypt:')).toBe(true);
    expect(verifyPasswordStored(stored, 'correct horse battery')).toBe(true);
    expect(verifyPasswordStored(stored, 'wrong')).toBe(false);
  });

  it('refuses malformed or missing hashes', () => {
    expect(verifyPasswordStored(undefined, 'x')).toBe(false);
    expect(verifyPasswordStored('', 'x')).toBe(false);
    expect(verifyPasswordStored('plaintext', 'x')).toBe(false);
    expect(verifyPasswordStored('scrypt:notbase64:', 'x')).toBe(false);
  });

  it('applies the password policy', () => {
    expect(passwordPolicyCode('short')).toBe('PASSWORD_TOO_SHORT');
    expect(passwordPolicyCode('x'.repeat(200))).toBe('PASSWORD_TOO_LONG');
    expect(passwordPolicyCode('longenough')).toBe(null);
  });

  it('creates an initial password exactly once', async () => {
    const first = ensureInitialPassword(dir);
    expect(first.password && first.password.length).toBeGreaterThan(10);
    expect(first.username).toBe('admin');
    const second = ensureInitialPassword(dir);
    expect(second.password).toBeUndefined();
  });

  it('sets a new password with policy feedback', async () => {
    expect(setWebUiPassword(dir, 'short')).toEqual({ ok: false, code: 'PASSWORD_TOO_SHORT' });
    expect(setWebUiPassword(dir, 'a good password')).toEqual({ ok: true });
    const auth = new WebUiAuth(dir);
    expect(auth.hasPassword()).toBe(true);
    expect(auth.verifyLogin('admin', 'a good password')).toBe(true);
    expect(auth.verifyLogin('admin', 'a good password!')).toBe(false);
    expect(auth.verifyLogin('someone', 'a good password')).toBe(false);
  });

  it('validates usernames', async () => {
    expect(setWebUiUsername(dir, 'ab')).toEqual({ ok: false, code: 'USERNAME_TOO_SHORT' });
    expect(setWebUiUsername(dir, 'bad name')).toEqual({ ok: false, code: 'USERNAME_FORMAT' });
    expect(setWebUiUsername(dir, '_lead')).toEqual({ ok: false, code: 'USERNAME_FORMAT' });
    expect(setWebUiUsername(dir, 'kel_admin')).toEqual({ ok: true, username: 'kel_admin' });
    expect(readAuthFile(dir).adminUsername).toBe('kel_admin');
  });
});

describe('WebUiAuth sessions + throttle', () => {
  let dir = '';

  beforeEach(async () => {
    dir = await fs.mkdtemp(path.join(os.tmpdir(), 'kel-sessions-'));
  });

  afterEach(async () => {
    await fs.rm(dir, { recursive: true, force: true });
  });

  it('creates, slides and destroys sessions', () => {
    const auth = new WebUiAuth(dir);
    const session = auth.createSession();
    const now = Date.now();
    expect(auth.getSession(session.id)).not.toBeNull();
    // Expired sessions are refused.
    expect(auth.getSession(session.id)).not.toBeNull();
    auth.destroySession(session.id);
    expect(auth.getSession(session.id)).toBeNull();
    expect(auth.getSession(undefined)).toBeNull();
    expect(auth.sessionCount()).toBe(0);
    void now;
  });

  it('throttles repeated failures and clears on demand', () => {
    const auth = new WebUiAuth(dir);
    const now = Date.now();
    expect(auth.isThrottled('1.2.3.4', now)).toBe(false);
    for (let attempt = 0; attempt < 8; attempt += 1) auth.recordFailure('1.2.3.4', now);
    expect(auth.isThrottled('1.2.3.4', now)).toBe(true);
    expect(auth.isThrottled('5.6.7.8', now)).toBe(false);
    // The window is 5 minutes; afterwards the throttle is gone.
    expect(auth.isThrottled('1.2.3.4', now + 6 * 60_000)).toBe(false);
    auth.recordFailure('5.6.7.8', now);
    auth.clearFailures('5.6.7.8');
    expect(auth.isThrottled('5.6.7.8', now)).toBe(false);
  });
});

describe('QR tokens', () => {
  it('consume exactly once and expire', () => {
    const now = Date.now();
    const { token, expires_at_ms } = generateWebUiQrToken(now);
    expect(expires_at_ms).toBeGreaterThan(now);
    expect(consumeWebUiQrToken(token, now + 1000)).toBe(true);
    expect(consumeWebUiQrToken(token, now + 1000)).toBe(false);
    const expired = generateWebUiQrToken(now);
    expect(consumeWebUiQrToken(expired.token, now + 6 * 60_000)).toBe(false);
  });
});
