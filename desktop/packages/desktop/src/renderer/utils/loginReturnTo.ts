/**
 * Where a signed-out visitor was heading (V2-05 deep links).
 *
 * The route guards in `components/layout/Router.tsx` remember it; the login page reads it. It lives
 * in sessionStorage rather than only in router history state because a deep link can arrive as a
 * full document load, go through more than one redirect while the session check is in flight, or be
 * reloaded — measured on the packaged build: `#/conversation/<id>` reached the sign-in page and the
 * visitor was then dropped on the default page, because the history entry that carried `from` was
 * replaced before sign-in finished. sessionStorage survives all three cases and is per-tab, so one
 * tab's pending destination never leaks into another.
 */
const KEY = 'kel:login-return-to';

/** Remember where the visitor was heading. The sign-in route itself is never a destination. */
export function rememberLoginReturnTo(path?: string | null): void {
  try {
    if (!path || path.startsWith('/login') || path === '/') return;
    window.sessionStorage.setItem(KEY, path);
  } catch {
    // Storage blocked (private mode): the visitor simply lands on the default page, as before.
  }
}

/** The destination a signed-out visitor is still waiting for, if any. */
export function pendingLoginReturnTo(): string | undefined {
  try {
    return window.sessionStorage.getItem(KEY) || undefined;
  } catch {
    return undefined;
  }
}

/** Forget it — called once the visitor is actually inside a protected route. */
export function clearLoginReturnTo(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
