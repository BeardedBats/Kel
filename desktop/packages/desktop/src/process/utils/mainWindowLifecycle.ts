/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { app, type BrowserWindow } from 'electron';
import { setApplicationMainWindow } from '../bridge/applicationBridge';
import { setNotificationMainWindow } from '../bridge/notificationBridge';
import { setDeepLinkMainWindow } from './deepLink';
import { setTrayMainWindow } from './tray';

export const bindMainWindowReferences = (window: BrowserWindow): void => {
  setTrayMainWindow(window);
  setDeepLinkMainWindow(window);
  setApplicationMainWindow(window);
  setNotificationMainWindow(window);
};

export const showAndFocusMainWindow = (window: BrowserWindow): void => {
  if (window.isMinimized()) {
    window.restore();
  }
  window.show();
  window.focus();
  app.focus({ steal: true });
  // Windows may refuse to activate the window when another app owns the
  // foreground lock (e.g. a second-instance launch). If focus was denied,
  // visibly request attention instead of doing nothing; clear the flash once
  // the window actually gains focus.
  setTimeout(() => {
    if (!window.isDestroyed() && !window.isFocused()) {
      console.log('[Kel] focus was denied (foreground lock); flashing taskbar to request attention');
      window.flashFrame(true);
      window.once('focus', () => {
        if (!window.isDestroyed()) {
          window.flashFrame(false);
        }
      });
    }
  }, 250);
};

export const showOrCreateMainWindow = ({
  mainWindow,
  createWindow,
}: {
  mainWindow: BrowserWindow | null | undefined;
  createWindow: () => void;
}): void => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    showAndFocusMainWindow(mainWindow);
    return;
  }

  createWindow();
};
