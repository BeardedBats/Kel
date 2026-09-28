/**
 * VIS-13: Activity names work the way its card does. VIS-14 / D-73.5: "Save as a recipe" is offered
 * only for work that finished and passed its checks.
 */
import React from 'react';
import { cleanup, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

const jobs = [
  {
    id: 'ok',
    state: 'CLOSED',
    verdict: 'VERIFIED',
    updated: 3,
    contract: { request: 'I want to create a little app that asks me questions every morning', handoff: { title: 'Morning questions app' } },
  },
  { id: 'failed', state: 'CLOSED', verdict: 'FAILED', updated: 2, contract: { request: 'Write the launch post' } },
  { id: 'stopped', state: 'CLOSED', verdict: 'CANCELLED', updated: 1, contract: { request: 'Tidy the notes folder' } },
];

vi.mock('@renderer/components/kel/kelApi', () => ({
  KEL_ALL_CONVERSATIONS: '*',
  kelState: async () => ({ jobs, continuation: [] }),
  kelProviders: { list: async () => ({ providers: [] }) },
  kelControl: vi.fn(),
  kelRecipePropose: vi.fn(),
  kelRecipeSave: vi.fn(),
}));
vi.mock('@renderer/components/kel/activeProject', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@renderer/components/kel/activeProject')>()),
  useProjects: () => ({ active: '*', loaded: true, projects: [], refresh: vi.fn() }),
  useConversationProject: () => ({ project: null, pending: false }),
}));
vi.mock('@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync', () => ({
  resolveConversationRoute: (route: string) => route,
}));

import KelActivityPage from '@renderer/pages/kel/activity';

afterEach(cleanup);

describe('Activity (VIS-13, VIS-14)', () => {
  it('uses the card’s title and offers Save as a recipe only for work that passed its checks', async () => {
    render(
      <MemoryRouter initialEntries={['/activity']}>
        <KelActivityPage />
      </MemoryRouter>
    );
    const finished = (await screen.findByText('Morning questions app')).closest('.kel-card') as HTMLElement;
    expect(within(finished).queryByText(/I want to create a little app/)).toBeNull();
    const saves = within(finished).getAllByRole('button', { name: /as a recipe/ });
    expect(saves.map((button) => button.getAttribute('aria-label'))).toEqual(['Save Morning questions app as a recipe']);
  });
});
