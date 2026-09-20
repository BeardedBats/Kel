/**
 * D12 — route transparency pins: the engine exposes why a run landed on a provider, and the Work
 * page says it in plain language — including honest fallbacks and skipped-provider reasons.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const service = read('runtime/kel/service.py');
const kelApi = read('desktop/packages/desktop/src/renderer/components/kel/kelApi.ts');
const workPage = read('desktop/packages/desktop/src/renderer/pages/kel/work/index.tsx');
const workLanguage = read('desktop/packages/desktop/src/renderer/components/kel/workLanguage.ts');

describe('route contract (D12)', () => {
  it('the engine exposes the run.claimed decision per active job', () => {
    expect(service).toContain("if event.get('type')!='run.claimed' or event.get('aggregate_id') not in active:");
    expect(service).toContain("'routes':routes,");
  });

  it('the client types it', () => {
    expect(kelApi).toContain('export interface KelJobRoute');
    expect(kelApi).toContain('routes?: Record<string, KelJobRoute>;');
  });

  it('bodyless reads are GETs over the remote gateway too (the bridge semantics)', () => {
    expect(kelApi).toContain("method: hasBody ? 'POST' : 'GET'");
  });
});

describe('route sentence (D12)', () => {
  it('speaks plainly, offers the fallback, and names skipped providers with reasons', () => {
    expect(workLanguage).toContain('Running on ');
    expect(workLanguage).toContain('If it fails, Kel will try ');
    expect(workLanguage).toContain('Skipped: ');
    expect(workLanguage).toContain("'quota exhausted': 'its quota is used up'");
    expect(workLanguage).toContain("'health circuit open': 'it had recent failures'");
    expect(workLanguage).toContain("'authentication unavailable': 'its key is not set'");
    expect(workLanguage).toContain('its cost is not known yet');
  });

  it('renders only when the engine actually recorded a decision', () => {
    expect(workPage).toContain('{routeSentence(routes[activeJob.id]) && (');
    expect(workPage).toContain('setRoutes(state.routes ?? {});');
  });
});
