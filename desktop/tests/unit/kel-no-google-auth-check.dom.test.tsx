/**
 * ST-21 — building the model list no longer runs the donor Google Auth status check (a stub that
 * always said no and warned on every page load); only the real provider list is read.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, renderHook, waitFor } from '@testing-library/react';

const listProviders = vi.fn();
const bridgeCalls: string[] = [];

vi.mock('@/common', () => ({
  ipcBridge: new Proxy(
    {},
    {
      get: (_target, ns: string) =>
        ns === 'mode'
          ? { listProviders: { invoke: () => listProviders() } }
          : new Proxy({}, { get: (_t, name: string) => ({ invoke: () => { bridgeCalls.push(`${ns}.${name}`); return Promise.resolve(null); } }) }),
    }
  ),
}));

import { useModelProviderList } from '@renderer/hooks/agent/useModelProviderList';

afterEach(cleanup);

describe('model provider list', () => {
  it('reads providers without any Google Auth status check or stub warning', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    listProviders.mockResolvedValue([
      { id: 'p1', name: 'OpenAI', platform: 'openai', base_url: '', api_key: '', models: ['gpt-5'], enabled: true },
    ]);
    const { result } = renderHook(() => useModelProviderList());
    await waitFor(() => expect(result.current.providers.map((p) => p.id)).toEqual(['p1']));
    expect(bridgeCalls.filter((call) => /google/i.test(call))).toEqual([]);
    expect(warn.mock.calls.flat().join(' ')).not.toMatch(/googleAuth/);
    warn.mockRestore();
  });
});
