/**
 * 36e8148 (parallel code streams): each Builder row names its part ("Part 2 of 3") next to the role.
 * Original header of the file this setup was copied from — bc873da: the engine's independent passes after the checks — Sentinel (security / data safety), the
 * Oracle (second opinion) and the Red Team (tries to break the accepted result) — each in the Oracle's
 * shape on /api/office/item. The detail's Review and checks column shows them in that order, what each
 * concluded first and what it looked at second; Sentinel and the Red Team only when the engine has
 * something to say. Same on the desktop panel and the phone sheet.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { KelWorkCardRow } from '@renderer/components/kel/workCards/KelWorkCardRow';
import { takePendingWorkCard } from '@renderer/components/kel/workCards/workCardEvents';
import { resetProjectsForTests } from '@renderer/components/kel/activeProject';
import type { OfficeItem, OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';
import { MIC, MIC_DETAIL } from './fixtures/kelOfficeFixtures';

let list: OfficeItem[] = [];
let details: Record<string, OfficeItemDetail> = {};

const install = () => {
  const request = vi.fn(async (route: string) => {
    if (route === '/api/project') return { projects: [{ id: 'personal', name: 'Personal', kind: 'user' }], active: '*' };
    if (route.startsWith('/api/office?project=')) return { generated: 1, project: '*', items: list };
    if (route.startsWith('/api/office/item?job=')) {
      const job = decodeURIComponent(route.split('=')[1]);
      if (details[job]) return details[job];
      throw new Error('That work has no live team to show.');
    }
    if (route.startsWith('/api/handoff')) return { application: null };
    return { ok: true };
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request,
    conversation: vi.fn(async (id: string) => (id === 'app-morning' ? 'engine-morning' : id)),
    openEngineConversation: vi.fn(async (cid: string) => `app-${cid.replace('engine-', '')}`),
  };
  return request;
};

const Chat: React.FC<{ phone: boolean }> = ({ phone }) => {
  const { id } = useParams();
  return <KelWorkCardRow conversationId={id} phone={phone} availableWidth={phone ? undefined : 920} pollActiveMs={40} pollIdleMs={80} openFolder={async () => undefined} />;
};

const renderRow = (phone = false) =>
  render(
    <MemoryRouter initialEntries={['/conversation/app-morning']}>
      <Routes>
        <Route path='/conversation/:id' element={<Chat phone={phone} />} />
      </Routes>
    </MemoryRouter>
  );


beforeEach(() => {
  list = [];
  details = {};
  resetProjectsForTests();
  takePendingWorkCard();
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('parallel code streams on the work card', () => {
  it('tags each Builder with its part, and one-step staff with nothing', async () => {
    list = [MIC];
    details = {
      [MIC.job_id]: {
        ...MIC_DETAIL,
        staff: [
          ...(MIC_DETAIL.staff ?? []).filter((m) => m.role === 'kel'),
          { id: 'b1', role: 'builder', role_label: 'Builder', step_label: 'Part 1 of 3: slugify in text_tools.py', doing: 'Working on part 1 of 3: slugify', state: 'done', model_label: 'Claude Opus 5.5', model_confirmed: true, reasoning: 'high' },
          { id: 'b2', role: 'builder', role_label: 'Builder', step_label: 'Part 2 of 3: clamp in num_tools.py', doing: 'Working on part 2 of 3: clamp', state: 'working', model_label: 'Claude Opus 5.5', model_confirmed: true, reasoning: 'high' },
          { id: 'b4', role: 'builder', role_label: 'Builder', step_label: 'Combining the parts', doing: 'Combining the parts', state: 'waiting', model_label: null, model_confirmed: false, reasoning: null },
        ],
      },
    };
    install();
    renderRow();
    fireEvent.click(await screen.findByRole('button', { name: /Mic mute toggle app/ }));
    const dialog = await screen.findByTestId('kel-office-detail');
    await waitFor(() => expect(within(dialog).getAllByTestId('kel-office-step-label')).toHaveLength(3));
    const tags = within(dialog).getAllByTestId('kel-office-step-label').map((n) => n.textContent);
    expect(tags).toEqual(['Part 1 of 3', 'Part 2 of 3', 'Combining the parts']);
    const kelRow = within(dialog).getAllByTestId('kel-office-member')[0];
    expect(within(kelRow).queryByTestId('kel-office-step-label')).toBeNull();
  });
});
