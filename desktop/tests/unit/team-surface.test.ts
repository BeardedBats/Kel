/**
 * D8 — the Team page is a developer surface: normal use shows plain staffing language, the
 * roster/studio views and the internals columns sit behind the developer toggle, and Kel manages
 * its own roster (the engine seeds shipped roles on first use; a person never has to).
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const teamPage = readFileSync(
  path.join(repoRoot, 'desktop/packages/desktop/src/renderer/pages/kel/team/index.tsx'),
  'utf8'
);
const teamEngine = readFileSync(path.join(repoRoot, 'runtime/kel/team.py'), 'utf8');

describe('Team page surface (D8)', () => {
  it('gates the roster/studio views and the internals columns behind the developer toggle', () => {
    expect(teamPage).toContain('team-developer-toggle');
    expect(teamPage).toContain('developerView ? view : ');
    expect(teamPage).toContain("effectiveView === 'roster'");
    expect(teamPage).toContain("effectiveView === 'studio'");
    expect(teamPage).toContain("effectiveView === 'office' && selected && developerView");
  });

  it('shows staffing in user language on the normal office view', () => {
    expect(teamPage).toContain('{staffingSummary(assignments)}');
    expect(teamPage).toContain('{assignmentLine(assignment)}');
  });

  it('never asks a person to seed a roster on a normal surface', () => {
    const seedLabels = teamPage.match(/Seed the default roster/g) ?? [];
    expect(seedLabels).toHaveLength(1); // developer-only roster view; the normal empty state is clean
    const officeMarker = teamPage.indexOf('Kel manages its own roster.');
    const seedIndex = teamPage.indexOf('Seed the default roster');
    expect(officeMarker).toBeGreaterThan(-1);
    expect(seedIndex).toBeGreaterThan(officeMarker);
  });
});

describe('roster self-seeding (D8)', () => {
  it('seeds shipped roles on first use and still fails closed for unknown ids', () => {
    expect(teamEngine).toContain(
      'Kel manages its own roster: a role that ships with the product is seeded on first'
    );
    expect(teamEngine).toContain('if template_id not in {seed[0] for seed in SEED_ROLES}:');
  });
});
