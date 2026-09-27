/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Search } from '@icon-park/react';
import classNames from 'classnames';
import { openKelCommandPalette } from '@renderer/components/kel/KelCommandPalette';
import type { SiderTooltipProps } from '@renderer/utils/ui/siderTooltip';

interface SiderSearchEntryProps {
  isMobile: boolean;
  collapsed: boolean;
  siderTooltipProps: SiderTooltipProps;
  onConversationSelect: () => void;
  onSessionClick?: () => void;
}

/**
 * CH-17: the phone sidebar's search entry opens the same search as the header button and
 * Ctrl+K (the command palette in search mode). Picking a chat there navigates to it, so the
 * sidebar is closed first to leave the result visible.
 */
const SiderSearchEntry: React.FC<SiderSearchEntryProps> = ({ isMobile, collapsed, onConversationSelect }) => {
  const label = isMobile ? 'Search chats' : 'Search';
  return (
    <button
      type='button'
      className={classNames(
        'w-full flex items-center gap-8px border-none bg-transparent cursor-pointer text-t-primary',
        collapsed ? 'justify-center h-32px rd-8px' : 'px-12px py-8px',
        isMobile && 'sider-action-btn-mobile'
      )}
      aria-label={label}
      data-testid='sider-search-entry'
      onClick={() => {
        onConversationSelect();
        openKelCommandPalette('search');
      }}
    >
      <Search theme='outline' size={16} fill='currentColor' />
      {!collapsed && <span>{label}</span>}
    </button>
  );
};

export default SiderSearchEntry;
