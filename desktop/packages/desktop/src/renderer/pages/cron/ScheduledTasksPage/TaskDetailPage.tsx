/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-57: one scheduled task, read from the engine — its details, pause/resume, edit, run now,
 * delete, and the runs the engine derives from its own jobs (never a separate run table).
 */

import AionModal from '@renderer/components/base/AionModal';
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { Checkbox, Message, Spin, Switch } from '@arco-design/web-react';
import { KelButton, KelCard } from '@renderer/components/kel/KelPrimitives';
import { kelRecipeGet, type KelSchedule, type KelScheduleRun } from '@renderer/components/kel/kelApi';
import { choiceLabel, useKelModelState } from '@renderer/components/kel/KelModelControl';
import { GENERAL_PROJECT_ID, GENERAL_PROJECT_NAME, useProjects } from '@renderer/components/kel/activeProject';
import { resolveConversationRoute } from '@/renderer/pages/conversation/GroupedHistory/hooks/useConversationListSync';
import { jobRouteFor } from '@renderer/components/kel/needsAttention';
import { formatNextRun, scheduleSentence } from '@renderer/pages/cron/cronUtils';
import { scheduleActions, useSchedule } from '@renderer/pages/cron/useSchedules';
import CreateTaskDialog from './CreateTaskDialog';

const errorText = (error: unknown, fallback: string) => String((error as Error)?.message || '').trim() || fallback;

/** The history dot/label colour: the engine's status in two tones plus neutral. */
const runTone = (run: KelScheduleRun): string | undefined => {
  const status = (run.status || '').toLowerCase();
  if (status === 'success') return 'ok';
  if (['needs_you', 'needs_look', 'not_started', 'failed'].includes(status)) return 'error';
  return undefined;
};

/** The route that opens a run: its chat (made on first use), or the job on Activity (D-70). */
export async function runRoute(run: KelScheduleRun): Promise<string | null> {
  if (run.conversation) {
    const open = window.kelAPI?.openEngineConversation;
    if (open) {
      try {
        const donor = await open(run.conversation);
        if (donor) return `/conversation/${donor}`;
      } catch {
        // Fall back to the route the chat list can resolve, then to the job.
      }
    }
    const mapped = resolveConversationRoute(`/conversation/${run.conversation}`);
    if (mapped !== `/conversation/${run.conversation}` || !run.job_id) return mapped;
  }
  return run.job_id ? jobRouteFor(run.job_id) : null;
}

const runSubtitle = (run: KelScheduleRun, schedule: KelSchedule): string =>
  run.cause?.trim() ||
  (run.conversation ? (schedule.start_mode === 'existing' ? 'Continued the conversation' : 'Opened a new conversation') : '');

