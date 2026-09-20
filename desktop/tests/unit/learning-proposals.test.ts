/**
 * D9 — controlled learning promotion pins: changes Kel proposes never apply by themselves, and the
 * Knowledge surface gives a person the accept / not-now / reject decision with the reason visible.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const kelApi = readFileSync(
  path.join(repoRoot, 'desktop/packages/desktop/src/renderer/components/kel/kelApi.ts'),
  'utf8'
);
const projectsPage = readFileSync(
  path.join(repoRoot, 'desktop/packages/desktop/src/renderer/pages/kel/projects/index.tsx'),
  'utf8'
);
const service = readFileSync(path.join(repoRoot, 'runtime/kel/service.py'), 'utf8');

describe('proposal contract (D9)', () => {
  it('the engine always returns the open proposal queue in /api/work', () => {
    expect(service).toContain("'proposals':memory.proposals(project_id,state='open')");
  });

  it('the client type declares the queue and the three human decisions', () => {
    expect(kelApi).toContain('export interface KelMemoryProposal');
    expect(kelApi).toContain('proposals: KelMemoryProposal[];');
    expect(kelApi).toContain("'accept_proposal'");
    expect(kelApi).toContain("'reject_proposal'");
    expect(kelApi).toContain("'defer_proposal'");
  });
});

describe('Kel suggests surface (D9)', () => {
  it('is quiet when there is nothing waiting', () => {
    expect(projectsPage).toContain('{proposals.length > 0 && (');
    expect(projectsPage).toContain('work?.memory.proposals ?? []');
  });

  it('speaks user language and never applies anything by itself', () => {
    expect(projectsPage).toContain('Kel suggests');
    expect(projectsPage).toContain('nothing here applies by itself');
    expect(projectsPage).toContain('Why: {proposal.why}');
  });

  it('wires the three decisions to the engine actions', () => {
    expect(projectsPage).toContain("kelMemoryAction('accept_proposal', proposal.id)");
    expect(projectsPage).toContain("kelMemoryAction('defer_proposal', proposal.id)");
    expect(projectsPage).toContain("kelMemoryAction('reject_proposal', proposal.id");
  });
});
