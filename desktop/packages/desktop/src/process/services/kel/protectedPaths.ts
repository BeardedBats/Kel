/**
 * KEL_PROTECTED_PATHS for the engine: places no model runtime may read or write (FN-01 / D-64).
 *
 * The engine's runtime guard (runtime/kel/runtime_guard.py, containment.py) reads this
 * semicolon-separated list and refuses every tool call that touches one of these folders, even in
 * Full access. The main process knows two things the engine cannot see reliably: where the
 * installed app lives, and the person's home folder. It passes the installed App folder and the
 * usual credential folders (SSH, cloud CLIs, Windows Credential Manager and DPAPI keys), keeping any
 * paths already set in the environment.
 */
import path from 'path';

/** Credential folders under the home folder (always joined with the platform separator). */
export const CREDENTIAL_FOLDERS: readonly string[][] = [
  ['.ssh'],
  ['.aws'],
  ['.azure'],
  ['.config', 'gcloud'],
  ['.kube'],
  ['.docker'],
  ['.gnupg'],
];

/** Credential folders under %APPDATA% / %LOCALAPPDATA% on Windows. */
const ROAMING_FOLDERS: readonly string[][] = [
  ['gcloud'],
  ['Microsoft', 'Credentials'],
  ['Microsoft', 'Protect'],
];
const LOCAL_FOLDERS: readonly string[][] = [
  ['Microsoft', 'Credentials'],
  ['Microsoft', 'Vault'],
];

export type ProtectedPathInput = {
  /** The existing environment value (kept first). */
  existing?: string;
  /** The person's home folder. */
  home: string;
  /** The installed app folder (the folder that holds Kel.exe); omitted when not packaged. */
  appDir?: string;
  appData?: string;
  localAppData?: string;
  platform?: NodeJS.Platform;
};

export function protectedPaths(input: ProtectedPathInput): string {
  const platform = input.platform ?? process.platform;
  const p = platform === 'win32' ? path.win32 : path.posix;
  const out: string[] = [];
  const seen = new Set<string>();
  const add = (value: string | undefined) => {
    const trimmed = (value || '').trim();
    if (!trimmed) return;
    const key = platform === 'win32' ? trimmed.toLowerCase() : trimmed;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(trimmed);
  };
  for (const part of (input.existing || '').split(';')) add(part);
  if (input.appDir) add(p.resolve(input.appDir));
  for (const parts of CREDENTIAL_FOLDERS) add(p.join(input.home, ...parts));
  if (platform === 'win32') {
    if (input.appData) for (const parts of ROAMING_FOLDERS) add(p.join(input.appData, ...parts));
    if (input.localAppData) for (const parts of LOCAL_FOLDERS) add(p.join(input.localAppData, ...parts));
  }
  return out.join(';');
}
