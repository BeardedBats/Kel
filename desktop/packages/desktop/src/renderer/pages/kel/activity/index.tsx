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

function Row({ title, detail }: { title: string; detail: string }) {
  return (
    <div className='kel-attention__row'>
      <div className='kel-attention__text'>
        <strong>{title}</strong>
        <span className='kel-meta'>{detail}</span>
      </div>
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
  const waiting = continuation.slice(0, 3);

  return (
    <div className='kel-page kel-shell-activity'>
      <div className='kel-page__head'>
        <div><ShellWorkspaceLink /><h1 className='kel-h1'>Activity</h1></div>
        <p className='kel-sub'>
          {providers.length === 1 ? '1 provider connected' : `${providers.length} providers connected`}
        </p>
      </div>

      <KelCard
        title='Happening now'
        chip={<span className='kel-meta'>{active.length === 1 ? 'one piece of work' : `${active.length} pieces of work`}</span>}
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
            />
          ))
        )}
      </KelCard>

      <KelCard
        title='Waiting on you'
        chip={<span className='kel-meta'>{waiting.length === 0 ? 'nothing waiting' : `${waiting.length} waiting`}</span>}
      >
        {waiting.length === 0 ? (
          <KelEmpty
            title='Nothing needs you right now.'
            why='Approvals and offers to continue land here when they genuinely need a person.'
          />
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
        chip={<span className='kel-meta'>{finished.length === 0 ? 'none yet' : `last ${finished.length}`}</span>}
      >
        {finished.length === 0 ? (
          <KelEmpty title='Nothing has finished yet.' why='Completed work shows up here with its outcome.' />
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
