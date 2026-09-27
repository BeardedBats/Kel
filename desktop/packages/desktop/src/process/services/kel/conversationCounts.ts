/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * ST-23: start-up asks the engine once (`GET /api/conversations`) how many messages and jobs each
 * conversation has, so empty chats are skipped without reading each one's full state.
 */

export type ConversationCount = { id: string; message_count: number; job_count: number };

/** The counts by conversation id, or null when the engine did not answer with them. */
export const conversationCounts = (listed: unknown): Map<string, ConversationCount> | null => {
  const rows = (listed as { conversations?: unknown } | null | undefined)?.conversations;
  if (!Array.isArray(rows)) return null;
  const counts = new Map<string, ConversationCount>();
  for (const row of rows) {
    const item = row as Partial<ConversationCount> | null;
    if (item && typeof item.id === 'string' && typeof item.message_count === 'number' && typeof item.job_count === 'number')
      counts.set(item.id, { id: item.id, message_count: item.message_count, job_count: item.job_count });
  }
  return counts;
};

/** True only when the engine said this conversation has no messages and no jobs. */
export const knownEmpty = (counts: Map<string, ConversationCount> | null, id: string): boolean => {
  const count = counts?.get(id);
  return Boolean(count) && count!.message_count === 0 && count!.job_count === 0;
};
