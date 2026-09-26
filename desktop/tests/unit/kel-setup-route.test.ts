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

  it('lets desktop show existing Work while keeping chat and new-work entry routes gated', () => {
    expect(setupRouteAllowed('/work', true)).toBe(true);
    expect(setupRouteAllowed('/work', false)).toBe(false);
    for (const path of ['/guid', '/conversation/existing', '/projects/recipes', '/dogfood', '/work/other']) {
      expect(setupRouteAllowed(path, true), path).toBe(false);
    }
  });
});
