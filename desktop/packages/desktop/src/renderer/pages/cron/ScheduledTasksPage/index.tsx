import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { Spin } from '@arco-design/web-react';
import ShellWorkspaceLink from '@renderer/components/kel/ShellWorkspaceLink';
import ShellSourceCardHeader from '@renderer/components/kel/ShellSourceCardHeader';
import { KelEmpty } from '@renderer/components/kel/KelPrimitives';
import { kelSchedules, type KelSchedule } from '@renderer/components/kel/kelApi';
import { useSchedules } from '@renderer/pages/cron/useSchedules';
import { formatNextRun, scheduleChip, scheduleSentence } from '@renderer/pages/cron/cronUtils';
import CreateTaskDialog from './CreateTaskDialog';
import type { ScheduleFromChatRequest } from '@renderer/pages/cron/scheduleFromChat';
import { ALL_PROJECTS, useProjects } from '@renderer/components/kel/activeProject';

const rowMeta = (schedule: KelSchedule, locale: string): string => {
  const when = scheduleSentence(schedule, locale);
  if (schedule.running) return `${when} · running now`;
  if (schedule.problem || !schedule.enabled || schedule.status === 'done') return `${when} · paused`;
  return schedule.next_due_at ? `${when} · next ${formatNextRun(schedule.next_due_at, locale)}` : when;
};

/**
 * Scheduled tasks (D-57): one row per engine schedule in the current project; a row opens that
 * task's page (`/scheduled/:id`), which owns its details, history, run-now, edit and delete (WK-8).
 * A link from before the move (`/scheduled?origin=<old id>`) lands on the task it became. A chat
 * menu's "Create scheduled task" arrives with `{ scheduleFromChat }` router state and opens the
 * editor filled in from that chat.
 */
export default function ScheduledTasksPage() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const origin = params.get('origin');
  const { schedules, loading, error } = useSchedules();
  const location = useLocation();
  const [createOpen, setCreateOpen] = useState(false);
  const [fromChat, setFromChat] = useState<ScheduleFromChatRequest | undefined>(undefined);
  const [originMissing, setOriginMissing] = useState(false);
  const { active } = useProjects();

  const requested = (location.state as { scheduleFromChat?: ScheduleFromChatRequest } | null)?.scheduleFromChat;
  useEffect(() => {
    if (!requested?.conversationId) return;
    setFromChat(requested);
    setCreateOpen(true);
    // Consume the request so Back or a reload does not open the editor again.
    navigate(`${location.pathname}${location.search}`, { replace: true, state: null });
  }, [requested, navigate, location.pathname, location.search]);

  const openBlank = () => {
    setFromChat(undefined);
    setCreateOpen(true);
  };

  useEffect(() => {
    if (!origin) return;
    let alive = true;
    setOriginMissing(false);
    kelSchedules
      .get({ origin })
      .then((schedule) => {
        if (!alive) return;
        if (schedule) navigate(`/scheduled/${encodeURIComponent(schedule.id)}`, { replace: true });
        else setOriginMissing(true);
      })
      .catch(() => {
        if (alive) setOriginMissing(true);
      });
    return () => {
      alive = false;
    };
  }, [origin, navigate]);

  const shown = active === ALL_PROJECTS ? schedules : schedules.filter((schedule) => schedule.project_id === active);
  const hiddenElsewhere = schedules.length - shown.length;

  return <div className='kel-scope'><main className='kel-page kel-shell-scheduled'>
    <div className='kel-page__head'>
      <div><ShellWorkspaceLink /><h1 className='kel-h1'>Scheduled tasks</h1></div>
      <span className='kel-grow' /><button type='button' className='kel-btn kel-btn--primary kel-shell-task-create-desktop' onClick={openBlank}>New task</button>
    </div>
    {originMissing && <p className='kel-meta' role='status'>That scheduled task is no longer here. It may have been deleted.</p>}
    <section className='kel-card kel-shell-task-list' aria-label='Scheduled tasks'>
      <ShellSourceCardHeader title='Scheduled tasks' description={`${shown.length} ${shown.length === 1 ? 'task' : 'tasks'}`} />
      <button type='button' className='kel-shell-task-create-mobile' aria-label='New task' onClick={openBlank}>+</button>
      {loading ? <Spin /> : error && shown.length === 0 ? (
        <KelEmpty title='Scheduled tasks are unavailable right now.' why={`${error} Your tasks are kept; try again in a moment.`} />
      ) : shown.length === 0 ? (
        // VIS-17: the header's "New task" is the one primary; the empty state explains, it adds no second.
        <KelEmpty
          title='No scheduled tasks yet.'
          why={hiddenElsewhere > 0
            ? `This project has none. ${hiddenElsewhere} ${hiddenElsewhere === 1 ? 'task belongs' : 'tasks belong'} to other projects — switch to All projects to see ${hiddenElsewhere === 1 ? 'it' : 'them'}.`
            : 'A scheduled task asks Kel to do the same thing on a schedule — for example, “every Friday at 4, summarize what changed in this project this week”. Each run shows up here with its result.'}
        />
      ) : <div>
        {shown.map(schedule => {
          const chip = scheduleChip(schedule);
          return <button key={schedule.id} type='button' className='kel-shell-task-row' data-testid={`scheduled-row-${schedule.id}`} onClick={() => navigate(`/scheduled/${encodeURIComponent(schedule.id)}`)}>
            <span>{schedule.name}</span><span className='kel-meta'>{rowMeta(schedule, i18n.language)}</span>
            <span className={`kel-chip ${chip.tone}`}>{chip.label}</span>
          </button>;
        })}
      </div>}
    </section>
    <p className='kel-meta kel-shell-scheduled-footer'>Scheduled tasks run while Kel is open on this computer.</p>
    <CreateTaskDialog visible={createOpen} onClose={() => setCreateOpen(false)} fromChat={fromChat} />
  </main></div>;
}
