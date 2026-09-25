import type { IMcpServer } from '@/common/config/storage';
import { Button, Dropdown, Menu, Popover, Tooltip } from '@arco-design/web-react';
import { Write, DeleteFour, Login, Plug, More } from '@icon-park/react';
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { McpOAuthStatus } from '@/renderer/hooks/mcp/useMcpOAuth';
import FeedbackButton from '@/renderer/components/base/FeedbackButton';
import { formatDateTime } from '@/renderer/services/i18n/format';

/**
 * Human-visual repair: donor-era internal MCP ids stay for compatibility, but the UI speaks Kel —
 * the built-in browser server shows as "Kel Browser" instead of its config id.
 */
const MCP_DISPLAY_NAMES: Record<string, string> = { 'aionui-browser': 'Kel Browser' };

interface McpServerHeaderProps {
  server: IMcpServer;
  isTestingConnection: boolean;
  oauthStatus?: McpOAuthStatus;
  isLoggingIn?: boolean;
  /** Extension-contributed servers are read-only */
  isReadOnly?: boolean;
  onTestConnection: (server: IMcpServer) => void;
  onEditServer: (server: IMcpServer) => void;
  onDeleteServer: (serverId: string) => void;
  onOAuthLogin?: (server: IMcpServer) => void;
}

const formatStatusTimestamp = (timestamp: number | undefined, locale: string): string | null => {
  if (!timestamp) {
    return null;
  }

  return formatDateTime(timestamp, locale);
};

const getStatusPopoverContent = (
  server: IMcpServer,
  locale: string,
  t?: (key: string, options?: Record<string, unknown>) => string
) => {
  if (server.last_test_status !== 'error' && server.last_test_status !== 'connected') {
    return null;
  }

  if (server.last_test_status === 'connected') {
    const checkedAt = formatStatusTimestamp(server.last_connected || server.updated_at, locale);
    return (
      <div className='max-w-300px space-y-2 text-13px leading-20px'>
        <div className='font-medium text-t-primary'>
          {t?.('settings.mcpCheckPassedSummary') || 'Manual check passed'}
        </div>
        {checkedAt ? (
          <div className='text-12px leading-18px text-t-secondary'>{`${t?.('settings.mcpCheckedAtLabel') || 'Checked at:'} ${checkedAt}`}</div>
        ) : null}
        <div className='text-12px leading-18px text-t-secondary opacity-80'>
          {t?.('settings.mcpCheckPurposeHint') ||
            'Used to verify whether the MCP configuration is available. It does not represent the real-time status in the current conversation.'}
        </div>
      </div>
    );
  }

  const checkedAt = formatStatusTimestamp(server.updated_at, locale);

  const reasonText =
    server.builtin && server.name === 'chrome-devtools' && server.transport.type === 'stdio'
      ? t?.('settings.mcpInlineCommandHint', {
          command: server.transport.command,
        }) || `Missing ${server.transport.command}. Install it and test again.`
      : t?.('settings.mcpInlineConfigHint') || 'Configuration may be incorrect. Review the MCP JSON and test again.';

  return (
    <div className='max-w-300px space-y-2 text-13px leading-20px'>
      <div className='font-medium text-t-primary'>{t?.('settings.mcpCheckFailedSummary') || 'Manual check failed'}</div>
      <div className='text-t-primary'>{reasonText}</div>
      {checkedAt ? (
        <div className='text-12px leading-18px text-t-secondary'>{`${t?.('settings.mcpCheckedAtLabel') || 'Checked at:'} ${checkedAt}`}</div>
      ) : null}
    </div>
  );
};

const getStatusText = (
  server: IMcpServer,
  last_test_status?: IMcpServer['last_test_status'],
  oauthStatus?: McpOAuthStatus,
  isTestingConnection?: boolean,
  t?: (key: string, options?: Record<string, unknown>) => string
) => {
  if (isTestingConnection || last_test_status === 'testing' || oauthStatus?.isChecking) {
    return t?.('settings.mcpTesting') || 'testing';
  }

  if (last_test_status === 'error') {
    if (server.builtin && server.name === 'chrome-devtools' && server.transport.type === 'stdio') {
      return (
        t?.('settings.mcpLocalCommandUnavailable', {
          command: server.transport.command,
        }) || `Requires ${server.transport.command} on this machine`
      );
    }
    return t?.('settings.mcpCheckFailedSimple') || 'Failed';
  }

  if (oauthStatus?.needsLogin) {
    return t?.('settings.mcpNeedsLogin') || 'Login required';
  }

  if (last_test_status === 'connected') {
    return t?.('settings.mcpCheckPassedSimple') || 'Manual check passed';
  }

  if (oauthStatus?.isAuthenticated) {
    return t?.('settings.mcpAuthenticated') || 'Authenticated';
  }

  return t?.('settings.mcpDisconnected') || 'Not tested';
};

