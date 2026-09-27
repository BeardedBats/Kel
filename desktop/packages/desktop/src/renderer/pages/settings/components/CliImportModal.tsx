import type { IMcpServer, IMcpTool } from '@/common/config/storage';
import { mcpService } from '@/common/adapter/ipcBridge';
import { Button, Message, Spin } from '@arco-design/web-react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AionModal from '@/renderer/components/base/AionModal';

/**
 * Tools → Add MCP server → "Import from a CLI" (Figma 313:3911): one list of the servers Claude Code
 * knows about, with Back and "Import N". Back returns to the Tools list; there is no multi-step
 * wizard (ST-16). A CLI's own connection state is never shown as Kel's: imported servers start
 * untested and Kel checks them itself, and claude.ai-hosted connectors are labelled as belonging to
 * Claude Code instead of being offered for import.
 */

type DetectedMcpServer = IMcpServer & {
  importable: boolean;
  import_skip_reason?: string;
};

const CLI = { backend: 'claude', name: 'Claude Code' } as const;

const normalizeImportSkipReason = (reason: string | undefined) =>
  reason
    ?.trim()
    .replace(/^[✓✗!•\-*✔✘:[\]\s]+/, '')
    .trim();

/** Connectors hosted by claude.ai belong to the user's Claude account, not to a config Kel can run. */
export const isClaudeAiConnector = (server: Pick<IMcpServer, 'name' | 'transport'>): boolean => {
  if (/^claude\.ai\b/i.test(server.name.trim())) return true;
  if (server.transport.type === 'stdio') return false;
  try {
    const host = new URL(server.transport.url).hostname.toLowerCase();
    return host === 'claude.ai' || host.endsWith('.claude.ai') || host.endsWith('.claude.com');
  } catch {
    return false;
  }
};

const unsupportedReason = (reason: string | undefined, t: ReturnType<typeof useTranslation>['t']) => {
  const normalized = normalizeImportSkipReason(reason);
  if (!normalized || normalized === 'Connected') return undefined;
  if (normalized === 'Plugin-managed MCP') return t('settings.mcpImportSkippedPluginManaged');
  if (normalized === 'Disabled') return t('settings.mcpImportSkippedDisabled');
  if (normalized === 'Needs authentication') return t('settings.mcpImportSkippedNeedsAuth');
  if (normalized === 'Disconnected' || normalized === 'Failed to connect') return t('settings.mcpImportSkippedUnavailable');
  return normalized;
};

export const toImportPayload = (server: DetectedMcpServer): Omit<IMcpServer, 'id' | 'created_at' | 'updated_at'> => {
  const serverConfig: Record<string, string | string[] | Record<string, string>> = {
    description: server.description,
  };
  if (server.transport.type === 'stdio') {
    serverConfig.command = server.transport.command;
    if (server.transport.args?.length) serverConfig.args = server.transport.args;
    if (server.transport.env && Object.keys(server.transport.env).length) serverConfig.env = server.transport.env;
  } else {
    serverConfig.type = server.transport.type;
    serverConfig.url = server.transport.url;
    if (server.transport.headers && Object.keys(server.transport.headers).length) {
      serverConfig.headers = server.transport.headers;
    }
  }
  return {
    name: server.name,
    description: server.description,
    enabled: server.enabled,
    transport: server.transport,
    // Not the CLI's status: Kel has not checked this server yet.
    last_test_status: undefined,
    tools: (server.tools || []) as IMcpTool[],
    original_json: JSON.stringify({ mcpServers: { [server.name]: serverConfig } }, null, 2),
  };
};

interface CliImportModalProps {
  visible: boolean;
  existingServerNames?: string[];
  onCancel: () => void;
  onBatchImport?: (
    servers: Omit<IMcpServer, 'id' | 'created_at' | 'updated_at'>[]
  ) => Promise<IMcpServer[] | void> | IMcpServer[] | void;
}

