import React from 'react';
import { Message } from '@arco-design/web-react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { KelDefaultModelCard } from '@renderer/components/kel/KelModelControl';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
it('reads and saves the default model through authenticated browser transport', async () => {
  vi.spyOn(Message, 'success').mockImplementation(() => ({} as ReturnType<typeof Message.success>));
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
  const requests: Array<{ url: string; body: Record<string, unknown> }> = [];
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const body = JSON.parse(init?.body || '{}');
    requests.push({ url: String(url), body });
    return { ok: true, json: async () => ({ default: null, conversation: null, providers: [] }) };
  }));
  render(<KelDefaultModelCard compact />);
  const automatic = await screen.findByTestId('kel-default-auto');
  fireEvent.click(automatic);
  await waitFor(() => expect(requests).toContainEqual({ url: '/kel/api/model', body: { action: 'set_default', choice: null } }));
  expect(screen.queryByText("Kel's model list is unavailable right now.")).toBeNull();
});
