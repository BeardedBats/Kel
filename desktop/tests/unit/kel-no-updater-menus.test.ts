/**
 * D-56 — the tray and application menus carry no update or Desktop Pet entries.
 */
import { describe, expect, it, vi } from 'vitest';
import type { MenuItemConstructorOptions } from 'electron';

const built: MenuItemConstructorOptions[][] = [];

vi.mock('electron', () => ({
  app: { name: 'Kel' },
  Menu: {
    buildFromTemplate: (template: MenuItemConstructorOptions[]) => {
      built.push(template);
      return {};
    },
    setApplicationMenu: vi.fn(),
  },
}));
vi.mock('@/common/electronSafe', () => ({
  electronApp: { isPackaged: false },
  electronMenu: { buildFromTemplate: vi.fn() },
  electronNativeImage: {},
  electronTray: vi.fn(),
}));
vi.mock('@/common', () => ({ ipcBridge: {} }));
vi.mock('@process/services/i18n', () => ({ default: { t: (key: string) => key } }));

import { buildTrayMenuTemplate } from '@/process/utils/tray';
import { setupApplicationMenu } from '@/process/utils/appMenu';

const labels = (items: MenuItemConstructorOptions[]): string[] =>
  items.flatMap((item) => [
    String(item.label ?? item.role ?? ''),
    ...(Array.isArray(item.submenu) ? labels(item.submenu) : []),
  ]);

describe('menus without updater or pet', () => {
  it('the tray menu has no update check and no pet submenu', () => {
    const all = labels(buildTrayMenuTemplate([{ id: 'c1', title: 'Chat' }], 2));
    expect(all).toContain('common.tray.about');
    expect(all).toContain('common.tray.quit');
    expect(all.filter((label) => /update|pet/i.test(label))).toEqual([]);
  });

  it('the application menu has no "Check for Updates" item', () => {
    setupApplicationMenu();
    const all = labels(built.at(-1) ?? []);
    expect(all).toContain('Edit');
    expect(all.filter((label) => /update/i.test(label))).toEqual([]);
  });
});
