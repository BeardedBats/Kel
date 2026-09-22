import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Spin, Switch } from '@arco-design/web-react';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import ShellSourceCardHeader from '@renderer/components/kel/ShellSourceCardHeader';
import { useAllCronJobs, useCronJobConversations } from '@renderer/pages/cron/useCronJobs';
import { formatSchedule, formatNextRun } from '@renderer/pages/cron/cronUtils';
import CreateTaskDialog from './CreateTaskDialog';

/** The list and selected task share the existing scheduler store. */
export default function ScheduledTasksPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { jobs, loading } = useAllCronJobs();
  const [selectedId, setSelectedId] = useState<string>();
  const [createOpen, setCreateOpen] = useState(false);
  const selected = jobs.find(job => job.id === selectedId) ?? jobs[0];
  const { conversations } = useCronJobConversations(selected?.id);
  const conversationId = conversations[0]?.id || selected?.metadata.conversation_id;
  return <div className='kel-scope'><main className='kel-page kel-shell-scheduled'>
    <div className='kel-page__head'>
      <div><ShellWorkspaceLink /><h1 className='kel-h1'>Scheduled tasks</h1></div>
      <span className='kel-grow' /><button type='button' className='kel-btn' onClick={() => setCreateOpen(true)}>New task</button>
    </div>
    <section className='kel-card' aria-label='Scheduled tasks'>
      <ShellSourceCardHeader title='Scheduled tasks' description={`${jobs.length} ${jobs.length === 1 ? 'task' : 'tasks'}`} />
      {loading ? <Spin /> : jobs.length === 0 ? <p className='kel-meta'>No scheduled tasks</p> : <div>
        {jobs.map(job => <button key={job.id} type='button' className='kel-shell-task-row' aria-pressed={selected?.id === job.id} onClick={() => setSelectedId(job.id)}>
          <span>{job.name}</span><span className='kel-meta'>{formatSchedule(job, t)}{job.enabled && job.state.next_run_at_ms ? ` · next ${formatNextRun(job.state.next_run_at_ms, i18n.language)}` : !job.enabled ? ' · paused' : ''}</span>
          <span className={`kel-chip ${job.enabled ? 'kel-chip--ok' : 'kel-chip--wait'}`}>{job.enabled ? 'Active' : 'Paused'}</span>
        </button>)}
      </div>}
    </section>
    {selected && <section className='kel-card kel-shell-task-detail' aria-label={selected.name}>
      <ShellSourceCardHeader title={selected.name} description={formatSchedule(selected, t)} />
      <div className='kel-shell-task-field'><span>Instructions</span><p>{selected.target.payload.text}</p></div>
      <div className='kel-shell-task-field'><span>Assistant</span><span>Kel</span></div>
      <div className='kel-shell-task-field'><span>Model</span><span>{selected.metadata.agent_config?.model_id || selected.metadata.agent_config?.model?.model || 'Automatic'}</span></div>
      <div className='kel-shell-task-field'><span>Execution mode</span><span>{selected.target.execution_mode === 'new_conversation' ? 'New conversation' : 'Existing conversation'}</span></div>
      <div className='kel-shell-task-field'><span>Queue</span><Switch checked={selected.state.queue_enabled} disabled aria-label='Queue' /></div>
      <div className='kel-shell-preference-row'><div><div>History</div><p className='kel-meta'>{selected.state.last_run_at_ms ? `Last run ${formatNextRun(selected.state.last_run_at_ms, i18n.language)} · ${selected.state.last_status === 'ok' ? 'succeeded' : selected.state.last_status || 'unknown'}` : 'No runs yet'}</p></div>
        <button type='button' className='kel-btn' disabled={!conversationId} onClick={() => conversationId && navigate(`/conversation/${conversationId}`)}>Go to conversation</button>
      </div>
    </section>}
    <CreateTaskDialog visible={createOpen} onClose={() => setCreateOpen(false)} />
  </main></div>;
}
