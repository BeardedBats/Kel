import React from 'react';
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import { bindToSourceProject, resetProjectsForTests, useConversationProject } from '@renderer/components/kel/activeProject';

vi.mock('@/common', () => ({ ipcBridge: { dialog: { showOpen: { invoke: vi.fn() } } } }));

type Row = { id: string; name: string; root?: string | null; kind: string; archived?: number | null; conversations?: number };
const engine = {
  projects: [] as Row[],
  active: '*',
  chatProject: { project: 'site', pending: false } as Record<string, unknown>,
  calls: [] as Array<Record<string, unknown>>,
};

const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
  if (route !== '/api/project' || !body) return {};
  engine.calls.push(body);
  switch (body.action) {
    case 'list':
      return { projects: engine.projects, active: engine.active };
    case 'set_active':
      engine.active = String(body.id);
      return { active: engine.active };
    case 'of':
      return engine.chatProject;
    case 'create': {
      const row = { id: 'new-one', name: String(body.name), root: (body.root as string) ?? null, kind: 'user' };
      engine.projects = [...engine.projects, row];
      return { id: row.id };
    }
    default:
      return {};
  }
});

const Location = () => {
  const location = useLocation();
  return <output data-testid='route'>{JSON.stringify({ path: location.pathname, state: location.state })}</output>;
};

const renderChip = (props: { conversationId?: string } = {}) =>
  render(
    <MemoryRouter initialEntries={['/projects/knowledge']}>
      <ShellWorkspaceLink {...props} />
      <Location />
    </MemoryRouter>
  );

beforeEach(() => {
  engine.projects = [
    { id: 'default', name: 'General', root: null, kind: 'general', conversations: 45 },
    { id: 'site', name: 'Website', root: 'C:\\fixtures\\site', kind: 'user' },
    { id: 'old', name: 'Old thing', root: null, kind: 'user', archived: 1700000000 },
    { id: 'acp-temp-1a2b', name: 'acp-temp-1a2b', root: 'C:\\Temp\\acp-temp-1a2b', kind: 'system' },
  ];
  engine.active = '*';
  engine.chatProject = { project: 'site', pending: false };
  engine.calls = [];
  request.mockClear();
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  localStorage.clear();
  resetProjectsForTests();
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Project switcher (D-54)', () => {
  it('names "All projects" when none is active and lists only live projects', async () => {
    renderChip();
    const chip = await screen.findByRole('button', { name: /All projects/ });
    fireEvent.click(chip);
    const menu = await screen.findByRole('dialog', { name: 'Projects' });
    expect(menu.textContent).toContain('General');
    expect(menu.textContent).toContain('Website');
    expect(menu.textContent).not.toContain('Old thing');
    expect(menu.textContent).not.toContain('acp-temp');
    expect(within(menu).getByRole('button', { name: 'All projects' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: 'New project' })).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/Workspace/);
  });

  it('makes the chosen project active in the engine and shows its name', async () => {
    renderChip();
    fireEvent.click(await screen.findByRole('button', { name: /All projects/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'Website' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'set_active', id: 'site' }));
    expect(await screen.findByRole('button', { name: /Website/ })).toBeTruthy();
    expect(screen.queryByRole('dialog', { name: 'Projects' })).toBeNull();
    // VIS-11: the chip's tooltip names the project, not its folder path.
    await waitFor(() => expect(screen.getByTestId('kel-project-chip').getAttribute('title')).toBe('Website'));
  });

  it('opens All projects from "Manage projects"', async () => {
    renderChip();
    fireEvent.click(await screen.findByRole('button', { name: /All projects/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'Manage projects' }));
    expect(JSON.parse(screen.getByTestId('route').textContent!).path).toBe('/projects/list');
  });

  it('creates a project and makes it active', async () => {
    renderChip();
    fireEvent.click(await screen.findByRole('button', { name: /All projects/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'New project' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Garden' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'set_active', id: 'new-one' }));
    expect(engine.calls).toContainEqual({ action: 'create', name: 'Garden', root: undefined });
    expect(await screen.findByRole('button', { name: /Garden/ })).toBeTruthy();
  });

  it('in a chat, shows that chat’s project and starts new chats elsewhere without moving it', async () => {
    engine.active = 'default';
    renderChip({ conversationId: 'chat-1' });
    const chip = await screen.findByRole('button', { name: /Website/ });
    expect(engine.calls).toContainEqual({ action: 'of', donor: 'chat-1' });
    fireEvent.click(chip);
    const menu = await screen.findByRole('dialog', { name: 'Projects' });
    expect(within(menu).getByRole('button', { name: 'Website' }).getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(within(menu).getByRole('button', { name: 'General' }));
    await waitFor(() => expect(JSON.parse(screen.getByTestId('route').textContent!).path).toBe('/guid'));
    expect(engine.calls).toContainEqual({ action: 'set_active', id: 'default' });
    expect(JSON.parse(screen.getByTestId('route').textContent!).state.projectNote).toBe(
      'New chats start in General. This chat stays in Website.'
    );
    expect(engine.calls.some((call) => call.action === 'bind')).toBe(false);
  });

  it('marks an archived chat project', async () => {
    engine.chatProject = { project: 'old', pending: false };
    renderChip({ conversationId: 'chat-2' });
    expect(await screen.findByRole('button', { name: /Old thing \(archived\)/ })).toBeTruthy();
  });

  it('imports the old per-device choice once, only for a live project the person made', async () => {
    localStorage.setItem('kel.activeWorkspace_v1', JSON.stringify({ id: 'site', name: 'Website', root: 'C:\\fixtures\\site' }));
    renderChip();
    expect(await screen.findByRole('button', { name: /Website/ })).toBeTruthy();
    expect(engine.calls).toContainEqual({ action: 'set_active', id: 'site' });
    expect(localStorage.getItem('kel.activeWorkspace_v1')).toBeNull();
  });

  it('drops an old choice that names an archived project without importing it', async () => {
    localStorage.setItem('kel.activeWorkspace_v1', JSON.stringify({ id: 'old', name: 'Old thing' }));
    renderChip();
    expect(await screen.findByRole('button', { name: /All projects/ })).toBeTruthy();
    expect(engine.calls.some((call) => call.action === 'set_active')).toBe(false);
    expect(localStorage.getItem('kel.activeWorkspace_v1')).toBeNull();
  });

  it('re-reads the active project when the window regains focus (changed on another device)', async () => {
    renderChip();
    await screen.findByRole('button', { name: /All projects/ });
    engine.active = 'site';
    await act(async () => {
      window.dispatchEvent(new Event('focus'));
    });
    expect(await screen.findByRole('button', { name: /Website/ })).toBeTruthy();
  });

  it('gives the composer footer the same chat project, with its folder', async () => {
    const { result } = renderHook(() => useConversationProject('chat-3'));
    await waitFor(() => expect(result.current.project?.name).toBe('Website'));
    expect(result.current.project?.root).toBe('C:\\fixtures\\site');
  });

  it('binds a fork (or "new chat here") to its source chat’s project', async () => {
    await bindToSourceProject('chat-src', 'chat-fork');
    expect(engine.calls).toContainEqual({ action: 'of', donor: 'chat-src' });
    expect(engine.calls).toContainEqual({ action: 'bind', donor: 'chat-fork', project: 'site' });
  });
});
