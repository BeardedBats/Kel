/**
 * D-72 — what Kel's replies and work used: the model and time on a reply's timestamp line with the cost
 * and tokens in its tooltip (FIX-0026), the cost and time in a work card's detail header, and the engine
 * route that reads both. A subscription call says "Included in your plan", never "$0.00"; unknown
 * numbers are left out.
 */
import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { shownKelMeta } from '@/common/chat/kelMessageMeta';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';
import { costWords, replyUsageWords, timeWords, tokenWords, usageHeaderLine } from '@renderer/components/kel/usage/usageWords';
import { KelOfficeDetail } from '@renderer/components/kel/workCards/KelOfficeDetail';
import { RECEIPTS, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

afterEach(() => cleanup());

const PLAN = { calls: 1, tokens: 1432, ms: 3400, cost: null, billing: 'plan', plan_cost_equivalent: 0.05, model_label: 'ChatGPT Luna', models: ['ChatGPT Luna'] };
const METERED = { calls: 1, tokens: 980, ms: 1200, cost: 0.0213, cost_basis: 'reported', billing: 'metered', model_label: 'DeepSeek Flash' };

describe('usage words', () => {
  it('says the plan instead of $0.00, and marks an estimate', () => {
    expect(costWords(PLAN)).toBe('Included in your plan');
    expect(costWords(METERED)).toBe('$0.02');
    expect(costWords({ ...METERED, cost_basis: 'estimated' })).toBe('~$0.02');
    expect(costWords({ ...METERED, cost: 0.0004 })).toBe('<$0.01');
    expect(costWords({ billing: 'mixed', cost: 0.4, cost_basis: 'reported' })).toBe('$0.40 + your plan');
    expect(costWords({ billing: 'metered', cost: null })).toBeNull();
  });

  it('formats tokens and time compactly, leaving unknowns out', () => {
    expect(tokenWords(1432)).toBe('1.4K tokens');
    expect(tokenWords(null)).toBeNull();
    expect(timeWords(3400)).toBe('3.4 s');
    expect(timeWords(42000)).toBe('42 s');
    expect(timeWords(5 * 60000)).toBe('5 min');
    expect(timeWords(65 * 60000)).toBe('1 h 5 min');
    expect(replyUsageWords({ billing: 'metered', cost: null, tokens: null, ms: null })).toEqual({ shown: [], hint: null });
    expect(usageHeaderLine(PLAN)).toBe('Included in your plan  ·  1.4K tokens  ·  3.4 s of model time');
  });
});

describe('a reply’s usage (FIX-0026)', () => {
  it('shows the model and time after the reply’s time, cost and tokens only in the tooltip', () => {
    expect(replyUsageWords(METERED)).toEqual({ shown: ['DeepSeek Flash', '1.2 s'], hint: '$0.02 · 980 tokens' });
    expect(replyUsageWords({ ...PLAN, ms: 3600, tokens: 2900 })).toEqual({ shown: ['ChatGPT Luna', '3.6 s'], hint: 'Included in your plan · 2.9K tokens' });
  });

  it('never says $0.00 for a subscription reply, and leaves unknowns out', () => {
    expect(replyUsageWords(PLAN).hint).not.toContain('$0.00');
    expect(replyUsageWords({ billing: 'plan', models: ['Codex'], ms: null })).toEqual({ shown: ['Codex'], hint: 'Included in your plan' });
    expect(replyUsageWords(null)).toEqual({ shown: [], hint: null });
  });

  it('a plain reply keeps only its usage through the chat’s filter', () => {
    expect(shownKelMeta({ answered_by: { label: 'ChatGPT Luna' }, usage: PLAN })).toEqual({ usage: PLAN });
    expect(shownKelMeta({ answered_by: { label: 'ChatGPT Luna' } })).toBeNull();
    const result = { kind: 'result', job: 'j', usage: PLAN };
    expect(shownKelMeta(result)).toBe(result);
  });
});

describe('the engine route', () => {
  it('admits the usage reads and nothing else', () => {
    expect(rendererKelRequestRefusal('/api/usage?conversation=abc-1')).toBeNull();
    expect(rendererKelRequestRefusal('/api/usage?job=job-1')).toBeNull();
    expect(rendererKelRequestRefusal('/api/usage')).not.toBeNull();
    expect(rendererKelRequestRefusal('/api/usage?job=../x')).not.toBeNull();
  });
});

describe('a work card’s detail header', () => {
  it('shows the work’s cost and model time', async () => {
    const request = vi.fn(async (route: string) => {
      if (route.startsWith('/api/office/item')) return { ...RECEIPTS_DETAIL, usage: { ...METERED, tokens: 86000, ms: 180000, billing: 'mixed', cost: 0.4 } };
      return {};
    });
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    render(
      <KelOfficeDetail item={RECEIPTS} pollMs={10000} onClose={() => undefined} onRemove={() => undefined} onTalk={() => undefined} onChanged={() => undefined} />
    );
    await waitFor(() => expect(screen.getByTestId('kel-office-usage').textContent).toBe('$0.40 + your plan  ·  86K tokens  ·  3 min of model time'));
  });

  it('says a subscription job is included in the plan', async () => {
    const request = vi.fn(async () => ({ ...RECEIPTS_DETAIL, usage: { ...PLAN, ms: 60000 } }));
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    render(
      <KelOfficeDetail item={RECEIPTS} pollMs={10000} onClose={() => undefined} onRemove={() => undefined} onTalk={() => undefined} onChanged={() => undefined} />
    );
    await waitFor(() => expect(screen.getByTestId('kel-office-usage').textContent).toContain('Included in your plan'));
  });
});
