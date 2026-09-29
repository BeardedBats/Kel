/**
 * Kel model choice — one plain control for Kel's model and the per-conversation override.
 *
 * D-73.3: "Kel's model" is ONE value — the Kel row of Staff & models (`/api/model` roles). Settings →
 * Model shows and edits that same value, and the composer's picker is a per-chat override of it. The
 * older default-model setting is only read (it still wins in the engine while it exists) and is cleared
 * the next time Kel's model is chosen anywhere.
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
import {
  KELS_MODEL_CHANGED_EVENT,
  KELS_MODEL_ROLE,
  kelStaffRoles,
  kelStaffSetRole,
  type StaffListing,
  type StaffModelOption,
  type StaffRoleRow,
} from './staffModels/staffModelsApi';

export type Choice = { provider: string | null; model: string | null };
/** `note` says, in plain words, why an option cannot answer in chat (CH-2), e.g. "Not supported for chat yet". */
type ModelOption = { id: string; label: string; available: boolean; note?: string | null };
type ProviderRow = { id: string; label: string; available: boolean; note?: string | null; options: ModelOption[] };
/** The engine's own answer for which model Kel uses (06ac92d): the Kel role, or this chat's override. */
export type KelModelInEffect = {
  kel?: { label?: string | null; model?: string | null; mode?: string | null; source?: string | null } | null;
  conversation_override?: unknown;
  in_effect?: 'kel' | 'conversation' | null;
};

export type ModelState = {
  default: Choice | null;
  conversation: Choice | null;
  providers: ProviderRow[];
  kel_model?: KelModelInEffect | null;
};

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

/** Kel's model as one plain name: the Kel row's model, or "Automatic" when Kel picks. */
export const kelsModelLabel = (row: Pick<StaffRoleRow, 'mode' | 'model' | 'model_label'> | null | undefined): string | null => {
  if (!row) return null;
  if (row.mode === 'AUTOMATIC' || !row.model) return 'Automatic';
  return row.model_label || row.model;
};

export type KelsModel = {
  /** The Kel row of Staff & models; null while unread, or when the engine has no roles (older engine). */
  row: StaffRoleRow | null;
  /** The models Kel's row can use, with whether each can run here. */
  models: StaffModelOption[];
  label: string | null;
  loaded: boolean;
  /** Choose Kel's model (null = Automatic). Writes the Kel row; every surface reads it again. */
  choose: (model: string | null) => Promise<void>;
  refresh: () => Promise<void>;
};

