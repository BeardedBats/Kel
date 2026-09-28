/**
 * VIS-2 / D-73.2 / JR-25 — the work-card colours come from one token set with a Light swap, and every
 * text token meets 4.5:1 on the card surfaces it sits on, in both modes. The surfaces are the ones the
 * stylesheet paints (dark: the Figma fills composited over the chat background; light: white, the pale
 * box fill and the selected card).
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const dir = resolve(__dirname, '../../packages/desktop/src/renderer/components/kel/workCards');
const row5 = readFileSync(resolve(dir, 'KelWorkCardsRow5.css'), 'utf8');
const cards = readFileSync(resolve(dir, 'KelWorkCards.css'), 'utf8');

const block = (selector: string): Record<string, string> => {
  const start = row5.indexOf(`${selector} {`);
  expect(start).toBeGreaterThanOrEqual(0);
  const body = row5.slice(start, row5.indexOf('}', start));
  const out: Record<string, string> = {};
  for (const match of body.matchAll(/--kel-wc-([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)) out[match[1]] = match[2];
  return out;
};

const luminance = (hex: string) => {
  const channels = [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const contrast = (a: string, b: string) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const TEXT = ['text', 'text-2', 'muted', 'faint', 'link', 'soft', 'needs-text', 'done-text', 'cyan', 'red'];
/** Dark: the detail panel, a card, and a result box, composited (see the audit notes). */
const DARK_SURFACES = ['#0e204a', '#132e65', '#122d64'];
/** Light: the panel/card, the box fill, the selected card. */
const LIGHT_SURFACES = ['#ffffff', '#f4f7fc', '#e9f0fc'];

describe('work-card colours (VIS-2, JR-25)', () => {
  it('define every text token for both modes', () => {
    const dark = block(':root');
    const light = block("html[data-theme='light']");
    for (const token of TEXT) {
      expect(dark[token], `dark ${token}`).toMatch(/^#/);
      expect(light[token], `light ${token}`).toMatch(/^#/);
    }
  });

  it.each([
    ['dark', ':root', DARK_SURFACES],
    ['light', "html[data-theme='light']", LIGHT_SURFACES],
  ] as const)('meets 4.5:1 for text in %s mode', (_mode, selector, surfaces) => {
    const tokens = block(selector);
    for (const token of TEXT)
      for (const surface of surfaces) expect(contrast(tokens[token], surface), `${token} on ${surface}`).toBeGreaterThanOrEqual(4.5);
  });

  it('paints no hard-coded text colours outside the tokens (primary buttons keep their Figma fill)', () => {
    const colours = [...`${cards}\n${row5.replace(/:root \{[\s\S]*?\}\nhtml\[data-theme='light'\] \{[\s\S]*?\}/, '')}`.matchAll(/(?<![-\w])color:\s*(#[0-9a-fA-F]{3,8})/g)].map(
      (match) => match[1].toLowerCase()
    );
    expect(new Set(colours)).toEqual(new Set(['#fff1f0']));
  });

  it('gives the cards, menu, detail, done card, scoping card and chips a Light surface', () => {
    const lightRules = row5
      .split(/\r?\n/)
      .filter((line) => line.startsWith("html[data-theme='light'] "))
      .join('\n');
    for (const piece of ['.kel-wc--row', '.kel-wc-menu', '.kel-wd', '.kel-dc', '.kel-sc', '.kel-chip-pick', '.kel-answer__box', '.kel-wc-overflow', '.kel-wd-result'])
      expect(lightRules, piece).toMatch(new RegExp(`\\${piece}(?![\\w-])`));
  });
});