const TaskDetailPage: React.FC = () => {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { schedule, runs, error, historyError, reload } = useSchedule({ id });
  const { projects } = useProjects();
  const { state: modelState } = useKelModelState();
  const [editOpen, setEditOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [keepConversations, setKeepConversations] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [recipeName, setRecipeName] = useState<string | null>(null);
  // Synchronous re-entry guard: two quick clicks must not start two runs.
  const runningNowRef = useRef(false);

  const recipeId = schedule?.target?.kind === 'recipe' ? schedule.target.recipe_id : null;
  const knownRecipeName = schedule?.target?.kind === 'recipe' ? schedule.target.recipe_name : null;
  useEffect(() => {
    setRecipeName(knownRecipeName ?? null);
    if (!recipeId || !schedule || knownRecipeName) return;
    let alive = true;
    kelRecipeGet(recipeId, { project: schedule.project_id })
      .then((answer) => {
        if (alive) setRecipeName(answer?.recipe?.name || null);
      })
      .catch((): undefined => undefined);
    return () => {
      alive = false;
    };
  }, [recipeId, knownRecipeName, schedule?.project_id]);

  const act = async (label: string, work: () => Promise<unknown>, done?: string) => {
    setBusy(label);
    try {
      await work();
      if (done) Message.success(done);
      await reload();
    } catch (failure) {
      Message.error(errorText(failure, 'Kel could not do that just now.'));
    } finally {
      setBusy(null);
    }
  };

  if (schedule === undefined && !error) {
    return <div className='size-full flex-center'><Spin /></div>;
  }

  const back = <button type='button' className='kel-task-detail-back' onClick={() => navigate('/scheduled')}>←&nbsp; All scheduled tasks</button>;

  if (!schedule) {
    return <main className='kel-page kel-scheduled-detail-desktop' data-testid='scheduled-detail-desktop'>
      {back}
      <KelCard title='Details' className='kel-task-detail-details'>
        <p className='kel-meta'>{error ? `This task is unavailable right now. ${error}` : 'This scheduled task is no longer here. It may have been deleted.'}</p>
      </KelCard>
    </main>;
  }

  const isManual = schedule.cadence?.kind === 'manual';
  const instructions = schedule.target?.kind === 'instruction' ? schedule.target.text : null;
  const projectName =
    schedule.project_name ||
    (projects ?? []).find((project) => project.id === schedule.project_id)?.name ||
    (schedule.project_id === GENERAL_PROJECT_ID ? GENERAL_PROJECT_NAME : projects ? 'Project unavailable' : '—');
  const modelName = schedule.model_label || (schedule.model?.provider
    ? modelState
      ? choiceLabel(modelState, schedule.model)
      : schedule.model.model || schedule.model.provider
    : 'Automatic');
  const stateLabel = schedule.problem ? 'Needs attention' : schedule.enabled ? 'Active' : 'Paused';

  const handleRunNow = async () => {
    if (runningNowRef.current) return;
    runningNowRef.current = true;
    setBusy('run');
    try {
      const answer = await scheduleActions.runNow(schedule.id);
      const route = answer?.conversation ? await runRoute({ conversation: answer.conversation }) : null;
      Message.success('Started. Its result shows here and in its conversation when it is checked.');
      await reload();
      if (route) navigate(route);
    } catch (failure) {
      Message.error(errorText(failure, 'Kel could not start this task just now.'));
    } finally {
      runningNowRef.current = false;
      setBusy(null);
    }
  };

  const handleDelete = async () => {
    setBusy('delete');
    try {
      await scheduleActions.remove(schedule.id, keepConversations ? 'keep' : 'delete');
      Message.success('Scheduled task deleted.');
      navigate('/scheduled');
    } catch (failure) {
      Message.error(errorText(failure, 'Kel could not delete this task just now.'));
      setBusy(null);
    }
  };

  const openRun = async (run: KelScheduleRun) => {
    const route = await runRoute(run);
    if (route) navigate(route);
    else Message.info('That run’s conversation is no longer available.');
  };

  return <>
    <main className='kel-page kel-scheduled-detail-desktop' data-testid='scheduled-detail-desktop'>
      {back}
      <header className='kel-task-detail-heading'>
        <h1>{schedule.name}</h1>
        <span className={`kel-task-detail-state${schedule.enabled && !schedule.problem ? ' kel-task-detail-state--active' : ''}`}>{stateLabel}</span>
        <span className='kel-grow' />
        {!isManual && <KelButton variant='quiet' disabled={busy !== null}
          onClick={() => void act('toggle', () => (schedule.enabled ? scheduleActions.pause(schedule.id) : scheduleActions.resume(schedule.id)),
            schedule.enabled ? 'Paused.' : 'Resumed.')}>
          {schedule.enabled ? 'Pause' : 'Resume'}
        </KelButton>}
        <KelButton variant='quiet' onClick={() => setEditOpen(true)}>Edit</KelButton>
        <KelButton variant='primary' disabled={busy !== null} onClick={() => void handleRunNow()}>
          {busy === 'run' ? 'Starting…' : 'Run now'}
        </KelButton>
      </header>
      {schedule.problem && <div className='kel-task-detail-problem' role='status'>
        <strong>Needs attention</strong> <span>{schedule.problem}</span>
      </div>}
      <KelCard title='Details' className='kel-task-detail-details'
        chip={<span className='kel-meta'>{scheduleSentence(schedule, i18n.language)}</span>}>
        <div className='kel-task-detail-instructions'>
          {instructions !== null
            ? <><span>Instructions</span><p>{instructions || '—'}</p></>
            : recipeId
              ? <><span>Recipe</span><p>{recipeName || recipeId}</p></>
              : <><span>Instructions</span><p>Unavailable right now.</p></>}
        </div>
        <div className='kel-task-detail-field'><span>Assistant</span><span>Kel</span></div>
        <div className='kel-task-detail-field'><span>Model</span><span>{modelName}</span></div>
        <div className='kel-task-detail-field'><span>Starts</span><span>{schedule.start_mode === 'existing' ? 'The same conversation each run' : 'A new conversation each run'}</span></div>
        <div className='kel-task-detail-field'><span>Project</span><span>{projectName}</span></div>
        {!isManual && <div className='kel-task-detail-field'><span>Next run</span><span>{schedule.enabled && !schedule.problem && schedule.next_due_at ? formatNextRun(schedule.next_due_at, i18n.language) : 'Paused'}</span></div>}
        <div className='kel-task-detail-field kel-task-detail-switch-row'>
          <span>Skip if still running<small>If the last run has not finished, Kel skips this one.</small></span>
          <Switch checked={schedule.skip_if_running} disabled={busy !== null} aria-label='Skip if still running'
            onChange={() => void act('skip', () => scheduleActions.update(schedule.id, { skip_if_running: !schedule.skip_if_running }))} />
        </div>
        <div className='kel-task-detail-field kel-task-detail-delete-row'>
          <span>Delete this task<small>Chats its finished runs opened are removed too.</small></span>
          <KelButton variant='danger' onClick={() => setConfirmDelete(true)}>Delete</KelButton>
        </div>
        {confirmDelete && <AionModal visible className='kel-task-delete-modal' variant='standard'
          header={{ title: 'Delete this scheduled task?', subtitle: 'Chats its finished runs opened are removed from your list. A run that is still going is kept and finishes.', showClose: false }}
          footer={null} closable={false} onCancel={() => setConfirmDelete(false)} focusLock autoFocus style={{ width: 460 }}>
          <Checkbox checked={keepConversations} onChange={setKeepConversations}>Keep the chats its runs opened</Checkbox>
          <div className='kel-task-delete-actions'>
            <KelButton variant='quiet' onClick={() => setConfirmDelete(false)}>Keep task</KelButton>
            <KelButton variant='danger' disabled={busy === 'delete'} onClick={() => void handleDelete()}>Delete task</KelButton>
          </div>
        </AionModal>}
      </KelCard>
      <KelCard title='History' className='kel-task-detail-history'>
        {runs === null
          ? <p className='kel-meta'>{historyError ? `History is unavailable right now. ${historyError}` : 'Loading…'}</p>
          : runs.length === 0
            ? <p className='kel-meta'>No runs yet.{!isManual && schedule.enabled && schedule.next_due_at ? ` Next run ${formatNextRun(schedule.next_due_at, i18n.language)}.` : ''}</p>
            : runs.map((run, index) => {
              const tone = runTone(run);
              const canOpen = Boolean(run.conversation || run.job_id);
              return <div className='kel-task-detail-history-row' key={`${run.submission_id || run.job_id || run.slot || index}-${index}`}>
                <span className='kel-task-detail-history-dot' data-state={tone} />
                <span className='kel-task-detail-history-text'>
                  <strong>{run.at ? formatNextRun(run.at, i18n.language) : run.slot ? formatNextRun(run.slot, i18n.language) : 'Time unavailable'}</strong>
                  <small>{runSubtitle(run, schedule)}</small>
                </span>
                <span className='kel-task-detail-run-status' data-state={tone}>{run.label || '—'}</span>
                {canOpen && <KelButton variant='primary' onClick={() => void openRun(run)}>Open</KelButton>}
              </div>;
            })}
      </KelCard>
    </main>
    <CreateTaskDialog visible={editOpen} onClose={() => { setEditOpen(false); void reload(); }} editSchedule={schedule} />
  </>;
};

export default TaskDetailPage;
