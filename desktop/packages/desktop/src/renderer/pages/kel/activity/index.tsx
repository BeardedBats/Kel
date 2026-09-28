import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import { officeList, type OfficeItem } from '@renderer/components/kel/workCards/officeApi';
/**
 * Kel D14 — Activity: an optional, high-level view of what Kel is doing, built entirely from state
 * other surfaces already expose. Permission grants, internal counters, worker identifiers, routing
 * packets, and database rows never appear here — those stay behind developer surfaces.
 *
 * One job, one story (WK-4): every job sits in exactly one section, chosen by the shared state
 * words (workLanguage.ts) — the same words Home and the in-chat card use. `?job=<id>` (from a work
 * card's "View in Activity", Needs you, the palette or a scheduled run) highlights that job and
 * scrolls it into view.
 *
 * D-70 item 5: the Work page is retired — the work cards at the top of the chat replace it. What the
 * cards do not offer keeps a minimal home here, on the one list that holds every job (including work
 * from before the cards, which never becomes a card): Pause and Resume, and "Save as a recipe" for
 * finished work, and the plain route sentence for running work (D12: which model it runs on and
 * what Kel falls back to). Stop stays on the work card and the in-chat card, where it is confirmed.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { KelButton, KelCard, KelEmpty } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { KelActivityLoading } from '@renderer/components/kel/KelDesktopPendingStates';
import { failureSentence } from '@renderer/components/kel/engineFailure';
import { passedItsChecks, workLabelFor } from '@renderer/components/kel/jobLabels';
import { routeSentence, workWords } from '@renderer/components/kel/workLanguage';
import { jobChatAction, resolveAttentionRoute } from '@renderer/components/kel/needsAttention';
import {
  KEL_ALL_CONVERSATIONS,
  kelControl,
  kelProviders,
  kelRecipePropose,
  kelRecipeSave,
  kelState,
  type KelJobRoute,
  type KelWorkJob,
} from '@renderer/components/kel/kelApi';
import { resolveConversationRoute } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';
import '@renderer/styles/kel-work.css';
import { useProjects } from '@renderer/components/kel/activeProject';

const FINISHED_CAP = 5;

const byUpdatedDesc = (a: KelWorkJob, b: KelWorkJob): number => (b.updated ?? 0) - (a.updated ?? 0);

/** A job's own project, for the recipe it can become (its chat names it; the contract otherwise). */
const jobScope = (job: KelWorkJob) =>
  job.conversation ? { conversation: job.conversation } : { project: job.contract?.project_id || 'default' };

const PAUSABLE = new Set(['RUNNING', 'QUEUED', 'READY']);

/** How pause/resume change a job right away, so the list never needs a reload to show it. */
const OPTIMISTIC: Record<'pause' | 'resume', { state: string; note: string }> = {
  pause: { state: 'PAUSED', note: 'Kel is pausing this.' },
  resume: { state: 'QUEUED', note: 'Kel is picking this back up.' },
};

type RecipeDraft = {
  jobId: string;
  recipe: Record<string, unknown>;
  preview: { steps: string[]; kind: string; milestones: number };
};

/** FN-13: a work card that is waiting on Nick — scoping questions or a needs-you card. */
export const needsNick = (item: OfficeItem): boolean =>
  Boolean(item && !item.finished && (item.needs_you || item.state === 'scoping' || item.state === 'needs_you'));

const askSentence = (item: OfficeItem): string =>
  item.state === 'scoping'
    ? `Kel has ${item.questions && item.questions > 1 ? `${item.questions} questions` : 'a question'} before it starts.`
    : item.status_line || 'Kel needs your answer to go on.';

