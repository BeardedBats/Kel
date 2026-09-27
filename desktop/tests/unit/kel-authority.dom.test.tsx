/**
 * D-64 — the authority mode is said plainly (Full access by default) with one "Ask first" switch, on
 * Permissions, Settings → System and Set up Kel. An engine that cannot say shows nothing.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@arco-design/web-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@arco-design/web-react')>();
  return { ...actual, Message: { success: vi.fn(), error: vi.fn() } };
});

import { KelAuthorityCard } from '@renderer/components/kel/KelAuthorityCard';
import { authorityModeOf } from '@renderer/components/kel/kelApi';

let mode: string | undefined = 'full';
let failModeRead = false;
const calls: Array<Record<string, unknown>> = [];

beforeEach(() => {
  mode = 'full';
  failModeRead = false;
  calls.length = 0;
  (window as unknown as { kelAPI: unknown }).kelAPI = {
    request: vi.fn(async (route: string, body?: Record<string, unknown>) => {
      if (route === '/api/autonomy' && body) calls.push(body);
      if (route === '/api/autonomy' && body?.action === 'mode') {
        if (failModeRead) throw new Error('Unknown autonomy action');
        return mode ? { mode, label: mode === 'full' ? 'Full access' : 'Ask first' } : {};
      }
      if (route === '/api/autonomy' && body?.action === 'set_mode') {
        mode = String(body.mode);
        return { mode };
      }
      return {};
    }),
  };
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('authority mode (D-64)', () => {
  it('reads the mode from the engine answer, accepting the authority_mode alias', () => {
    expect(authorityModeOf({ mode: 'full' })).toBe('full');
    expect(authorityModeOf({ authority_mode: 'ask' })).toBe('ask');
    expect(authorityModeOf({ mode: 'sometimes' })).toBeNull();
    expect(authorityModeOf({})).toBeNull();
  });

  it('says Full access plainly and switches to Ask first only when the person asks', async () => {
    render(<KelAuthorityCard />);
    const label = await screen.findByTestId('kel-authority-mode');
    expect(label.textContent).toBe('Full access');
    expect(screen.getByTestId('kel-authority-card').textContent).toContain(
      'Kel acts without asking. It never changes its own app or data, and everything it does shows in Activity.'
    );
    const toggle = screen.getByRole('switch', { name: 'Ask first' });
    expect(toggle.getAttribute('aria-checked')).toBe('false');
    expect(calls.filter((call) => call.action === 'set_mode')).toEqual([]);

    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getByTestId('kel-authority-mode').textContent).toBe('Ask first'));
    expect(calls).toContainEqual({ action: 'set_mode', mode: 'ask' });
    expect(screen.getByRole('switch', { name: 'Ask first' }).getAttribute('aria-checked')).toBe('true');

    fireEvent.click(screen.getByRole('switch', { name: 'Ask first' }));
    await waitFor(() => expect(screen.getByTestId('kel-authority-mode').textContent).toBe('Full access'));
    expect(calls).toContainEqual({ action: 'set_mode', mode: 'full' });
  });

  it('shows nothing when the engine cannot say which mode it is in', async () => {
    failModeRead = true;
    const view = render(<KelAuthorityCard />);
    await waitFor(() => expect(calls).toContainEqual({ action: 'mode' }));
    expect(view.container.textContent).toBe('');
  });

  it('shows nothing when the answer carries no mode', async () => {
    mode = undefined;
    const view = render(<KelAuthorityCard />);
    await waitFor(() => expect(calls).toContainEqual({ action: 'mode' }));
    expect(view.container.textContent).toBe('');
  });

  it('settles the Set up Kel Autonomy step with the same control', async () => {
    vi.doMock('@renderer/components/kel/KelModelControl', () => ({ KelDefaultModelCard: () => null }));
    const { default: Setup } = await import('@renderer/pages/kel/onboarding');
    render(<MemoryRouter initialEntries={['/onboarding']}><Setup /></MemoryRouter>);
    expect((await screen.findByTestId('kel-authority-mode')).textContent).toBe('Full access');
    expect(screen.queryByText('Ask before edits')).toBeNull();
  });

  it('leads the Permissions page with the mode', async () => {
    const { default: Permissions } = await import('@renderer/pages/kel/autonomy');
    render(<MemoryRouter initialEntries={['/autonomy']}><Permissions /></MemoryRouter>);
    expect((await screen.findByTestId('kel-authority-mode')).textContent).toBe('Full access');
    expect(screen.getByRole('switch', { name: 'Ask first' })).toBeTruthy();
  });
});
