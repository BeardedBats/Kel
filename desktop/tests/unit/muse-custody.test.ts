/**
 * D-75.3: one key flow for Muse. The key Ramble saved before moves into custody once (then the engine
 * drops its plaintext copy); a key already in custody is handed to the running engine; nothing moves
 * when there is no key. Pages cannot save, clear, supply or read the key through the engine.
 */
import { describe, expect, it, vi } from 'vitest';
import { syncMuseCustody, MUSE_PROVIDER, MUSE_FIELD } from '@/process/services/kel/museCustody';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';

const custody = (initial: Record<string, string> = {}) => {
  const store = { ...initial };
  return {
    store,
    get: (provider: string, field: string) => store[`${provider}:${field}`] ?? null,
    set: (provider: string, field: string, value: string) => {
      store[`${provider}:${field}`] = value;
    },
  };
};

describe('syncMuseCustody', () => {
  it('moves the key Ramble saved into custody once and drops the plaintext copy', async () => {
    const deps = custody();
    const request = vi.fn(async (_route: string, body: { action: string }) =>
      body.action === 'legacy_key' ? { key: 'older-ramble-key' } : { has_key: true });
    expect(await syncMuseCustody(request, deps)).toBe('moved');
    expect(deps.store[`${MUSE_PROVIDER}:${MUSE_FIELD}`]).toBe('older-ramble-key');
    expect(request).toHaveBeenLastCalledWith('/api/transcription', { action: 'supply', key: 'older-ramble-key', drop_legacy: true });
  });

  it('hands the custody key to the engine without asking for the old one', async () => {
    const deps = custody({ 'muse:api_key': 'custody-key' });
    const request = vi.fn(async () => ({}));
    expect(await syncMuseCustody(request, deps)).toBe('custody');
    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith('/api/transcription', { action: 'supply', key: 'custody-key', drop_legacy: true });
  });

  it('does nothing when there is no key anywhere', async () => {
    const request = vi.fn(async () => ({ key: '' }));
    expect(await syncMuseCustody(request, custody())).toBe('none');
    expect(request).toHaveBeenCalledTimes(1);
  });

  it('keeps the older copy when custody cannot hold the key', async () => {
    const request = vi.fn(async () => ({ key: 'older' }));
    const deps = { get: () => null, set: vi.fn() };
    expect(await syncMuseCustody(request, deps)).toBe('none');
    expect(request).toHaveBeenCalledTimes(1);
  });
});

describe('renderer guard', () => {
  it('refuses the Muse key actions from a page, but not the transcription library', () => {
    for (const action of ['set_key', 'clear_key', 'supply', 'legacy_key']) {
      expect(rendererKelRequestRefusal('/api/transcription', { action, key: 'x' })).toBe('The Muse key is managed in Settings → Providers');
    }
    expect(rendererKelRequestRefusal('/api/transcription', { action: 'status' })).toBeNull();
    expect(rendererKelRequestRefusal('/api/transcription', { action: 'library' })).toBeNull();
  });
});
