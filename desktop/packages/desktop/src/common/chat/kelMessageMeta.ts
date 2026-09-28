/**
 * CH-2/CP-14: the details the engine records with one of Kel's messages (`messages.meta`, parsed
 * into `/api/state`). The chat keeps them out of the message text and shows them only on request.
 *
 * - a reply: who answered it and, when the chosen model could not answer, what was chosen;
 * - a checked result (`kind: 'result'`): verdict, checks, who did and who reviewed the work, and
 *   the plain summary lines;
 * - quiet notes: `kind: 'stopped'` (a reply the person stopped) and `kind: 'amendment'` (work
 *   restarted with a change).
 */
export type KelWorkerLabel = { provider?: string | null; model?: string | null; label?: string | null };

export type KelMessageMeta = {
  kind?: 'result' | 'stopped' | 'amendment' | string;
  answered_by?: KelWorkerLabel | null;
  fallback_from?: (KelWorkerLabel & { note?: string | null }) | null;
  fallback_noted?: string | null;
  verdict?: 'VERIFIED' | 'UNCERTAIN' | 'FAILED' | string | null;
  checks?: Array<{ kind?: string | null; verdict?: string | null }>;
  executed_by?: KelWorkerLabel[];
  reviewed_by?: KelWorkerLabel[];
  summary?: string[];
  submission?: string;
  replaced_job?: string | null;
  /** D-70: the job a result belongs to (its done card reads that work's top card). */
  job?: string | null;
  /** D-70: Kel's "before I start" questions (`kind: 'scoping'`) are this scoping record. */
  scoping?: string | null;
};

/** Notes Kel posts about the conversation itself, shown as quiet system lines. */
export const isKelNoteMeta = (meta: KelMessageMeta | null | undefined): boolean =>
  meta?.kind === 'stopped' || meta?.kind === 'amendment';

/**
 * The part of a message's metadata the chat shows: results, replies that fell back from the chosen
 * model, and the quiet notes. Everything else (every reply's plain "who answered") stays in the
 * engine, so the chat's own copy of its history does not grow with it.
 */
export const shownKelMeta = (meta: unknown): KelMessageMeta | null => {
  if (!meta || typeof meta !== 'object' || Array.isArray(meta)) return null;
  const value = meta as KelMessageMeta;
  if (value.kind === 'result' || value.kind === 'scoping' || isKelNoteMeta(value) || value.fallback_from) return value;
  return null;
};
