/** Kel microphone button for the chat composer: record, watch it type, stop, edit, send.
 *
 * Replaces the donor SpeechInputButton (browser speech recognition that needs a network service)
 * with Kel's own transcription pipeline. The transcript lands in the composer as editable text —
 * it is never sent automatically, so the user can fix or remove it first.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Message } from '@arco-design/web-react';
import { friendlyMicError, startMicCapture, type MicCapture } from '@renderer/utils/transcription/audio';
import { kelRequest } from '@renderer/components/kel/kelApi';

type MicState = 'idle' | 'requesting' | 'recording' | 'working';

type Props = {
  onTranscript: (text: string) => void;
  onLiveTranscript?: (text: string | null) => void;
  disabled?: boolean;
};

/**
 * Transcription goes through the same Kel transport as every other call: the desktop's preload bridge,
 * or — away from the desktop, on a phone — the web-host's session-gated `/kel` gateway. This used to
 * require `window.kelAPI` directly, which a browser never has, so mobile voice failed before a single
 * request left the page and the failure was swallowed into a silent recording.
 */
const request = <T,>(route: string, body?: unknown): Promise<T> => kelRequest<T>(route, body);

/** Plain sentences for the composer, never transport jargon or internal ids. */
function transcriptionErrorSentence(error: unknown): string {
  const raw = String((error as Error)?.message ?? error ?? '');
  if (/key|credential|unauthor|forbidden|401|403/i.test(raw)) {
    return 'Voice needs the transcription key that is already set up for Kel on the desktop.';
  }
  if (/not connected|unreachable|failed to fetch|network/i.test(raw)) {
    return 'Kel is not reachable right now, so that recording could not be transcribed.';
  }
  return 'Kel could not transcribe that recording — nothing was added to the chat.';
}

const MicIcon = (
  <svg width='15' height='15' viewBox='0 0 24 24' fill='none' aria-hidden='true'>
    <path d='M12 3a3 3 0 0 1 3 3v6a3 3 0 1 1-6 0V6a3 3 0 0 1 3-3Z' fill='currentColor' />
    <path d='M6 11a6 6 0 0 0 12 0M12 17v4' stroke='currentColor' strokeWidth='1.8' strokeLinecap='round' />
  </svg>
);