function Row({
  job,
  all,
  focused,
  action,
}: {
  job: KelWorkJob;
  all: KelWorkJob[];
  focused: boolean;
  action?: React.ReactNode;
}) {
  const view = workWords(job);
  const running = job.state === 'RUNNING' || job.state === 'VERIFYING';
  const step =
    job.contract?.milestones?.find((item) => item.id && job.milestones?.[item.id]?.state === 'RUNNING')?.objective;
  return (
    <div
      className={`kel-attention__row kel-shell-activity__item${focused ? ' kel-work-focus' : ''}`}
      data-job-id={job.id}
      data-section={view.section}
      aria-current={focused ? 'true' : undefined}
    >
      {running && <span className='kel-shell-activity__dot' aria-hidden='true' />}
      <div className='kel-attention__text'>
        <strong>{workLabelFor(job.id, all)}</strong>
        <span className='kel-meta kel-shell-activity__desktop-detail' data-testid='activity-state'>
          {`${view.label} — ${view.sentence}`}
        </span>
        <span className='kel-meta kel-shell-activity__mobile-detail'>{step || view.label}</span>
      </div>
      {running && <span className='kel-shell-activity__state'>{view.label}</span>}
      {action}
    </div>
  );
}

const KelActivityPage: React.FC = () => {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const focusId = params.get('job');
  const [jobs, setJobs] = useState<KelWorkJob[] | null>(null);
  const [routes, setRoutes] = useState<Record<string, KelJobRoute>>({});
  const [providerLabels, setProviderLabels] = useState<Record<string, string>>({});
  // FN-13: what the work cards say needs Nick (scoping questions, a needs-you card) — "All clear"
  // only when nothing does.
  const [asks, setAsks] = useState<OfficeItem[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [draft, setDraft] = useState<RecipeDraft | null>(null);
  // What a control just asked for, shown until the engine reports it (no reload, no flicker back).
  const [pending, setPending] = useState<Record<string, string>>({});
  const followUps = useRef<number[]>([]);
  const scrolledTo = useRef<string | null>(null);
  // D-54: Activity shows the active project's jobs ('*' = every project).
  const { active, loaded } = useProjects();

  const load = useCallback(async () => {
    if (!loaded) return;
    try {
      const [state, providers, office] = await Promise.all([
        kelState(KEL_ALL_CONVERSATIONS, active),
        // D19: the route sentence names providers the way a person knows them.
        Promise.resolve()
          .then(() => kelProviders.list())
          .catch((): null => null),
        Promise.resolve()
          .then(() => officeList(active || '*'))
          .catch((): null => null),
      ]);
      setAsks((office?.items ?? []).filter(needsNick));
      setJobs(state.jobs ?? []);
      setRoutes(state.routes ?? {});
      setProviderLabels(
        Object.fromEntries((providers?.providers ?? []).map((item) => [item.provider, item.label]))
      );
      setPending((current) => {
        const next = { ...current };
        for (const job of state.jobs ?? []) {
          if (next[job.id] && (job.state === next[job.id] || ['CLOSED', 'CANCELLED'].includes(job.state))) delete next[job.id];
        }
        return next;
      });
      setError(null);
    } catch (err) {
      setJobs([]);
      setError(err);
    }
  }, [active, loaded]);

  useEffect(() => {
    void load();
    return () => {
      followUps.current.forEach((timer) => window.clearTimeout(timer));
    };
  }, [load]);

  // Bring the job a work card pointed at into view once it has rendered.
  useEffect(() => {
    if (!focusId || !jobs || scrolledTo.current === focusId) return;
    const row = Array.from(document.querySelectorAll<HTMLElement>('[data-job-id]')).find(
      (element) => element.dataset.jobId === focusId
    );
    if (!row) return;
    scrolledTo.current = focusId;
    row.scrollIntoView?.({ block: 'center' });
  }, [focusId, jobs]);

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
    async (jobId: string, failLabel: string, fn: () => Promise<string | null>) => {
      setBusy(jobId);
      setNotes((current) => ({ ...current, [jobId]: '' }));
      try {
        const success = await fn();
        if (success) setNotes((current) => ({ ...current, [jobId]: success }));
      } catch (err) {
        setNotes((current) => ({
          ...current,
          [jobId]: `${failLabel} didn't go through, so nothing changed. ${failureSentence(err, 'Kel did not answer — try again.')}`,
        }));
      } finally {
        setBusy(null);
      }
    },
    []
  );

  const control = (job: KelWorkJob, action: 'pause' | 'resume'): void =>
    void act(job.id, action === 'pause' ? 'Pause' : 'Resume', async () => {
      await kelControl(job.id, action);
      setPending((current) => ({ ...current, [job.id]: OPTIMISTIC[action].state }));
      await load();
      settle();
      return OPTIMISTIC[action].note;
    });

  const proposeRecipe = (job: KelWorkJob): void =>
    void act(job.id, 'Saving as a recipe', async () => {
      const proposal = await kelRecipePropose(job.id, jobScope(job));
      setDraft({ jobId: job.id, recipe: proposal.recipe, preview: proposal.preview });
      return null;
    });

  const saveRecipe = (job: KelWorkJob, current: RecipeDraft): void =>
    void act(job.id, 'Saving the recipe', async () => {
      await kelRecipeSave(current.recipe, jobScope(job));
      setDraft(null);
      return 'Saved as a recipe. It is in Recipes.';
    });

  if (error) {
    return (
      <div className='kel-page kel-shell-activity'>
        <KelFailureCard error={error} onRetry={() => void load()} />
      </div>
    );
  }

  if (jobs === null) return <KelActivityLoading />;

  const all = jobs
    .map((job) => (pending[job.id] ? { ...job, state: pending[job.id] } : job))
    .toSorted(byUpdatedDesc);
  const now = all.filter((job) => workWords(job).section === 'now');
  const waiting = all.filter((job) => workWords(job).section === 'waiting');
  const finishedAll = all.filter((job) => workWords(job).section === 'finished');
  // The focused job is always shown, even when it is older than the recent few.
  const finished = finishedAll.filter((job, index) => index < FINISHED_CAP || job.id === focusId);

  const openChat = (job: KelWorkJob) => navigate(resolveAttentionRoute(jobChatAction(job), resolveConversationRoute));
  // FN-13: a card that needs Nick and is not already a waiting job row (scoping has no job yet).
  const waitingIds = new Set(waiting.map((job) => job.id));
  const openAsks = asks.filter((item) => !waitingIds.has(item.job_id));
  const openAsk = (item: OfficeItem) => {
    const open = (window as unknown as { kelAPI?: { openEngineConversation?: (cid: string) => Promise<string | null> } }).kelAPI?.openEngineConversation;
    if (!item.conversation_id || !open) {
      navigate('/guid');
      return;
    }
    void open(item.conversation_id)
      .then((donor) => navigate(donor ? `/conversation/${donor}` : '/guid'))
      .catch(() => navigate('/guid'));
  };
  const title = (job: KelWorkJob) => workLabelFor(job.id, all);

  /** A job's note and recipe draft, under its row (never a second row for the same job). */
  const extra = (job: KelWorkJob) => {
    const note = notes[job.id];
    const ownDraft = draft?.jobId === job.id ? draft : null;
    // Only when the engine actually recorded a decision for work that is still going.
    const route = workWords(job).section === 'now' ? routeSentence(routes[job.id], providerLabels) : null;
    if (!note && !ownDraft && !route) return null;
    return (
      <div className='kel-activity-job-extra' data-testid={`activity-extra-${job.id}`}>
        {route && <p className='kel-meta kel-activity-route'>{route}</p>}
        {note && (
          <p className='kel-meta' role='status'>
            {note}
          </p>
        )}
        {ownDraft && (
          <div className='kel-activity-recipe-draft' role='group' aria-label={`Save ${title(job)} as a recipe`}>
            <p className='kel-sub'>
              {`A ready-made task from this work, with ${ownDraft.preview.milestones} ${ownDraft.preview.milestones === 1 ? 'step' : 'steps'}. It is saved only when you confirm.`}
            </p>
            {ownDraft.preview.steps.length > 0 && <p className='kel-meta'>{ownDraft.preview.steps.join(' · ')}</p>}
            <div className='kel-row'>
              <KelButton variant='secondary' disabled={busy === job.id} onClick={() => saveRecipe(job, ownDraft)}>
                Save recipe
              </KelButton>
              <KelButton variant='quiet' disabled={busy === job.id} onClick={() => setDraft(null)}>
                Cancel
              </KelButton>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className='kel-page kel-shell-activity'>
      <div className='kel-page__head'>
        <div><ShellWorkspaceLink /><h1 className='kel-h1'>Activity</h1></div>
      </div>

      <KelCard title='Happening now'>
        {now.length === 0 ? (
          <KelEmpty
            title='Nothing is running right now.'
            why='When you ask Kel for something real, its progress shows up here.'
          />
        ) : (
          now.map((job) => (
            <React.Fragment key={job.id}>
              <Row
                job={job}
                all={all}
                focused={job.id === focusId}
                action={
                  PAUSABLE.has(job.state) ? (
                    <KelButton
                      variant='quiet'
                      disabled={busy === job.id}
                      ariaLabel={`Pause ${title(job)}`}
                      onClick={() => control(job, 'pause')}
                    >
                      Pause
                    </KelButton>
                  ) : undefined
                }
              />
              {extra(job)}
            </React.Fragment>
          ))
        )}
      </KelCard>

      <KelCard title='Waiting on you'>
        {openAsks.map((item) => (
          <div key={item.scoping_id || item.job_id} className='kel-attention__row kel-shell-activity__item'
            data-section='waiting' data-testid='activity-ask'>
            <div className='kel-attention__text'>
              <strong>{item.title}</strong>
              <span className='kel-meta' data-testid='activity-state'>{askSentence(item)}</span>
            </div>
            <KelButton variant='secondary' onClick={() => openAsk(item)} ariaLabel={`Open the chat for ${item.title}`}>
              Open the chat
            </KelButton>
          </div>
        ))}
        {waiting.length === 0 && openAsks.length === 0 ? (
          <p className='kel-meta kel-shell-activity-clear'>All clear.</p>
        ) : (
          waiting.map((job) => (
            <React.Fragment key={job.id}>
              <Row
                job={job}
                all={all}
                focused={job.id === focusId}
                action={
                  <>
                    {job.state === 'PAUSED' && (
                      <KelButton
                        variant='secondary'
                        disabled={busy === job.id}
                        ariaLabel={`Resume ${title(job)}`}
                        onClick={() => control(job, 'resume')}
                      >
                        Resume
                      </KelButton>
                    )}
                    <KelButton variant='secondary' onClick={() => openChat(job)} ariaLabel={`Open the chat for ${title(job)}`}>
                      Open the chat
                    </KelButton>
                  </>
                }
              />
              {extra(job)}
            </React.Fragment>
          ))
        )}
      </KelCard>

      <KelCard title='Recently finished'>
        {finished.length === 0 ? (
          <p className='kel-meta kel-shell-activity-clear'>Nothing has finished yet.</p>
        ) : (
          finished.map((job) => (
            <React.Fragment key={job.id}>
              <Row
                job={job}
                all={all}
                focused={job.id === focusId}
                action={
                  // D-73.5 / VIS-14: only work that finished and passed its checks becomes a recipe.
                  passedItsChecks(job) && draft?.jobId !== job.id ? (
                    <KelButton
                      variant='quiet'
                      disabled={busy === job.id}
                      ariaLabel={`Save ${title(job)} as a recipe`}
                      onClick={() => proposeRecipe(job)}
                    >
                      Save as a recipe
                    </KelButton>
                  ) : undefined
                }
              />
              {extra(job)}
            </React.Fragment>
          ))
        )}
      </KelCard>
    </div>
  );
};

export default KelActivityPage;
