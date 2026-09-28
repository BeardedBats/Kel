/**
 * D-75.2: edit a sent message and answer the last reply again.
 *
 * The engine rewinds the conversation (`/api/rewind`): the edited message and the direct replies
 * after it leave what Kel reads, while work already handed off (its acknowledgement, card and
 * result) stays and is never re-run. This module hides the chat rows that showed the rewound
 * messages — remembered in the engine, so a reload or another window hides them too — and sends
 * the (edited) request again as an ordinary message. Editing a message that started work is an
 * amendment (D-55): nothing is hidden and the edited text goes to Kel as the change.
 */
import { useCallback, useEffect, useRef } from 'react';
import { Message } from '@arco-design/web-react';
import type { TMessage } from '@/common/chat/chatLib';
import { emitter, useAddEventListener, type KelRewriteRequest } from '@/renderer/utils/emitter';
import { kelRequest } from '@renderer/components/kel/kelApi';
import { useUpdateMessageList } from '../hooks';
import { parseFileMarker } from './fileMarker';
import { forgetHiddenRows, kelBridge as bridge } from '@/renderer/utils/chat/kelHiddenRows';

export type RewoundMessage = { seq: number; role: string; text: string };
export type RewindResult = {
  mode: 'rewind' | 'amend';
  rewound: RewoundMessage[];
  kept: RewoundMessage[];
  text?: string;
  attachments?: string[];
  submission?: string;
};


/** The visible text and attached file paths of one chat row. */
export function rowText(message: TMessage): { text: string; files: string[] } {
  const content = (message as { content?: { content?: unknown } }).content?.content;
  if (typeof content !== 'string') return { text: '', files: [] };
  const parsed = parseFileMarker(content, message.position === 'right');
  return { text: parsed.text.trim(), files: parsed.files };
}

const isRewindableRow = (message: TMessage): boolean => message.type === 'text' || message.type === 'tips';

/**
 * The rows from `fromId` to the end that showed rewound messages: text rows, except those showing a
 * message the engine kept (handed-off work). Cards, tool calls and approvals always stay.
 */
export function rowsToHide(list: TMessage[], fromId: string, kept: RewoundMessage[]): string[] {
  const index = list.findIndex((message) => message.id === fromId);
  if (index < 0) return [];
  const keptSeqs = new Set(kept.map((item) => item.seq));
  const out: string[] = [];
  for (const message of list.slice(index)) {
    if (!isRewindableRow(message)) continue;
    const recovered = /^kel-history-(\d+)$/.exec(message.id);
    if (recovered && keptSeqs.has(Number(recovered[1]))) continue;
    const role = message.position === 'right' ? 'user' : 'assistant';
    const { text } = rowText(message);
    const keeps = kept.some((item) => {
      const keptText = item.text.trim();
      return item.role === role && Boolean(text) && Boolean(keptText) && (text === keptText || text.startsWith(keptText));
    });
    if (!keeps) out.push(message.id);
  }
  return out;
}

/** How many later user rows repeat this row's text (0 = it is the last one with that text). */
export function occurrenceFromEnd(list: TMessage[], messageId: string, text: string): number {
  const index = list.findIndex((message) => message.id === messageId);
  if (index < 0) return 0;
  return list
    .slice(index + 1)
    .filter((message) => message.type === 'text' && message.position === 'right' && rowText(message).text === text.trim())
    .length;
}

const failure = (error: unknown): string =>
  String((error as Error)?.message || error || '') || "Kel couldn't do that just now. Try again.";

/**
 * Run one edit or regenerate for the open chat. `list` is the chat's rows as shown; `hide` removes
 * rows from the open list. Returns what was resent (for tests), or null when nothing happened.
 */
export async function runRewrite(
  request: KelRewriteRequest,
  list: TMessage[],
  hide: (ids: string[]) => void
): Promise<{ text: string; files: string[]; hidden: string[] } | null> {
  const donorId = request.conversationId;
  const cid = (await bridge()?.conversation?.(donorId)) as string | null | undefined;
  if (!cid) throw new Error("Kel couldn't find this chat. Reload it and try again.");
  let fromId = request.messageId;
  let text: string;
  let files: string[];
  let result: RewindResult;
  if (request.kind === 'edit') {
    text = request.newText.trim();
    files = request.files;
    if (!text) return null;
    result = await kelRequest<RewindResult>('/api/rewind', {
      action: 'edit',
      conversation: cid,
      text: request.text,
      occurrence: occurrenceFromEnd(list, request.messageId, request.text),
    });
  } else {
    result = await kelRequest<RewindResult>('/api/rewind', { action: 'regenerate', conversation: cid });
    text = String(result.text ?? '').trim();
    const replyIndex = list.findIndex((message) => message.id === request.messageId);
    const before = replyIndex < 0 ? list : list.slice(0, replyIndex + 1);
    const asked = [...before]
      .reverse()
      .find((message) => message.type === 'text' && message.position === 'right' && rowText(message).text === text);
    fromId = asked?.id ?? request.messageId;
    files = asked ? rowText(asked).files : [];
  }
  let ids: string[] = [];
  if (result.mode === 'rewind') {
    ids = rowsToHide(list, fromId, result.kept ?? []);
    if (ids.length) {
      await kelRequest('/api/rewind', { action: 'hide', conversation: cid, rows: ids });
      forgetHiddenRows(donorId);
      hide(ids);
    }
  }
  emitter.emit('kel.message.resend', text, donorId, files);
  return { text, files, hidden: ids };
}

/** Mounted once by the message list: handles edit/regenerate requests for its chat. */
export function useKelRewriteHandler(conversationId: string | undefined, list: TMessage[]): void {
  const update = useUpdateMessageList();
  const listRef = useRef(list);
  useEffect(() => {
    listRef.current = list;
  }, [list]);
  const busy = useRef(false);
  const handle = useCallback(
    (request: KelRewriteRequest) => {
      if (!conversationId || request.conversationId !== conversationId || busy.current) return;
      busy.current = true;
      void runRewrite(request, listRef.current, (ids) => {
        const drop = new Set(ids);
        update((current) => current.filter((message) => !drop.has(message.id)));
      })
        .catch((error: unknown) => {
          Message.warning(failure(error));
        })
        .finally(() => {
          busy.current = false;
        });
    },
    [conversationId, update]
  );
  useAddEventListener('kel.message.rewrite', handle, [handle]);
}
