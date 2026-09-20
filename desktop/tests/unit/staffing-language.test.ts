/**
 * D8 — staffing language pins: normal surfaces never expose workforce internals.
 */
import { describe, expect, it } from 'vitest';
import {
  assignmentLine,
  staffingSummary,
  type StaffingAssignment,
} from '@renderer/components/kel/staffingLanguage';

const assignment = (over: Partial<StaffingAssignment> = {}): StaffingAssignment => ({
  assignment_id: 'as-1',
  role: 'Independent Reviewer',
  derived_state: 'RUNNING',
  updated: 100,
  role_version: 3,
  snapshot_digest: 'abcdef0123456789',
  budget: 8,
  spent: 2,
  provider: 'codex',
  model: 'gpt-x',
  ...over,
});

describe('staffing summary (D8)', () => {
  it('says Kel is alone when nothing is staffed', () => {
    expect(staffingSummary([])).toBe('Kel is working alone on this step.');
  });

  it('says an independent review is in use, in the user language the directive asks for', () => {
    const line = staffingSummary([assignment()]);
    expect(line).toBe('Kel is using an independent review.');
  });

  it('counts multiple reviews and extra specialists separately', () => {
    const line = staffingSummary([
      assignment({ assignment_id: 'a1' }),
      assignment({ assignment_id: 'a2' }),
      assignment({ assignment_id: 'a3', role: 'Builder' }),
    ]);
    expect(line).toContain('2 independent reviews');
    expect(line).toContain('One more specialist is helping.');
  });
});

describe('assignment lines (D8)', () => {
  it('maps review, security and ordinary help to plain sentences', () => {
    expect(assignmentLine(assignment({ role: 'Independent Reviewer', derived_state: 'RUNNING' }))).toBe(
      'An independent review: in progress'
    );
    expect(assignmentLine(assignment({ role: 'Security Reviewer', derived_state: 'WAITING' }))).toBe(
      'An independent review: waiting'
    );
    expect(assignmentLine(assignment({ role: 'Sentinel', derived_state: 'DONE' }))).toBe(
      'An independent review: finished'
    );
    expect(assignmentLine(assignment({ role: 'Builder', derived_state: 'VERIFIED' }))).toBe('Extra help: finished');
    expect(assignmentLine(assignment({ role: 'Builder', derived_state: 'FAILED' }))).toBe(
      'Extra help: stopped and needs a look'
    );
  });

  it('never leaks internals into the sentence', () => {
    const lines = [
      assignmentLine(assignment()),
      staffingSummary([assignment()]),
      assignmentLine(assignment({ role: 'Security Reviewer', derived_state: 'BLOCKED' })),
    ].join(' ');
    for (const banned of ['D0', 'D1', 'D2', 'D3', 'D4', 'tier', 'budget', 'digest', 'v3', 'abcdef01', 'as-1']) {
      expect(lines).not.toContain(banned);
    }
  });
});
