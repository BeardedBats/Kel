/**
 * D-64 — how much Kel does on its own, said plainly, with one switch back to "Ask first".
 *
 * Shown on Permissions, in Settings → System and in Set up Kel (which settles the old Autonomy
 * choice). The mode is read from the engine every time; when the engine cannot say (an engine
 * without this setting, or no answer), nothing is shown rather than a guess (JR-16/JR-18/JR-19).
 */
import { Message, Switch } from '@arco-design/web-react';
import React, { useCallback, useEffect, useState } from 'react';
import { KelCard } from './KelPrimitives';
import { authorityModeOf, kelAuthority, type KelAuthorityMode } from './kelApi';

export const AUTHORITY_TEXT: Record<KelAuthorityMode, { label: string; body: string }> = {
  full: {
    label: 'Full access',
    body: 'Kel acts without asking. It never changes its own app or data, and everything it does shows in Activity.',
  },
  ask: {
    label: 'Ask first',
    body: 'Kel asks before it changes files, runs commands, uses a new website or changes something in a connected service. Everything it does shows in Activity.',
  },
};

export const KelAuthorityCard: React.FC<{ title?: string }> = ({ title = 'How much Kel does on its own' }) => {
  const [mode, setMode] = useState<KelAuthorityMode | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    kelAuthority
      .get()
      .then((state) => {
        if (!cancelled) setMode(authorityModeOf(state));
      })
      .catch(() => {
        if (!cancelled) setMode(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const change = useCallback(async (askFirst: boolean) => {
    const next: KelAuthorityMode = askFirst ? 'ask' : 'full';
    setBusy(true);
    try {
      const state = await kelAuthority.set(next);
      const confirmed = authorityModeOf(state) ?? next;
      setMode(confirmed);
      Message.success(confirmed === 'ask' ? 'Kel will ask before it acts.' : 'Kel will act without asking.');
    } catch {
      Message.error('Kel could not change that setting. Try again.');
    } finally {
      setBusy(false);
    }
  }, []);

  if (!mode) return null;
  const text = AUTHORITY_TEXT[mode];
  return (
    <KelCard title={title} data-testid='kel-authority-card'>
      <div className='kel-shell-preference-row'>
        <div>
          <div className='kel-strong' data-testid='kel-authority-mode' data-mode={mode}>
            {text.label}
          </div>
          <p className='kel-meta m-0'>{text.body}</p>
        </div>
        <label className='kel-row' style={{ gap: 8, flexShrink: 0 }}>
          <span>Ask first</span>
          <Switch
            aria-label='Ask first'
            size='small'
            checked={mode === 'ask'}
            disabled={busy}
            onChange={(value) => void change(value)}
          />
        </label>
      </div>
    </KelCard>
  );
};

export default KelAuthorityCard;