const CliImportModal: React.FC<CliImportModalProps> = ({ visible, existingServerNames = [], onCancel, onBatchImport }) => {
  const { t } = useTranslation();
  const [servers, setServers] = useState<DetectedMcpServer[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const existing = useMemo(() => new Set(existingServerNames), [existingServerNames]);

  const importable = useCallback(
    (server: DetectedMcpServer) =>
      !existing.has(server.name) &&
      !isClaudeAiConnector(server) &&
      (server.importable || normalizeImportSkipReason(server.import_skip_reason) === 'Connected'),
    [existing]
  );

  const importableServers = useMemo(() => servers.filter(importable), [servers, importable]);
  const ordered = useMemo(
    () => [...importableServers, ...servers.filter((server) => !importableServers.includes(server))],
    [importableServers, servers]
  );
  const toImport = importableServers.filter((server) => selected.has(server.name));

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    setServers([]);
    setSelected(new Set());
    setSubmitting(false);
    setLoading(true);
    void mcpService.getAgentMcpConfigs
      .invoke()
      .then((configs) => {
        if (cancelled) return;
        const found = (configs.find((config) => config.source === CLI.backend)?.servers ?? []) as DetectedMcpServer[];
        setServers(found);
        setSelected(new Set(found.map((server) => server.name)));
      })
      .catch((error) => {
        if (!cancelled) console.error('Failed to read MCP servers from the CLI:', error);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [visible]);

  const handleImport = async () => {
    if (submitting || !onBatchImport || toImport.length === 0) return;
    setSubmitting(true);
    try {
      const result = await onBatchImport(toImport.map(toImportPayload));
      const count = Array.isArray(result) ? result.length : 0;
      // The import hook already explains a failure; only a real import closes the sheet.
      if (count > 0) {
        Message.success(`Imported ${count} ${count === 1 ? 'server' : 'servers'}. Kel is checking ${count === 1 ? 'it' : 'them'} now.`);
        onCancel();
      }
    } catch (error) {
      console.error('Failed to import MCP servers:', error);
    } finally {
      setSubmitting(false);
    }
  };

  if (!visible) return null;

  const statusFor = (server: DetectedMcpServer) => {
    if (existing.has(server.name)) return { text: 'Already added', state: 'muted' };
    if (isClaudeAiConnector(server)) return { text: `Belongs to your ${CLI.name} account`, state: 'muted' };
    if (!importable(server)) {
      const needsAuth = normalizeImportSkipReason(server.import_skip_reason) === 'Needs authentication';
      return needsAuth
        ? { text: 'Sign in to it in the CLI first', state: 'auth' }
        : { text: unsupportedReason(server.import_skip_reason, t) || 'Cannot import', state: 'muted' };
    }
    return selected.has(server.name) ? { text: 'Will import', state: 'selected' } : { text: 'Not selected', state: 'muted' };
  };

  return (
    <AionModal
      variant='standard'
      className='kel-tools-cli-modal'
      header={{
        title: 'Import from a CLI',
        subtitle: loading
          ? undefined
          : `Kel found ${servers.length} ${servers.length === 1 ? 'server' : 'servers'} in ${CLI.name}.`,
        showClose: false,
      }}
      visible={visible}
      onCancel={onCancel}
      footer={{
        render: () => (
          <div className='kel-tools-cli-actions'>
            <Button onClick={onCancel}>Back</Button>
            <Button
              type='primary'
              onClick={() => void handleImport()}
              loading={submitting}
              disabled={loading || submitting || toImport.length === 0}
            >
              Import {toImport.length}
            </Button>
          </div>
        ),
      }}
      style={{ width: 600 }}
    >
      <div className='flex min-h-0 flex-col'>
        {loading ? (
          <div className='py-8'>
            <div className='flex items-center gap-3 bg-fill-1 rounded-lg p-4'>
              <Spin size={20} />
              <div className='text-t-secondary text-sm'>{t('settings.mcpLoadingTools')}</div>
            </div>
          </div>
        ) : servers.length > 0 ? (
          <div className='kel-tools-cli-list'>
            {ordered.map((server) => {
              const selectable = importable(server);
              const checked = selectable && selected.has(server.name);
              const status = statusFor(server);
              return (
                <label className='kel-tools-cli-row' key={server.id || server.name}>
                  <input
                    type='checkbox'
                    checked={checked}
                    disabled={!selectable}
                    aria-label={server.name}
                    onChange={(event) =>
                      setSelected((previous) => {
                        const next = new Set(previous);
                        if (event.target.checked) next.add(server.name);
                        else next.delete(server.name);
                        return next;
                      })
                    }
                  />
                  <span className='kel-tools-cli-row__name'>{server.name}</span>
                  <strong data-state={status.state}>{status.text}</strong>
                </label>
              );
            })}
          </div>
        ) : (
          <div className='text-center py-8 text-t-secondary'>{t('settings.mcpNoServersFound')}</div>
        )}
      </div>
    </AionModal>
  );
};

export default CliImportModal;