/** D-73.3: the one "Kel's model", read from the Kel row of Staff & models. */
export const useKelsModel = (): KelsModel => {
  const [listing, setListing] = useState<StaffListing | null>(null);
  const [loaded, setLoaded] = useState(false);
  const refresh = useCallback(async () => {
    try {
      setListing(await kelStaffRoles());
    } catch {
      setListing(null);
    } finally {
      setLoaded(true);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const again = (): void => void refresh();
    window.addEventListener(KELS_MODEL_CHANGED_EVENT, again);
    return () => window.removeEventListener(KELS_MODEL_CHANGED_EVENT, again);
  }, [refresh]);
  const row = listing?.roles.find((entry) => entry.role === KELS_MODEL_ROLE) ?? null;
  const choose = useCallback(
    async (model: string | null) => {
      const reasoning = row?.reasoning || 'auto';
      const next = await kelStaffSetRole(
        KELS_MODEL_ROLE,
        model ? { mode: row?.mode === 'FIXED' ? 'FIXED' : 'PREFERRED', model, reasoning } : { mode: 'AUTOMATIC', reasoning }
      );
      setListing(next);
    },
    [row?.mode, row?.reasoning]
  );
  return { row, models: row ? listing?.models ?? [] : [], label: kelsModelLabel(row), loaded, choose, refresh };
};

/** Why one of Kel's models cannot be chosen, in plain words; null when it can run here. */
export const kelsModelNote = (option: StaffModelOption): string | null => {
  if (option.available !== false) return null;
  const note = (option.note || '').trim();
  return !note || SETUP_NOTES.has(note.toLowerCase()) ? 'Needs setup' : note;
};

/** Settings → Staff & models, for the chat whose engine conversation is `cid` when there is one. */
export const staffModelsPath = (cid?: string | null): string =>
  cid ? `/settings/staff?conversation=${encodeURIComponent(cid)}` : '/settings/staff';

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

  // D-73.3: Kel's model (one value). A chat's own pick overrides it; the older default setting, while it
  // still exists, is what the engine uses — so it is named rather than hidden.
  const kels = useKelsModel();
  // A change of Kel's model elsewhere may have cleared the older default: read the choice again.
  useEffect(() => {
    const again = (): void => void refresh();
    window.addEventListener(KELS_MODEL_CHANGED_EVENT, again);
    return () => window.removeEventListener(KELS_MODEL_CHANGED_EVENT, again);
  }, [refresh]);
  const effectiveLabel = useMemo(() => {
    if (!state) return null;
    if (state.conversation?.provider) return { label: choiceLabel(state, state.conversation), scope: 'this chat' };
    // An engine that reports what is in effect has retired the older default: Kel's role decides.
    if (state.kel_model) return { label: state.kel_model.kel?.label || kels.label || 'Automatic', scope: 'default' };
    if (state.default?.provider || !kels.label) return { label: choiceLabel(state, state.default), scope: 'default' };
    return { label: kels.label, scope: 'default' };
  }, [state, kels.label]);

  /** What "Use Kel's model" means right now, by name. */
  const kelsLabel = state?.kel_model
    ? state.kel_model.kel?.label || kels.label || 'Automatic'
    : state?.default?.provider
      ? choiceLabel(state, state.default)
      : kels.label ?? choiceLabel(state, null);

  return { state, cid, effectiveLabel, kels, kelsLabel, refresh, setDefault, setConversation };
};

const availabilityLabel = (note: string | null) => (
  <span className={`ms-auto kel-chip ${note ? 'kel-chip--wait' : 'kel-chip--ok'}`}>{note ?? 'Available'}</span>
);

export const KelModelPill: React.FC<{ conversationId?: string }> = ({ conversationId }) => {
  const navigate = useNavigate();
  const { state, cid, effectiveLabel, kels, kelsLabel, setDefault, setConversation } = useKelModelState(conversationId);
  // Staff & models opened from a chat names that chat's own model when it has one (FN-06).
  const staffPath = staffModelsPath(cid);
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
      <Menu.Item key='kel-model-scope' onClick={() => navigate(staffPath)}>
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
      kels={kels.row ? { label: kelsLabel ?? 'Automatic', row: kels.row, models: kels.models, choose: kels.choose } : undefined}
      onChoose={(choice, scope) => scope === 'conversation' ? setConversation(choice) : setDefault(choice)}
      onClose={() => setPopupVisible(false)}
      onAdd={() => { setPopupVisible(false); navigate('/settings/model?add=1'); }}
      onSettings={() => { setPopupVisible(false); navigate('/settings/model'); }}
      onStaff={() => { setPopupVisible(false); navigate(staffPath); }} menuId={menuId} /> : items}
      trigger='click' position={desktop ? 'tr' : 'bl'} unmountOnExit={desktop}
      // D-78: Kel's own popover motion runs on the desktop menu (it grows in and leaves as a copy).
      triggerProps={desktop ? { duration: 0 } : undefined}
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

/**
 * D-73.3: Settings → Model's card for Kel's model — the same value as the Kel row in Staff & models
 * (reasoning and Fixed/Preferred live there). An engine without roles keeps the older default list.
 */
