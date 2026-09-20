/**
 * D1 — provider status presentation + Providers page wiring.
 *
 * The engine states are the truth; the UI must never upgrade them (no "Available" for an
 * unauthenticated or paused provider) and must explain each state in plain language.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { presentProvider, toneChipClass, usableNow } from '@renderer/components/kel/providerStatus';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoDesktop = path.resolve(here, '..', '..');
const read = (relative: string) => readFileSync(path.join(repoDesktop, relative), 'utf8');

describe('presentProvider (D1)', () => {
  it('renders usable engine states as Available', () => {
    for (const status of ['healthy', 'quota', 'quota_not_reported']) {
      const view = presentProvider({ status });
      expect(view.label).toBe('Available');
      expect(view.tone).toBe('ok');
      expect(view.reason.length).toBeGreaterThan(0);
    }
  });

  it('never claims Available for a provider that is not ready', () => {
    for (const status of ['installed_not_authenticated', 'not_installed', 'degraded', 'unavailable']) {
      expect(presentProvider({ status }).label).not.toBe('Available');
    }
  });

  it('explains auth-related setup in plain language', () => {
    const api = presentProvider({ status: 'installed_not_authenticated', note: 'API key needed' });
    expect(api.label).toBe('Needs setup');
    expect(api.reason).toMatch(/API key/);
    const cli = presentProvider({ status: 'installed_not_authenticated', note: 'sign-in needed' });
    expect(cli.label).toBe('Needs setup');
    expect(cli.reason).toMatch(/signed in/i);
  });

  it('reports a CLI that is not installed as Unavailable', () => {
    const view = presentProvider({ status: 'not_installed', class: 'native-cli', note: 'not on PATH' });
    expect(view.label).toBe('Unavailable');
    expect(view.tone).toBe('failed');
  });

  it('calls a paused provider temporarily unavailable and keeps the retry time', () => {
    const until = Date.now() + 60_000;
    const view = presentProvider({ status: 'degraded', failures: 3, circuit_until: until });
    expect(view.label).toBe('Temporarily unavailable');
    expect(view.until).toBe(until);
    expect(view.reason).toMatch(/3 recent failures/);
  });

  it('never invents a human state for an unknown engine status', () => {
    const view = presentProvider({ status: 'some_new_state', note: 'info' });
    expect(view.tone).toBe('uncertain');
    expect(view.label).toBe('some new state');
    expect(view.reason).toBe('info');
  });

  it('maps tones to the existing chip classes', () => {
    expect(toneChipClass('ok')).toBe('kel-chip kel-chip--ok');
    expect(toneChipClass('wait')).toBe('kel-chip kel-chip--wait');
    expect(toneChipClass('uncertain')).toBe('kel-chip kel-chip--uncertain');
    expect(toneChipClass('failed')).toBe('kel-chip kel-chip--failed');
  });

  it('counts only genuinely usable providers as usable', () => {
    expect(usableNow({ status: 'quota_not_reported' })).toBe(true);
    expect(usableNow({ status: 'degraded' })).toBe(false);
    expect(usableNow({ status: 'installed_not_authenticated' })).toBe(false);
  });
});

describe('Providers page wiring (D1)', () => {
  const page = read('packages/desktop/src/renderer/pages/kel/providers/index.tsx');

  it('renders human statuses through presentProvider', () => {
    expect(page).toContain('presentProvider(');
    expect(page).not.toContain("status.replace(/_/g, ' ')");
  });

  it('offers the Save + Verify setup flow', () => {
    expect(page).toContain('Save + Verify');
    expect(page).toContain('saveKey(');
  });

  it('never prints a raw credential value: the input is a password field', () => {
    expect(page).toContain("type=\"password\"");
  });
});
