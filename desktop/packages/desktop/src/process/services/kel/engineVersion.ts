/**
 * Which live Kel engine this desktop build may reuse (audit A1 / ENG-01).
 *
 * The desktop talks to a detached engine over HTTP: answering `/api/state` proves something is
 * listening, not that it is the engine this build shipped with. An upgrade replaces
 * `resources/kel-engine`, so a leftover engine from the previous version must not be reused.
 *
 * `expected` is the engine version this build expects. An empty value means the caller cannot know
 * it (an unpackaged dev run, where `app.getVersion()` reports Electron's own version); that case is
 * deliberately *not* enforced rather than failing every dev start closed.
 */
export function engineVersionAccepted(live: unknown, expected: unknown): boolean {
  const wanted = typeof expected === 'string' ? expected.trim() : '';
  if (!wanted) return true;
  return typeof live === 'string' && live.trim() === wanted;
}
