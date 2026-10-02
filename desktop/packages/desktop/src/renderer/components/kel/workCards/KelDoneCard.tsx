/**
 * D-70 item 2 — the compact done card on Kel's result message (Figma 5d). Title, the verified
 * state ("Done and checked" only for work whose checks passed, D-53), and
 * where a coding change was applied (D-65 truth from changeApplication.ts)
 * with "Open" for its folder (D-79: no Undo — Nick asks Kel; Apply / Leave it while a checked change
 * waits for Nick), and
 * Details opens the full work panel with its result and checks. Failed, stopped and needs-you results use the same card
 * with their own words. Work without a top card (from before the cards) renders `fallback` instead
 * — today's message details.
 */
import { ipcBridge } from '@/common';
import type { KelMessageMeta } from '@/common/chat/kelMessageMeta';
import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  RollText,
  SwapIn,
  cardStateTransition,
  drawOn,
  frameWrite,
  isArrivalTime,
  isReducedMotion,
  prepareEnter,
  settleIn,
  spring,
  useEntrance,
  MOTION,
} from '@renderer/motion';
import { applicationLine, isApplied, placeWords } from '../changeApplication';
import { type KelChangeApplication } from '../kelApi';
import { sendNeedsAnswer } from './needsAnswer';
import { officeItem, type OfficeItemDetail } from './officeApi';
import { REFRESH_WORK_CARDS_EVENT, openWorkCard, refreshWorkCards } from './workCardEvents';
import { StateIcon, iconFolder, iconFolder13 } from './workCardIcons';
import { COMPLETE_LABEL, clockTime, completedAt, isUncertain, isUndone, panelStateLabel, undoneLine } from './workCardModel';
import './KelWorkCardsRow5.css';

const PASS = new Set(['passed', 'pass', 'verified', 'ok', 'success', 'accepted']);

/** "4 of 4 checks passed" from the checks the engine recorded with the result (never invented). */
export const checksLine = (meta: Pick<KelMessageMeta, 'checks'> | null | undefined): string | null => {
  const checks = meta?.checks ?? [];
  if (!checks.length) return null;
  const passedCount = checks.filter((check) => PASS.has(String(check?.verdict ?? '').toLowerCase())).length;
  return `${passedCount} of ${checks.length} check${checks.length === 1 ? '' : 's'} passed`;
};

/**
 * One sentence of the result: the published text without Kel's lead-in ("Here's … — it passed its
 * checks."), first sentence only. Null when there is nothing beyond the lead-in.
 */