const KelMicButton: React.FC<Props> = ({ onTranscript, onLiveTranscript, disabled }) => {
  const [state, setState] = useState<MicState>('idle');
  const [seconds, setSeconds] = useState(0);
  const captureRef = useRef<MicCapture | null>(null);
  const sessionRef = useRef<string | null>(null);
  const liveRef = useRef(false);
  const chainRef = useRef<Promise<unknown>>(Promise.resolve());
  const lastErrorRef = useRef<string>('');
  const timerRef = useRef<number | null>(null);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(
    () => () => {
      captureRef.current?.cancel();
      stopTimer();
    },
    [stopTimer]
  );

  const start = useCallback(async () => {
    if (state !== 'idle' || disabled) return;
    setState('requesting');
    try {
      const capture = await startMicCapture((pcm) => {
        const session = sessionRef.current;
        if (!session) return;
        chainRef.current = chainRef.current
          .then(() => request<Record<string, unknown>>('/api/transcription', { action: 'stream_chunk', session, pcm }))
          .then((result) => {
            const text = typeof result.text === 'string' ? result.text : '';
            if (text && onLiveTranscript) onLiveTranscript(text);
          })
          .catch(() => {
            /* live text is best-effort; the final transcript still lands below */
          });
      });
      captureRef.current = capture;
      try {
        const started = await request<Record<string, unknown>>('/api/transcription', { action: 'stream_start' });
        sessionRef.current = typeof started.session_id === 'string' ? started.session_id : null;
        liveRef.current = Boolean(started.live && started.session_id);
      } catch (error) {
        // Never pretend live transcription is running. The recording itself is still Kel's to
        // transcribe when it stops, so say exactly that — and remember the reason for the moment the
        // user stops, when the fallback either produces the transcript or the plain sentence below.
        liveRef.current = false;
        sessionRef.current = null;
        lastErrorRef.current = transcriptionErrorSentence(error);
        Message.info('Live typing is not available right now — Kel will transcribe the recording when you stop.');
      }
      setSeconds(0);
      setState('recording');
      timerRef.current = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch (error) {
      setState('idle');
      Message.error(friendlyMicError(error));
    }
  }, [disabled, onLiveTranscript, state]);

  const stop = useCallback(
    async (cancel: boolean) => {
      const capture = captureRef.current;
      if (!capture) {
        setState('idle');
        return;
      }
      captureRef.current = null;
      stopTimer();
      const session = sessionRef.current;
      sessionRef.current = null;
      if (cancel) {
        capture.cancel();
        onLiveTranscript?.(null);
        if (session) void request('/api/transcription', { action: 'stream_finish', session }).catch(() => {});
        liveRef.current = false;
        setSeconds(0);
        setState('idle');
        return;
      }
      setState('working');
      try {
        const recording = await capture.stop();
        await chainRef.current.catch(() => {});
        let text = '';
        if (session && liveRef.current) {
          const finished = await request<Record<string, unknown>>('/api/transcription', { action: 'stream_finish', session });
          text = typeof finished.text === 'string' ? finished.text : '';
        }
        if (!text.trim()) {
          const quick = await request<Record<string, unknown>>('/api/transcription', {
            action: 'quick_transcribe',
            filename: 'dictation.wav',
            audio: recording.base64,
            duration_ms: recording.durationMs,
          });
          text = typeof quick.text === 'string' ? quick.text : '';
        }
        onLiveTranscript?.(null);
        if (text.trim()) {
          onTranscript(text.trim());
          lastErrorRef.current = '';
        } else if (lastErrorRef.current) {
          // The live channel already learned why nothing could come through: repeat that reason instead
          // of guessing about the recording.
          Message.error(lastErrorRef.current);
          lastErrorRef.current = '';
        } else {
          Message.warning('Kel could not make out any speech in that recording.');
        }
      } catch (error) {
        onLiveTranscript?.(null);
        // Plain sentences only: never the engine's or the transport's own words.
        Message.error(transcriptionErrorSentence(error));
      } finally {
        liveRef.current = false;
        setSeconds(0);
        setState('idle');
      }
    },
    [onLiveTranscript, onTranscript, stopTimer]
  );

  useEffect(() => {
    if (state !== 'recording') return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        void stop(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [state, stop]);

  const label =
    state === 'idle'
      ? 'Record a message'
      : state === 'requesting'
        ? 'Waiting for the microphone…'
        : state === 'recording'
          ? 'Recording — click to stop'
          : 'Writing the transcript…';
  const timer = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

  return (
    <span className='inline-flex items-center gap-4px' data-testid='kel-mic' data-state={state}>
      <button
        type='button'
        className={`inline-flex h-32px items-center gap-6px rounded-999px border-none px-10px transition-colors ${
          state === 'recording'
            ? 'bg-[rgba(217,69,69,0.14)] text-[rgb(217,69,69)]'
            : 'bg-transparent text-t-secondary hover:bg-fill-2 hover:text-t-primary'
        }`}
        aria-label={label}
        title={label}
        data-testid='kel-mic-toggle'
        disabled={disabled || state === 'working'}
        onClick={() => (state === 'recording' ? void stop(false) : void start())}
      >
        {state === 'recording' ? (
          <span
            className='inline-block size-12px rounded-2px bg-[rgb(217,69,69)]'
            data-testid='kel-mic-stop'
            aria-hidden='true'
          />
        ) : (
          MicIcon
        )}
        {state === 'recording' && <span className='text-12px font-medium'>Recording {timer}</span>}
        {state === 'requesting' && <span className='text-12px'>…</span>}
        {state === 'working' && <span className='text-12px'>Working…</span>}
      </button>
      {state === 'recording' && (
        <button
          type='button'
          className='inline-flex h-24px items-center rounded-999px border-none bg-transparent px-6px text-12px text-t-secondary hover:bg-fill-2 hover:text-t-primary'
          aria-label='Cancel recording'
          data-testid='kel-mic-cancel'
          onClick={() => void stop(true)}
        >
          Cancel
        </button>
      )}
    </span>
  );
};

export default KelMicButton;
