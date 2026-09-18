import { describe, expect, it } from 'vitest';
import { engineVersionAccepted } from '@process/services/kel/engineVersion';

/**
 * Audit A1 / ENG-01: detached-engine reuse must compare `engine_version`, not just whether
 * `/api/state` answers.
 */
describe('engineVersionAccepted', () => {
  it('accepts exactly the expected engine version', () => {
    expect(engineVersionAccepted('1.5.0', '1.5.0')).toBe(true);
    expect(engineVersionAccepted(' 1.5.0 ', '1.5.0')).toBe(true);
    expect(engineVersionAccepted('1.5.0', ' 1.5.0 ')).toBe(true);
  });

  it('refuses a stale, missing or non-string engine version', () => {
    expect(engineVersionAccepted('1.4.0', '1.5.0')).toBe(false);
    expect(engineVersionAccepted('1.5.0.1', '1.5.0')).toBe(false);
    expect(engineVersionAccepted(undefined, '1.5.0')).toBe(false);
    expect(engineVersionAccepted(null, '1.5.0')).toBe(false);
    expect(engineVersionAccepted('', '1.5.0')).toBe(false);
    expect(engineVersionAccepted(1.5, '1.5.0')).toBe(false);
    expect(engineVersionAccepted({ engine_version: '1.5.0' }, '1.5.0')).toBe(false);
  });

  it('does not enforce the check when this build cannot know the expected version', () => {
    // Unpackaged dev runs report Electron's version through `app.getVersion()`; the caller passes
    // an empty expectation instead of failing every start closed.
    expect(engineVersionAccepted('1.5.0', '')).toBe(true);
    expect(engineVersionAccepted('anything', undefined)).toBe(true);
    expect(engineVersionAccepted(undefined, '')).toBe(true);
  });
});
