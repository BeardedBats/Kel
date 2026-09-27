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
import { kelControl, kelHandoff, kelRetry, type KelHandoff, type KelHandoffPhase } from './kelApi';
import './KelWorkCard.css';

export const KEL_WORK_CARD_POLL_MS = 3000;
const TERMINAL: KelHandoffPhase[] = ['done', 'needs_look', 'stopped', 'failed_to_start'];

export const isTerminalPhase = (phase: KelHandoffPhase | undefined): boolean =>
  phase !== undefined && TERMINAL.includes(phase);

/** The card's headline for one phase — plain words, never a claim the records do not support. */
export const workHeadline = (view: Pick<KelHandoff, 'phase' | 'accepted' | 'total' | 'verdict'>): string => {
  switch (view.phase) {
    case 'starting':
      return 'Getting started…';
    case 'running':
      return view.total > 0 ? `Working on it · ${view.accepted} of ${view.total} parts checked` : 'Working on it';
    case 'needs_you':
      return 'Waiting for your OK';
    case 'waiting':
      return 'Waiting to continue';
    case 'done':
      return view.verdict === 'VERIFIED' ? 'Done and checked' : 'Finished, but not fully verified';
    case 'needs_look':
      return 'Finished, but not fully verified';
    case 'stopped':
      return 'Stopped';
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

  const retry = () =>
    guarded(async () => {
      await kelRetry(submissionId);
      setView((current) => (current ? { ...current, phase: 'starting', can_retry: false, why: null } : current));
      setGeneration((value) => value + 1);
    });

  const phase = view?.phase ?? 'starting';
  const running = phase === 'starting' || phase === 'running';
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
            onClick={() => navigate('/activity')}
            data-testid='kel-work-activity'
          >
            View in Activity
          </button>
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
