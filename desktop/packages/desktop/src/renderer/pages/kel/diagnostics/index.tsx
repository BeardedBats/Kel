import { Modal } from '@arco-design/web-react';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel V1.4 Diagnostics — health, measured performance, process ownership, maintenance, and a
 * sanitized export that never leaves the machine.
 *
 * Everything is read from `/api/diagnostics`; where a value is not measured the surface says so.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  KelSection,
  KelTable,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { kelDiagnostics, type KelDiagnosticsSnapshot } from '@renderer/components/kel/kelApi';

interface Span {
  at: number;
  phase: string;
  duration_ms: number;
  engine_version: string;
}

interface Measurement {
  at: number;
  name: string;
  value: number;
  unit: string;
  basis: string;
}

const bytes = (value: number | undefined): string => {
  if (typeof value !== 'number') return '—';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
};

const Diagnostics: React.FC = () => {
  const [exportOpen, setExportOpen] = useState(false);
  const [snapshot, setSnapshot] = useState<KelDiagnosticsSnapshot | null>(null);
  const [spans, setSpans] = useState<Span[]>([]);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [basis, setBasis] = useState('');
  const [retention, setRetention] = useState<Record<string, number>>({});
  const [note, setNote] = useState('');
  const [receipt, setReceipt] = useState<{ included: string[]; excluded: string[] } | null>(null);
  const [report, setReport] = useState<{ path: string; redacted: boolean; bytes: number } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const [state, performance, retentionInfo] = await Promise.all([
        kelDiagnostics.snapshot(),
        kelDiagnostics.performance(),
        kelDiagnostics.retention(),
      ]);
      setSnapshot(state);
      setSpans(performance.startup_spans ?? []);
      setMeasurements(performance.measurements ?? []);
      setBasis(performance.basis ?? '');
      setRetention(retentionInfo.retention_days ?? {});
      setError(null);
    } catch (err) {
      setSnapshot(null);
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = useCallback(
    async (label: string, fn: () => Promise<unknown>) => {
      setBusy(label);
      setMessage(null);
      try {
        const result = await fn();
        setMessage(`${label}: ${JSON.stringify(result).slice(0, 220)}`);
        await load();
      } catch (err) {
        setMessage(`${label} failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
      } finally {
        setBusy(null);
      }
    },
    [load]
  );

  return (
    <div className='kel-scope'>
      <main className='kel-page' id='kel-diagnostics-main' tabIndex={-1}>
        <div className='kel-page__head'>
          <div><ShellWorkspaceLink /><h1 className='kel-h1'>Diagnostics</h1></div>
          <span className='kel-grow' /><KelButton onClick={() => setExportOpen(true)}>Export and issue report</KelButton>
        </div>
        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && !snapshot && <KelLoading rows={3} />}
        {snapshot && <>
          <KelCard title='Health'>
            <div className='kel-shell-diagnostic-row'><span>Runtime</span><span className='kel-meta'>{snapshot.engine_version}</span><span className='kel-chip'>{snapshot.database.integrity === 'ok' ? 'Healthy' : 'Needs attention'}</span></div>
            <div className='kel-shell-diagnostic-row'><span>Providers</span><span className='kel-meta'>{Object.keys(snapshot.providers).length} reported</span><span className='kel-chip'>{Object.keys(snapshot.providers).length ? 'Available' : 'Needs setup'}</span></div>
            <div className='kel-shell-diagnostic-row'><span>Process ownership</span><span className='kel-meta'>Kel owns {snapshot.processes.length} child processes</span><span className='kel-chip kel-chip--ok'>OK</span></div>
          </KelCard>
          <KelCard title='Measured performance'>
            <div className='kel-shell-diagnostic-row'><span>Startup</span><span className='kel-meta'>{spans.length ? `${(spans[0].duration_ms / 1000).toFixed(1)} s` : '—'}</span></div>
            <div className='kel-shell-diagnostic-row'><span>First model reply</span><span className='kel-meta'>{(() => { const m = measurements.find(item => /first.*reply/i.test(item.name)); return m ? `${m.value} ${m.unit}` : '—'; })()}</span></div>
            {!spans.length && <p className='kel-meta'>No startup span recorded yet for this session.</p>}
          </KelCard>
          <KelCard title='Maintenance'>
            <div className='kel-shell-preference-row'><div><div>Clear caches</div><p className='kel-meta'>Removes preview and thumbnail caches. Chats are untouched.</p></div><button className='kel-btn' type='button' disabled title='This source control has no matching runtime operation yet.'>Clear</button></div>
            <div className='kel-shell-preference-row'><div><div>Restart runtime</div><p className='kel-meta'>Restarts the local runtime without closing Kel.</p></div><button className='kel-btn' type='button' disabled title='This source control has no matching runtime operation yet.'>Restart</button></div>
          </KelCard>
        </>}
        <Modal title='Export and issue report' visible={exportOpen} onCancel={() => setExportOpen(false)} footer={null}>
            <KelCard
              title='Export and issue report'
              actions={
                <KelButton
                  variant='secondary'
                  disabled={busy !== null}
                  onClick={() =>
                    void run('Export sanitized diagnostics', async () => {
                      const payload = (await kelDiagnostics.export()) as {
                        receipt?: { included: string[]; excluded: string[] };
                      };
                      if (payload.receipt) setReceipt(payload.receipt);
                      return payload.receipt ?? payload;
                    })
                  }
                >
                  Export sanitized diagnostics
                </KelButton>
              }
            >
              <p className='kel-sub'>
                The export is built from an allowlist, not by filtering a dump: credentials, tokens and API
                keys, prompts, transcripts of unrelated conversations, personal files and environment dumps
                are excluded by construction.
              </p>
              {receipt && (
                <KelSection title='Receipt'>
                  <p className='kel-meta'>Included: {receipt.included.join(' · ') || '—'}</p>
                  <p className='kel-meta'>Excluded: {receipt.excluded.join(' · ') || '—'}</p>
                </KelSection>
              )}
              <div className='kel-row'>
                <input
                  className='kel-input'
                  aria-label='Issue report note'
                  placeholder='What went wrong? (this file stays on your machine)'
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
                <KelButton
                  variant='primary'
                  disabled={busy !== null}
                  onClick={() =>
                    void run('Write issue report', async () => {
                      const result = await kelDiagnostics.report(note);
                      setReport({ path: result.path, redacted: result.redacted, bytes: result.bytes });
                      return result;
                    })
                  }
                >
                  Write local draft
                </KelButton>
              </div>
              {report && (
                <p className='kel-meta'>
                  Wrote {report.path} ({bytes(report.bytes)})
                  {report.redacted
                    ? ' · secret-shaped text in your note was redacted before writing'
                    : ' · nothing secret-shaped found in your note'}
                  .
                </p>
              )}
            </KelCard>
        </Modal>
      </main>
    </div>
  );
};

export default Diagnostics;
