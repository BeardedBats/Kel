import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel Work — every job, in the same plain words every other surface uses, with its one next step.
 *
 * Read-only over `/api/state` (jobs) and `/api/work` (each job's next action); the engine owns all
 * state. The default view speaks in user decisions (JR-11/JR-16): the job's title, its state from
 * the shared state words (workLanguage.ts), what it is waiting for, and one action. Steps, checks,
 * receipts, routing and budget live behind a closed "Details" disclosure.
 *
 * `?job=<id>` selects a job (the palette, Home "Needs you" and Activity link here).
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  KelMeter,
  KelSection,
  KelWorkChip,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { routeSentence, workWords } from '@renderer/components/kel/workLanguage';
import { requestTitle } from '@renderer/components/kel/needsAttention';
import { selectedWorkJob, currentWorkStep } from '@renderer/components/kel/workViewState';
import {
  KEL_ALL_CONVERSATIONS,
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
  type KelJobRoute,
  type KelWorkJob,
} from '@renderer/components/kel/kelApi';
import '@renderer/styles/kel-work.css';

/**
 * What a job is waiting for, in one sentence (D7/D19). A route-blocked job resumes by itself when a
 * model becomes available; one waiting without a route block is an interrupted run the engine will
 * not replay on its own, so it names the person's own next step instead of promising a continuation.
 */
const waitReason = (job: KelWorkJob): string | null => {
  if (job.state === 'WAITING_RESOURCE' && !job.route_block) {
    return 'A run stopped mid-flight. Your work is preserved — reply “continue” in the chat for a fresh attempt.';
  }
  if (job.state === 'WAITING_RESOURCE') return 'Waiting for an available model — Kel will continue automatically.';
  const view = workWords(job);
  return view.section === 'now' && job.state !== 'QUEUED' && job.state !== 'READY' ? null : view.sentence;
};

// Step states in user language — no raw engine enums.
const STEP_STATE_TEXT: Record<string, string> = {
  QUEUED: 'Not started',
  READY: 'Not started',
  RUNNING: 'In progress',
  ACCEPTED: 'Checked',
  BLOCKED: 'Needs your OK',
  FAILED: "Didn't pass",
  NEEDS_REPAIR: 'Being fixed',
  UNCERTAIN: 'Not fully checked',
  CANCELLED: 'Stopped',
};

const stepStateText = (state: string | undefined): string =>
  (state && STEP_STATE_TEXT[state]) || 'Not started';

const DIRECT_LABEL: Record<string, string> = {
  answer: 'Answer request',
  resume: 'Resume',
  stop: 'Stop',
  retry: 'Try again',
};

/** Attention first (JR-13): what waits on you, then what is going, then what finished; newest first. */
const SECTION_ORDER = { waiting: 0, now: 1, finished: 2 } as const;
const attentionOrder = (a: KelWorkJob, b: KelWorkJob): number =>
  SECTION_ORDER[workWords(a).section] - SECTION_ORDER[workWords(b).section] || (b.updated ?? 0) - (a.updated ?? 0);

/** How a control changes a job right away, so the page never needs a reload to show it. */
const OPTIMISTIC: Record<'pause' | 'resume' | 'cancel', { state: string; note: string }> = {
  pause: { state: 'PAUSED', note: 'Kel is pausing this.' },
  resume: { state: 'QUEUED', note: 'Kel is picking this back up.' },
  cancel: { state: 'CANCELLING', note: 'Kel is stopping this. Anything already checked is kept.' },
};

const WorkCenter: React.FC = () => {
  const [params, setParams] = useSearchParams();
  const requested = params.get('job');
  const [jobs, setJobs] = useState<KelWorkJob[] | null>(null);
  const [routes, setRoutes] = useState<Record<string, KelJobRoute>>({});
  const [providerLabels, setProviderLabels] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string | null>(requested);
  const [artifact, setArtifact] = useState<{ step: string; text: string } | null>(null);
  const [recipeDraft, setRecipeDraft] = useState<{
    recipe: Record<string, unknown>;
    preview: { steps: string[]; kind: string; milestones: number };
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [confirmStop, setConfirmStop] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [rowActions, setRowActions] = useState<Record<string, KelWorkRow>>({});
  const followUps = useRef<number[]>([]);
  // What a control just asked for, shown until the engine reports it (no reload, no flicker back).
  const [pending, setPending] = useState<Record<string, string>>({});

  useEffect(() => {
    if (requested) setSelected(requested);
  }, [requested]);

  const load = useCallback(async () => {
    try {
      const [state, providers] = await Promise.all([
        kelState(KEL_ALL_CONVERSATIONS),
        // D19: the route sentence names providers the way a person knows them.
        kelProviders.list().catch((): null => null),
      ]);
      setJobs(state.jobs ?? []);
      setPending((current) => {
        const next = { ...current };
        for (const job of state.jobs ?? []) {
          if (next[job.id] && (job.state === next[job.id] || ['CLOSED', 'CANCELLED'].includes(job.state))) delete next[job.id];
        }
        return next;
      });
      setRoutes(state.routes ?? {});
      setProviderLabels(
        Object.fromEntries(
          ((providers as { providers?: { provider: string; label: string }[] } | null)?.providers ?? []).map(
            (item) => [item.provider, item.label]
          )
        )
      );
      // V2-06 follow-through: the rows are the same authoritative surface the chat's Work panel
      // reads, so every job here can offer its one action with the id that action needs.
      const conversations = Array.from(
        new Set((state.jobs ?? []).map((job) => job.conversation).filter((id): id is string => Boolean(id)))
      ).slice(0, 4);
      const rowLists = await Promise.all(conversations.map((cid) => kelWorkRows(cid).catch((): KelWorkRow[] => [])));
      const merged: Record<string, KelWorkRow> = {};
      for (const list of rowLists) for (const row of list) merged[row.job_id] = row;
      setRowActions(merged);
      setError(null);
    } catch (err) {
      setJobs([]);
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
    return () => {
      followUps.current.forEach((timer) => window.clearTimeout(timer));
    };
  }, [load]);

  /** Re-read a couple of times after a control so the engine's settled state shows without a reload. */
  const settle = useCallback(() => {
    followUps.current.forEach((timer) => window.clearTimeout(timer));
    followUps.current = [1500, 4000].map((ms, index, all) =>
      window.setTimeout(() => {
        void load().then(() => {
          if (index === all.length - 1) setPending({});
        });
      }, ms)
    );
  }, [load]);

  const act = useCallback(
    async (failLabel: string, fn: () => Promise<unknown>, success?: string) => {
      setBusy(true);
      setNote(null);
      try {
        await fn();
        if (success) setNote(success);
        await load();
        settle();
      } catch (err) {
        setNote(`${failLabel} didn't go through. ${failureSentence(err, 'Kel did not answer — try again.')}`);
      } finally {
        setBusy(false);
      }
    },
    [load, settle]
  );

  const control = useCallback(
    async (jobId: string, action: 'pause' | 'resume' | 'cancel') => {
      const { state, note: sentence } = OPTIMISTIC[action];
      const label = action === 'pause' ? 'Pause' : action === 'resume' ? 'Resume' : 'Stop';
      await act(label, async () => {
        await kelControl(jobId, action);
        setPending((current) => ({ ...current, [jobId]: state }));
        setConfirmStop(false);
      }, sentence);
    },
    [act]
  );

  const select = useCallback(
    (jobId: string) => {
      setSelected(jobId);
      setConfirmStop(false);
      setArtifact(null);
      setRecipeDraft(null);
      setNote(null);
      const next = new URLSearchParams(params);
      next.set('job', jobId);
      setParams(next, { replace: true });
    },
    [params, setParams]
  );

  const actDirect = useCallback(
    async (jobId: string, direct: NonNullable<KelWorkRow['direct']>) => {
      if (direct.action === 'stop') {
        // Stopping is confirmed, like the in-chat card's Stop.
        select(jobId);
        setConfirmStop(true);
        return;
      }
      await act(DIRECT_LABEL[direct.action] ?? 'That step', async () => {
        const conversation = rowActions[jobId]?.related?.conversation ?? 'main';
        if (direct.action === 'answer') {
          const state = direct.id ? null : await kelState(conversation);
          const approvalId = direct.id ?? state?.approvals?.find(
            (approval) => approval.job_id === jobId && approval.status === 'PENDING'
          )?.id;
          if (typeof approvalId !== 'string') throw new Error('The permission request is no longer available.');
          await kelApproval(approvalId, true, conversation);
        } else if (direct.action === 'resume' && direct.route === '/api/send') {
          await kelSend(conversation, 'continue');
        } else if (direct.action === 'resume') {
          await kelControl(jobId, 'resume');
        } else if (direct.action === 'retry') {
          if (!direct.id) throw new Error('The saved request is no longer available.');
          await kelRetry(direct.id);
        } else {
          throw new Error('This action is no longer available.');
        }
      }, direct.action === 'resume' ? OPTIMISTIC.resume.note : direct.action === 'retry' ? 'Kel is trying this again.' : 'Kel is continuing.');
    },
    [act, rowActions, select]
  );

  const ordered = useMemo(
    () => (jobs ?? []).map((job) => (pending[job.id] ? { ...job, state: pending[job.id] } : job)).toSorted(attentionOrder),
    [jobs, pending]
  );
  const activeJob = selectedWorkJob(ordered, selected);
  const steps = activeJob
    ? (activeJob.contract?.milestones ?? []).map((spec) => ({ spec, runtime: activeJob.milestones?.[spec.id] }))
    : [];
  const checked = steps.filter((step) => step.runtime?.state === 'ACCEPTED');
  const activeView = activeJob ? workWords(activeJob) : null;
  const route = activeJob ? routeSentence(routes[activeJob.id], providerLabels) : null;

  const openStep = (stepId: string, objective: string): void =>
    void act('Opening the result', async () => {
      if (!activeJob) return;
      const text = await kelArtifact(activeJob.id, stepId);
      setArtifact({ step: objective, text: typeof text === 'string' ? text : JSON.stringify(text, null, 2) });
    });

  return (
    <div className="kel-scope" data-density={(jobs?.length ?? 0) > 10 ? 'compact' : 'comfortable'}>
      <a className="kel-skip" href="#kel-work-main">
        Skip to main content
      </a>
      <main className="kel-page" id="kel-work-main" tabIndex={-1}>
        <div className="kel-page__head">
          <div>
            <ShellWorkspaceLink /><h1 className="kel-h1">Work</h1>
          </div>
        </div>

        {error && <KelFailureCard error={error} onRetry={() => void load()} />}
        {!error && jobs === null && <KelLoading rows={4} />}

        {!error && jobs !== null && jobs.length === 0 && (
          <KelCard title="Jobs">
            <KelEmpty
              title="No work yet."
              why="When you ask Kel for something real, it shows up here with its progress and the one next step."
            />
          </KelCard>
        )}

        {!error && jobs !== null && jobs.length > 0 && (
          <KelCard title="Jobs">
            <ul className="kel-work-rows" aria-label="Jobs">
              {ordered.map((job) => {
                const direct = rowActions[job.id]?.direct;
                const reason = waitReason(job);
                const step = job.state === 'RUNNING' || job.state === 'VERIFYING' ? currentWorkStep(job) : null;
                const isActive = activeJob?.id === job.id;
                return (
                  <li
                    key={job.id}
                    className={`kel-work-row${isActive && requested === job.id ? ' kel-work-focus' : ''}`}
                    data-job-id={job.id}
                  >
                    <div className="kel-work-row__main">
                      <button
                        type="button"
                        className="kel-work-row__title kel-work-job-select"
                        aria-pressed={isActive}
                        title={job.contract?.request ?? undefined}
                        onClick={() => select(job.id)}
                      >
                        {requestTitle(job)}
                      </button>
                      <span className="kel-meta kel-work-row__detail">
                        {[step && step !== '—' ? step : null, reason].filter(Boolean).join(' · ') || workWords(job).sentence}
                      </span>
                    </div>
                    <div className="kel-work-row__side">
                      <KelWorkChip job={job} />
                      <span className="kel-meta">{formatWhen(job.updated ?? null)}</span>
                      {direct && job.state !== 'CANCELLED' && job.state !== 'CANCELLING' ? (
                        <KelButton
                          variant="secondary"
                          disabled={busy}
                          ariaLabel={`${DIRECT_LABEL[direct.action] ?? 'Continue'}: ${requestTitle(job)}`}
                          onClick={() => void actDirect(job.id, direct)}
                        >
                          {DIRECT_LABEL[direct.action] ?? 'Continue'}
                        </KelButton>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          </KelCard>
        )}

        {activeJob && activeView && (
          <KelCard
            className="kel-work-verification"
            title={requestTitle(activeJob)}
            chip={<KelWorkChip job={activeJob} />}
          >
            <p className="kel-sub" data-testid="work-selected-summary">
              {steps.length > 0
                ? `${activeView.sentence} ${checked.length} of ${steps.length} steps checked.`
                : activeView.sentence}
            </p>
            <div className="kel-work-actions">
              {(activeJob.state === 'RUNNING' || activeJob.state === 'QUEUED' || activeJob.state === 'READY') && (
                <KelButton variant="secondary" disabled={busy || confirmStop} onClick={() => void control(activeJob.id, 'pause')}>
                  Pause
                </KelButton>
              )}
              {activeJob.state === 'PAUSED' && (
                <KelButton variant="secondary" disabled={busy || confirmStop} onClick={() => void control(activeJob.id, 'resume')}>
                  Resume
                </KelButton>
              )}
              {!['CLOSED', 'CANCELLED', 'CANCELLING', 'CANCEL_REQUESTED'].includes(activeJob.state) && !confirmStop && (
                <KelButton variant="secondary" disabled={busy} onClick={() => setConfirmStop(true)}>
                  Stop
                </KelButton>
              )}
              <KelButton
                variant="quiet"
                disabled={busy}
                onClick={() =>
                  void act('Saving as a recipe', async () => {
                    setRecipeDraft(await kelRecipePropose(activeJob.id));
                  })
                }
              >
                Save as a recipe
              </KelButton>
            </div>
            {confirmStop && (
              <div className="kel-work-confirm" role="group" aria-label="Confirm stop" data-testid="work-stop-confirm">
                <span>Stop this work? Anything already checked is kept.</span>
                <KelButton variant="quiet" disabled={busy} onClick={() => setConfirmStop(false)}>
                  Keep going
                </KelButton>
                <KelButton variant="danger" disabled={busy} onClick={() => void control(activeJob.id, 'cancel')}>
                  Stop it
                </KelButton>
              </div>
            )}
            {note && (
              <p className="kel-meta" role="status">
                {note}
              </p>
            )}
            {recipeDraft && (
              <KelSection title="Save as a recipe">
                <p className="kel-sub">
                  {`A ready-made task from this job, with ${recipeDraft.preview.milestones} steps. It is saved only when you confirm.`}
                </p>
                <p className="kel-meta">{recipeDraft.preview.steps.join(' · ')}</p>
                <div className="kel-row">
                  <KelButton
                    variant="secondary"
                    disabled={busy}
                    onClick={() =>
                      void act('Saving the recipe', async () => {
                        await kelRecipeSave(recipeDraft.recipe);
                        setRecipeDraft(null);
                      }, 'Saved as a recipe.')
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
            <details className="kel-work-details" data-testid="work-details">
              <summary>Details</summary>
              {steps.length === 0 ? (
                <p className="kel-meta">No step has started yet. Nothing counts as checked until its checks pass.</p>
              ) : (
                <ol className="kel-work-steps" aria-label="Steps">
                  {steps.map(({ spec, runtime }) => (
                    <li key={spec.id}>
                      <span className="kel-strong">{spec.objective ?? 'Step'}</span>
                      <span className="kel-meta">
                        {`${stepStateText(runtime?.state)}${(runtime?.attempts ?? 0) > 1 ? ' · tried again' : ''}`}
                      </span>
                      {runtime?.state === 'ACCEPTED' ? (
                        <KelButton variant="quiet" disabled={busy} onClick={() => openStep(spec.id, spec.objective ?? 'Step')}>
                          View result
                        </KelButton>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
              {route && <p className="kel-meta">{route}</p>}
              <KelMeter used={activeJob.spent ?? 0} total={activeJob.budget ?? 8} />
              {artifact && (
                <KelSection title={`Result — ${artifact.step}`}>
                  <pre className="kel-code">{artifact.text.slice(0, 4000)}</pre>
                </KelSection>
              )}
            </details>
          </KelCard>
        )}
      </main>
    </div>
  );
};

export default WorkCenter;
