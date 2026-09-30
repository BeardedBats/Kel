import { afterEach, expect, it, vi } from 'vitest';
import { kelWorkImports, type KelImportPreview } from '@renderer/components/kel/kelApi';
afterEach(() => { delete (window as unknown as { kelAPI?: unknown }).kelAPI; });
it('confirms only the selected Project and exact preview identity', async () => {
  const request = vi.fn().mockResolvedValue({});
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  const preview = { preview_id: 'id', digest: 'stamp', project_id: 'old-project', action: 'preview',
    content: 'private text that need not be sent twice', reference_files: [{ name: 'note.txt', text: 'facts' }] } as unknown as KelImportPreview;
  await kelWorkImports.confirm('current-project', preview);
  expect(request).toHaveBeenCalledWith('/api/work-hub/imports', { action: 'confirm', project_id: 'current-project',
    preview_id: 'id', digest: 'stamp', confirm: true });
});
