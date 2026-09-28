/**
 * FN-12: on the Recipes page Nick writes a new recipe and renames or re-words one; Preview says
 * what each step does; "More actions" opens this recipe's own actions (no second recipe table and
 * no internal ids); runs read "Ran <recipe>".
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import KelProjectsPage from '@renderer/pages/kel/projects';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import { stepLabel } from '@renderer/pages/kel/projects/RecipeEditor';
import { workTitle } from '@renderer/components/kel/jobLabels';
import { routeSentence } from '@renderer/components/kel/workLanguage';

vi.mock('@/common', () => ({ ipcBridge: { dialog: { showOpen: { invoke: vi.fn() } } } }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));

const calls: Array<{ route: string; body?: Record<string, unknown> }> = [];
const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
  calls.push({ route, body });
  if (route === '/api/project' && body?.action === 'list') {
    return { projects: [{ id: 'default', name: 'General', kind: 'general' }], active: 'default' };
  }
  if (route === '/api/work?project=default') {
    return {
      project_id: 'default', memory: { records: [], proposals: [], conflicts: [] }, map: null,
      recipes: { entries: [{ recipe_id: 'job-3ad8abcd1234', name: 'Quarterly summary', source: 'from_job:3ad8abcd-1234', steps: [{}] }] },
    };
  }
  if (route === '/api/recipes' && body?.action === 'categories') return { categories: [] };
  if (route === '/api/recipes' && body?.action === 'get') {
    return {
      recipe: {
        recipe_id: 'job-3ad8abcd1234', name: 'Quarterly summary', description: 'Saved from work.', inputs: [],
        steps: [{ id: 'document', title: 'document', objective: 'Write a one-page summary of the Q3 report. Keep it short.' }],
      },
    };
  }
  if (route === '/api/recipes' && body?.action === 'last_result') return { sentence: '' };
  if (route === '/api/recipes' && body?.action === 'history') {
    return { history: [{ job_id: '3ad8abcd-1234', state: 'CLOSED', verdict: 'VERIFIED', created: 1700000000 }] };
  }
  return { saved: true };
});

const open = () =>
  render(
    <MemoryRouter initialEntries={['/projects/recipes']}>
      <Routes>
        <Route path='*' element={<KelProjectsPage />} />
      </Routes>
    </MemoryRouter>
  );

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  calls.length = 0;
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  resetProjectsForTests();
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Recipes page (FN-12)', () => {
  it('writes a new recipe', async () => {
    open();
    fireEvent.click(await screen.findByRole('button', { name: 'New recipe' }));
    const editor = screen.getByTestId('recipe-editor');
    fireEvent.change(within(editor).getByLabelText('Recipe name'), { target: { value: 'Inbox triage' } });
    fireEvent.change(within(editor).getByLabelText('Step 1'), { target: { value: 'Sort the inbox into three piles.' } });
    fireEvent.click(within(editor).getByText('Add a step'));
    fireEvent.change(within(editor).getByLabelText('Step 2'), { target: { value: 'Reply to the urgent ones.' } });
    fireEvent.click(within(editor).getByRole('button', { name: 'Save recipe' }));
    await waitFor(() =>
      expect(calls).toContainEqual({
        route: '/api/recipes',
        body: {
          action: 'create', name: 'Inbox triage', description: '',
          steps: [{ objective: 'Sort the inbox into three piles.' }, { objective: 'Reply to the urgent ones.' }],
          project: 'default',
        },
      })
    );
    await waitFor(() => expect(screen.queryByTestId('recipe-editor')).toBeNull());
  });

  it('previews what each step does, and More actions renames without a second table', async () => {
    open();
    fireEvent.click(await screen.findByRole('button', { name: 'Preview' }));
    expect((await screen.findAllByText('Write a one-page summary of the Q3 report')).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: 'More actions' }));
    expect(screen.queryByText(/from_job:/)).toBeNull();
    expect(screen.queryByTestId('recipe-library-controls')).toBeNull();
    fireEvent.click(within(screen.getByTestId('recipe-more-actions')).getByText('Rename and edit'));
    const editor = await screen.findByTestId('recipe-editor');
    const name = within(editor).getByLabelText('Recipe name') as HTMLInputElement;
    expect(name.value).toBe('Quarterly summary');
    fireEvent.change(name, { target: { value: 'Q3 summary' } });
    fireEvent.click(within(editor).getByRole('button', { name: 'Save recipe' }));
    await waitFor(() =>
      expect(
        calls.some((call) => call.body?.action === 'update' && call.body?.name === 'Q3 summary' && call.body?.recipe_id === 'job-3ad8abcd1234')
      ).toBe(true)
    );
  });

  it('lists runs as "Ran <recipe>" without job ids', async () => {
    open();
    fireEvent.click(await screen.findByRole('button', { name: 'Preview' }));
    fireEvent.click(await screen.findByRole('button', { name: 'More actions' }));
    fireEvent.click(within(screen.getByTestId('recipe-more-actions')).getByText('All runs'));
    expect(await screen.findByText('Ran Quarterly summary')).toBeTruthy();
    expect(screen.queryByText(/3ad8abcd/)).toBeNull();
  });
});

describe('recipe words elsewhere (FN-12)', () => {
  it('names a step by what it does when its title is only an internal id', () => {
    expect(stepLabel({ id: 'document', title: 'document', objective: 'Draft the plan. Then check it.' })).toBe('Draft the plan');
    expect(stepLabel({ id: 'step-1', title: 'Collect the numbers', objective: 'x' })).toBe('Collect the numbers');
  });

  it('names a recipe run after its recipe in Activity, old runs included', () => {
    expect(workTitle({ contract: { request: 'Run the recipe “Inbox triage”.', recipe: { name: 'Inbox triage' } } })).toBe('Ran Inbox triage');
    expect(workTitle({ contract: { request: 'Run recipe Weekly rankings v1.0.0 (job-3ad8abcd1234).' } })).toBe('Ran Weekly rankings');
  });

  it('names runtimes the way a person knows them', () => {
    const sentence = routeSentence({ provider: 'codex', route: { selected: 'codex', fallbacks: ['claude'], excluded: {} } } as never, {});
    expect(sentence).toContain('Running on Codex');
    expect(sentence).toContain('Kel will try Claude.');
  });
});
