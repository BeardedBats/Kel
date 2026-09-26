import React, { useState } from 'react';
import { Message } from '@arco-design/web-react';
import check from '@renderer/assets/figma/chat-pickers/model-check.svg';
import plus from '@renderer/assets/figma/chat-pickers/model-plus.svg';
import settings from '@renderer/assets/figma/chat-pickers/model-settings.svg';
import type { Choice, ModelState } from './KelModelControl';

type Scope = 'conversation' | 'default';

export const KelDesktopModelMenu: React.FC<{
  state: ModelState;
  hasConversation: boolean;
  onChoose: (choice: Choice | null, scope: Scope) => Promise<void>;
  onClose: () => void;
  onAdd: () => void;
  onSettings: () => void;
}> = ({ state, hasConversation, onChoose, onClose, onAdd, onSettings }) => {
  const [scope, setScope] = useState<Scope>(hasConversation ? 'conversation' : 'default');
  const [pending, setPending] = useState(false);
  const selected = scope === 'conversation' ? state.conversation : state.default;
  const choose = async (choice: Choice | null) => {
    if (pending) return;
    setPending(true);
    try { await onChoose(choice, scope); onClose(); }
    catch (error) { Message.error((error as Error).message || 'Kel could not change the model just now.'); }
    finally { setPending(false); }
  };
  return <div className='kel-desktop-model-menu kel-desktop-picker' data-testid='kel-desktop-model-menu' aria-label='Model picker' onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); onClose(); } }}>
    <div className='kel-desktop-model-menu__scope' role='tablist' aria-label='Model scope'>
      <button type='button' role='tab' aria-selected={scope === 'conversation'} disabled={!hasConversation || pending} onClick={() => setScope('conversation')}>This chat</button>
      <button type='button' role='tab' aria-selected={scope === 'default'} disabled={pending} onClick={() => setScope('default')}>Default for new chats</button>
    </div>
    <button type='button' className='kel-desktop-picker__row' aria-pressed={!selected?.provider} disabled={pending} onClick={() => void choose(null)}>
      <span>Automatic</span><small>{scope === 'conversation' && state.default?.provider ? 'Uses default' : 'Kel picks'}</small>
      {!selected?.provider && <img src={check} alt='' />}
    </button>
    {state.providers.flatMap(provider => provider.options.map(option => {
      const active = selected?.provider === provider.id && selected.model === option.id;
      return <button type='button' key={`${provider.id}:${option.id}`} className='kel-desktop-picker__row' aria-pressed={active} disabled={pending} onClick={() => void choose({ provider: provider.id, model: option.id })}>
        <span>{option.label}</span>{active ? <img src={check} alt='' /> : !option.available && <small>Needs setup</small>}
      </button>;
    }))}
    <div className='kel-desktop-picker__divider' />
    <button type='button' className='kel-desktop-picker__row' onClick={onAdd}><img src={plus} alt='' /><span>Add Model</span></button>
    <button type='button' className='kel-desktop-picker__row' onClick={onSettings}><img src={settings} alt='' /><span>Open model settings</span></button>
  </div>;
};
