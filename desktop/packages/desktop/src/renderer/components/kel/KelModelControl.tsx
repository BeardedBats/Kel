/**
 * Kel model choice — one plain control for the default model and the per-conversation override.
 *
 * The choice is a soft preference for Kel's routing (Auto keeps the original order, a chosen
 * provider is tried first, every fallback stays intact). Provider machinery, ids and endpoints
 * never appear here; only plain labels and availability.
 */
import { Dropdown, Menu, Message } from '@arco-design/web-react';
import { Down } from '@icon-park/react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KelCard } from './KelPrimitives';
import { kelRequest } from './kelApi';
import { KelDesktopModelMenu } from './KelDesktopModelMenu';
import plugIcon from '@renderer/assets/figma/model/plug.svg';
import { findByAttribute, useMenuKeyboard } from '@/renderer/hooks/ui/useMenuKeyboard';

export type Choice = { provider: string | null; model: string | null };
/** `note` says, in plain words, why an option cannot answer in chat (CH-2), e.g. "Not supported for chat yet". */
type ModelOption = { id: string; label: string; available: boolean; note?: string | null };
type ProviderRow = { id: string; label: string; available: boolean; note?: string | null; options: ModelOption[] };
export type ModelState = { default: Choice | null; conversation: Choice | null; providers: ProviderRow[] };

const request = <T,>(body: Record<string, unknown>): Promise<T> => kelRequest<T>('/api/model', body);

/** Engine notes that all mean the person can fix it in Providers; JR-42 says them as "Needs setup". */
const SETUP_NOTES = new Set(['api key needed', 'sign-in needed', 'not connected yet']);

/** Why an option cannot be picked, in plain words; null when it can answer in chat. */
export const unavailableNote = (option: ModelOption, provider?: Pick<ProviderRow, 'note'>): string | null => {
  if (option.available) return null;
  const note = option.note || provider?.note || 'Needs setup';
  return SETUP_NOTES.has(note.toLowerCase()) ? 'Needs setup' : note;
};

/**
 * D-69: a model picked in a chat (or as the default) is Kel's own — its replies and plans. Staff always
 * run on their role models, set in Settings → Staff & models (D-70 item 3). Said once, the same way,
 * wherever Kel's model is picked.
 */
export const KEL_MODEL_SCOPE_NOTE = "Kel's model — staff use their own (Settings → Staff & models)";

/** A provider Kel has no way to run yet cannot be fixed from Providers, so it offers no "Set up". */
export const NOT_SUPPORTED_NOTE = 'Not supported for chat yet';

/** The plain name of a model choice ('Automatic' when Kel picks). */
export const choiceLabel = (state: ModelState | null, choice: Choice | null): string => {
  if (!choice || !choice.provider) return 'Automatic';
  const provider = (state?.providers ?? []).find((entry) => entry.id === choice.provider);
  const option = provider?.options.find((entry) => entry.id === choice.model);
  if (!provider) return 'Automatic';
  return option ? `${option.label}` : provider.label;
};

