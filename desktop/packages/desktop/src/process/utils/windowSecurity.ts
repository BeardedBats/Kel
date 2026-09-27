/**
 * CP-13 — the desktop window only ever shows Kel's own pages.
 *
 * - A link that asks for a new window (`target=_blank`, `window.open`) never opens an Electron
 *   window: web links (http/https/mailto) go to the person's own browser, anything else is refused.
 * - The app window cannot be navigated away from Kel's renderer. A navigation to a web link is
 *   handed to the browser instead; any other destination is refused.
 * - A `<webview>` (the HTML/web preview) is attached with pinned, powerless preferences: no Node,
 *   no preload, context isolation and the sandbox on. Only web, file, data and blob content may be
 *   attached.
 *
 * The dev server (http://localhost) counts as Kel's renderer only in a development build.
 */
import type { Event as ElectronEvent, WebContents, WebPreferences } from 'electron';

export interface WindowSecurityOptions {
  isPackaged: boolean;
  /** The dev server URL (`ELECTRON_RENDERER_URL`) in development builds. */
  devServerUrl?: string | null;
  /** Hands a web link to the person's browser (`shell.openExternal`). */
  openExternal: (url: string) => void;
}

const parse = (url: string): URL | null => {
  try {
    return new URL(url);
  } catch {
    return null;
  }
};

/** A link that belongs in the person's browser rather than in Kel's window. */
export const isExternalWebUrl = (url: string): boolean => {
  const parsed = parse(url);
  return parsed !== null && ['http:', 'https:', 'mailto:'].includes(parsed.protocol);
};

/** Kel's own renderer: the packaged `file:` page, or the dev server in a development build. */
export const isAppUrl = (url: string, options: Pick<WindowSecurityOptions, 'isPackaged' | 'devServerUrl'>): boolean => {
  const parsed = parse(url);
  if (!parsed) return false;
  if (parsed.protocol === 'file:') return true;
  if (options.isPackaged || !options.devServerUrl) return false;
  const dev = parse(options.devServerUrl);
  return dev !== null && parsed.origin === dev.origin;
};

/** Pin a webview's preferences so the guest page gets no Node, no preload and a sandbox. */
export const pinWebviewPreferences = (preferences: WebPreferences): WebPreferences => {
  delete preferences.preload;
  delete (preferences as WebPreferences & { preloadURL?: string }).preloadURL;
  preferences.nodeIntegration = false;
  preferences.nodeIntegrationInSubFrames = false;
  preferences.nodeIntegrationInWorker = false;
  preferences.contextIsolation = true;
  preferences.sandbox = true;
  preferences.webSecurity = true;
  preferences.allowRunningInsecureContent = false;
  preferences.webviewTag = false;
  return preferences;
};

/** Content a preview webview may show. */
export const isAllowedWebviewSource = (src: string | undefined): boolean => {
  if (!src) return true; // an empty webview (about:blank) is filled in later
  const parsed = parse(src);
  return parsed !== null && ['http:', 'https:', 'file:', 'data:', 'blob:', 'about:'].includes(parsed.protocol);
};

type WindowOpenDetails = { url: string };
type GuardableContents = Pick<WebContents, 'setWindowOpenHandler' | 'on' | 'getType'>;

/** Install the guards on one webContents (called for every webContents Electron creates). */
export const installWebContentsSecurity = (contents: GuardableContents, options: WindowSecurityOptions): void => {
  contents.setWindowOpenHandler(({ url }: WindowOpenDetails) => {
    if (isExternalWebUrl(url)) options.openExternal(url);
    return { action: 'deny' };
  });

  // Webview guests are previews of the person's own pages and may navigate within themselves; the
  // app window itself only ever shows Kel's renderer.
  if (contents.getType() === 'webview') return;

  contents.on('will-navigate', (event: ElectronEvent, url: string) => {
    if (isAppUrl(url, options)) return;
    event.preventDefault();
    if (isExternalWebUrl(url)) options.openExternal(url);
  });

  contents.on(
    'will-attach-webview',
    (event: ElectronEvent, preferences: WebPreferences, params: Record<string, string | undefined>) => {
      pinWebviewPreferences(preferences);
      if (!isAllowedWebviewSource(params.src)) event.preventDefault();
    }
  );
};
