/**
 * Fix Capture (V2.0 preflight) — the capture state machine.
 *
 * Pure on purpose: every rule the feature promises (a second press stops, Esc cancels, Record Again
 * keeps the target but drops the words, a cancel never saves, saving is exactly one fix) is decided
 * here, so it can be pinned without a running app or a microphone.
 */
import type { CapturedElement } from './captureTarget';

export type FixCapturePhase =
  | 'idle'
  | 'selecting'
  /** Target chosen, window captured, capture UI deliberately not on screen yet. */
  | 'preparing'
  | 'recording'
  /** Stop asked for: audio and the live transcript are still finishing. */
  | 'stopping'
  | 'review'
  | 'saving'
  | 'saved';

export interface FixCaptureScreenshot {
  screenshot: string;
  image: { width: number; height: number };
  content: { width: number; height: number };
  display: { scale: number };
  captured_at: number;
}

export interface FixCaptureState {
  phase: FixCapturePhase;
  target: CapturedElement | null;
  screenshot: FixCaptureScreenshot | null;
  /** Live transcript while recording. */
  live: string;
  /** The words that will be saved (editable in review; Record Again replaces them). */
  draft: string;
  seconds: number;
  /** One honest sentence for the person, when there is something to say. */
  note: string | null;
  /** True while the recording is still held so transcription can be retried (never re-recorded). */
  retryable: boolean;
  savedId: string | null;
  route: string | null;
  pageTitle: string | null;
  conversation: string | null;
}

export const initialFixCaptureState: FixCaptureState = {
  phase: 'idle',
  target: null,
  screenshot: null,
  live: '',
  draft: '',
  seconds: 0,
  note: null,
  retryable: false,
  savedId: null,
  route: null,
  pageTitle: null,
  conversation: null,
};

export type FixCaptureEvent =
  | { type: 'begin'; route: string | null; pageTitle: string | null; conversation: string | null }
  | { type: 'pick'; target: CapturedElement }
  | { type: 'capture'; screenshot: FixCaptureScreenshot | null; note?: string }
  | { type: 'started' }
  | { type: 'mic-failed'; note: string }
  | { type: 'tick' }
  | { type: 'live'; text: string }
  | { type: 'stop' }
  | { type: 'stopped'; text: string; note?: string; retryable?: boolean }
  /** A retry produced real words: fill the review and drop the failure state. */
  | { type: 'transcribed'; text: string }
  | { type: 'note'; note: string | null }
  | { type: 'edit'; text: string }
  | { type: 'again' }
  | { type: 'save' }
  | { type: 'saved'; id: string }
  | { type: 'save-failed'; note: string }
  | { type: 'cancel' }
  | { type: 'dismiss' };

const ACTIVE: FixCapturePhase[] = ['selecting', 'preparing', 'recording', 'stopping', 'review'];

export const isCapturing = (phase: FixCapturePhase): boolean => ACTIVE.includes(phase);

export function fixCaptureReducer(state: FixCaptureState, event: FixCaptureEvent): FixCaptureState {
  switch (event.type) {
    case 'begin':
      if (state.phase !== 'idle') return state;
      return {
        ...initialFixCaptureState,
        phase: 'selecting',
        route: event.route,
        pageTitle: event.pageTitle,
        conversation: event.conversation,
      };
    case 'pick':
      // Choosing the target happens once; a stray second click cannot re-target a capture.
      if (state.phase !== 'selecting') return state;
      return { ...state, phase: 'preparing', target: event.target, note: null };
    case 'capture':
      if (state.phase !== 'preparing') return state;
      return { ...state, screenshot: event.screenshot, note: event.note ?? state.note };
    case 'started':
      if (state.phase !== 'preparing') return state;
      return { ...state, phase: 'recording', seconds: 0, live: '', note: null };
    case 'mic-failed':
      // No microphone: the words can still be typed, so the capture continues instead of dying.
      if (state.phase !== 'preparing' && state.phase !== 'recording') return state;
      return { ...state, phase: 'review', note: event.note, seconds: 0, live: '', retryable: false };
    case 'tick':
      if (state.phase !== 'recording') return state;
      return { ...state, seconds: state.seconds + 1 };
    case 'live':
      if (state.phase !== 'recording') return state;
      return { ...state, live: event.text };
    case 'stop':
      if (state.phase !== 'recording') return state;
      return { ...state, phase: 'stopping' };
    case 'stopped':
      if (state.phase !== 'stopping' && state.phase !== 'recording') return state;
      return {
        ...state,
        phase: 'review',
        draft: event.text,
        live: '',
        note: event.note ?? null,
        retryable: event.retryable ?? false,
      };
    case 'transcribed':
      if (state.phase !== 'review') return state;
      return { ...state, draft: event.text, note: null, retryable: false };
    case 'note':
      if (state.phase !== 'review' && state.phase !== 'stopping') return state;
      return { ...state, note: event.note };
    case 'edit':
      if (state.phase !== 'review') return state;
      return { ...state, draft: event.text };
    case 'again':
      // Record Again keeps who/what/where, drops the words AND the failed recording: the previous
      // attempt is neither saved nor kept around.
      if (state.phase !== 'review' && state.phase !== 'stopping') return state;
      return { ...state, phase: 'recording', draft: '', live: '', seconds: 0, note: null, retryable: false };
    case 'save':
      if (state.phase !== 'review') return state;
      return { ...state, phase: 'saving', note: null };
    case 'saved':
      if (state.phase !== 'saving') return state;
      return { ...state, phase: 'saved', savedId: event.id, note: null };
    case 'save-failed':
      if (state.phase !== 'saving') return state;
      return { ...state, phase: 'review', note: event.note };
    case 'cancel':
      // Cancelling never saves and never leaves a partial record; a save already in flight is
      // allowed to finish (it either saved or it reported why it could not).
      if (state.phase === 'saving' || state.phase === 'saved' || state.phase === 'idle') return state;
      return { ...initialFixCaptureState };
    case 'dismiss':
      if (state.phase !== 'saved') return state;
      return { ...initialFixCaptureState };
    default:
      return state;
  }
}
