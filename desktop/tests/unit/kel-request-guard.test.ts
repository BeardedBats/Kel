import { describe, expect, it } from 'vitest';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';

describe('rendererKelRequestRefusal (D-33/D-34 credential custody)', () => {
  it('allows ordinary renderer routes and connection metadata actions', () => {
    expect(rendererKelRequestRefusal('/api/state?conversation=*')).toBeNull();
    expect(rendererKelRequestRefusal('/api/connections', { action: 'list' })).toBeNull();
    expect(rendererKelRequestRefusal('/api/connections', { action: 'set_credential', id: 'c1', fields: ['api_key'] })).toBeNull();
    expect(rendererKelRequestRefusal('/api/connections', { action: 'save', kind: 'api_key', name: 'Stripe' })).toBeNull();
  });

  it('refuses unknown routes', () => {
    expect(rendererKelRequestRefusal('/api/shutdown-idle')).toBe('Unknown Kel action');
    expect(rendererKelRequestRefusal(42)).toBe('Unknown Kel action');
  });

  it('refuses credential-bearing connection actions from the renderer', () => {
    for (const action of ['supply', 'oauth-initiate', 'oauth-claim', 'oauth-revoke', 'test', 'run', 'call']) {
      expect(rendererKelRequestRefusal('/api/connections', { action, id: 'c1' })).not.toBeNull();
    }
  });

  it('refuses any body that carries credential values', () => {
    expect(rendererKelRequestRefusal('/api/providers', { action: 'x', credentials: { key: 'v' } })).not.toBeNull();
    expect(rendererKelRequestRefusal('/api/model', { nested: { token: 'v' } })).not.toBeNull();
  });
});
