/**
 * D17 — the integrations overview: one place to see connected / needs-setup / unavailable, in the
 * engine's own words, with a path to setup. Composed from the same `/api/capabilities` rows the
 * per-chat tools pill uses, so the two can never disagree.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const kelApi = read('desktop/packages/desktop/src/renderer/components/kel/kelApi.ts');
const providersPage = read('desktop/packages/desktop/src/renderer/pages/kel/providers/index.tsx');
const service = read('runtime/kel/service.py');

describe('integrations overview (D17)', () => {
  it('reads the engine inventory, not a copy', () => {
    expect(kelApi).toContain('export interface KelCapabilityRow');
    expect(kelApi).toContain("call<KelCapabilityRow[]>('/api/capabilities', { action: 'get', conversation })");
    expect(providersPage).toContain('kelCapabilities().catch(() => [])');
    expect(service).toContain("if action in ('get','list'):");
    expect(service).toContain('return snapshot(self.store,conversation)');
  });

  it('states connected / needs setup / unavailable in plain words with the reason', () => {
    expect(providersPage).toContain('<KelCard');
    expect(providersPage).toContain('title="Integrations"');
    expect(providersPage).toContain("'all available'");
    expect(providersPage).toContain("'some need setup'");
    expect(providersPage).toContain("? 'Connected'");
    expect(providersPage).toContain('`Needs setup — ');
    expect(providersPage).toContain('`Unavailable — ');
  });

  it('points at the setup surface and never fakes an action on unavailable rows', () => {
    expect(providersPage).toContain("onClick={() => navigate('/settings/tools')}");
    expect(providersPage).toContain("row.availability === 'needs_setup' && (");
  });
});
