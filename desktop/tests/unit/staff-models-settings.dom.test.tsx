/**
 * D-70 item 3 — Settings → Staff & models. One row per staff role over the engine's `/api/model`
 * roles actions (D-66 design §2): the page shows what the engine lists (order, labels, modes,
 * models, reasoning levels), writes go through set_role / reset_role, a model the engine says cannot
 * run here reads "Can't run here" with the engine's reason and what Kel does instead, and a failed
 * write says what happened and what to do without raw error text.
 */
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StaffModelsSettings from '@renderer/pages/settings/StaffModelsSettings';
import { KelDesktopModelMenu } from '@renderer/components/kel/KelDesktopModelMenu';
import { KEL_MODEL_SCOPE_NOTE } from '@renderer/components/kel/KelModelControl';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key }) }));

type Row = Record<string, unknown> & { role: string };

const MODELS = [
  { id: 'gpt-6-luna', label: 'ChatGPT Luna', available: true, reasoning_options: ['auto', 'low', 'medium', 'high', 'xhigh', 'max'] },
  { id: 'gpt-6-astra', label: 'GPT-6 Astra', available: true, reasoning_options: ['auto', 'low', 'medium', 'high', 'xhigh', 'ultra'] },
  { id: 'claude-opus-5-5', label: 'Claude Opus 5.5', available: false, note: 'Claude Opus 5.5 needs Claude Code, which is not set up on this computer', reasoning_options: ['auto', 'low', 'medium', 'high', 'xhigh', 'max'] },
  { id: 'claude-sonnet', label: 'Claude Sonnet', available: true, reasoning_options: ['auto', 'low', 'medium', 'high', 'xhigh', 'max'] },
  { id: 'deepseek-flash', label: 'DeepSeek Flash', available: false, note: 'DeepSeek Flash has no DeepSeek connection in this version of Kel', reasoning_options: ['auto'] },
];

const DEFAULTS: Record<string, [string, string | null]> = {
  kel: ['PREFERRED', 'gpt-6-luna'],
  discovery: ['PREFERRED', 'claude-sonnet'],
  designer: ['PREFERRED', 'claude-sonnet'],
  builder: ['PREFERRED', 'claude-opus-5-5'],
  verifier: ['PREFERRED', 'gpt-6-astra'],
  oracle: ['PREFERRED', 'gpt-6-astra'],
  utility: ['PREFERRED', 'deepseek-flash'],
  architect: ['AUTOMATIC', null],
  sentinel: ['AUTOMATIC', null],
  release: ['AUTOMATIC', null],
};
const LABELS: Record<string, string> = {
  kel: 'Kel', discovery: 'Discovery (research)', designer: 'Designer', builder: 'Builder', verifier: 'Verifier',
  oracle: 'Oracle (second opinion)', utility: 'Utility work', architect: 'Architect', sentinel: 'Sentinel', release: 'Release',
};

/** A tiny engine: the same listing rules as runtime/kel/role_models.py `listing`. */
const makeEngine = () => {
  const saved: Record<string, { mode: string; model: string | null; reasoning: string }> = {};
  const row = (role: string): Row => {
    const [mode, model] = DEFAULTS[role];
    const current = saved[role] ?? { mode, model, reasoning: 'auto' };
    const info = MODELS.find((entry) => entry.id === current.model);
    return {
      role,
      label: LABELS[role],
      mode: current.mode,
      model: current.model,
      model_label: info?.label ?? null,
      reasoning: current.reasoning,
      reasoning_options: info ? info.reasoning_options : ['auto'],
      available: info ? info.available : true,
      note: info && !info.available ? info.note : null,
      is_default: !saved[role],
      fallbacks: role === 'builder' ? ['Codex'] : [],
      default: { mode, model, reasoning: 'auto' },
    };
  };
  // Engine order (role_models.ROLES), not the order the page shows.
  const listing = () => ({ roles: Object.keys(DEFAULTS).map(row), models: MODELS, modes: [] });
  const request = vi.fn(async (route: string, body?: { action?: string; role?: string; mode?: string; model?: string; reasoning?: string }) => {
    if (route !== '/api/model') return {};
    if (body?.action === 'set_role' && body.role) {
      saved[body.role] = { mode: body.mode!, model: body.mode === 'AUTOMATIC' ? null : (body.model ?? null), reasoning: body.reasoning ?? 'auto' };
    }
    if (body?.action === 'reset_role' && body.role) delete saved[body.role];
    return listing();
  });
  return { request, saved };
};

let engine: ReturnType<typeof makeEngine>;

