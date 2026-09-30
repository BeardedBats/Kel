/** Settings reports the configured boundary without claiming complete Windows read confinement. */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { KelMemoryFolderCard } from '@renderer/components/kel/KelMemoryFolderCard';

const NOT_YET = {
  folder: 'C:\\Users\\Nick\\Desktop\\Kel\\Memory',
  claude: 'Kel checks Claude tools; this is not complete Windows read confinement.',
  codex: 'Codex writes stay in its working folders. Reads outside Memory remain available. Stronger protection limits some reads.',
  codex_reads_blocked: false,
  codex_configured_mode: 'unelevated',
  codex_readiness: 'not_checked',
  codex_read_coverage: 'unconfined',
  codex_complete_read_confinement: false,
  codex_setup_available: true,
  codex_setup: null,
};
let memory: Record<string, unknown> | undefined;
const calls: Array<Record<string, unknown>> = [];
beforeEach(() => {
  memory = { ...NOT_YET };
  calls.length = 0;
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request: vi.fn(async (route: string, body?: Record<string, unknown>) => {
      if (route === '/api/autonomy' && body) calls.push(body);
      if (body?.action === 'mode') return memory ? { mode: 'full', memory } : { mode: 'full' };
      if (body?.action === 'codex_sandbox_setup') return { started: true, memory: { ...memory, codex_setup: 'running' } };
      return {};
    }),
  };
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Memory folder card (D-81)', () => {
  it('shows the folder, actual read limit and deliberate setup action', async () => {
    render(<KelMemoryFolderCard />);
    expect((await screen.findByTestId('kel-memory-folder')).textContent).toBe('C:\\Users\\Nick\\Desktop\\Kel\\Memory');
    const codex = screen.getByTestId('kel-memory-codex');
    expect(codex.getAttribute('data-blocked')).toBe('no');
    expect(codex.textContent).toBe('Codex read protectionNot fully confined');
    const card = screen.getByTestId('kel-memory-folder-card');
    expect(card.textContent).toContain(NOT_YET.codex);
    expect(card.textContent).not.toContain(NOT_YET.claude);
    expect(screen.getByRole('button', { name: 'Set up stronger Codex protection' })).toBeTruthy();
  });

  it('asks the engine for the one-time setup and waits for Windows', async () => {
    render(<KelMemoryFolderCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'Set up stronger Codex protection' }));
    await waitFor(() => expect(calls.some(c => c.action === 'codex_sandbox_setup')).toBe(true));
    expect(await screen.findByRole('button', { name: 'Waiting for Windows…' })).toBeTruthy();
  });

  it('reports ready protection as partial and renders nothing when the engine cannot say', async () => {
    memory = { ...NOT_YET, codex_reads_blocked: true, codex_configured_mode: 'elevated', codex_readiness: 'ready',
      codex_read_coverage: 'partial-deny-list', codex_setup_available: false,
      codex: 'The stronger sandbox limits some reads outside Memory.' };
    render(<KelMemoryFolderCard />);
    const codex = await screen.findByTestId('kel-memory-codex');
    expect(codex.getAttribute('data-blocked')).toBe('no');
    expect(codex.textContent).toContain('Partial protection');
    expect(screen.queryByRole('button')).toBeNull();
    cleanup();
    memory = undefined;
    const { container } = render(<KelMemoryFolderCard />);
    await waitFor(() => expect(calls.filter(c => c.action === 'mode').length).toBeGreaterThan(1));
    expect(container.textContent).toBe('');
  });

  it('reports selected protection as unavailable until readiness is confirmed', async () => {
    memory = { ...NOT_YET, codex_configured_mode: 'elevated', codex_readiness: 'not_ready', codex_read_coverage: 'partial-deny-list' };
    render(<KelMemoryFolderCard />);
    const codex = await screen.findByTestId('kel-memory-codex');
    expect(codex.textContent).toContain('Unavailable');
    expect(codex.getAttribute('data-blocked')).toBe('no');
    expect(codex.getAttribute('data-coverage')).toBe('partial-deny-list');
    expect(screen.getByRole('button', { name: 'Set up stronger Codex protection' })).toBeTruthy();
  });
});
