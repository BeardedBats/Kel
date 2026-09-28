/**
 * D14 — the optional high-level Activity view: composed from existing state, nothing internal.
 * Pins: the route + nav entry exist, the page speaks in user language, and no internals (leases,
 * epochs, worker/run ids, routing packets, DB rows) leak into it. D-70: the Work page is retired;
 * Activity holds every job and shares its sentences through workLanguage.ts.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const activityPage = read('desktop/packages/desktop/src/renderer/pages/kel/activity/index.tsx');
const router = read('desktop/packages/desktop/src/renderer/components/layout/Router.tsx');
const nav = read(
  'desktop/packages/desktop/src/renderer/components/layout/Sider/SiderNav/KelNavEntries.tsx'
);
const workLanguage = read(
  'desktop/packages/desktop/src/renderer/components/kel/workLanguage.ts'
);

describe('Activity surface (D14)', () => {
  it('is routable and reachable from the sider as an optional place', () => {
    expect(router).toContain("const KelActivity = React.lazy(() => import('@renderer/pages/kel/activity'));");
    expect(router).toContain("<Route path='/activity' element={withRouteFallback(KelActivity)} />");
    expect(nav).toContain("{ id: 'activity', path: '/activity', label: 'Activity', Icon: AllApplication },");
  });

  it('shows only high-level state, in user language', () => {
    expect(activityPage).toContain('Happening now');
    expect(activityPage).toContain('Waiting on you');
    expect(activityPage).toContain('Recently finished');
    expect(activityPage).not.toContain('providers connected');
    expect(activityPage).toContain('workLabelFor(job.id, all)');
    // One job, one story: sections and words come from the shared table. D-70: the plain route
    // sentence moved here from the retired Work page, for work that is still going.
    expect(activityPage).toContain('workWords(job).section');
    expect(activityPage).toContain("workWords(job).section === 'now' ? routeSentence(routes[job.id], providerLabels) : null");
  });

  it('never leaks internals', () => {
    for (const banned of ['lease_id', 'epoch', 'run_id', 'digest', 'reservation', 'revision']) {
      expect(activityPage).not.toContain(banned);
    }
  });

  it('shares its sentences through workLanguage.ts', () => {
    expect(workLanguage).toContain('export const VERDICT_TEXT');
    expect(workLanguage).toContain('export const routeSentence');
    expect(workLanguage).toContain('export const jobStateText');
    expect(workLanguage).toContain('export function workWords');
    expect(activityPage).toContain("import { routeSentence, workWords } from '@renderer/components/kel/workLanguage';");
    expect(activityPage).not.toContain('const routeSentence =');
  });
});
