/**
 * D-81 — Settings → Permissions says where the AI tools work (the Memory folder) and, until Nick allows
 * Codex's stronger Windows sandbox once, that Codex's reads outside it are not yet blocked, with the
 * one button that asks Windows. An engine that cannot say shows nothing.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { KelMemoryFolderCard } from '@renderer/components/kel/KelMemoryFolderCard';

const NOT_YET = {
  folder: 'C:\\Users\\Nick\\Desktop\\Kel\\Memory',
  claude: "Claude Code is held to the Memory folder by Kel's guard, which checks every file and command it uses.",
  codex:
    'Codex can write only inside the Memory folder, but reads outside it are not yet blocked for Codex. Allow its Windows sandbox once (one Windows admin prompt) to block them.',
  codex_reads_blocked: false,
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
  it('names the folder and says plainly that Codex reads are not yet blocked', async () => {
    render(<KelMemoryFolderCard />);
    expect(await screen.findByText('C:\\Users\\Nick\\Desktop\\Kel\\Memory')).toBeTruthy();
    const codex = screen.getByTestId('kel-memory-codex');
    expect(codex.getAttribute('data-blocked')).toBe('no');
    expect(codex.textContent).toContain('not yet blocked for Codex');
  });

  it('asks the engine for the one-time setup and waits for Windows', async () => {
    render(<KelMemoryFolderCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'Block Codex reads outside Memory' }));
    await waitFor(() => expect(calls.some((c) => c.action === 'codex_sandbox_setup')).toBe(true));
    expect(await screen.findByRole('button', { name: 'Waiting for Windows…' })).toBeTruthy();
  });

  it('shows no button once Windows blocks Codex reads, and nothing when the engine cannot say', async () => {
    memory = { ...NOT_YET, codex_reads_blocked: true, codex_setup_available: false, codex: 'Codex runs in its own Windows sandbox.' };
    render(<KelMemoryFolderCard />);
    expect((await screen.findByTestId('kel-memory-codex')).getAttribute('data-blocked')).toBe('yes');
    expect(screen.queryByRole('button')).toBeNull();
    cleanup();
    memory = undefined;
    const { container } = render(<KelMemoryFolderCard />);
    await waitFor(() => expect(calls.filter((c) => c.action === 'mode').length).toBeGreaterThan(1));
    expect(container.textContent).toBe('');
  });
});
