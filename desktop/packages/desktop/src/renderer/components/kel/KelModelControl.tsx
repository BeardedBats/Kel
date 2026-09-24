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

type Choice = { provider: string | null; model: string | null };
type ModelOption = { id: string; label: string; available: boolean };
type ProviderRow = { id: string; label: string; available: boolean; options: ModelOption[] };
type ModelState = { default: Choice | null; conversation: Choice | null; providers: ProviderRow[] };

const request = <T,>(body: Record<string, unknown>): Promise<T> => kelRequest<T>('/api/model', body);

const choiceLabel = (state: ModelState | null, choice: Choice | null): string => {
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
      try {
        if (!choice || !choice.provider) {
          await request({ action: 'clear_conversation', conversation: cid ?? undefined });
          Message.success('This chat follows the default model again.');
        } else {
          await request({ action: 'set_conversation', conversation: cid ?? undefined, choice });
          Message.success('Saved. This chat will use that model.');
        }
      } catch (error) {
        // Audit COR-03: the engine's own sentence (e.g. 'Open a conversation before choosing its
        // model.') is the honest message; a transport failure gets a plain fallback instead of an
        // unhandled rejection with no feedback.
        const detail = String((error as Error)?.message || '').trim();
        Message.error(detail || 'Kel could not change the model just now.');
      }
      await refresh();
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

const availabilityLabel = (available: boolean) => (
  <span className={`ms-auto kel-chip ${available ? 'kel-chip--ok' : 'kel-chip--wait'}`}>
    {available ? 'Available' : 'Needs setup'}
  </span>
);

export const KelModelPill: React.FC<{ conversationId?: string }> = ({ conversationId }) => {
  const navigate = useNavigate();
  const { state, effectiveLabel, setDefault, setConversation } = useKelModelState(conversationId);

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
    <Menu style={{ maxHeight: 420, overflowY: 'auto', minWidth: 240 }}>
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
                disabled={false}
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
                    availabilityLabel(option.available)
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
              disabled={false}
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
                  availabilityLabel(option.available)
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
    <Dropdown droplist={items} trigger='click' position='bl' unmountOnExit={false}>
      <button
        type='button'
        data-testid='kel-model-pill'
        className='flex items-center gap-4px text-12px px-8px h-24px rounded-12px cursor-pointer'
        style={{ background: 'var(--color-fill-2)', color: 'var(--color-text-1)', border: '1px solid var(--color-border-2)' }}
      >
        <span>Kel model: {effectiveLabel.label}</span>
        <Down size={12} />
      </button>
    </Dropdown>
  );
};

export const KelDefaultModelCard: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const { state, setDefault } = useKelModelState();
  // Defensive: a payload without the provider listing must not take the page down with it.
  const providers = state?.providers ?? [];

  return (
    <KelCard title='Available now' data-testid='kel-default-model-card'>
      {!compact && <p className='text-14px text-t-secondary m-0 mb-10px'>
        Kel uses this model for normal conversations. The list shows the models available to Kel right
        now — a chat can still pick its own model from the chat header, and Automatic keeps Kel's
        routing across every available provider.
      </p>}
      {!state ? (
        <p className='text-14px text-t-secondary m-0'>Kel's model list is unavailable right now.</p>
      ) : (
        <div className='flex flex-col gap-4px'>
          <button
            type='button'
            data-testid='kel-default-auto'
            aria-pressed={!state.default}
            onClick={() => void setDefault(null)}
            className='flex items-center text-left px-10px py-8px rounded-8px cursor-pointer'
            style={{ background: !state.default ? 'var(--color-fill-2)' : 'transparent', border: '1px solid var(--color-border-2)' }}
          >
            <span className='text-14px'>Automatic<span className='kel-desktop-only'> — Kel picks what is available</span></span>
            {!state.default ? <span className='ms-auto text-11px text-t-secondary'>Current</span> : null}
          </button>
          {providers.map((provider) =>
            provider.options.map((option) => {
              const current = state.default?.provider === provider.id && state.default?.model === option.id;
              return (
                <button
                  key={provider.id + '-' + option.id}
                  type='button'
                  disabled={false}
                  data-testid={'kel-default-' + provider.id + '-' + option.id}
                  aria-pressed={current}
                  onClick={() => void setDefault({ provider: provider.id, model: option.id })}
                  className='flex items-center text-left px-10px py-8px rounded-8px cursor-pointer disabled:cursor-not-allowed'
                  style={{
                    background: current ? 'var(--kel-surface-2)' : 'transparent',
                    border: `1px solid ${current ? 'var(--kel-border-strong)' : 'var(--kel-border)'}`,
                  }}
                >
                  <span className='text-14px' style={{ opacity: option.available ? 1 : 0.6 }}>
                    {option.label}
                    <span className='ms-6px text-12px text-t-secondary kel-desktop-only'>{provider.label}</span>
                  </span>
                  {current ? <span className='ms-auto text-12px text-t-secondary'>Current</span> : availabilityLabel(option.available)}
                </button>
              );
            })
          )}
        </div>
      )}
      <p className='text-12px text-t-secondary m-0 mt-8px kel-desktop-only'>Saved immediately. Switching back to Automatic restores Kel's normal routing.</p>
    </KelCard>
  );
};
