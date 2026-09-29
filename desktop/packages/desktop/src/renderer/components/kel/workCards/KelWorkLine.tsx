/**
 * D-70 item 2 — one live view (Figma 5c, 5d). While staffed work runs, the in-thread work card is
 * this single line under Kel's acknowledgement: "Handed to the team · <title> · <state> · X of Y —
 * follow it above". It names the same state as the work's top card and opens that card's panel;
 * nothing else in the thread repeats the work. When the work finishes the line points down to Kel's
 * result message, which carries the done card.
 */
import React, { useLayoutEffect, useRef } from 'react';
import { RollText, SwapIn, cardStateTransition, enter, frameWrite, isReducedMotion, offerShared, prepareEnter, spring, useArrival } from '@renderer/motion';
import type { KelHandoff } from '../kelApi';
import { StatusDot, iconCheck, iconChevronDown, iconStopMuted, iconWarning } from './workCardIcons';
import { openWorkCard } from './workCardEvents';
import { UNCERTAIN_LABEL } from './workCardModel';
import './KelWorkCardsRow5.css';

type LineState = 'starting' | 'working' | 'in_review' | 'needs_you' | 'done' | 'failed' | 'stopped';

/** The line's state, from the same engine words the top card uses (`office_state`). */
export const lineState = (view: Pick<KelHandoff, 'phase' | 'verdict' | 'job_id'> & { office_state?: string | null }): LineState => {
  if (!view.job_id) return 'starting';
  switch (view.office_state) {
    case 'working':
    case 'in_review':
    case 'needs_you':
    case 'done':
    case 'failed':
    case 'stopped':
      return view.office_state;
    default:
      break;
  }
  if (view.phase === 'stopped') return 'stopped';
  if (view.phase === 'done') return view.verdict === 'VERIFIED' ? 'done' : 'failed';
  if (view.phase === 'needs_look') return 'failed';
  if (view.phase === 'needs_you') return 'needs_you';
  return 'working';
};

const counted = (view: Pick<KelHandoff, 'accepted' | 'total'>): string | null =>
  view.total > 0 ? `${Math.min(view.accepted, view.total)} of ${view.total}` : null;

/** "Working · 2 of 5", "Done and checked", "Didn't pass its checks" — never "checked" unless VERIFIED. */
export const lineWords = (state: LineState, view: Pick<KelHandoff, 'accepted' | 'total' | 'verdict'>): string => {
  const count = counted(view);
  switch (state) {
    case 'starting':
      return 'Getting started';
    case 'in_review':
      return count ? `In review · ${count}` : 'In review';
    case 'needs_you':
      return 'Needs you';
    case 'done':
      return view.verdict === 'VERIFIED' ? 'Done and checked' : 'Done';
    case 'failed':
      // LIVE-10: checks Kel could not confirm are not checks that failed.
      return String(view.verdict ?? '').toUpperCase() === 'UNCERTAIN' ? UNCERTAIN_LABEL : 'Didn’t pass its checks';
    case 'stopped':
      return 'Stopped';
    default:
      return count ? `Working · ${count}` : 'Working';
  }
};

const FINISHED: LineState[] = ['done', 'failed', 'stopped'];

type Props = {
  view: KelHandoff & { office_state?: string | null };
};

export const KelWorkLine: React.FC<Props> = ({ view }) => {
  const state = lineState(view);
  const finished = FINISHED.includes(state);
  const words = lineWords(state, view);
  const pointer = finished ? (state === 'stopped' ? '— see it above' : '— result below') : '— follow it above';
  const job = view.job_id;

  const lineRef = useRef<HTMLButtonElement>(null);
  const arrived = useArrival();
  const settling = cardStateTransition(state) === 'settling';

  // §10.2 step 1: a line that arrives while Nick watches reveals from its leading edge, its parts in order.
  useLayoutEffect(() => {
    const line = lineRef.current;
    if (!arrived || !line) return;
    const parts = Array.from(line.querySelectorAll<HTMLElement>(':scope > *'));
    prepareEnter(parts);
    if (!isReducedMotion()) {
      line.style.clipPath = 'inset(0 100% 0 0 round 8px)';
      void spring(0, 1, 'morph', (v) => {
        frameWrite(line, () => {
          line.style.clipPath = v >= 0.999 ? '' : `inset(0 ${((1 - v) * 100).toFixed(2)}% 0 0 round 8px)`;
        });
      }, { eps: 0.001 }).finished.then(() => {
        line.style.clipPath = '';
      });
    }
    void enter(parts, { stagger: 25, delay: 60 });
  }, []);

  // §10.2 step 2: the top card lifts out of this line once the row has the work (a shared element).
  const offered = useRef<string | null>(null);
  useLayoutEffect(() => {
    if (!job || offered.current === job || finished || !lineRef.current) return;
    offered.current = job;
    if (arrived) offerShared(`handoff:${job}`, lineRef.current);
  }, [job, finished]);

  const go = () => {
    if (!job) return;
    if (finished && state !== 'stopped') {
      // 5d: the line points down to Kel's result, which carries the done card.
      const card = document.querySelector<HTMLElement>(`[data-done-card="${job}"]`);
      if (card) {
        card.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return;
      }
    }
    openWorkCard(job);
  };

  const lead = (
    <SwapIn
      className={`kel-wl__lead${state === 'done' || state === 'failed' || state === 'stopped' ? ' kel-wl__lead--check' : ''}`}
      swapKey={state === 'in_review' || state === 'needs_you' || state === 'working' || state === 'starting' ? `dot:${state}` : state}
      draw={state === 'done'}
      settle={settling}
    >
      {state === 'done' ? (
        <img src={iconCheck} alt='' />
      ) : state === 'failed' ? (
        <img src={iconWarning} alt='' />
      ) : state === 'stopped' ? (
        <img src={iconStopMuted} alt='' />
      ) : (
        <StatusDot tone={state === 'in_review' ? 'review' : state === 'needs_you' ? 'needs' : 'working'} />
      )}
    </SwapIn>
  );

  return (
    <button
      ref={lineRef}
      type='button'
      className={`kel-wl kel-wl--${state}`}
      onClick={go}
      disabled={!job}
      aria-label={`${view.title ?? 'Your request'}: ${words}. ${finished ? 'The result is below.' : 'Open it at the top of the chat.'}`}
      data-testid='kel-work-line'
      data-state={state}
    >
      {lead}
      <span className='kel-wl__handed'>Handed to the team</span>
      <span className='kel-wl__dot' aria-hidden='true'>
        ·
      </span>
      <span className='kel-wl__title'>{view.title ?? 'Your request'}</span>
      <RollText className='kel-wl__state' value={words} settle={settling} testId='kel-work-line-state' />
      <RollText className='kel-wl__pointer' value={pointer} settle={settling} />
      <img className={`kel-wl__chev${finished ? '' : ' kel-wl__chev--up'}`} src={iconChevronDown} alt='' />
    </button>
  );
};

export default KelWorkLine;
