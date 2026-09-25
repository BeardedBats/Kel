import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
/**
 * Kel D14 — Activity: an optional, high-level view of what Kel is doing, built entirely from state
 * other surfaces already expose. Permission grants, internal counters, worker identifiers, routing
 * packets, and database rows never appear here — those stay behind developer surfaces (the Team
 * page's developer view).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  KelButton,
  KelCard,
  KelEmpty,
  KelLoading,
  formatWhen,
} from '@renderer/components/kel/KelPrimitives';
import { KelFailureCard } from '@renderer/components/kel/KelFailureCard';
import { workLabelFor } from '@renderer/components/kel/jobLabels';
import { VERDICT_TEXT, jobStateText, routeSentence } from '@renderer/components/kel/workLanguage';
import { kelState, type KelContinuationCandidate, type KelJobRoute, type KelWorkJob } from '@renderer/components/kel/kelApi';

const TERMINAL = new Set(['CLOSED', 'CANCELLED']);

function Row({ title, detail, mobileDetail, state }: { title: string; detail: string; mobileDetail?: string; state?: string }) {
  return (
    <div className='kel-attention__row kel-shell-activity__item'>
      {state === 'RUNNING' && <span className='kel-shell-activity__dot' aria-hidden='true' />}
      <div className='kel-attention__text'>
        <strong>{title}</strong>
        <span className='kel-meta kel-shell-activity__desktop-detail'>{detail}</span>
        <span className='kel-meta kel-shell-activity__mobile-detail'>{mobileDetail || detail}</span>
      </div>
      {state === 'RUNNING' && <span className='kel-shell-activity__state'>Running</span>}
    </div>
  );
}

const KelActivityPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<KelWorkJob[] | null>(null);
  const [routes, setRoutes] = useState<Record<string, KelJobRoute>>({});
  const [continuation, setContinuation] = useState<KelContinuationCandidate[]>([]);
  const [providers, setProviders] = useState<string[]>([]);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const state = await kelState();
      setJobs(state.jobs ?? []);
      setRoutes(state.routes ?? {});
      setContinuation(state.continuation ?? []);
      setProviders(state.providers ?? []);
      setError(null);
    } catch (err) {
      setJobs([]);
      setError(err);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <div className='kel-page kel-shell-activity'>
        <KelFailureCard error={error} onRetry={() => void load()} />
      </div>
    );
  }

  if (jobs === null) return <KelLoading />;

  const all = jobs ?? [];
  const active = all.filter((job) => !TERMINAL.has(job.state));
  const finished = all.filter((job) => job.state === 'CLOSED').slice(0, 5);
  const waiting = continuation.filter((candidate) => {
    const state = candidate.state ?? candidate.job?.state;
    if (state === 'AWAITING_USER' || state === 'PAUSED') return true;
    if (state === 'WAITING_RESOURCE') {
      const job = all.find((item) => item.id === candidate.job_id);
      return !job?.route_block;
    }
    return state === 'CLOSED' && candidate.verdict !== 'VERIFIED';
  }).slice(0, 3);

  return (
    <div className='kel-page kel-shell-activity'>
      <div className='kel-page__head'>
        <div><ShellWorkspaceLink /><h1 className='kel-h1'>Activity</h1></div>
      </div>

      <KelCard
        title='Happening now'
      >
        {active.length === 0 ? (
          <KelEmpty
            title='Nothing is running right now.'
            why='When you ask Kel for something real, its progress shows up here.'
          />
        ) : (
          active.map((job) => (
            <Row
              key={job.id}
              title={workLabelFor(job.id, all)}
              detail={[jobStateText(job.state), routeSentence(routes[job.id])].filter(Boolean).join(' · ')}
              mobileDetail={job.contract?.milestones?.find((item) => item.id && job.milestones?.[item.id]?.state === 'RUNNING')?.objective || job.contract?.milestones?.[0]?.objective || jobStateText(job.state)}
              state={job.state}
            />
          ))
        )}
      </KelCard>

      <KelCard
        title='Waiting on you'
      >
        {waiting.length === 0 ? (
          <p className='kel-meta kel-shell-activity-clear'>All clear.</p>
        ) : (
          waiting.map((candidate, index) => (
            <div className='kel-row' key={`${candidate.job_id ?? 'candidate'}-${index}`}>
              <div className='kel-attention__text'>
                <strong>{candidate.summary || workLabelFor(candidate.job_id ?? '', all)}</strong>
                <span className='kel-meta'>{candidate.state ? jobStateText(candidate.state) : 'ready to continue'}</span>
              </div>
              <span className='kel-grow' />
              <KelButton variant='secondary' onClick={() => navigate('/work')}>
                Open Work
              </KelButton>
            </div>
          ))
        )}
      </KelCard>

      <KelCard
        title='Recently finished'
      >
        {finished.length === 0 ? (
            <p className='kel-meta kel-shell-activity-clear'>All clear.</p>
        ) : (
          finished.map((job) => (
            <Row
              key={job.id}
              title={workLabelFor(job.id, all)}
              detail={job.verdict ? VERDICT_TEXT[job.verdict] ?? jobStateText(job.state) : jobStateText(job.state)}
            />
          ))
        )}
      </KelCard>
    </div>
  );
};

export default KelActivityPage;
