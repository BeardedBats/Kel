/**
 * Batch 6 (visual findings 16/17): one shared failure card for every Kel surface.
 *
 * Design: one state, one primary action, one quiet action; the raw detail exists only behind the
 * "Technical details" disclosure and the diagnostics copy. No infrastructure vocabulary ever
 * renders as visible copy.
 */
import React, { useCallback, useMemo, useState } from 'react';
import { KelButton } from './KelPrimitives';
import { classifyEngineFailure, diagnosticsText, failureCopy, stripTransportEnvelope } from './engineFailure';
import { engineDiagnostics } from './kelApi';

export interface KelFailureCardProps {
  /** The raw failure exactly as caught. Classification and copy happen here. */
  error: unknown;
  /** The safe retry for this surface (reloads from authoritative state — never a replay). */
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
  heading?: string;
  context?: string;
  retryDisabled?: boolean;
}

export const KelFailureCard: React.FC<KelFailureCardProps> = ({ error, onRetry, retryLabel = 'Try again', className, heading, context, retryDisabled }) => {
  const raw = useMemo(
    () => (error instanceof Error ? `${error.name}: ${error.message}` : String(error ?? '')),
    [error]
  );
  const kind = useMemo(() => classifyEngineFailure(error), [error]);
  const copy = useMemo(() => failureCopy(kind, stripTransportEnvelope(raw)), [kind, raw]);
  const [details, setDetails] = useState('');
  const [copied, setCopied] = useState(false);

  const buildDetails = useCallback(async () => {
    const bundle = await engineDiagnostics();
    return diagnosticsText({
      title: copy.title,
      raw,
      engineVersion: bundle.engineVersion,
      address: bundle.address,
      logTail: bundle.logTail,
    });
  }, [copy.title, raw]);

  const copyDiagnostics = useCallback(async () => {
    const text = await buildDetails();
    setDetails(text);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard refused: the disclosure below still carries the same text.
      setCopied(false);
    }
  }, [buildDetails]);

  return (
    <section className={`kel-failure${className ? ` ${className}` : ''}`} role='alert'>
      <h2 className='kel-failure__title'>{heading || copy.title}</h2>
      <p className='kel-failure__detail'>{context ? `${context} ${copy.detail}` : copy.detail}</p>
      <div className='kel-failure__actions'>
        {onRetry && (
          <KelButton variant='primary' onClick={onRetry} disabled={retryDisabled}>
            {retryLabel}
          </KelButton>
        )}
        <KelButton variant='quiet' onClick={() => void copyDiagnostics()}>
          {copied ? 'Diagnostics copied' : 'Copy diagnostics'}
        </KelButton>
      </div>
      <details
        className='kel-failure__details'
        onToggle={(event) => {
          if ((event.target as HTMLDetailsElement).open && !details) void buildDetails().then(setDetails);
        }}
      >
        <summary>Technical details</summary>
        <pre className='kel-failure__raw'>{details || 'Loading details…'}</pre>
      </details>
    </section>
  );
};
