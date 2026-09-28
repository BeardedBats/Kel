import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import KelProjectsList from '@renderer/pages/kel/projects/list';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';

const dialog = vi.hoisted(() => ({ invoke: vi.fn() }));
vi.mock('@/common', () => ({ ipcBridge: { dialog: { showOpen: dialog } } }));

type Row = {
  id: string; name: string; root?: string | null; kind: string; archived?: number | null;
  conversations?: number; open_work?: number; test_command?: string[] | null;
};
const engine = { projects: [] as Row[], active: '*', calls: [] as Array<Record<string, unknown>> };

const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
  if (route !== '/api/project' || !body) return {};
  engine.calls.push(body);
  const row = engine.projects.find((project) => project.id === body.id);
  switch (body.action) {
    case 'list':
      return { projects: engine.projects, active: engine.active };
    case 'set_active':
      engine.active = String(body.id);
      return { active: engine.active };
    case 'update':
      if (row) Object.assign(row, Object.fromEntries(Object.entries(body).filter(([key]) => !['action', 'id'].includes(key))));
      return { id: body.id };
    case 'archive':
      if (row) row.archived = 1700000000;
      return {};
    case 'restore':
      if (row) row.archived = null;
      return {};
    case 'delete':
      engine.projects = engine.projects.filter((project) => project.id !== body.id);
      return {};
    default:
      return {};
  }
});

const Location = () => {
  const location = useLocation();
  return <output data-testid='route'>{`${location.pathname}${location.search}`}</output>;
};

const renderList = (entry = '/projects/list') =>
  render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path='*' element={<><KelProjectsList /><Location /></>} />
      </Routes>
    </MemoryRouter>
  );

beforeEach(() => {
  engine.projects = [
    { id: 'default', name: 'General', root: null, kind: 'general', conversations: 45 },
    { id: 'site', name: 'Website', root: 'C:\\fixtures\\clients\\site', kind: 'user', conversations: 3, test_command: ['npm', 'test'] },
    { id: 'empty', name: 'Empty idea', root: null, kind: 'user', conversations: 0, archived: 1700000000 },
    { id: 'kept', name: 'Kept chats', root: null, kind: 'user', conversations: 2, archived: 1700000000 },
    { id: 'acp-temp-9z', name: 'acp-temp-9z', root: 'C:\\Temp\\acp-temp-9z', kind: 'system' },
  ];
  engine.active = 'site';
  engine.calls = [];
  dialog.invoke.mockReset();
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  resetProjectsForTests();
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('All projects page (D-54)', () => {
  it('lists each project with its folder, test command and chats, and hides plumbing', async () => {
    renderList();
    const site = await screen.findByTestId('kel-project-row-site');
    expect(within(site).getByText('site').getAttribute('title')).toBe('C:\\fixtures\\clients\\site');
    expect(within(site).getByText('Tests: npm test')).toBeTruthy();
    expect(within(site).getByText('3 chats')).toBeTruthy();
    expect(within(site).getByText('Active')).toBeTruthy();
    expect(within(screen.getByTestId('kel-project-row-default')).getByText('No folder')).toBeTruthy();
    expect(within(screen.getByTestId('kel-project-row-default')).queryByRole('button', { name: 'Archive' })).toBeNull();
    expect(screen.queryByText('acp-temp-9z')).toBeNull();
    expect(screen.getByText('Your active project is the same on every device.')).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/Workspace/);
    // VIS-15: one primary per view — "New project"; each row's Open is a secondary button.
    expect(Array.from(document.querySelectorAll('.kel-btn--primary')).map((button) => button.textContent)).toEqual(['New project']);
  });

  it('opens a project by making it active and going to its Knowledge', async () => {
    renderList();
    fireEvent.click(within(await screen.findByTestId('kel-project-row-default')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(screen.getByTestId('route').textContent).toBe('/projects/knowledge'));
    expect(engine.calls).toContainEqual({ action: 'set_active', id: 'default' });
  });

  it('renames in place, sending only the name', async () => {
    renderList();
    fireEvent.click(within(await screen.findByTestId('kel-project-row-site')).getByRole('button', { name: 'Rename' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Project name' }), { target: { value: 'Website 2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'update', id: 'site', name: 'Website 2' }));
    expect(await within(screen.getByTestId('kel-project-row-site')).findByText('Website 2')).toBeTruthy();
  });

  it('sets a folder from the folder picker', async () => {
    dialog.invoke.mockResolvedValue(['C:\\fixtures\\garden']);
    renderList();
    fireEvent.click(within(await screen.findByTestId('kel-project-row-default')).getByRole('button', { name: 'Set folder' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'update', id: 'default', root: 'C:\\fixtures\\garden' }));
  });

  it('edits the test command as separate arguments and can remove it', async () => {
    renderList();
    fireEvent.click(within(await screen.findByTestId('kel-project-row-site')).getByRole('button', { name: 'Test command' }));
    const editor = screen.getByRole('group', { name: 'Test command for Website' });
    expect((within(editor).getByRole('textbox', { name: 'Command part 1' }) as HTMLInputElement).value).toBe('npm');
    fireEvent.click(within(editor).getByRole('button', { name: 'Add part' }));
    fireEvent.change(within(editor).getByRole('textbox', { name: 'Command part 3' }), { target: { value: '--silent' } });
    fireEvent.click(within(editor).getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(engine.calls).toContainEqual({ action: 'update', id: 'site', test_command: ['npm', 'test', '--silent'] })
    );
    fireEvent.click(within(screen.getByTestId('kel-project-row-site')).getByRole('button', { name: 'Test command' }));
    fireEvent.click(screen.getByRole('button', { name: 'Remove test command' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'update', id: 'site', test_command: null }));
  });

  it('archives only after confirming, and restores from Archived', async () => {
    renderList();
    fireEvent.click(within(await screen.findByTestId('kel-project-row-site')).getByRole('button', { name: 'Archive' }));
    expect(engine.calls.some((call) => call.action === 'archive')).toBe(false);
    fireEvent.click(within(screen.getByRole('group', { name: 'Archive Website' })).getByRole('button', { name: 'Archive' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'archive', id: 'site' }));
    fireEvent.click(within(await screen.findByTestId('kel-project-row-kept')).getByRole('button', { name: 'Restore' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'restore', id: 'kept' }));
  });

  it('offers Delete only for an archived project that holds nothing', async () => {
    renderList();
    const kept = await screen.findByTestId('kel-project-row-kept');
    expect(within(kept).queryByRole('button', { name: 'Delete' })).toBeNull();
    fireEvent.click(within(screen.getByTestId('kel-project-row-empty')).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(engine.calls).toContainEqual({ action: 'delete', id: 'empty' }));
  });

  it('opens the test command editor from a deep link', async () => {
    renderList('/projects/list?edit=default&focus=test');
    expect(await screen.findByRole('group', { name: 'Test command for General' })).toBeTruthy();
    expect(screen.getByTestId('kel-project-row-default').getAttribute('data-editing')).toBe('true');
  });

  it('says what the engine refused', async () => {
    request.mockImplementationOnce(async () => ({ projects: engine.projects, active: engine.active }));
    renderList();
    await screen.findByTestId('kel-project-row-site');
    request.mockImplementationOnce(async () => {
      throw new Error('This project still has 3 chats. Archive it instead.');
    });
    fireEvent.click(within(screen.getByTestId('kel-project-row-site')).getByRole('button', { name: 'Rename' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Project name' }), { target: { value: 'X' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect((await screen.findByRole('alert')).textContent).toMatch(/Rename didn't work/);
  });
});
