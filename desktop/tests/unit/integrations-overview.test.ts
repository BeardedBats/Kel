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
    expect(providersPage).toContain('kelCapabilities().catch((): KelCapabilityRow[] => [])');
    expect(service).toContain("if action in ('get','list'):");
    expect(service).toContain('return snapshot(self.store,conversation)');
  });

  it('shows the provider label and reason from live state', () => {
    expect(providersPage).toContain('title="Integrations"');
    expect(providersPage).toContain('{view.label}');
    expect(providersPage).toContain('{view.reason}');
    expect(providersPage).not.toContain('Provider tools and credential settings');
  });

  it('keeps real credential setup and disables save without a key', () => {
    expect(providersPage).toContain('Save + Verify');
    expect(providersPage).toContain('disabled={busy || !keyDraft.value || !secure?.available}');
    expect(providersPage).toContain('void saveKey(provider.provider)');
  });
});
