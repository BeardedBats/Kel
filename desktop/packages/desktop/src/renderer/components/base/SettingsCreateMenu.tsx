/**
 * Kel settings "create / add" menu — the shared action-neutral entry point used
 * across settings surfaces.
 *
 * Clicking the button only opens a dropdown; the caller decides which actions it
 * offers:
 *   - "via chat" (only when the caller supplies `onChat`, e.g. the scheduled-tasks
 *     page which prefills Kel's own composer),
 *   - extra actions (imports etc.),
 *   - the manual action.
 *
 * There is deliberately no built-in chat target: the donor build handed the chat
 * item to its bundled assistant, which is outside Kel's single-assistant scope.
 */
import { Button, Dropdown, Menu } from '@arco-design/web-react';
import { Down } from '@icon-park/react';
import classNames from 'classnames';
import React, { useCallback } from 'react';

export type SettingsCreateExtraAction = {
  key: string;
  label: string;
  onClick: () => void;
};

export type SettingsCreateMenuProps = {
  /** Button label in its plain, action-neutral form — e.g. "Add model". */
  label: string;
  /** Menu label for the "via chat" item; the item shows only when `onChat` is set. */
  chatLabel?: string;
  /** Caller-provided chat handoff (e.g. prefill Kel's composer). */
  onChat?: () => void;
  /** The manual action and its menu label. */
  onManual?: () => void;
  manualLabel?: string;
  /** Extra menu actions inserted before the manual item (e.g. MCP imports). */
  extraActions?: SettingsCreateExtraAction[];
  type?: 'primary' | 'outline' | 'secondary' | 'default';
  size?: 'mini' | 'small' | 'default' | 'large';
  className?: string;
  'data-testid'?: string;
};

const CHAT_KEY = '__chat__';
const MANUAL_KEY = '__manual__';

const SettingsCreateMenu: React.FC<SettingsCreateMenuProps> = ({
  label,
  chatLabel,
  onChat,
  onManual,
  manualLabel,
  extraActions,
  type = 'primary',
  size = 'small',
  className,
  ['data-testid']: testId,
}) => {
  const handleSelect = useCallback(
    (key: string) => {
      if (key === CHAT_KEY) {
        onChat?.();
      } else if (key === MANUAL_KEY) {
        onManual?.();
      } else {
        extraActions?.find((action) => action.key === key)?.onClick();
      }
    },
    [onChat, onManual, extraActions]
  );

  const droplist = (
    <Menu onClickMenuItem={handleSelect}>
      {onChat ? (
        <Menu.Item key={CHAT_KEY} data-testid={testId ? `${testId}-chat` : undefined}>
          {chatLabel}
        </Menu.Item>
      ) : null}
      {extraActions?.map((action) => (
        <Menu.Item key={action.key} data-testid={testId ? `${testId}-${action.key}` : undefined}>
          {action.label}
        </Menu.Item>
      ))}
      {onManual && manualLabel ? (
        <Menu.Item key={MANUAL_KEY} data-testid={testId ? `${testId}-manual` : undefined}>
          {manualLabel}
        </Menu.Item>
      ) : null}
    </Menu>
  );

  return (
    <Dropdown trigger='click' droplist={droplist} position='br'>
      <Button
        type={type}
        size={size}
        className={classNames('!h-32px !rounded-8px !px-14px', className)}
        data-testid={testId}
      >
        <span className='flex items-center gap-6px'>
          {label}
          <Down theme='outline' size={14} fill='currentColor' />
        </span>
      </Button>
    </Dropdown>
  );
};

export default SettingsCreateMenu;
