/**
 * @license
 * Copyright 2026 Kel
 * SPDX-License-Identifier: Apache-2.0
 *
 * D-57: the chat header's small clock for a chat a scheduled task uses (its own chat, or the chat
 * its latest run opened). Opens that task's page. Renders nothing for any other chat.
 */

import { iconColors } from '@/renderer/styles/colors';
import { useLayoutContext } from '@/renderer/hooks/context/LayoutContext';
import { Button, Tooltip } from '@arco-design/web-react';
import { AlarmClock } from '@icon-park/react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSchedules } from '../useSchedules';
import { scheduleStatus } from '../cronUtils';

interface ScheduleIndicatorProps {
  /** The app chat id. */
  conversation_id: string;
  /** A chat the old scheduler made names its task; that task keeps its id as `origin`. */
  cron_job_id?: string;
}

const ScheduleIndicator: React.FC<ScheduleIndicatorProps> = ({ conversation_id, cron_job_id }) => {
  const navigate = useNavigate();
  const layout = useLayoutContext();
  const { schedules } = useSchedules();
  const [engineId, setEngineId] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setEngineId(null);
    const lookup = window.kelAPI?.conversation;
    if (lookup) {
      lookup(conversation_id)
        .then((cid) => {
          if (alive) setEngineId(typeof cid === 'string' ? cid : null);
        })
        .catch((): undefined => undefined);
    }
    return () => {
      alive = false;
    };
  }, [conversation_id]);

  const ids = new Set([conversation_id, engineId].filter((value): value is string => Boolean(value)));
  const schedule =
    schedules.find((item) => item.start_mode === 'existing' && item.conversation_id && ids.has(item.conversation_id)) ??
    schedules.find((item) => item.last_run?.conversation && ids.has(item.last_run.conversation)) ??
    (cron_job_id ? schedules.find((item) => item.origin === cron_job_id) : undefined);

  // Kept off narrow widths so the title bar stays uncluttered; the sidebar entry still reaches it.
  if (!schedule || layout?.isMobile) return null;

  const status = scheduleStatus(schedule);
  const tip = status === 'error' ? `${schedule.name} — needs attention` : status === 'paused' ? `${schedule.name} — paused` : schedule.name;

  return (
    <Tooltip content={tip}>
      <Button
        type='text'
        size='small'
        aria-label={`Scheduled task: ${tip}`}
        className='cron-job-manager-button chat-header-cron-pill !h-auto !w-auto !min-w-0 !px-0 !py-0'
        onClick={() => navigate(`/scheduled/${encodeURIComponent(schedule.id)}`)}
      >
        <span data-testid='schedule-indicator' className='inline-flex items-center gap-2px rounded-full px-8px py-2px bg-2'>
          <AlarmClock theme='outline' size={16} fill={iconColors.primary} />
          <span
            className={`ms-4px w-8px h-8px rounded-full ${status === 'error' ? 'bg-[#f53f3f]' : status === 'paused' ? 'bg-[#ff7d00]' : 'bg-[#00b42a]'}`}
          />
        </span>
      </Button>
    </Tooltip>
  );
};

export default ScheduleIndicator;
