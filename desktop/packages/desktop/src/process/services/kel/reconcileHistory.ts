/** Kel adaptation: recover durable replies written while the desktop was closed. */
export type KelMessage = { seq: number; at: number; role: string; text: string };
export type HistoryMessage = {
  id: string;
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

export function recoverHistory(
  id: string,
  prefix: HistoryMessage[],
  messages: KelMessage[],
  native: HistoryMessage[]
): HistoryMessage[] {
  const fixed = new Set(prefix.map((row) => row.id));
  // ACP can concatenate several Kel replies into one donor message. Consume
  // each matching segment once, in order; repeated replies are not a set.
  const available = native
    .filter((row) => row.type === 'text')
    .map((row) => ({ position: row.position, text: String(row.content.content).trim() }));
  const recovered = [...prefix];
  for (const message of messages) {
    const key = 'kel-history-' + message.seq;
    if (fixed.has(key)) continue;
    const position = message.role === 'user' ? 'right' : 'left';
    const text = message.text.trim();
    const match = available.find(
      (row) => row.position === position && (row.text === text || row.text.startsWith(text + '\n\n'))
    );
    if (match) {
      match.text = match.text.slice(text.length).trimStart();
      continue;
    }
    recovered.push({
      id: key,
      msg_id: key,
      type: 'text',
      position,
      conversation_id: id,
      created_at: message.at * 1000,
      content: { content: message.text },
    });
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
