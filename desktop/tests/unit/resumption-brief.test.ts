/**
 * D6 — resumption brief: derived-only, real actions, quiet when there is nothing to say.
 */
import { describe, expect, it } from 'vitest';
import {
  BRIEF_SECTION_CAP,
  buildResumptionBrief,
  RESTORE_FRESH_MS,
  type ResumptionPayload,
} from '@renderer/components/kel/resumptionBrief';
import type { KelBoundaryRequest, KelContinuationCandidate, KelWorkJob } from '@renderer/components/kel/kelApi';

const job = (over: Partial<KelWorkJob> & { id: string }): KelWorkJob => ({
  state: 'RUNNING',
  contract: { request: 'Tidy the notes', project_id: 'P-A' },
  conversation: 'conv-a',
  updated: 100,
  ...over,
});

const candidate = (over: Partial<KelContinuationCandidate> = {}): KelContinuationCandidate => ({
  job_id: 'j1',
  summary: 'Tidy the notes',
  reasons: ['paused before finishing'],
  state: 'PAUSED',
  ...over,
});

const boundary = (over: Partial<KelBoundaryRequest> = {}): KelBoundaryRequest => ({
  request_id: 'br-1',
  lease_id: 'lease-1',
  scope: 'web',
  target: 'example.com',
  what: 'Look something up on the web',
  status: 'PENDING',
  created: 50,
  ...over,
});

const brief = (payload: ResumptionPayload) => buildResumptionBrief({ now: 1_800_000_000_000, ...payload });

