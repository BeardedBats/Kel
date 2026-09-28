/**
 * HVRA-MINOR-001 — the Permissions "Work" column must present human work references, never raw
 * engine job ids on the primary surface. The raw id stays available in support detail.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { workLabelFor } from '@renderer/components/kel/jobLabels';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoDesktop = path.resolve(here, '..', '..');
const read = (relative: string) => readFileSync(path.join(repoDesktop, relative), 'utf8');

describe('workLabelFor (HVRA-MINOR-001)', () => {
  it('uses the job request as the primary work label', () => {
    const jobs = [
      { id: 'abc-123', contract: { request: 'Write the weekly summary file to your Documents folder.' } },
    ];
    expect(workLabelFor('abc-123', jobs)).toBe('Write the weekly summary file to your Documents folder.');
  });

  it('labels work even when the job id looks like an internal engine slug', () => {
    const jobs = [
      { id: 'job_review_summary', contract: { request: 'Review the long response and summarize risks.' } },
    ];
    expect(workLabelFor('job_review_summary', jobs)).toBe('Review the long response and summarize risks.');
  });

  it('never renders a raw engine job id when the job cannot be resolved', () => {
    expect(workLabelFor('job_review_summary', [])).toBe('Work item');
    expect(workLabelFor('opaque-uuid-0001', [{ id: 'other', contract: { request: 'x' } }])).toBe('Work item');
    expect(workLabelFor('job_review_summary', null)).toBe('Work item');
  });

  it('names work the way its card does: the handoff title, else the request shortened like the engine (VIS-13)', () => {
    expect(workLabelFor('j1', [{ id: 'j1', contract: { request: 'Do the thing\nextra detail' } }])).toBe(
      'Do the thing extra detail'
    );
    expect(
      workLabelFor('j3', [{ id: 'j3', contract: { request: 'Build me a tiny app', handoff: { title: 'Tiny app' } } }])
    ).toBe('Tiny app');
    const label = workLabelFor('j2', [{ id: 'j2', contract: { request: 'word '.repeat(80) } }]);
    expect(label.length).toBeLessThanOrEqual(60);
    expect(label.endsWith('…')).toBe(true);
    expect(label).not.toMatch(/ …$/);
  });
});

describe('Permissions page wiring (HVRA-MINOR-001)', () => {
  it('renders the Work column through workLabelFor with the raw id in support detail', () => {
    const page = read('packages/desktop/src/renderer/pages/kel/autonomy/index.tsx');
    expect(page).toContain('workLabelFor(lease.job_id, jobs)');
    // JR-16: the raw reference is no longer a hover title on the primary column; it lives only in
    // the "Work references" support table behind Details.
    expect(page).not.toContain('title={`Work reference: ${lease.job_id}`}');
    expect(page).toContain('title="Work references"');
  });
});
