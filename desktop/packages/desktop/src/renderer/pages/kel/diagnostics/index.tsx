import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import Modal from '@renderer/components/base/AionModal';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel V1.4 Diagnostics — health, measured performance, process ownership, maintenance, and one
 * sanitized issue report that is saved on this computer (never sent anywhere).
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
import { shortPlace } from '@renderer/components/kel/workLanguage';
import '@renderer/styles/kel-work.css';

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

/** Controls the engine cannot perform yet say so in visible words, not only in a tooltip. */
const NOT_AVAILABLE = 'Not available in this version yet.';

const Diagnostics: React.FC = () => {
  const isMobile = Boolean(useLayoutContext()?.isMobile);
  const [exportPreviewVersion, setExportPreviewVersion] = useState(0);
  const [exportPreviewError, setExportPreviewError] = useState<unknown>(null);
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

  useEffect(() => {
    if (!exportOpen) return;
    let canceled = false;
    setReceipt(null);
    setExportPreviewError(null);
    void kelDiagnostics.export().then((payload) => {
      if (!canceled && payload.receipt) setReceipt(payload.receipt as { included: string[]; excluded: string[] });
    }).catch((err: unknown) => { if (!canceled) setExportPreviewError(err); });
    return () => { canceled = true; };
  }, [exportOpen, exportPreviewVersion]);

  const run = useCallback(
    async (label: string, fn: () => Promise<unknown>) => {
      setBusy(label);
      setMessage(null);
      try {
        const result = await fn();
        void result;
        setMessage('Report saved on this computer.');
        await load();
      } catch (err) {
        setMessage(`${label} failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
      } finally {
        setBusy(null);
      }
    },
    [load]
  );

  const saveReport = (): void =>
    void run('Saving the report', async () => {
      const result = await kelDiagnostics.report(note);
      setReport({ path: result.path, redacted: result.redacted, bytes: result.bytes });
      return result;
    });

  // No full paths (JR-16): the file name and where it lives, in words.
  const reportLine = report
    ? `Saved ${shortPlace(report.path)} (${bytes(report.bytes)}) in the diagnostics folder of your Kel data${report.redacted ? ' · secret-looking text in your note was hidden' : ''}.`
    : null;

  return (
    <div className='kel-scope'>
      <main className='kel-page' id='kel-diagnostics-main' tabIndex={-1}>
        <div className='kel-page__head'>
          <div><ShellWorkspaceLink /><h1 className='kel-h1'>Diagnostics</h1></div>
          <span className='kel-grow' /><KelButton variant="primary" onClick={() => setExportOpen(true)}>Export and issue report</KelButton>
        </div>
        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && !snapshot && <KelLoading rows={3} />}
        {snapshot && <>
          <KelCard title='Health'>
            <div className='kel-shell-diagnostic-row'><span>Runtime</span><span className='kel-meta'>{snapshot.engine_version}</span><span className={`kel-chip ${snapshot.database.integrity === 'ok' ? 'kel-chip--ok' : 'kel-chip--wait'}`}>{snapshot.database.integrity === 'ok' ? 'Healthy' : 'Needs attention'}</span></div>
            <div className='kel-shell-diagnostic-row'><span>Providers</span><span className='kel-meta'>{Object.keys(snapshot.providers).length} reported</span><span className={`kel-chip ${Object.keys(snapshot.providers).length ? 'kel-chip--ok' : 'kel-chip--wait'}`}>{Object.keys(snapshot.providers).length ? 'Available' : 'Needs setup'}</span></div>
            <div className='kel-shell-diagnostic-row'><span>Process ownership</span><span className='kel-meta'>Kel owns {snapshot.processes.length} child processes</span><span className='kel-chip kel-chip--ok'>OK</span></div>
          </KelCard>
          <KelCard title='Measured performance'>
            <div className='kel-shell-diagnostic-row'><span>Startup</span><span className='kel-meta'>{spans.length ? `${(spans[0].duration_ms / 1000).toFixed(1)} s` : '—'}</span></div>
            <div className='kel-shell-diagnostic-row'><span>First model reply</span><span className='kel-meta'>{(() => { const m = measurements.find(item => /first.*reply/i.test(item.name)); return m ? `${m.value} ${m.unit}` : '—'; })()}</span></div>
            {!spans.length && <p className='kel-meta'>No startup span recorded yet for this session.</p>}
          </KelCard>
          <KelCard title='Maintenance'>
            <div className='kel-shell-preference-row'><div><div>Clear caches</div><p className='kel-meta'>Removes preview and thumbnail caches. Chats are untouched.</p><p className='kel-meta kel-work-why-disabled' id='kel-diag-clear-why'>{NOT_AVAILABLE}</p></div><button className='kel-btn kel-btn--danger' type='button' disabled aria-describedby='kel-diag-clear-why'>Clear</button></div>
            <div className='kel-shell-preference-row'><div><div>Restart Kel's engine</div><p className='kel-meta'>Restarts Kel's engine without closing the app.</p><p className='kel-meta kel-work-why-disabled' id='kel-diag-restart-why'>{NOT_AVAILABLE}</p></div><button className='kel-btn kel-btn--primary' type='button' disabled aria-describedby='kel-diag-restart-why'>Restart</button></div>
          </KelCard>
        </>}
        <Modal className={isMobile ? undefined : 'kel-diagnostics-export-modal'} variant={isMobile ? undefined : 'standard'}
          title='Export and issue report' header={isMobile ? undefined : { title: 'Export and issue report', subtitle: 'Kel leaves out keys, file paths and chat text. The report is saved on this computer — nothing is sent.', showClose: false }}
          visible={exportOpen} onCancel={() => setExportOpen(false)} footer={null} alignCenter={isMobile ? undefined : false}
          style={isMobile ? undefined : { width: 560, top: 0, marginTop: 120 }} autoFocus focusLock>
          {isMobile ? (
            <KelCard title='Export and issue report'>
              <p className='kel-sub'>
                The report is built from an allowlist, not by filtering a dump: credentials, tokens and API
                keys, prompts, unrelated chats, personal files and environment details are left out. It is
                saved on this computer; nothing is sent.
              </p>
              {receipt && (
                <KelSection title='What the report includes'>
                  <p className='kel-meta'>Included: {receipt.included.join(' · ') || '—'}</p>
                  <p className='kel-meta'>Left out: {receipt.excluded.join(' · ') || '—'}</p>
                </KelSection>
              )}
              <div className='kel-row'>
                <input
                  className='kel-input'
                  aria-label='Issue report note'
                  placeholder='What went wrong? (optional)'
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
                <KelButton variant='primary' disabled={busy !== null} onClick={saveReport}>
                  Save report
                </KelButton>
              </div>
              {message && <p className='kel-meta' role='status'>{busy ? 'Working…' : message}</p>}
              {reportLine && <p className='kel-meta'>{reportLine}</p>}
            </KelCard>
          ) : (
            <div className='kel-diagnostics-export-body'>
              {exportPreviewError ? <KelFailureCard error={exportPreviewError} onRetry={() => setExportPreviewVersion((version) => version + 1)} /> : !receipt ? <KelLoading rows={2} /> : <>
                <div className='kel-diagnostics-export-receipt'>
                  <section><h3>Included</h3>
                    <p>✓ Engine version and counts</p><p>✓ Runtime state and retention</p><p>✓ Performance summary</p>
                  </section>
                  <section><h3>Excluded</h3>
                    <p>× API keys and credentials</p><p>× File contents and workspace paths</p><p>× Chat and transcript text</p>
                  </section>
                </div>
                <details className='kel-diagnostics-export-details'><summary>Full export receipt</summary><p>Included: {receipt.included.join(' · ')}</p><p>Excluded: {receipt.excluded.join(' · ')}</p></details>
              </>}
              <label className='kel-diagnostics-export-note'><span>What happened? (optional)</span><textarea rows={2} aria-label='Issue report note' value={note} onChange={(event) => setNote(event.target.value)} /></label>
              <div className='kel-diagnostics-export-actions'>
                <KelButton variant='quiet' disabled={busy !== null} onClick={() => setExportOpen(false)}>Close</KelButton>
                <KelButton variant='primary' disabled={busy !== null || !receipt} onClick={saveReport}>Save report</KelButton>
              </div>
              {message && <p className='kel-diagnostics-export-result' role='status'>{busy ? 'Working…' : message}</p>}
              {reportLine && <p className='kel-diagnostics-export-result'>{reportLine}</p>}
            </div>
          )}
        </Modal>
      </main>
    </div>
  );
};

export default Diagnostics;
