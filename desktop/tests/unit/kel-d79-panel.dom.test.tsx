/**
 * D-79 — the simplified work-card detail panel: "Complete" with its date and time in a tooltip, the
 * team as coloured role names (no avatars; what each did in a tooltip; parallel Builders share the
 * Builder colour; every role colour meets 4.5:1 on the dark panel — Kel is dark only, D-82), one-line steps with the full words
 * in a tooltip, and the Review Team's one status.
 */
import React from 'react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelOfficeDetail } from '@renderer/components/kel/workCards/KelOfficeDetail';
import type { OfficeItem, OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';
import {
  COMPLETE_LABEL,
  ROLE_COLOR_KEYS,
  completedAt,
  panelStateLabel,
  reviewProblemLine,
  reviewTeamState,
  roleColorKey,
  teamHeading,
} from '@renderer/components/kel/workCards/workCardModel';
import { MIC_DETAIL, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

const css = readFileSync(resolve(__dirname, '../../packages/desktop/src/renderer/components/kel/workCards/KelWorkCards.css'), 'utf8');

const install = (detail: OfficeItemDetail) => {
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request: vi.fn(async (route: string) => {
      if (route.startsWith('/api/office/item?job=')) return detail;
      if (route.startsWith('/api/handoff')) return { application: null };
      throw new Error(`unexpected ${route}`);
    }),
  };
};

const renderDetail = (detail: OfficeItemDetail) => {
  install(detail);
  render(
    <KelOfficeDetail
      item={detail as unknown as OfficeItem}
      pollMs={60000}
      onClose={() => undefined}
      onRemove={() => undefined}
      onTalk={() => undefined}
      onChanged={() => undefined}
      openFolder={async () => undefined}
    />
  );
};

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('D-79 status', () => {
  it('"Done and checked" becomes "Complete"; the other states keep their short words', () => {
    expect(panelStateLabel({ ...RECEIPTS_DETAIL })).toBe(COMPLETE_LABEL);
    expect(panelStateLabel({ ...MIC_DETAIL, state: 'working' })).toBe('Working');
    expect(panelStateLabel({ ...MIC_DETAIL, state: 'needs_you' })).toBe('Needs you');
  });

  it('the tooltip is MM/DD/YY hh:mm AM/PM', () => {
    const at = new Date(2026, 8, 29, 9, 31).getTime() / 1000;
    expect(completedAt(at)).toBe('09/29/26 09:31 AM');
    expect(completedAt(new Date(2026, 0, 2, 15, 5).getTime())).toBe('01/02/26 03:05 PM');
    expect(completedAt(null)).toBeNull();
  });

  it('hovering "Complete" shows the date and time', async () => {
    renderDetail({ ...RECEIPTS_DETAIL, finished_at: new Date(2026, 8, 29, 9, 31).getTime() / 1000 });
    const word = await screen.findByTestId('kel-office-detail-state-word');
    expect(within(word).getByTestId('kel-office-detail-state').textContent).toBe('Complete');
    expect(word.getAttribute('title')).toBe('09/29/26 09:31 AM');
  });
});

describe('D-79 team', () => {
  it('heads "Team · N agents", has no avatars, and puts what each agent did in its tooltip', async () => {
    renderDetail(MIC_DETAIL);
    const members = await screen.findAllByTestId('kel-office-member');
    const dialog = screen.getByTestId('kel-office-detail');
    expect(dialog.querySelector('.kel-wd-col--team h3')?.textContent).toBe(teamHeading(MIC_DETAIL.staff ?? []));
    expect(dialog.querySelector('.kel-wd-avatar, .kel-wc-avatar')).toBeNull();
    const builder = members.find((row) => row.textContent?.includes('Builder'))!;
    expect(builder.className).toContain('kel-role--builder');
    expect(builder.getAttribute('title')).toBe('Writing the global hotkey listener');
    expect(builder.querySelector('.kel-wd-doing')).toBeNull();
  });

  it('parallel Builders share the Builder colour and keep their "Part N of M" tag', async () => {
    renderDetail({
      ...MIC_DETAIL,
      staff: [
        { id: 'b1', role: 'builder', role_label: 'Builder', step_label: 'Part 1 of 2: the hotkey', state: 'working', model_label: 'Claude Opus 5.5' },
        { id: 'b2', role: 'builder', role_label: 'Builder', step_label: 'Part 2 of 2: the tray', state: 'working', model_label: 'Claude Opus 5.5' },
      ],
    });
    const rows = await screen.findAllByTestId('kel-office-member');
    expect(rows.map((row) => row.className.match(/kel-role--[a-z-]+/)?.[0])).toEqual(['kel-role--builder', 'kel-role--builder']);
    expect(rows.map((row) => within(row).getByTestId('kel-office-step-label').textContent)).toEqual(['Part 1 of 2', 'Part 2 of 2']);
  });

  it('gives every role its own colour key (Kel stays white; unknown roles are neutral)', () => {
    expect(roleColorKey({ role: 'commander' })).toBe('kel');
    expect(roleColorKey({ role: 'red_team' })).toBe('red-team');
    expect(roleColorKey({ role: 'someone_new' })).toBe('other');
    expect(new Set(ROLE_COLOR_KEYS).size).toBe(ROLE_COLOR_KEYS.length);
  });

  const tokens = (scope: string): Record<string, string> => {
    const start = css.indexOf(`${scope} {\n  --kel-role-kel`);
    expect(start).toBeGreaterThanOrEqual(0);
    const body = css.slice(start, css.indexOf('}', start));
    return Object.fromEntries(Array.from(body.matchAll(/--kel-role-([a-z-]+):\s*(#[0-9a-fA-F]{6})/g)).map((m) => [m[1], m[2].toLowerCase()]));
  };
  const lum = (hex: string) => {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const contrast = (a: string, b: string) => {
    const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };

  it('every role colour is distinct and meets 4.5:1 on the dark panel (Kel is dark only, D-82)', () => {
    const surfaces = ['#0e204a', '#132e65'];
    const set = tokens(':root');
    for (const key of ROLE_COLOR_KEYS) {
      expect(set[key], key).toMatch(/^#/);
      for (const surface of surfaces) expect(contrast(set[key], surface), `${key} on ${surface}`).toBeGreaterThanOrEqual(4.5);
    }
    const colours = ROLE_COLOR_KEYS.map((key) => set[key]);
    expect(new Set(colours).size).toBe(colours.length);
    expect(tokens(':root').kel).toBe('#ffffff');
  });
});

describe('D-79 steps', () => {
  it('each step is one line with its full words in a tooltip, and no times', async () => {
    const long = 'Build the hotkey and the tray icon, then wire both into the startup path so it runs at login';
    renderDetail({ ...MIC_DETAIL, steps: [{ id: 's1', label: long, state: 'done', at: 1 }, { id: 's2', label: 'Check it', state: 'running', at: null }] });
    const steps = await screen.findAllByTestId('kel-office-step');
    expect(steps[0].getAttribute('title')).toBe(long);
    expect(within(steps[0]).getByTestId('kel-office-step-text').textContent).toBe(long);
    expect(steps[0].querySelector('.kel-wd-step__when')?.textContent).toBe('');
    expect(steps[1].querySelector('.kel-wd-step__when')?.textContent).toBe('Now');
    // The stylesheet keeps the label on one line with an ellipsis.
    const rule = css.slice(css.indexOf('.kel-wd .kel-wd-step__label {'), css.indexOf('}', css.indexOf('.kel-wd .kel-wd-step__label {')));
    expect(rule).toMatch(/white-space:\s*nowrap/);
    expect(rule).toMatch(/text-overflow:\s*ellipsis/);
    // The icon owns a fixed slot in its own row.
    expect(steps.every((step) => step.querySelector(':scope > .kel-wd-step__lead img'))).toBe(true);
  });
});

describe('D-79 Review Team', () => {
  const base = { ...MIC_DETAIL, review: { verdict: null, findings: [] }, verification: { result: null, summary: [] }, oracle: null } as OfficeItemDetail;

  it.each([
    ['Not started', { ...base, state: 'working' }],
    ['In progress', { ...base, state: 'in_review' }],
    ['Passed', { ...RECEIPTS_DETAIL }],
    ['Failed', { ...base, state: 'failed', review: { verdict: 'failed', findings: [] }, verification: { result: 'failed', summary: [] } }],
  ] as const)('says "%s"', (word, view) => {
    expect(reviewTeamState(view as OfficeItemDetail)).toBe(word);
  });

  it('checks that never ran read "Never ran" — never "Failed" (Nick, 2026-09-29)', async () => {
    const never = { ...base, state: 'failed', review: { verdict: 'uncertain', findings: [] }, verification: { result: 'not_confirmed', summary: [] } } as OfficeItemDetail;
    expect(reviewTeamState(never)).toBe('Never ran');
    renderDetail(never);
    const review = await screen.findByTestId('kel-office-review');
    expect(within(review).getByTestId('kel-office-review-state').textContent).toBe('Never ran');
    expect(screen.getByTestId('kel-office-detail-state').textContent).toBe('Never ran');
    expect(screen.getByTestId('kel-office-detail').textContent).not.toMatch(/Failed|Didn’t pass|Couldn’t fully check/);
  });

  it('a problem is one line: what it is and who is on it', () => {
    const view = {
      ...base,
      state: 'in_review',
      staff: [{ id: 'b', role: 'builder', role_label: 'Builder', state: 'working' }],
      sentinel: { state: 'done', findings: [{ summary: 'A password stored in plain text.', severity: 'blocker', status: 'open' }] },
    } as OfficeItemDetail;
    expect(reviewProblemLine(view)).toBe('Sentinel found a password stored in plain text · Builder is fixing it');
    expect(reviewProblemLine(base)).toBeNull();
  });

  it('renders the one status and the problem line, nothing else', async () => {
    renderDetail({ ...base, state: 'in_review', sentinel: { state: 'done', findings: [{ summary: 'The token is logged', severity: 'critical', status: 'open' }] } } as OfficeItemDetail);
    const review = await screen.findByTestId('kel-office-review');
    expect(within(review).getByTestId('kel-office-review-state').textContent).toBe('In progress');
    expect(within(review).getByTestId('kel-office-review-problem').textContent).toMatch(/^Sentinel found the token is logged/);
    expect(review.children.length).toBe(2);
  });
});
