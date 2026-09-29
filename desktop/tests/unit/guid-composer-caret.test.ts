/**
 * FIX-0018 and the selection "shadow" in the Home composer (both measured off-screen on 2026-09-29).
 *
 * A 12px border radius on the one-line textarea clipped the caret to about 11px at the start of the
 * line (19px once any text was typed) and cut the selection highlight into a rounded, shadowed shape.
 * Nick also asked that "What's up?" leave as soon as the box is focused. Layout is not available in
 * jsdom, so these pin the two sources of those behaviours.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(__dirname, '../../packages/desktop/src/renderer');
const card = readFileSync(resolve(root, 'pages/guid/components/GuidInputCard.tsx'), 'utf8');
const shell = readFileSync(resolve(root, 'styles/kel-shell.css'), 'utf8');

describe('Home composer textarea (FIX-0018)', () => {
  it('has no border radius of its own, so the caret and the selection are never clipped', () => {
    const textarea = card.slice(card.indexOf('<Input.TextArea'), card.indexOf("data-testid='guid-input'"));
    expect(textarea).toContain('className=');
    expect(textarea).not.toMatch(/\brounded(-|\b)/);
  });

  it('hides the placeholder while the composer is focused', () => {
    expect(shell).toMatch(
      /\.kel-v2-shell :is\(\.kel-shell-composer, \.sendbox-panel\) textarea:focus::placeholder \{ color: transparent !important; -webkit-text-fill-color: transparent !important; \}/
    );
  });
});
