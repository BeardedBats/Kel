/**
 * Campaign C donor-cluster pins (AUD-MINOR-007/008/009).
 *
 * These tests assert the reachability and identity decisions mechanically:
 *  - the desktop-pet subsystem is disabled by policy and every reachable entry point is gated;
 *  - the desktop build defaults to the Kel packaging config (Kel identity) and never points
 *    electron-builder at the donor config directly;
 *  - the aioncore provenance recorder used by the packaging step exists and is wired.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { KEL_PET_SUBSYSTEM_ENABLED } from '@/process/pet/petPolicy';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoDesktop = path.resolve(here, '..', '..');
const read = (relative: string) => readFileSync(path.join(repoDesktop, relative), 'utf8');

describe('donor-surface policy (AUD-MINOR-008)', () => {
  it('the desktop pet is disabled by policy', () => {
    expect(KEL_PET_SUBSYSTEM_ENABLED).toBe(false);
  });

  it('every reachable entry point is gated by the policy', () => {
    expect(read('packages/desktop/src/process/pet/petManager.ts')).toContain('KEL_PET_SUBSYSTEM_ENABLED');
    expect(read('packages/desktop/src/process/bridge/systemSettingsBridge.ts')).toContain(
      'enabled && !KEL_PET_SUBSYSTEM_ENABLED'
    );
    expect(read('packages/desktop/src/index.ts')).toContain('petEnabled === true && KEL_PET_SUBSYSTEM_ENABLED');
  });
});

describe('desktop pet truthfulness (RA-MINOR-003)', () => {
  it('a refused enable rejects loudly instead of resolving silently', () => {
    const bridge = read('packages/desktop/src/process/bridge/systemSettingsBridge.ts');
    expect(bridge).toContain("throw new Error('The desktop pet is not available in this build");
    expect(bridge).toContain("stays off");
  });

  it('the settings toggle reverts and explains when the enable is refused', () => {
    const page = read('packages/desktop/src/renderer/pages/settings/PetSettings.tsx');
    expect(page).toContain('Message.error');
    expect(page).toMatch(/getPetEnabled\.invoke\(\)/);
    expect(page).toContain('void settle();');
  });
});

describe('Kel build identity (AUD-MINOR-009)', () => {
  const builder = read('scripts/build-with-builder.js');
  const kelConfig = JSON.parse(read('kel-builder.json'));

  it('kel-builder.json carries Kel identity', () => {
    expect(kelConfig.productName).toBe('Kel');
    expect(kelConfig.appId).toBe('com.kel.desktop');
  });

  it('the build script defaults to the Kel config and never targets the donor config directly', () => {
    expect(builder).not.toContain('--config packages/desktop/electron-builder.yml');
    expect(builder).toContain("KEL_BUILDER_CONFIG = 'kel-builder.json'");
    expect(builder).toContain('assertKelBuildIdentity();');
  });
});

describe('aioncore provenance binding (AUD-MINOR-007)', () => {
  it('the packaging step records and asserts binary provenance', () => {
    const prepare = read('packages/shared-scripts/src/prepare-aioncore.js');
    expect(prepare).toContain("writeJson(path.join(targetDir, 'provenance.json'), provenance);");
    expect(prepare).toContain('writeProvenance,');
    expect(read('scripts/build-with-builder.js')).toContain('aioncore provenance.json missing');
  });
});

describe('installer message branding (RA-MINOR-002)', () => {
  it('installer failure dialogs carry no donor product names', () => {
    const messages = read('resources/windows/installer-messages.nsh');
    expect(messages).not.toMatch(/AionUi/);
    expect(messages).not.toMatch(/AionCore/);
    expect(messages).toMatch(/Kel installation failed/);
    expect(messages).toMatch(/Kel 安装失败/);
  });

  it('the support report header and footer use Kel naming', () => {
    const report = read('resources/windows/support/report-installer-failure.ps1');
    expect(report).toContain("'Kel installer failure ' + $code");
    expect(report).toContain("'To Kel Team'");
    expect(report).not.toMatch(/AionUi Team/);
  });
});
