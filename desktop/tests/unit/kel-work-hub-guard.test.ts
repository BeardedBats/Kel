import { afterEach, describe, expect, it, vi } from 'vitest';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';
import { kelHubSearch } from '@/renderer/components/kel/kelApi';

afterEach(() => vi.unstubAllGlobals());

describe('work hub renderer boundary', () => {
  it('allows bounded known scoped routes', () => {
    expect(rendererKelRequestRefusal('/api/work-hub/imports', { project_id: 'default', action: 'preview', content: 'Existing work' })).toBeNull();
    expect(rendererKelRequestRefusal('/api/work-hub/search?project_id=default&query=useful%20result')).toBeNull();
    expect(rendererKelRequestRefusal('/api/work-hub/procedures?project_id=default&recipe_id=saved-work&version=2')).toBeNull();
  });
  it('rejects arbitrary endpoints, query names and credential-bearing bodies', () => {
    expect(rendererKelRequestRefusal('/api/work-hub/execute')).toBeTruthy();
    expect(rendererKelRequestRefusal('/api/work-hub/imports?path=C%3A%2FUsers')).toBeTruthy();
    expect(rendererKelRequestRefusal('/api/work-hub/imports', { credentials: { token: 'secret' } })).toBeTruthy();
    expect(rendererKelRequestRefusal('/api/work-hub/search?query=' + 'a'.repeat(2100))).toBeTruthy();
  });
  it('passes ordinary search punctuation through the bounded route', async () => {
    const request = vi.fn(async (route: string) => {
      expect(rendererKelRequestRefusal(route)).toBeNull();
      expect(new URL(route, 'http://local').searchParams.get('query')).toBe("Nick's notes (draft)!");
      return { query: "Nick's notes (draft)!", conversations: [] };
    });
    vi.stubGlobal('window', { kelAPI: { request } });
    await kelHubSearch('default', "Nick's notes (draft)!");
    expect(request).toHaveBeenCalledOnce();
  });
});
