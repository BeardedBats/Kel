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
import { describeElement, savedGeometry } from './captureTarget';
import {
  fixCaptureReducer,
  initialFixCaptureState,
  type FixCaptureScreenshot,
  type FixCaptureState,
  type FixCaptureVoice,
} from './fixCaptureMachine';

declare const __APP_VERSION__: string;

const LIVE_POLL_MS = 900;
/** Below this the engine is not asked to transcribe at all — a stray click is not feedback. */
const MIN_AUDIO_MS = 400;
/** The one sentence a person reads when Muse could not transcribe their recording. */
const TRANSCRIBE_FAILED = "Couldn't transcribe this recording.";

/** Said with every voice failure: the finding itself is never lost (FIX-0019). */
const STILL_SAVED = 'Save still keeps the screenshot and the spot you clicked.';
const PARTIAL_NOTE = 'Only part of what you said came through. Add the rest, or retry the transcription.';

const failureNote = (error: unknown): string => {
  const detail = (failureSentence(error, '') || '').trim();
  const head = detail && detail !== TRANSCRIBE_FAILED ? `${TRANSCRIBE_FAILED} ${detail}` : TRANSCRIBE_FAILED;
  return `${head} ${STILL_SAVED}`;
};

/**
 * The unsaved fix, kept on this computer until the engine confirms the save. If Kel closes, reloads or
 * the capture layer is remounted mid-capture, the next start saves what was there instead of losing it.
 */
export const FIX_DRAFT_KEY = 'kel.fixCapture.draft.v1';

type FixSaveBody = Parameters<typeof kelDogfood.save>[0];

