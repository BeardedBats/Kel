/**
 * D-68 — one work card: the reusable component behind every card in the row (Figma 4a) and every
 * entry in the "+N more" menu (Figma 4c). Variants: `row` | `menu`; state variants come from the
 * engine's `state`; `selected` is the open card (Figma 4b). The card itself is a button that opens
 * the detail; a finished card also carries a separate remove button (running work never does).
 */
import React, { useLayoutEffect, useRef } from 'react';
import { ProgressFill, RollText, SwapIn, cardStateTransition, exitGhostAt, fillTone, enter, prepareEnter, pulse, settleIn, snapshotGhost, useArrival, useEntrance, type Snapshot } from '@renderer/motion';
import type { OfficeItem, OfficeTeamChip } from './officeApi';
import { StateIcon, iconClose } from './workCardIcons';
import {
  cardUncertain,
  clockTime,
  initials,
  cardStateLabel,
  isFinished,
  progressFraction,
  questionCount,
  ringTone,
  roleName,
  stepCount,
} from './workCardModel';
import './KelWorkCardsRow5.css';

const MAX_AVATARS = 3;

/** One avatar: pops in when it joins while Nick watches (§10.7), pulses when its ring changes (§10.4). */
const KelAvatar: React.FC<{ member: OfficeTeamChip; tone: string; index: number }> = ({ member, tone, index }) => {
  const ref = useRef<HTMLSpanElement>(null);
  const arrived = useArrival();
  const lastTone = useRef(tone);
  useEntrance(ref, arrived, { y: 0, blur: 4, scale: 0.6, delay: index * 60 });
  useLayoutEffect(() => {
    if (lastTone.current === tone) return;
    lastTone.current = tone;
    void pulse(ref.current, 40 + index * 45);
  }, [tone]);
  return (
    <span ref={ref} className={`kel-wc-avatar kel-wc-avatar--${tone}`} title={roleName(member)}>
      {initials(member)}
    </span>
  );
};

/** The finish beat: the old avatars leave as a copy (already gone from the layout), time and × settle. */
const settleFinish = async (card: HTMLElement, agents: Snapshot | null) => {
  void exitGhostAt(agents, { scale: 0.6, blur: 4, ms: 120 });
  const parts = Array.from(card.querySelectorAll<HTMLElement>(':scope > .kel-wc__remove, .kel-wc-time'));
  prepareEnter(parts, { y: 0, blur: 3 });
  await settleIn(parts, { stagger: 40, delay: 80 });
};

export const KelAgentStack: React.FC<{ team: OfficeTeamChip[]; itemState: string; max?: number }> = ({ team, itemState, max = MAX_AVATARS }) => {
  if (!team.length) return null;
  const shown = team.slice(0, max);
  return (
    <span className='kel-wc-agents' aria-hidden='true' data-count={shown.length}>
      {shown.map((member, index) => (
        <KelAvatar key={`${member.role}-${index}`} member={member} tone={ringTone(member, itemState)} index={index} />
      ))}
    </span>
  );
};

/** The words a screen reader hears for a card: title, state, steps, team. */
export const cardAccessibleName = (item: OfficeItem, team: OfficeTeamChip[]): string => {
  const parts = [item.title, cardStateLabel(item)];
  const count = stepCount(item);
  if (count) parts.push(`${count} steps`);
  const questions = item.state === 'scoping' ? questionCount(item) : null;
  if (questions) parts.push(`Kel has ${questions} before it starts`);
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
  /** `strip` is the phone's compact card: the team sits beside the title so the state row fits. */
  variant?: 'row' | 'menu' | 'strip';
  selected?: boolean;
  removing?: boolean;
  onOpen: (item: OfficeItem, trigger: HTMLElement) => void;
  onRemove?: (item: OfficeItem) => void;
  /** D-74.3: "Not now" on an open scoping card — cancels Kel's questions; nothing starts. */
  onNotNow?: (item: OfficeItem) => void;
};

