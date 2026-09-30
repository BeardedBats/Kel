import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { afterEach, expect, it, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import {
  checkedKibbleInstaller,
  openKibbleInstaller,
} from '../../packages/desktop/src/process/services/kel/kibbleInstaller';

const roots: string[] = [];
afterEach(() => {
  for (const root of roots.splice(0)) fs.rmSync(root, { recursive: true, force: true });
});
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-kibble-installer-'));
  roots.push(root);
  const folder = path.join(root, 'Candidate-a123');
  fs.mkdirSync(folder);
  const installer = path.join(folder, 'Kel-Kibble-Update-1.7.0-x64.exe');
  fs.writeFileSync(installer, 'fixture installer');
  const release = {
    state: 'READY',
    candidate_path: folder,
    installer_path: installer,
    installer_sha256: createHash('sha256').update(fs.readFileSync(installer)).digest('hex'),
  };
  return { root, installer, release };
}
it('accepts only the saved ready installer with its exact build hash', () => {
  const { root, installer, release } = fixture();
  expect(checkedKibbleInstaller(release, root)).toBe(installer);
  fs.appendFileSync(installer, 'changed');
  expect(() => checkedKibbleInstaller(release, root)).toThrow('changed after');
});
it('refuses an installer outside the candidate and a build that is not ready', () => {
  const { root, installer, release } = fixture();
  expect(() => checkedKibbleInstaller({ ...release, state: 'PACKAGING' }, root)).toThrow('checked update');
  const outside = path.join(root, 'Kel-Kibble-Update-1.exe');
  fs.copyFileSync(installer, outside);
  expect(() => checkedKibbleInstaller({ ...release, installer_path: outside }, root)).toThrow('outside');
});

it('launches the installer toward canonical App without a shell or a silent install', async () => {
  const child = Object.assign(new EventEmitter(), { unref: vi.fn() });
  const launch = vi.fn(() => {
    queueMicrotask(() => child.emit('spawn'));
    return child;
  });
  await openKibbleInstaller('C:\\Kel folder\\Update.exe', 'C:\\Kel folder\\App', launch as never);
  expect(launch).toHaveBeenCalledWith('C:\\Kel folder\\Update.exe', ['/D=' + path.resolve('C:\\Kel folder\\App')], {
    detached: true,
    shell: false,
    stdio: 'ignore',
    windowsHide: false,
  });
  expect(child.unref).toHaveBeenCalledOnce();
});

it('reports launch failure instead of claiming the installer opened', async () => {
  const child = Object.assign(new EventEmitter(), { unref: vi.fn() });
  const launch = vi.fn(() => {
    queueMicrotask(() => child.emit('error', new Error('cannot launch')));
    return child;
  });
  await expect(openKibbleInstaller('Update.exe', 'App', launch as never)).rejects.toThrow('cannot launch');
  expect(child.unref).not.toHaveBeenCalled();
});
