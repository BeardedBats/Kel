/**
 * Kel conversational hand-off card (D-53).
 *
 * When a message is real work, Kel acknowledges it in the chat, ends the turn so the composer stays
 * usable, and this card stands in the conversation for the background work. It reads the engine's
 * live hand-off view (`/api/handoff`) every few seconds until the work settles; the checked result
 * itself arrives as Kel's next message. The card only ever says what the engine's records support:
 * "Done and checked" is reserved for a VERIFIED result.
 */
import kelMark from '@renderer/assets/figma/kel-mark.png';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { resolveEngineConversation } from './KelApprovalCard';
import { kelControl, kelHandoff, kelRetry, kelUndoChange, type KelHandoff, type KelHandoffPhase } from './kelApi';
import { applicationLine, isApplied } from './changeApplication';
import { WORK_WORDS, workWords } from './workLanguage';
import { announceHandoffLive } from './useKelLiveWork';
import { KelWorkLine } from './workCards/KelWorkLine';
import { answerApply } from './workCards/officeApi';
import { refreshWorkCards } from './workCards/workCardEvents';
import './KelWorkCard.css';

export const KEL_WORK_CARD_POLL_MS = 3000;
const TERMINAL: KelHandoffPhase[] = ['done', 'needs_look', 'stopped', 'failed_to_start'];

export const isTerminalPhase = (phase: KelHandoffPhase | undefined): boolean =>
  phase !== undefined && TERMINAL.includes(phase);

/** The card's headline for one phase — plain words, never a claim the records do not support.
 *  Settled phases use the shared state words (workLanguage.ts), so the card, Work, Activity and
 *  Home all describe one job the same way. */
/** CP-3: the work finished and its result was checked, but the checks failed — not "not fully checked". */
export const FAILED_CHECKS_HEADLINE = "Finished, but didn't pass its checks";

export const workHeadline = (view: Pick<KelHandoff, 'phase' | 'accepted' | 'total' | 'verdict'>): string => {
  if ((view.phase === 'needs_look' || view.phase === 'done') && view.verdict === 'FAILED') return FAILED_CHECKS_HEADLINE;
  switch (view.phase) {
    case 'starting':
      return 'Getting started…';
    case 'running':
      return view.total > 0 ? `Working on it · ${view.accepted} of ${view.total} parts checked` : 'Working on it';
    case 'needs_you':
      return WORK_WORDS.AWAITING_USER.label;
    case 'waiting':
      return 'Waiting to continue';
    case 'done':
      return workWords({ state: 'CLOSED', verdict: view.verdict }).label;
    case 'needs_look':
      return WORK_WORDS.UNCHECKED.label;
    case 'stopped':
      return WORK_WORDS.CANCELLED.label;
    case 'failed_to_start':
      return 'Couldn’t get started';
    default:
      return 'Working on it';
  }
};

const tone = (phase: KelHandoffPhase | undefined): 'active' | 'attention' | 'success' | 'quiet' => {
  if (phase === 'done') return 'success';
  if (phase === 'needs_you' || phase === 'waiting' || phase === 'needs_look' || phase === 'failed_to_start')
    return 'attention';
  if (phase === 'stopped') return 'quiet';
  return 'active';
};

type Props = {
  submissionId: string;
  /** The conversation id the row carries (the donor id); the engine id is resolved from it. */
  conversationId: string;
  pollMs?: number;
};

