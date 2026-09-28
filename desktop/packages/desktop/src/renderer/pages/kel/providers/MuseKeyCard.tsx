/**
 * D-75.3: the Muse key (Ramble's transcription) is managed here, with the other keys, through the
 * same OS-backed custody. The value goes from this box to the main process's store and never comes
 * back to the page; the engine only says whether a key is available and where it came from.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { KelButton, KelCard } from '@renderer/components/kel/KelPrimitives';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { kelRequest } from '@renderer/components/kel/kelApi';
import { toneChipClass } from '@renderer/components/kel/providerStatus';

export const MUSE_PROVIDER = 'muse';

type MuseStatus = { mode?: string; has_key?: boolean; source?: string; label?: string; detail?: string };

/** Plain words for where the working key comes from (never the key). */
export const museSourceLine = (status: MuseStatus | null, stored: boolean): string => {
  if (!status) return 'Checking…';
  if (status.mode === 'fixture') return 'Practice mode is on, so Ramble transcribes with practice text.';
  if (!status.has_key) return 'No Muse key yet. Add one so Ramble can transcribe your recordings.';
  if (status.source === 'environment') return "Kel is using a key set in this computer's environment.";
  if (status.source === 'transcriptions-app' && !stored)
    return 'Kel is using the key the Transcriptions app stored on this computer. Adding one here replaces it for Kel.';
  return 'The key is saved in the OS-backed store and Ramble transcribes with Muse.';
};

const MuseKeyCard: React.FC<{ secureAvailable: boolean; stored: boolean; onChanged: () => void }> = ({
  secureAvailable,
  stored,
  onChanged,
}) => {
  const location = useLocation();
  const focused = new URLSearchParams(location.search).get('provider') === MUSE_PROVIDER;
  const [status, setStatus] = useState<MuseStatus | null>(null);
  const [draft, setDraft] = useState<string | null>(focused ? '' : null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const ref = useRef<HTMLDetailsElement>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await kelRequest<MuseStatus>('/api/transcription', { action: 'status' }));
    } catch {
      setStatus({ mode: 'unavailable', has_key: false });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (focused) ref.current?.scrollIntoView?.({ block: 'center' });
  }, [focused]);

  const save = async () => {
    if (!draft) return;
    setBusy(true);
    setNote(null);
    try {
      await window.kelAPI?.credentials?.set(MUSE_PROVIDER, 'api_key', draft);
      setDraft(null);
      onChanged();
      await refresh();
      setNote('Saved. Ramble transcribes with this key now.');
    } catch (err) {
      setNote(`Couldn't save the Muse key. ${failureSentence(err, 'Kel did not answer — try again.')}`);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setNote(null);
    try {
      await window.kelAPI?.credentials?.remove(MUSE_PROVIDER);
      onChanged();
      await refresh();
      setNote('Removed the Muse key Kel kept.');
    } catch (err) {
      setNote(`Couldn't remove the Muse key. ${failureSentence(err, 'Kel did not answer — try again.')}`);
    } finally {
      setBusy(false);
    }
  };

  const ready = Boolean(status?.has_key) || status?.mode === 'fixture';
  const chip = <span className={toneChipClass(ready ? 'ok' : 'wait')}>{status ? (ready ? 'Ready' : 'Needs setup') : 'Checking'}</span>;
  return (
    <details className="kel-shell-provider" id="muse" ref={ref} open={focused || undefined} data-testid="muse-key-card">
      <summary>
        <span>Muse</span>
        <span className="kel-meta">Ramble transcription</span>
        <span className="kel-grow" />
        {chip}
      </summary>
      <KelCard
        title="Muse"
        chip={chip}
        actions={
          <span className="kel-row">
            <KelButton
              variant={ready ? 'secondary' : 'primary'}
              disabled={busy}
              onClick={() => setDraft((value) => (value === null ? '' : null))}
            >
              {stored ? 'Update key' : 'Set up'}
            </KelButton>
            {stored && (
              <KelButton variant="quiet" disabled={busy} onClick={() => void remove()}>
                Remove key
              </KelButton>
            )}
          </span>
        }
      >
        <p className="kel-sub">API · Meta Model key for Ramble's transcription</p>
        <p className="kel-meta" data-testid="muse-key-source">{museSourceLine(status, stored)}</p>
        {draft !== null && (
          <div className="kel-row">
            <input
              className="kel-input"
              type="password"
              aria-label="Muse API key"
              placeholder="paste the key — it goes to the OS store, never the page"
              value={draft}
              autoFocus={focused}
              onChange={(event) => setDraft(event.target.value)}
            />
            <KelButton variant="primary" disabled={busy || !draft || !secureAvailable} onClick={() => void save()}>
              Save
            </KelButton>
            <KelButton variant="quiet" disabled={busy} onClick={() => setDraft(null)}>
              Cancel
            </KelButton>
          </div>
        )}
        {!secureAvailable && (
          <p className="kel-meta">OS-backed storage is unavailable on this system, so Kel cannot store a key here.</p>
        )}
        {note && <p className="kel-meta">{note}</p>}
      </KelCard>
    </details>
  );
};

export default MuseKeyCard;
