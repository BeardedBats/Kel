/** Kel adaptation: merge an immutable migration prefix with donor-owned history. */
import type { MessageCursorPage } from '@/common/adapter/ipcBridge';
import type { TMessage } from '@/common/chat/chatLib';

type PageOptions = {
  limit?: number;
  before?: string;
  after?: string;
  anchorMessageId?: string;
  contentMode?: 'compact' | 'full';
};
type PageLoader = (options: PageOptions) => Promise<MessageCursorPage<TMessage>>;
const PREFIX = 'kel-merged:';

export async function readKelHistory(conversationId: string): Promise<TMessage[]> {
  const host = globalThis as typeof globalThis & {
    window?: { kelAPI?: { history?: (id: string) => Promise<TMessage[]> } };
  };
  return (await host.window?.kelAPI?.history?.(conversationId)) ?? [];
}

const cursor = (message: TMessage): string => PREFIX + encodeURIComponent(message.id);
const cursorIndex = (rows: TMessage[], value: string): number => {
  if (!value.startsWith(PREFIX)) throw new Error('Invalid migrated-history cursor');
  const id = decodeURIComponent(value.slice(PREFIX.length));
  const index = rows.findIndex((row) => row.id === id);
  if (index < 0) throw new Error('History cursor no longer exists; reload the conversation');
  return index;
};

export async function loadKelHistoryPage(
  legacy: TMessage[],
  options: PageOptions,
  loadNative: PageLoader
): Promise<MessageCursorPage<TMessage>> {
  // Native pages keep their own opaque cursors. Never pass our merged cursor upstream.
  const pages: TMessage[][] = [];
  const visited = new Set<string>();
  let before: string | undefined;
  for (let count = 0; ; count += 1) {
    if (count >= 1000) throw new Error('Migrated history exceeds the supported 200000 native message window');
    const page = await loadNative({ limit: 200, before, contentMode: options.contentMode });
    pages.unshift(page.items);
    if (!page.has_more_before) break;
    if (!page.oldest_cursor || visited.has(page.oldest_cursor)) {
      throw new Error('Native history returned a repeated or missing cursor');
    }
    before = page.oldest_cursor;
    visited.add(before);
  }
  const overrides = new Map(legacy.map((row) => [row.id, row]));
  const rows = [
    ...new Map(
      [...legacy, ...pages.flat().map((row) => overrides.get(row.id) || row)].map((row) => [row.id, row])
    ).values(),
  ].toSorted((a, b) => a.created_at - b.created_at);
  const limit = Math.max(1, Math.min(200, options.limit ?? 50));
  let start = Math.max(0, rows.length - limit);
  let end = rows.length;
  if (options.anchorMessageId) {
    const anchor = rows.findIndex(
      (row) => row.id === options.anchorMessageId || row.msg_id === options.anchorMessageId
    );
    if (anchor < 0) throw new Error('History message not found');
    start = Math.max(0, anchor - Math.floor(limit / 2));
    end = Math.min(rows.length, start + limit);
  } else if (options.before) {
    end = cursorIndex(rows, options.before);
    start = Math.max(0, end - limit);
  } else if (options.after) {
    start = cursorIndex(rows, options.after) + 1;
    end = Math.min(rows.length, start + limit);
  }
  const items = rows.slice(start, end);
  return {
    items,
    oldest_cursor: items.length ? cursor(items[0]) : null,
    newest_cursor: items.length ? cursor(items[items.length - 1]) : null,
    has_more_before: start > 0,
    has_more_after: end < rows.length,
  };
}
