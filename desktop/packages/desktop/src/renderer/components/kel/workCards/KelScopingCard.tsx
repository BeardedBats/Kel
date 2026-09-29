/**
 * D-70 item 4 — scoping before big work (Figma 5e, 5f). Under Kel's "Happy to. It's a bigger job…"
 * line: "Before I start · N quick questions", each question with quick picks and "Something else…"
 * (a typed answer), the "I'll build: …" line, Start, "Just start with your best guess" and
 * "Nothing starts until you choose." (D-55). Once started the card collapses to one line with the
 * answers and when it started; the work itself then appears as a normal hand-off below.
 * D-74.3: "Not now" cancels the questions — nothing starts, and the card settles into one line.
 */
import kelMark from '@renderer/assets/figma/kel-mark.png';
import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { LOOKS, morphInto, snapshotGhost, type Snapshot } from '@renderer/motion';
import { emitter } from '@/renderer/utils/emitter';
import { resolveEngineConversation } from '../KelApprovalCard';
import { KelAnswerBox } from './KelAnswerBox';
import { KelChoiceChips, OTHER_CHIP } from './KelChoiceChips';
import {
  scopingBestGuess,
  scopingDismiss,
  scopingStart,
  scopingView,
  type ScopingAnswer,
  type ScopingRecorded,
  type ScopingView,
} from './officeApi';
import { REFRESH_WORK_CARDS_EVENT, refreshWorkCards } from './workCardEvents';
import { iconChat, iconCheck, iconSparkle } from './workCardIcons';
import { clockTime } from './workCardModel';
import './KelWorkCardsRow5.css';

/**
 * D-73 item 10: Design Vetting (the retired Work panel's tab) is reached from here — for work that
 * needs a real spec first. It puts Kel's vetting start in the composer; Nick sends it (vetting runs in
 * the chat: numbered questions, "process answers", "finish spec").
 */
export const vettingPrompt = (title: string | null | undefined): string =>
  `start design vetting: ${String(title ?? '').trim() || 'this work'}`;

const focusComposer = (attempts = 20) => {
  const textarea = document.querySelector<HTMLTextAreaElement>('.sendbox-panel textarea');
  if (textarea) {
    textarea.focus();
    textarea.setSelectionRange?.(textarea.value.length, textarea.value.length);
  } else if (attempts > 0) window.setTimeout(() => focusComposer(attempts - 1), 100);
};

/** Figma 5e: "Before I start · 3 quick questions". */
export const scopingHeading = (count: number): string => `Before I start · ${count} quick question${count === 1 ? '' : 's'}`;

type Picks = Record<string, { option?: string; other?: boolean; text?: string }>;

/** While the card is open it reads the engine again this often, so answers typed in the chat show. */
export const SCOPING_POLL_MS = 3000;

/**
 * The picks the card shows: what Nick picked here, else what Kel understood from his message in the
 * chat (the engine's `recorded` answers, via the same ingestion as the card's own).
 */
export const picksWithRecorded = (picks: Picks, recorded: Record<string, ScopingRecorded> | null | undefined): Picks => {
  const out: Picks = {};
  for (const [id, answer] of Object.entries(recorded ?? {})) {
    if (answer?.option) out[id] = { option: answer.option };
    else if (answer?.text) out[id] = { other: true, text: answer.text };
  }
  return { ...out, ...picks };
};

/** The answers Start sends: a picked option, or what was typed under "Something else…". */
export const answersFor = (picks: Picks): Record<string, ScopingAnswer> => {
  const out: Record<string, ScopingAnswer> = {};
  for (const [id, pick] of Object.entries(picks)) {
    if (pick.other) {
      const text = (pick.text ?? '').trim();
      if (text) out[id] = { text };
    } else if (pick.option) out[id] = { option: pick.option };
  }
  return out;
};

type Props = {
  scopingId: string;
  /** The app conversation this card is shown in (its engine conversation scopes every action). */
  conversationId?: string;
};

