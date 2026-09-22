import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel V1.4 Work Center — every job, its real state, its wait reason, and its budget.
 * Read-only over `/api/state` (jobs) and `/api/team` (assignments); the engine owns all state.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  KelMeter,
  KelSection,
  KelStatusChip,
  KelTable,
  formatWhen,
  statusFromDerived,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { NeedsAttention } from '@renderer/components/kel/KelNeedsAttention';
import { assignmentLine, staffingSummary } from '@renderer/components/kel/staffingLanguage';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { VERDICT_TEXT, routeSentence } from '@renderer/components/kel/workLanguage';
import {
  kelArtifact,
  kelControl,
  kelApproval,
  kelRetry,
  kelSend,
  kelWorkRows,
  type KelWorkRow,
  kelProviders,
  kelRecipePropose,
  kelRecipeSave,
  kelState,
  kelTeam,
  type KelAssignment,
  type KelContinuationCandidate,
  type KelJobRoute,
  type KelWorkJob,
} from '@renderer/components/kel/kelApi';

const WAIT_REASON: Record<string, string> = {
  QUEUED: 'Queued — Kel will pick this up in order.',
  READY: 'Ready to run as soon as a model is available.',
  PAUSED: 'Paused — resume when you are ready.',
  AWAITING_USER: 'Waiting on you — an approval is pending.',
  WAITING_RESOURCE: 'Waiting for an available model — Kel will continue automatically.',
  BLOCKED: 'Blocked by a safety rule; the reason is recorded.',
};

/**
 * What a waiting job is actually waiting for (D7/D19). A route-blocked job resumes by itself when
 * a model becomes available; a job waiting without a route block is an *interrupted run* — the
 * engine fenced it and will not replay it on its own, so promising an automatic continuation there
 * would be a state lie. That one names the person's own next step instead.
 */
const waitReason = (job: KelWorkJob): string | null => {
  if (job.state === 'WAITING_RESOURCE' && !job.route_block) {
    return 'A run stopped mid-flight. Your work is preserved — reply “continue” in the chat for a fresh attempt.';
  }
  return WAIT_REASON[job.state] ?? null;
};

// Human-visual repair: milestone states in user language — no raw engine enums.
// (VERDICT_TEXT and the routing sentence live in workLanguage.ts, shared with the Activity view.)
const MILESTONE_STATE_TEXT: Record<string, string> = {
  QUEUED: 'Waiting to start',
  RUNNING: 'In progress',
  ACCEPTED: 'Accepted',
  BLOCKED: 'Blocked',
  FAILED: 'Failed',
};

const DIRECT_LABEL: Record<string, string> = {
  answer: 'Answer request',
  resume: 'Resume',
  stop: 'Stop',
  retry: 'Try again',
};