export const KelWorkCard: React.FC<Props> = ({ submissionId, conversationId, pollMs = KEL_WORK_CARD_POLL_MS }) => {
  const navigate = useNavigate();
  const [engineCid, setEngineCid] = useState<string | null>(null);
  const [view, setView] = useState<KelHandoff | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [generation, setGeneration] = useState(0);
  const inFlight = useRef(false);

  useEffect(() => {
    let alive = true;
    void resolveEngineConversation(conversationId).then((cid) => {
      if (alive) setEngineCid(cid);
    });
    return () => {
      alive = false;
    };
  }, [conversationId]);

  const refresh = useCallback(async (): Promise<KelHandoff | null> => {
    if (!engineCid || !submissionId) return null;
    try {
      const next = await kelHandoff(engineCid, submissionId);
      setView(next);
      // The sidebar row shows "working" while this hand-off runs (CH-11) without polling on its own.
      announceHandoffLive(engineCid, submissionId, !isTerminalPhase(next.phase));
      setUnavailable(false);
      return next;
    } catch {
      setUnavailable(true);
      return null;
    }
  }, [engineCid, submissionId]);

  // Poll until the work settles; a retry (generation) starts a fresh round.
  useEffect(() => {
    if (!engineCid) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const tick = async () => {
      const next = await refresh();
      if (stopped || (next && isTerminalPhase(next.phase))) return;
      timer = setTimeout(() => void tick(), pollMs);
    };
    void tick();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [engineCid, refresh, pollMs, generation]);

  const guarded = async (action: () => Promise<unknown>) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setNotice('');
    try {
      await action();
    } catch (error) {
      const detail = String((error as Error)?.message || '').trim();
      setNotice(detail || 'Kel could not reach its engine just now. Try again in a moment.');
    } finally {
      setBusy(false);
      inFlight.current = false;
    }
  };

  const stop = () =>
    guarded(async () => {
      if (!view?.job_id) return;
      await kelControl(view.job_id, 'cancel');
      setConfirming(false);
      await refresh();
    });

  // D-65: Full access applied the verified change on its own; Undo puts the saved files back.
  const undo = () =>
    guarded(async () => {
      if (!view?.job_id) return;
      await kelUndoChange(view.job_id);
      await refresh();
    });

  // D-70: a checked change that waits for you (Ask first, or held in Full access): Apply or Leave it,
  // on the same route as the top card's answer, with you as the actor.
  const answer = (choice: 'apply_anyway' | 'leave') =>
    guarded(async () => {
      if (!view?.job_id) return;
      await answerApply(view.job_id, choice);
      await refresh();
    });

  const retry = () =>
    guarded(async () => {
      await kelRetry(submissionId);
      setView((current) => (current ? { ...current, phase: 'starting', can_retry: false, why: null } : current));
      setGeneration((value) => value + 1);
    });

  // D-78 / §10.2: the moment work is handed off (a job id appears for running work), ask the top row
  // to read now — the new card must be there for the hand-off, not on the next 30 s idle poll.
  const announced = useRef<string | null>(null);
  useEffect(() => {
    const job = view?.job_id;
    if (!job || announced.current === job || isTerminalPhase(view?.phase)) return;
    announced.current = job;
    refreshWorkCards();
  }, [view?.job_id, view?.phase]);

  const phase = view?.phase ?? 'starting';
  // D-70 item 2: staffed work has its top card; in the thread it is one line pointing at it. Work
  // from before the cards (no `staffed`) and a hand-off that could not start keep this card.
  const staffedView = view as (KelHandoff & { staffed?: boolean; office_state?: string | null }) | null;
  if (staffedView && phase !== 'failed_to_start' && (staffedView.staffed || (!staffedView.job_id && phase === 'starting'))) {
    return <KelWorkLine view={staffedView} />;
  }
  const running = phase === 'starting' || phase === 'running';
  const waitingChange = phase === 'needs_you' && Boolean(view?.job_id && view.application?.waiting_reason);
  const headline = view ? workHeadline(view) : unavailable ? 'Checking on this work…' : 'Getting started…';
  const detail =
    phase === 'failed_to_start'
      ? view?.error || view?.why
      : phase === 'needs_you' || phase === 'waiting' || phase === 'needs_look'
        ? view?.why
        : null;

  return (
    <div
      className={`kel-work-card kel-work-card--${tone(view?.phase)}`}
      data-testid='kel-work-card'
      data-phase={phase}
    >
      <div className='kel-work-card__heading'>
        <span className={`kel-work-card__mark${running ? ' kel-work-card__mark--active' : ''}`} aria-hidden='true'>
          <img src={kelMark} alt='' width={18} height={18} />
        </span>
        <div className='kel-work-card__titles'>
          <strong className='kel-work-card__headline' role='status' aria-live='polite' data-testid='kel-work-headline'>
            {phase === 'done' && view?.verdict === 'VERIFIED' ? (
              <span className='kel-work-card__check' aria-hidden='true'>
                ✓{' '}
              </span>
            ) : null}
            {headline}
          </strong>
          {view?.title ? (
            <span className='kel-work-card__title' data-testid='kel-work-title'>
              {view.title}
            </span>
          ) : null}
        </div>
      </div>
      {detail ? (
        <div className='kel-work-card__body' data-testid='kel-work-why'>
          {detail}
        </div>
      ) : null}
      {phase === 'done' && applicationLine(view?.application) ? (
        <div className='kel-work-card__body' data-testid='kel-work-application'>
          {applicationLine(view?.application)}
        </div>
      ) : null}
      {confirming ? (
        <div className='kel-work-card__confirm' data-testid='kel-work-confirm'>
          <span>Stop this work? Anything already checked is kept.</span>
          <div className='kel-work-card__actions'>
            <button type='button' disabled={busy} onClick={() => setConfirming(false)} data-testid='kel-work-keep'>
              Keep going
            </button>
            <button
              type='button'
              className='kel-work-card__danger'
              disabled={busy}
              onClick={() => void stop()}
              data-testid='kel-work-stop-confirm'
            >
              Stop it
            </button>
          </div>
        </div>
      ) : (
        <div className='kel-work-card__actions'>
          <button
            type='button'
            className='kel-work-card__link'
            onClick={() => navigate(view?.job_id ? `/activity?job=${encodeURIComponent(view.job_id)}` : '/activity')}
            data-testid='kel-work-activity'
          >
            View in Activity
          </button>
          {phase === 'done' && view?.job_id && isApplied(view.application) ? (
            <button type='button' disabled={busy} onClick={() => void undo()} data-testid='kel-work-undo'>
              Undo
            </button>
          ) : null}
          {waitingChange ? (
            <>
              <button
                type='button'
                className='kel-work-card__primary'
                disabled={busy}
                onClick={() => void answer('apply_anyway')}
                data-testid='kel-work-apply'
              >
                {view?.application?.ask_first ? 'Apply' : 'Apply anyway'}
              </button>
              <button type='button' disabled={busy} onClick={() => void answer('leave')} data-testid='kel-work-leave'>
                Leave it
              </button>
            </>
          ) : null}
          {view?.can_retry ? (
            <button
              type='button'
              className='kel-work-card__primary'
              disabled={busy}
              onClick={() => void retry()}
              data-testid='kel-work-retry'
            >
              Retry
            </button>
          ) : null}
          {view?.can_stop && view.job_id ? (
            <button type='button' disabled={busy} onClick={() => setConfirming(true)} data-testid='kel-work-stop'>
              Stop
            </button>
          ) : null}
        </div>
      )}
      {notice ? (
        <div className='kel-work-card__notice' data-testid='kel-work-notice'>
          {notice}
        </div>
      ) : null}
    </div>
  );
};

export default KelWorkCard;
