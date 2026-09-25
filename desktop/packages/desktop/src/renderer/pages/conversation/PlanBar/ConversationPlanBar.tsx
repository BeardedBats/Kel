/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { CheckOne, Down } from '@icon-park/react';
import { getChatSurfaceWidthClass } from '@renderer/pages/conversation/utils/chatSurfaceWidth';
import { useConversationRuntimeView } from '@renderer/pages/conversation/runtime/useConversationRuntimeView';
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLatestPlan } from './useLatestPlan';

/**
 * Live plan / to-do progress for the running turn, pinned above the send box.
 *
 * Deliberately NOT a message row: a plan is a snapshot that gets replaced, so
 * streaming it into the conversation both duplicated cards and buried the
 * current state under later messages.
 *
 * Renders nothing — and reserves no space — unless a plan belongs to the turn
 * running right now.
 */
const ConversationPlanBar: React.FC<{ conversation_id: string }> = ({ conversation_id }) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const plan = useLatestPlan();
  const { isProcessing, activeTurnId } = useConversationRuntimeView(conversation_id);

  const entries = useMemo(() => plan?.content.entries ?? [], [plan]);
  const completed = useMemo(() => entries.filter((entry) => entry.status === 'completed').length, [entries]);
  const current = useMemo(
    () => entries.find((entry) => entry.status === 'in_progress')
      ?? entries.find((entry) => entry.status === 'pending')
      ?? entries[entries.length - 1],
    [entries]
  );

  if (!plan || !entries.length || !isProcessing) return null;
  // A plan whose turn already ended must not hang over the next turn. Rows
  // written before turn_id existed degrade to the isProcessing check alone.
  if (plan.content.turn_id && plan.content.turn_id !== activeTurnId) return null;

  return (
    <div
      data-testid='conversation-plan-bar'
      className={`${getChatSurfaceWidthClass()} kel-plan-bar shrink-0`}
    >
      <button
        type='button'
        className='kel-plan-bar__summary'
        aria-expanded={expanded}
        aria-label={expanded ? t('conversation.planBar.collapse') : t('conversation.planBar.expand')}
        onClick={() => setExpanded((value) => !value)}
      >
        <strong>{t('conversation.planBar.title')}</strong>
        <span className='kel-plan-bar__count'>{completed}/{entries.length}</span>
        <span className='kel-plan-bar__current'>{current?.content}</span>
        <span className='kel-plan-bar__meter' aria-hidden='true'><span style={{ width: `${completed / entries.length * 100}%` }} /></span>
        <span className='kel-plan-bar__expand'>Expand plan</span>
        <Down size={14} className={`kel-plan-bar__chevron${expanded ? ' kel-plan-bar__chevron--open' : ''}`} />
      </button>
      {expanded && (
        <div
          className='kel-plan-bar__entries flex flex-col gap-6px overflow-y-auto overscroll-contain'
          // Viewport-relative, matching CommandQueuePanel's cap in this same
          // stack. The zone above the send box can hold the queue, the thought
          // bar and a multi-line input at once; a FIXED cap here eats a large
          // share of a short window and squeezes the message list.
          style={{ maxHeight: 'min(22vh, 180px)' }}
        >
          {entries.map((entry, index) => (
            <div key={`${index}-${entry.content}`} className='flex items-center gap-8px text-t-secondary text-13px'>
              {entry.status === 'completed' ? (
                <CheckOne size={16} theme='filled' className='flex text-success shrink-0' />
              ) : (
                <div className='size-14px rd-full b-2px b-solid border-3 shrink-0' />
              )}
              <span className={entry.status === 'in_progress' ? 'text-t-primary' : undefined}>{entry.content}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ConversationPlanBar;
