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
  KelStatusChip,
  KelTable,
  formatWhen,
  statusFromDerived,
} from '@renderer/components/kel/KelPrimitives';
import { kelState, kelTeam, type KelAssignment, type KelWorkJob } from '@renderer/components/kel/kelApi';

const WAIT_REASON: Record<string, string> = {
  PAUSED: 'Paused — resume when you are ready.',
  AWAITING_USER: 'Waiting on you — an approval is pending.',
  WAITING_RESOURCE: 'Waiting on a resource; Kel will continue automatically.',
  BLOCKED: 'Blocked by a guardrail; the reason is recorded.',
};

const WorkCenter: React.FC = () => {
  const [jobs, setJobs] = useState<KelWorkJob[] | null>(null);
  const [assignments, setAssignments] = useState<KelAssignment[]>([]);
  const [error, setError] = useState<{ cause: string; fix: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const [state, team] = await Promise.all([kelState(), kelTeam.office('default')]);
      setJobs(state.jobs ?? []);
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

  useEffect(() => {
    void load();
  }, [load]);

  const waiting = (jobs ?? []).filter((job) =>
    ['AWAITING_USER', 'PAUSED', 'WAITING_RESOURCE', 'BLOCKED'].includes(job.state)
  ).length;

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
