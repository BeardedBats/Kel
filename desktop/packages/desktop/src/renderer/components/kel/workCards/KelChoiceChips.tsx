/**
 * D-70 — quick-pick chips (Figma row 5: 5a "Kel is asking you", 5e scoping card). Reusable: a row
 * of answers to pick from, the picked one filled with a check, and an optional dashed
 * "Something else…" chip that hands over to a typed answer. A radio group for assistive tech.
 */
import React from 'react';
import { iconCheck12Light } from './workCardIcons';

export interface ChoiceChip {
  id: string;
  label: string;
}

type Props = {
  options: ChoiceChip[];
  /** The picked chip's id; `OTHER_CHIP` when "Something else…" is picked; null for none. */
  selected?: string | null;
  onPick: (id: string) => void;
  /** Show the dashed "Something else…" chip. */
  other?: boolean;
  otherLabel?: string;
  disabled?: boolean;
  /** Names the group ("Where should it live?"). */
  label: string;
  testId?: string;
};

export const OTHER_CHIP = '__other__';

export const KelChoiceChips: React.FC<Props> = ({
  options,
  selected = null,
  onPick,
  other = false,
  otherLabel = 'Something else…',
  disabled = false,
  label,
  testId,
}) => (
  <div className='kel-chips' role='radiogroup' aria-label={label} data-testid={testId}>
    {options.map((option) => {
      const picked = selected === option.id;
      return (
        <button
          key={option.id}
          type='button'
          role='radio'
          aria-checked={picked}
          className={`kel-chip-pick${picked ? ' is-picked' : ''}`}
          disabled={disabled}
          onClick={() => onPick(option.id)}
          data-testid='kel-chip'
        >
          {picked ? <img src={iconCheck12Light} alt='' /> : null}
          {option.label}
        </button>
      );
    })}
    {other ? (
      <button
        type='button'
        role='radio'
        aria-checked={selected === OTHER_CHIP}
        className={`kel-chip-pick kel-chip-pick--other${selected === OTHER_CHIP ? ' is-picked' : ''}`}
        disabled={disabled}
        onClick={() => onPick(OTHER_CHIP)}
        data-testid='kel-chip-other'
      >
        {otherLabel}
      </button>
    ) : null}
  </div>
);

export default KelChoiceChips;
