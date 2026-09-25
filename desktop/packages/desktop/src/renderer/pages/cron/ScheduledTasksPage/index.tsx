import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Spin } from '@arco-design/web-react';
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
  const [editOpen, setEditOpen] = useState(false);
  const [mobileDetailsOpen, setMobileDetailsOpen] = useState(false);
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);
  const selected = jobs.find(job => job.id === selectedId) ?? jobs[0];
  const { conversations } = useCronJobConversations(selected?.id);
  const conversationId = conversations[0]?.id || selected?.metadata.conversation_id;
  return <div className='kel-scope'><main className='kel-page kel-shell-scheduled'>
    <div className='kel-page__head'>
      <div><ShellWorkspaceLink /><h1 className='kel-h1'>Scheduled tasks</h1></div>
      <span className='kel-grow' /><button type='button' className='kel-btn kel-shell-task-create-desktop' onClick={() => setCreateOpen(true)}>New task</button>
    </div>
    <section className='kel-card kel-shell-task-list' aria-label='Scheduled tasks'>
      <ShellSourceCardHeader title='Scheduled tasks' description={`${jobs.length} ${jobs.length === 1 ? 'task' : 'tasks'}`} />
      <button type='button' className='kel-shell-task-create-mobile' aria-label='New task' onClick={() => setCreateOpen(true)}>+</button>
      {loading ? <Spin /> : jobs.length === 0 ? <p className='kel-meta'>No scheduled tasks</p> : <div>
        {jobs.map(job => <button key={job.id} type='button' className='kel-shell-task-row' aria-pressed={selected?.id === job.id} onClick={() => { setSelectedId(job.id); setMobileDetailsOpen(false); setMobileHistoryOpen(false); }}>
          <span>{job.name}</span><span className='kel-meta'>{formatSchedule(job, t)}{job.enabled && job.state.next_run_at_ms ? ` · next ${formatNextRun(job.state.next_run_at_ms, i18n.language)}` : !job.enabled ? ' · paused' : ''}</span>
          <span className={`kel-chip ${job.enabled ? 'kel-chip--ok' : 'kel-chip--wait'}`}>{job.enabled ? 'Active' : 'Paused'}</span>
        </button>)}
      </div>}
    </section>
    {selected && <section className='kel-card kel-shell-task-detail kel-shell-task-detail-desktop' aria-label={selected.name}>
      <ShellSourceCardHeader title={selected.name} description={formatSchedule(selected, t)} />
      <div className='kel-shell-task-field'><span>Instructions</span><p>{selected.target.payload.text}</p></div>
      <div className='kel-shell-task-field'><span>Assistant</span><button type='button' className='kel-shell-task-setting-control' onClick={() => setEditOpen(true)} aria-label='Edit assistant'>{selected.metadata.agent_config?.name || 'Kel'}<span aria-hidden='true'>⌄</span></button></div>
      <div className='kel-shell-task-field'><span>Model</span><button type='button' className='kel-shell-task-setting-control' onClick={() => setEditOpen(true)} aria-label='Edit model'>{selected.metadata.agent_config?.model_id || selected.metadata.agent_config?.model?.model || 'Automatic'}<span aria-hidden='true'>⌄</span></button></div>
      <div className='kel-shell-task-field'><span>Execution mode</span><button type='button' className='kel-shell-task-setting-control' onClick={() => setEditOpen(true)} aria-label='Edit execution mode'>{selected.target.execution_mode === 'new_conversation' ? 'New conversation' : 'Existing conversation'}<span aria-hidden='true'>⌄</span></button></div>
      <div className='kel-shell-preference-row'><div><div>History</div><p className='kel-meta'>{selected.state.last_run_at_ms ? `Last run ${formatNextRun(selected.state.last_run_at_ms, i18n.language)} · ${selected.state.last_status === 'ok' ? 'succeeded' : selected.state.last_status || 'unknown'}` : 'No runs yet'}</p></div>
        <button type='button' className='kel-btn' disabled={!conversationId} onClick={() => conversationId && navigate(`/conversation/${conversationId}`)}>Go to conversation</button>
      </div>
    </section>}
    {selected && <section className='kel-card kel-shell-task-detail-mobile' aria-label={`${selected.name} summary`}>
      <div className='kel-shell-task-mobile-title'>
        <ShellSourceCardHeader title={selected.name} />
        <button type='button' aria-label='Task details' aria-expanded={mobileDetailsOpen} onClick={() => setMobileDetailsOpen(open => !open)}>ⓘ</button>
      </div>
      <div className='kel-shell-task-mobile-row'><span>Assistant</span><span>Kel</span></div>
      <div className='kel-shell-task-mobile-row'><span>Model</span><span>{selected.metadata.agent_config?.model_id || selected.metadata.agent_config?.model?.model || 'Automatic'}</span></div>
      <div className='kel-shell-task-mobile-row'><span>Queue</span><span>{selected.state.queue_enabled ? 'On' : 'Off'}</span></div>
      <button type='button' className='kel-shell-task-mobile-row kel-shell-task-mobile-history' onClick={() => { if (conversationId) navigate(`/conversation/${conversationId}`); else setMobileHistoryOpen(open => !open); }}>
        <span>History</span><span aria-hidden='true'>›</span>
      </button>
      {mobileHistoryOpen && <p className='kel-meta'>{selected.state.last_run_at_ms ? `Last run ${formatNextRun(selected.state.last_run_at_ms, i18n.language)} · ${selected.state.last_status || 'unknown'}` : 'No runs yet'}</p>}
      {mobileDetailsOpen && <div className='kel-shell-task-mobile-extra'><strong>Instructions</strong><p>{selected.target.payload.text}</p><strong>Execution mode</strong><p>{selected.target.execution_mode === 'new_conversation' ? 'New conversation' : 'Existing conversation'}</p></div>}
    </section>}
    <CreateTaskDialog visible={createOpen || editOpen} onClose={() => { setCreateOpen(false); setEditOpen(false); }} editJob={editOpen ? selected : undefined} />
  </main></div>;
}