export const resultSentence = (text: string | null | undefined): string | null => {
  let body = String(text ?? '').trim();
  if (!body) return null;
  body = body.replace(/^Here[’']s[^\n]*?—\s*it passed its checks\.\s*/i, '').replace(/`([^`\n]+)`/g, '$1').trim();
  const first = body.split(/\n\s*\n/)[0]?.replace(/\s+/g, ' ').trim() ?? '';
  if (!first) return null;
  const sentence = first.match(/^.+?[.!?](?=\s|$)/)?.[0] ?? first;
  return sentence.length > 220 ? `${sentence.slice(0, 219).trimEnd()}…` : sentence;
};

/**
 * "Applied to Calc demo (folder R6Proj) at 10:31 AM · you can undo it", or the D-65 words for other
 * states. The project's name and folder appear once; the full path stays behind "Open folder".
 */
export const appliedWords = (application: KelChangeApplication | null | undefined, at: number | null | undefined): string | null => {
  if (!application) return null;
  if (isApplied(application) && application.state === 'APPLIED') {
    const when = clockTime(at);
    return `Applied to ${placeWords(application)}${when ? ` at ${when}` : ''} · you can undo it`;
  }
  return applicationLine(application);
};

/**
 * The result sentence without the D-65 "Applied to <place>:" lead when the applied line already says
 * where (old results named the full path there): "Changed calc.py; added test_calc.py (2 files)."
 */
export const withoutPlace = (sentence: string | null): string | null => {
  if (!sentence) return sentence;
  const match = sentence.match(/^(?:Your new project is ready\.\s*)?Applied to .+?:\s+(?=(?:changed|added|removed|no files)\b)/i);
  if (!match) return sentence;
  const rest = sentence.slice(match[0].length).trim();
  return rest ? rest.charAt(0).toUpperCase() + rest.slice(1) : null;
};

const defaultOpenFolder = async (path: string) => {
  try {
    await ipcBridge.shell.openFile.invoke(path);
  } catch {
    await ipcBridge.shell.showItemInFolder.invoke(path);
  }
};

type Props = {
  job: string;
  meta?: KelMessageMeta | null;
  /** Shown instead when this work has no top card (older work). */
  fallback?: React.ReactNode;
  openFolder?: (path: string) => Promise<unknown>;
};

/** A failure arrives like any other content (§10.9): it enters; it never shakes. */
const DoneNotice: React.FC<{ text: string }> = ({ text }) => {
  const ref = useRef<HTMLParagraphElement>(null);
  useEntrance(ref, true, { y: 4 });
  return (
    <p ref={ref} className='kel-dc__notice' role='alert'>
      {text}
    </p>
  );
};

export const KelDoneCard: React.FC<Props> = ({ job, fallback = null, openFolder = defaultOpenFolder }) => {
  const [detail, setDetail] = useState<OfficeItemDetail | null>(null);
  const [noCard, setNoCard] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const read = useCallback(async () => {
    try {
      const next = await officeItem(job);
      setDetail(next);
      setNoCard(false);
    } catch {
      setNoCard(true);
    }
  }, [job]);

  useEffect(() => {
    void read();
  }, [read]);

  // An answer or Undo on the top card updates this card too (one live view).
  useEffect(() => {
    const again = (): void => void read();
    window.addEventListener(REFRESH_WORK_CARDS_EVENT, again);
    return () => window.removeEventListener(REFRESH_WORK_CARDS_EVENT, again);
  }, [read]);

  // D-78 §10.8: the done card unfolds from its top edge when it arrives while Nick watches.
  const cardRef = useRef<HTMLElement>(null);
  const actionsRef = useRef<HTMLDivElement>(null);
  const arrivedAt = useRef<boolean | null>(null);
  const shownOnce = useRef(false);
  if (detail && arrivedAt.current === null) arrivedAt.current = isArrivalTime();
  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!card || shownOnce.current) return;
    shownOnce.current = true;
    if (!arrivedAt.current) return;
    const parts = Array.from(card.querySelectorAll<HTMLElement>(':scope > .kel-dc__head, :scope > .kel-dc__result, :scope > .kel-dc__applied, :scope > .kel-dc__actions'));
    // A resting result: its rows settle in, in reading order, while the card unfolds.
    prepareEnter(parts, { y: 0, blur: MOTION.settleBlurPx });
    if (!isReducedMotion()) {
      card.style.clipPath = 'inset(0 0 100% 0 round 10px)';
      void spring(0, 1, 'morph', (v) => {
        frameWrite(card, () => {
          card.style.clipPath = v >= 0.999 ? '' : `inset(0 0 ${((1 - v) * 100).toFixed(2)}% 0 round 10px)`;
        });
      }, { eps: 0.001 }).finished.then(() => {
        card.style.clipPath = '';
      });
    }
    void settleIn(parts, { stagger: 40, delay: 100 });
    const check = card.querySelector<HTMLElement>('.kel-dc__lead img');
    if (check && detail?.state === 'done') void drawOn(check, { delay: 160 });
  });

  if (noCard) return <>{fallback}</>;
  if (!detail) return null;

  const application = detail.application ?? null;
  const applied = (detail.kind ?? '') === 'code' && isApplied(application);
  // D-79: "Open" (the project folder) stays; there is no Undo here — Nick asks Kel.
  const folder = (detail.kind ?? '') === 'code' ? application?.root ?? null : null;
  const state = detail.state;
  const label = state === 'failed' && !isUncertain(detail) ? 'Didn’t pass its checks' : panelStateLabel(detail);
  const completeTip = label === COMPLETE_LABEL ? completedAt(detail.finished_at ?? detail.updated_at) ?? undefined : undefined;
  // LIVE-12: an undone change says when it was undone and what came back (the engine's record).
  const undone = (detail.kind ?? '') === 'code' && isUndone({ undone: detail.undone, application });
  const applyWords =
    (detail.kind ?? '') === 'code'
      ? undone
        ? undoneLine({ undone: detail.undone, application })
        : appliedWords(application, detail.finished_at)
      : null;
  const uncertain = state === 'failed' && isUncertain(detail);
  const settles = cardStateTransition(state) === 'settling';
  // D-70: a checked change that waits for Nick (Ask first, or held in Full access) is answered here
  // too, through the same route as its top card: Apply / Apply anyway, or Leave it.
  const applyQuestion = detail.state === 'needs_you' && detail.question?.kind === 'apply' ? detail.question : null;

  const guarded = async (action: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true);
    setNotice('');
    try {
      await action();
    } catch (error) {
      setNotice(String((error as Error)?.message || '').trim() || 'Kel could not reach its engine just now.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      ref={cardRef}
      className={`kel-dc kel-dc--${state}${uncertain ? ' is-uncertain' : ''}`}
      aria-label={`${detail.title}: ${label}`}
      data-testid='kel-done-card'
      data-done-card={job}
      data-state={state}
    >
      <div className='kel-dc__head'>
        <SwapIn className='kel-dc__lead' swapKey={`${state}${uncertain ? ':u' : ''}`} draw={state === 'done'} settle={settles}>
          <StateIcon state={state} size='detail' uncertain={uncertain} />
        </SwapIn>
        <span className='kel-dc__title'>{detail.title}</span>
        <span className='kel-dc__state-word' title={completeTip}>
          <RollText className='kel-dc__state' value={label} settle={settles} testId='kel-done-card-state' />
        </span>
        <span className='kel-wc-push' />
      </div>
      {applyWords ? (
        <div className='kel-dc__applied' data-testid='kel-done-card-applied' title={applied && folder ? folder : undefined}>
          <img src={iconFolder13} alt='' />
          {/* Nick: "Undone — the earlier files are back." is a resting state; it settles in slowly. */}
          <RollText value={applyWords} settle={undone} flipSiblings={false} />
        </div>
      ) : null}
      <div className='kel-dc__actions' ref={actionsRef}>
        {applyQuestion?.options?.map((option) => (
          <button
            key={option.id}
            type='button'
            className={`kel-wd-button${option.id === 'leave' ? '' : ' kel-wd-button--primary'}`}
            disabled={busy}
            onClick={() =>
              void guarded(async () => {
                await sendNeedsAnswer(applyQuestion, { option });
                refreshWorkCards();
                await read();
              })
            }
            data-testid={`kel-done-card-answer-${option.id}`}
          >
            {option.label}
          </button>
        ))}
        {folder ? (
          <button
            type='button'
            className='kel-wd-button'
            disabled={busy}
            onClick={() => void guarded(async () => openFolder(folder))}
            aria-label='Open the project folder'
            title='Open the project folder'
            data-testid='kel-done-card-folder'
          >
            <img src={iconFolder} alt='' />
            Open
          </button>
        ) : null}
        <span className='kel-wc-push' />
        <button type='button' className='kel-wd-button' onClick={() => openWorkCard(job)} data-testid='kel-done-card-details'>
          Details
        </button>
      </div>
      {notice ? <DoneNotice text={notice} /> : null}
    </section>
  );
};

export default KelDoneCard;