const supportsOAuth = (server: IMcpServer) =>
  server.transport.type === 'http' || server.transport.type === 'sse' || server.transport.type === 'streamable_http';

const McpServerHeader: React.FC<McpServerHeaderProps> = ({
  server,
  isTestingConnection,
  oauthStatus,
  isLoggingIn,
  isReadOnly,
  onTestConnection,
  onEditServer,
  onDeleteServer,
  onOAuthLogin,
}) => {
  const { t, i18n } = useTranslation();

  const oauthCapable = supportsOAuth(server);
  const needsLogin = oauthCapable && oauthStatus?.needsLogin;
  const statusText = getStatusText(server, server.last_test_status, oauthStatus, isTestingConnection, t);
  const statusPopoverContent = getStatusPopoverContent(server, i18n.language, t);

  const isError = server.last_test_status === 'error';
  const visualStatus =
    isTestingConnection || oauthStatus?.isChecking
      ? 'Checking'
      : isError || needsLogin
        ? isError
          ? 'Check failed'
          : 'Sign in needed'
        : server.last_test_status === 'connected' || oauthStatus?.isAuthenticated
          ? 'Connected'
          : 'Not tested';
  const statusKind = isError
    ? 'error'
    : needsLogin
      ? 'attention'
      : visualStatus === 'Connected'
        ? 'connected'
        : 'muted';

  return (
    <div className='kel-tools-mcp-header flex items-center justify-between group'>
      <div className='kel-tools-mcp-name flex items-center gap-2'>
        <Plug className='kel-tools-mcp-plug' size='14' />
        <span>{MCP_DISPLAY_NAMES[server.name] ?? server.name}</span>
      </div>
      <div className='kel-tools-mcp-status' data-status={statusKind}>
        {statusPopoverContent ? (
          <Popover className='kel-tools-status-popover' content={statusPopoverContent} trigger='hover' position='top'>
            <span>{visualStatus}</span>
          </Popover>
        ) : (
          <Tooltip content={statusText} position='top'>
            <span>{visualStatus}</span>
          </Tooltip>
        )}
      </div>
      <div className='kel-tools-mcp-actions' onClick={(e) => e.stopPropagation()}>
        {isError && <FeedbackButton module='mcp-tools' label='Report issue' />}
        {!isReadOnly && needsLogin && onOAuthLogin && (
          <Button
            size='mini'
            type='primary'
            icon={<Login size={'14'} />}
            title='Sign in'
            loading={isLoggingIn}
            onClick={() => onOAuthLogin(server)}
          >
            Sign in
          </Button>
        )}
        {!isReadOnly && !needsLogin && (
          <Button
            className='kel-tools-mcp-retest'
            size='mini'
            title={t('settings.mcpTestConnection')}
            loading={isTestingConnection}
            onClick={() => onTestConnection(server)}
          >
            Test
          </Button>
        )}
        {!isReadOnly && !server.builtin && (
          <Dropdown
            trigger='click'
            droplist={
              <Menu>
                <Menu.Item key='edit' onClick={() => onEditServer(server)}>
                  <div className='flex items-center gap-2'>
                    <Write size={'14'} />
                    {t('settings.mcpEditServer')}
                  </div>
                </Menu.Item>
                <Menu.Item key='delete' onClick={() => onDeleteServer(server.id)}>
                  <div className='flex items-center gap-2 text-red-500'>
                    <DeleteFour size={'14'} />
                    {t('settings.mcpDeleteServer')}
                  </div>
                </Menu.Item>
              </Menu>
            }
          >
            <Button
              className='kel-tools-mcp-more'
              size='mini'
              icon={<More size={'14'} />}
              aria-label='Server actions'
            />
          </Dropdown>
        )}
      </div>
      <span className='kel-tools-mcp-chevron' aria-hidden='true'>
        ›
      </span>
    </div>
  );
};

export default McpServerHeader;
