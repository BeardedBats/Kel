import { describe, expect, it } from 'vitest';
import { protectedPaths } from '@process/services/kel/protectedPaths';

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
