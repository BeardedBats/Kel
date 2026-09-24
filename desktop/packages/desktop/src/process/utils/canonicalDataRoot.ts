import path from 'path';

/** An installed Kel at Kel/App writes all durable state to its sibling Kel/Data. */
export function canonicalDataRoot(executablePath: string, isPackaged: boolean): string | null {
  if (!isPackaged) return null;
  const installDir = path.dirname(executablePath);
  const kelDir = path.dirname(installDir);
  if (path.basename(installDir).toLowerCase() !== 'app') return null;
  if (path.basename(kelDir).toLowerCase() !== 'kel') return null;
  return path.join(kelDir, 'Data');
}
