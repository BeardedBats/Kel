/**
 * D-88: the Writer and the Animator are staff roles — a Settings row each (in the order work flows),
 * a plain line saying what they do, and their own pale role colour on the dark work panel (D-79, D-82).
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { STAFF_DESCRIPTIONS, STAFF_ORDER } from '../../packages/desktop/src/renderer/components/kel/staffModels/staffModelsApi';
import { ROLE_COLOR_KEYS, roleColorKey, roleName } from '../../packages/desktop/src/renderer/components/kel/workCards/workCardModel';

describe('D-88 Writer and Animator roles', () => {
  it('sit in the Settings order where work flows: Writer before Builder, Animator after it', () => {
    const order = [...STAFF_ORDER] as string[];
    expect(order.indexOf('writer')).toBe(order.indexOf('builder') - 1);
    expect(order.indexOf('animator')).toBe(order.indexOf('builder') + 1);
    expect(STAFF_DESCRIPTIONS.writer).toMatch(/words/);
    expect(STAFF_DESCRIPTIONS.animator).toMatch(/motion/);
  });

  it('each has its own colour key and name', () => {
    expect(roleColorKey({ role: 'writer' })).toBe('writer');
    expect(roleColorKey({ role: 'animator' })).toBe('animator');
    expect(roleName({ role: 'animator', role_label: '' })).toBe('Animator');
    expect(new Set(ROLE_COLOR_KEYS).size).toBe(ROLE_COLOR_KEYS.length);
  });

  it('defines both colours in the stylesheet, distinct from every other role', () => {
    const css = readFileSync(join(__dirname, '../../packages/desktop/src/renderer/components/kel/workCards/KelWorkCards.css'), 'utf8');
    const colours = Object.fromEntries(Array.from(css.matchAll(/--kel-role-([a-z-]+):\s*(#[0-9a-fA-F]{6})/g)).map((m) => [m[1], m[2].toLowerCase()]));
    expect(colours.writer).toBeTruthy();
    expect(colours.animator).toBeTruthy();
    const all = ROLE_COLOR_KEYS.map((key) => colours[key]);
    expect(new Set(all).size).toBe(all.length);
    expect(css).toContain('.kel-role--writer');
    expect(css).toContain('.kel-role--animator');
  });
});
