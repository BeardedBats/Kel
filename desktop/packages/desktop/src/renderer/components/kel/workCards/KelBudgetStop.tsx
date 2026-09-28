/**
 * Routing 2 §5.4 — a piece of work that stopped on its budget. The card says what it used against its
 * budget in plain numbers and offers "Raise budget" (`POST /api/office {action:'raise_budget'}`), which
 * moves it one size up and lets it continue; the answer says how big the new budget is. Kel never
 * raises a budget on its own and never continues on a cheaper model.
 */
import React, { useState } from 'react';
import { officeRaiseBudget, type OfficeBudget, type OfficeBudgetCeilings } from './officeApi';
import { StatusDot } from './workCardIcons';

/** The budget sizes in plain words (the engine's classes tiny / standard / deep / high-assurance). */
export const BUDGET_SIZES: Record<string, string> = {
  tiny: 'small',
  standard: 'standard',
  deep: 'large',
  'high-assurance': 'largest',
};

export const budgetSize = (value: string | null | undefined): string => BUDGET_SIZES[String(value ?? '')] ?? String(value ?? 'standard');

const tokens = (value: number): string =>
  value >= 1_000_000 ? `${Number((value / 1_000_000).toFixed(1))}M` : `${Math.round(value / 1000)}K`;

const minutes = (value: number): string => {
  if (value >= 60 && value % 60 === 0) return `${value / 60} hour${value === 60 ? '' : 's'}`;
  return `${value} minutes`;
};

/** "up to 8M tokens, 4 hours of run time and $30 of model use" */
export const ceilingWords = (ceilings: OfficeBudgetCeilings | null | undefined): string | null => {
  if (!ceilings) return null;
  const parts = [
    typeof ceilings.tokens === 'number' ? `${tokens(ceilings.tokens)} tokens` : null,
    typeof ceilings.minutes === 'number' ? `${minutes(ceilings.minutes)} of run time` : null,
    typeof ceilings.cost === 'number' ? `$${ceilings.cost.toFixed(0)} of model use` : null,
  ].filter((part): part is string => Boolean(part));
  if (!parts.length) return null;
  const last = parts.pop();
  return `up to ${parts.length ? `${parts.join(', ')} and ${last}` : last}`;
};

/** "It has used about 2.9M of its 3M tokens, 42 of its 90 minutes and $9.80 of its $10." */
export const usedWords = (budget: OfficeBudget | null | undefined): string | null => {
  const used = budget?.used;
  const ceilings = budget?.ceilings;
  if (!used || !ceilings) return null;
  const parts = [
    typeof used.tokens === 'number' && typeof ceilings.tokens === 'number' ? `${tokens(used.tokens)} of its ${tokens(ceilings.tokens)} tokens` : null,
    typeof used.ms === 'number' && typeof ceilings.minutes === 'number'
      ? `${Math.round(used.ms / 60000)} of its ${ceilings.minutes} minutes`
      : null,
    typeof used.cost === 'number' && typeof ceilings.cost === 'number' ? `$${used.cost.toFixed(2)} of its $${ceilings.cost.toFixed(0)}` : null,
  ].filter((part): part is string => Boolean(part));
  if (!parts.length) return null;
  const last = parts.pop();
  return `It has used about ${parts.length ? `${parts.join(', ')} and ${last}` : last}.`;
};

/** What Nick sees after raising: the new size in plain words. */
export const raisedWords = (from: string | null | undefined, to: string | null | undefined, ceilings: OfficeBudgetCeilings | null | undefined): string => {
  const size = ceilingWords(ceilings);
  return `Raised this work’s budget from ${budgetSize(from)} to ${budgetSize(to)}${size ? ` — ${size}` : ''}. Kel is continuing.`;
};

type Props = {
  job: string;
  budget: OfficeBudget;
  /** Called with what raising did, in plain words, so the panel says it and reads the new state. */
  onRaised: (words: string) => void;
};

export const KelBudgetStop: React.FC<Props> = ({ job, budget, onRaised }) => {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const raise = async () => {
    if (busy) return;
    setBusy(true);
    setNotice('');
    try {
      const out = await officeRaiseBudget(job);
      onRaised(raisedWords(out?.from ?? budget.class, out?.to, out?.ceilings));
    } catch (error) {
      setNotice(String((error as Error)?.message || '').trim() || 'Kel could not raise the budget just now. Try again in a moment.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className='kel-wd-result kel-wd-result--needs' aria-label='Stopped on its budget' data-testid='kel-budget-stop'>
      <div className='kel-wd-result__head'>
        <StatusDot tone='needs' />
        <strong>Stopped on its budget</strong>
      </div>
      <p>
        {`This work reached its ${budgetSize(budget.class)} budget, so Kel stopped before the next step rather than continue on a cheaper model.`}
        {usedWords(budget) ? ` ${usedWords(budget)}` : ''}
      </p>
      <div className='kel-wd-budget__actions'>
        {budget.can_raise ? (
          <button type='button' className='kel-wd-button kel-wd-button--primary' disabled={busy} onClick={() => void raise()} data-testid='kel-budget-raise'>
            Raise budget
          </button>
        ) : (
          <span className='kel-wd-meta'>This work already has the largest budget. Stop it, or talk to Kel about a smaller next step.</span>
        )}
        {budget.can_raise && budget.next ? <span className='kel-wd-meta'>{`Next size: ${budgetSize(budget.next)} — ${ceilingWords(budget.next_ceilings) ?? ''}`}</span> : null}
      </div>
      {notice ? (
        <p className='kel-wd-notice' role='alert'>
          {notice}
        </p>
      ) : null}
    </section>
  );
};

export default KelBudgetStop;
