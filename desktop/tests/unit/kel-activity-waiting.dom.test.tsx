/**
 * FN-13: Activity's "Waiting on you" counts what the work cards say needs Nick — scoping questions
 * and needs-you cards — and never says "All clear" while something does.
 */
import React from 'react';
import { cleanup, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

const office = { items: [] as Array<Record<string, unknown>> };
vi.mock('@renderer/components/kel/kelApi', () => ({
  KEL_ALL_CONVERSATIONS: '*',
  kelState: async () => ({ jobs: [], continuation: [] }),
  kelProviders: { list: async () => ({ providers: [] }) },
  kelControl: vi.fn(),
  kelRecipePropose: vi.fn(),
  kelRecipeSave: vi.fn(),
  kelRequest: async () => office,
}));
vi.mock('@renderer/components/kel/activeProject', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@renderer/components/kel/activeProject')>()),
  useProjects: () => ({ active: '*', loaded: true, projects: [], refresh: vi.fn() }),
  useConversationProject: () => ({ project: null, pending: false }),
}));
vi.mock('@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync', () => ({
  resolveConversationRoute: (route: string) => route,
}));

import KelActivityPage, { needsNick } from '@renderer/pages/kel/activity';

afterEach(cleanup);

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/activity']}>
      <KelActivityPage />
    </MemoryRouter>
  );

describe('Waiting on you (FN-13)', () => {
  it('lists a scoping card and a needs-you card instead of "All clear"', async () => {
    office.items = [
      { job_id: 'scope-1', title: 'Garden app', state: 'scoping', questions: 2, scoping_id: 'scope-1', conversation_id: 'c1' },
      { job_id: 'job-2', title: 'Launch post', state: 'needs_you', needs_you: true, status_line: 'Kel asked which date to use.' },
      { job_id: 'job-3', title: 'Old work', state: 'done', finished: true },
    ];
    renderPage();
    const asks = await screen.findAllByTestId('activity-ask');
    expect(asks).toHaveLength(2);
    expect(asks[0].textContent).toContain('Kel has 2 questions before it starts.');
    expect(asks[1].textContent).toContain('Kel asked which date to use.');
    expect(screen.queryByText('All clear.')).toBeNull();
  });

  it('says "All clear" only when nothing needs Nick', async () => {
    office.items = [{ job_id: 'job-3', title: 'Old work', state: 'done', finished: true }];
    renderPage();
    expect(await screen.findByText('All clear.')).toBeTruthy();
  });

  it('knows what needs Nick', () => {
    expect(needsNick({ job_id: 'a', title: 'x', state: 'working', needs_you: true } as never)).toBe(true);
    expect(needsNick({ job_id: 'a', title: 'x', state: 'scoping' } as never)).toBe(true);
    expect(needsNick({ job_id: 'a', title: 'x', state: 'working' } as never)).toBe(false);
  });
});
