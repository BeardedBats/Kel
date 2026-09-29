/**
 * D-81 — the Memory folder: where every AI tool Kel runs reads and writes, and nothing else.
 *
 * Shown on Settings → Permissions under the access mode. Read from the engine every time (nothing is
 * shown when the engine cannot say). D-87: only the folder, whether Codex's reads outside it are
 * blocked, and — until Nick allows Codex's stronger Windows sandbox once — the one button that asks
 * Windows (one administrator prompt from OpenAI's setup helper). No explanatory sentences.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { KelButton, KelCard } from './KelPrimitives';
import { kelMemoryFolder, type KelMemoryFolderState } from './kelApi';

export const KelMemoryFolderCard: React.FC = () => {
  const [state, setState] = useState<KelMemoryFolderState | null>(null);
  const [asking, setAsking] = useState(false);

  const load = useCallback(async () => {
    try {
      setState(await kelMemoryFolder.get());
    } catch {
      setState(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // While Windows' prompt is open, look again every few seconds until the setup has finished.
  useEffect(() => {
    if (!asking && state?.codex_setup !== 'running') return undefined;
    const timer = window.setInterval(() => {
      void load();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [asking, state?.codex_setup, load]);

  useEffect(() => {
    if (asking && state && state.codex_setup !== 'running') setAsking(false);
  }, [asking, state]);

  const allow = useCallback(async () => {
    setAsking(true);
    try {
      const answer = await kelMemoryFolder.setupCodexSandbox();
      if (answer.memory) setState(answer.memory);
    } catch {
      setAsking(false);
    }
  }, []);

  if (!state?.folder) return null;
  const running = asking || state.codex_setup === 'running';
  return (
    <KelCard title="Where the AI tools work" data-testid="kel-memory-folder-card">
      <div className="kel-row">
        <span className="kel-meta">Memory folder</span>
        <span className="kel-strong" data-testid="kel-memory-folder">
          {state.folder}
        </span>
      </div>
      <div className="kel-row" data-testid="kel-memory-codex" data-blocked={state.codex_reads_blocked ? 'yes' : 'no'}>
        <span className="kel-meta">Codex reads outside Memory</span>
        <span className="kel-strong">{state.codex_reads_blocked ? 'Blocked' : 'Not blocked'}</span>
      </div>
      {state.codex_setup === 'failed' && state.codex_error && <p className="kel-meta m-0">{state.codex_error}</p>}
      {state.codex_setup_available && (
        <div className="kel-row">
          <KelButton variant="secondary" disabled={running} onClick={() => void allow()}>
            {running ? 'Waiting for Windows…' : 'Block Codex reads outside Memory'}
          </KelButton>
        </div>
      )}
    </KelCard>
  );
};

export default KelMemoryFolderCard;