export const KelOfficeCard: React.FC<Props> = ({ item, team, variant = 'row', selected = false, removing = false, onOpen, onRemove, onNotNow }) => {
  const lastStateForFill = useRef(item.state);
  useLayoutEffect(() => {
    lastStateForFill.current = item.state;
  });
  const finished = isFinished(item.state);
  const scoping = item.state === 'scoping';
  const label = cardStateLabel(item);
  // LIVE-10: the list's own verdict tells work Kel couldn't fully check from work that failed.
  const uncertain = cardUncertain(item);
  const notNow = scoping && Boolean(onNotNow);
  // D-70 (5e): a scoping card counts Kel's questions, has no progress yet and no team yet.
  const count = scoping ? questionCount(item) : stepCount(item);
  const at = finished ? clockTime(item.finished_at ?? item.updated_at) : null;
  const fill = `${(progressFraction(item) * 100).toFixed(2)}%`;
  const removable = finished && Boolean(onRemove);

  void fill;
  // D-78 §10.7: a scoping card that starts — its track appears and the first step's fill stretches in.
  const startedFromScoping = lastStateForFill.current === 'scoping' && !scoping;
  // D-78: a finished state is the resting end of the chain — it settles in (MOTION.md §2.1).
  const settling = cardStateTransition(item.state) === 'settling';
  const stateKey = `${item.state}${uncertain ? ':uncertain' : ''}`;

  const progress = scoping ? (
    <span className='kel-wc-progress kel-wc-progress--none' aria-hidden='true' />
  ) : (
    <span className='kel-wc-progress' aria-hidden='true'>
      <ProgressFill fraction={progressFraction(item)} tone={fillTone(item.state, uncertain)} mountFrom={startedFromScoping ? 0 : undefined} />
    </span>
  );

  // §10.4 Done: the avatars step away from where they were; the finish time and the remove × settle in.
  const cardRef = useRef<HTMLDivElement>(null);
  const lastState = useRef(item.state);
  const leaving = useRef<Snapshot | null>(null);
  if (lastState.current !== item.state && !isFinished(lastState.current) && finished && cardRef.current) {
    leaving.current = snapshotGhost(cardRef.current.querySelector('.kel-wc-agents'));
  }
  useLayoutEffect(() => {
    const before = lastState.current;
    lastState.current = item.state;
    if (before === 'scoping' && item.state !== 'scoping' && cardRef.current) {
      const track = cardRef.current.querySelector<HTMLElement>('.kel-wc-progress');
      if (track) {
        prepareEnter(track, { y: 0, blur: 0 });
        void enter(track, { y: 0, blur: 0, ms: 160 });
      }
    }
    if (before === item.state || isFinished(before) || !finished) return;
    const card = cardRef.current;
    if (!card) return;
    void settleFinish(card, leaving.current);
    leaving.current = null;
  }, [item.state]);

  const labelText = <RollText className='kel-wc-state-label' value={label} settle={settling} testId='kel-office-card-state' />;
  const countText = count ? <RollText className='kel-wc-count' value={count} /> : null;
  const icon = (
    <SwapIn className='kel-wc-state-icon' swapKey={stateKey} draw={item.state === 'done'} settle={settling}>
      <StateIcon state={item.state} uncertain={uncertain} />
    </SwapIn>
  );

  return (
    <div
      ref={cardRef}
      className={`kel-wc kel-wc--${variant === 'strip' ? 'row kel-wc--strip' : variant} kel-wc--${item.state}${selected ? ' is-selected' : ''}${removable ? ' has-remove' : ''}${uncertain ? ' is-uncertain' : ''}${notNow ? ' has-not-now' : ''}`}
      data-testid='kel-office-card'
      data-job={item.job_id}
      data-state={item.state}
    >
      <button
        type='button'
        className='kel-wc__open'
        aria-haspopup={scoping ? undefined : 'dialog'}
        aria-expanded={scoping ? undefined : selected}
        aria-label={cardAccessibleName(item, team)}
        onClick={(event) => onOpen(item, event.currentTarget)}
      >
        {variant === 'strip' ? (
          <>
            <span className='kel-wc__title-row'>
              <span className='kel-wc__title'>{item.title}</span>
              {finished || scoping ? null : <KelAgentStack team={team} itemState={item.state} max={2} />}
            </span>
            {progress}
            <span className='kel-wc__state-row'>
              {icon}
              {labelText}
              {countText}
              <span className='kel-wc-push' />
              {finished && at ? <span className='kel-wc-time'>{at}</span> : null}
            </span>
          </>
        ) : variant === 'row' ? (
          <>
            <span className='kel-wc__title-row'>
              <span className='kel-wc__title'>{item.title}</span>
            </span>
            {progress}
            <span className='kel-wc__state-row'>
              {icon}
              {labelText}
              {countText}
              <span className='kel-wc-push' />
              {finished ? (at ? <span className='kel-wc-time'>{at}</span> : null) : scoping ? null : <KelAgentStack team={team} itemState={item.state} />}
            </span>
          </>
        ) : (
          <>
            <span className='kel-wc__title-row'>
              {icon}
              <span className='kel-wc__title'>{item.title}</span>
              <span className='kel-wc-push' />
            </span>
            <span className='kel-wc__state-row'>
              {progress}
              {labelText}
              {finished ? (at ? <span className='kel-wc-count'>{at}</span> : null) : countText}
              <span className='kel-wc-push' />
              {finished || scoping ? null : <KelAgentStack team={team} itemState={item.state} />}
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
      {notNow ? (
        <button
          type='button'
          className='kel-wc__not-now'
          aria-label={`Not now: ${item.title}`}
          title='Cancel these questions. Nothing starts.'
          disabled={removing}
          onClick={(event) => {
            event.stopPropagation();
            onNotNow?.(item);
          }}
          data-testid='kel-office-card-not-now'
        >
          Not now
        </button>
      ) : null}
    </div>
  );
};

export default KelOfficeCard;
