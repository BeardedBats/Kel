/**
 * D19 residual — the donor org (`iOfficeAI`, the upstream AionUi publisher) must not appear in any
 * user-reachable renderer source. The only tolerated occurrence is a maintenance comment that names
 * the upstream issue being tracked; anything else fails this pin.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..', '..');
const rendererSrc = path.join(repoRoot, 'desktop/packages/desktop/src/renderer');

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else if (/\.(ts|tsx)$/.test(entry)) out.push(full);
  }
  return out;
}

describe('donor org references (D19 residual)', () => {
  it('keeps the donor org out of user-reachable renderer source', () => {
    const hits = walk(rendererSrc).filter((file) => readFileSync(file, 'utf8').includes('iOfficeAI'));
    const relative = hits.map((file) => path.relative(repoRoot, file).replace(/\\/g, '/'));
    expect(relative).toEqual(['desktop/packages/desktop/src/renderer/utils/ui/siderTooltip.ts']);
  });

  it('the two former links are gone entirely', () => {
    const office = readFileSync(
      path.join(rendererSrc, 'pages/conversation/Preview/components/viewers/OfficeWatchViewer.tsx'),
      'utf8'
    );
    const hub = readFileSync(path.join(rendererSrc, 'pages/settings/AgentSettings/AgentHubModal.tsx'), 'utf8');
    expect(office).not.toContain('OFFICECLI_INSTALL_URL');
    expect(office).not.toContain('iOfficeAI');
    expect(hub).not.toContain('AION_HUB_REPO_URL');
    expect(hub).not.toContain('iOfficeAI');
    expect(hub).not.toContain('Open a PR on AionHub');
  });
});
