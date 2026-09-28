/**
 * D19 — provider ids are engine internals; every surface speaks the provider's name.
 *
 * The installed battery found the Anthropic API entry (engine id `internal`) leaking that id into
 * user copy in three places: the Work route sentence, the provider save confirmation, and the
 * readiness "prefer" buttons. The id stays engine-side — credential references are keyed by it and
 * renaming it is a migration-class change (recorded in KNOWN_LIMITATIONS) — so the renderer names
 * providers through the inventory labels instead.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { routeSentence } from '@renderer/components/kel/workLanguage';
import type { KelJobRoute } from '@renderer/components/kel/kelApi';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const providersPage = read('desktop/packages/desktop/src/renderer/pages/kel/providers/index.tsx');
const activityPage = read('desktop/packages/desktop/src/renderer/pages/kel/activity/index.tsx');

const anthropicRoute: KelJobRoute = {
  provider: 'internal',
  route: {
    selected: 'internal',
    policy: 'eligible-cost-v1',
    unknown_cost: false,
    fallbacks: ['deepseek'],
    excluded: { codex: ['quota exhausted'] },
  },
  at: 0,
};

const LABELS = { internal: 'Anthropic API', deepseek: 'DeepSeek API', codex: 'Codex' };

describe('provider names on the work surfaces (D19)', () => {
  it('the route sentence uses the inventory name, never the engine id', () => {
    const sentence = routeSentence(anthropicRoute, LABELS);
    expect(sentence).toContain('Running on Anthropic API');
    expect(sentence).toContain('the cheapest eligible option');
    expect(sentence).toContain('If it fails, Kel will try DeepSeek API');
    expect(sentence).toContain('Skipped: Codex (its quota is used up)');
    expect(sentence).not.toContain('internal');
  });

  it('falls back to a readable name, not a raw id, when the inventory did not load', () => {
    const bare: KelJobRoute = { provider: 'claude-code', route: { selected: 'claude-code' } };
    const sentence = routeSentence(bare);
    expect(sentence).toBe('Running on claude code.');
    expect(sentence).not.toContain('claude-code');
  });

  it('Activity (which replaced the Work page, D-70) reads the provider inventory for those names', () => {
    expect(activityPage).toContain('kelProviders.list()');
    expect(activityPage).toContain('routeSentence(routes[job.id], providerLabels)');
    expect(activityPage).toContain('setProviderLabels(');
  });

  it('the provider confirmation and the readiness choices name the provider', () => {
    expect(providersPage).toContain('const nameOf = useCallback(');
    expect(providersPage).toContain('Saved and verified ${providerName}');
    expect(providersPage).not.toContain('Saved and verified ${provider}:');
    expect(providersPage).toContain("{name ? nameOf(name) : 'auto'}");
  });

  it('the readiness answer names its chain instead of listing engine ids', () => {
    expect(providersPage).toContain('readiness.chain.map((id) => nameOf(id))');
    expect(providersPage).not.toContain('readiness.chain.join(');
    // The unknown-id fallback humanizes rather than printing the id.
    expect(providersPage).toContain("?.label ?? id.replace(/-/g, ' ')");
  });
});

describe('Providers lists models by name, never by id (VIS-24)', () => {
  it('shows the plain model names and skips a built-in CLI model that only repeats the provider', async () => {
    const { modelNames } = await import('@renderer/pages/kel/providers');
    expect(modelNames({ label: 'Claude (built-in)', models: [{ id: 'claude-native', capabilities: [], label: 'Claude (built-in)' }] })).toBe('');
    expect(
      modelNames({
        label: 'DeepSeek API',
        models: [
          { id: 'deepseek-flash', capabilities: [], label: 'DeepSeek Flash' },
          { id: 'deepseek-v4-pro', capabilities: [], label: 'DeepSeek V4 Pro' },
        ],
      })
    ).toBe('DeepSeek Flash · DeepSeek V4 Pro');
    expect(modelNames({ label: 'Codex', models: [{ id: 'codex-native', capabilities: [], label: 'Codex (built-in)' }] })).toBe('');
    // An engine without names (older build) shows nothing rather than a raw id.
    expect(modelNames({ label: 'OpenRouter', models: [{ id: 'deepseek/deepseek-v4.1-flash', capabilities: [] }] })).toBe('');
  });
});
