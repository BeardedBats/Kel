import type { AcpConfigOptionDto } from '@/common/types/platform/acpTypes';
import { deriveSelectOption, getRuntimeConfigOptionsKey } from '@/renderer/hooks/agent/useAcpConfigOptions';
import React from 'react';
import useSWR from 'swr';

/** Observe the composer's confirmed catalog. Never start a runtime or change permission. */
const ShellConversationModeLabel: React.FC<{ conversationId: string }> = ({ conversationId }) => {
  const { data } = useSWR<AcpConfigOptionDto[] | null>(getRuntimeConfigOptionsKey(conversationId), null, {
    revalidateOnMount: false,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });
  const mode = deriveSelectOption(data, 'mode', ['mode', 'session_mode']);
  const current = mode?.options.find((option) => option.value === mode.currentValue);
  if (!current) return null;
  const label = current.value === 'plan' ? 'Planning' : current.label;
  return <span className='kel-shell-chat-mode-label' data-testid='chat-mode-label'>{label}</span>;
};

export default ShellConversationModeLabel;
