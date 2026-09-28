/**
 * The result card names where a change went once: the project's name and its folder, never the full
 * path twice. The full path stays reachable through "Open folder".
 */
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { applicationLine, folderName, placeWords } from '@renderer/components/kel/changeApplication';
import { KelDoneCard, withoutPlace } from '@renderer/components/kel/workCards/KelDoneCard';
import type { OfficeItemDetail } from '@renderer/components/kel/workCards/officeApi';
import { AT, RECEIPTS_DETAIL } from './fixtures/kelOfficeFixtures';

afterEach(() => cleanup());

const ROOT = 'C:\\Users\\Nick\\Desktop\\R6Proj';

describe('where a change went, in words', () => {
  it('is the project name and its folder, or just the folder', () => {
    expect(folderName(ROOT)).toBe('R6Proj');
    expect(folderName('/home/nick/calc/')).toBe('calc');
    expect(placeWords({ state: 'APPLIED', auto: true, root: ROOT, files: 2, waiting_reason: null, project_name: 'Calc demo', folder: 'R6Proj' })).toBe(
      'Calc demo (folder R6Proj)'
    );
    expect(placeWords({ state: 'APPLIED', auto: true, root: ROOT, files: 2, waiting_reason: null, project_name: 'R6Proj' })).toBe('R6Proj');
    expect(placeWords({ state: 'APPLIED', auto: true, root: ROOT, files: 2, waiting_reason: null })).toBe('R6Proj');
    expect(applicationLine({ state: 'APPLIED', auto: true, root: ROOT, files: 2, waiting_reason: null })).toBe(
      'Applied automatically to R6Proj (2 files). The earlier files are saved.'
    );
  });

  it('drops the "Applied to <place>:" lead from the result sentence, old full paths included', () => {
    expect(withoutPlace('Applied to Calc demo (folder R6Proj): changed calc.py; added test_calc.py (2 files).')).toBe(
      'Changed calc.py; added test_calc.py (2 files).'
    );
    expect(withoutPlace(`Applied to ${ROOT}: changed calc.py (1 file).`)).toBe('Changed calc.py (1 file).');
    expect(withoutPlace('Your new project is ready. Applied to calc-app: added app.py (1 file).')).toBe('Added app.py (1 file).');
    expect(withoutPlace('A tray app that mutes your mic.')).toBe('A tray app that mutes your mic.');
  });
});

describe('the done card', () => {
  it('shows the name and folder once and keeps the full path behind Open folder', async () => {
    const detail: OfficeItemDetail = {
      ...RECEIPTS_DETAIL,
      job_id: 'job-calc',
      title: 'Add multiply to calc.py',
      kind: 'code',
      finished_at: AT(10, 31),
      result: `Applied to Calc demo (folder R6Proj): changed calc.py; changed test_calc.py (2 files).\n\nHow it was checked: \`pytest\` passed.`,
      application: { state: 'APPLIED', auto: true, root: ROOT, files: 2, waiting_reason: null, project_name: 'Calc demo', folder: 'R6Proj' },
    };
    (window as unknown as { kelAPI: unknown }).kelAPI = { request: vi.fn(async () => detail) };
    const openFolder = vi.fn(async () => undefined);
    render(<KelDoneCard job='job-calc' openFolder={openFolder} />);
    const card = await screen.findByTestId('kel-done-card');
    expect(card.textContent).not.toContain(ROOT);
    expect(card.textContent?.match(/R6Proj/g)?.length).toBe(1);
    expect(within(card).getByText('Changed calc.py; changed test_calc.py (2 files).')).toBeTruthy();
    expect(within(card).getByTestId('kel-done-card-applied').textContent).toBe(
      'Applied to Calc demo (folder R6Proj) at 10:31 AM · you can undo it'
    );
    fireEvent.click(within(card).getByTestId('kel-done-card-folder'));
    await waitFor(() => expect(openFolder).toHaveBeenCalledWith(ROOT));
  });
});
