/**
 * Kel system card — keep this computer awake for long work.
 *
 * The switch drives a real power-save inhibition in the main process (sleep only, so the screen may
 * still dim); the card reports the live state instead of assuming the switch took effect, and the
 * inhibition is released when Kel closes.
 */
import { Switch, Message } from '@arco-design/web-react';
import React, { useCallback, useEffect, useState } from 'react';
import { ipcBridge } from '@/common';
import { KelCard } from './KelPrimitives';

export const KelKeepAwakeCard: React.FC = () => {
  const [enabled, setEnabled] = useState(false);
  const [active, setActive] = useState(false);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const state = await ipcBridge.systemSettings.getKeepAwake.invoke();
      setEnabled(state.enabled);
      setActive(state.active);
    } catch {
      setEnabled(false);
      setActive(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const change = useCallback(
    async (next: boolean) => {
      setBusy(true);
      try {
        const state = await ipcBridge.systemSettings.setKeepAwake.invoke({ enabled: next });
        setEnabled(state.enabled);
        setActive(state.active);
        Message.success(
          next ? 'Kel will keep this computer awake while it works.' : 'Kel will let this computer sleep again.'
        );
      } catch {
        Message.error('Kel could not change that setting. Try again.');
        void refresh();
      } finally {
        setBusy(false);
      }
    },
    [refresh]
  );

  return (
    <KelCard
      title='Keep this computer awake'
      data-testid='kel-keep-awake-card'
      actions={
        <span data-testid='kel-keep-awake-switch'>
          <Switch size='small' checked={enabled} disabled={busy} onChange={(value) => void change(value)} />
        </span>
      }
    >
      <p className='text-14px text-t-secondary m-0'>
        Long jobs and scheduled work keep running instead of waiting for the computer to wake up. Kel prevents sleep
        only — your screen can still dim. This applies to this computer, and it stops when Kel closes.
      </p>
      <p
        className='text-14px text-t-secondary m-0 mt-8px'
        data-testid='kel-keep-awake-state'
        data-active={active ? 'true' : 'false'}
      >
        {active ? 'Active — this computer will not sleep while Kel is open.' : 'Off — the computer sleeps normally.'}
      </p>
    </KelCard>
  );
};

export default KelKeepAwakeCard;
