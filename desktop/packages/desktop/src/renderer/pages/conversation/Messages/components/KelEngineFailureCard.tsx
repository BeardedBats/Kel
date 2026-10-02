/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 */

import { Attention } from '@icon-park/react';
import React, { useEffect, useState } from 'react';
import { useConversationContextSafe } from '@/renderer/hooks/context/ConversationContext';
import { iconColors } from '@/renderer/styles/colors';
import { emitter } from '@/renderer/utils/emitter';
import { useMessageList } from '../hooks';
import type { TMessage } from '@/common/chat/chatLib';
import { kelWorkSubmissionId } from '@/common/chat/kelWork';
import { HANDOFF_STATE_EVENT, lastHandoffViews } from '@renderer/components/kel/workCards/handoffMemory';

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
export const friendlyReason = (reason: string): string => {
  if (/project needs a test command/i.test(reason)) return 'Add a test command to this project before Kel changes its code.';
  if (/no image tool|cannot generate an image/i.test(reason)) return 'No image tool is available. Connect Codex, then try again here.';
  if (/timed? ?out|took too long/i.test(reason)) return 'This took too long. Try again.';
  if (/structured result|invalid json|parse/i.test(reason)) return 'Kel could not use the model’s answer. Try again.';
  if (/auth|api key|sign.?in|credential/i.test(reason)) return 'This model needs a sign-in. Sign in, then try again.';
  if (/quota|rate.?limit|limit (was )?reached/i.test(reason)) return 'This model has reached its limit. Try again later.';
  return 'Kel could not start this request. Try again.';
};

/** A handoff card owns a failed start in this user turn. Keep standalone failures visible. */
export const hasWorkFailureOwner = (messages: TMessage[], messageId: string): boolean => {
  const index = messages.findIndex(item => item.id === messageId);
  if (index < 0) return false;
  const failed = messages[index];
  if (failed.type !== 'text' || !/^I wasn't able to get that started\s*[—-]/.test(failed.content.content.trim())) return false;
  const conversation = messages[index].conversation_id;
  for (let i = index - 1; i >= 0; i--) {
    const item = messages[i];
    if (item.conversation_id !== conversation || item.hidden) continue;
    if (item.type === 'text' && item.position === 'right') return false;
    if (item.type === 'acp_tool_call') {
      const sid = kelWorkSubmissionId(item.content?.update?.tool_call_id);
      if (!sid) continue;
      const view = lastHandoffViews.get(sid);
      const reason = parseEngineFailure(failed.content.content);
      const recorded = String(view?.error || view?.why || '').trim().replace(/\.$/, '');
      return view?.phase === 'failed_to_start' && Boolean(reason && recorded && reason === recorded);
    }
  }
  return false;
};

export const useHandoffFailureOwner = (messages: TMessage[], messageId: string, failure: string | null): boolean => {
  const [, update] = useState(0);
  useEffect(() => {
    if (!failure) return;
    const refresh = () => update(value => value + 1);
    window.addEventListener(HANDOFF_STATE_EVENT, refresh);
    return () => window.removeEventListener(HANDOFF_STATE_EVENT, refresh);
  }, [failure]);
  return Boolean(failure && hasWorkFailureOwner(messages, messageId));
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
        <button type='button' className='kel-chat-agent-error__model'
          onClick={() => emitter.emit('agent.error.pick-model', conversationId)}>Change model</button>
      </details>
    </section>
  );
};

export default KelEngineFailureCard;
