import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import Setup from '@renderer/pages/kel/onboarding';

const controls = vi.hoisted(() => ({ choose: vi.fn(), save: vi.fn() }));
vi.mock('@/common', () => ({ ipcBridge: { dialog: { showOpen: { invoke: controls.choose } } } }));
vi.mock('@/common/config/configService', () => ({ configService: { set: controls.save } }));
vi.mock('@renderer/hooks/context/LayoutContext', () => ({ useLayoutContext: () => ({ isMobile: false }) }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks(); });
function Route() { const location = useLocation(); return <output data-testid='route'>{JSON.stringify({ path: location.pathname, state: location.state })}</output>; }
function open() {
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  vi.stubGlobal('fetch', vi.fn(async url => ({ ok: true, json: async () => String(url).includes('/model') ? { default: null, conversation: null, providers: [] } : { providers: [], projects: [{ id: 'default', name: 'General' }], engine_version: 'fixture', rules: [], digest: '' } })));
  render(<MemoryRouter initialEntries={['/onboarding']}><Setup /><Route /></MemoryRouter>);
}
it('uses actual model state and routes a selected folder to the composer after saving setup', async () => {
  controls.choose.mockResolvedValue(['C:/fixture-workspace']); controls.save.mockResolvedValue(undefined); open();
  await screen.findByTestId('kel-default-auto');
  expect(screen.getByText('No folder selected')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Change', exact: true }));
  await screen.findByText('C:/fixture-workspace');
  expect(controls.choose).toHaveBeenCalledWith({ properties: ['openDirectory', 'createDirectory'] });
  fireEvent.click(screen.getByRole('button', { name: 'Start using Kel' }));
  await waitFor(() => expect(JSON.parse(screen.getByTestId('route').textContent!).path).toBe('/guid'));
  expect(controls.save).toHaveBeenCalledWith('kel.onboardingCompleted_v1', true);
  expect(JSON.parse(screen.getByTestId('route').textContent!).state.workspace).toBe('C:/fixture-workspace');
});
it('keeps folder selection empty on cancellation and makes progress keyboard accessible', async () => {
  controls.choose.mockResolvedValue([]); open(); await screen.findByTestId('kel-default-auto');
  fireEvent.click(screen.getByRole('button', { name: 'Change', exact: true }));
  await waitFor(() => expect(controls.choose).toHaveBeenCalledTimes(1));
  expect(screen.getByText('No folder selected')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Step 2: Connect a model' }));
  expect(screen.getByText('Step 2 of 5')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Step 2: Connect a model' }).getAttribute('aria-current')).toBe('step');
  expect(controls.save).not.toHaveBeenCalled();
});
