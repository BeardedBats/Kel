/**
 * The engine-identity guard (audit A1 / ENG-01, extended by R8.B).
 *
 * The packaged desktop refuses to reuse a live engine that reports a different version than the app
 * it shipped with, so that an upgrade can never keep talking to the previous engine. The engine's
 * reported version is its own `__version__` (single-sourced in `runtime/kel/__init__.py`), and the
 * desktop's expectation is `app.getVersion()` — i.e. this package's `version`. The two are asserted
 * equal on the engine side (`runtime/tests/test_v16_r8_identity.py`).
 */
import { describe, expect, it } from 'vitest';
import { engineVersionAccepted } from './engineVersion';

describe('engineVersionAccepted', () => {
  it('accepts an identical version', () => {
    expect(engineVersionAccepted('1.6.0', '1.6.0')).toBe(true);
    expect(engineVersionAccepted(' 1.6.0 ', '1.6.0')).toBe(true);
  });

  it('refuses a different or stale version', () => {
    expect(engineVersionAccepted('1.5.0', '1.6.0')).toBe(false);
    expect(engineVersionAccepted(undefined, '1.6.0')).toBe(false);
    expect(engineVersionAccepted(160, '1.6.0')).toBe(false);
  });

  it('does not enforce an expectation it cannot know', () => {
    expect(engineVersionAccepted('anything', '')).toBe(true);
    expect(engineVersionAccepted('anything', undefined)).toBe(true);
  });
});
