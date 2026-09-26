import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import Activity from '@renderer/pages/kel/activity';
import Providers from '@renderer/pages/kel/providers';

const api = vi.hoisted(() => ({ state: vi.fn(), list: vi.fn(), credentials: vi.fn() }));
vi.mock('@renderer/components/kel/kelApi', () => ({
  kelState: api.state,
  kelProviders: { list: api.list, credentials: api.credentials },
  kelCapabilities: vi.fn(async () => []),
  engineDiagnostics: vi.fn(async () => ({ engineVersion: 'fixture', address: '127.0.0.1', logTail: '' })),
}));

describe('Desktop pending states', () => {
  it('keeps loading distinct from an empty Activity result', async () => {
    let resolve: (value: object) => void;
    api.state.mockReturnValue(new Promise(done => { resolve = done; }));
    const view = render(<MemoryRouter><Activity /></MemoryRouter>);
    expect(screen.getByRole('status', { name: 'Loading activity' }).getAttribute('aria-busy')).toBe('true');
    expect(view.container.querySelectorAll('.kel-skeleton-row')).toHaveLength(7);
    expect(screen.queryByText('Nothing is running right now.')).toBeNull();
    await act(async () => resolve!({ jobs: [], routes: {}, continuation: [], providers: [] }));
    expect(await screen.findByText('Nothing is running right now.')).toBeTruthy();
    expect(view.container.querySelectorAll('.kel-skeleton-row')).toHaveLength(0);
  });
  it('prevents repeated provider retries and replaces failure after a successful reload', async () => {
    let resolve: (value: object) => void;
    api.credentials.mockResolvedValue({ credentials: [] });
    api.list.mockRejectedValueOnce(new Error('Request timed out')).mockReturnValueOnce(new Promise(done => { resolve = done; }));
    const view = render(<MemoryRouter><Providers /></MemoryRouter>);
    expect(await screen.findByText('Kel couldn’t complete that')).toBeTruthy();
    expect(screen.getByText(/Kel could not load your providers/)).toBeTruthy();
    expect(view.container.querySelectorAll('.kel-skeleton-row')).toHaveLength(2);
    const retry = screen.getByRole('button', { name: 'Try again', exact: true });
    fireEvent.click(retry);
    await waitFor(() => expect((retry as HTMLButtonElement).disabled).toBe(true));
    fireEvent.click(retry);
    expect(api.list).toHaveBeenCalledTimes(2);
    await act(async () => resolve!({ providers: [] }));
    await waitFor(() => expect(screen.queryByText('Kel couldn’t complete that')).toBeNull());
    expect(view.container.querySelectorAll('.kel-skeleton-row')).toHaveLength(0);
  });
});
