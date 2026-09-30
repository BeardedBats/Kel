import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';

/** NSIS reads /D as its last argument. An argument array preserves spaces without shell quoting. */
export async function openKibbleInstaller(installer: string, appRoot: string, launch = spawn): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const child = launch(installer, ['/D=' + path.resolve(appRoot)], {
      detached: true,
      shell: false,
      stdio: 'ignore',
      windowsHide: false,
    });
    child.once('error', reject);
    child.once('spawn', () => {
      child.unref();
      resolve();
    });
  });
}

/** Only the engine's saved, hashed candidate can be launched. Renderer paths are never accepted. */
export function checkedKibbleInstaller(release: unknown, tempRoot: string): string {
  const candidate = release as {
    state?: string;
    candidate_path?: string;
    installer_path?: string;
    installer_sha256?: string;
  };
  if (
    !candidate ||
    candidate.state !== 'READY' ||
    !candidate.installer_path ||
    !candidate.candidate_path ||
    !candidate.installer_sha256
  ) {
    throw new Error('Build a checked update before installing it.');
  }
  const allowed = fs.realpathSync(tempRoot);
  const folder = fs.realpathSync(candidate.candidate_path);
  const target = fs.realpathSync(candidate.installer_path);
  if (
    path.dirname(folder) !== allowed ||
    !/^Candidate-[a-f0-9]+$/i.test(path.basename(folder)) ||
    path.dirname(target) !== folder ||
    !/^Kel-Kibble-Update-.*\.exe$/i.test(path.basename(target))
  ) {
    throw new Error('This installer is outside Kel’s candidate folder.');
  }
  const digest = createHash('sha256').update(fs.readFileSync(target)).digest('hex');
  if (digest !== candidate.installer_sha256)
    throw new Error('This installer changed after its build. Build the update again.');
  return target;
}
