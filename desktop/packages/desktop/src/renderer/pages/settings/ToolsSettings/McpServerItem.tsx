import { Button, Collapse } from '@arco-design/web-react';
import React from 'react';
import type { IMcpServer } from '@/common/config/storage';
import McpServerHeader from './McpServerHeader';
import McpServerToolsList from './McpServerToolsList';
import type { McpOAuthStatus } from '@/renderer/hooks/mcp/useMcpOAuth';

interface McpServerItemProps {
  server: IMcpServer;
  isCollapsed: boolean;
  isTestingConnection: boolean;
  oauthStatus?: McpOAuthStatus;
  isLoggingIn?: boolean;
  onToggleCollapse: () => void;
  onTestConnection: (server: IMcpServer) => void;
  onEditServer: (server: IMcpServer) => void;
  onDeleteServer: (serverId: string) => void;
  onOAuthLogin?: (server: IMcpServer) => void;
  onToggleEnabled?: (server: IMcpServer, enabled: boolean) => void;
  isToggling?: boolean;
  /** ST-14: the plain reason the last check failed, when this session ran it. */
  lastError?: string;
}

const McpServerItem: React.FC<McpServerItemProps> = ({
  server,
  isCollapsed,
  isTestingConnection,
  oauthStatus,
  isLoggingIn,
  onToggleCollapse,
  onTestConnection,
  onEditServer,
  onDeleteServer,
  onOAuthLogin,
  onToggleEnabled,
  isToggling,
  lastError,
}) => {
  const checkedAt = server.updated_at
    ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(
        server.updated_at
      )
    : null;

  return (
    <>
      <Collapse
        key={server.id}
        activeKey={isCollapsed ? ['1'] : []}
        onChange={onToggleCollapse}
        className='mb-4 [&_div.arco-collapse-item-header-title]:flex-1'
      >
        <Collapse.Item
          header={
            <McpServerHeader
              server={server}
              isTestingConnection={isTestingConnection}
              oauthStatus={oauthStatus}
              isLoggingIn={isLoggingIn}
              onTestConnection={onTestConnection}
              onEditServer={onEditServer}
              onDeleteServer={onDeleteServer}
              onOAuthLogin={onOAuthLogin}
              onToggleEnabled={onToggleEnabled}
              isToggling={isToggling}
            />
          }
          name='1'
          className={'[&_div.arco-collapse-item-content-box]:py-3'}
        >
          <div className='kel-tools-mcp-mobile-action'>
            <Button size='mini' loading={isTestingConnection} onClick={() => onTestConnection(server)}>
              Check connection
            </Button>
          </div>
          <McpServerToolsList server={server} />
        </Collapse.Item>
      </Collapse>
      {server.last_test_status === 'error' && (
        <div className='kel-tools-mcp-error-detail'>
          <div className='kel-tools-mcp-error-note'>
            <span aria-hidden='true'>⚠</span>
            <span data-testid='mcp-error-reason'>
              {lastError || 'Configuration may be incorrect. Review the MCP JSON and test again.'}
            </span>
          </div>
          {checkedAt && <span className='kel-tools-mcp-checked'>Checked {checkedAt}</span>}
        </div>
      )}
    </>
  );
};

export default McpServerItem;
