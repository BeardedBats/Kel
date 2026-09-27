import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Spin } from '@arco-design/web-react';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import ShellSourceCardHeader from '@renderer/components/kel/ShellSourceCardHeader';
import { KelEmpty } from '@renderer/components/kel/KelPrimitives';
import { useAllCronJobs } from '@renderer/pages/cron/useCronJobs';
import { formatSchedule, formatNextRun } from '@renderer/pages/cron/cronUtils';
import CreateTaskDialog from './CreateTaskDialog';

/**
 * Scheduled tasks: one row per task; a row opens that task's page (`/scheduled/:id`), which owns
 * its details, history, run-now, edit and delete (WK-8).
 */
export default function ScheduledTasksPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { jobs, loading } = useAllCronJobs();
  const [createOpen, setCreateOpen] = useState(false);
  return <div className='kel-scope'><main className='kel-page kel-shell-scheduled'>
    <div className='kel-page__head'>
      <div><ShellWorkspaceLink /><h1 className='kel-h1'>Scheduled tasks</h1></div>
      <span className='kel-grow' /><button type='button' className='kel-btn kel-btn--primary kel-shell-task-create-desktop' onClick={() => setCreateOpen(true)}>New task</button>
    </div>
    <section className='kel-card kel-shell-task-list' aria-label='Scheduled tasks'>
      <ShellSourceCardHeader title='Scheduled tasks' description={`${jobs.length} ${jobs.length === 1 ? 'task' : 'tasks'}`} />
      <button type='button' className='kel-shell-task-create-mobile' aria-label='New task' onClick={() => setCreateOpen(true)}>+</button>
      {loading ? <Spin /> : jobs.length === 0 ? (
        <KelEmpty
          title='No scheduled tasks yet.'
          why='A scheduled task asks Kel to do the same thing on a schedule — for example, “every weekday at 9, summarize my inbox”. Each run shows up here with its result.'
          actionLabel='New task'
          onAction={() => setCreateOpen(true)}
        />
      ) : <div>
        {jobs.map(job => <button key={job.id} type='button' className='kel-shell-task-row' data-testid={`scheduled-row-${job.id}`} onClick={() => navigate(`/scheduled/${encodeURIComponent(job.id)}`)}>
          <span>{job.name}</span><span className='kel-meta'>{formatSchedule(job, t)}{job.enabled && job.state.next_run_at_ms ? ` · next ${formatNextRun(job.state.next_run_at_ms, i18n.language)}` : !job.enabled ? ' · paused' : ''}</span>
          <span className={`kel-chip ${job.enabled ? 'kel-chip--ok' : 'kel-chip--wait'}`}>{job.enabled ? 'Active' : 'Paused'}</span>
        </button>)}
      </div>}
    </section>
    <CreateTaskDialog visible={createOpen} onClose={() => setCreateOpen(false)} />
  </main></div>;
}
