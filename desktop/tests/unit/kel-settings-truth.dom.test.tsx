/**
 * Settings truth & polish (2026-09-27 audit): ST-05 keep-awake live state, ST-06 per-server
 * switch and "Last check passed" wording, ST-07/10/11/12 Connections, ST-13 backup dialog,
 * ST-17 empty Paste JSON, ST-18 Escape closes the Add MCP server menu.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const bridge = vi.hoisted(() => ({
  getKeepAwake: vi.fn(),
  setKeepAwake: vi.fn(),
  showOpen: vi.fn(),
  showItemInFolder: vi.fn(),
}));

vi.mock('@/common', () => ({
  ipcBridge: {
    systemSettings: {
      getKeepAwake: { invoke: bridge.getKeepAwake },
      setKeepAwake: { invoke: bridge.setKeepAwake },
    },
    dialog: { showOpen: { invoke: bridge.showOpen } },
    shell: { showItemInFolder: { invoke: bridge.showItemInFolder } },
  },
}));

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock('@arco-design/web-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@arco-design/web-react')>();
  return { ...actual, Message: { ...actual.Message, success: toast.success, error: toast.error } };
});

// CodeMirror does not lay out in jsdom; a textarea stands in with the same value/onChange contract.
vi.mock('@uiw/react-codemirror', () => ({
  default: ({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) => (
    <textarea aria-label='MCP JSON' value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
  ),
}));
// A stable `t` (the real one is stable once i18n is initialised; an uninitialised one is not).
const i18n = vi.hoisted(() => {
  const t = (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key;
  return { t, value: { t, i18n: { language: 'en-US' } } };
});
vi.mock('react-i18next', () => ({ useTranslation: () => i18n.value }));
vi.mock('@/renderer/hooks/context/ThemeContext', () => ({ useThemeContext: () => ({ theme: 'dark' }) }));
vi.mock('@/renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));

import { KelKeepAwakeCard } from '@renderer/components/kel/KelKeepAwakeCard';
import McpServerHeader, { formatLastCheckTime, getMcpVisualStatus } from '@renderer/pages/settings/ToolsSettings/McpServerHeader';
import SettingsCreateMenu from '@renderer/components/base/SettingsCreateMenu';
import JsonImportModal from '@renderer/pages/settings/components/JsonImportModal';
import { KelDataCard, BACKUP_EXCLUDES } from '@renderer/components/kel/KelDataCard';
import {
  connectionRowStatus,
  draftFromKnownService,
  knownServiceCredentialText,
  purposePlaceholder,
} from '@renderer/pages/kel/connections';
import { plainFailureToast } from '@renderer/hooks/mcp/useMcpConnection';
import type { IMcpServer } from '@/common/config/storage';
import type { KelKnownService } from '@renderer/components/kel/kelApi';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('ST-05 keep awake reports the live state (JR-48)', () => {
  it('shows Active only when the main process holds the computer awake', async () => {
    bridge.getKeepAwake.mockResolvedValue({ enabled: true, active: true });
    render(<KelKeepAwakeCard compact />);
    await waitFor(() => expect(screen.getByTestId('kel-keep-awake-state').textContent).toBe('Active'));
  });

  it('says so when the switch is on but nothing holds the computer awake', async () => {
    bridge.getKeepAwake.mockResolvedValue({ enabled: true, active: false });
    render(<KelKeepAwakeCard compact />);
    await waitFor(() => expect(screen.getByTestId('kel-keep-awake-state').textContent).toMatch(/^Not active/));
  });

  it('shows Off when switched off', async () => {
    bridge.getKeepAwake.mockResolvedValue({ enabled: false, active: false });
    render(<KelKeepAwakeCard compact />);
    await waitFor(() => expect(screen.getByTestId('kel-keep-awake-state').textContent).toBe('Off'));
    expect(screen.getByText(/Stops this computer from sleeping/)).toBeTruthy();
  });
});

const server = (over: Partial<IMcpServer> = {}): IMcpServer => ({
  id: 's1',
  name: 'weather',
  enabled: true,
  transport: { type: 'stdio', command: 'npx', args: [] },
  created_at: 1,
  updated_at: 1,
  original_json: '{}',
  ...over,
});

describe('ST-06 MCP server rows', () => {
  it('says when the last check passed instead of claiming a live connection', () => {
    const now = new Date(2026, 8, 27, 18, 0);
    const at = new Date(2026, 8, 27, 15, 42).getTime();
    expect(getMcpVisualStatus(server({ last_test_status: 'connected', last_connected: at }), {}, now).label).toBe(
      'Last check passed 3:42 PM'
    );
    expect(formatLastCheckTime(new Date(2026, 8, 20, 9, 0).getTime(), now)).toBe('Sep 20');
    expect(getMcpVisualStatus(server({ enabled: false, last_test_status: 'connected' })).label).toBe('Off');
    expect(getMcpVisualStatus(server({ last_test_status: 'error' })).label).toBe('Check failed');
  });

  it('has an On/Off switch per server with an accessible name', () => {
    const onToggleEnabled = vi.fn();
    render(
      <McpServerHeader
        server={server({ name: 'aionui-browser', builtin: true, enabled: false })}
        isTestingConnection={false}
        onTestConnection={vi.fn()}
        onEditServer={vi.fn()}
        onDeleteServer={vi.fn()}
        onToggleEnabled={onToggleEnabled}
      />
    );
    const toggle = screen.getByRole('switch', { name: 'Use Kel Browser' });
    fireEvent.click(toggle);
    expect(onToggleEnabled).toHaveBeenCalledWith(expect.objectContaining({ name: 'aionui-browser' }), true);
  });

  it('ST-14: a failed check reads as one plain sentence with the reason', () => {
    expect(plainFailureToast('aionui-browser', 'Kel could not reach the MCP server.')).toBe(
      "Kel Browser didn't pass its check: Kel could not reach the MCP server."
    );
  });
});

describe('ST-18 the Add MCP server menu closes on Escape', () => {
  it('opens on click and closes on Escape', async () => {
    render(
      <SettingsCreateMenu label='Add MCP server' data-testid='add-mcp' extraActions={[{ key: 'json', label: 'Paste JSON', onClick: vi.fn() }]} />
    );
    const button = screen.getByTestId('add-mcp');
    fireEvent.click(button);
    await waitFor(() => expect(button.getAttribute('aria-expanded')).toBe('true'));
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(button.getAttribute('aria-expanded')).toBe('false'));
  });
});

describe('ST-17 Paste JSON', () => {
  it('starts empty with a placeholder and enables Add server only for valid JSON', async () => {
    const onSubmit = vi.fn();
    render(<JsonImportModal visible onCancel={vi.fn()} onSubmit={onSubmit} />);
    const field = screen.getByLabelText('MCP JSON') as HTMLTextAreaElement;
    expect(field.value).toBe('');
    expect(field.placeholder).toContain('mcpServers');
    const add = () => screen.getByTestId('mcp-json-submit') as HTMLButtonElement;
    expect(add().disabled).toBe(true);
    fireEvent.change(field, { target: { value: '{ "mcpServers": ' } });
    await waitFor(() => expect(add().disabled).toBe(true));
    fireEvent.change(field, { target: { value: '{ "mcpServers": { "w": { "command": "npx", "args": ["-y", "w"] } } }' } });
    await waitFor(() => expect(add().disabled).toBe(false));
  });
});

const drive: KelKnownService = {
  id: 'google-drive',
  name: 'Google Drive',
  kind: 'oauth',
  base_url: 'https://www.googleapis.com/drive/v3',
  auth_method: 'header',
  auth_header: 'Authorization',
  auth_prefix: 'Bearer ',
  docs_url: '',
  test_endpoint: '',
  credential:
    'your own Google sign-in app — an OAuth client ID and secret of the "Desktop app" type from Google Cloud Console. Then you choose Connect, sign in with Google in your browser, and Kel keeps the token',
  source: 'documented',
  note: 'Kel can see the names and types of your Drive files — never their contents — and changes nothing. Before Connect works, save the client ID as a credential named client_id and the secret as one named client_secret.',
};

describe('Connections (ST-07, ST-10, ST-11, ST-12)', () => {
  it('ST-10: Google Drive says plainly what it needs, in the engine’s words', () => {
    expect(knownServiceCredentialText(drive)).toBe(drive.credential);
    expect(knownServiceCredentialText(drive)).toMatch(/OAuth client ID and secret/);
    expect(knownServiceCredentialText({ credential: 'a key from your account.' })).toBe('a key from your account');
  });

  it('ST-11: a template note never lands in the purpose field', () => {
    const draft = draftFromKnownService(drive);
    expect(draft.notes).toBe('');
    expect(draft.service_hint).toBe(drive.note);
    expect(draft.service_hint).toMatch(/never their contents/);
  });

  it('ST-12: the purpose placeholder fits the service', () => {
    expect(purposePlaceholder('google-drive')).toBe('e.g. see which files are in my Drive');
    expect(purposePlaceholder(undefined)).toMatch(/^e\.g\./);
  });

  it('ST-07: the row shows the recorded check result', () => {
    expect(connectionRowStatus({ has_credentials: false, last_test_state: null, last_test_at: null }).label).toBe(
      'Needs a credential'
    );
    expect(connectionRowStatus({ has_credentials: true, last_test_state: 'refused', last_test_at: 5 })).toEqual({
      label: 'Credential refused',
      state: 'check-failed',
    });
    expect(connectionRowStatus({ has_credentials: true, last_test_state: 'ok', last_test_at: 5 }).label).toBe('Working');
    expect(connectionRowStatus({ has_credentials: true, last_test_state: null, last_test_at: null }).label).toBe(
      'Ready — not tested'
    );
  });
});

describe('ST-13 backup dialog', () => {
  it('states what is included and excluded, picks a folder, and closes after a backup', async () => {
    const request = vi.fn(async (route: string, body: { action?: string }) => {
      if (route === '/api/data-path') return { root: 'C:\\Kel\\Data', database: 'C:\\Kel\\Data\\engine\\kel.sqlite3' };
      if (body.action === 'create') return { folder: 'D:\\Backups\\Kel-Backup-20260927-120000', summary: { conversations: 3 }, skipped: [] };
      return {};
    });
    (window as unknown as { kelAPI: unknown }).kelAPI = { request };
    bridge.showOpen.mockResolvedValue(['D:\\Backups']);
    render(<KelDataCard />);
    fireEvent.click(screen.getByTestId('backup-now'));
    expect((await screen.findByTestId('backup-excludes')).textContent).toBe(BACKUP_EXCLUDES);
    expect(screen.getByTestId('backup-includes').textContent).toMatch(/chats, projects/);
    const folder = screen.getByLabelText('Backup folder') as HTMLInputElement;
    expect(folder.readOnly).toBe(true);
    fireEvent.click(screen.getByTestId('backup-choose-folder'));
    await waitFor(() => expect(folder.value).toBe('D:\\Backups'));
    const confirm = screen.getAllByRole('button', { name: 'Back up now' }).find((b) => b.closest('.arco-modal-footer'));
    await act(async () => {
      fireEvent.click(confirm as HTMLElement);
    });
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/backup', { action: 'create', target: 'D:\\Backups' }));
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(expect.objectContaining({ content: expect.stringContaining('Kel-Backup-20260927-120000 (3 chats)') }))
    );
    await waitFor(() => expect(screen.queryByTestId('backup-dialog')).toBeNull());
  });
});
