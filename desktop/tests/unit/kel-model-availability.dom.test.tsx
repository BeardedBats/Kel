/**
 * CH-2/CP-3: a model Kel cannot answer with is shown with the engine's plain reason ("Not supported
 * for chat yet", "Needs setup") and cannot be picked — in the desktop menu, the phone sheet, the
 * narrow-window menu and the default-model settings card. Providers never read "Available" for a
 * provider the engine says it cannot run.
 */
import React from 'react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelDesktopModelMenu } from '@renderer/components/kel/KelDesktopModelMenu';
import { KelMobileModelPicker } from '@renderer/components/kel/KelMobileModelPicker';
import { KelDefaultModelCard, KelModelPill, unavailableNote } from '@renderer/components/kel/KelModelControl';
import { presentProvider, usableNow } from '@renderer/components/kel/providerStatus';

const state = {
  default: null,
  conversation: null,
  providers: [
    { id: 'claude-code', label: 'Claude', available: true, note: null, options: [{ id: 'claude-native', label: 'Claude', available: true, note: null }] },
    { id: 'deepseek', label: 'DeepSeek', available: false, note: 'Not supported for chat yet', options: [{ id: 'deepseek-chat', label: 'DeepSeek Chat', available: false, note: 'Not supported for chat yet' }] },
    { id: 'internal', label: 'Anthropic API', available: false, note: 'API key needed', options: [{ id: 'claude-sonnet-4-6', label: 'Claude Sonnet', available: false }] },
  ],
};

const installKel = () => {
  const request = vi.fn(async (_route: string, body?: Record<string, unknown>) => (body?.action === 'get' ? state : {}));
  (window as unknown as { kelAPI: unknown }).kelAPI = { request, conversation: vi.fn(async () => 'engine-1') };
  return request;
};

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('unavailableNote', () => {
  it('prefers the option note, then the provider note, then "Needs setup"', () => {
    expect(unavailableNote({ id: 'x', label: 'X', available: true })).toBeNull();
    expect(unavailableNote({ id: 'x', label: 'X', available: false, note: 'Sign-in needed' })).toBe('Sign-in needed');
    expect(unavailableNote({ id: 'x', label: 'X', available: false }, { note: 'API key needed' })).toBe('API key needed');
    expect(unavailableNote({ id: 'x', label: 'X', available: false })).toBe('Needs setup');
  });
});

describe('desktop model menu', () => {
  it('shows why an option is unavailable and never lets it be picked', () => {
    const onChoose = vi.fn(async () => {});
    render(<KelDesktopModelMenu state={state} hasConversation onChoose={onChoose} onClose={vi.fn()} onAdd={vi.fn()} onSettings={vi.fn()} />);
    const deepseek = screen.getByRole('button', { name: /DeepSeek Chat/ }) as HTMLButtonElement;
    expect(deepseek.disabled).toBe(true);
    expect(deepseek.textContent).toContain('Not supported for chat yet');
    const sonnet = screen.getByRole('button', { name: /Claude Sonnet/ }) as HTMLButtonElement;
    expect(sonnet.disabled).toBe(true);
    expect(sonnet.textContent).toContain('API key needed');
    fireEvent.click(deepseek);
    expect(onChoose).not.toHaveBeenCalled();
    const claude = screen.getByRole('button', { name: 'Claude' }) as HTMLButtonElement;
    expect(claude.disabled).toBe(false);
    fireEvent.click(claude);
    expect(onChoose).toHaveBeenCalledWith({ provider: 'claude-code', model: 'claude-native' }, 'conversation');
  });
});

describe('phone model sheet', () => {
  it('disables unavailable choices and shows their reason', async () => {
    const request = installKel();
    render(<MemoryRouter><KelMobileModelPicker conversationId='donor-1' open onClose={vi.fn()} /></MemoryRouter>);
    const deepseek = (await screen.findByText('DeepSeek Chat')).closest('button') as HTMLButtonElement;
    expect(deepseek.disabled).toBe(true);
    expect(deepseek.textContent).toContain('Not supported for chat yet');
    fireEvent.click(deepseek);
    expect(request.mock.calls.some(([, body]) => (body as { action?: string })?.action === 'set_conversation')).toBe(false);
    expect((screen.getByText('Claude Sonnet').closest('button') as HTMLButtonElement).textContent).toContain('API key needed');
  });
});

describe('narrow-window model menu', () => {
  it('marks unavailable options disabled with their reason', async () => {
    installKel();
    const width = window.innerWidth;
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 500 });
    try {
      render(<MemoryRouter><KelModelPill conversationId='donor-1' /></MemoryRouter>);
      fireEvent.click(await screen.findByText(/Kel model: Automatic/));
      await screen.findAllByText('Not supported for chat yet');
      const disabled = Array.from(document.querySelectorAll('.arco-dropdown-menu-item.arco-dropdown-menu-disabled'));
      const texts = disabled.map((node) => node.textContent ?? '');
      // Once under "This chat" and once under "Default for new chats".
      expect(texts.filter((text) => text.includes('DeepSeek Chat') && text.includes('Not supported for chat yet'))).toHaveLength(2);
      expect(texts.filter((text) => text.includes('Claude Sonnet') && text.includes('API key needed'))).toHaveLength(2);
      expect(texts.some((text) => text.includes('Available'))).toBe(false);
    } finally {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: width });
    }
  });
});

const Where = () => <div data-testid='where'>{useLocation().pathname}</div>;

describe('default model settings card', () => {
  it('offers setup only where setup can help and never picks an unavailable model', async () => {
    const request = installKel();
    render(
      <MemoryRouter initialEntries={['/settings/model']}>
        <Routes>
          <Route path='/settings/model' element={<KelDefaultModelCard />} />
          <Route path='/settings/providers' element={<Where />} />
        </Routes>
      </MemoryRouter>
    );
    const deepseek = (await screen.findByTestId('kel-default-deepseek-deepseek-chat')) as HTMLButtonElement;
    expect(deepseek.disabled).toBe(true);
    expect(deepseek.textContent).toContain('Not supported for chat yet');
    expect(deepseek.textContent).not.toContain('Set up');
    const sonnet = screen.getByTestId('kel-default-internal-claude-sonnet-4-6') as HTMLButtonElement;
    expect(sonnet.textContent).toContain('API key needed');
    expect(sonnet.textContent).toContain('Set up');
    fireEvent.click(sonnet);
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/settings/providers'));
    expect(request.mock.calls.some(([, body]) => (body as { action?: string })?.action === 'set_default')).toBe(false);
  });
});

describe('provider availability (Providers page rows)', () => {
  it('never reads Available when the engine says Kel cannot answer with it', () => {
    const view = presentProvider({ status: 'healthy', available: false, available_note: 'Not supported for chat yet' });
    expect(view.label).toBe('Not supported for chat yet');
    expect(view.tone).toBe('wait');
    expect(view.reason).toMatch(/cannot answer with it in chat yet/);
    expect(usableNow({ status: 'healthy', available: false })).toBe(false);
  });

  it('keeps the existing words when the provider is available or the engine is older', () => {
    expect(presentProvider({ status: 'healthy', available: true, available_note: null }).label).toBe('Available');
    expect(presentProvider({ status: 'healthy' }).label).toBe('Available');
    expect(presentProvider({ status: 'installed_not_authenticated', available: false, available_note: 'API key needed', note: 'API key needed' }).label).toBe('Needs setup');
    expect(usableNow({ status: 'healthy' })).toBe(true);
  });
});
