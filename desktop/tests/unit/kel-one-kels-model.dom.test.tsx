/**
 * D-73.3 — one "Kel's model". Settings → Model and the Kel row in Staff & models read and write the same
 * value (the Kel row of `/api/model` roles); the composer picker is a per-chat override of it. The older
 * default-model setting is named while it still decides, and cleared whenever Kel's model is chosen.
 * Also: the command palette's Vetting rows open their chat now that the Work panel is gone.
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { KelDefaultModelCard, KelModelPill, kelsModelLabel } from '@renderer/components/kel/KelModelControl';
import { KelDesktopModelMenu } from '@renderer/components/kel/KelDesktopModelMenu';
import { KELS_MODEL_CHANGED_EVENT, kelStaffSetRole } from '@renderer/components/kel/staffModels/staffModelsApi';

vi.mock('@arco-design/web-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@arco-design/web-react')>();
  return { ...actual, Message: { success: vi.fn(), error: vi.fn(), info: vi.fn() } };
});

type Row = { role: string; label: string; mode: 'AUTOMATIC' | 'PREFERRED' | 'FIXED'; model: string | null; model_label?: string | null; reasoning: string };

const MODELS = [
  { id: 'gpt-6-luna', label: 'ChatGPT Luna', version: 'GPT-6 Luna', available: true },
  { id: 'claude-opus-5-5', label: 'Claude Opus 5.5', version: 'Opus 5.5', available: true },
  { id: 'deepseek-flash', label: 'DeepSeek Flash', version: 'V4.1 Flash', available: false, note: 'API key needed' },
];
const PROVIDERS = [
  { id: 'codex', label: 'Codex', available: true, note: null, options: [{ id: 'codex-native', label: 'Codex', available: true, note: null }] },
];

const engine = (start: { kel: Row; default?: { provider: string; model: string } | null }) => {
  const state = { kel: { ...start.kel }, default: start.default ?? null, conversation: null as null | { provider: string; model: string } };
  const listing = () => ({ roles: [state.kel, { role: 'builder', label: 'Builder', mode: 'PREFERRED', model: 'claude-opus-5-5', reasoning: 'auto' }], models: MODELS });
  const request = vi.fn(async (route: string, body?: Record<string, unknown>) => {
    if (route !== '/api/model') return {};
    switch (body?.action) {
      case 'roles':
        return listing();
      case 'set_role': {
        if (body.role === 'kel') {
          const model = (body.model as string | undefined) ?? null;
          state.kel = {
            ...state.kel,
            mode: body.mode as Row['mode'],
            model: body.mode === 'AUTOMATIC' ? null : model,
            model_label: MODELS.find((entry) => entry.id === model)?.label ?? null,
            reasoning: String(body.reasoning),
          };
        }
        return listing();
      }
      case 'set_default':
        state.default = (body.choice as typeof state.default) ?? null;
        return { default: state.default, conversation: null };
      case 'set_conversation':
        state.conversation = body.choice as typeof state.conversation;
        return { default: state.default, conversation: state.conversation };
      case 'get':
        return { default: state.default, conversation: state.conversation, providers: PROVIDERS };
      default:
        return {};
    }
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = { request, conversation: vi.fn(async () => 'engine-1') };
  return { request, state };
};

const writes = (request: ReturnType<typeof vi.fn>) =>
  request.mock.calls.map(([, body]) => body as Record<string, unknown>).filter((body) => body && body.action !== 'roles' && body.action !== 'get');

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const LUNA: Row = { role: 'kel', label: 'Kel', mode: 'PREFERRED', model: 'gpt-6-luna', model_label: 'ChatGPT Luna', reasoning: 'high' };

describe("Settings → Model edits Kel's model (the Kel row)", () => {
  it('shows the Kel row as current and writes the Kel row, keeping its reasoning', async () => {
    const { request, state } = engine({ kel: LUNA });
    render(
      <MemoryRouter>
        <KelDefaultModelCard compact />
      </MemoryRouter>
    );
    const card = await screen.findByTestId('kel-kels-model-rows');
    expect(within(card).getByTestId('kel-kels-model-gpt-6-luna').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('kel-default-model-card').textContent).toContain("Kel's model");
    fireEvent.click(within(card).getByTestId('kel-kels-model-claude-opus-5-5'));
    await waitFor(() => expect(state.kel.model).toBe('claude-opus-5-5'));
    expect(writes(request)[0]).toEqual({ action: 'set_role', role: 'kel', mode: 'PREFERRED', model: 'claude-opus-5-5', reasoning: 'high' });
    await waitFor(() => expect(within(card).getByTestId('kel-kels-model-claude-opus-5-5').getAttribute('aria-pressed')).toBe('true'));
  });

  it('names an older default that still answers, and clears it when Kel’s model is chosen', async () => {
    const { request, state } = engine({ kel: LUNA, default: { provider: 'codex', model: 'codex-native' } });
    render(
      <MemoryRouter>
        <KelDefaultModelCard compact />
      </MemoryRouter>
    );
    expect((await screen.findByTestId('kel-model-older-default')).textContent).toContain('Codex answers your chats');
    fireEvent.click(screen.getByTestId('kel-default-auto'));
    await waitFor(() => expect(state.default).toBeNull());
    expect(writes(request)).toEqual([
      { action: 'set_role', role: 'kel', mode: 'AUTOMATIC', reasoning: 'high' },
      { action: 'set_default', choice: null },
    ]);
    await waitFor(() => expect(screen.queryByTestId('kel-model-older-default')).toBeNull());
  });

  it('a change from the Staff & models Kel row reaches every open surface', async () => {
    const { state } = engine({ kel: LUNA });
    render(
      <MemoryRouter>
        <KelDefaultModelCard compact />
      </MemoryRouter>
    );
    await screen.findByTestId('kel-kels-model-rows');
    const heard = vi.fn();
    window.addEventListener(KELS_MODEL_CHANGED_EVENT, heard);
    await act(async () => {
      await kelStaffSetRole('kel', { mode: 'FIXED', model: 'claude-opus-5-5', reasoning: 'auto' });
    });
    window.removeEventListener(KELS_MODEL_CHANGED_EVENT, heard);
    expect(heard).toHaveBeenCalledTimes(1);
    expect(state.kel.mode).toBe('FIXED');
    await waitFor(() => expect(screen.getByTestId('kel-kels-model-claude-opus-5-5').getAttribute('aria-pressed')).toBe('true'));
  });

  it('writing another role touches nothing else', async () => {
    const { request } = engine({ kel: LUNA });
    await kelStaffSetRole('builder', { mode: 'PREFERRED', model: 'claude-opus-5-5', reasoning: 'auto' });
    expect(writes(request).map((body) => body.action)).toEqual(['set_role']);
  });
});

describe("the composer picker is a per-chat override of Kel's model", () => {
  it("names Kel's model on the pill and in the chat tab's reset row", async () => {
    engine({ kel: LUNA });
    render(
      <MemoryRouter>
        <KelModelPill conversationId='c1' />
      </MemoryRouter>
    );
    expect(await screen.findByRole('button', { name: "Kel's model: ChatGPT Luna" })).toBeTruthy();
  });

  it("the Kel's model tab writes the Kel row; the chat tab writes only this chat", async () => {
    const choose = vi.fn(async () => undefined);
    const onChoose = vi.fn(async () => undefined);
    render(
      <KelDesktopModelMenu
        state={{ default: null, conversation: null, providers: PROVIDERS }}
        hasConversation
        kels={{ label: 'ChatGPT Luna', row: LUNA as never, models: MODELS, choose }}
        onChoose={onChoose}
        onClose={vi.fn()}
        onAdd={vi.fn()}
        onSettings={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: "Use Kel's model (ChatGPT Luna)" })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Codex' }));
    await waitFor(() => expect(onChoose).toHaveBeenCalledWith({ provider: 'codex', model: 'codex-native' }, 'conversation'));
    fireEvent.click(screen.getByRole('tab', { name: "Kel's model" }));
    expect(screen.getByRole('button', { name: /ChatGPT Luna/ }).getAttribute('aria-pressed')).toBe('true');
    expect((screen.getByRole('button', { name: /DeepSeek Flash/ }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: /Claude Opus 5.5/ }));
    await waitFor(() => expect(choose).toHaveBeenCalledWith('claude-opus-5-5'));
    expect(onChoose).toHaveBeenCalledTimes(1);
  });

  it('labels Kel’s model plainly', () => {
    expect(kelsModelLabel({ mode: 'AUTOMATIC', model: null })).toBe('Automatic');
    expect(kelsModelLabel({ mode: 'PREFERRED', model: 'gpt-6-luna', model_label: 'ChatGPT Luna' })).toBe('ChatGPT Luna');
    expect(kelsModelLabel(null)).toBeNull();
  });
});

const Where = () => {
  const location = useLocation();
  return <div data-testid='where'>{location.pathname}</div>;
};

describe('the palette finds a vetting session and opens its chat (Work panel retired)', () => {
  it('says where vetting continues and opens that chat', async () => {
    const request = vi.fn(async (route: string) => {
      if (route === '/api/search')
        return { vetting: [{ id: 'v1', title: 'Garden dashboard', snippet: '', conversation_id: 'engine-garden' }], transcripts: [], conversations: [] };
      if (route.startsWith('/api/state')) return { jobs: [], providers: [], projects: [] };
      return {};
    });
    (window as unknown as { kelAPI: unknown }).kelAPI = { request, openEngineConversation: vi.fn(async () => 'app-garden') };
    const { default: KelCommandPalette } = await import('@renderer/components/kel/KelCommandPalette');
    render(
      <MemoryRouter initialEntries={['/guid']}>
        <KelCommandPalette />
        <Routes>
          <Route path='*' element={<Where />} />
        </Routes>
      </MemoryRouter>
    );
    await act(async () => {
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    });
    // The row no longer points at the retired Work panel (its words are what the palette matches on).
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'work panel' } });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 400));
    });
    expect(screen.queryByRole('option', { name: /Garden dashboard/ })).toBeNull();
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'open its chat' } });
    const option = await screen.findByRole('option', { name: /Garden dashboard/ }, { timeout: 3000 });
    fireEvent.click(option);
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/conversation/app-garden'));
  });
});
