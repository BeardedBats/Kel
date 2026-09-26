import React from 'react';
import { Dropdown } from '@arco-design/web-react';

export type DesktopFileAction = { label: string; onClick: () => void; disabled?: boolean };

export const KelDesktopFileToolbar: React.FC<{
  viewMode: 'source' | 'preview';
  split: boolean;
  onViewMode: (mode: 'source' | 'preview') => void;
  onSplit: () => void;
  onAddToChat: () => void;
  canAddToChat?: boolean;
  actions: DesktopFileAction[];
}> = ({ viewMode, split, onViewMode, onSplit, onAddToChat, canAddToChat = true, actions }) => {
  const [moreOpen, setMoreOpen] = React.useState(false);
  return <div className='kel-file-toolbar'>
    <div role='tablist' aria-label='File view' className='kel-file-view-tabs'>
      <button type='button' role='tab' aria-selected={!split && viewMode === 'preview'} onClick={() => onViewMode('preview')}>Preview</button>
      <button type='button' role='tab' aria-selected={!split && viewMode === 'source'} onClick={() => onViewMode('source')}>Code</button>
    </div>
    <div className='kel-file-toolbar-actions'>
      <button type='button' disabled={!canAddToChat} onClick={onAddToChat}>Add to chat</button>
      <button type='button' aria-pressed={split} onClick={onSplit}>{split ? 'Close split screen' : 'Open split screen'}</button>
      <Dropdown trigger='click' position='br' popupVisible={moreOpen} onVisibleChange={setMoreOpen} droplist={<div className='kel-desktop-picker kel-file-action-menu'>
        {actions.map(action => <button key={action.label} type='button' className='kel-desktop-picker__row' disabled={action.disabled} onClick={() => { setMoreOpen(false); action.onClick(); }}>{action.label}</button>)}
      </div>}><button type='button' aria-label='More file actions' aria-haspopup='menu'>⋯</button></Dropdown>
    </div>
  </div>;
};

export const KelDesktopFileStatus: React.FC<{
  path: string;
  content: string;
  dirty: boolean;
  onReveal?: () => void;
}> = ({ path, content, dirty, onReveal }) => {
  const lines = content ? content.split(/\r\n|\r|\n/).length : 0;
  return <div className='kel-file-status'>
    <span title={path}>{path} · {lines} {lines === 1 ? 'line' : 'lines'}{dirty ? ' · unsaved changes' : ''}</span>
    {onReveal && <button type='button' onClick={onReveal}>Show in folder</button>}
  </div>;
};
