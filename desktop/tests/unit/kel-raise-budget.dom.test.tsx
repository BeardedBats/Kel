/**
 * Routing 2 §5.4 — a work card that stopped on its budget says what it used and offers "Raise budget",
 * which goes to `POST /api/office {action:'raise_budget'}` and answers with the new size in plain words.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { rendererKelRequestRefusal } from '@/process/services/kel/kelRequestGuard';
import { ceilingWords, raisedWords, usedWords } from '@renderer/components/kel/workCards/KelBudgetStop';
import { KelOfficeDetail } from '@renderer/components/kel/workCards/KelOfficeDetail';
import type { OfficeItem, OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';
import { RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

afterEach(() => cleanup());

const STOPPED_ITEM: OfficeItem = { ...RECEIPTS_DETAIL, job_id: 'job-big', title: 'Big refactor', state: 'needs_you', finished_at: null } as OfficeItem;
const BUDGET = {
  class: 'standard',
  ceilings: { tokens: 3_000_000, minutes: 90, cost: 10 },
  used: { tokens: 2_900_000, ms: 42 * 60000, cost: 9.8 },
  held: { tokens: 0, ms: 0, cost: 0 },
  stopped: true,
  can_raise: true,
  next: 'deep',
  next_ceilings: { tokens: 8_000_000, minutes: 240, cost: 30 },
};

describe('budget words', () => {
  it('names sizes and numbers plainly', () => {
    expect(ceilingWords({ tokens: 8_000_000, minutes: 240, cost: 30 })).toBe('up to 8M tokens, 4 hours of run time and $30 of model use');
    expect(usedWords(BUDGET)).toBe('It has used about 2.9M of its 3M tokens, 42 of its 90 minutes and $9.80 of its $10.');
    expect(raisedWords('standard', 'deep', { tokens: 8_000_000, minutes: 240, cost: 30 })).toBe(
      'Raised this work’s budget from standard to large — up to 8M tokens, 4 hours of run time and $30 of model use. Kel is continuing.'
    );
  });

  it('the work view may raise a budget, and still nothing else', () => {
    expect(rendererKelRequestRefusal('/api/office', { action: 'raise_budget', id: 'job-1' })).toBeNull();
    expect(rendererKelRequestRefusal('/api/office', { action: 'dismiss', id: 'job-1' })).toBeNull();
    expect(rendererKelRequestRefusal('/api/office', { action: 'stop', id: 'job-1' })).not.toBeNull();
  });
});

describe('a card stopped on its budget', () => {
  const renderDetail = (detail: () => OfficeItemDetail) => {
    const request = vi.fn(async (route: string, body?: { action?: string }) => {
      if (route === '/api/office' && body?.action === 'raise_budget')
        return { job_id: 'job-big', from: 'standard', to: 'deep', ceilings: { tokens: 8_000_000, minutes: 240, cost: 30 } };
      if (route.startsWith('/api/office/item')) return detail();
      return {};
    });
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    const onChanged = vi.fn();
    render(
      <KelOfficeDetail item={STOPPED_ITEM} pollMs={10000} onClose={() => undefined} onRemove={() => undefined} onTalk={() => undefined} onChanged={onChanged} />
    );
    return { request, onChanged };
  };

  it('offers Raise budget and says how big the new budget is', async () => {
    let current: OfficeItemDetail = { ...RECEIPTS_DETAIL, ...STOPPED_ITEM, budget: BUDGET } as OfficeItemDetail;
    const { request, onChanged } = renderDetail(() => current);
    const panel = await screen.findByTestId('kel-budget-stop');
    expect(panel.textContent).toContain('This work reached its standard budget');
    expect(panel.textContent).toContain('It has used about 2.9M of its 3M tokens');
    expect(panel.textContent).toContain('Next size: large — up to 8M tokens');
    current = { ...current, state: 'working', budget: { ...BUDGET, class: 'deep', stopped: false, can_raise: false } } as OfficeItemDetail;
    fireEvent.click(screen.getByTestId('kel-budget-raise'));
    const raised = await screen.findByTestId('kel-budget-raised');
    expect(raised.textContent).toBe(
      'Raised this work’s budget from standard to large — up to 8M tokens, 4 hours of run time and $30 of model use. Kel is continuing.'
    );
    expect(request).toHaveBeenCalledWith('/api/office', { action: 'raise_budget', id: 'job-big' });
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(screen.queryByTestId('kel-budget-stop')).toBeNull();
  });

  it('the largest budget cannot be raised and says so', async () => {
    renderDetail(() => ({ ...RECEIPTS_DETAIL, ...STOPPED_ITEM, budget: { ...BUDGET, class: 'high-assurance', can_raise: false, next: null } }) as OfficeItemDetail);
    const panel = await screen.findByTestId('kel-budget-stop');
    expect(panel.textContent).toContain('already has the largest budget');
    expect(screen.queryByTestId('kel-budget-raise')).toBeNull();
  });
});