export const useKelModelState = (conversationId?: string) => {
  const [state, setState] = useState<ModelState | null>(null);
  const [cid, setCid] = useState<string | null>(null);

  const refresh = useCallback(
    async (targetCid?: string | null) => {
      try {
        const body: Record<string, unknown> = { action: 'get' };
        const resolved = targetCid ?? cid;
        if (resolved) body.conversation = resolved;
        const next = await request<ModelState>(body);
        setState(next);
      } catch (error) {
        // The control stays hidden when the engine is not reachable.
        setState(null);
      }
    },
    [cid]
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      let resolved: string | null = null;
      if (conversationId) {
        try {
          const api = (window as unknown as { kelAPI?: { conversation?: (id: string) => Promise<string> } }).kelAPI;
          resolved = (await api?.conversation?.(conversationId)) ?? null;
        } catch (error) {
          resolved = null;
        }
      }
      if (!alive) return;
      setCid(resolved);
      await refresh(resolved);
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const setDefault = useCallback(
    async (choice: Choice | null) => {
      await request({ action: 'set_default', choice });
      if (conversationId) {
        Message.success('Saved. New chats will use this model.');
      } else {
        Message.success('Saved. New chats will use this model.');
      }
      await refresh();
    },
    [conversationId, refresh]
  );

  const setConversation = useCallback(
    async (choice: Choice | null) => {
      if (!conversationId) return;
      // A new chat is linked to its engine conversation only after the pill first mounted, so an
      // empty lookup is retried at choice time instead of failing with "Open a conversation...".
      let target = cid;
      if (!target) {
        try {
          const api = (window as unknown as { kelAPI?: { conversation?: (id: string) => Promise<string> } }).kelAPI;
          target = (await api?.conversation?.(conversationId)) ?? null;
          if (target) setCid(target);
        } catch {
          target = null;
        }
      }
      try {
        if (!choice || !choice.provider) {
          await request({ action: 'clear_conversation', conversation: target ?? undefined });
          Message.success('This chat follows the default model again.');
        } else {
          await request({ action: 'set_conversation', conversation: target ?? undefined, choice });
          Message.success('Saved. This chat will use that model.');
        }
      } catch (error) {
        // Audit COR-03: the engine's own sentence (e.g. 'Open a conversation before choosing its
        // model.') is the honest message; a transport failure gets a plain fallback instead of an
        // unhandled rejection with no feedback.
        const detail = String((error as Error)?.message || '').trim();
        Message.error(detail || 'Kel could not change the model just now.');
      }
      await refresh(target);
    },
    [cid, conversationId, refresh]
  );

  const effectiveLabel = useMemo(() => {
    if (!state) return null;
    const effective = state.conversation ?? state.default;
    const scope = state.conversation ? 'this chat' : 'default';
    return { label: choiceLabel(state, effective), scope };
  }, [state]);

  return { state, cid, effectiveLabel, refresh, setDefault, setConversation };
};

const availabilityLabel = (note: string | null) => (
  <span className={`ms-auto kel-chip ${note ? 'kel-chip--wait' : 'kel-chip--ok'}`}>{note ?? 'Available'}</span>
);

export const KelModelPill: React.FC<{ conversationId?: string }> = ({ conversationId }) => {
  const navigate = useNavigate();
  const { state, effectiveLabel, setDefault, setConversation } = useKelModelState(conversationId);
  const [desktop, setDesktop] = useState(() => window.innerWidth >= 768);
  const [popupVisible, setPopupVisible] = useState(false);
  // VIS-10: keyboard like the project chip (focus in, arrows, Escape back to the picker, closes on
  // page change). Hooks run before the early return below.
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const menuId = React.useId();
  useMenuKeyboard({
    open: popupVisible,
    onClose: () => setPopupVisible(false),
    getMenu: () => findByAttribute('data-kel-model-menu', menuId),
    triggerRef,
  });
  useEffect(() => {
    const resize = () => setDesktop(window.innerWidth >= 768);
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  if (!state || !effectiveLabel) {
    return (
      <button
        type='button'
        data-testid='kel-model-pill'
        className='flex items-center gap-4px text-12px px-8px h-24px rounded-12px opacity-70'
        style={{ background: 'var(--color-fill-2)', color: 'var(--color-text-2)', border: '1px solid var(--color-border-2)' }}
        disabled
      >
        <span>Kel model: …</span>
      </button>
    );
  }

  const providers = state.providers ?? [];
  const items = (
    <Menu style={{ maxHeight: 420, overflowY: 'auto', minWidth: 240 }} data-kel-model-menu={menuId}>
      <Menu.Item key='kel-model-scope' onClick={() => navigate('/settings/staff')}>
        <span className='text-12px text-t-secondary'>{KEL_MODEL_SCOPE_NOTE}</span>
      </Menu.Item>
      {conversationId ? (
        <Menu.ItemGroup title='This chat'>
          <Menu.Item key='chat-global' disabled={false} onClick={() => void setConversation(null)}>
            <span className='flex items-center w-full'>
              <span>Use the default model</span>
              {!state.conversation ? <span className='ms-auto text-12px text-t-secondary'>Current</span> : null}
            </span>
          </Menu.Item>
          {providers.map((provider) =>
            provider.options.map((option) => (
              <Menu.Item
                key={'chat-' + provider.id + '-' + option.id}
                disabled={!option.available}
                onClick={() => {
                  if (state.conversation?.provider === provider.id && state.conversation?.model === option.id) {
                    void setConversation(null);
                  } else {
                    void setConversation({ provider: provider.id, model: option.id });
                  }
                }}
              >
                <span className='flex items-center w-full'>
                  <span>
                    {option.label}
                    <span className='ms-6px text-11px text-t-secondary'>{provider.label}</span>
                  </span>
                  {state.conversation?.provider === provider.id && state.conversation?.model === option.id ? (
                    <span className='ms-auto text-12px'>Current</span>
                  ) : (
                    availabilityLabel(unavailableNote(option, provider))
                  )}
                </span>
              </Menu.Item>
            ))
          )}
        </Menu.ItemGroup>
      ) : null}
      <Menu.ItemGroup title={conversationId ? 'Default for new chats' : 'Default model'}>
        <Menu.Item
          key='auto'
          onClick={() => {
            void setDefault(null);
          }}
        >
          <span className='flex items-center w-full'>
            <span>Automatic — Kel picks what is available</span>
            {!state.default ? <span className='ms-auto text-12px text-t-secondary'>Current</span> : null}
          </span>
        </Menu.Item>
        {providers.map((provider) =>
          provider.options.map((option) => (
            <Menu.Item
              key={'default-' + provider.id + '-' + option.id}
              disabled={!option.available}
              onClick={() => {
                void setDefault({ provider: provider.id, model: option.id });
              }}
            >
              <span className='flex items-center w-full'>
                <span>
                  {option.label}
                  <span className='ms-6px text-11px text-t-secondary'>{provider.label}</span>
                </span>
                {state.default?.provider === provider.id && state.default?.model === option.id ? (
                  <span className='ms-auto text-12px'>Current</span>
                ) : (
                  availabilityLabel(unavailableNote(option, provider))
                )}
              </span>
            </Menu.Item>
          ))
        )}
      </Menu.ItemGroup>
      <Menu.Item key='details' disabled>
        <span className='text-12px text-t-secondary'>
          Details: answering with {effectiveLabel.label} ({effectiveLabel.scope})
        </span>
      </Menu.Item>
      <Menu.Item key='settings' onClick={() => navigate('/settings/model')}>
        Open model settings
      </Menu.Item>
    </Menu>
  );

  return (
    <Dropdown droplist={desktop ? <KelDesktopModelMenu state={state} hasConversation={!!conversationId}
      onChoose={(choice, scope) => scope === 'conversation' ? setConversation(choice) : setDefault(choice)}
      onClose={() => setPopupVisible(false)}
      onAdd={() => { setPopupVisible(false); navigate('/settings/model?add=1'); }}
      onSettings={() => { setPopupVisible(false); navigate('/settings/model'); }}
      onStaff={() => { setPopupVisible(false); navigate('/settings/staff'); }} menuId={menuId} /> : items}
      trigger='click' position={desktop ? 'tr' : 'bl'} unmountOnExit={desktop}
      popupVisible={popupVisible} onVisibleChange={setPopupVisible}>
      <button
        ref={triggerRef}
        type='button'
        data-testid='kel-model-pill'
        title={KEL_MODEL_SCOPE_NOTE}
        aria-label={`Kel's model: ${effectiveLabel.label}`}
        aria-haspopup='dialog'
        aria-expanded={popupVisible}
        className={desktop ? 'kel-desktop-model-trigger' : 'flex items-center gap-4px text-12px px-8px h-24px rounded-12px cursor-pointer'}
        style={desktop ? undefined : { background: 'var(--color-fill-2)', color: 'var(--color-text-1)', border: '1px solid var(--color-border-2)' }}
      >
        <span>{desktop ? effectiveLabel.label : `Kel model: ${effectiveLabel.label}`}</span>
        <Down size={12} />
      </button>
    </Dropdown>
  );
};

export const KelDefaultModelCard: React.FC<{ compact?: boolean; title?: string }> = ({ compact = false, title = 'Default model' }) => {
  const navigate = useNavigate();
  const { state, setDefault } = useKelModelState();
  // Defensive: a payload without the provider listing must not take the page down with it.
  const providers = state?.providers ?? [];

  return (
    <KelCard title={title} data-testid='kel-default-model-card'>
      {!compact && <p className='text-14px text-t-secondary m-0 mb-10px'>
        Kel uses this model for normal conversations. The list shows the models available to Kel right
        now — a chat can still pick its own model from the chat header, and Automatic keeps Kel's
        routing across every available provider.
      </p>}
      {!state ? (
        <p className='text-14px text-t-secondary m-0'>Kel's model list is unavailable right now.</p>
      ) : (
        <div className='flex flex-col gap-4px kel-shell-default-model-rows'>
          <button
            type='button'
            data-testid='kel-default-auto'
            aria-pressed={!state.default}
            onClick={() => void setDefault(null)}
            className='flex items-center text-left px-10px py-8px rounded-8px cursor-pointer kel-shell-default-model-row'
            style={{ background: !state.default ? 'var(--color-fill-2)' : 'transparent', border: '1px solid var(--color-border-2)' }}
          >
            <span className='kel-shell-default-model-lead' aria-hidden='true'>✦</span>
            <span className='kel-shell-default-model-name'>Automatic<span>Kel picks what is available</span></span>
            <span className='kel-shell-default-model-status'>{!state.default ? 'Current' : ''}</span>
            <span className='kel-shell-default-model-action' />
          </button>
          {providers.map((provider) =>
            provider.options.map((option) => {
              const current = state.default?.provider === provider.id && state.default?.model === option.id;
              const note = unavailableNote(option, provider);
              // CH-2: an option Kel cannot answer with is never picked here; one that setup can fix
              // leads to Providers, one Kel cannot run yet says so and does nothing.
              const settable = note !== NOT_SUPPORTED_NOTE;
              return (
                <button
                  key={provider.id + '-' + option.id}
                  type='button'
                  disabled={!settable}
                  data-testid={'kel-default-' + provider.id + '-' + option.id}
                  aria-pressed={current}
                  onClick={() => (!note ? void setDefault({ provider: provider.id, model: option.id }) : navigate('/settings/providers'))}
                  className='flex items-center text-left px-10px py-8px rounded-8px cursor-pointer kel-shell-default-model-row'
                  style={{
                    background: current ? 'var(--kel-surface-2)' : 'transparent',
                    border: `1px solid ${current ? 'var(--kel-border-strong)' : 'var(--kel-border)'}`,
                  }}
                >
                  <span className='kel-shell-default-model-lead' aria-hidden='true'><img src={plugIcon} alt='' width={14} height={14} /></span>
                  <span className='kel-shell-default-model-name'>{option.label}<span>{provider.label}</span></span>
                  <span className={`kel-shell-default-model-status${note ? ' kel-shell-default-model-status--wait' : ''}`}>
                    {current && !note ? 'Current' : note ?? 'Available'}
                  </span>
                  <span className='kel-shell-default-model-action'>{current || !settable ? '' : note ? 'Set up' : 'Use'}</span>
                </button>
              );
            })
          )}
        </div>
      )}
    </KelCard>
  );
};
