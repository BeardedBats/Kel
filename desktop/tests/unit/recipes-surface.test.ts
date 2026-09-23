/**
 * D10 — recipe loop pins: the engine's own primitives (draft from a settled job, confirmation-gated
 * save, run through the existing execution) are on the shipped HTTP surface, and the desktop offers
 * exactly the honest steps — Run on the Recipes tab, draft-then-confirm on the Work page.
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
const workPage = readFileSync(
  path.join(repoRoot, 'desktop/packages/desktop/src/renderer/pages/kel/work/index.tsx'),
  'utf8'
);
const service = readFileSync(path.join(repoRoot, 'runtime/kel/service.py'), 'utf8');

describe('recipe contract (D10)', () => {
  it('exposes draft, run and confirmation-gated save over /api/recipes', () => {
    expect(service).toContain("if action=='propose_from_job':");
    expect(service).toContain('return library.propose_from_job(data.get(\'job_id\',\'\'))');
    expect(service).toContain("if action=='save':");
    expect(service).toContain("confirm=data.get('confirm') is True");
  });

  it('the client speaks the same three actions', () => {
    expect(kelApi).toContain("action: 'propose_from_job'");
    expect(kelApi).toContain("action: 'run'");
    expect(kelApi).toContain("action: 'save', recipe, confirm: true");
  });
});

describe('Recipes tab (D10)', () => {
  it('can run a recipe and points at where the run lives', () => {
    expect(projectsPage).toContain('kelRecipeRun(draft.recipeId, values)');
    expect(projectsPage).toContain('Run request sent — follow it on Work');
    expect(projectsPage).toContain('Preview (dry run)');
  });
});

describe('Save as a recipe (D10)', () => {
  it('drafts first and saves only on explicit confirmation', () => {
    expect(workPage).toContain('Save as a recipe');
    expect(workPage).toContain('setRecipeDraft(await kelRecipePropose(activeJob.id))');
    expect(workPage).toContain('It is saved only when you confirm.');
    expect(workPage.match(/kelRecipeSave\(recipeDraft\.recipe\)/g) ?? []).toHaveLength(1);
  });
});
