/**
 * D-56 / handoff §26 — Kel has no consumer updater. About shows the version and build only.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('@/common', () => ({ ipcBridge: { shell: { showItemInFolder: { invoke: vi.fn() } } } }));
vi.mock('@renderer/components/base/AionModal', () => ({ default: () => null }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

import AboutModalContent from '@renderer/components/settings/SettingsModal/contents/AboutModalContent';

beforeEach(() => {
  vi.stubGlobal('__APP_VERSION__', '1.7.0-dev');
  (window as unknown as { electronAPI?: unknown }).electronAPI = {};
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { electronAPI?: unknown }).electronAPI;
  vi.unstubAllGlobals();
});

describe('About (no consumer updater)', () => {
  it('shows the version and build without any update control', () => {
    render(<AboutModalContent />);
    expect(screen.getByText('v1.7.0-dev')).toBeTruthy();
    expect(screen.getByText('1.7.0 · dev')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /update|install/i })).toBeNull();
    expect(screen.queryByText(/check for updates|prerelease|update log|report issue/i)).toBeNull();
    expect(screen.queryByRole('switch')).toBeNull();
  });

  it('shows the build the package was made from (VIS-27)', async () => {
    vi.stubGlobal('__APP_BUILD__', '5294c27');
    vi.resetModules();
    const { default: About } = await import('@renderer/components/settings/SettingsModal/contents/AboutModalContent');
    render(<About />);
    expect(screen.getByTestId('about-build').textContent).toBe('Build5294c27');
  });
});
