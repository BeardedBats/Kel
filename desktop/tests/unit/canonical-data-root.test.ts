import path from 'path';
import { describe, expect, it } from 'vitest';
import { canonicalDataRoot } from '../../packages/desktop/src/process/utils/canonicalDataRoot';

describe('canonical installed data root', () => {
  const kelDir = path.join('C:', 'Users', 'Nick', 'Desktop', 'Kel');
  const installed = path.join(kelDir, 'App', 'Kel.exe');

  it('keeps the installed app on one sibling Data tree', () => {
    expect(canonicalDataRoot(installed, true)).toBe(path.join(kelDir, 'Data'));
  });

  it('leaves development and temporary candidates isolated', () => {
    expect(canonicalDataRoot(installed, false)).toBeNull();
    expect(canonicalDataRoot(path.join(kelDir, 'Temp', 'Candidate-123', 'Kel.exe'), true)).toBeNull();
  });
});