const WorkCenter: React.FC = () => {
  const [jobs, setJobs] = useState<KelWorkJob[] | null>(null);
  const [routes, setRoutes] = useState<Record<string, KelJobRoute>>({});
  const [providerLabels, setProviderLabels] = useState<Record<string, string>>({});
  const [assignments, setAssignments] = useState<KelAssignment[]>([]);
  const [continuation, setContinuation] = useState<KelContinuationCandidate[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<{ milestone: string; text: string } | null>(null);
  const [recipeDraft, setRecipeDraft] = useState<{
    recipe: Record<string, unknown>;
    preview: { steps: string[]; kind: string; milestones: number };
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [rowActions, setRowActions] = useState<Record<string, KelWorkRow>>({});

  const load = useCallback(async () => {
    try {
      const [state, team, providers] = await Promise.all([
        kelState(),
        kelTeam.office('default'),
        // D19: the route sentence names providers the way a person knows them, so the inventory
        // of names is read alongside the state (never the engine's raw ids).
        kelProviders.list().catch((): null => null),
      ]);
      setJobs(state.jobs ?? []);
      setRoutes(state.routes ?? {});
      setProviderLabels(
        Object.fromEntries(
          ((providers as { providers?: { provider: string; label: string }[] } | null)?.providers ?? []).map(
            (item) => [item.provider, item.label]
          )
        )
      );
      setContinuation(state.continuation ?? []);
      setAssignments(team.assignments ?? []);
      // V2-06 follow-through: the rows are the same authoritative surface the chat's Work panel
      // reads, so every job here can offer its one action with the id that action needs.
      const conversations = Array.from(
        new Set(
          (state.jobs ?? [])
            .map((job) => job.conversation)
            .filter((id): id is string => Boolean(id))
        )
      ).slice(0, 4);
      const rowLists = await Promise.all(
        conversations.map((cid) => kelWorkRows(cid).catch((): KelWorkRow[] => []))
      );
      const merged: Record<string, KelWorkRow> = {};
      for (const list of rowLists) for (const row of list) merged[row.job_id] = row;
      setRowActions(merged);
      setError(null);
    } catch (err) {
      setJobs([]);
      setError(err);
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
        setNote(`${label} failed. ${failureSentence(err, 'The engine did not answer — try again.')}`);
      } finally {
        setBusy(false);
      }
    },
    [load]
  );

  const actDirect = useCallback(
    async (jobId: string, direct: NonNullable<KelWorkRow['direct']>) => {
      await act(`Next step (${direct.action})`, async () => {
        if (direct.action === 'answer' && direct.id) {
          await kelApproval(direct.id, true, rowActions[jobId]?.related?.conversation);
        } else if (direct.action === 'resume' && direct.route === '/api/send') {
          await kelSend(rowActions[jobId]?.related?.conversation ?? 'main', 'continue');
        } else if (direct.action === 'resume') {
          await kelControl(jobId, 'resume');
        } else if (direct.action === 'stop') {
          await kelControl(jobId, 'cancel');
        } else if (direct.action === 'retry' && direct.id) {
          await kelRetry(direct.id);
        }
      });
    },
    [act, rowActions]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const waiting = (jobs ?? []).filter((job) =>
    ['AWAITING_USER', 'PAUSED', 'WAITING_RESOURCE', 'BLOCKED'].includes(job.state)
  ).length;
  // Design system §6: the same components switch to compact density above ten rows on table-first
  // views, rather than shrinking type below the scale.
  const dense = (jobs?.length ?? 0) + (assignments?.length ?? 0) > 10;
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
    <div className="kel-scope" data-density={dense ? 'compact' : 'comfortable'}>
      <a className="kel-skip" href="#kel-work-main">
        Skip to main content
      </a>
      <main className="kel-page" id="kel-work-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <ShellWorkspaceLink /><h1 className="kel-h1">Work</h1>
          </div>
          <span className="kel-grow" />
          <KelButton variant="secondary" disabled={!activeJob || busy} onClick={() => activeJob && void act('Recipe draft', async () => { setRecipeDraft(await kelRecipePropose(activeJob.id)); })}>
            Save as a recipe
          </KelButton>
        </div>


        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && jobs === null && <KelLoading rows={4} />}

        {!error && jobs !== null && jobs.length === 0 && continuation.length === 0 && (
          <KelCard title="Jobs"><KelEmpty
            title="No unfinished work in this project."
            why="Kel keeps unfinished jobs here so you can pick them up."
          /></KelCard>
        )}

        {!error && jobs !== null && jobs.length > 0 && (
          <KelCard title="Jobs">
            <KelTable
              head={['Job', 'State', 'Current step', 'Budget', 'Updated', 'Next']}
              rows={jobs.map((job) => [
                <span className="kel-strong" key={`${job.id}-id`}>
                  {job.contract?.request ?? job.id}
                </span>,
                <KelStatusChip key={`${job.id}-state`} status={statusFromDerived(job.state)} />,
                <span key={`${job.id}-step`}>
                  {job.contract?.milestones?.[0]?.objective ?? '—'}
                  {waitReason(job) ? (
                    <>
                      <br />
                      <span className="kel-meta">{waitReason(job)}</span>
                    </>
                  ) : null}
                </span>,
                <KelMeter key={`${job.id}-budget`} used={job.spent ?? 0} total={job.budget ?? 8} />,
                <span className="kel-meta" key={`${job.id}-when`}>
                  {formatWhen(job.updated ?? null)}
                </span>,
                <span key={`${job.id}-next`}>
                  {rowActions[job.id]?.direct ? (
                    <KelButton
                      variant="secondary"
                      disabled={busy}
                      onClick={() => void actDirect(job.id, rowActions[job.id].direct as NonNullable<KelWorkRow['direct']>)}
                    >
                      {DIRECT_LABEL[rowActions[job.id].direct?.action ?? ''] ?? 'Continue'}
                    </KelButton>
                  ) : (
                    <span className="kel-meta">{rowActions[job.id]?.next ?? '—'}</span>
                  )}
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
                {(activeJob.state === 'RUNNING' || activeJob.state === 'QUEUED' || activeJob.state === 'READY') && (
                  <KelButton
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void act('Pause', () => kelControl(activeJob.id, 'pause'))}
                  >
                    Pause
                  </KelButton>
                )}
                {activeJob.state === 'PAUSED' && (
                  <KelButton
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void act('Resume', () => kelControl(activeJob.id, 'resume'))}
                  >
                    Resume
                  </KelButton>
                )}
                {!['CLOSED', 'CANCELLED'].includes(activeJob.state) && (
                  <KelButton
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void act('Cancel', () => kelControl(activeJob.id, 'cancel'))}
                  >
                    Cancel
                  </KelButton>
                )}
                <KelButton
                  variant="quiet"
                  disabled={busy}
                  onClick={() =>
                    void act('Recipe draft', async () => {
                      setRecipeDraft(await kelRecipePropose(activeJob.id));
                    })
                  }
                >
                  Save as a recipe
                </KelButton>
              </span>
            }
          >
            <p className="kel-sub">
              {`Progress: ${accepted.length} of ${activeMilestones.length} steps verified · `}
              {activeJob.verdict
                ? VERDICT_TEXT[activeJob.verdict] ?? `verification status: ${activeJob.verdict.toLowerCase().replace(/_/g, ' ')}`
                : 'verification runs after the checks pass'}
            </p>
            {routeSentence(routes[activeJob.id], providerLabels) && (
              <p className="kel-meta">{routeSentence(routes[activeJob.id], providerLabels)}</p>
            )}
            {recipeDraft && (
              <KelSection title="Save as a recipe">
                <p className="kel-sub">
                  {`Draft from this job: ${recipeDraft.preview.milestones} steps (${recipeDraft.preview.kind}). It is saved only when you confirm.`}
                </p>
                <p className="kel-meta">{recipeDraft.preview.steps.join(' · ')}</p>
                <div className="kel-row">
                  <KelButton
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                      void act('Recipe saved', async () => {
                        await kelRecipeSave(recipeDraft.recipe);
                        setRecipeDraft(null);
                      })
                    }
                  >
                    Save recipe
                  </KelButton>
                  <KelButton variant="quiet" onClick={() => setRecipeDraft(null)}>
                    Cancel
                  </KelButton>
                </div>
              </KelSection>
            )}
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
                    {MILESTONE_STATE_TEXT[m.runtime.state] ??
                      (m.runtime.state ? m.runtime.state.toLowerCase().replace(/_/g, ' ') : 'unknown')}
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

        <KelCard title="Waiting to continue">
          {continuation.length === 0 ? (
            <KelEmpty
              title="Nothing."
              why="When a job pauses, is interrupted, or waits on you, it appears here with the exact reason."
            />
          ) : (
            <ol>
              {continuation.map((candidate, index) => {
                const id = candidate.job?.id ?? candidate.job_id ?? `candidate-${index}`;
                const reasons = candidate.reasons ?? [];
                const related = (jobs ?? []).find((job) => job.id === id);
                const verdictLabel =
                  candidate.verdict === 'VERIFIED'
                    ? 'verified'
                    : candidate.verdict === 'FAILED'
                      ? 'checks failed'
                      : candidate.verdict
                        ? 'not verified yet'
                        : null;
                return (
                  <li key={id}>
                    <span className="kel-strong">
                      {`${index + 1}. ${
                        candidate.summary ?? related?.contract?.request ?? 'A task is waiting to continue'
                      }`}
                    </span>{' '}
                    <KelStatusChip
                      status={statusFromDerived(candidate.state ?? candidate.job?.state ?? 'QUEUED')}
                    />
                    <div className="kel-meta">
                      {verdictLabel ? `${verdictLabel} · ` : ''}
                      {reasons.length ? `${reasons.join(', ')} · ` : ''}
                      To continue, reply “continue” (or pick a number) in the chat — Kel never resumes on its
                      own.
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
              why="Kel assigns a specialist only when a milestone actually runs — there are never decorative specialists."
            />
          ) : (
            <div>
              <p className='kel-meta' style={{ margin: '0 0 6px' }}>
                {staffingSummary(assignments)}
              </p>
              {assignments.map((assignment) => (
                <div className='kel-attention__row' key={assignment.assignment_id}>
                  <div className='kel-attention__text'>
                    <strong>{assignmentLine(assignment)}</strong>
                    <span className='kel-meta'>{`${assignment.role} · updated ${formatWhen(assignment.updated)}`}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </KelCard>
      </main>
    </div>
  );
};

export default WorkCenter;
