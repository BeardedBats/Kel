/** Kel adaptation: recover durable replies written while the desktop was closed. */
import { isKelNoteMeta, shownKelMeta, type KelMessageMeta } from '@/common/chat/kelMessageMeta';

export type KelMessage = { seq: number; at: number; role: string; text: string; meta?: unknown };
export type HistoryMessage = {
  id: string;
  /**
   * A copy of a streamed (native) row that only adds the engine's message details (`kel_meta`).
   * It stands in for that row when the chat reads its history and is rebuilt on every reconcile.
   */
  kel_overlay?: boolean;
  msg_id: string;
  type: string;
  position: string;
  conversation_id: string;
  created_at: number;
  /**
   * Text rows carry `content.content`; Kel approval anchors carry `{kind, ref_id}`; a hand-off work
   * card (D-53) carries an ACP tool-call `update` whose id is `kel-work:<submission id>`.
   */
  content: {
    content?: string;
    /** CH-2/CP-14: the details the engine recorded with this message (results, fallbacks, notes). */
    kel_meta?: KelMessageMeta;
    kind?: 'access' | 'action';
    ref_id?: string;
    update?: {
      sessionUpdate?: string;
      tool_call_id?: string;
      status?: string;
      title?: string;
      kind?: string;
      rawInput?: Record<string, unknown>;
    };
  };
};

/** The hand-off fields `/api/state` reports per submission (D-53). */
export type KelSubmission = { id: string; state?: string; ack_seq?: number | null; title?: string | null };

const WORK_PREFIX = 'kel-work:';
const workCardId = (row: HistoryMessage): string | undefined =>
  row.type === 'acp_tool_call' ? row.content?.update?.tool_call_id : undefined;

/** The text row for one engine message, carrying the details the chat shows (if any). */
export function historyRow(id: string, message: KelMessage): HistoryMessage {
  const key = 'kel-history-' + message.seq;
  const meta = shownKelMeta(message.meta);
  return {
    id: key,
    msg_id: key,
    type: 'text',
    position: message.role === 'user' ? 'right' : 'left',
    conversation_id: id,
    created_at: message.at * 1000,
    content: meta ? { content: message.text, kel_meta: meta } : { content: message.text },
  };
}

type MetaPart = { text: string; meta: KelMessageMeta };

/** Which of the messages one streamed row carries gives that row its details. */
function overlayMeta(rowText: string, parts: MetaPart[]): KelMessageMeta | null {
  // A quiet note restyles its whole row, so it applies only when the row is exactly that note.
  const note = parts.find((part) => isKelNoteMeta(part.meta));
  if (note) return parts.length === 1 && note.text === rowText ? note.meta : null;
  const results = parts.filter((part) => part.meta.kind === 'result');
  const pick = results.length ? results : parts;
  return pick.length ? pick[pick.length - 1].meta : null;
}

const sameMeta = (a: unknown, b: unknown): boolean => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

export function recoverHistory(
  id: string,
  prefix: HistoryMessage[],
  messages: KelMessage[],
  native: HistoryMessage[]
): HistoryMessage[] {
  // Overlays are derived from the current streamed rows: rebuild them, never carry old ones over.
  const recovered = prefix.filter((row) => !row.kel_overlay);
  const fixed = new Map(recovered.map((row, index) => [row.id, index]));
  // ACP can concatenate several Kel replies into one donor message. Consume
  // each matching segment once, in order; repeated replies are not a set.
  const available = native
    .filter((row) => row.type === 'text')
    .map((row) => {
      const text = String(row.content.content).trim();
      return { row, position: row.position, whole: text, text, parts: [] as MetaPart[] };
    });
  for (const message of messages) {
    const key = 'kel-history-' + message.seq;
    const meta = shownKelMeta(message.meta);
    const index = fixed.get(key);
    if (index !== undefined) {
      // A row recovered before the engine recorded its details picks them up.
      const row = recovered[index];
      if (meta && !sameMeta(row.content.kel_meta, meta))
        recovered[index] = { ...row, content: { ...row.content, kel_meta: meta } };
      continue;
    }
    const position = message.role === 'user' ? 'right' : 'left';
    const text = message.text.trim();
    const match = available.find(
      (row) => row.position === position && (row.text === text || row.text.startsWith(text + '\n\n'))
    );
    if (match) {
      match.text = match.text.slice(text.length).trimStart();
      if (meta) match.parts.push({ text, meta });
      continue;
    }
    recovered.push(historyRow(id, message));
  }
  // CH-2/CP-14: a streamed row keeps its text; a copy that adds the engine's details stands in for it.
  for (const entry of available) {
    const meta = overlayMeta(entry.whole, entry.parts);
    if (meta) recovered.push({ ...entry.row, kel_overlay: true, content: { ...entry.row.content, kel_meta: meta } });
  }
  return recovered;
}

/**
 * D-53: every acknowledged hand-off has exactly one live work card in the conversation. The card is
 * normally streamed by the engine's ACP turn; when that row is missing (the desktop was closed, the
 * stream dropped, or the conversation was recovered from Kel's own records) one card row is added
 * right after the acknowledgement. Existing rows — native or recovered — are never duplicated.
 */
export function ensureWorkCards(
  history: HistoryMessage[],
  submissions: KelSubmission[],
  native: HistoryMessage[],
  id: string,
  messages: KelMessage[] = []
): HistoryMessage[] {
  const present = new Set<string>();
  for (const row of [...native, ...history]) {
    const toolCall = workCardId(row);
    if (toolCall?.startsWith(WORK_PREFIX)) present.add(toolCall);
  }
  const out = [...history];
  for (const submission of submissions) {
    if (!submission?.id || !submission.ack_seq) continue;
    const toolCallId = WORK_PREFIX + submission.id;
    const rowId = 'kel-work-' + submission.id;
    if (present.has(toolCallId) || out.some((row) => row.id === rowId)) continue;
    const ack = messages.find((message) => message.seq === submission.ack_seq);
    out.push({
      id: rowId,
      msg_id: rowId,
      type: 'acp_tool_call',
      position: 'left',
      conversation_id: id,
      created_at: (ack?.at ?? 0) * 1000 + 1,
      content: {
        update: {
          sessionUpdate: 'tool_call',
          tool_call_id: toolCallId,
          status: 'pending',
          title: 'Working on it in the background',
          kind: 'execute',
          rawInput: { submission_id: submission.id },
        },
      },
    });
    present.add(toolCallId);
  }
  return out;
}

/**
 * LIVE-7: the app chats (donor ids) whose engine conversation gained a message with details
 * (`/api/messages/since` items). A conversation open in two app chats names both.
 */
export function donorsForMessages(
  mapping: Record<string, string>,
  items: Array<{ conversation_id?: unknown }> | undefined
): string[] {
  const wanted = new Set(
    (items || []).map((item) => item?.conversation_id).filter((cid): cid is string => typeof cid === 'string')
  );
  return Object.entries(mapping)
    .filter(([, cid]) => wanted.has(cid))
    .map(([donorId]) => donorId);
}
