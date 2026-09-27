/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

import { Attention } from '@icon-park/react';
import React from 'react';
import { useConversationContextSafe } from '@/renderer/hooks/context/ConversationContext';
import { iconColors } from '@/renderer/styles/colors';
import { emitter } from '@/renderer/utils/emitter';
import { useMessageList } from '../hooks';

/**
 * The engine reports a failed start as plain assistant text. Kel shows it as the Figma
 * "Chat — Agent error" card (273:13090) instead of a bare sentence.
 */
const FAILURE_PATTERNS: RegExp[] = [
  /^Kel could not plan this request:\s*([\s\S]+)$/,
  /^I wasn't able to get that started\s*[—-]\s*([\s\S]+?)\.?\s*You can retry it[\s\S]*$/,
];

/** Returns the failure reason when `text` is one of the engine's failure sentences, else null. */
export const parseEngineFailure = (text: string): string | null => {
  const trimmed = text.trim();
  for (const pattern of FAILURE_PATTERNS) {
    const match = trimmed.match(pattern);
    if (match) return match[1].trim();
  }
  return null;
};

/** Plain-language body for the raw engine reason; the raw text stays available under Details. */
const friendlyReason = (reason: string): string => {
  if (/timed? ?out|took too long/i.test(reason)) return 'The model took too long. Try again or pick another model.';
  if (/structured result|invalid json|parse/i.test(reason)) return 'The model sent back an answer Kel could not use. Try again or pick another model.';
  if (/auth|api key|sign.?in|credential/i.test(reason)) return 'The model needs to be set up before Kel can use it. Pick another model or finish its setup.';
  if (/quota|rate.?limit|limit (was )?reached/i.test(reason)) return 'The model has hit its usage limit. Pick another model or try again later.';
  return 'Something went wrong before Kel could start. Try again or pick another model.';
};

const KelEngineFailureCard: React.FC<{ reason: string; messageId: string; conversationId: string }> = ({
  reason,
  messageId,
  conversationId,
}) => {
  const conversation = useConversationContextSafe();
  const messages = useMessageList();
  const index = messages.findIndex((item) => item.id === messageId);
  const previousUser = index < 0
    ? undefined
    : messages.slice(0, index).reverse().find((item) => item.type === 'text' && item.position === 'right' && !item.hidden);
  const retryText = previousUser?.type === 'text' ? previousUser.content.content.trim() : '';
  const canRetry = Boolean(retryText) && !/\[\[AION_FILES\]\]|@@/.test(retryText) && !conversation?.hideSendBox;

  return (
    <section className='kel-chat-agent-error' role='alert' data-testid='kel-engine-failure'>
      <div className='kel-chat-agent-error__heading'>
        <Attention theme='filled' size='16' strokeLinejoin='bevel' className='m-t-2px' fill={iconColors.danger} />
        <strong>Kel couldn’t reply</strong>
      </div>
      <p className='kel-chat-agent-error__body'>{friendlyReason(reason)}</p>
      <div className='kel-chat-agent-error__actions'>
        <button
          type='button'
          className='kel-chat-agent-error__model'
          onClick={() => emitter.emit('agent.error.pick-model', conversationId)}
        >
          Pick another model
        </button>
        {canRetry && (
          <button
            type='button'
            className='kel-chat-agent-error__retry'
            onClick={() => emitter.emit('agent.error.retry', retryText, conversationId)}
          >
            Try again
          </button>
        )}
      </div>
      <details className='kel-chat-agent-error__details'>
        <summary>Details</summary>
        <div className='kel-chat-agent-error__diagnostics'>{reason}</div>
      </details>
    </section>
  );
};

export default KelEngineFailureCard;