const draftStore = {
  read(): FixSaveBody | null {
    try {
      const raw = window.localStorage?.getItem(FIX_DRAFT_KEY);
      const parsed = raw ? (JSON.parse(raw) as FixSaveBody) : null;
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch {
      return null;
    }
  },
  write(body: FixSaveBody): void {
    try {
      window.localStorage?.setItem(FIX_DRAFT_KEY, JSON.stringify(body));
    } catch {
      /* storage unavailable: the in-memory capture is still there */
    }
  },
  clear(): void {
    try {
      window.localStorage?.removeItem(FIX_DRAFT_KEY);
    } catch {
      /* nothing to clear */
    }
  },
};

/** One fix as the engine stores it, from the capture state (the same body for save and recovery). */
const saveBody = (state: FixCaptureState, transcript: string, voice: FixCaptureVoice): FixSaveBody => {
  const shot = state.screenshot;
  // FIX-0018's box was off by the 115% zoom: the rect is saved in the screenshot's own pixels.
  const geometry = shot
    ? savedGeometry(state.target, shot.image, { width: window.innerWidth, height: window.innerHeight })
    : { element: state.target, window: null };
  return {
    transcript: transcript.trim(),
    screenshot: shot?.screenshot ?? null,
    route: state.route,
    page_title: state.pageTitle,
    element: geometry.element,
    window: geometry.window,
    version: typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : null,
    conversation: state.conversation,
    diagnostics: voice ? { voice } : null,
  };
};

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
  /** Transcribe the recording that is already captured — never asks for a new one. */
  retry: () => Promise<void>;
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
  /** The temp screenshot of a capture that has not been saved yet (or null). */
  const pendingRef = useRef<string | null>(null);
  /** The completed recording, held so a failed transcription can be retried without re-recording. */
  const audioRef = useRef<{ base64: string; durationMs: number } | null>(null);
  /** The newest live words, so a failed finish still keeps whatever was heard. */
  const liveRef = useRef('');

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

  /**
   * A cancelled capture leaves nothing behind: the temp screenshot goes back to the engine, which
   * deletes it. After a save the engine has already moved that file under the fix id, so this is a
   * no-op — which is the point: cancelling can never delete a saved fix's screenshot.
   */
  const discardCapture = useCallback((relpath: string | null | undefined) => {
    if (!relpath) return;
    void kelRequest('/api/dogfood', { action: 'discard', screenshot: relpath }).catch(() => {});
  }, []);

  /**
   * Cancel audio + live session. An explicit cancel (Esc, Cancel) also throws the capture away; an
   * unmount keeps the screenshot and the stored draft so the next start can still save the fix.
   */
  const teardown = useCallback(
    (keepCapture = false) => {
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
      if (pendingRef.current && !keepCapture) {
        discardCapture(pendingRef.current);
      }
      pendingRef.current = null;
      if (!keepCapture) draftStore.clear();
      // Cancel/Esc throws the recording away too: nothing is left to retry or save.
      audioRef.current = null;
    },
    [discardCapture, endSession, stopTimers]
  );

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
      liveRef.current = '';
      dispatch({ type: 'started' });
      tickRef.current = window.setInterval(() => dispatch({ type: 'tick' }), 1000);
      if (started.live && started.session_id) {
        pollRef.current = window.setInterval(() => {
          const session = sessionRef.current;
          if (!session) return;
          void kelRequest<{ text?: string }>('/api/transcription', { action: 'stream_status', session })
            .then((live) => {
              if (live.text) liveRef.current = live.text;
              dispatch({ type: 'live', text: live.text || '' });
            })
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
    teardown(false);
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
      // Held until the fix is saved: a cancelled capture hands this path back to the engine.
      pendingRef.current = screenshot?.screenshot ?? null;
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
        // Kept for the whole review: a failed transcription can be retried on this exact recording.
        audioRef.current = { base64: recording.base64, durationMs: recording.durationMs };
        await chainRef.current.catch(() => {});
        let text = '';
        // The engine says whether the live stream heard the whole recording; when it did not and it
        // could not recover the rest, the words are marked partial instead of passed off as all of it.
        let complete = true;
        if (session) {
          try {
            const finished = await kelRequest<{ text?: string; complete?: boolean }>('/api/transcription', {
              action: 'stream_finish',
              session,
            });
            text = finished.text || '';
            complete = finished.complete !== false;
          } catch (error) {
            if (!liveRef.current.trim()) throw error;
            text = liveRef.current;
            complete = false;
          }
        }
        if (!text.trim() && recording.durationMs > MIN_AUDIO_MS) {
          const quick = await kelRequest<{ text?: string }>('/api/transcription', {
            action: 'quick_transcribe',
            filename: 'fix-capture.wav',
            audio: recording.base64,
            duration_ms: recording.durationMs,
          });
          text = quick.text || '';
          complete = true;
        }
        const produced = text.trim();
        if (produced && complete) {
          dispatch({ type: 'stopped', text: produced });
        } else if (produced) {
          dispatch({ type: 'stopped', text: produced, note: PARTIAL_NOTE, retryable: true, voice: 'partial' });
        } else if (recording.durationMs > MIN_AUDIO_MS) {
          // Real audio came back with no words: a failure a person can retry, and never a lost fix.
          dispatch({
            type: 'stopped',
            text: '',
            note: `${TRANSCRIBE_FAILED} ${STILL_SAVED}`,
            retryable: true,
            voice: 'none',
          });
        } else {
          // Too short to be feedback at all (a stray click): nothing to transcribe, nothing to retry.
          dispatch({ type: 'stopped', text: '', voice: 'none' });
        }
      } catch (error) {
        const heard = liveRef.current.trim();
        dispatch({
          type: 'stopped',
          text: heard,
          note: failureNote(error),
          retryable: audioRef.current !== null,
          voice: heard ? 'partial' : 'none',
        });
      }
    })();
  }, [state.phase, stopTimers]);

  const retry = useCallback(async () => {
    if (state.phase !== 'review') return;
    const audio = audioRef.current;
    if (!audio) return;
    dispatch({ type: 'note', note: 'Transcribing the recording again…' });
    try {
      const quick = await kelRequest<{ text?: string }>('/api/transcription', {
        action: 'quick_transcribe',
        filename: 'fix-capture.wav',
        audio: audio.base64,
        duration_ms: audio.durationMs,
      });
      const text = (quick.text || '').trim();
      if (!text) {
        dispatch({ type: 'note', note: `${TRANSCRIBE_FAILED} ${STILL_SAVED}` });
        return;
      }
      dispatch({ type: 'transcribed', text });
    } catch (error) {
      dispatch({ type: 'note', note: failureNote(error) });
    }
  }, [state.phase]);

  const again = useCallback(() => {
    if (state.phase !== 'review' && state.phase !== 'stopping') return;
    stopTimers();
    endSession();
    audioRef.current = null;
    dispatch({ type: 'again' });
    void startSession();
  }, [endSession, startSession, state.phase, stopTimers]);

  const save = useCallback(async () => {
    if (state.phase !== 'review') return;
    const body = saveBody(state, state.draft, state.draft.trim() ? state.voice : 'none');
    draftStore.write(body);
    dispatch({ type: 'save' });
    try {
      const saved = await kelDogfood.save(body);
      // Only a confirmed save lets go of the local draft.
      draftStore.clear();
      dispatch({ type: 'saved', id: saved.id });
      pendingRef.current = null;
      audioRef.current = null;
      // Keep the saved report visible so the person can send it directly to Kel.
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

  // Keep the unsaved fix on this computer while it is being captured: the words heard so far while
  // recording (marked partial), the reviewed note afterwards. Cleared only by a confirmed save or an
  // explicit cancel.
  useEffect(() => {
    if (!state.target) return;
    if (state.phase === 'recording' || state.phase === 'stopping') {
      draftStore.write(saveBody(state, state.live, state.live.trim() ? 'partial' : 'none'));
    } else if (state.phase === 'review') {
      draftStore.write(saveBody(state, state.draft, state.draft.trim() ? state.voice : 'none'));
    }
  }, [state]);

  // A fix left unsaved when Kel last closed (or this layer was remounted) is saved now, marked as
  // recovered. The draft is released first so a double mount cannot save it twice, and put back if
  // the engine does not confirm.
  useEffect(() => {
    const leftover = draftStore.read();
    if (!leftover) return;
    draftStore.clear();
    const diagnostics = { ...(leftover.diagnostics ?? {}), recovered: true };
    void kelDogfood.save({ ...leftover, diagnostics }).catch(() => draftStore.write(leftover));
  }, []);

  useEffect(
    () => () => {
      if (dismissRef.current !== null) window.clearTimeout(dismissRef.current);
      teardown(true);
    },
    [teardown]
  );

  return { state, begin, cancel, pick, stop, again, retry, save, dismiss, setDraft };
}
