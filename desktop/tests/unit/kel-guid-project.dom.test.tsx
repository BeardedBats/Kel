import React from 'react';
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';

const bridge = vi.hoisted(() => ({ create: vi.fn(), showOpen: vi.fn() }));
vi.mock('@/common', () => ({
  ipcBridge: {
    conversation: { create: { invoke: bridge.create } },
    dialog: { showOpen: { invoke: bridge.showOpen } },
  },
}));

type Row = { id: string; name: string; root?: string | null; kind: string };
const order: string[] = [];
const engine = { projects: [] as Row[], active: '*', calls: [] as Array<Record<string, unknown>> };
const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
  if (route !== '/api/project' || !body) return {};
  engine.calls.push(body);
  order.push(String(body.action));
  if (body.action === 'list') return { projects: engine.projects, active: engine.active };
  if (body.action === 'set_active') {
    engine.active = String(body.id);
    return { active: engine.active };
  }
  if (body.action === 'for_folder') {
    const row = { id: 'garden', name: 'garden', root: String(body.root), kind: 'user' };
    engine.projects = [...engine.projects, row];
    return { id: row.id };
  }
  return {};
});

beforeEach(() => {
  engine.projects = [
    { id: 'default', name: 'General', root: null, kind: 'general' },
    { id: 'site', name: 'Website', root: 'C:\\fixtures\\site', kind: 'user' },
  ];
  engine.active = 'site';
  engine.calls = [];
  order.length = 0;
  bridge.create.mockReset();
  bridge.showOpen.mockReset();
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  resetProjectsForTests();
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const sendDeps = (projectId: string, dir: string, navigate: (path: string) => Promise<void>) => ({
  input: 'hello',
  setInput: vi.fn(),
  files: [],
  setFiles: vi.fn(),
  dir,
  projectId,
  setLoading: vi.fn(),
  loading: false,
  selectedAssistantId: 'kel',
  selectedAssistantBackend: 'acp',
  selectedMode: '',
  selectedAcpModel: null,
  current_model: undefined,
  guidDisabledBuiltinSkills: undefined,
  guidEnabledSkills: undefined,
  availableMcpServers: [],
  selectedMcpServerIds: undefined,
  isGoogleAuth: false,
  setMentionOpen: vi.fn(),
  setMentionQuery: vi.fn(),
  setMentionSelectorOpen: vi.fn(),
  setMentionActiveIndex: vi.fn(),
  navigate: navigate as never,
  t: ((key: string) => key) as never,
  localeKey: 'en-US',
});

describe('New chats start in the active project (D-54)', () => {
  it('sends the project with the new chat and binds it before the chat opens', async () => {
    const { useGuidSend } = await import('@renderer/pages/guid/hooks/useGuidSend');
    bridge.create.mockImplementation(async () => {
      order.push('create');
      return { id: 'donor-1' };
    });
    const navigate = vi.fn(async (path: string) => {
      order.push(`navigate ${path}`);
    });
    const { result } = renderHook(() => useGuidSend(sendDeps('site', 'C:\\fixtures\\site', navigate)));
    await act(async () => {
      await result.current.handleSend();
    });
    const extra = bridge.create.mock.calls[0][0].extra;
    expect(extra).toMatchObject({ kel_project_id: 'site', workspace: 'C:\\fixtures\\site', custom_workspace: true });
    expect(engine.calls).toContainEqual({ action: 'bind', donor: 'donor-1', project: 'site' });
    expect(order).toEqual(['create', 'bind', 'navigate /conversation/donor-1']);
  });

  it('still opens the chat when the binding cannot be recorded', async () => {
    const { useGuidSend } = await import('@renderer/pages/guid/hooks/useGuidSend');
    bridge.create.mockResolvedValue({ id: 'donor-2' });
    request.mockImplementationOnce(async () => {
      throw new Error('engine away');
    });
    const navigate = vi.fn(async () => undefined);
    const { result } = renderHook(() => useGuidSend(sendDeps('default', '', navigate)));
    await act(async () => {
      await result.current.handleSend();
    });
    expect(bridge.create.mock.calls[0][0].extra).toMatchObject({ kel_project_id: 'default', workspace: '', custom_workspace: false });
    expect(navigate).toHaveBeenCalledWith('/conversation/donor-2');
  });

  it('takes the folder and project from the active project', async () => {
    const { useGuidInput } = await import('@renderer/pages/guid/hooks/useGuidInput');
    const { result } = renderHook(() => useGuidInput({ locationState: null }));
    await waitFor(() => expect(result.current.projectId).toBe('site'));
    expect(result.current.dir).toBe('C:\\fixtures\\site');
  });

  it('uses General (no folder) for new chats while all projects are shown', async () => {
    engine.active = '*';
    const { useGuidInput } = await import('@renderer/pages/guid/hooks/useGuidInput');
    const { result } = renderHook(() => useGuidInput({ locationState: null }));
    await waitFor(() => expect(result.current.projectId).toBe('default'));
    expect(result.current.dir).toBe('');
  });

  it('opens Home "in a folder" by making that folder’s project active', async () => {
    const { useGuidInput } = await import('@renderer/pages/guid/hooks/useGuidInput');
    const { result } = renderHook(() => useGuidInput({ locationState: { workspace: 'C:\\fixtures\\garden' } }));
    await waitFor(() => expect(result.current.projectId).toBe('garden'));
    expect(engine.calls).toContainEqual({ action: 'for_folder', root: 'C:\\fixtures\\garden' });
    expect(engine.calls).toContainEqual({ action: 'set_active', id: 'garden' });
    expect(result.current.dir).toBe('C:\\fixtures\\garden');
  });

  it('keeps the header chip and the composer footer on the same project', async () => {
    const { default: ShellWorkspaceLink } = await import('@renderer/components/kel/ShellWorkspaceLink');
    const { default: GuidWorkspaceFootnote } = await import('@renderer/pages/guid/components/GuidWorkspaceFootnote');
    render(
      <MemoryRouter>
        <ShellWorkspaceLink />
        <GuidWorkspaceFootnote />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByTestId('kel-project-chip').textContent).toBe('Website'));
    expect(within(screen.getByTestId('kel-composer-project')).getByText('Website')).toBeTruthy();

    // Choosing General in the footer changes the header too.
    fireEvent.click(screen.getByTestId('workspace-selector-btn'));
    fireEvent.click(within(await screen.findByTestId('kel-desktop-project-menu')).getByRole('button', { name: 'General' }));
    await waitFor(() => expect(screen.getByTestId('kel-project-chip').textContent).toBe('General'));
    expect(within(screen.getByTestId('kel-composer-project')).getByText('General')).toBeTruthy();
    expect(engine.calls).toContainEqual({ action: 'set_active', id: 'default' });
  });

  it('turns a browsed folder into the active project from the composer', async () => {
    bridge.showOpen.mockResolvedValue(['C:\\fixtures\\garden']);
    const { default: GuidWorkspaceFootnote } = await import('@renderer/pages/guid/components/GuidWorkspaceFootnote');
    render(<GuidWorkspaceFootnote />);
    await waitFor(() => expect(within(screen.getByTestId('kel-composer-project')).getByText('Website')).toBeTruthy());
    fireEvent.click(screen.getByTestId('workspace-selector-btn'));
    fireEvent.click(await screen.findByRole('button', { name: 'Choose a different folder' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'set_active', id: 'garden' }));
    expect(engine.calls).toContainEqual({ action: 'for_folder', root: 'C:\\fixtures\\garden' });
    expect(await within(screen.getByTestId('kel-composer-project')).findByText('garden')).toBeTruthy();
  });
});