/** `compact` is accepted for older callers; since D-87 the card never carries a description. */
export const KelDefaultModelCard: React.FC<{ compact?: boolean; title?: string }> = ({ title }) => {
  const navigate = useNavigate();
  const { state, kels, setDefault } = useKelModelState();
  const [busy, setBusy] = useState(false);
  // Defensive: a payload without the provider listing must not take the page down with it.
  const providers = state?.providers ?? [];

  if (kels.row) {
    const row = kels.row;
    const automatic = row.mode === 'AUTOMATIC' || !row.model;
    const choose = async (model: string | null) => {
      if (busy) return;
      setBusy(true);
      try {
        await kels.choose(model);
        Message.success(model ? 'Saved. Kel will use this model.' : 'Saved. Kel picks what is available.');
      } catch (error) {
        Message.error(String((error as Error)?.message || '').trim() || 'Kel could not change its model just now.');
      } finally {
        setBusy(false);
      }
    };
    // Only an engine that still honours the older default gets it named; newer engines ignore it.
    const older = state?.default?.provider && !state.kel_model ? choiceLabel(state, state.default) : null;
    return (
      <KelCard title={title ?? "Kel's model"} data-testid='kel-default-model-card'>
        {older ? (
          <p className='text-14px m-0 mb-10px' data-testid='kel-model-older-default'>
            {`Right now ${older} answers your chats — an older setting. Choose Kel's model below to make it the one setting.`}
          </p>
        ) : null}
        <div className='flex flex-col gap-4px kel-shell-default-model-rows' data-testid='kel-kels-model-rows'>
          <button
            type='button'
            data-testid='kel-default-auto'
            aria-pressed={automatic && !older}
            disabled={busy}
            onClick={() => void choose(null)}
            className='flex items-center text-left px-10px py-8px rounded-8px cursor-pointer kel-shell-default-model-row'
            style={{ background: automatic && !older ? 'var(--color-fill-2)' : 'transparent', border: '1px solid var(--color-border-2)' }}
          >
            <span className='kel-shell-default-model-lead' aria-hidden='true'>✦</span>
            <span className='kel-shell-default-model-name'>Automatic</span>
            <span className='kel-shell-default-model-status'>{automatic && !older ? 'Current' : ''}</span>
            <span className='kel-shell-default-model-action' />
          </button>
          {kels.models.map((option) => {
            const current = !automatic && !older && row.model === option.id;
            const note = kelsModelNote(option);
            return (
              <button
                key={option.id}
                type='button'
                disabled={busy}
                data-testid={'kel-kels-model-' + option.id}
                aria-pressed={current}
                onClick={() => (note ? navigate('/settings/providers') : void choose(option.id))}
                className='flex items-center text-left px-10px py-8px rounded-8px cursor-pointer kel-shell-default-model-row'
                style={{
                  background: current ? 'var(--kel-surface-2)' : 'transparent',
                  border: `1px solid ${current ? 'var(--kel-border-strong)' : 'var(--kel-border)'}`,
                }}
              >
                <span className='kel-shell-default-model-lead' aria-hidden='true'><img src={plugIcon} alt='' width={14} height={14} /></span>
                <span className='kel-shell-default-model-name'>{option.label}<span>{option.version && option.version !== option.label ? option.version : ''}</span></span>
                <span className={`kel-shell-default-model-status${note ? ' kel-shell-default-model-status--wait' : ''}`}>
                  {current && !note ? 'Current' : note ?? 'Available'}
                </span>
                <span className='kel-shell-default-model-action'>{current ? '' : note ? 'Set up' : 'Use'}</span>
              </button>
            );
          })}
        </div>
        <button type='button' className='kel-btn kel-btn--quiet mt-8px' onClick={() => navigate('/settings/staff')} data-testid='kel-model-staff-link'>
          Reasoning level and the staff’s models: Staff &amp; models
        </button>
      </KelCard>
    );
  }

  return (
    <KelCard title={title ?? 'Default model'} data-testid='kel-default-model-card'>
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
            <span className='kel-shell-default-model-name'>Automatic</span>
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
