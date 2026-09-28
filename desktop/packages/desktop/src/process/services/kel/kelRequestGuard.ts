/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * What the renderer may ask the engine for through `kel:request`.
 *
 * Credential custody belongs to the main process (D-33/D-34): the renderer never receives a
 * credential value and never supplies one. The route allowlist alone is not enough because one
 * route (`/api/connections`) carries both metadata actions and credential-bearing actions, so the
 * body is checked too. The main process calls the engine directly for the credential actions.
 */

const ROUTE =
  /^\/api\/(state(?:\?conversation=(?:[a-zA-Z0-9-]+|\*)(?:&project=(?:[a-zA-Z0-9_-]+|\*))?)?|work\?(?:conversation=[a-zA-Z0-9-]+|project=(?:[a-zA-Z0-9_-]+|\*))|handoff\?conversation=[a-zA-Z0-9-]+&submission=[a-zA-Z0-9-]+|office(?:\?(?:project=(?:[a-zA-Z0-9_-]+|\*)|conversation=[a-zA-Z0-9-]+))?|office\/item\?job=[a-zA-Z0-9-]+|usage\?(?:conversation=[a-zA-Z0-9-]+|job=[a-zA-Z0-9-]+)|scoping(?:\?id=[a-zA-Z0-9-]+(?:&conversation=[a-zA-Z0-9-]+)?)?|project|conversation|conversation-title|send|rewind|memory|map|recipes|schedules|brief|team|vetting|transcription|dogfood(?:\?action=get&id=FIX-[0-9]{4}|\?status=(?:OPEN|BATCHED|FIXED|DISMISSED))?|model|capabilities|connections|data-path|backup|search|providers|autonomy|diagnostics|control|approval|approvals(?:\?conversation=[a-zA-Z0-9-]+)?|retry|apply|lineage\?job=[a-zA-Z0-9-]+(?:&milestone=[a-zA-Z0-9_-]+)?|artifact\?job=[a-zA-Z0-9-]+&milestone=[a-zA-Z0-9_-]+|artifact\?lineage=[a-zA-Z0-9-]+)$/;

/**
 * D-57: `import` brings the old scheduler's tasks into the engine once, from the main process only —
 * a page must not be able to plant schedules with a made-up origin.
 */
const SHELL_ONLY_SCHEDULE_ACTIONS = new Set(['import']);

/**
 * D-75.3: the Muse (Ramble) key is managed in Settings → Providers through the main process's custody;
 * no page saves, clears, supplies or reads it through the engine directly.
 */
const SHELL_ONLY_TRANSCRIPTION_ACTIONS = new Set(['set_key', 'clear_key', 'supply', 'legacy_key']);

/** Connection actions that move, supply or claim credential values — main process only. */
const SHELL_ONLY_CONNECTION_ACTIONS = new Set(['supply', 'oauth-initiate', 'oauth-claim', 'oauth-revoke', 'test', 'run', 'call']);

const carriesCredentials = (value: unknown, depth = 0): boolean => {
  if (!value || typeof value !== 'object' || depth > 4) return false;
  for (const [key, inner] of Object.entries(value as Record<string, unknown>)) {
    if (key === 'credentials' || key === 'secret' || key === 'api_key' || key === 'token') return true;
    if (carriesCredentials(inner, depth + 1)) return true;
  }
  return false;
};

/** Null when the renderer may send this request; otherwise the reason it is refused. */
export const rendererKelRequestRefusal = (route: unknown, body?: unknown): string | null => {
  if (typeof route !== 'string' || !ROUTE.test(route)) return 'Unknown Kel action';
  if (carriesCredentials(body)) return 'Credentials are handled by Kel, not by this page';
  if (route === '/api/connections') {
    const action = body && typeof body === 'object' ? (body as { action?: unknown }).action : undefined;
    if (typeof action === 'string' && SHELL_ONLY_CONNECTION_ACTIONS.has(action)) {
      return 'Credentials are handled by Kel, not by this page';
    }
  }
  if (route === '/api/transcription') {
    const action = body && typeof body === 'object' ? (body as { action?: unknown }).action : undefined;
    if (typeof action === 'string' && SHELL_ONLY_TRANSCRIPTION_ACTIONS.has(action)) {
      return 'The Muse key is managed in Settings → Providers';
    }
  }
  if (route === '/api/office' && body !== undefined) {
    // D-66/D-68: the live work view is read-only apart from removing a finished card (a bodyless
    // call is the read itself) and, Routing 2 §5.4, raising a budget-stopped job's budget.
    const action = body && typeof body === 'object' ? (body as { action?: unknown }).action : undefined;
    if (action !== 'dismiss' && action !== 'raise_budget') return 'The work view can only remove a finished card or raise a budget';
  }
  if (route === '/api/schedules') {
    const action = body && typeof body === 'object' ? (body as { action?: unknown }).action : undefined;
    if (typeof action === 'string' && SHELL_ONLY_SCHEDULE_ACTIONS.has(action)) {
      return 'Kel moves old scheduled tasks over by itself; this page cannot import them';
    }
  }
  return null;
};