export const KelScopingCard: React.FC<Props> = ({ scopingId, conversationId }) => {
  const [view, setView] = useState<ScopingView | null>(null);
  const [engineCid, setEngineCid] = useState<string | null>(null);
  const [picks, setPicks] = useState<Picks>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let alive = true;
    if (!conversationId) {
      setEngineCid('');
      return;
    }
    void resolveEngineConversation(conversationId).then((cid) => {
      if (alive) setEngineCid(cid);
    });
    return () => {
      alive = false;
    };
  }, [conversationId]);

  const read = useCallback(async () => {
    try {
      const next = await scopingView(scopingId, engineCid || null);
      // Started work never reopens: a read that left before Start answered is older than Start.
      setView((current) => (current && current.state !== 'open' && next?.state === 'open' ? current : next));
    } catch {
      setView(null);
    }
  }, [scopingId, engineCid]);

  useEffect(() => {
    if (engineCid === null) return;
    void read();
  }, [engineCid, read]);

  // D-70 item 4: answers typed in the chat (and "start" / "go") reach the engine, not this card —
  // so while it is open it reads again, and at once when the work cards are asked to refresh.
  const open = view?.state === 'open';
  useEffect(() => {
    if (engineCid === null || !open) return;
    const timer = setInterval(() => void read(), SCOPING_POLL_MS);
    const now = (): void => {
      void read();
    };
    window.addEventListener(REFRESH_WORK_CARDS_EVENT, now);
    return () => {
      clearInterval(timer);
      window.removeEventListener(REFRESH_WORK_CARDS_EVENT, now);
    };
  }, [engineCid, open, read]);

  // D-78 §10.7: Start (or Not now) collapses the card into its one-line summary — the card's surface
  // shrinks into the line (height on `morph`, width on `snappy`, radius 12 → 8) and the summary, the
  // resting end of the questions, settles in with its check drawing on. Copied before React swaps it.
  const hostRef = useRef<HTMLElement | null>(null);
  const seenState = useRef(view?.state ?? null);
  const leaving = useRef<Snapshot | null>(null);
  if (seenState.current === 'open' && view && view.state !== 'open' && !leaving.current && hostRef.current) {
    leaving.current = snapshotGhost(hostRef.current);
  }
  useLayoutEffect(() => {
    const was = seenState.current;
    seenState.current = view?.state ?? null;
    const snap = leaving.current;
    leaving.current = null;
    const line = hostRef.current;
    if (was !== 'open' || !view || view.state === 'open' || !snap || !line) return;
    void morphInto({ from: snap, to: line, fromLook: LOOKS.scoping, toLook: LOOKS.collapsed, settle: true, draw: view.state === 'dismissed' ? undefined : ':scope > img', presets: { h: 'morph', w: 'snappy', y: 'morph' } });
  }, [view?.state]);
  const setHost = (el: HTMLElement | null) => {
    hostRef.current = el;
  };

  if (!view) return null;

  if (view.state === 'dismissed') {
    return (
      <div ref={setHost} className='kel-sc-collapsed kel-sc-collapsed--dismissed' data-testid='kel-scoping-dismissed' data-scoping-card={view.id}>
        <img src={iconChat} alt='' />
        <span className='kel-sc-collapsed__word'>Not now</span>
        <span className='kel-sc-collapsed__answers'>Nothing started. Ask again whenever you want it.</span>
      </div>
    );
  }

  if (view.state !== 'open') {
    const started = clockTime(view.started_at);
    return (
      <div ref={setHost} className='kel-sc-collapsed' data-testid='kel-scoping-collapsed' data-scoping-card={view.id}>
        <img src={iconCheck} alt='' />
        <span className='kel-sc-collapsed__word'>{view.state === 'best_guess' ? 'Scoped · best guess' : 'Scoped'}</span>
        <span className='kel-sc-collapsed__answers'>{view.answer_line ?? ''}</span>
        <span className='kel-wc-push' />
        {started ? <span className='kel-sc-collapsed__at'>{`Started ${started}`}</span> : null}
      </div>
    );
  }

  const run = async (action: () => Promise<ScopingView>) => {
    if (busy) return;
    setBusy(true);
    setNotice('');
    try {
      const next = await action();
      setView(next);
      refreshWorkCards();
    } catch (error) {
      setNotice(String((error as Error)?.message || '').trim() || 'Kel could not start this just now. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const shown = picksWithRecorded(picks, view.recorded);
  const typedCount = Object.keys(view.recorded ?? {}).length;

  const pick = (question: string, id: string) =>
    setPicks((current) => ({
      ...current,
      [question]: id === OTHER_CHIP ? { other: true, text: shown[question]?.text ?? current[question]?.text ?? '' } : { option: id },
    }));

  return (
    <section ref={setHost} className='kel-sc' aria-label='Kel’s questions before it starts' data-testid='kel-scoping-card' data-scoping-card={view.id}>
      <div className='kel-sc__head'>
        <img className='kel-sc__mark' src={kelMark} alt='' />
        <h3>{scopingHeading(view.questions.length)}</h3>
        <span className='kel-wc-push' />
        <span className='kel-sc__state'>
          <img src={iconChat} alt='' />
          Scoping
        </span>
      </div>
      {typedCount ? (
        <p className='kel-sc__typed' data-testid='kel-scoping-typed'>
          {`Filled in from your message (${typedCount} of ${view.questions.length}). Change any, then Start — or say “start” in the chat.`}
        </p>
      ) : null}
      {view.questions.map((question) => {
        const current = shown[question.id];
        const selected = current?.other ? OTHER_CHIP : current?.option ?? null;
        return (
          <div className='kel-sc__question' key={question.id} data-testid='kel-scoping-question'>
            <p className='kel-sc__prompt'>{question.question}</p>
            <KelChoiceChips
              label={question.question}
              options={question.options.map((option) => ({ id: option.code, label: option.label }))}
              selected={selected}
              other
              disabled={busy}
              onPick={(id) => pick(question.id, id)}
            />
            {current?.other ? (
              <KelAnswerBox
                label={`Your answer to: ${question.question}`}
                placeholder='Type your answer…'
                showSend={false}
                autoFocus
                disabled={busy}
                value={current.text ?? ''}
                onChange={(text) => setPicks((all) => ({ ...all, [question.id]: { other: true, text } }))}
                onSend={() => undefined}
                maxLength={200}
              />
            ) : null}
          </div>
        );
      })}
      <div className='kel-sc__divider' />
      <div className='kel-sc__summary'>
        <img src={iconSparkle} alt='' />
        <p data-testid='kel-scoping-summary'>{view.summary}</p>
      </div>
      <div className='kel-sc__actions'>
        <button
          type='button'
          className='kel-wd-button kel-wd-button--primary'
          disabled={busy}
          onClick={() => void run(() => scopingStart(view.id, answersFor(shown), engineCid || null))}
          data-testid='kel-scoping-start'
        >
          Start
        </button>
        <button
          type='button'
          className='kel-wd-button'
          disabled={busy}
          onClick={() => void run(() => scopingBestGuess(view.id, engineCid || null))}
          data-testid='kel-scoping-best-guess'
        >
          Just start with your best guess
        </button>
        <button
          type='button'
          className='kel-wd-button kel-sc__vetting'
          disabled={busy}
          title='Kel asks everything a full spec needs, in batches, and keeps each decision with its reason.'
          onClick={() => {
            emitter.emit('sendbox.fill', vettingPrompt(view.title));
            focusComposer();
          }}
          data-testid='kel-scoping-vetting'
        >
          Vet the design first
        </button>
        <button
          type='button'
          className='kel-wd-button'
          disabled={busy}
          title='Cancel these questions. Nothing starts.'
          onClick={() => void run(() => scopingDismiss(view.id, engineCid || null))}
          data-testid='kel-scoping-not-now'
        >
          Not now
        </button>
        <span className='kel-wc-push' />
        <span className='kel-sc__nothing'>Nothing starts until you choose.</span>
      </div>
      {notice ? (
        <p className='kel-sc__notice' role='alert'>
          {notice}
        </p>
      ) : null}
    </section>
  );
};

export default KelScopingCard;
