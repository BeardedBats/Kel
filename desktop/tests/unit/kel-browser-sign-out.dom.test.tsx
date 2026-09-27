/**
 * CP-12 — in a browser (WebUI), signing out is a visible "Sign out" button in Settings → Remote /
 * WebUI, not a hidden Ctrl/Cmd+Shift+L chord. The desktop window (no sign-in) shows no such button.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const logout = vi.fn(async () => undefined);
const closePreview = vi.fn();
const clearPreviewForScope = vi.fn();
vi.mock('@renderer/hooks/context/AuthContext', () => ({ useAuth: () => ({ status: 'authenticated', logout }) }));
vi.mock('@renderer/pages/conversation/Preview/context/PreviewContext', () => ({
  usePreviewContext: () => ({ closePreview, clearPreviewForScope }),
}));

import { BrowserSignOutCard } from '@renderer/pages/settings/WebuiSettings';

beforeEach(() => {
  logout.mockClear();
  clearPreviewForScope.mockClear();
});
afterEach(() => {
  cleanup();
  delete (window as { electronAPI?: unknown }).electronAPI;
});

describe('signing out of the WebUI', () => {
  it('offers a visible Sign out in a browser and signs out on click', async () => {
    render(<BrowserSignOutCard />);
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await waitFor(() => expect(logout).toHaveBeenCalledTimes(1));
    expect(clearPreviewForScope).toHaveBeenCalledTimes(1);
  });

  it('shows nothing in the desktop window', () => {
    (window as { electronAPI?: unknown }).electronAPI = {};
    const view = render(<BrowserSignOutCard />);
    expect(view.container.textContent).toBe('');
  });
});
