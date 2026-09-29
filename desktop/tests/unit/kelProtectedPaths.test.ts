import { describe, expect, it } from 'vitest';
import { memoryRoot, protectedPaths } from '@process/services/kel/protectedPaths';

/** FN-01: the main process hands the engine's runtime guard the app and credential folders. */
describe('protectedPaths', () => {
  const windows = {
    home: 'C:\\Users\\Nick',
    appDir: 'C:\\Users\\Nick\\Desktop\\Kel\\App',
    appData: 'C:\\Users\\Nick\\AppData\\Roaming',
    localAppData: 'C:\\Users\\Nick\\AppData\\Local',
    platform: 'win32' as const,
  };

  it('names the installed app and the credential folders, separated by semicolons', () => {
    const parts = protectedPaths(windows).split(';');
    expect(parts).toContain('C:\\Users\\Nick\\Desktop\\Kel\\App');
    for (const folder of ['.ssh', '.aws', '.azure', '.config\\gcloud']) {
      expect(parts).toContain('C:\\Users\\Nick\\' + folder);
    }
    expect(parts).toContain('C:\\Users\\Nick\\AppData\\Roaming\\gcloud');
    expect(parts).toContain('C:\\Users\\Nick\\AppData\\Roaming\\Microsoft\\Credentials');
    expect(parts).toContain('C:\\Users\\Nick\\AppData\\Local\\Microsoft\\Credentials');
    expect(parts).toContain('C:\\Users\\Nick\\AppData\\Roaming\\Microsoft\\Protect');
  });

  it('keeps paths already set, first, without duplicates', () => {
    const value = protectedPaths({ ...windows, existing: 'D:\\Secrets; c:\\users\\nick\\.ssh' });
    const parts = value.split(';');
    expect(parts[0]).toBe('D:\\Secrets');
    expect(parts.filter((p) => p.toLowerCase() === 'c:\\users\\nick\\.ssh')).toHaveLength(1);
  });

  it('leaves the app out when Kel is not the installed build', () => {
    const value = protectedPaths({ ...windows, appDir: undefined });
    expect(value).not.toContain('Desktop\\Kel\\App');
    expect(value).toContain('C:\\Users\\Nick\\.ssh');
  });
});

/** D-81: the engine is told where the Memory folder is: beside the installed App, unless already set. */
describe('memoryRoot', () => {
  it('is the Memory folder beside the installed App', () => {
    expect(memoryRoot({ appDir: 'C:\\Users\\Nick\\Desktop\\Kel\\App', platform: 'win32' })).toBe(
      'C:\\Users\\Nick\\Desktop\\Kel\\Memory'
    );
  });

  it('keeps a value already set and passes nothing for an unpackaged build', () => {
    expect(memoryRoot({ existing: 'D:\\Scratch\\Memory', appDir: 'C:\\Kel\\App', platform: 'win32' })).toBe(
      'D:\\Scratch\\Memory'
    );
    expect(memoryRoot({ platform: 'win32' })).toBeUndefined();
  });
});
