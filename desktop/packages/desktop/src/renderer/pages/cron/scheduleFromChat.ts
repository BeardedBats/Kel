/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-57: "Create scheduled task" from a chat's menu opens the scheduled-task editor filled in from
 * that chat — a name, the chat's request as the instructions, and the chat's project. The person
 * reviews and changes anything before creating it; nothing is saved from here.
 */

import type { TMessage } from '@/common/chat/chatLib';
import { kelProjects } from '@renderer/components/kel/kelApi';
import { buildAutoTitleFromContent } from '@/renderer/utils/chat/autoTitle';
import { readMessageContent } from '@/renderer/utils/chat/conversationExport';
import { loadConversationMessagePage } from '@/renderer/utils/chat/messagePagination';

/** Where the chat menu's request comes from (router state on `/scheduled`). */
export type ScheduleFromChatRequest = { conversationId: string; name?: string };

export type ScheduleFromChatDraft = { name: string; prompt: string; projectId: string | null };

/** The engine's limits (`kel/schedules.py`): a name up to 120 characters, instructions up to 20,000. */
const NAME_LIMIT = 120;
const PROMPT_LIMIT = 20000;
/** A chat's title until Kel names it; not a useful task name. */
const UNTITLED = new Set(['', 'new chat', 'new conversation']);
const PAGE = 200;
/** Enough history for any real chat; a longer one uses the oldest request read so far. */
const MAX_PAGES = 5;

const userText = (message: TMessage): string =>
  message.type === 'text' && message.position === 'right' ? readMessageContent(message).trim() : '';

/** The chat's request: its first message from the person (oldest first across pages). */
export const firstRequestOf = async (conversationId: string): Promise<string> => {
  let page = await loadConversationMessagePage(conversationId, { limit: PAGE, contentMode: 'full' });
  let oldest = '';
  for (let read = 1; ; read += 1) {
    const found = page.items.map(userText).find(Boolean);
    if (found) oldest = found;
    const before = page.oldest_cursor ?? undefined;
    if (!page.has_more_before || !before || read >= MAX_PAGES) return oldest;
    page = await loadConversationMessagePage(conversationId, { limit: PAGE, before, contentMode: 'full' });
  }
};

const chatProjectId = async (conversationId: string): Promise<string | null> => {
  const answer = await kelProjects.of({ donor: conversationId });
  const project = answer?.project;
  if (project && typeof project === 'object') return project.id || null;
  return typeof project === 'string' && project ? project : null;
};

/** A name for the task: the chat's own title, else the start of its request. */
export const taskNameFor = (chatName: string | undefined, request: string): string => {
  const title = (chatName ?? '').replace(/\s+/g, ' ').trim();
  if (!UNTITLED.has(title.toLowerCase())) return title.slice(0, NAME_LIMIT);
  return buildAutoTitleFromContent(request) ?? 'Scheduled task';
};

/** Each part is best effort: whatever cannot be read is left for the person to fill in. */
export const scheduleDraftFromChat = async ({ conversationId, name }: ScheduleFromChatRequest): Promise<ScheduleFromChatDraft> => {
  const [request, projectId] = await Promise.all([
    firstRequestOf(conversationId).catch(() => ''),
    chatProjectId(conversationId).catch((): null => null),
  ]);
  return { name: taskNameFor(name, request), prompt: request.slice(0, PROMPT_LIMIT), projectId };
};
