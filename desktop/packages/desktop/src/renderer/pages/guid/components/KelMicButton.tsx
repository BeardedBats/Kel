/** Kel microphone button for the chat composer: record, watch it type, stop, edit, send.
 *
 * Replaces the donor SpeechInputButton (browser speech recognition that needs a network service)
 * with Kel's own transcription pipeline. The transcript lands in the composer as editable text —
 * it is never sent automatically, so the user can fix or remove it first.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Message } from '@arco-design/web-react';
import { friendlyMicError, startMicCapture, type MicCapture } from '@renderer/utils/transcription/audio';

type MicState = 'idle' | 'requesting' | 'recording' | 'working';

type Props = {
  onTranscript: (text: string) => void;
  onLiveTranscript?: (text: string) => void;
  disabled?: boolean;
};

async function request(route: string, body?: unknown): Promise<Record<string, unknown>> {
  const api = window.kelAPI;
  if (!api) throw new Error('Kel is not connected');
  return (await api.request(route, body)) as Record<string, unknown>;
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
          .then(() => request('/api/transcription', { action: 'stream_chunk', session, pcm }))
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
        const started = await request('/api/transcription', { action: 'stream_start' });
        sessionRef.current = typeof started.session_id === 'string' ? started.session_id : null;
        liveRef.current = Boolean(started.live && started.session_id);
      } catch {
        liveRef.current = false;
        sessionRef.current = null;
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
          const finished = await request('/api/transcription', { action: 'stream_finish', session });
          text = typeof finished.text === 'string' ? finished.text : '';
        }
        if (!text.trim()) {
          const quick = await request('/api/transcription', {
            action: 'quick_transcribe',
            filename: 'dictation.wav',
            audio: recording.base64,
            duration_ms: recording.durationMs,
          });
          text = typeof quick.text === 'string' ? quick.text : '';
        }
        if (text.trim()) onTranscript(text.trim());
        else Message.warning('Kel could not make out any speech in that recording.');
      } catch (error) {
        Message.error(String((error as Error)?.message || error));
      } finally {
        liveRef.current = false;
        setSeconds(0);
        setState('idle');
      }
    },
    [onTranscript, stopTimer]
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
