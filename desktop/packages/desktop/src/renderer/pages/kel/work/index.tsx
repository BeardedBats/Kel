/**
 * Kel V1.4 Work Center — every job, its real state, its wait reason, and its budget.
 * Read-only over `/api/state` (jobs) and `/api/team` (assignments); the engine owns all state.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelErrorState,
  KelLoading,
  KelMeter,
  KelSection,
  KelStatusChip,
  KelTable,
  formatWhen,
  statusFromDerived,
} from '@renderer/components/kel/KelPrimitives';
import {
  kelArtifact,
  kelControl,
  kelState,
  kelTeam,
  type KelAssignment,
  type KelContinuationCandidate,
  type KelWorkJob,
} from '@renderer/components/kel/kelApi';

const WAIT_REASON: Record<string, string> = {
  PAUSED: 'Paused — resume when you are ready.',
  AWAITING_USER: 'Waiting on you — an approval is pending.',
  WAITING_RESOURCE: 'Waiting on a resource; Kel will continue automatically.',
  BLOCKED: 'Blocked by a guardrail; the reason is recorded.',
};

const WorkCenter: React.FC = () => {
  const [jobs, setJobs] = useState<KelWorkJob[] | null>(null);
  const [assignments, setAssignments] = useState<KelAssignment[]>([]);
  const [continuation, setContinuation] = useState<KelContinuationCandidate[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<{ milestone: string; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<{ cause: string; fix: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const [state, team] = await Promise.all([kelState(), kelTeam.office('default')]);
      setJobs(state.jobs ?? []);
      setContinuation(state.continuation ?? []);
      setAssignments(team.assignments ?? []);
      setError(null);
    } catch (err) {
      setJobs([]);
      setError({
        cause: err instanceof Error ? err.message : 'The engine did not answer.',
        fix: 'Check that the Kel engine is running, then press Reload.',
      });
    }
  }, []);

  const act = useCallback(
    async (label: string, fn: () => Promise<unknown>) => {
      setBusy(true);
      setNote(null);
      try {
        await fn();
        setNote(`${label} sent to the engine.`);
        await load();
      } catch (err) {
        setNote(`${label} failed: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const waiting = (jobs ?? []).filter((job) =>
    ['AWAITING_USER', 'PAUSED', 'WAITING_RESOURCE', 'BLOCKED'].includes(job.state)
  ).length;
  const activeJob = jobs?.find((job) => job.id === (selected ?? jobs[0]?.id)) ?? null;
  const activeMilestones = activeJob
    ? Object.entries(activeJob.milestones ?? {}).map(([id, runtime]) => ({
        id,
        runtime,
        spec: (activeJob.contract?.milestones ?? []).find((m) => m.id === id),
      }))
    : [];
  const accepted = activeMilestones.filter((m) => m.runtime.state === 'ACCEPTED');
  const newestAccepted = accepted.length ? accepted[accepted.length - 1].id : null;

  // The receipt is shown by default for the newest accepted milestone; the per-row buttons stay
  // available, and a refusal from the engine is swallowed here because the row still reports it.
  useEffect(() => {
    if (!activeJob || !newestAccepted) return;
    let cancelled = false;
    void (async () => {
      try {
        const text = await kelArtifact(activeJob.id, newestAccepted);
        if (!cancelled) {
          setArtifact({
            milestone: newestAccepted,
            text: typeof text === 'string' ? text : JSON.stringify(text, null, 2),
          });
        }
      } catch {
        /* the receipt is optional; the View artifact button stays available */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeJob, newestAccepted]);

  return (
    <div className="kel-scope">
      <a className="kel-skip" href="#kel-work-main">
        Skip to main content
      </a>
      <main className="kel-page" id="kel-work-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <h1 className="kel-h1">Work</h1>
            <p className="kel-sub">
              {jobs === null
                ? 'Loading jobs…'
                : `${jobs.length} ${jobs.length === 1 ? 'job' : 'jobs'} in this project · ${waiting} waiting on you`}
            </p>
          </div>
          <span className="kel-grow" />
          <KelButton variant="secondary" onClick={() => void load()}>
            Reload
          </KelButton>
        </div>

        {error && <KelErrorState title="Work could not be loaded" cause={error.cause} fix={error.fix} />}
        {!error && jobs === null && <KelLoading rows={4} />}

        {!error && jobs !== null && jobs.length === 0 && (
          <KelEmpty
            title="No unfinished work in this project."
            why="Jobs appear here as soon as Kel accepts a task, and they stay until they are verified or cancelled."
          />
        )}

        {!error && jobs !== null && jobs.length > 0 && (
          <KelCard title="Jobs">
            <KelTable
              head={['Job', 'State', 'Current step', 'Budget', 'Updated']}
              rows={jobs.map((job) => [
                <span className="kel-strong" key={`${job.id}-id`}>
                  {job.contract?.request ?? job.id}
                </span>,
                <KelStatusChip key={`${job.id}-state`} status={statusFromDerived(job.state)} />,
                <span key={`${job.id}-step`}>
                  {job.contract?.milestones?.[0]?.objective ?? '—'}
                  {WAIT_REASON[job.state] ? (
                    <>
                      <br />
                      <span className="kel-meta">{WAIT_REASON[job.state]}</span>
                    </>
                  ) : null}
                </span>,
                <KelMeter key={`${job.id}-budget`} used={job.spent ?? 0} total={job.budget ?? 8} />,
                <span className="kel-meta" key={`${job.id}-when`}>
                  {formatWhen(job.id ? Date.now() / 1000 : null)}
                </span>,
              ])}
            />
          </KelCard>
        )}

        {activeJob && (
          <KelCard
            title={`Verification — ${activeJob.contract?.request?.slice(0, 60) ?? activeJob.id}`}
            chip={<KelStatusChip status={statusFromDerived(activeJob.state)} />}
            actions={
              <span className="kel-row">
                <KelButton
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void act('Pause', () => kelControl(activeJob.id, 'pause'))}
                >
                  Pause
                </KelButton>
                <KelButton
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void act('Resume', () => kelControl(activeJob.id, 'resume'))}
                >
                  Resume
                </KelButton>
                <KelButton
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void act('Cancel', () => kelControl(activeJob.id, 'cancel'))}
                >
                  Cancel
                </KelButton>
              </span>
            }
          >
            <p className="kel-sub">
              {`Worker reported: ${accepted.length} of ${activeMilestones.length} milestones accepted · Kel verified: `}
              {activeJob.verdict ?? 'not yet — verification runs after the checks pass'}
            </p>
            {activeMilestones.length === 0 ? (
              <KelEmpty
                title="No milestone has started yet."
                why="Kel reports work as it runs, and reports nothing as verified until the checks pass."
              />
            ) : (
              <KelTable
                head={['Milestone', 'Worker state', 'Attempts', 'Checks', 'Evidence']}
                rows={activeMilestones.map((m) => [
                  <span className="kel-strong" key={`${m.id}-n`}>
                    {m.spec?.objective ?? m.id}
                  </span>,
                  <span className="kel-meta" key={`${m.id}-s`}>
                    {m.runtime.state ?? 'unknown'}
                  </span>,
                  <span className="kel-meta" key={`${m.id}-a`}>
                    {`${m.runtime.attempts ?? 0}${(m.runtime.attempts ?? 0) > 1 ? ' · retried' : ''}`}
                  </span>,
                  <span className="kel-meta" key={`${m.id}-c`}>
                    {`${m.spec?.checks?.length ?? 0} checks${m.spec?.filename ? ` · ${m.spec.filename}` : ''}`}
                  </span>,
                  m.runtime.state === 'ACCEPTED' ? (
                    <KelButton
                      key={`${m.id}-e`}
                      variant="quiet"
                      disabled={busy}
                      onClick={() =>
                        void act('Open artifact', async () => {
                          const text = await kelArtifact(activeJob.id, m.id);
                          setArtifact({
                            milestone: m.id,
                            text: typeof text === 'string' ? text : JSON.stringify(text, null, 2),
                          });
                        })
                      }
                    >
                      View artifact
                    </KelButton>
                  ) : (
                    <span className="kel-meta" key={`${m.id}-e`}>
                      not verified — checks have not passed
                    </span>
                  ),
                ])}
              />
            )}
            {note && <p className="kel-meta">{note}</p>}
            {artifact && (
              <KelSection title={`Receipt — ${artifact.milestone}`}>
                <pre className="kel-code">{artifact.text.slice(0, 4000)}</pre>
              </KelSection>
            )}
          </KelCard>
        )}

        <KelCard title="Continuation">
          {continuation.length === 0 ? (
            <KelEmpty
              title="Nothing waiting to continue."
              why="When a job pauses, is interrupted, or waits on you, it appears here with the exact reason."
            />
          ) : (
            <ol>
              {continuation.map((candidate, index) => {
                const id = candidate.job?.id ?? candidate.job_id ?? `candidate-${index}`;
                const reasons = candidate.reasons ?? [];
                return (
                  <li key={id}>
                    <span className="kel-strong">{`${index + 1}. ${candidate.summary ?? id}`}</span>{' '}
                    <KelStatusChip
                      status={statusFromDerived(candidate.state ?? candidate.job?.state ?? 'QUEUED')}
                    />
                    <div className="kel-meta">
                      {candidate.verdict ? `verdict: ${candidate.verdict} · ` : ''}
                      {reasons.length ? `why: ${reasons.join(', ')}` : 'durable state only — no hidden reasoning'}
                      {' · '}
                      Continue from chat (say “continue”, or pick a number) — Kel never resumes work in the
                      background without you.
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </KelCard>

        <KelCard title="Team assignments">
          {assignments.length === 0 ? (
            <KelEmpty
              title="No specialist has been assigned yet."
              why="Kel assigns a specialist only when a milestone actually runs — there are never decorative workers."
            />
          ) : (
            <KelTable
              head={['Specialist', 'Role version', 'State', 'Provider', 'Budget', 'Updated']}
              rows={assignments.map((assignment) => [
                <span className="kel-strong" key={`${assignment.assignment_id}-role`}>
                  {assignment.role}
                </span>,
                <span className="kel-meta" key={`${assignment.assignment_id}-v`}>
                  {`v${assignment.role_version} · ${assignment.snapshot_digest.slice(0, 8)}`}
                </span>,
                <KelStatusChip
                  key={`${assignment.assignment_id}-state`}
                  status={statusFromDerived(assignment.derived_state)}
                />,
                <span className="kel-meta" key={`${assignment.assignment_id}-p`}>
                  {assignment.provider ? `${assignment.provider} / ${assignment.model ?? 'default'}` : '—'}
                </span>,
                <KelMeter
                  key={`${assignment.assignment_id}-budget`}
                  used={assignment.spent ?? 0}
                  total={assignment.budget ?? 8}
                />,
                <span className="kel-meta" key={`${assignment.assignment_id}-when`}>
                  {formatWhen(assignment.updated)}
                </span>,
              ])}
            />
          )}
        </KelCard>
      </main>
    </div>
  );
};

export default WorkCenter;
