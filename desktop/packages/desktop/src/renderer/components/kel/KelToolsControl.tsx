/**
 * Kel tools — what Kel may use in THIS conversation, in plain words.
 *
 * A compact control beside the model pill. Each capability is one plain word (Web, Files, Terminal,
 * GitHub); the menu offers Use default / Enabled for this chat / Disabled for this chat, plus Enable
 * once for a single request. Availability is stated in plain words and an unavailable capability can
 * never be switched on — the engine refuses it.
 */
import { Dropdown, Menu, Message } from '@arco-design/web-react';
import toolsIcon from '@renderer/assets/figma/nav-tools.svg';
import chevronIcon from '@renderer/assets/figma/chat-shell/mode-chevron.svg';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

type CapabilityRow = {
  id: string;
  label: string;
  description: string;
  availability: 'available' | 'needs_setup' | 'unavailable';
  availability_reason: string;
  global: 'on' | 'off';
  override: 'default' | 'on' | 'off';
  effective: 'on' | 'off';
  usable: boolean;
};

const request = <T,>(body: Record<string, unknown>): Promise<T> => {
  const api = (window as unknown as { kelAPI?: { request: (route: string, payload?: unknown) => Promise<unknown> } }).kelAPI;
  if (!api) return Promise.reject(new Error('Kel connection is unavailable'));
  return api.request('/api/capabilities', body) as Promise<T>;
};

const availabilityWords = (row: CapabilityRow): string => {
  if (row.availability === 'available') return 'Available';
  if (row.availability === 'needs_setup') return 'Needs setup';
  return 'Unavailable';
};

