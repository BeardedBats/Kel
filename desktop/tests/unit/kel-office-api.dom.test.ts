import { afterEach, describe, expect, it, vi } from 'vitest';
import { kelOffice, kelOfficeDismiss, kelOfficeItem } from '@/renderer/components/kel/kelApi';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';

describe('D-66/D-68 live work client', () => {
  afterEach(() => {
    delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  });

  const bridge = () => {
    const request = vi.fn(async (route: string) => (route.startsWith('/api/office/item') ? { job_id: 'j-1' } : { items: [] }));
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    return request;
  };

  it('reads the cards and one item through routes the renderer allowlist admits', async () => {
    const request = bridge();
    await kelOffice();
    await kelOffice({ project: 'default' });
    await kelOffice({ conversation: 'abc-123' });
    await kelOfficeItem('0f8c2a1e-1111-2222-3333-444455556666');
    const routes = request.mock.calls.map((call) => call[0]);
    expect(routes).toEqual([
      '/api/office?project=*',
      '/api/office?project=default',
      '/api/office?conversation=abc-123',
      '/api/office/item?job=0f8c2a1e-1111-2222-3333-444455556666',
    ]);
    for (const route of routes) expect(rendererKelRequestRefusal(route)).toBeNull();
  });

  it('removes a finished card with the one write the view has', async () => {
    const request = bridge();
    await kelOfficeDismiss('j-1');
    expect(request).toHaveBeenCalledWith('/api/office', { action: 'dismiss', id: 'j-1' });
    expect(rendererKelRequestRefusal('/api/office', { action: 'dismiss', id: 'j-1' })).toBeNull();
  });
});
