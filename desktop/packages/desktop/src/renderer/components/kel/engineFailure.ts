/**
 * Batch 6 (visual findings 16/17): one truthful classifier + copy source for engine failures.
 *
 * Pure module — no React, no IPC, no DOM. The renderer uses it to translate whatever crossed the
 * bridge (engine sentences, transport failures, unexpected shapes) into sentences a person can
 * read, while the raw text is kept only for the "Technical details" disclosure and "Copy
 * diagnostics". Normal users must never see `TypeError: fetch failed`, module/stack traces, IPC
 * envelopes, or broker/daemon vocabulary.
 */

export type EngineFailureClass =
  | 'bridge-unavailable' // the preload bridge itself is missing
  | 'engine-unreachable' // nothing is listening (fetch failed / refused / reset)
  | 'engine-timeout' // the engine accepted the socket but did not answer in time
  | 'engine-starting' // the engine is still coming up (startup gate)
  | 'engine-sentence' // a plain-language sentence written by the engine itself
  | 'unexpected'; // anything else — honest generic copy, raw behind diagnostics only

const IPC_ENVELOPE = /^Error invoking remote method '[^']*':\s*/;
const ERROR_PREFIX = /^(?:TypeError|Error|UnhandledPromiseRejection):\s*/;
// Markers of implementation detail that must never render as user copy.
const RAW_MARKERS =
  /(error invoking remote|typeerror|traceback|\bat\s+\w+\s+\(|econnrefused|econnreset|ehostunreach|enetunreach|epipe|socket hang up|fetch failed|node_modules|[a-z]:\\|\.py[:)]|\bipc\b|\brpc\b|\bdaemon\b|\bbroker\b|\bstack\b)/i;

/** Strip Electron/IPC wrappers so classification sees the actual failure text. */
export function stripTransportEnvelope(raw: string): string {
  let text = (raw || '').trim();
  text = text.replace(IPC_ENVELOPE, '');
  for (let i = 0; i < 2; i += 1) {
    const next = text.replace(ERROR_PREFIX, '');
    if (next === text) break;
    text = next;
  }
  return text.trim();
}

export function classifyEngineFailure(error: unknown): EngineFailureClass {
  const raw = typeof error === 'string' ? error : String((error as Error)?.message ?? error ?? '');
  const lower = raw.toLowerCase();
  if (/kel bridge unavailable|window\.kelapi|kelapi is undefined/.test(lower)) return 'bridge-unavailable';
  if (/fetch failed|econnrefused|econnreset|ehostunreach|enetunreach|epipe|socket hang up|network error|err_connection/.test(lower)) return 'engine-unreachable';
  if (/etimedout|timed out|timeout|abort(error)?\b|operation was aborted/.test(lower)) return 'engine-timeout';
  if (/did not start|is starting|still starting|not ready yet|starting up/.test(lower)) return 'engine-starting';
  const text = stripTransportEnvelope(raw);
  if (text && !RAW_MARKERS.test(text)) return 'engine-sentence';
  return 'unexpected';
}

export interface EngineFailureCopy {
  title: string;
  detail: string;
}

/** Copy for a failure, from the person's point of view. `sentence` carries engine text when the
 *  engine wrote something a person can read; it is the detail only for `engine-sentence`. */
export function failureCopy(kind: EngineFailureClass, sentence = ''): EngineFailureCopy {
  switch (kind) {
    case 'bridge-unavailable':
      return {
        title: 'Kel needs a restart',
        detail: "Kel's interface can't be reached right now. Close and open Kel again — your work is safe on disk.",
      };
    case 'engine-unreachable':
      return {
        title: "Kel's engine isn't running",
        detail: "Kel couldn't reach its local engine. Your work is preserved, and Kel will try to bring the engine back.",
      };
    case 'engine-timeout':
      return {
        title: 'Kel is taking too long to answer',
        detail: 'The engine is running but did not answer in time. Nothing was lost — try again in a moment.',
      };
    case 'engine-starting':
      return {
        title: 'Kel is still starting',
        detail: 'The engine is coming up. This usually takes a few seconds.',
      };
    case 'engine-sentence':
      return {
        title: "Kel couldn't complete that",
        detail: sentence || 'The request was not completed. Try again.',
      };
    case 'unexpected':
    default:
      return {
        title: 'Something went wrong',
        detail: "Kel hit an unexpected problem and did not finish. Try again — if it keeps happening, the technical details below help Kel's team.",
      };
  }
}

/** One-line replacement for the raw `ErrorMessage` sites: never leak transport text. Plain
 *  engine sentences pass through unchanged; transport failures get the local-engine sentence. */
export function failureSentence(error: unknown, fallback: string): string {
  const kind = classifyEngineFailure(error);
  if (kind === 'engine-sentence') return failureCopy(kind, stripTransportEnvelope(String((error as Error)?.message ?? error ?? ''))).detail;
  const copy = failureCopy(kind);
  if (kind === 'unexpected') return copy.detail || fallback;
  return copy.detail;
}

export type EngineLinkState = 'starting' | 'connected' | 'reconnecting' | 'recovered' | 'unrecoverable';

export interface EngineStateFrame {
  state: EngineLinkState;
  attempts: number;
  maxAttempts: number;
  at: number;
  detail?: string;
}

export interface EngineStateCopy {
  title: string;
  detail: string;
  tone: 'info' | 'ok' | 'failed';
}

/** Shell strip copy. `null` when there is nothing to say (fully connected, no incident). */
export function engineStateCopy(frame: EngineStateFrame | undefined | null): EngineStateCopy | null {
  if (!frame) return null;
  switch (frame.state) {
    case 'starting':
      return { title: 'Kel is starting', detail: 'The engine is coming up. This usually takes a few seconds.', tone: 'info' };
    case 'reconnecting':
      return {
        title: 'Kel is reconnecting',
        detail: 'The engine stopped answering. Kel is bringing it back — your work is preserved.',
        tone: 'info',
      };
    case 'recovered':
      return {
        title: 'Kel restarted successfully',
        detail: 'The engine is back and your work is preserved. You can continue where you left off.',
        tone: 'ok',
      };
    case 'unrecoverable':
      return {
        title: "Kel couldn't recover on its own",
        detail:
          frame.attempts > 0
            ? `The engine did not come back after ${frame.attempts} attempt${frame.attempts === 1 ? '' : 's'}. Close and open Kel, or try a restart below.`
            : 'The engine did not come back. Close and open Kel, or try a restart below.',
        tone: 'failed',
      };
    case 'connected':
    default:
      return null;
  }
}

/** Text for the diagnostics disclosure / clipboard. Raw detail lives ONLY here. */
export function diagnosticsText(input: {
  title: string;
  raw?: string;
  route?: string;
  engineVersion?: string;
  address?: string;
  logTail?: string;
  at?: number;
}): string {
  const lines = [
    `Kel diagnostics — ${input.title}`,
    `time: ${new Date(input.at ?? Date.now()).toISOString()}`,
    input.engineVersion ? `engine: ${input.engineVersion}` : '',
    input.address ? `engine address: ${input.address}` : '',
    input.route ? `request: ${input.route}` : '',
    '',
    'raw detail:',
    (input.raw || '').trim() || '(none captured)',
  ].filter((line) => line !== '');
  if (input.logTail) {
    lines.push('', 'desktop.log (tail):', input.logTail.trimEnd());
  }
  return lines.join('\n');
}
