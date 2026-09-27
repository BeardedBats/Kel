/**
 * ST-16 — "Import from a CLI" is one Kel list (Figma 313:3911). Back returns to the Tools list
 * instead of opening the donor One-Click Import wizard, and Claude Code's claude.ai-hosted
 * connectors are never offered or shown as connected to Kel.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const getAgentMcpConfigs = vi.fn();
const success = vi.fn();

vi.mock('@/common/adapter/ipcBridge', () => ({ mcpService: { getAgentMcpConfigs: { invoke: () => getAgentMcpConfigs() } } }));
vi.mock('@arco-design/web-react', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  Message: { success: (text: string) => success(text), error: vi.fn() },
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock('@/renderer/components/base/AionModal', () => ({
  default: ({
    header,
    footer,
    children,
  }: {
    header: { title: string; subtitle?: string };
    footer: { render: () => React.ReactNode };
    children: React.ReactNode;
  }) => (
    <div role='dialog' aria-label={header.title}>
      <p>{header.subtitle}</p>
      {children}
      {footer.render()}
    </div>
  ),
}));

import CliImportModal from '@renderer/pages/settings/components/CliImportModal';

const stdio = (command: string) => ({ type: 'stdio' as const, command, args: [] as string[] });
const cliServers = [
  { id: 'a', name: 'github', enabled: true, transport: stdio('gh-mcp'), importable: true, last_test_status: 'connected' },
  { id: 'b', name: 'filesystem', enabled: true, transport: stdio('fs-mcp'), importable: true },
  {
    id: 'c',
    name: 'claude.ai Gmail',
    enabled: true,
    transport: { type: 'http' as const, url: 'https://gmail.mcp.claude.com/mcp' },
    importable: false,
    import_skip_reason: '✓ Connected',
    last_test_status: 'connected',
  },
  { id: 'd', name: 'figma', enabled: true, transport: stdio('figma'), importable: false, import_skip_reason: '! Needs authentication' },
  { id: 'e', name: 'chrome-devtools', enabled: true, transport: stdio('npx'), importable: true },
];

beforeEach(() => {
  getAgentMcpConfigs.mockResolvedValue([{ source: 'claude', servers: cliServers }]);
  success.mockReset();
});
afterEach(cleanup);

describe('Import from a CLI', () => {
  it('lists Claude Code servers with Kel statuses and keeps claude.ai connectors out', async () => {
    render(<CliImportModal visible existingServerNames={['chrome-devtools']} onCancel={vi.fn()} onBatchImport={vi.fn()} />);
    expect(await screen.findByText('Kel found 5 servers in Claude Code.')).toBeTruthy();
    const gmail = screen.getByRole('checkbox', { name: 'claude.ai Gmail' }) as HTMLInputElement;
    expect(gmail.disabled).toBe(true);
    expect(gmail.checked).toBe(false);
    expect(screen.getByText('Belongs to your Claude Code account')).toBeTruthy();
    expect(screen.getByText('Sign in to it in the CLI first')).toBeTruthy();
    expect(screen.getByText('Already added')).toBeTruthy();
    expect(screen.queryByText(/^Connected$/)).toBeNull();
    expect(screen.getByRole('button', { name: 'Import 2' })).toBeTruthy();
    expect(screen.queryByText('settings.mcpOneKeyImport')).toBeNull();
  });

  it('Back returns to the Tools list instead of opening a wizard step', async () => {
    const onCancel = vi.fn();
    render(<CliImportModal visible onCancel={onCancel} onBatchImport={vi.fn()} />);
    await screen.findByText('Kel found 5 servers in Claude Code.');
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('combobox')).toBeNull();
  });

  it('imports the selected servers untested, then closes with a truthful count', async () => {
    const onCancel = vi.fn();
    const onBatchImport = vi.fn(async (servers: Array<{ name: string }>) => servers.map((s) => ({ ...s, id: s.name })));
    render(<CliImportModal visible onCancel={onCancel} onBatchImport={onBatchImport as never} />);
    await screen.findByText('Kel found 5 servers in Claude Code.');
    fireEvent.click(screen.getByRole('checkbox', { name: 'filesystem' }));
    fireEvent.click(screen.getByRole('button', { name: 'Import 2' }));
    await waitFor(() => expect(onCancel).toHaveBeenCalledTimes(1));
    const payload = onBatchImport.mock.calls[0][0] as Array<{ name: string; last_test_status?: string }>;
    expect(payload.map((s) => s.name)).toEqual(['github', 'chrome-devtools']);
    expect(payload.every((s) => s.last_test_status === undefined)).toBe(true);
    expect(success).toHaveBeenCalledWith('Imported 2 servers. Kel is checking them now.');
  });
});
