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
  KelErrorState,
  KelLoading,
  KelSection,
  KelTable,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
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
  const [error, setError] = useState<string | null>(null);

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
      setError(err instanceof Error ? err.message : 'The engine did not answer.');
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
        setMessage(`${label} failed: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setBusy(null);
      }
    },
    [load]
  );

  return (
    <div className='kel-scope'>
      <a className='kel-skip' href='#kel-diagnostics-main'>
        Skip to main content
      </a>
      <main className='kel-page' id='kel-diagnostics-main' tabIndex={-1}>
        <div className='kel-page__head'>
          <div>
            <h1 className='kel-h1'>Diagnostics</h1>
            <p className='kel-sub'>
              {snapshot
                ? `Engine ${snapshot.engine_version} · ${snapshot.counts.jobs} jobs · ${snapshot.counts.runs} runs · database integrity ${snapshot.database.integrity}`
                : 'Reading engine health…'}
            </p>
          </div>
          <span className='kel-grow' />
          <KelButton variant='secondary' onClick={() => void load()}>
            Reload
          </KelButton>
          <KelButton
            variant='primary'
            disabled={busy !== null}
            onClick={() => void run('Observe now', () => kelDiagnostics.observe())}
          >
            Observe now
          </KelButton>
        </div>

        {error && (
          <KelErrorState
            title='Diagnostics could not be read'
            cause={error}
            fix='Check that the Kel engine is running, then press Reload.'
          />
        )}
        {!error && !snapshot && <KelLoading rows={4} />}
        {message && <p className='kel-meta'>{message}</p>}

        {snapshot && (
          <>
            <KelCard title='Health'>
              <KelTable
                head={['Measure', 'Value', 'Note']}
                rows={[
                  ['Database integrity', snapshot.database.integrity, 'PRAGMA integrity_check'],
                  ['Database size', bytes(snapshot.database.size_bytes), 'main file'],
                  ['Write-ahead log', bytes(snapshot.database.wal_bytes), 'wal sidecar'],
                  [
                    'Free pages',
                    `${snapshot.database.freelist_pages} of ${snapshot.database.page_count}`,
                    `${snapshot.database.fragmentation_percent}% fragmented`,
                  ],
                  [
                    'Runs past their fence',
                    String(snapshot.runs.expired_unfenced),
                    snapshot.runs.expired_unfenced > 0
                      ? 'the engine will fence these on its next sweep'
                      : 'none waiting',
                  ],
                ]}
              />
              {snapshot.database.problems.length > 0 && (
                <p className='kel-meta'>
                  Problems: {snapshot.database.problems.join(' · ')} — database health is reported, not
                  guessed.
                </p>
              )}
            </KelCard>

            <KelCard title='Measured performance'>
              {spans.length === 0 ? (
                <KelEmpty
                  title='No startup span recorded yet.'
                  why='The engine records the cost of its own start on every launch; this install has none in the window.'
                />
              ) : (
                <KelTable
                  head={['Phase', 'Duration', 'Engine', 'When']}
                  rows={spans.map((span, index) => [
                    <span className='kel-strong' key={`s${index}`}>
                      {span.phase}
                    </span>,
                    `${span.duration_ms} ms`,
                    span.engine_version,
                    formatWhen(span.at),
                  ])}
                />
              )}
              {measurements.length > 0 && (
                <KelSection title='Measurements'>
                  <KelTable
                    head={['Name', 'Value', 'Basis', 'When']}
                    rows={measurements.map((row, index) => [
                      row.name,
                      `${row.value} ${row.unit}`,
                      row.basis,
                      formatWhen(row.at),
                    ])}
                  />
                </KelSection>
              )}
              <p className='kel-meta'>{basis}</p>
            </KelCard>

            <KelCard title='Providers'>
              {Object.keys(snapshot.providers).length === 0 ? (
                <KelEmpty
                  title='No provider has reported state yet.'
                  why='Provider health, quota and latency appear here once the engine has talked to one.'
                />
              ) : (
                <KelTable
                  head={['Provider', 'Failures', 'Circuit until', 'Quota', 'Observed']}
                  rows={Object.entries(snapshot.providers).map(([provider, state]) => [
                    <span className='kel-strong' key={`${provider}-n`}>
                      {provider}
                    </span>,
                    String((state as Record<string, unknown>).failures ?? 0),
                    (state as Record<string, unknown>).circuit_until
                      ? formatWhen(Number((state as Record<string, unknown>).circuit_until))
                      : 'closed',
                    (state as Record<string, unknown>).quota === undefined ||
                    (state as Record<string, unknown>).quota === null
                      ? 'Not reported'
                      : `${(state as Record<string, unknown>).quota}% left`,
                    (state as Record<string, unknown>).quota_observed_at
                      ? formatWhen(Number((state as Record<string, unknown>).quota_observed_at))
                      : '—',
                  ])}
                />
              )}
            </KelCard>

            <KelCard title='Process ownership'>
              {snapshot.processes.length === 0 ? (
                <p className='kel-meta'>
                  No worker process is recorded — Kel owns nothing right now.
                </p>
              ) : (
                <KelTable
                  head={['Run', 'PID', 'Alive', 'Deadline', 'Identity']}
                  rows={snapshot.processes.map((row) => [
                    <span className='kel-code' key={`${row.run_id}-r`}>
                      {row.run_id.slice(0, 12)}
                    </span>,
                    String(row.pid),
                    row.alive ? 'yes' : 'no — orphan candidate',
                    row.past_deadline ? 'past deadline' : formatWhen(row.deadline),
                    <span className='kel-meta' key={`${row.run_id}-i`}>
                      {row.identity}
                    </span>,
                  ])}
                />
              )}
            </KelCard>

            <KelCard
              title='Maintenance'
              actions={
                <span className='kel-row'>
                  <KelButton
                    variant='secondary'
                    disabled={busy !== null}
                    onClick={() => void run('Purge expired observations', () => kelDiagnostics.purge())}
                  >
                    Purge expired observations
                  </KelButton>
                  <KelButton
                    variant='secondary'
                    disabled={busy !== null}
                    onClick={() => void run('Compact database', () => kelDiagnostics.compact())}
                  >
                    Compact database
                  </KelButton>
                </span>
              }
            >
              <KelTable
                head={['Retention', 'Days kept', 'What it applies to']}
                rows={Object.entries(retention).map(([key, days]) => [
                  <span className='kel-strong' key={`${key}-k`}>
                    {key}
                  </span>,
                  String(days),
                  'observations only — jobs, memories and approvals are never purged',
                ])}
              />
              <p className='kel-meta'>
                Compaction writes a backup first, then vacuums; the receipt names both sizes.
              </p>
            </KelCard>

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
          </>
        )}
      </main>
    </div>
  );
};

export default Diagnostics;
