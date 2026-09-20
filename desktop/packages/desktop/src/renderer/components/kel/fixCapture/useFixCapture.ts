/**
 * Fix Capture (V2.0 preflight) — the capture itself, wired to the pieces Kel already has.
 *
 * The words come from Kel's own transcription family (`/api/transcription` live session, with the
 * practice provider when no Meta key is connected, and the same one-shot fallback the Transcription
 * page uses). The screenshot comes from the main process. The durable record goes to `/api/dogfood`.
 * Nothing new is invented: no second transcription engine, no second database.
 */
import { useCallback, useEffect, useReducer, useRef } from 'react';
import { failureSentence } from '../engineFailure';
import { kelDogfood, kelRequest } from '../kelApi';
import { friendlyMicError, startMicCapture, type MicCapture } from '@renderer/utils/transcription/audio';
import { describeElement } from './captureTarget';
import {
  fixCaptureReducer,
  initialFixCaptureState,
  type FixCaptureScreenshot,
  type FixCaptureState,
} from './fixCaptureMachine';

declare const __APP_VERSION__: string;

const LIVE_POLL_MS = 900;
const SAVED_DISMISS_MS = 2400;
/** Below this the engine is not asked to transcribe at all — a stray click is not feedback. */
const MIN_AUDIO_MS = 400;

export interface FixCaptureContext {
  route: string | null;
  pageTitle: string | null;
  conversation: string | null;
}

export interface FixCaptureApi {
  state: FixCaptureState;
  begin: () => void;
  cancel: () => void;
  pick: (element: Element) => Promise<void>;
  stop: () => void;
  again: () => void;
  save: () => Promise<void>;
  dismiss: () => void;
  setDraft: (text: string) => void;
}

const nextFrames = (): Promise<void> =>
  new Promise((resolve) => {
    if (typeof requestAnimationFrame !== 'function') {
      resolve();
      return;
    }
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
  });

