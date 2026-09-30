/**
 * The command palette's surface (D2 in docs/v2/evidence/v2-19/UI_ACCEPTANCE_R21.md). The theme colour
 * rows that shared this file left Settings → Appearance with D-82 (Kel is dark only).
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('command palette surface (D2)', () => {
  it('uses the current desktop overlay glass instead of page-card glass', () => {
    const renderer = resolve(__dirname, '../../packages/desktop/src/renderer');
    const palette = readFileSync(resolve(renderer, 'components/kel/KelCommandPalette.tsx'), 'utf8');
    const css = readFileSync(resolve(renderer, 'styles/kel-shell.css'), 'utf8');
    expect(palette).toContain("className='kel-palette'");
    expect(palette).not.toContain("className='kel-card kel-palette'");
    expect(css).toMatch(/\.kel-palette\[role='dialog'\][^}]*rgba\(15,45,100,\.94\)/);
    expect(css).toMatch(/\.kel-palette\[role='dialog'\][^}]*backdrop-filter: blur\(24px\)/);
  });
});
