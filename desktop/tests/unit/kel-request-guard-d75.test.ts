import { describe, expect, it } from 'vitest';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';

describe('D-75 renderer routes', () => {
  it('lets the chat edit a message and answer the last reply again (D-75.2)', () => {
    for (const action of ['edit', 'regenerate', 'hide', 'hidden']) {
      expect(rendererKelRequestRefusal('/api/rewind', { action, conversation: 'c1' })).toBeNull();
    }
  });
});
