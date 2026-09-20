/**
 * D19 — the interrupted-run promise.
 *
 * A run that stops mid-flight is fenced by the engine (the milestone stays UNCERTAIN so nothing
 * replays an unconfirmed external writer on its own), the Work page tells the person to reply
 * "continue", and the engine must actually re-arm the work when they do. Before this pin the
 * person's "continue" attached a conversation link and resumed nothing, while the Work page
 * promised the fenced state would "continue automatically" — a dead control and a state lie.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const workPage = read('desktop/packages/desktop/src/renderer/pages/kel/work/index.tsx');
const continuation = read('runtime/kel/continuation.py');
const core = read('runtime/kel/core.py');
const continuationTests = read('runtime/tests/test_v13_continuation.py');

describe('the interrupted-run promise (D19)', () => {
  it('the Work page never promises an automatic continuation for a fenced run', () => {
    expect(workPage).toContain("if (job.state === 'WAITING_RESOURCE' && !job.route_block) {");
    expect(workPage).toContain('A run stopped mid-flight. Your work is preserved');
    // The automatic sentence survives only for route-blocked jobs (which really do resume).
    expect(workPage).toContain(
      "WAITING_RESOURCE: 'Waiting for an available model — Kel will continue automatically.',"
    );
    expect(workPage).toContain('return WAIT_REASON[job.state] ?? null;');
  });

  it('the engine continuation re-arms an interrupted run instead of attaching and stopping', () => {
    expect(continuation).toContain("elif state in ('WAITING_RESOURCE', 'CLOSED'):");
    expect(continuation).toContain('self.store.reopen(job_id, reason=reason)');
    // ...and a route-blocked job keeps its own automatic path.
    expect(continuation).toContain('self.store.retry_route(job_id)');
  });

  it('reopen lifts the fence only for work a person can still retry', () => {
    expect(core).toContain("elif m['state'] == 'UNCERTAIN' and m['attempts'] < 4:");
    expect(core).toContain("m.update(state='NEEDS_REPAIR', artifact=None, checks=[],");
  });

  it('the journey itself is pinned in the engine suite', () => {
    expect(continuationTests).toContain(
      'def test_continue_after_a_lost_run_finishes_the_same_job'
    );
    expect(continuationTests).toContain(
      'def test_execute_resume_keeps_an_automatic_route_wait_separate'
    );
  });
});
