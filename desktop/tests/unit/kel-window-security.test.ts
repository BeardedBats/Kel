/**
 * CP-13 — the desktop window keeps to Kel's own pages: new windows are refused (web links go to the
 * browser), the app window cannot be navigated away, preview webviews get pinned powerless
 * preferences, a packaged build refuses a remote debugging port unless KEL_ALLOW_DEBUG_PORT=1, the
 * packaged menu has no developer entries, and the built page carries a strict CSP.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it, vi } from 'vitest';
import type { MenuItemConstructorOptions, WebPreferences } from 'electron';

vi.mock('electron', () => ({
  app: { name: 'Kel', isPackaged: true },
  Menu: { buildFromTemplate: vi.fn(), setApplicationMenu: vi.fn() },
}));

import {
  installWebContentsSecurity,
  isAllowedWebviewSource,
  isAppUrl,
  isExternalWebUrl,
  pinWebviewPreferences,
} from '@process/utils/windowSecurity';
import { debugPortRefusal, hasRemoteDebuggingSwitch } from '@process/utils/debugPortPolicy';
import { buildApplicationMenuTemplate } from '@process/utils/appMenu';
import {
  CONTENT_SECURITY_POLICY,
  CONTENT_SECURITY_POLICY_DIRECTIVES,
  injectContentSecurityPolicy,
} from '@/common/security/contentSecurityPolicy';

type Handler = (...args: unknown[]) => void;
const fakeContents = (type: string) => {
  const handlers = new Map<string, Handler>();
  let openHandler: ((details: { url: string }) => { action: string }) | null = null;
  return {
    handlers,
    open: (url: string) => openHandler!({ url }),
    contents: {
      getType: () => type,
      setWindowOpenHandler: (handler: (details: { url: string }) => { action: string }) => {
        openHandler = handler;
      },
      on: (name: string, handler: Handler) => {
        handlers.set(name, handler);
      },
    },
  };
};
const event = () => ({ preventDefault: vi.fn() });

describe('window guards (CP-13)', () => {
  const packaged = { isPackaged: true, devServerUrl: null };

  it('knows Kel pages from web links', () => {
    expect(isAppUrl('file:///C:/Kel/resources/app/out/renderer/index.html#/guid', packaged)).toBe(true);
    expect(isAppUrl('http://localhost:5173/', packaged)).toBe(false);
    expect(isAppUrl('http://localhost:5173/#/guid', { isPackaged: false, devServerUrl: 'http://localhost:5173' })).toBe(true);
    expect(isAppUrl('http://localhost:9999/', { isPackaged: false, devServerUrl: 'http://localhost:5173' })).toBe(false);
    expect(isExternalWebUrl('https://example.com')).toBe(true);
    expect(isExternalWebUrl('mailto:nick@example.com')).toBe(true);
    expect(isExternalWebUrl('file:///C:/Windows/System32/calc.exe')).toBe(false);
    expect(isExternalWebUrl('javascript:alert(1)')).toBe(false);
  });

  it('never opens an Electron window; web links go to the browser', () => {
    const openExternal = vi.fn();
    const window = fakeContents('window');
    installWebContentsSecurity(window.contents as never, { ...packaged, openExternal });
    expect(window.open('https://example.com/docs')).toEqual({ action: 'deny' });
    expect(openExternal).toHaveBeenCalledWith('https://example.com/docs');
    expect(window.open('file:///C:/secret.txt')).toEqual({ action: 'deny' });
    expect(openExternal).toHaveBeenCalledTimes(1);
  });

  it('keeps the app window on Kel pages and sends web links to the browser', () => {
    const openExternal = vi.fn();
    const window = fakeContents('window');
    installWebContentsSecurity(window.contents as never, { ...packaged, openExternal });
    const navigate = window.handlers.get('will-navigate')!;
    const toWeb = event();
    navigate(toWeb, 'https://evil.example/login');
    expect(toWeb.preventDefault).toHaveBeenCalled();
    expect(openExternal).toHaveBeenCalledWith('https://evil.example/login');
    const toOwnPage = event();
    navigate(toOwnPage, 'file:///C:/Kel/out/renderer/index.html');
    expect(toOwnPage.preventDefault).not.toHaveBeenCalled();
    const toDevServer = event();
    navigate(toDevServer, 'http://localhost:5173/');
    expect(toDevServer.preventDefault).toHaveBeenCalled();
  });

  it('attaches preview webviews with no Node, no preload and a sandbox', () => {
    const window = fakeContents('window');
    installWebContentsSecurity(window.contents as never, { ...packaged, openExternal: vi.fn() });
    const attach = window.handlers.get('will-attach-webview')!;
    const prefs = {
      preload: 'C:/evil/preload.js',
      nodeIntegration: true,
      contextIsolation: false,
      sandbox: false,
      allowRunningInsecureContent: true,
    } as WebPreferences;
    const ok = event();
    attach(ok, prefs, { src: 'file:///C:/project/index.html' });
    expect(ok.preventDefault).not.toHaveBeenCalled();
    expect(prefs).toMatchObject({
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      allowRunningInsecureContent: false,
      webviewTag: false,
    });
    expect(prefs.preload).toBeUndefined();
    const bad = event();
    attach(bad, {} as WebPreferences, { src: 'chrome://settings' });
    expect(bad.preventDefault).toHaveBeenCalled();
    expect(isAllowedWebviewSource('https://example.com')).toBe(true);
    expect(pinWebviewPreferences({ nodeIntegrationInSubFrames: true } as WebPreferences).nodeIntegrationInSubFrames).toBe(false);
  });

  it('lets a preview webview navigate inside itself but not open windows', () => {
    const openExternal = vi.fn();
    const guest = fakeContents('webview');
    installWebContentsSecurity(guest.contents as never, { ...packaged, openExternal });
    expect(guest.handlers.has('will-navigate')).toBe(false);
    expect(guest.open('https://example.com')).toEqual({ action: 'deny' });
    expect(openExternal).toHaveBeenCalledWith('https://example.com');
  });
});

describe('remote debugging port (CP-13)', () => {
  it('refuses the switch in a packaged build unless KEL_ALLOW_DEBUG_PORT=1', () => {
    const argv = ['Kel.exe', '--remote-debugging-port=9333'];
    expect(hasRemoteDebuggingSwitch(argv)).toBe(true);
    expect(hasRemoteDebuggingSwitch(['Kel.exe', '--remote-debugging-pipe'])).toBe(true);
    expect(hasRemoteDebuggingSwitch(['Kel.exe'])).toBe(false);
    expect(debugPortRefusal({ isPackaged: true, argv, env: {} })).toMatch(/KEL_ALLOW_DEBUG_PORT=1/);
    expect(debugPortRefusal({ isPackaged: true, argv, env: { KEL_ALLOW_DEBUG_PORT: '1' } })).toBeNull();
    expect(debugPortRefusal({ isPackaged: true, argv, env: { KEL_ALLOW_DEBUG_PORT: 'yes' } })).not.toBeNull();
    expect(debugPortRefusal({ isPackaged: false, argv, env: {} })).toBeNull();
    expect(debugPortRefusal({ isPackaged: true, argv: ['Kel.exe'], env: {} })).toBeNull();
  });
});

const roles = (items: MenuItemConstructorOptions[]): string[] =>
  items.flatMap((item) => [
    String(item.role ?? item.label ?? ''),
    ...(Array.isArray(item.submenu) ? roles(item.submenu) : []),
  ]);

describe('application menu (CP-13)', () => {
  it('has no reload, DevTools or full-screen entries when packaged', () => {
    for (const platform of ['win32', 'darwin'] as const) {
      const all = roles(buildApplicationMenuTemplate(true, platform));
      expect(all).toEqual(expect.arrayContaining(['copy', 'paste', 'zoomIn', 'resetZoom']));
      expect(all.filter((role) => /reload|devtools|fullscreen/i.test(role))).toEqual([]);
    }
  });

  it('keeps the developer entries in a development build', () => {
    const all = roles(buildApplicationMenuTemplate(false, 'win32'));
    expect(all).toEqual(expect.arrayContaining(['reload', 'forceReload', 'toggleDevTools', 'togglefullscreen']));
  });
});

describe('renderer Content Security Policy (CP-13)', () => {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const html = readFileSync(path.resolve(here, '../../packages/desktop/src/renderer/index.html'), 'utf8');

  it('forbids inline and remote scripts and plug-ins', () => {
    expect(CONTENT_SECURITY_POLICY_DIRECTIVES['script-src']).toEqual(["'self'"]);
    expect(CONTENT_SECURITY_POLICY_DIRECTIVES['object-src']).toEqual(["'none'"]);
    expect(CONTENT_SECURITY_POLICY).not.toMatch(/unsafe-eval|script-src[^;]*unsafe-inline|script-src[^;]*https:/);
  });

  it('is injected first into the built page, once', () => {
    const built = injectContentSecurityPolicy(html);
    const head = built.slice(built.indexOf('<head>'), built.indexOf('</head>'));
    expect(head.indexOf('http-equiv="Content-Security-Policy"')).toBeGreaterThan(-1);
    expect(head.indexOf('http-equiv="Content-Security-Policy"')).toBeLessThan(head.indexOf('<script'));
    expect(injectContentSecurityPolicy(built)).toBe(built);
  });

  it('leaves no inline script in the page (they would be blocked)', () => {
    const scripts = html.match(/<script\b[^>]*>/g) ?? [];
    expect(scripts.length).toBeGreaterThan(0);
    for (const tag of scripts) expect(tag).toMatch(/\ssrc=/);
  });
});
