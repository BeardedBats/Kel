import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useKelModelState } from './KelModelControl';

type Scope = 'conversation' | 'default';

export const KelMobileModelPicker: React.FC<{
  conversationId: string;
  open: boolean;
  onClose: () => void;
}> = ({ conversationId, open, onClose }) => {
  const navigate = useNavigate();
  const { state, setConversation, setDefault } = useKelModelState(conversationId);
  const [scope, setScope] = useState<Scope>('conversation');
  const choices = useMemo(() => state?.providers.flatMap((provider) =>
    provider.options.map((option) => ({ ...option, providerId: provider.id, providerLabel: provider.label }))
  ) ?? [], [state]);

  useEffect(() => {
    if (!open) return;
    setScope('conversation');
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;
  const selected = scope === 'conversation' ? state?.conversation : state?.default;
  const isAutomatic = !selected?.provider;

  return createPortal(
    <div className='kel-mobile-model-picker' data-testid='kel-mobile-model-picker'>
      <button type='button' className='kel-mobile-model-picker__scrim' aria-label='Close model picker' onClick={onClose} />
      <section className='kel-mobile-model-picker__sheet' role='dialog' aria-modal='true' aria-label='Model'>
        <div className='kel-mobile-model-picker__handle' aria-hidden='true' />
        <h2>Model</h2>
        <div className='kel-mobile-model-picker__tabs' role='tablist' aria-label='Model scope'>
          <button type='button' role='tab' aria-selected={scope === 'conversation'} onClick={() => setScope('conversation')}>This chat</button>
          <button type='button' role='tab' aria-selected={scope === 'default'} onClick={() => setScope('default')}>Default for new chats</button>
        </div>
        <div className='kel-mobile-model-picker__choices'>
          <button type='button' className='kel-mobile-model-picker__choice' aria-pressed={isAutomatic} onClick={() => {
            if (scope === 'conversation') void setConversation(null);
            else void setDefault(null);
          }}>
            <span><strong>Automatic</strong><small>{scope === 'conversation' && state?.default?.provider ? 'Uses your default' : 'Kel picks'}</small></span>
            {isAutomatic && <span className='kel-mobile-model-picker__check' aria-hidden='true'>✓</span>}
          </button>
          {choices.map((choice) => {
            const active = selected?.provider === choice.providerId && selected.model === choice.id;
            return <button type='button' key={`${choice.providerId}:${choice.id}`} className='kel-mobile-model-picker__choice' aria-pressed={active} onClick={() => {
              const value = { provider: choice.providerId, model: choice.id };
              if (scope === 'conversation') void setConversation(value);
              else void setDefault(value);
            }}>
              <span><strong>{choice.label}</strong>{!choice.available && <small>Needs setup</small>}</span>
              {active && <span className='kel-mobile-model-picker__check' aria-hidden='true'>✓</span>}
            </button>;
          })}
          {!state && <p className='kel-mobile-model-picker__empty'>Kel's model list is unavailable right now.</p>}
        </div>
        <button type='button' className='kel-mobile-model-picker__add' onClick={() => { onClose(); navigate('/settings/model'); }}>Add model</button>
      </section>
    </div>,
    document.body
  );
};
