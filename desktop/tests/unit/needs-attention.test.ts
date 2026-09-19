/**
 * R9.D — hostile tests for the "Needs your attention" aggregator.
 *
 * These pin the directive's §9 requirements: derived-only mapping; actions only to existing
 * authoritative surfaces; project isolation fail-closed (Project A items can never appear under
 * Project B, and unbound items are excluded when a project filter is active); unknown/stale
 * items fail honestly with no action; and no worker/lease/routing vocabulary ever appears.
 */
import { describe, expect, it } from 'vitest';
import { collectAttention } from '@renderer/components/kel/needsAttention';
import type { KelBoundaryRequest, KelWorkJob } from '@renderer/components/kel/kelApi';

const job = (over: Partial<KelWorkJob> & { id: string }): KelWorkJob => ({
  state: 'RUNNING',
  contract: { request: 'Tidy the notes', project_id: 'P-A' },
  conversation: 'conv-a',
  updated: 100,
  ...over,
});

const boundary = (over: Partial<KelBoundaryRequest>): KelBoundaryRequest => ({
  request_id: 'br-1',
  lease_id: 'lease-1',
  scope: 'web',
  target: 'example.com',
  what: 'Look something up on the web',
  status: 'PENDING',
  created: 50,
  ...over,
});

describe('collectAttention — mapping', () => {
  it('maps waiting states to plain-language items with existing-surface actions only', () => {
    const items = collectAttention({
      jobs: [
        job({ id: 'j1', state: 'AWAITING_USER' }),
        job({ id: 'j2', state: 'BLOCKED' }),
        job({ id: 'j3', state: 'CLOSED', verdict: 'FAILED' }),
        job({ id: 'j4', state: 'CLOSED', verdict: 'UNVERIFIED' }),
        job({ id: 'j5', state: 'CLOSED', verdict: 'VERIFIED' }),
        job({ id: 'j6', state: 'RUNNING' }),
      ],
      continuation: [{ job_id: 'j1' }],
      boundaryRequests: [boundary({}), boundary({ request_id: 'br-2', status: 'GRANTED' })],
    });
    const kinds = items.map((item) => item.kind).sort();
    expect(kinds).toEqual(['approval', 'continuation', 'failure', 'input', 'permission', 'review']);
    for (const item of items) {
      if (item.action) {
        expect(['/conversation/conv-a', '/work', '/autonomy']).toContain(item.action.to);
      }
    }
  });

  it('renders no vocabulary from the machinery', () => {
    const items = collectAttention({
      jobs: [job({ id: 'j1', state: 'AWAITING_USER' }), job({ id: 'j2', state: 'BLOCKED' })],
      continuation: [{ job_id: 'j1' }],
      boundaryRequests: [boundary({})],
    });
    const visible = JSON.stringify(items).toLowerCase();
    for (const banned of ['lease', 'assignment', 'worker', 'runtime', 'router', 'queue', 'agent_id', 'provider']) {
      expect(visible).not.toContain(banned);
    }
  });
});

describe('collectAttention — hostile project isolation', () => {
  it('never lets a Project A item appear under a Project B filter (fail-closed)', () => {
    const items = collectAttention(
      {
        jobs: [job({ id: 'jA', state: 'AWAITING_USER' }), job({ id: 'jB', state: 'AWAITING_USER', contract: { request: 'B work', project_id: 'P-B' }, conversation: 'conv-b' })],
        boundaryRequests: [boundary({})], // unbound to any project
      },
      { projectId: 'P-B' }
    );
    expect(items.length).toBe(1);
    expect(items[0].id).toBe('approval-jB');
    for (const item of items) expect(item.projectId).toBe('P-B');
  });

  it('excludes items with no project binding when a project filter is active', () => {
    const items = collectAttention({ boundaryRequests: [boundary({})] }, { projectId: 'P-A' });
    expect(items).toEqual([]);
  });

  it('keeps the same payload unattributed when no filter is given (the global view)', () => {
    const items = collectAttention({ boundaryRequests: [boundary({})] });
    expect(items.length).toBe(1);
    expect(items[0].kind).toBe('permission');
  });
});

describe('collectAttention — unknown/stale items fail honestly', () => {
  it('a continuation pointing at missing work becomes a stale item with no action', () => {
    const items = collectAttention({ continuation: [{ job_id: 'missing' }] });
    expect(items.length).toBe(1);
    expect(items[0].kind).toBe('stale');
    expect(items[0].action).toBeUndefined();
    expect(items[0].title).toMatch(/no longer available/i);
  });

  it('a waiting job without a conversation still opens the Work list, never a guessed chat', () => {
    const items = collectAttention({ jobs: [job({ id: 'j1', state: 'AWAITING_USER', conversation: undefined })] });
    expect(items[0].action?.to).toBe('/work');
  });

  it('drops closed-and-verified work and non-pending boundary requests entirely', () => {
    const items = collectAttention({
      jobs: [job({ id: 'j1', state: 'CLOSED', verdict: 'VERIFIED' })],
      boundaryRequests: [boundary({ status: 'DENIED' })],
    });
    expect(items).toEqual([]);
  });
});
