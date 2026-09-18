/**
 * Capability recommendations — the engine's refusal payload, mapped to card actions.
 *
 * The engine only ever recommends real capabilities with real next steps (see
 * `runtime/kel/capabilities.recommendation`): a capability disabled for this conversation can be
 * allowed once, enabled for the chat, or explicitly kept off. Unknown action ids are dropped
 * (fail-closed rendering) so a stale engine cannot invent UI.
 */
export type CapabilityRecommendation = {
  capability: string;
  label: string;
  reason: string;
  actions: string[];
};

export type CapabilityCardActionId = 'allow_once' | 'enable' | 'keep_disabled';
export type CapabilityCardAction = { id: CapabilityCardActionId; label: string };

const ACTION_LABELS: Record<CapabilityCardActionId, string> = {
  allow_once: 'Allow once',
  enable: 'Enable for this chat',
  keep_disabled: 'Keep it off',
};

export function capabilityCardActions(rec: CapabilityRecommendation | null | undefined): CapabilityCardAction[] {
  if (!rec || !Array.isArray(rec.actions)) return [];
  return rec.actions
    .filter((id): id is CapabilityCardActionId => id in ACTION_LABELS)
    .map((id) => ({ id, label: ACTION_LABELS[id] }));
}

export function capabilityActionRequest(
  action: CapabilityCardActionId,
  conversation: string,
  capability: string
): { route: string; body: Record<string, unknown> } | null {
  if (action === 'allow_once') {
    return { route: '/api/capabilities', body: { action: 'allow_once', conversation, capability } };
  }
  if (action === 'enable') {
    return { route: '/api/capabilities', body: { action: 'set', conversation, capability, state: 'on' } };
  }
  return null; // Keep it off only dismisses the card — no state change.
}

export function capabilityConfirmation(action: CapabilityCardActionId, label: string): string {
  if (action === 'allow_once') return `Allowed once — Kel can use ${label} for the next request that needs it.`;
  if (action === 'enable') return `${label} is on for this conversation.`;
  return `${label} stays off for this conversation.`;
}
