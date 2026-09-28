import { describe, expect, it } from 'vitest';
import { setupRouteAllowed } from '../../packages/desktop/src/renderer/components/layout/setupRoute';

describe('first-run setup routes', () => {
  it('keeps setup and its configuration links available', () => {
    for (const path of [
      '/onboarding', '/settings/appearance', '/settings/model', '/providers',
      '/connections', '/projects/knowledge', '/autonomy',
      // D-70: Permissions, Providers and Diagnostics live in Settings now.
      '/settings/permissions', '/settings/providers', '/settings/diagnostics', '/settings/staff',
    ]) {
      expect(setupRouteAllowed(path), path).toBe(true);
    }
  });

  it('still gates main Kel pages until setup is saved', () => {
    for (const path of ['/guid', '/work', '/activity', '/projects/recipes', '/dogfood']) {
      expect(setupRouteAllowed(path), path).toBe(false);
    }
  });

  it('keeps chat and new-work entry routes gated on desktop too (the Work page is retired, D-70)', () => {
    for (const path of ['/guid', '/conversation/existing', '/projects/recipes', '/dogfood', '/work', '/work/other']) {
      expect(setupRouteAllowed(path, true), path).toBe(false);
    }
  });
});
