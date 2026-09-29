/**
 * D16 — live capability revision pins: the Permissions page states the rule in user language, and
 * the engine keeps enforcing it at call time (fresh lease read, fail-closed).
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const autonomy = read('runtime/kel/autonomy.py');

describe('live capability revision (D16)', () => {
  // D-87 removed the Permissions page's explanation of this rule (no meta text); the engine pins below hold it.
  it('the engine enforces it at call time, fail-closed', () => {
    expect(autonomy).toContain('"""Fails closed. Returns');
    expect(autonomy).toContain("return {'allowed': False, 'rule': 'lease-' + lease['state'].lower(),");
    expect(autonomy).toContain("'reason': 'Lease is %s' % lease['state']");
  });

  it('only user input can widen a boundary', () => {
    expect(autonomy).toContain("if actor != 'user':");
    expect(autonomy).toContain('raise PolicyError(\'Only user input can resolve a boundary request\')');
  });
});
