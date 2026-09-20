/**
 * D15 — containment remains deliberate: the emergency stop is a two-step action in the UI, it
 * explains exactly what it does, and the engine still owns the semantics (the shell cannot
 * self-authorize and cannot issue leases).
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const read = (relative: string) => readFileSync(path.join(repoRoot, relative), 'utf8');

const autonomyPage = read('desktop/packages/desktop/src/renderer/pages/kel/autonomy/index.tsx');
const service = read('runtime/kel/service.py');

describe('emergency stop is deliberate (D15)', () => {
  it('arms on the first click and only stops on an explicit confirmation', () => {
    expect(autonomyPage).toContain('const [stopArmed, setStopArmed] = useState(false);');
    expect(autonomyPage).toContain('onClick={() => setStopArmed(true)}');
    expect(autonomyPage).toContain('Yes — stop everything');
    expect(autonomyPage).toContain('Keep going');
    expect(autonomyPage).toContain('choose Yes to confirm, or Keep going to leave everything as it is');
  });

  it('the engine call happens only inside the confirmed branch', () => {
    const armAt = autonomyPage.indexOf('{!stopArmed ? (');
    const engineCallAt = autonomyPage.indexOf('kelAutonomy.emergencyStop()');
    const disarmAt = autonomyPage.indexOf('setStopArmed(false)');
    expect(armAt).toBeGreaterThan(-1);
    expect(engineCallAt).toBeGreaterThan(armAt);
    // The call sits in the same handler that disarms the confirmation — the confirmed branch.
    expect(engineCallAt).toBeLessThan(disarmAt);
    expect((autonomyPage.match(/kelAutonomy\.emergencyStop\(\)/g) ?? [])).toHaveLength(1);
  });

  it('the service still owns the authority: the shell cannot issue leases or fake an actor', () => {
    expect(service).toContain("if data.get('action') not in ('leases','requests','guardrails','decisions','check','revoke','resolve','emergency_stop')");
    expect(service).toContain("payload['actor']='user'");
  });
});
