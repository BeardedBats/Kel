/**
 * D-75.2: the chat rows a conversation hides because they showed messages an edit or a regenerate
 * rewound. The engine keeps the list (`/api/rewind` hidden/hide) so every window and every reload
 * hides the same rows; this module caches it per chat.
 */
import { kelRequest } from '@renderer/components/kel/kelApi';

type KelBridge = { conversation?: (id: string) => Promise<unknown> };
export const kelBridge = (): KelBridge | undefined =>
  (globalThis as unknown as { window?: { kelAPI?: KelBridge } }).window?.kelAPI;

const hiddenCache = new Map<string, Promise<Set<string>>>();

/** The chat rows this conversation hides (rows that showed rewound messages). */
export function hiddenRows(donorId: string): Promise<Set<string>> {
  const conversation = kelBridge()?.conversation;
  if (!donorId || !conversation) return Promise.resolve(new Set());
  const cached = hiddenCache.get(donorId);
  if (cached) return cached;
  const load = (async () => {
    const cid = (await conversation(donorId)) as string | null;
    if (!cid) return new Set<string>();
    const out = await kelRequest<{ rows?: string[] }>('/api/rewind', { action: 'hidden', conversation: cid });
    return new Set(out?.rows ?? []);
  })().catch(() => {
    hiddenCache.delete(donorId); // an engine without rewind (or a hiccup): try again next time
    return new Set<string>();
  });
  hiddenCache.set(donorId, load);
  return load;
}

export function forgetHiddenRows(donorId: string): void {
  hiddenCache.delete(donorId);
}

export async function withoutHiddenRows<T extends { id: string }>(donorId: string, items: T[]): Promise<T[]> {
  const hidden = await hiddenRows(donorId);
  return hidden.size ? items.filter((item) => !hidden.has(item.id)) : items;
}

