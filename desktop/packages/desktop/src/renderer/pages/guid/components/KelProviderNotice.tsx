/**
 * Kel provider notice — when no model is usable, say so before the user types.
 *
 * Kel's worst silent failure is answering nothing when no provider can serve a reply.
 * This banner mirrors the Providers page's own "usable" rule (status healthy or quota) and
 * points at the one place that can fix it. It renders nothing when a model is available.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KelButton } from '@renderer/components/kel/KelPrimitives';
import { kelProviders } from '@renderer/components/kel/kelApi';

const USABLE = new Set(['healthy', 'quota']);

const KelProviderNotice: React.FC = () => {
  const navigate = useNavigate();
  const [state, setState] = useState<{ total: number; usable: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const payload = await kelProviders.list();
        const providers = payload.providers ?? [];
        if (!cancelled) {
          setState({
            total: providers.length,
            usable: providers.filter((provider) => USABLE.has(provider.status)).length,
          });
        }
      } catch {
        // The engine answers this on every other surface too; staying quiet here keeps
        // the composer clean when the failure is the engine itself being unreachable.
        if (!cancelled) setState(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!state || state.usable > 0) return null;

  const message =
    state.total === 0
      ? 'No model is connected yet — connect one and Kel can answer.'
      : 'None of your connected models is available right now, so Kel will wait instead of guessing.';

  return (
    <div className='kel-card' style={{ marginBottom: 12 }}>
      <div className='kel-row' style={{ alignItems: 'center', gap: 12 }}>
        <span className='kel-sub kel-grow' style={{ margin: 0 }}>
          {message}
        </span>
        <KelButton variant='primary' onClick={() => navigate('/providers')}>
          Open Providers
        </KelButton>
      </div>
    </div>
  );
};

export default KelProviderNotice;
