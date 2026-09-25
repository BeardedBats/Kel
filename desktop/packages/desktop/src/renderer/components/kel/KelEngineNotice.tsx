/**
 * Batch 6 (visual findings 16/17): the shell-level engine-link strip.
 *
 * In-flow (never a floating island), hidden while connected; shows the honest supervision state —
 * reconnecting / restarted-and-work-preserved / could-not-recover — with the one action that
 * really works in that state. Durable truth stays in the engine's records; this owns no workflow.
 */
import React, { useEffect, useState } from 'react';
import { engineStateCopy, type EngineStateFrame } from './engineFailure';
import { engineRetry, engineState, onEngineState } from './kelApi';
import { KelButton } from './KelPrimitives';

export const useKelEngineFrame = (): EngineStateFrame | null => {
  const [frame, setFrame] = useState<EngineStateFrame | null>(null);
  useEffect(() => {
    let alive = true;
    void engineState().then((next) => {
      if (alive) setFrame(next);
    });
    const off = onEngineState((next) => setFrame(next));
    return () => {
      alive = false;
      off();
    };
  }, []);
  return frame;
};

export const KelEngineNotice: React.FC = () => {
  const frame = useKelEngineFrame();
  const [recoveredHidden, setRecoveredHidden] = useState(false);
  const [retrying, setRetrying] = useState(false);

  // A recovery notice retires itself; the incident is over and the strip must not become furniture.
  useEffect(() => {
    setRecoveredHidden(false);
    if (frame?.state !== 'recovered') return;
    const timer = setTimeout(() => setRecoveredHidden(true), 8000);
    return () => clearTimeout(timer);
  }, [frame?.state, frame?.at]);

  const copy = engineStateCopy(frame);
  if (!copy) return null;
  if (frame?.state === 'recovered' && recoveredHidden) return null;

  return (
    <div className={`kel-engine-notice kel-engine-notice--${copy.tone}`} role='status' aria-live='polite'>
      <div className='kel-engine-notice__text'>
        <strong>{copy.title}</strong>
        <span>{copy.detail}</span>
      </div>
      {frame?.state === 'unrecoverable' && (
        <KelButton
          variant='secondary'
          disabled={retrying}
          onClick={() => {
            setRetrying(true);
            void engineRetry().finally(() => setRetrying(false));
          }}
        >
          {retrying ? 'Trying…' : "Try to restart Kel's engine"}
        </KelButton>
      )}
    </div>
  );
};

export const KelChatReconnectingNotice: React.FC<{ mobile: boolean }> = ({ mobile }) => {
  const [retrying, setRetrying] = useState(false);
  return (
    <div className='kel-chat-reconnecting chat-surface-fluid' role='status' aria-live='polite' data-testid='kel-chat-reconnecting'>
      <span className='kel-chat-reconnecting__spinner' aria-hidden='true' />
      <span className='kel-chat-reconnecting__text'>
        <strong>Kel is reconnecting</strong>
        <small>{mobile ? 'Messages send when Kel is back.' : 'Your chat is safe. Messages send when Kel is back.'}</small>
      </span>
      <button type='button' disabled={retrying} onClick={() => {
        setRetrying(true);
        void engineRetry().finally(() => setRetrying(false));
      }}>{retrying ? 'Restarting…' : mobile ? 'Restart' : 'Restart engine'}</button>
    </div>
  );
};
