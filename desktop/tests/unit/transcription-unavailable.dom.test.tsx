import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Ramble from '@renderer/pages/kel/transcription';

const layout = vi.hoisted(() => ({ isMobile: false }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => layout }));
vi.mock('@renderer/hooks/context/ThemeContext', () => ({ useThemeContext: () => ({ theme: 'dark' }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it.each([false, true])('keeps file input available when insecure recording is unavailable (mobile=%s)', async (mobile) => {
  layout.isMobile = mobile;
  vi.stubGlobal('isSecureContext', false);
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ folders: [], transcripts: [] }) })));
  render(<MemoryRouter><Ramble /></MemoryRouter>);
  expect((await screen.findByTestId('microphone-unavailable')).textContent).toContain('Use Kel on the desktop, or upload an audio file.');
  expect((screen.getByTestId('record-button') as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByTestId('upload-button') as HTMLButtonElement).disabled).toBe(false);
  expect((screen.getByTestId('upload-input') as HTMLInputElement).disabled).toBe(false);
});