beforeEach(() => {
  engine = makeEngine();
  (window as unknown as { kelAPI: unknown }).kelAPI = { request: engine.request };
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/settings/staff']}>
      <StaffModelsSettings />
    </MemoryRouter>
  );

const rowFor = (role: string) => screen.getByTestId(`staff-row-${role}`);

describe('Settings → Staff & models (D-70 item 3)', () => {
  it('loads every role from the engine, in the order work flows, with a plain line each', async () => {
    renderPage();
    await screen.findByTestId('staff-row-kel');
    expect(engine.request).toHaveBeenCalledWith('/api/model', { action: 'roles' });
    const order = Array.from(document.querySelectorAll('[data-testid^="staff-row-"]')).map((el) => el.getAttribute('data-role'));
    expect(order).toEqual(['kel', 'discovery', 'architect', 'designer', 'builder', 'verifier', 'sentinel', 'release', 'oracle', 'utility']);
    expect(screen.getByRole('heading', { name: 'Staff & models' })).toBeTruthy();
    // D-87: no description of how staff work above the rows.
    expect(screen.queryByTestId('staff-defaults-note')).toBeNull();
    expect(within(rowFor('builder')).getByText('Writes the code and builds the pages.')).toBeTruthy();
    const kelModel = within(rowFor('kel')).getByRole('combobox', { name: 'Kel: model' }) as HTMLSelectElement;
    expect(kelModel.value).toBe('gpt-6-luna');
    const architectModel = within(rowFor('architect')).getByRole('combobox', { name: 'Architect: model' }) as HTMLSelectElement;
    expect(architectModel.disabled).toBe(true);
    expect(architectModel.selectedOptions[0].textContent).toBe('Kel chooses');
    // Every row starts on its default, so none offers a reset.
    expect(screen.queryByRole('button', { name: /^Reset / })).toBeNull();
  });

  it('shows honest availability: the engine reason and what Kel does instead', async () => {
    renderPage();
    await screen.findByTestId('staff-row-builder');
    const builder = rowFor('builder');
    expect(within(builder).getByText("Can't run here")).toBeTruthy();
    expect(screen.getByTestId('staff-note-builder').textContent).toBe(
      'Claude Opus 5.5 needs Claude Code, which is not set up on this computer. Kel falls back to Codex and says so on the work card.'
    );
    expect(screen.getByTestId('staff-note-utility').textContent).toContain('has no DeepSeek connection in this version of Kel');
    expect(within(rowFor('verifier')).getByText('Available')).toBeTruthy();
    // Unavailable models stay choosable (Preferred falls back) but say so in the list.
    const options = Array.from((within(builder).getByRole('combobox', { name: 'Builder: model' }) as HTMLSelectElement).options).map((o) => o.textContent);
    expect(options).toContain('DeepSeek Flash (unavailable)');
    expect(options).toContain('GPT-6 Astra');
  });

  it('sets a role through set_role and shows the engine’s answer, then resets it', async () => {
    renderPage();
    await screen.findByTestId('staff-row-verifier');
    await act(async () => {
      fireEvent.change(within(rowFor('verifier')).getByRole('combobox', { name: 'Verifier: reasoning' }), { target: { value: 'ultra' } });
    });
    expect(engine.request).toHaveBeenCalledWith('/api/model', { action: 'set_role', role: 'verifier', mode: 'PREFERRED', model: 'gpt-6-astra', reasoning: 'ultra' });
    await waitFor(() => expect((within(rowFor('verifier')).getByRole('combobox', { name: 'Verifier: reasoning' }) as HTMLSelectElement).value).toBe('ultra'));
    expect(within(rowFor('verifier')).getByText('Default: Preferred · GPT-6 Astra')).toBeTruthy();

    // Changing the model keeps a level the new model offers, and drops one it does not.
    await act(async () => {
      fireEvent.change(within(rowFor('verifier')).getByRole('combobox', { name: 'Verifier: model' }), { target: { value: 'claude-sonnet' } });
    });
    expect(engine.request).toHaveBeenLastCalledWith('/api/model', { action: 'set_role', role: 'verifier', mode: 'PREFERRED', model: 'claude-sonnet', reasoning: 'auto' });

    // Fixed with a model that cannot run: the work waits, and the row says what to do.
    await act(async () => {
      fireEvent.change(within(rowFor('verifier')).getByRole('combobox', { name: 'Verifier: model' }), { target: { value: 'claude-opus-5-5' } });
    });
    await act(async () => {
      fireEvent.change(within(rowFor('verifier')).getByRole('combobox', { name: 'Verifier: mode' }), { target: { value: 'FIXED' } });
    });
    expect(engine.request).toHaveBeenLastCalledWith('/api/model', { action: 'set_role', role: 'verifier', mode: 'FIXED', model: 'claude-opus-5-5', reasoning: 'auto' });
    await waitFor(() => expect(screen.getByTestId('staff-note-verifier').textContent).toContain('Work for this role waits until it can run. Pick another model, or switch to Preferred.'));

    await act(async () => {
      fireEvent.click(within(rowFor('verifier')).getByRole('button', { name: 'Reset Verifier to default' }));
    });
    expect(engine.request).toHaveBeenLastCalledWith('/api/model', { action: 'reset_role', role: 'verifier' });
    await waitFor(() => expect((within(rowFor('verifier')).getByRole('combobox', { name: 'Verifier: model' }) as HTMLSelectElement).value).toBe('gpt-6-astra'));
    expect(within(rowFor('verifier')).queryByRole('button', { name: 'Reset Verifier to default' })).toBeNull();
  });

  it('switches a role to Automatic without a model, and back to Preferred on its default model', async () => {
    renderPage();
    await screen.findByTestId('staff-row-discovery');
    await act(async () => {
      fireEvent.change(within(rowFor('discovery')).getByRole('combobox', { name: 'Discovery (research): mode' }), { target: { value: 'AUTOMATIC' } });
    });
    expect(engine.request).toHaveBeenLastCalledWith('/api/model', { action: 'set_role', role: 'discovery', mode: 'AUTOMATIC', reasoning: 'auto' });
    await act(async () => {
      fireEvent.change(within(rowFor('architect')).getByRole('combobox', { name: 'Architect: mode' }), { target: { value: 'PREFERRED' } });
    });
    // Architect has no default model, so the first model that can run here is used.
    expect(engine.request).toHaveBeenLastCalledWith('/api/model', { action: 'set_role', role: 'architect', mode: 'PREFERRED', model: 'gpt-6-luna', reasoning: 'auto' });
  });

  it('says what happened and what to do when a write fails, with no raw error text', async () => {
    engine.request.mockImplementation(async (_route: string, body?: { action?: string }) => {
      if (body?.action === 'set_role') throw new Error('Claude Sonnet does not offer Ultra reasoning.');
      if (body?.action === 'reset_role') throw new Error("Error invoking remote method 'kel:request': TypeError: fetch failed");
      return { roles: [{ role: 'designer', label: 'Designer', mode: 'PREFERRED', model: 'claude-sonnet', reasoning: 'auto', reasoning_options: ['auto', 'low'], available: true, is_default: false, default: { mode: 'PREFERRED', model: 'claude-fable-5-1', reasoning: 'auto' } }], models: MODELS };
    });
    renderPage();
    await screen.findByTestId('staff-row-designer');
    await act(async () => {
      fireEvent.change(within(rowFor('designer')).getByRole('combobox', { name: 'Designer: reasoning' }), { target: { value: 'low' } });
    });
    expect((await within(rowFor('designer')).findByRole('alert')).textContent).toBe(
      "Kel couldn't save that change for Designer, so nothing changed. Claude Sonnet does not offer Ultra reasoning."
    );
    await act(async () => {
      fireEvent.click(within(rowFor('designer')).getByRole('button', { name: 'Reset Designer to default' }));
    });
    const alert = await within(rowFor('designer')).findByRole('alert');
    expect(alert.textContent).toMatch(/^Kel couldn't reset the model for Designer, so nothing changed\. /);
    expect(alert.textContent).not.toMatch(/invoking|TypeError|fetch failed|kel:request/);
  });

  it('shows a plain failure with a retry when the roles cannot be read', async () => {
    engine.request.mockRejectedValueOnce(new Error('connect ECONNREFUSED 127.0.0.1:8765'));
    renderPage();
    const retry = await screen.findByRole('button', { name: 'Try again' });
    expect(document.body.textContent).not.toMatch(/ECONNREFUSED|127\.0\.0\.1/);
    await act(async () => {
      fireEvent.click(retry);
    });
    expect(await screen.findByTestId('staff-row-kel')).toBeTruthy();
  });
});

describe("the composer's picker is Kel's own model (D-69)", () => {
  it('says staff use their own models and links to Staff & models', () => {
    const onStaff = vi.fn();
    const state = { default: null, conversation: null, providers: [] };
    render(<KelDesktopModelMenu state={state} hasConversation onChoose={vi.fn(async () => {})} onClose={vi.fn()} onAdd={vi.fn()} onSettings={vi.fn()} onStaff={onStaff} />);
    expect(screen.getByTestId('kel-model-menu-caption').textContent).toBe(KEL_MODEL_SCOPE_NOTE);
    expect(KEL_MODEL_SCOPE_NOTE).toBe("Kel's model — staff use their own (Settings → Staff & models)");
    fireEvent.click(screen.getByRole('button', { name: 'Staff & models' }));
    expect(onStaff).toHaveBeenCalledTimes(1);
  });
});
