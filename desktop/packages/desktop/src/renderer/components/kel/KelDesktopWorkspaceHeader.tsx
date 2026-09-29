import React, { useRef } from 'react';
import { EdgePill } from '@renderer/motion';
import { Dropdown } from '@arco-design/web-react';
import search from '@renderer/assets/figma/workspace-panel/search.svg';
import refresh from '@renderer/assets/figma/workspace-panel/refresh.svg';
import close from '@renderer/assets/figma/workspace-panel/close.svg';

export const KelDesktopWorkspaceHeader: React.FC<{
  tab: 'files' | 'changes';
  changeCount?: number;
  searching: boolean;
  refreshing: boolean;
  onTab: (tab: 'files' | 'changes') => void;
  onSearch: () => void;
  onRefresh: () => void;
  onClose: () => void;
  onAddFolder?: () => void;
  onCollapseAll?: () => void;
}> = ({ tab, changeCount, searching, refreshing, onTab, onSearch, onRefresh, onClose, onAddFolder, onCollapseAll }) => {
  const [actionsOpen, setActionsOpen] = React.useState(false);
  const tabsRef = useRef<HTMLDivElement>(null);
  return <>
  <div className='kel-workspace-head'>
    <h2><Dropdown trigger='click' position='bl' popupVisible={actionsOpen} onVisibleChange={setActionsOpen} droplist={<div className='kel-desktop-picker kel-workspace-action-menu'>
      <button type='button' className='kel-desktop-picker__row' onClick={() => { setActionsOpen(false); onAddFolder?.(); }}>Add folder</button>
      <button type='button' className='kel-desktop-picker__row' onClick={() => { setActionsOpen(false); onCollapseAll?.(); }}>Collapse all folders</button>
    </div>}><button type='button' className='kel-workspace-heading-action' aria-label='Files actions' aria-haspopup='menu'>Files</button></Dropdown></h2>
    <button type='button' aria-label='Search files' aria-pressed={searching} onClick={onSearch}><img src={search} alt='' /></button>
    <button type='button' aria-label='Refresh files' disabled={refreshing} aria-busy={refreshing} onClick={onRefresh}><img src={refresh} alt='' /></button>
    <button type='button' aria-label='Close files' onClick={onClose}><img src={close} alt='' /></button>
  </div>
  <div ref={tabsRef} className='kel-workspace-tabs' role='tablist' aria-label='Files view'>
    <EdgePill containerRef={tabsRef} active="button[aria-selected='true']" trigger={tab} axis='x' className='kel-tab-pill' />
    <button type='button' role='tab' aria-selected={tab === 'files'} onClick={() => onTab('files')}>Files</button>
    <button type='button' role='tab' aria-selected={tab === 'changes'} onClick={() => onTab('changes')}>Changes{changeCount === undefined ? '' : ` · ${changeCount}`}</button>
  </div>
</>;
};
