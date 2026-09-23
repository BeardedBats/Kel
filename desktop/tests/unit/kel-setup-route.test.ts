import { describe, expect, it } from 'vitest';
import { setupRouteAllowed } from '../../packages/desktop/src/renderer/components/layout/setupRoute';

describe('first-run setup routes', () => {
  it('keeps setup and its configuration links available', () => {
    for (const path of [
      '/onboarding', '/settings/appearance', '/settings/model', '/providers',
      '/connections', '/projects/knowledge', '/autonomy',
    ]) {
      expect(setupRouteAllowed(path), path).toBe(true);
    }
  });

  it('still gates main Kel pages until setup is saved', () => {
    for (const path of ['/guid', '/work', '/activity', '/projects/recipes', '/dogfood']) {
      expect(setupRouteAllowed(path), path).toBe(false);
    }
  });
});
