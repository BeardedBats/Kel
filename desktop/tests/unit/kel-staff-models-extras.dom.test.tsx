/**
 * Settings → Staff & models: "fell back to X last time" per role (the engine's last run, asked vs
 * ran) and the read-only "How Kel picks models" table from `/api/model {action:'ranking'}`.
 */
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StaffModelsSettings, { RankingCard } from '@renderer/pages/settings/StaffModelsSettings';
import { fellBackLine } from '@renderer/components/kel/staffModels/staffModelsApi';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key }) }));

const MODELS = [
  { id: 'claude-opus-5-5', label: 'Claude Opus 5.5', available: true, reasoning_options: ['auto', 'low', 'high'] },
  { id: 'codex', label: 'Codex', available: true, reasoning_options: ['auto'] },
];
const ROLES = [
  {
    role: 'builder', label: 'Builder', mode: 'PREFERRED', model: 'claude-opus-5-5', model_label: 'Claude Opus 5.5', reasoning: 'auto',
    available: true, is_default: true, fallbacks: ['Codex'],
    last_run: { asked: 'claude-opus-5-5', asked_label: 'Claude Opus 5.5', ran: 'codex', ran_label: 'Codex', fell_back: true, confirmed: true,
      why: "Claude Opus 5.5 can't run here: your account doesn't offer it in Claude Code" },
  },
  {
    role: 'verifier', label: 'Verifier', mode: 'PREFERRED', model: 'codex', model_label: 'Codex', reasoning: 'auto', available: true, is_default: false,
    last_run: { asked: 'codex', asked_label: 'Codex', ran: 'codex', ran_label: 'Codex', fell_back: false, confirmed: true },
  },
];
const RANKING = {
  classes: [
    {
      task_class: 'coding', label: 'Coding', role: 'builder', role_label: 'Builder', mode: 'PREFERRED', tier: 'standard', tier_label: 'Standard',
      models: [
        { id: 'claude-opus-5-5', label: 'Claude Opus 5.5', rank: 1, runnable: true, protected: true, why: 'your preferred choice for Builder' },
        { id: 'codex', label: 'Codex', rank: 2, runnable: true, protected: true, why: 'the fallback you set for Builder' },
        { id: 'gpt-6-astra', label: 'GPT-6 Astra', rank: 3, runnable: true, why: 'a looser fit for standard work; included in your plan' },
        { id: 'deepseek-flash', label: 'DeepSeek Flash', rank: 4, runnable: false, why: 'DeepSeek Flash needs a DeepSeek API key' },
      ],
    },
    {
      task_class: 'review', label: 'Review', role: 'verifier', role_label: 'Verifier', mode: 'AUTOMATIC', tier: 'assurance', tier_label: 'Assurance',
      models: [{ id: 'deepseek-flash', label: 'DeepSeek Flash', rank: 1, runnable: false, why: 'needs a key' }],
    },
  ],
};

beforeEach(() => {
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request: vi.fn(async (route: string, body?: { action?: string }) => {
      if (route === '/api/model' && body?.action === 'ranking') return RANKING;
      if (route === '/api/model') return { roles: ROLES, models: MODELS, modes: [] };
      return {};
    }),
  };
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('fell back last time', () => {
  it('reads the engine’s last run in one plain line', () => {
    expect(fellBackLine(ROLES[0].last_run)).toBe(
      "Fell back to Codex last time (asked for Claude Opus 5.5): Claude Opus 5.5 can't run here: your account doesn't offer it in Claude Code."
    );
    expect(fellBackLine(ROLES[1].last_run)).toBeNull();
    expect(fellBackLine(null)).toBeNull();
  });

  it('shows on the role that fell back and nowhere else', async () => {
    render(
      <MemoryRouter initialEntries={['/settings/staff']}>
        <StaffModelsSettings />
      </MemoryRouter>
    );
    expect((await screen.findByTestId('staff-last-builder')).textContent).toMatch(/^Fell back to Codex last time/);
    expect(screen.queryByTestId('staff-last-verifier')).toBeNull();
  });
});

describe('How Kel picks models', () => {
  it('lists each kind of work with plain labels and the order Kel tries', async () => {
    render(<RankingCard />);
    const table = await screen.findByTestId('staff-ranking');
    expect([...table.querySelectorAll('thead th')].map((th) => th.textContent)).toEqual(['Work', 'Decided by', 'Effort', 'Kel tries']);
    const coding = within(table).getByTestId('ranking-row-coding');
    expect([...coding.querySelectorAll('th, td')].map((cell) => cell.textContent)).toEqual([
      'Coding',
      'Builder · Preferred',
      'Standard',
      "Claude Opus 5.5, then Codex, then GPT-6 Astra" + 'Claude Opus 5.5: your preferred choice for Builder.' + "1 other model can't run here.",
    ]);
    const review = within(table).getByTestId('ranking-row-review');
    expect(review.textContent).toContain('Verifier · Automatic');
    expect(review.textContent).toContain('Most careful');
    expect(review.textContent).toContain('Nothing can run this here yet.');
  });
});