export const KelToolsControl: React.FC<{ conversationId?: string }> = ({ conversationId }) => {
  const navigate = useNavigate();
  const [rows, setRows] = useState<CapabilityRow[] | null>(null);
  const [cid, setCid] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async (target?: string | null) => {
    const resolved = target ?? cid;
    try {
      const next = await request<unknown>({ action: 'get', conversation: resolved ?? undefined });
      setRows(Array.isArray(next) ? (next as CapabilityRow[]) : null);
    } catch {
      setRows(null);
    }
  }, [cid]);

  useEffect(() => {
    let alive = true;
    (async () => {
      let resolved: string | null = null;
      if (conversationId) {
        try {
          const api = (window as unknown as { kelAPI?: { conversation?: (id: string) => Promise<string> } }).kelAPI;
          resolved = (await api?.conversation?.(conversationId)) ?? null;
        } catch {
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

  const choose = useCallback(
    async (capability: string, choice: 'default' | 'on' | 'off', label: string) => {
      setBusy(true);
      try {
        // The engine answers a change with the new state, not the rows: re-read the rows so the menu
        // never holds a non-list (which crashed the whole window).
        await request<unknown>({ action: 'set', conversation: cid ?? undefined, capability, state: choice });
        await refresh();
        Message.success(
          choice === 'default'
            ? `${label} follows your usual setting here again.`
            : choice === 'on'
              ? `${label} is on for this conversation.`
              : `${label} is off for this conversation.`
        );
      } catch {
        Message.error('Kel could not change that just now.');
        void refresh();
      } finally {
        setBusy(false);
      }
    },
    [cid, refresh]
  );

  const enableOnce = useCallback(
    async (capability: string, label: string) => {
      setBusy(true);
      try {
        await request<unknown>({ action: 'allow_once', conversation: cid ?? undefined, capability });
        await refresh();
        Message.success(`${label} is allowed for your next request only.`);
      } catch {
        Message.error('Kel could not allow that just now.');
      } finally {
        setBusy(false);
      }
    },
    [cid, refresh]
  );

  const resetAll = useCallback(async () => {
    setBusy(true);
    try {
      await request<unknown>({ action: 'reset', conversation: cid ?? undefined });
      await refresh();
      Message.success('This conversation follows your usual settings again.');
    } catch {
      Message.error('Kel could not reset that just now.');
    } finally {
      setBusy(false);
    }
  }, [cid, refresh]);

  const changed = useMemo(() => (rows ?? []).filter((row) => row.override !== 'default').length, [rows]);

  const items = (
    <Menu className='kel-tools-menu' data-testid='kel-tools-menu'>
      {(rows ?? []).map((row) => (
        <Menu.ItemGroup key={row.id} title={`${row.label} — ${availabilityWords(row)}`}>
          {row.availability !== 'available' ? (
            <Menu.Item key={`${row.id}-setup`} onClick={() => navigate('/settings/tools')} data-testid={`kel-tool-${row.id}-setup`}>
              <span className='text-12px'>{row.availability_reason}</span>
            </Menu.Item>
          ) : row.global === 'off' && row.override !== 'on' ? (
            <Menu.Item key={`${row.id}-off`} disabled data-testid={`kel-tool-${row.id}-global-off`}>
              <span className='text-12px'>Off for all chats (change it in Settings)</span>
            </Menu.Item>
          ) : null}
          <Menu.Item
            key={`${row.id}-default`}
            className={row.override === 'default' ? 'kel-tools-menu__current' : undefined}
            onClick={() => void choose(row.id, 'default', row.label)}
            data-testid={`kel-tool-${row.id}-default`}
          >
            <span className='flex items-center w-full'>
              <span>Use default</span>
              {row.override === 'default' ? <span className='ms-auto text-11px text-t-secondary'>Current</span> : null}
            </span>
          </Menu.Item>
          <Menu.Item
            key={`${row.id}-on`}
            className={row.override === 'on' ? 'kel-tools-menu__current' : undefined}
            onClick={() => void choose(row.id, 'on', row.label)}
            data-testid={`kel-tool-${row.id}-on`}
          >
            <span className='flex items-center w-full'>
              <span>Enabled for this chat</span>
              {row.override === 'on' ? <span className='ms-auto text-11px text-t-secondary'>Current</span> : null}
            </span>
          </Menu.Item>
          <Menu.Item
            key={`${row.id}-off`}
            className={row.override === 'off' ? 'kel-tools-menu__current' : undefined}
            onClick={() => void choose(row.id, 'off', row.label)}
            data-testid={`kel-tool-${row.id}-off`}
          >
            <span className='flex items-center w-full'>
              <span>Disabled for this chat</span>
              {row.override === 'off' ? <span className='ms-auto text-11px text-t-secondary'>Current</span> : null}
            </span>
          </Menu.Item>
          {row.override === 'off' && row.availability === 'available' ? (
            <Menu.Item key={`${row.id}-once`} onClick={() => void enableOnce(row.id, row.label)} data-testid={`kel-tool-${row.id}-once`}>
              <span className='flex items-center w-full'>
                <span>Allow once (next request only)</span>
              </span>
            </Menu.Item>
          ) : null}
        </Menu.ItemGroup>
      ))}
      <Menu.Item key='reset' disabled={!changed} onClick={() => void resetAll()} data-testid='kel-tools-reset'>
        <span className='text-12px'>{changed ? 'Reset this conversation to your usual settings' : 'This conversation uses your usual settings'}</span>
      </Menu.Item>
    </Menu>
  );

  // Footer crumb (Figma Chat footer 273:9251): icon + label + chevron. The menu opens above its trigger
  // like the Permission menu (273:9273) and scrolls inside a capped height instead of covering the page.
  return (
    <Dropdown
      droplist={items}
      trigger='click'
      position='tl'
      unmountOnExit={false}
      getPopupContainer={() => document.body}
      triggerProps={{ className: 'kel-tools-menu-popup', popupAlign: { top: 8 } }}
    >
      <button type='button' data-testid='kel-tools-pill' disabled={busy} className='kel-shell-crumb kel-tools-crumb'>
        <img src={toolsIcon} alt='' width={14} height={14} />
        <span>{changed ? `Tools · ${changed}` : 'Tools'}</span>
        <img src={chevronIcon} alt='' width={12} height={12} className='kel-shell-crumb__chevron' />
      </button>
    </Dropdown>
  );
};

export default KelToolsControl;
