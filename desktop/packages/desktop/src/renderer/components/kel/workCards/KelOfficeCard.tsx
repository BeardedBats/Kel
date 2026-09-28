/**
 * D-68 — one work card: the reusable component behind every card in the row (Figma 4a) and every
 * entry in the "+N more" menu (Figma 4c). Variants: `row` | `menu`; state variants come from the
 * engine's `state`; `selected` is the open card (Figma 4b). The card itself is a button that opens
 * the detail; a finished card also carries a separate remove button (running work never does).
 */
import React from 'react';
import type { OfficeItem, OfficeTeamChip } from './officeApi';
import { StateIcon, iconClose } from './workCardIcons';
import {
  clockTime,
  initials,
  isFinished,
  progressFraction,
  ringTone,
  roleName,
  stateLabel,
  stepCount,
} from './workCardModel';

const MAX_AVATARS = 3;

export const KelAgentStack: React.FC<{ team: OfficeTeamChip[]; itemState: string }> = ({ team, itemState }) => {
  if (!team.length) return null;
  const shown = team.slice(0, MAX_AVATARS);
  return (
    <span className='kel-wc-agents' aria-hidden='true'>
      {shown.map((member, index) => (
        <span
          key={`${member.role}-${index}`}
          className={`kel-wc-avatar kel-wc-avatar--${ringTone(member, itemState)}`}
          title={roleName(member)}
        >
          {initials(member)}
        </span>
      ))}
    </span>
  );
};

/** The words a screen reader hears for a card: title, state, steps, team. */
export const cardAccessibleName = (item: OfficeItem, team: OfficeTeamChip[]): string => {
  const parts = [item.title, stateLabel(item.state)];
  const count = stepCount(item);
  if (count) parts.push(`${count} steps`);
  if (isFinished(item.state)) {
    const at = clockTime(item.finished_at ?? item.updated_at);
    if (at) parts.push(`finished ${at}`);
  } else if (team.length) {
    parts.push(`team: ${team.map((member) => roleName(member)).join(', ')}`);
  }
  return parts.join(', ');
};

type Props = {
  item: OfficeItem;
  team: OfficeTeamChip[];
  variant?: 'row' | 'menu';
  selected?: boolean;
  removing?: boolean;
  onOpen: (item: OfficeItem, trigger: HTMLElement) => void;
  onRemove?: (item: OfficeItem) => void;
};

export const KelOfficeCard: React.FC<Props> = ({ item, team, variant = 'row', selected = false, removing = false, onOpen, onRemove }) => {
  const finished = isFinished(item.state);
  const label = stateLabel(item.state);
  const count = stepCount(item);
  const at = finished ? clockTime(item.finished_at ?? item.updated_at) : null;
  const fill = `${(progressFraction(item) * 100).toFixed(2)}%`;
  const removable = finished && Boolean(onRemove);

  const progress = (
    <span className='kel-wc-progress' aria-hidden='true'>
      <span className='kel-wc-progress__fill' style={{ width: fill }} />
    </span>
  );

  const labelText = (
    <span className='kel-wc-state-label' data-testid='kel-office-card-state'>
      {label}
    </span>
  );

  return (
    <div
      className={`kel-wc kel-wc--${variant} kel-wc--${item.state}${selected ? ' is-selected' : ''}${removable ? ' has-remove' : ''}`}
      data-testid='kel-office-card'
      data-job={item.job_id}
      data-state={item.state}
    >
      <button
        type='button'
        className='kel-wc__open'
        aria-haspopup='dialog'
        aria-expanded={selected}
        aria-label={cardAccessibleName(item, team)}
        onClick={(event) => onOpen(item, event.currentTarget)}
      >
        {variant === 'row' ? (
          <>
            <span className='kel-wc__title-row'>
              <span className='kel-wc__title'>{item.title}</span>
            </span>
            {progress}
            <span className='kel-wc__state-row'>
              <StateIcon state={item.state} />
              {labelText}
              {count ? <span className='kel-wc-count'>{count}</span> : null}
              <span className='kel-wc-push' />
              {finished ? (at ? <span className='kel-wc-time'>{at}</span> : null) : <KelAgentStack team={team} itemState={item.state} />}
            </span>
          </>
        ) : (
          <>
            <span className='kel-wc__title-row'>
              <StateIcon state={item.state} />
              <span className='kel-wc__title'>{item.title}</span>
              <span className='kel-wc-push' />
            </span>
            <span className='kel-wc__state-row'>
              {progress}
              {labelText}
              {finished ? (at ? <span className='kel-wc-count'>{at}</span> : null) : count ? <span className='kel-wc-count'>{count}</span> : null}
              <span className='kel-wc-push' />
              {finished ? null : <KelAgentStack team={team} itemState={item.state} />}
            </span>
          </>
        )}
      </button>
      {removable ? (
        <button
          type='button'
          className='kel-wc__remove'
          aria-label={`Remove ${item.title}`}
          disabled={removing}
          onClick={(event) => {
            event.stopPropagation();
            onRemove?.(item);
          }}
          data-testid='kel-office-card-remove'
        >
          <img src={iconClose} alt='' />
        </button>
      ) : null}
    </div>
  );
};

export default KelOfficeCard;