export function useFixCapture(context: () => FixCaptureContext): FixCaptureApi {
  const [state, dispatch] = useReducer(fixCaptureReducer, initialFixCaptureState);
  const captureRef = useRef<MicCapture | null>(null);
  const sessionRef = useRef<string | null>(null);
  const chainRef = useRef<Promise<unknown>>(Promise.resolve());
  const epochRef = useRef(0);
  const tickRef = useRef<number | null>(null);
  const pollRef = useRef<number | null>(null);
  const dismissRef = useRef<number | null>(null);

  const stopTimers = useCallback(() => {
    if (tickRef.current !== null) window.clearInterval(tickRef.current);
    if (pollRef.current !== null) window.clearInterval(pollRef.current);
    tickRef.current = null;
    pollRef.current = null;
  }, []);

  const endSession = useCallback(() => {
    const session = sessionRef.current;
    sessionRef.current = null;
    if (session) {
      void kelRequest('/api/transcription', { action: 'stream_finish', session }).catch(() => {});
    }
  }, []);

  /** Cancel audio + live session; used by Esc, click-outside, unmount. Never saves anything. */
  const teardown = useCallback(() => {
    epochRef.current += 1;
    stopTimers();
    const capture = captureRef.current;
    captureRef.current = null;
    try {
      capture?.cancel();
    } catch {
      /* already gone */
    }
    endSession();
  }, [endSession, stopTimers]);

  /** Start (or restart) one live recording: microphone first, then the engine session. */
  const startSession = useCallback(async () => {
    const epoch = (epochRef.current += 1);
    let capture: MicCapture | null = null;
    let micReady = false;
    try {
      capture = await startMicCapture((pcm) => {
        const session = sessionRef.current;
        if (!session) return;
        // Chunks stay in order through one chain, exactly like the Transcription page.
        chainRef.current = chainRef.current
          .then(() => kelRequest('/api/transcription', { action: 'stream_chunk', session, pcm }))
          .catch(() => {});
      });
      micReady = true;
      if (epoch !== epochRef.current) {
        capture.cancel();
        return;
      }
      captureRef.current = capture;
      const started = await kelRequest<{ session_id: string | null; live: boolean }>('/api/transcription', {
        action: 'stream_start',
      });
      if (epoch !== epochRef.current) {
        capture.cancel();
        captureRef.current = null;
        if (started.live && started.session_id) {
          void kelRequest('/api/transcription', { action: 'stream_finish', session: started.session_id }).catch(
            () => {}
          );
        }
        return;
      }
      sessionRef.current = started.live ? started.session_id : null;
      dispatch({ type: 'started' });
      tickRef.current = window.setInterval(() => dispatch({ type: 'tick' }), 1000);
      if (started.live && started.session_id) {
        pollRef.current = window.setInterval(() => {
          const session = sessionRef.current;
          if (!session) return;
          void kelRequest<{ text?: string }>('/api/transcription', { action: 'stream_status', session })
            .then((live) => dispatch({ type: 'live', text: live.text || '' }))
            .catch(() => {});
        }, LIVE_POLL_MS);
      }
    } catch (error) {
      epochRef.current += 1;
      captureRef.current = null;
      try {
        capture?.cancel();
      } catch {
        /* already gone */
      }
      endSession();
      dispatch({
        type: 'mic-failed',
        note: micReady
          ? failureSentence(error, 'Kel could not start the transcript — type what happened instead.')
          : `${friendlyMicError(error)} You can type what happened instead.`,
      });
    }
  }, [endSession]);

  const begin = useCallback(() => {
    if (state.phase !== 'idle') return;
    const facts = context();
    dispatch({ type: 'begin', route: facts.route, pageTitle: facts.pageTitle, conversation: facts.conversation });
  }, [context, state.phase]);

  const cancel = useCallback(() => {
    if (state.phase === 'idle' || state.phase === 'saving' || state.phase === 'saved') return;
    teardown();
    dispatch({ type: 'cancel' });
  }, [state.phase, teardown]);

  const pick = useCallback(
    async (element: Element) => {
      if (state.phase !== 'selecting') return;
      const target = describeElement(element);
      if (!target) return;
      dispatch({ type: 'pick', target });
      // Two frames: the selection overlay leaves the screen before the window is captured, so the
      // screenshot shows Kel as it was, and the highlight is never baked into the image.
      await nextFrames();
      const screenshot: FixCaptureScreenshot | null = await kelDogfood.capture();
      dispatch({
        type: 'capture',
        screenshot,
        note: screenshot
          ? undefined
          : 'A screenshot is not available on this surface — what you say and the element context are still saved.',
      });
      await startSession();
    },
    [startSession, state.phase]
  );

  const stop = useCallback(() => {
    if (state.phase !== 'recording') return;
    dispatch({ type: 'stop' });
    epochRef.current += 1;
    stopTimers();
    const capture = captureRef.current;
    captureRef.current = null;
    const session = sessionRef.current;
    sessionRef.current = null;
    void (async () => {
      try {
        if (!capture) {
          dispatch({ type: 'stopped', text: '' });
          return;
        }
        const recording = await capture.stop();
        await chainRef.current.catch(() => {});
        let text = '';
        if (session) {
          const finished = await kelRequest<{ text?: string }>('/api/transcription', {
            action: 'stream_finish',
            session,
          });
          text = finished.text || '';
        }
        if (!text.trim() && recording.durationMs > MIN_AUDIO_MS) {
          const quick = await kelRequest<{ text?: string }>('/api/transcription', {
            action: 'quick_transcribe',
            filename: 'fix-capture.wav',
            audio: recording.base64,
            duration_ms: recording.durationMs,
          });
          text = quick.text || '';
        }
        dispatch({ type: 'stopped', text });
      } catch (error) {
        dispatch({
          type: 'stopped',
          text: '',
          note: failureSentence(error, 'That recording could not be transcribed — type what happened instead.'),
        });
      }
    })();
  }, [state.phase, stopTimers]);

  const again = useCallback(() => {
    if (state.phase !== 'review' && state.phase !== 'stopping') return;
    stopTimers();
    endSession();
    dispatch({ type: 'again' });
    void startSession();
  }, [endSession, startSession, state.phase, stopTimers]);

  const save = useCallback(async () => {
    if (state.phase !== 'review') return;
    const shot = state.screenshot;
    dispatch({ type: 'save' });
    try {
      const saved = await kelDogfood.save({
        transcript: state.draft.trim(),
        screenshot: shot?.screenshot ?? null,
        route: state.route,
        page_title: state.pageTitle,
        element: state.target,
        window: shot
          ? {
              width: shot.content.width,
              height: shot.content.height,
              scale: shot.image.width / Math.max(1, shot.content.width),
            }
          : null,
        version: typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : null,
        conversation: state.conversation,
      });
      dispatch({ type: 'saved', id: saved.id });
      dismissRef.current = window.setTimeout(() => dispatch({ type: 'dismiss' }), SAVED_DISMISS_MS);
    } catch (error) {
      dispatch({
        type: 'save-failed',
        note: failureSentence(error, 'Kel could not save that fix — your words are still here, try again.'),
      });
    }
  }, [state]);

  const dismiss = useCallback(() => {
    if (dismissRef.current !== null) window.clearTimeout(dismissRef.current);
    dispatch({ type: 'dismiss' });
  }, []);

  const setDraft = useCallback((text: string) => dispatch({ type: 'edit', text }), []);

  useEffect(
    () => () => {
      if (dismissRef.current !== null) window.clearTimeout(dismissRef.current);
      epochRef.current += 1;
      stopTimers();
      try {
        captureRef.current?.cancel();
      } catch {
        /* already gone */
      }
      captureRef.current = null;
      const session = sessionRef.current;
      sessionRef.current = null;
      if (session) void kelRequest('/api/transcription', { action: 'stream_finish', session }).catch(() => {});
    },
    [stopTimers]
  );

  return { state, begin, cancel, pick, stop, again, save, dismiss, setDraft };
}
