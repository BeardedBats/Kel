/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import kelMark from '@renderer/assets/figma/kel-mark.png';
import { ipcBridge } from '@/common';
import { AgentLogoIcon } from '@/renderer/components/agent/AgentBadge';
import { usePresetAssistantInfo } from '@/renderer/hooks/agent/usePresetAssistantInfo';
import { resolveConversationBackend } from '@/renderer/pages/conversation/utils/conversationAssistantIdentity';
import React from 'react';
import useSWR from 'swr';

type MobileConversationBrandProps = {
  conversation_id: string;
  fallbackTitle: string;
};

const MobileConversationBrand: React.FC<MobileConversationBrandProps> = ({ conversation_id, fallbackTitle }) => {
  const { data: conversation } = useSWR(
    conversation_id ? `mobile-titlebar.conversation.${conversation_id}` : null,
    () => ipcBridge.conversation.get.invoke({ id: conversation_id })
  );
  const { info: presetAssistant } = usePresetAssistantInfo(conversation || undefined);
  const backend = resolveConversationBackend(conversation, presetAssistant?.backend);

  const showLogo = Boolean(backend || presetAssistant);
  const title = conversation?.name || fallbackTitle;

  return (
    <span className='app-titlebar__brand-mobile'>
      {showLogo && (
        presetAssistant ? <AgentLogoIcon
          backend={backend}
          agent_name={title}
          agentLogo={presetAssistant?.logo}
          agentLogoIsEmoji={presetAssistant?.isEmoji}
          agentLogoIsFallback={presetAssistant?.isFallback}
        /> : <img src={kelMark} alt="" width={22} height={22} />
      )}
      <span className='app-titlebar__brand-text'>{title}</span>
    </span>
  );
};

export default MobileConversationBrand;
