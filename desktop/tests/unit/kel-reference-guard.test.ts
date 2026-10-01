import { expect, it } from 'vitest';
import { rendererKelRequestRefusal } from '../../packages/desktop/src/process/services/kel/kelRequestGuard';

it('allows selected reference extraction and scoped original retrieval through the bridge', () => {
  expect(rendererKelRequestRefusal('/api/work-hub/references?project_id=default')).toBeNull();
  expect(rendererKelRequestRefusal('/api/work-hub/references', { action: 'extract', project_id: 'default', name: 'reference.pdf', content: 'JVBERi0=' })).toBeNull();
  expect(rendererKelRequestRefusal('/api/work-hub/references', { action: 'original', project_id: 'default', id: 'receipt' })).toBeNull();
});

it('preserves path and credential refusal for reference requests', () => {
  expect(rendererKelRequestRefusal('/api/work-hub/references?path=C%3A%2FUsers')).toBeTruthy();
  expect(rendererKelRequestRefusal('/api/work-hub/references', { credentials: { token: 'secret' } })).toBeTruthy();
  expect(rendererKelRequestRefusal('/api/work-hub/references/execute')).toBeTruthy();
});
