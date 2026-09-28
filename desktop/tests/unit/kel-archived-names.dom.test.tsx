/**
 * VIS-25: archived chats are grouped under project names, never under the id their working folder
 * happens to be named with.
 */
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SWRConfig } from 'swr';

const conv = (id: string, name: string) => ({
  type: 'conversation',
  conversation: { id, name, created_at: 1, extra: {} },
});

vi.mock('@/common', () => ({
  ipcBridge: {
    sidebar: {
      get: {
        invoke: async () => ({
          groups: [
            {
              scope: { type: 'dir', key: 'd1', path: 'C:\\Kel\\aion-workspaces\\8095c45b-ba76-4f84-85d5-323c8775def1', name: '8095c45b-ba76-4f84-85d5-323c8775def1' },
              items: [conv('chat-in-garden', 'Plan the beds')],
              has_more: false,
            },
            {
              scope: { type: 'dir', key: 'd2', path: 'C:\\Kel\\aion-workspaces\\71b5a4d9-fc96-4a26-bf7a-f2a51d0b4bf8', name: '71b5a4d9-fc96-4a26-bf7a-f2a51d0b4bf8' },
              items: [conv('loose-chat', 'New conversation')],
              has_more: false,
            },
            {
              scope: { type: 'dir', key: 'd3', path: 'C:/Users/Nick/Projects/Recipes/', name: 'Recipes' },
              items: [conv('chat-in-folder', 'Soup ideas')],
              has_more: false,
            },
          ],
        }),
      },
    },
  },
}));
vi.mock('@renderer/components/kel/kelApi', () => ({
  kelProjects: {
    list: async () => ({
      projects: [
        { id: 'p-garden', name: 'Garden planner', root: 'C:\\Kel\\Projects\\Garden' },
        { id: 'p-recipes', name: 'Family recipes', root: 'C:\\Users\\Nick\\Projects\\Recipes' },
      ],
    }),
    of: async ({ donor }: { donor: string }) => (donor === 'chat-in-garden' ? { project: 'p-garden' } : { project: null }),
  },
}));
vi.mock('@/renderer/utils/model/agentLogo', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/renderer/utils/model/agentLogo')>()),
  useAgentLogos: () => ({}),
}));
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => (key === 'settings.archived.noProject' ? 'No project' : key),
    i18n: { language: 'en-US' },
  }),
}));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));

import ArchivedSettings, { archivedGroupName } from '@renderer/pages/settings/ArchivedSettings';
import { MemoryRouter } from 'react-router-dom';

afterEach(cleanup);

describe('Archived groups (VIS-25)', () => {
  it('titles each group with its project name, or "No project", and never an id', async () => {
    render(
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
        <MemoryRouter>
          <ArchivedSettings />
        </MemoryRouter>
      </SWRConfig>
    );
    expect(await screen.findByText('Garden planner')).toBeTruthy();
    expect(await screen.findByText('Family recipes')).toBeTruthy();
    expect(await screen.findByText('No project')).toBeTruthy();
    expect(screen.getAllByText('No project')).toHaveLength(1);
    expect(document.body.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-/);
  });

  it('keeps a readable folder name when the folder is not a project', () => {
    expect(archivedGroupName({ type: 'dir', path: 'D:/work/notes', name: 'notes' }, [], null, 'No project')).toBe('notes');
  });
});
