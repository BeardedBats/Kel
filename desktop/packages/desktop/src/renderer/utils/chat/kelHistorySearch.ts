/** Kel adaptation: search the immutable imported prefix through donor search rows. */
import { ipcBridge } from '@/common';
import type { PaginatedResult } from '@/common/adapter/ipcBridge';
import { isBackendHttpError } from '@/common/adapter/httpBridge';
import type { TMessage } from '@/common/chat/chatLib';
import type { IMessageSearchItem } from '@/common/types/team/database';

type SearchOptions = { keyword: string; page?: number; page_size?: number };

export async function searchKelConversationMessages(
  options: SearchOptions
): Promise<PaginatedResult<IMessageSearchItem>> {
  const host = globalThis as typeof globalThis & {
    window?: { kelAPI?: { historySearch?: (query: string) => Promise<TMessage[]> } };
  };
  const history = (await host.window?.kelAPI?.historySearch?.(options.keyword)) ?? [];
  if (!history.length) return ipcBridge.database.searchConversationMessages.invoke(options);

  const native: IMessageSearchItem[] = [];
  for (let page = 1; ; page += 1) {
    if (page > 1000) throw new Error('Migrated search exceeds the supported result window');
    const result = await ipcBridge.database.searchConversationMessages.invoke({
      keyword: options.keyword,
      page,
      page_size: 200,
    });
    native.push(...result.items);
    if (!result.has_more) break;
    if (!result.items.length) throw new Error('Native search returned an empty continuing page');
  }
  // Fetch real donor records so navigation, title, project and assistant identity remain authoritative.
  const conversationIds = [...new Set(history.map((message) => message.conversation_id))];
  const conversations = new Map(
    await Promise.all(
      conversationIds.map(async (id) => {
        try {
          return [id, await ipcBridge.conversation.get.invoke({ id })] as const;
        } catch (error) {
          if (isBackendHttpError(error) && error.status === 404) return [id, null] as const;
          throw error;
        }
      })
    )
  );
  const legacy: IMessageSearchItem[] = history
    .filter((message) => message.type === 'text' && conversations.get(message.conversation_id))
    .map((message) => ({
      conversation: conversations.get(message.conversation_id)!,
      message_id: message.id,
      message_type: message.type,
      message_created_at: message.created_at ?? 0,
      preview_text: message.type === 'text' ? message.content.content : '',
    }));
  const rows = [
    ...new Map([...legacy, ...native].map((item) => [item.conversation.id + ':' + item.message_id, item])).values(),
  ].sort((a, b) => b.message_created_at - a.message_created_at || a.message_id.localeCompare(b.message_id));
  const size = Math.max(1, Math.min(200, options.page_size ?? 50));
  const page = Math.max(1, options.page ?? 1);
  const start = (page - 1) * size;
  return { items: rows.slice(start, start + size), total: rows.length, has_more: start + size < rows.length };
}
