/**
 * VIS-26: the Back up / Restore dialog opens as a Kel modal (Figma 314:4383), not a stock Arco one.
 */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/common', () => ({
  ipcBridge: { dialog: { showOpen: { invoke: vi.fn() } }, shell: { showItemInFolder: { invoke: vi.fn() } } },
}));

import { KelDataCard } from '@renderer/components/kel/KelDataCard';

afterEach(() => {
  cleanup();
  delete (window as unknown as { kelAPI?: unknown }).kelAPI;
});

describe('Back up / Restore dialog (VIS-26)', () => {
  it.each([
    ['backup-now', 'Back up now'],
    ['restore-inspect', 'Restore from a backup'],
  ])('%s opens in the Kel modal style', async (trigger, title) => {
    (window as unknown as { kelAPI: unknown }).kelAPI = {
      request: vi.fn(async () => ({ root: 'C:\Kel\Data', database: 'C:\Kel\Data\engine\kel.sqlite3' })),
    };
    render(<KelDataCard />);
    fireEvent.click(screen.getByTestId(trigger));
    const dialog = (await screen.findByTestId('backup-dialog')).closest('.arco-modal');
    expect(dialog?.classList.contains('kel-shell-dialog-modal')).toBe(true);
    expect(dialog?.querySelector('.arco-modal-title')?.textContent).toBe(title);
  });
});
