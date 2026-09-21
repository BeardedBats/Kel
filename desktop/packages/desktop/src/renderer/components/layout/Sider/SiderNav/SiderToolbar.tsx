// Kel shell: Figma New Chat v2 (152:163), preserving existing callbacks.
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { SiderTooltipProps } from '@renderer/utils/ui/siderTooltip';
import plus from '@renderer/assets/figma/plus.svg';
interface SiderToolbarProps {
  isMobile: boolean; isBatchMode: boolean; collapsed: boolean;
  siderTooltipProps: SiderTooltipProps; onNewChat: () => void; onToggleBatchMode: () => void;
}
const SiderToolbar: React.FC<SiderToolbarProps> = ({ isBatchMode, collapsed, onNewChat, onToggleBatchMode }) => {
  const { t } = useTranslation();
  return <div className='kel-shell-toolbar'>
    <button type='button' className='kel-shell-new-chat' onClick={onNewChat} aria-label='New Chat'>
      <img src={plus} alt='' width={22} height={22} />{!collapsed && <span>New Chat</span>}
    </button>
    <button type='button' className='kel-shell-batch' onClick={onToggleBatchMode}
      aria-pressed={isBatchMode} aria-label={t('conversation.history.batchManage')}
      title={t('conversation.history.batchManage')}>⋯</button>
  </div>;
};
export default SiderToolbar;
