/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import type { MenuItemConstructorOptions } from 'electron';
import { Menu, app } from 'electron';

/**
 * CP-13: a packaged Kel has no developer entries — no reload (which would drop live work), no
 * DevTools and no full-screen toggle (F11). Development builds keep them.
 */
export function buildApplicationMenuTemplate(
  isPackaged: boolean,
  platform: NodeJS.Platform = process.platform
): MenuItemConstructorOptions[] {
  const isMac = platform === 'darwin';

  const template: MenuItemConstructorOptions[] = [];

  if (isMac) {
    template.push({
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    });
  }

  template.push({
    label: 'Edit',
    submenu: [
      { role: 'undo' },
      { role: 'redo' },
      { type: 'separator' },
      { role: 'cut' },
      { role: 'copy' },
      { role: 'paste' },
      ...(isMac
        ? ([{ role: 'pasteAndMatchStyle' }, { role: 'delete' }, { role: 'selectAll' }] as MenuItemConstructorOptions[])
        : ([{ role: 'delete' }, { type: 'separator' }, { role: 'selectAll' }] as MenuItemConstructorOptions[])),
    ],
  });

  const developerEntries: MenuItemConstructorOptions[] = isPackaged
    ? []
    : [{ role: 'reload' }, { role: 'forceReload' }, { role: 'toggleDevTools' }, { type: 'separator' }];
  template.push({
    label: 'View',
    submenu: [
      ...developerEntries,
      { role: 'resetZoom' },
      { role: 'zoomIn' },
      { role: 'zoomOut' },
      ...(isPackaged ? [] : ([{ type: 'separator' }, { role: 'togglefullscreen' }] as MenuItemConstructorOptions[])),
    ],
  });

  return template;
}

export function setupApplicationMenu(): void {
  const menu = Menu.buildFromTemplate(buildApplicationMenuTemplate(app.isPackaged));
  Menu.setApplicationMenu(menu);
}
