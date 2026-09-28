/**
 * Settings → Staff & models: "When Kel asks first" — the engine's one scoping setting in plain words
 * (always for bigger work, only for very big work, never), read and written over `/api/scoping`.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ScopingThresholdCard } from '@renderer/pages/settings/StaffModelsSettings';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? key }) }));

const OPTIONS = [
  { id: 'D2', label: 'Always for bigger work', hint: 'When Kel would put a team on it. This is the default.' },
  { id: 'D3', label: 'Only for very big work', hint: 'When the work is big enough for several staff at once, or high-risk.' },
  { id: 'never', label: 'Never', hint: 'Kel starts straight away and decides the details itself.' },
];

let value = 'D2';
let fail = false;
const request = vi.fn(async (route: string, body?: { action?: string; value?: string }) => {
  if (route !== '/api/scoping') return {};
  if (body?.action === 'set_threshold') {
    if (fail) throw new Error('database is locked');
    value = body.value ?? value;
  }
  return { threshold: value, default: 'D2', options: OPTIONS };
});

beforeEach(() => {
  value = 'D2';
  fail = false;
  request.mockClear();
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('When Kel asks first', () => {
  it('shows the three plain choices with the default picked and its meaning', async () => {
    render(<ScopingThresholdCard />);
    const select = (await screen.findByTestId('scoping-threshold-select')) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe('D2'));
    expect([...select.options].map((option) => option.textContent)).toEqual(['Always for bigger work', 'Only for very big work', 'Never']);
    expect(screen.getByTestId('scoping-threshold-hint').textContent).toContain('This is the default.');
    expect(request).toHaveBeenCalledWith('/api/scoping', { action: 'threshold' });
  });

  it('writes the engine setting and shows what it now means', async () => {
    render(<ScopingThresholdCard />);
    const select = (await screen.findByTestId('scoping-threshold-select')) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe('D2'));
    fireEvent.change(select, { target: { value: 'never' } });
    await waitFor(() => expect(select.value).toBe('never'));
    expect(request).toHaveBeenCalledWith('/api/scoping', { action: 'set_threshold', value: 'never' });
    expect(screen.getByTestId('scoping-threshold-hint').textContent).toBe('Kel starts straight away and decides the details itself.');
  });

  it('says plainly when a change could not be saved', async () => {
    fail = true;
    render(<ScopingThresholdCard />);
    const select = (await screen.findByTestId('scoping-threshold-select')) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe('D2'));
    fireEvent.change(select, { target: { value: 'D3' } });
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toMatch(/^Kel couldn't save that, so nothing changed\./);
    expect(select.value).toBe('D2');
  });
});
