/**
 * Main-process side of the 2026-09-27 settings audit: ST-06 (chrome-devtools-mcp is pinned),
 * ST-15 (the image-generation server path always follows the app), ST-09 (the saved zoom is
 * applied when the page finishes loading) and the stale chat-folder repair reaching archived chats.
 */
import { describe, expect, it, vi } from 'vitest';

vi.mock('electron', () => ({ BrowserWindow: { getAllWindows: () => [] }, app: { isPackaged: false, getPath: () => '' } }));
vi.mock('@process/utils/initStorage', () => ({ getBuiltinMcpScriptPath: (name: string) => `/app/${name}.js`, ProcessConfig: {} }));
vi.mock('@process/utils/migrateAssistants', () => ({ migrateAssistantsToBackend: vi.fn() }));
vi.mock('@/common/config/configMigration', () => ({
  migrateConfigStorage: vi.fn(),
  migrateLegacyMcpConfigToDb: vi.fn(),
  migrateProviders: vi.fn(),
}));

import { pinChromeDevtoolsArgs, repairImageServerScriptPath } from '@process/utils/runBackendMigrations';
import { CHROME_DEVTOOLS_MCP_VERSION } from '@process/resources/builtinMcp/browserServerPort';
import { applyZoomToWindow, initializeZoomFactor } from '@process/utils/zoom';
import { listConversationsForRepair } from '@process/services/kel/repairWorkspacePaths';

describe('ST-06 chrome-devtools-mcp is pinned', () => {
  it('replaces @latest (and a bare spec) with the pinned version', () => {
    expect(pinChromeDevtoolsArgs(['-y', 'chrome-devtools-mcp@latest'])).toEqual([
      '-y',
      `chrome-devtools-mcp@${CHROME_DEVTOOLS_MCP_VERSION}`,
    ]);
    expect(pinChromeDevtoolsArgs(['-y', 'chrome-devtools-mcp'])).toEqual([
      '-y',
      `chrome-devtools-mcp@${CHROME_DEVTOOLS_MCP_VERSION}`,
    ]);
    expect(CHROME_DEVTOOLS_MCP_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
  });

  it('leaves an already pinned version alone (including one the person chose)', () => {
    expect(pinChromeDevtoolsArgs(['-y', 'chrome-devtools-mcp@0.9.0'])).toBeNull();
    expect(pinChromeDevtoolsArgs(undefined)).toBeNull();
  });
});

describe('ST-15 image-generation server path', () => {
  it('points a stale server at the current script and keeps its env', () => {
    const repaired = repairImageServerScriptPath(
      { transport: { type: 'stdio', command: 'node', args: ['/old/app/builtin-mcp-image-gen.js'], env: { KEY_REF: 'p1' } } },
      { transport: { type: 'stdio', command: 'node', args: ['/app/builtin-mcp-image-gen.js'] } }
    );
    expect(repaired?.transport).toEqual({
      type: 'stdio',
      command: 'node',
      args: ['/app/builtin-mcp-image-gen.js'],
      env: { KEY_REF: 'p1' },
    });
    expect(JSON.parse(repaired!.original_json).mcpServers['aionui-image-generation'].args).toEqual([
      '/app/builtin-mcp-image-gen.js',
    ]);
  });

  it('does nothing when the path already matches', () => {
    const transport = { type: 'stdio' as const, command: 'node', args: ['/app/builtin-mcp-image-gen.js'] };
    expect(repairImageServerScriptPath({ transport: { ...transport, env: { A: 'b' } } }, { transport })).toBeNull();
  });
});

describe('ST-09 saved zoom', () => {
  it('re-applies the saved zoom every time the page finishes loading', () => {
    const handlers: Record<string, () => void> = {};
    const setZoomFactor = vi.fn();
    const win = {
      isDestroyed: () => false,
      webContents: { setZoomFactor, on: (event: string, handler: () => void) => (handlers[event] = handler) },
    };
    initializeZoomFactor(1.1);
    applyZoomToWindow(win as never);
    expect(setZoomFactor).toHaveBeenLastCalledWith(1.1);
    setZoomFactor.mockClear();
    handlers['did-finish-load']();
    expect(setZoomFactor).toHaveBeenCalledWith(1.1);
  });
});

describe('stale chat folders: the repair reads archived chats too', () => {
  it('reads every active chat and every archived page, once each', async () => {
    const conv = (id: string) => ({ type: 'conversation', conversation: { id, extra: { workspace: `C:\\old\\aion-workspaces\\${id}` } } });
    const get = vi.fn(async (route: string) => {
      if (route.startsWith('/api/conversations?')) return { items: [{ id: 'a1', extra: {} }, { id: 'a2', extra: {} }], has_more: false };
      if (route.startsWith('/api/sidebar?'))
        return {
          groups: [
            { scope: { type: 'project', project_id: 'p1' }, items: [conv('x1')], has_more: false },
            { scope: { type: 'chats' }, items: [conv('x2')], has_more: true, next_cursor: 'c1' },
          ],
        };
      if (route.startsWith('/api/sidebar/items?')) {
        const params = new URLSearchParams(route.split('?')[1]);
        expect(params.get('archived')).toBe('true');
        expect(params.get('scope')).toBe('chats');
        return params.get('cursor') === 'c1'
          ? { items: [conv('x3'), conv('x2')], has_more: true, next_cursor: 'c2' }
          : { items: [conv('x4')], has_more: false };
      }
      throw new Error(route);
    });
    const listed = await listConversationsForRepair(get);
    expect(listed.map((item) => item.id)).toEqual(['a1', 'a2', 'x1', 'x2', 'x3', 'x4']);
    expect(get.mock.calls[0][0]).toBe('/api/conversations?limit=10000');
  });

  it('still returns the active chats when the archived read fails', async () => {
    const listed = await listConversationsForRepair(async (route) => {
      if (route.startsWith('/api/conversations?')) return { items: [{ id: 'a1' }] };
      throw new Error('offline');
    });
    expect(listed.map((item) => item.id)).toEqual(['a1']);
  });
});
