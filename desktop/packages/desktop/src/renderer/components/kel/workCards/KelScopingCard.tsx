/**
 * D-70 item 4 — scoping before big work (Figma 5e, 5f). Under Kel's "Happy to. It's a bigger job…"
 * line: "Before I start · N quick questions", each question with quick picks and "Something else…"
 * (a typed answer), the "I'll build: …" line, Start, "Just start with your best guess" and
 * "Nothing starts until you choose." (D-55). Once started the card collapses to one line with the
 * answers and when it started; the work itself then appears as a normal hand-off below.
 */
import kelMark from '@renderer/assets/figma/kel-mark.png';
import React, { useCallback, useEffect, useState } from 'react';
import { resolveEngineConversation } from '../KelApprovalCard';
import { KelAnswerBox } from './KelAnswerBox';
import { KelChoiceChips, OTHER_CHIP } from './KelChoiceChips';
import { scopingBestGuess, scopingStart, scopingView, type ScopingAnswer, type ScopingView } from './officeApi';
import { refreshWorkCards } from './workCardEvents';
import { iconChat, iconCheck, iconSparkle } from './workCardIcons';
import { clockTime } from './workCardModel';
import './KelWorkCardsRow5.css';

const NUMBERS = ['no', 'one', 'two', 'three', 'four'];

export const scopingHeading = (count: number): string =>
  `Before I start · ${NUMBERS[count] ?? count} quick question${count === 1 ? '' : 's'}`;

type Picks = Record<string, { option?: string; other?: boolean; text?: string }>;

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
      setView(await scopingView(scopingId, engineCid || null));
    } catch {
      setView(null);
    }
  }, [scopingId, engineCid]);

  useEffect(() => {
    if (engineCid === null) return;
    void read();
  }, [engineCid, read]);

  if (!view) return null;

  if (view.state !== 'open') {
    const started = clockTime(view.started_at);
    return (
      <div className='kel-sc-collapsed' data-testid='kel-scoping-collapsed' data-scoping-card={view.id}>
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

  const pick = (question: string, id: string) =>
    setPicks((current) => ({
      ...current,
      [question]: id === OTHER_CHIP ? { other: true, text: current[question]?.text ?? '' } : { option: id },
    }));

  return (
    <section className='kel-sc' aria-label='Kel’s questions before it starts' data-testid='kel-scoping-card' data-scoping-card={view.id}>
      <div className='kel-sc__head'>
        <img className='kel-sc__mark' src={kelMark} alt='' />
        <h3>{scopingHeading(view.questions.length)}</h3>
        <span className='kel-wc-push' />
        <span className='kel-sc__state'>
          <img src={iconChat} alt='' />
          Scoping
        </span>
      </div>
      {view.questions.map((question) => {
        const current = picks[question.id];
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
          onClick={() => void run(() => scopingStart(view.id, answersFor(picks), engineCid || null))}
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
