/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import type { ICronJob } from '@/common/adapter/ipcBridge';

type StatusTone = 'paused' | 'error' | 'active';

const CronStatusTag: React.FC<{ job: ICronJob }> = ({ job }) => {
  const { t } = useTranslation();

  let label = t('cron.status.active');
  let tone: StatusTone = 'active';

  if (!job.enabled) {
    tone = 'paused';
    label = t('cron.status.paused');
  } else if (job.state.last_status === 'error' || job.state.last_status === 'missed') {
    tone = 'error';
    label = t('cron.status.error');
  }

  return (
    <span className={`kel-chip ${tone === 'paused' ? 'kel-chip--wait' : tone === 'error' ? 'kel-chip--failed' : 'kel-chip--ok'}`}>
      {label}
    </span>
  );
};

export default CronStatusTag;
