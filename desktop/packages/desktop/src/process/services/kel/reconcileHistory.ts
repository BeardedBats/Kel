/** Kel adaptation: recover durable replies written while the desktop was closed. */
export type KelMessage = { seq: number; at: number; role: string; text: string };
export type HistoryMessage = {
  id: string;
  msg_id: string;
  type: string;
  position: string;
  conversation_id: string;
  created_at: number;
  content: { content: string };
};

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
