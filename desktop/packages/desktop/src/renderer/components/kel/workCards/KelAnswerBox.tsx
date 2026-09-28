/**
 * D-70 — the answer input (Figma 5a "Answer": a 36px box and a primary Send). Reusable for any
 * "type your answer to Kel" spot: Enter sends, Shift+Enter is not needed (one line), an empty
 * answer cannot be sent, and the box stays disabled while its answer is on its way.
 */
import React, { useState } from 'react';

type Props = {
  onSend: (text: string) => void | Promise<unknown>;
  placeholder?: string;
  sendLabel?: string;
  disabled?: boolean;
  /** Names the input for assistive tech (the question it answers). */
  label: string;
  /** Show the Send button (a scoping answer is sent with Start instead). */
  showSend?: boolean;
  /** Controlled value (optional); the box keeps its own text otherwise. */
  value?: string;
  onChange?: (text: string) => void;
  autoFocus?: boolean;
  maxLength?: number;
  testId?: string;
};

export const KelAnswerBox: React.FC<Props> = ({
  onSend,
  placeholder = 'Or type your answer…',
  sendLabel = 'Send',
  disabled = false,
  label,
  showSend = true,
  value,
  onChange,
  autoFocus = false,
  maxLength = 2000,
  testId,
}) => {
  const [own, setOwn] = useState('');
  const text = value ?? own;
  const setText = (next: string) => {
    if (onChange) onChange(next);
    if (value === undefined) setOwn(next);
  };
  const send = () => {
    const answer = text.trim();
    if (!answer || disabled) return;
    void Promise.resolve(onSend(answer)).then(() => {
      if (value === undefined) setOwn('');
    });
  };
  return (
    <div className='kel-answer' data-testid={testId}>
      <input
        className='kel-answer__box'
        type='text'
        value={text}
        placeholder={placeholder}
        aria-label={label}
        disabled={disabled}
        maxLength={maxLength}
        autoFocus={autoFocus}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.nativeEvent.isComposing) {
            event.preventDefault();
            if (showSend) send();
          }
        }}
        data-testid='kel-answer-input'
      />
      {showSend ? (
        <button
          type='button'
          className='kel-wd-button kel-wd-button--primary'
          disabled={disabled || !text.trim()}
          onClick={send}
          data-testid='kel-answer-send'
        >
          {sendLabel}
        </button>
      ) : null}
    </div>
  );
};

export default KelAnswerBox;
