/**
 * FN-02 / FN-15: the last restore's outcome is said once, in plain words — in Settings → System
 * (Data and backup) until dismissed, and as a one-time line in the Home brief — and the restore
 * prompt only asks for keys again when they are really gone (a different PC).
 */
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/common', () => ({
  ipcBridge: { dialog: { showOpen: { invoke: vi.fn() } }, shell: { showItemInFolder: { invoke: vi.fn() } } },
}));

import { BACKUP_EXCLUDES, KelDataCard } from '@renderer/components/kel/KelDataCard';
import { buildResumptionBrief } from '@renderer/components/kel/resumptionBrief';

const FAILED = {
  ok: false,
  status: 'rolled_back',
  title: 'Kel could not restore your backup',
  detail:
    'Kel could not replace your chats because another program still had some of those files open. Kel put back everything it had changed, so your data is exactly as it was before the restore. To try again, quit Kel completely, reopen it, and choose Restore in Settings → System.',
  technical: 'PermissionError (32)',
  at: 1_790_000_000,
  notice: true,
  dismissed: false,
};

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

const mount = (outcome: unknown) => {
  const request = vi.fn(async (route: string, body: { action?: string }) => {
    if (route === '/api/data-path') return { root: 'C:\\Kel\\Data', database: 'C:\\Kel\\Data\\engine\\kel.sqlite3' };
    if (body?.action === 'outcome') return { outcome };
    return { outcome: null };
  });
  (window as unknown as { kelAPI: unknown }).kelAPI = { request };
  render(<KelDataCard />);
  return request;
};

describe('Data and backup: the last restore', () => {
  it('says what happened, which part, what Kel did and what next — the raw reason only under Details', async () => {
    const request = mount(FAILED);
    const row = await screen.findByTestId('restore-outcome');
    expect(row.textContent).toContain('Kel could not restore your backup');
    expect(row.textContent).toContain('your chats');
    expect(row.textContent).toContain('put back everything it had changed');
    expect(row.textContent).toContain('choose Restore in Settings');
    expect(row.querySelector('details')?.textContent).toContain('PermissionError');
    await act(async () => {
      fireEvent.click(screen.getByTestId('restore-outcome-dismiss'));
    });
    expect(screen.queryByTestId('restore-outcome')).toBeNull();
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/backup', { action: 'outcome-dismiss' }));
  });

  it('shows nothing when no restore was attempted or it was dismissed', async () => {
    const request = mount(null);
    await waitFor(() => expect(request).toHaveBeenCalledWith('/api/backup', { action: 'outcome' }));
    expect(screen.queryByTestId('restore-outcome')).toBeNull();
    cleanup();
    mount({ ...FAILED, dismissed: true });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByTestId('restore-outcome')).toBeNull();
  });

  it('FN-15: keys are said to stay on this PC, not to be added again after every restore', () => {
    expect(BACKUP_EXCLUDES).toMatch(/on purpose/);
    expect(BACKUP_EXCLUDES).toMatch(/stay on this PC/);
    expect(BACKUP_EXCLUDES).toMatch(/different PC/);
    expect(BACKUP_EXCLUDES).not.toMatch(/Add them again after a restore/);
  });
});

describe('Home brief: the restore line is a one-time notice', () => {
  it('uses the recorded title and words while the notice is new', () => {
    const brief = buildResumptionBrief({ restore: FAILED, now: 1_790_000_100_000 });
    const line = brief.lines.find((entry) => entry.kind === 'restore');
    expect(line?.title).toBe('Kel could not restore your backup');
    expect(line?.detail).toContain('your data is exactly as it was');
    expect(line?.detail).not.toMatch(/^PermissionError$/);
    expect(line?.action?.to).toBe('/settings/system');
  });

  it('is gone once seen', () => {
    const seen = buildResumptionBrief({ restore: { ...FAILED, notice: false }, now: 1_790_000_100_000 });
    expect(seen.lines.some((entry) => entry.kind === 'restore')).toBe(false);
    const restored = buildResumptionBrief({
      restore: { ok: true, title: 'Your backup was restored', at: 1_790_000_000, notice: false },
      now: 1_790_000_100_000,
    });
    expect(restored.lines.some((entry) => entry.kind === 'restore')).toBe(false);
  });
});
