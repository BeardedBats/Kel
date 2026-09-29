/**
 * D-89 (Nick, 2026-09-29) — check wording across Kel: "Never ran" only when the checks genuinely never
 * ran, "Incomplete" when some ran but not all or the result is unconfirmed (and whenever the data cannot
 * tell), never "failed" for either.
 */
import { describe, expect, it } from 'vitest';
import { kelDetailRows, resultWords } from '@renderer/pages/conversation/Messages/components/KelMessageDetails';
import { VERDICT_TEXT, workWords } from '@renderer/components/kel/workLanguage';
import { lineWords } from '@renderer/components/kel/workCards/KelWorkLine';
import { checksNeverRan, uncertainLabel } from '@renderer/components/kel/workCards/workCardModel';

describe('D-89 check wording', () => {
  it('the work cards read the verification result', () => {
    expect(checksNeverRan({ verification: { result: 'not_run', summary: [] } })).toBe(true);
    expect(uncertainLabel({ verification: { result: 'not_run', summary: [] } })).toBe('Never ran');
    expect(uncertainLabel({ verification: { result: 'not_confirmed', summary: [] } })).toBe('Incomplete');
    expect(uncertainLabel({})).toBe('Incomplete');
  });

  it('a message’s details: Never ran only when every recorded check never ran', () => {
    expect(resultWords({ verdict: 'UNCERTAIN', checks: [{ kind: 'tests', verdict: 'NOT_RUN' }] } as never)).toBe('Never ran');
    expect(resultWords({ verdict: 'UNCERTAIN', checks: [{ kind: 'tests', verdict: 'VERIFIED' }, { kind: 'review', verdict: 'NOT_RUN' }] } as never)).toBe('Incomplete');
    expect(resultWords({ verdict: 'UNCERTAIN', checks: [] } as never)).toBe('Incomplete');
    expect(resultWords({ verdict: 'VERIFIED', checks: [] } as never)).toBe('Passed its checks');
    const rows = kelDetailRows({ kind: 'result', verdict: 'UNCERTAIN', checks: [{ kind: 'tests', verdict: 'UNCERTAIN' }] } as never);
    const text = JSON.stringify(rows);
    expect(text).toContain('Incomplete');
    expect(text).not.toMatch(/not fully|not confirmed|failed/i);
  });

  it('Activity and the in-thread line cannot tell from a verdict alone: "Incomplete", never failed', () => {
    expect(VERDICT_TEXT.UNCERTAIN).toBe('Incomplete');
    expect(workWords({ state: 'CLOSED', verdict: 'UNCERTAIN' }).label).toBe('Incomplete');
    expect(lineWords('failed', { accepted: 1, total: 3, verdict: 'UNCERTAIN' })).toBe('Incomplete');
  });
});
