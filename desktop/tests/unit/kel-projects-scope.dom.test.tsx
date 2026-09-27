import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import KelProjectsPage from '@renderer/pages/kel/projects';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';

vi.mock('@/common', () => ({ ipcBridge: { dialog: { showOpen: { invoke: vi.fn() } } } }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));

const record = (id: string, topic: string) => ({
  id, type: 'fact', topic, summary: topic, trust: 3, status: 'active', user_confirmed: 0,
  source_type: 'job', source_ref: 'j', confidence: 1, updated: 1700000000,
});
const work = (records: unknown[], recipes: unknown[]) => ({
  project_id: 'x', memory: { records, proposals: [], conflicts: [] }, map: null, recipes: { entries: recipes },
});

const engine = { active: '*', calls: [] as Array<{ route: string; body?: Record<string, unknown> }> };
const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
  engine.calls.push({ route, body });
  if (route === '/api/project' && body?.action === 'list') {
    return {
      projects: [
        { id: 'default', name: 'General', kind: 'general' },
        { id: 'site', name: 'Website', root: 'C:\\site', kind: 'user' },
      ],
      active: engine.active,
    };
  }
  if (route === '/api/work?project=default') return work([record('m1', 'Coffee order')], [{ recipe_id: 'b1', name: 'Tidy notes', source: 'builtin' }]);
  if (route === '/api/work?project=site') {
    return work([record('m2', 'Deploy target')], [
      { recipe_id: 'b1', name: 'Tidy notes', source: 'builtin' },
      { recipe_id: 'r9', name: 'Ship it', source: 'project' },
    ]);
  }
  if (route === '/api/recipes' && body?.action === 'get') return { recipe: { recipe_id: 'r9', name: 'Ship it', inputs: [], steps: [] } };
  if (route === '/api/recipes' && body?.action === 'preview') {
    return { needs_project: true, project_id: 'site', missing: ['folder'], message: 'This project needs a folder first.' };
  }
  return {};
});

const Location = () => <output data-testid='route'>{`${useLocation().pathname}${useLocation().search}`}</output>;
const open = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path='*' element={<><KelProjectsPage /><Location /></>} />
      </Routes>
    </MemoryRouter>
  );

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  engine.active = '*';
  engine.calls = [];
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  resetProjectsForTests();
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Projects pages follow the active project (D-54)', () => {
  it('reads only the active project', async () => {
    engine.active = 'site';
    open('/projects/knowledge');
    expect(await screen.findByText('Deploy target')).toBeTruthy();
    expect(screen.queryByText('Coffee order')).toBeNull();
    expect(engine.calls.some((call) => call.route === '/api/work?project=site')).toBe(true);
    expect(engine.calls.some((call) => call.route.includes('conversation=main'))).toBe(false);
  });

  it('groups Knowledge by project for All projects and sends each action to the record’s own project', async () => {
    open('/projects/knowledge');
    const generalTable = await screen.findByRole('region', { name: 'Saved knowledge in General' });
    expect(within(generalTable).getByText('Coffee order')).toBeTruthy();
    const siteTable = screen.getByRole('region', { name: 'Saved knowledge in Website' });
    fireEvent.click(within(siteTable).getByRole('button', { name: 'Forget' }));
    await waitFor(() =>
      expect(engine.calls).toContainEqual({ route: '/api/memory', body: { action: 'forget', id: 'm2', project: 'site' } })
    );
    expect(screen.getByText('Choose a project to see its map.')).toBeTruthy();
  });

  it('shows built-in recipes once and labels each project recipe with its project', async () => {
    open('/projects/recipes');
    await screen.findAllByText('Ship it · Website');
    const library = document.querySelector('.kel-recipe-desktop-current') as HTMLElement;
    expect(within(library).getByText('Ship it · Website')).toBeTruthy();
    expect(within(library).getAllByText('Tidy notes')).toHaveLength(1);
  });

  it('sends a recipe that needs a folder to that project’s folder setting', async () => {
    open('/projects/recipes');
    await screen.findAllByText('Ship it · Website');
    const library = document.querySelector('.kel-recipe-desktop-current') as HTMLElement;
    const row = within(library).getByText('Ship it · Website').closest('.kel-recipe-desktop-row') as HTMLElement;
    fireEvent.click(within(row).getByRole('button', { name: 'Run' }));
    fireEvent.click((await screen.findAllByRole('button', { name: 'Start recipe' }))[0]);
    await waitFor(() =>
      expect(engine.calls).toContainEqual({ route: '/api/recipes', body: { action: 'preview', recipe_id: 'r9', inputs: {}, project: 'site' } })
    );
    fireEvent.click((await screen.findAllByRole('button', { name: 'Set project folder' }))[0]);
    expect(screen.getByTestId('route').textContent).toBe('/projects/list?edit=site&focus=folder');
  });
});