describe('buildResumptionBrief', () => {
  it('stays quiet when durable state has nothing to report', () => {
    const result = brief({});
    expect(result.quiet).toBe(true);
    expect(result.lines).toEqual([]);
    expect(result.summary).toBe('Nothing needs you right now.');
  });

  it('puts a failed restore first, with a real action', () => {
    const result = brief({
      restore: { ok: false, detail: 'The backup folder was incomplete.', at: 1_799_999_000_000 },
      jobs: [job({ id: 'j1', state: 'AWAITING_USER' })],
    });
    expect(result.quiet).toBe(false);
    expect(result.lines[0].kind).toBe('restore');
    expect(result.lines[0].title).toMatch(/restore did not finish/i);
    expect(result.lines[0].detail).toContain('incomplete');
    expect(result.lines[0].action?.to).toBe('/settings');
  });

  it('reports finished work with the conversation action, and never as needs-you', () => {
    const result = brief({
      jobs: [
        job({ id: 'done', state: 'CLOSED', verdict: 'VERIFIED' }),
        job({ id: 'bad', state: 'CLOSED', verdict: 'FAILED' }),
      ],
    });
    const finished = result.lines.filter((line) => line.kind === 'finished');
    expect(finished).toHaveLength(1);
    expect(finished[0].title).toBe('Finished: Tidy the notes');
    expect(finished[0].action?.to).toBe('/conversation/conv-a');
    // The failed job surfaces as needs-you, not as finished.
    expect(result.lines.some((line) => line.kind === 'needs-you' && line.title.match(/failure/i))).toBe(true);
    expect(result.summary).toContain('1 finished');
  });

  it('separates stopped work from needs-you work', () => {
    const result = brief({
      jobs: [
        job({ id: 'paused', state: 'PAUSED' }),
        job({ id: 'blocked', state: 'BLOCKED' }),
        job({ id: 'waiting', state: 'WAITING_RESOURCE', route_block: 'No model is available right now' }),
      ],
    });
    const stopped = result.lines.filter((line) => line.kind === 'stopped');
    // Only a deliberate pause is "stopped": a route-blocked job resumes by itself (go-ahead/Work).
    expect(stopped.map((line) => line.id)).toEqual(['brief-stopped-paused']);
    expect(stopped[0].detail).toMatch(/pick it back up/i);
    // BLOCKED stays needs-you only (no duplicate line).
    expect(result.lines.some((line) => line.kind === 'needs-you')).toBe(true);
  });

  it('surfaces an orphaned run as needs-you exactly once, with the engine reason', () => {
    const result = brief({
      jobs: [
        job({
          id: 'orphan',
          state: 'WAITING_RESOURCE',
          milestones: { m1: { state: 'UNCERTAIN', error: 'Expired run; native state requires reconciliation' } },
        }),
      ],
      // The engine also lists it as a continuation candidate; the brief must not repeat it.
      continuation: [candidate({ job_id: 'orphan', summary: 'A run stopped mid-flight' })],
    });
    const needsYou = result.lines.filter((line) => line.kind === 'needs-you');
    expect(needsYou).toHaveLength(1);
    expect(needsYou[0].title).toMatch(/fresh start/i);
    expect(needsYou[0].detail).toContain('requires reconciliation');
    expect(needsYou[0].detail).toContain('will not replay it on its own');
    expect(result.lines.filter((line) => line.kind === 'resumable')).toHaveLength(0);
    expect(result.lines.filter((line) => line.kind === 'stopped')).toHaveLength(0);
    expect(result.summary).toContain('1 needs you');
  });

  it('keeps a route-blocked job in the go-ahead section with the engine reason, never needs-you', () => {
    const result = brief({
      jobs: [job({ id: 'w1', state: 'WAITING_RESOURCE', route_block: 'No model is available right now' })],
      continuation: [candidate({ job_id: 'w1', reasons: ['No model is available right now'] })],
    });
    expect(result.lines.filter((line) => line.kind === 'needs-you')).toHaveLength(0);
    const resumable = result.lines.filter((line) => line.kind === 'resumable');
    expect(resumable).toHaveLength(1);
    expect(resumable[0].detail).toContain('No model is available right now');
  });

  it('carries the engine reason into a paused job line when one is recorded', () => {
    const result = brief({
      jobs: [
        job({
          id: 'p2',
          state: 'PAUSED',
          milestones: { m1: { state: 'NEEDS_REPAIR', error: 'Checks failed on the last attempt' } },
        }),
      ],
    });
    const stopped = result.lines.filter((line) => line.kind === 'stopped');
    expect(stopped).toHaveLength(1);
    expect(stopped[0].detail).toContain('Checks failed on the last attempt');
  });

  it('turns continuation candidates into go-ahead lines with the reasons', () => {
    const result = brief({ continuation: [candidate({ reasons: ['waiting on you', 'checks not run'] })] });
    const resumable = result.lines.filter((line) => line.kind === 'resumable');
    expect(resumable).toHaveLength(1);
    expect(resumable[0].title).toContain('Tidy the notes');
    expect(resumable[0].detail).toContain('waiting on you, checks not run');
    expect(resumable[0].detail).toContain('Kel never resumes on its own');
    expect(result.summary).toContain('1 waiting for your go-ahead');
  });

  it('caps each section and points at Work for the rest', () => {
    const many = Array.from({ length: BRIEF_SECTION_CAP + 2 }, (_, index) =>
      job({ id: `wait-${index}`, state: 'AWAITING_USER' })
    );
    const result = brief({ jobs: many });
    const needsYou = result.lines.filter((line) => line.kind === 'needs-you');
    expect(needsYou).toHaveLength(BRIEF_SECTION_CAP + 1); // capped items + the "more" line
    expect(needsYou.at(-1)?.title).toMatch(/2 more things need you/);
    expect(needsYou.at(-1)?.action?.to).toBe('/work');
  });

  it('adds the informational restore line only while it is fresh, in either time unit', () => {
    const now = 1_800_000_000_000;
    const freshMs = buildResumptionBrief({ now, restore: { ok: true, at: now - 60_000 } });
    expect(freshMs.lines.some((line) => line.id === 'restore-ok')).toBe(true);
    const freshSeconds = buildResumptionBrief({ now, restore: { ok: true, at: Math.floor((now - 60_000) / 1000) } });
    expect(freshSeconds.lines.some((line) => line.id === 'restore-ok')).toBe(true);
    const stale = buildResumptionBrief({ now, restore: { ok: true, at: now - RESTORE_FRESH_MS - 1 } });
    expect(stale.lines.some((line) => line.id === 'restore-ok')).toBe(false);
    expect(stale.quiet).toBe(true);
  });

  it('never carries machinery vocabulary', () => {
    const result = brief({
      jobs: [job({ id: 'j1', state: 'AWAITING_USER' }), job({ id: 'j2', state: 'CLOSED', verdict: 'UNVERIFIED' })],
      continuation: [candidate()],
      boundaryRequests: [boundary()],
      restore: { ok: false, detail: '', at: 0 },
    });
    const visible = JSON.stringify(result).toLowerCase();
    for (const banned of ['lease', 'assignment', 'worker', 'runtime', 'router', 'queue', 'agent_id']) {
      expect(visible).not.toContain(banned);
    }
  });
});
