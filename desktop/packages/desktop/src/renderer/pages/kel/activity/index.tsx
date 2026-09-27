import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel D14 — Activity: an optional, high-level view of what Kel is doing, built entirely from state
 * other surfaces already expose. Permission grants, internal counters, worker identifiers, routing
 * packets, and database rows never appear here — those stay behind developer surfaces.
 *
 * One job, one story (WK-4): every job sits in exactly one section, chosen by the shared state
 * words (workLanguage.ts) — the same words Work, Home and the in-chat card use. `?job=<id>` (from
 * a work card's "View in Activity") highlights that job and scrolls it into view.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { KelButton, KelCard, KelEmpty } from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { KelActivityLoading } from '@renderer/components/kel/KelDesktopPendingStates';
import { workLabelFor } from '@renderer/components/kel/jobLabels';
import { workWords } from '@renderer/components/kel/workLanguage';
import { jobChatAction, resolveAttentionRoute } from '@renderer/components/kel/needsAttention';
import { KEL_ALL_CONVERSATIONS, kelState, type KelWorkJob } from '@renderer/components/kel/kelApi';
import { resolveConversationRoute } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';
import '@renderer/styles/kel-work.css';

const FINISHED_CAP = 5;

const byUpdatedDesc = (a: KelWorkJob, b: KelWorkJob): number => (b.updated ?? 0) - (a.updated ?? 0);

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
  const [error, setError] = useState<unknown>(null);
  const scrolledTo = useRef<string | null>(null);

  const load = useCallback(async () => {
    try {
      const state = await kelState(KEL_ALL_CONVERSATIONS);
      setJobs(state.jobs ?? []);
      setError(null);
    } catch (err) {
      setJobs([]);
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
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

  if (error) {
    return (
      <div className='kel-page kel-shell-activity'>
        <KelFailureCard error={error} onRetry={() => void load()} />
      </div>
    );
  }

  if (jobs === null) return <KelActivityLoading />;

  const all = jobs.toSorted(byUpdatedDesc);
  const now = all.filter((job) => workWords(job).section === 'now');
  const waiting = all.filter((job) => workWords(job).section === 'waiting');
  const finishedAll = all.filter((job) => workWords(job).section === 'finished');
  // The focused job is always shown, even when it is older than the recent few.
  const finished = finishedAll.filter((job, index) => index < FINISHED_CAP || job.id === focusId);

  const openChat = (job: KelWorkJob) => navigate(resolveAttentionRoute(jobChatAction(job), resolveConversationRoute));

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
          now.map((job) => <Row key={job.id} job={job} all={all} focused={job.id === focusId} />)
        )}
      </KelCard>

      <KelCard title='Waiting on you'>
        {waiting.length === 0 ? (
          <p className='kel-meta kel-shell-activity-clear'>All clear.</p>
        ) : (
          waiting.map((job) => (
            <Row
              key={job.id}
              job={job}
              all={all}
              focused={job.id === focusId}
              action={
                <KelButton variant='secondary' onClick={() => openChat(job)} ariaLabel={`Open the chat for ${workLabelFor(job.id, all)}`}>
                  Open the chat
                </KelButton>
              }
            />
          ))
        )}
      </KelCard>

      <KelCard title='Recently finished'>
        {finished.length === 0 ? (
          <p className='kel-meta kel-shell-activity-clear'>Nothing has finished yet.</p>
        ) : (
          finished.map((job) => <Row key={job.id} job={job} all={all} focused={job.id === focusId} />)
        )}
      </KelCard>
    </div>
  );
};

export default KelActivityPage;
