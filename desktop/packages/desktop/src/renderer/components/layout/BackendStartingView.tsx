/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { Spin, Typography } from '@arco-design/web-react';
import React from 'react';
import kelMark from '@renderer/assets/figma/kel-mark.png';
import startupClock from '@renderer/assets/figma/refresh/desktop-startup-clock.svg';
import startupLoader from '@renderer/assets/figma/refresh/desktop-startup-loader.svg';
import { useTranslation } from 'react-i18next';

/**
 * Full-screen, benign "backend is still starting" view. Shown while the backend
 * process is alive but not yet ready (reason `backend_startup_pending_slow`).
 *
 * This is intentionally NOT an error modal: it carries no report / download /
 * restart buttons and no reinstall / antivirus / missing-resource copy — the
 * backend binary exists and was observed listening, so such guidance would be
 * misleading. The top-level gate unmounts this view as soon as the backend
 * becomes ready (switching to the App) or the process exits (switching to the
 * honest-failure view). System-level quit (window close, tray, Cmd+Q) stays
 * available at the OS/main-process layer, so no in-view exit control is needed.
 */
const BackendStartingView: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className='kel-v2-shell kel-startup-screen' data-testid='backend-starting-view'>
      <section className='kel-startup-desktop kel-startup-card' aria-label='Starting up' aria-live='polite'>
        <div className='kel-startup-logo'><img src={kelMark} alt='' /><span>Kel</span></div>
        <div className='kel-startup-titles'><h1>{t('common.backendStartup.pendingSlow.title')}</h1><p>This takes a few seconds.</p></div>
        <div className='kel-startup-steps'>
          <div><img src={startupClock} alt='' /><span>Local data</span><strong className='kel-startup-waiting'>Waiting</strong></div>
          <div><img className='kel-startup-loader' src={startupLoader} alt='' /><span>Kel engine</span><strong className='kel-startup-starting'>Starting</strong></div>
          <div><img src={startupClock} alt='' /><span>Chats</span><strong className='kel-startup-waiting'>Waiting</strong></div>
        </div>
      </section>
    <div
      className='kel-startup-legacy min-h-screen bg-bg-1 flex flex-col items-center justify-center gap-16px'
    >
      <Spin size={28} />
      <div className='text-center px-24px max-w-480px'>
        <Typography.Title heading={5} className='mb-8px text-t-1'>
          {t('common.backendStartup.pendingSlow.title')}
        </Typography.Title>
        <Typography.Paragraph className='mb-0 text-t-secondary' data-testid='backend-starting-description'>
          {t('common.backendStartup.pendingSlow.description')}
        </Typography.Paragraph>
      </div>
    </div>
    </div>
  );
};

export default BackendStartingView;
