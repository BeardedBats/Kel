/**
 * CH-9: a chat's name belongs to Kel as well as to the chat list.
 *
 * The rename paths (the sidebar's Rename dialog and the chat header) first rename the donor
 * conversation; this then passes the same name to the engine (`/api/conversation-title`), so it
 * survives the first-message auto-title and every surface that reads Kel's conversation list.
 * The engine's name is secondary: a failure here never undoes or fails the rename itself.
 */
import { kelRequest } from '@/renderer/components/kel/kelApi';

/** True when the engine stored the name; false (and logged) when it could not be passed on. */
export async function syncEngineConversationTitle(donorId: string, title: string): Promise<boolean> {
  const name = title.trim();
  const api = typeof window === 'undefined' ? undefined : window.kelAPI;
  // Away from the desktop there is no donor → engine resolver; the desktop keeps the two in step.
  if (!donorId || !name || !api?.conversation) return false;
  try {
    const engineId = await api.conversation(donorId);
    if (typeof engineId !== 'string' || !engineId) return false;
    await kelRequest('/api/conversation-title', { conversation: engineId, title: name });
    return true;
  } catch (error) {
    console.warn('[Kel] The chat was renamed, but Kel could not store the new name yet', error);
    return false;
  }
}
