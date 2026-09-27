import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import Setup from '@renderer/pages/kel/onboarding';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';

const controls = vi.hoisted(() => ({ choose: vi.fn(), save: vi.fn(), initialize: vi.fn(), get: vi.fn() }));
vi.mock('@/common', () => ({ ipcBridge: { dialog: { showOpen: { invoke: controls.choose } } } }));
vi.mock('@/common/config/configService', () => ({ configService: { set: controls.save, initialize: controls.initialize, get: controls.get } }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));

type Project = { id: string; name: string; root?: string | null; kind: string };
let projects: Project[] = [];
let active = '*';
const projectCalls: Array<Record<string, unknown>> = [];

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks(); });
beforeEach(() => {
  controls.choose.mockReset(); controls.save.mockReset(); controls.get.mockReset();
  controls.initialize.mockResolvedValue(undefined);
  projects = [{ id: 'default', name: 'General', root: null, kind: 'general' }];
  active = '*';
  projectCalls.length = 0;
  resetProjectsForTests();
});
function Route() { const location = useLocation(); return <output data-testid='route'>{JSON.stringify({ path: location.pathname, state: location.state })}</output>; }
function open() {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: { body?: string }) => {
    const body = init?.body ? JSON.parse(init.body) as Record<string, unknown> : {};
    let payload: unknown = { providers: [], projects, engine_version: 'fixture', rules: [], digest: '' };
    if (String(url).includes('/model')) payload = { default: null, conversation: null, providers: [] };
    if (String(url).endsWith('/api/project')) {
      projectCalls.push(body);
      if (body.action === 'list') payload = { projects, active };
      if (body.action === 'for_folder') {
        const root = String(body.root);
        const made = { id: 'fixture-project', name: root.split('/').pop()!, root, kind: 'user' };
        projects = [...projects, made];
        payload = { id: made.id, name: made.name, root };
      }
      if (body.action === 'set_active') { active = String(body.id); payload = { active }; }
    }
    return { ok: true, json: async () => payload };
  }));
  render(<MemoryRouter initialEntries={['/onboarding']}><Setup /><Route /></MemoryRouter>);
}

it('turns the chosen folder into the active project and ends in the composer without a folder hand-off', async () => {
  controls.choose.mockResolvedValue(['C:/fixture-workspace']); controls.save.mockResolvedValue(undefined); open();
  await screen.findByTestId('kel-default-auto');
  expect(screen.getByText('Project folder')).toBeTruthy();
  expect(screen.getByText('No folder selected')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Change', exact: true }));
  await screen.findByText('C:/fixture-workspace');
  expect(controls.choose).toHaveBeenCalledWith({ properties: ['openDirectory', 'createDirectory'] });
  expect(projectCalls).toContainEqual({ action: 'for_folder', root: 'C:/fixture-workspace' });
  expect(projectCalls).toContainEqual({ action: 'set_active', id: 'fixture-project' });
  // D-54: the folder belongs to the project in the engine; Setup keeps no copy of its own.
  expect(controls.save).not.toHaveBeenCalledWith('kel.setupWorkspace_v1', expect.anything());
  fireEvent.click(screen.getByRole('button', { name: 'Start using Kel' }));
  await waitFor(() => expect(JSON.parse(screen.getByTestId('route').textContent!).path).toBe('/guid'));
  expect(controls.save).toHaveBeenCalledWith('kel.onboardingCompleted_v1', true);
  expect(JSON.parse(screen.getByTestId('route').textContent!).state).toBeNull();
});

it('shows the active project folder the engine already has', async () => {
  projects = [...projects, { id: 'site', name: 'Site', root: 'C:/remembered-folder', kind: 'user' }];
  active = 'site';
  open();
  await screen.findByText('C:/remembered-folder');
  expect(controls.get).not.toHaveBeenCalledWith('kel.setupWorkspace_v1');
  expect(controls.save).not.toHaveBeenCalled();
});

it('says why when Kel cannot use the chosen folder and keeps the current project', async () => {
  controls.choose.mockResolvedValue(['C:/session-folder']);
  open(); await screen.findByTestId('kel-default-auto');
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: { body?: string }) => {
    const body = init?.body ? JSON.parse(init.body) as Record<string, unknown> : {};
    if (String(url).endsWith('/api/project') && body.action === 'for_folder') return { ok: false, status: 400, json: async () => ({ error: 'KEL_ENGINE_UNREACHABLE' }) };
    return { ok: true, json: async () => (body.action === 'list' ? { projects, active } : {}) };
  }));
  fireEvent.click(screen.getByRole('button', { name: 'Change', exact: true }));
  expect((await screen.findByRole('alert')).textContent).toMatch(/Kel stopped answering/);
  expect(screen.getByText('No folder selected')).toBeTruthy();
});

it('keeps the project unchanged on cancellation and makes progress keyboard accessible', async () => {
  controls.choose.mockResolvedValue([]); open(); await screen.findByTestId('kel-default-auto');
  fireEvent.click(screen.getByRole('button', { name: 'Change', exact: true }));
  await waitFor(() => expect(controls.choose).toHaveBeenCalledTimes(1));
  expect(screen.getByText('No folder selected')).toBeTruthy();
  expect(projectCalls.some((call) => call.action === 'for_folder' || call.action === 'set_active')).toBe(false);
  expect(screen.getByRole('button', { name: 'Step 3: Project' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Step 2: Connect a model' }));
  expect(screen.getByText('Step 2 of 5')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Step 2: Connect a model' }).getAttribute('aria-current')).toBe('step');
  expect(controls.save).not.toHaveBeenCalled();
});
