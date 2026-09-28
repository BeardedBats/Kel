import React, { useState } from 'react';
import { Message } from '@arco-design/web-react';
import check from '@renderer/assets/figma/chat-pickers/model-check.svg';
import plus from '@renderer/assets/figma/chat-pickers/model-plus.svg';
import settings from '@renderer/assets/figma/chat-pickers/model-settings.svg';
import { choiceLabel, unavailableNote, KEL_MODEL_SCOPE_NOTE, type Choice, type ModelState } from './KelModelControl';
import './kel-model-availability.css';

type Scope = 'conversation' | 'default';

export const KelDesktopModelMenu: React.FC<{
  state: ModelState;
  hasConversation: boolean;
  onChoose: (choice: Choice | null, scope: Scope) => Promise<void>;
  onClose: () => void;
  onAdd: () => void;
  onSettings: () => void;
  /** D-69/D-70: staff run on their own role models; this opens Settings → Staff & models. */
  onStaff?: () => void;
  /** Lets the opener find this menu for keyboard handling (VIS-10). */
  menuId?: string;
}> = ({ state, hasConversation, onChoose, onClose, onAdd, onSettings, onStaff, menuId }) => {
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
  return <div className='kel-desktop-model-menu kel-desktop-picker' data-testid='kel-desktop-model-menu' data-kel-model-menu={menuId} role='dialog' aria-label='Model picker' onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); onClose(); } }}>
    <p className='kel-desktop-model-menu__caption' data-testid='kel-model-menu-caption'>{KEL_MODEL_SCOPE_NOTE}</p>
    <div className='kel-desktop-model-menu__scope' role='tablist' aria-label='Model scope'>
      <button type='button' role='tab' aria-selected={scope === 'conversation'} disabled={!hasConversation || pending} onClick={() => setScope('conversation')}>This chat</button>
      <button type='button' role='tab' aria-selected={scope === 'default'} disabled={pending} onClick={() => setScope('default')}>Default for new chats</button>
    </div>
    <button type='button' className='kel-desktop-picker__row' aria-pressed={!selected?.provider} disabled={pending} onClick={() => void choose(null)}>
      {scope === 'conversation'
        ? <span>{`Use default (${choiceLabel(state, state.default)})`}</span>
        : <><span>Automatic</span><small>Kel picks</small></>}
      {!selected?.provider && <img src={check} alt='' />}
    </button>
    {state.providers.flatMap(provider => provider.options.map(option => {
      const active = selected?.provider === provider.id && selected.model === option.id;
      // CH-2: an option Kel cannot answer with says why ("Not supported for chat yet", "Needs setup")
      // and cannot be picked; Add Model and model settings stay the way to set one up.
      const note = unavailableNote(option, provider);
      return <button type='button' key={`${provider.id}:${option.id}`} className='kel-desktop-picker__row' aria-pressed={active} disabled={pending || !!note} onClick={() => void choose({ provider: provider.id, model: option.id })}>
        <span>{option.label}</span>{note ? <small>{note}</small> : active && <img src={check} alt='' />}
      </button>;
    }))}
    <div className='kel-desktop-picker__divider' />
    <button type='button' className='kel-desktop-picker__row' onClick={onAdd}><img src={plus} alt='' /><span>Add model</span></button>
    <button type='button' className='kel-desktop-picker__row' onClick={onSettings}><img src={settings} alt='' /><span>Open model settings</span></button>
    {onStaff && <button type='button' className='kel-desktop-picker__row' onClick={onStaff}><img src={settings} alt='' /><span>Staff & models</span></button>}
  </div>;
};
