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
const activityPage = readFileSync(
  path.join(repoRoot, 'desktop/packages/desktop/src/renderer/pages/kel/activity/index.tsx'),
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
    expect(kelApi).toMatch(/action: 'save',\s*recipe,\s*confirm: true/);
  });
});

describe('Recipes tab (D10)', () => {
  it('can run a recipe and points at where the run lives', () => {
    expect(projectsPage).toContain('kelRecipeRun(draft.recipeId, values, scope)');
    expect(projectsPage).toContain('Run request sent — follow it in Activity.');
    expect(projectsPage).toContain('>Preview</button>');
  });
});

describe('Save as a recipe (D10)', () => {
  it('drafts first and saves only on explicit confirmation', () => {
    // D-70: the Work page is retired; finished work is saved as a recipe from Activity.
    expect(activityPage).toContain('Save as a recipe');
    expect(activityPage).toContain('const proposal = await kelRecipePropose(job.id, jobScope(job));');
    expect(activityPage).toContain('It is saved only when you confirm.');
    expect(activityPage.match(/kelRecipeSave\(current\.recipe, jobScope\(job\)\)/g) ?? []).toHaveLength(1);
  });
});
