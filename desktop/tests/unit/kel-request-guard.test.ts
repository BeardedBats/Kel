import { describe, expect, it } from 'vitest';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';

describe('rendererKelRequestRefusal (D-33/D-34 credential custody)', () => {
  it('allows ordinary renderer routes and connection metadata actions', () => {
    expect(rendererKelRequestRefusal('/api/state?conversation=*')).toBeNull();
    expect(rendererKelRequestRefusal('/api/connections', { action: 'list' })).toBeNull();
    expect(rendererKelRequestRefusal('/api/connections', { action: 'set_credential', id: 'c1', fields: ['api_key'] })).toBeNull();
    expect(rendererKelRequestRefusal('/api/connections', { action: 'save', kind: 'api_key', name: 'Stripe' })).toBeNull();
  });

  it('allows the D-54 project-scoped reads and the conversation routes', () => {
    for (const route of [
      '/api/state?conversation=*&project=*',
      '/api/state?conversation=*&project=default',
      '/api/state?conversation=abc-123&project=i-want-to-create-a-little-app-that-a',
      '/api/work?project=*',
      '/api/work?project=default',
      '/api/work?conversation=abc-123',
      '/api/project',
      '/api/conversation',
      '/api/conversation-title',
    ]) {
      expect(rendererKelRequestRefusal(route, {})).toBeNull();
    }
  });

  it('refuses malformed project scopes', () => {
    for (const route of [
      '/api/work?project=a/b',
      '/api/work?conversation=*',
      '/api/state?project=default',
      '/api/state?conversation=*&project=a&x=1',
      '/api/work?project=default&conversation=x',
    ]) {
      expect(rendererKelRequestRefusal(route)).toBe('Unknown Kel action');
    }
  });

  it('allows the D-66 live work reads and only the D-68 dismiss write', () => {
    for (const route of [
      '/api/office',
      '/api/office?project=*',
      '/api/office?project=default',
      '/api/office?conversation=abc-123',
      '/api/office/item?job=0f8c2a1e-1111-2222-3333-444455556666',
    ]) {
      expect(rendererKelRequestRefusal(route)).toBeNull();
    }
    expect(rendererKelRequestRefusal('/api/office', { action: 'dismiss', id: 'job-1' })).toBeNull();
    for (const body of [{ action: 'restore', id: 'job-1' }, { id: 'job-1' }, {}]) {
      expect(rendererKelRequestRefusal('/api/office', body)).not.toBeNull();
    }
    for (const route of [
      '/api/office?project=a/b',
      '/api/office?conversation=*',
      '/api/office?project=*&conversation=x',
      '/api/office/item',
      '/api/office/item?job=a&x=1',
      '/api/office/other',
    ]) {
      expect(rendererKelRequestRefusal(route)).toBe('Unknown Kel action');
    }
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

  it('allows the D-57 schedule actions and keeps the donor import in the main process', () => {
    for (const action of ['list', 'get', 'create', 'update', 'pause', 'resume', 'delete', 'run_now', 'history', 'preview', 'migration_status']) {
      expect(rendererKelRequestRefusal('/api/schedules', { action, id: 's1' })).toBeNull();
    }
    expect(rendererKelRequestRefusal('/api/schedules', { action: 'import', items: [{ origin: 'x' }] })).not.toBeNull();
    expect(rendererKelRequestRefusal('/api/schedules?action=import')).toBe('Unknown Kel action');
  });

  it('refuses any body that carries credential values', () => {
    expect(rendererKelRequestRefusal('/api/providers', { action: 'x', credentials: { key: 'v' } })).not.toBeNull();
    expect(rendererKelRequestRefusal('/api/model', { nested: { token: 'v' } })).not.toBeNull();
  });
});
