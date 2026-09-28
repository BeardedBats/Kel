/**
 * D-70 item 1 — "Kel is asking you" at the top of a needs-you card's panel (Figma 5a), and the line
 * that replaces it once the answer is on its way (5b). The question, Kel's quick picks, an answer
 * box with Send, and the reminder that the answer goes to Kel, not to an agent. The card itself
 * takes its new state from the next read of the engine.
 */
import kelMark from '@renderer/assets/figma/kel-mark.png';
import React, { useState } from 'react';
import { KelAnswerBox } from './KelAnswerBox';
import { KelChoiceChips } from './KelChoiceChips';
import type { OfficeQuestion } from './officeApi';
import { answeredFollowUp, answeredWords, sendNeedsAnswer, type NeedsAnswer } from './needsAnswer';
import { iconCheck14 } from './workCardIcons';
import { clockTime } from './workCardModel';

export type AnsweredNote = { words: string; follow: string; at: number };

type Props = {
  question: OfficeQuestion;
  /** Called once the engine took the answer (the panel reads the work again). */
  onAnswered: (note: AnsweredNote) => void;
  /** Test seam: the route an answer takes. */
  send?: (question: OfficeQuestion, answer: NeedsAnswer) => Promise<void>;
};

export const KelAnsweredLine: React.FC<{ note: AnsweredNote }> = ({ note }) => (
  <div className='kel-na-answered' role='status' data-testid='kel-needs-answered'>
    <img className='kel-na-answered__check' src={iconCheck14} alt='' />
    <span className='kel-na-answered__words'>{`You answered: ${note.words}`}</span>
    <span className='kel-na-dot' aria-hidden='true'>
      ·
    </span>
    <img className='kel-na-answered__mark' src={kelMark} alt='' />
    <span className='kel-na-answered__follow'>{note.follow}</span>
    <span className='kel-wc-push' />
    <span className='kel-na-answered__at'>{clockTime(note.at) ?? ''}</span>
  </div>
);

export const KelNeedsAnswer: React.FC<Props> = ({ question, onAnswered, send = sendNeedsAnswer }) => {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const options = question.options ?? [];

  const answer = async (value: NeedsAnswer) => {
    if (busy) return;
    setBusy(true);
    setNotice('');
    try {
      await send(question, value);
      onAnswered({ words: answeredWords(value), follow: answeredFollowUp(question, value), at: Date.now() / 1000 });
    } catch (error) {
      setNotice(String((error as Error)?.message || '').trim() || 'Kel could not take that answer just now. Try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className='kel-na' aria-label='Kel is asking you' data-testid='kel-needs-question' data-wait={question.kind}>
      <div className='kel-na__head'>
        <img className='kel-na__mark' src={kelMark} alt='' />
        <strong>Kel is asking you</strong>
        <span className='kel-na__meta'>·  This work is paused until you answer</span>
        {question.wait ? <span className='kel-wc-sr'>{`, ${question.wait}`}</span> : null}
      </div>
      <p className='kel-na__question' data-testid='kel-needs-question-text'>
        {question.text}
      </p>
      {question.detail ? <p className='kel-na__detail'>{question.detail}</p> : null}
      {options.length ? (
        <KelChoiceChips
          label={question.text}
          options={options}
          disabled={busy}
          onPick={(id) => {
            const option = options.find((entry) => entry.id === id);
            if (option) void answer({ option });
          }}
          testId='kel-needs-chips'
        />
      ) : null}
      {question.answer_box !== false ? (
        <KelAnswerBox label={`Your answer to: ${question.text}`} disabled={busy} onSend={(text) => answer({ text })} />
      ) : null}
      {notice ? (
        <p className='kel-wd-notice' role='alert'>
          {notice}
        </p>
      ) : null}
      <p className='kel-na__goes'>
        <img src={kelMark} alt='' />
        Your answer goes to Kel, not to an agent. Kel will pass it on and continue.
      </p>
    </section>
  );
};

export default KelNeedsAnswer;
