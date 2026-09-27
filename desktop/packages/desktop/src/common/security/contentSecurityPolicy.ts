/**
 * CP-13 — the renderer's Content Security Policy (packaged builds and the WebUI).
 *
 * Injected as a `<meta http-equiv="Content-Security-Policy">` into the built `index.html` (the
 * desktop window loads it from `file:`, where there are no response headers; the WebUI serves the
 * same file). Development builds (Vite dev server, hot reload) run without it.
 *
 * What the renderer actually needs:
 * - scripts: only Kel's own bundle ('self'). No inline script, no eval, no CDN.
 * - styles: Kel's own CSS plus inline styles (Arco, CodeMirror and the Markdown shadow view inject
 *   <style> elements at runtime).
 * - connections: the local backend and its WebSocket on 127.0.0.1/localhost (desktop), or the page's
 *   own origin (WebUI, including its WebSocket).
 * - images and media: Kel's files, data:/blob: URLs, local files, and web images shown in replies.
 * - frames (HTML/web previews): the person's own pages and web pages; they never get Kel's powers
 *   (see process/utils/windowSecurity.ts for the webview side).
 */
export const CONTENT_SECURITY_POLICY_DIRECTIVES: Readonly<Record<string, readonly string[]>> = {
  'default-src': ["'self'"],
  'script-src': ["'self'"],
  'style-src': ["'self'", "'unsafe-inline'"],
  'img-src': ["'self'", 'data:', 'blob:', 'file:', 'https:', 'http://127.0.0.1:*', 'http://localhost:*'],
  'font-src': ["'self'", 'data:'],
  'media-src': ["'self'", 'data:', 'blob:', 'file:', 'mediastream:'],
  'connect-src': [
    "'self'",
    'http://127.0.0.1:*',
    'ws://127.0.0.1:*',
    'http://localhost:*',
    'ws://localhost:*',
    'data:',
    'blob:',
  ],
  'frame-src': ["'self'", 'data:', 'blob:', 'file:', 'http:', 'https:'],
  'worker-src': ["'self'", 'blob:'],
  'manifest-src': ["'self'"],
  'object-src': ["'none'"],
  'base-uri': ["'self'"],
  'form-action': ["'self'"],
};

export const CONTENT_SECURITY_POLICY = Object.entries(CONTENT_SECURITY_POLICY_DIRECTIVES)
  .map(([directive, sources]) => `${directive} ${sources.join(' ')}`)
  .join('; ');

export const CONTENT_SECURITY_POLICY_META = `<meta http-equiv="Content-Security-Policy" content="${CONTENT_SECURITY_POLICY}" />`;

/** Put the policy first in <head> so it covers every resource the page loads. */
export const injectContentSecurityPolicy = (html: string): string =>
  html.includes('http-equiv="Content-Security-Policy"')
    ? html
    : html.replace(/<head>/i, `<head>\n    ${CONTENT_SECURITY_POLICY_META}`);
