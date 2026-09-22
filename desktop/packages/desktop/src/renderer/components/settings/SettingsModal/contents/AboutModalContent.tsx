import { KelCard } from '@renderer/components/kel/KelPrimitives';
import { useNavigate } from 'react-router-dom';
/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { Button, Switch, Message } from '@arco-design/web-react';
import { Right } from '@icon-park/react';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { isElectronDesktop, openExternalUrl } from '@/renderer/utils/platform';
import FeedbackReportModal from './FeedbackReportModal';
import { ipcBridge } from '@/common';
import { getIncludePrerelease, runUpdateCheck } from '@/renderer/components/settings/checkForUpdatesShared';
import { UPDATE_AVAILABLE_EVENT } from '@/renderer/components/settings/useUpdateNotificationController';
import { IS_DISCONTINUED_BUILD } from '@/renderer/utils/discontinuedBuild';
import { OPEN_MIGRATION_DIALOG_EVENT } from '@/renderer/components/settings/UpdateMigrationDialog';
import {
  getUpdateReadyState,
  setUpdateReadyState,
  subscribeUpdateReadyState,
  type UpdateReadyState,
} from '@/renderer/components/settings/updateReadyState';

// __APP_VERSION__ is injected by electron.vite.config.ts `define:` from the
// repo-root package.json. The previous `import packageJson from
// '../../../../../../package.json'` resolved to packages/desktop/package.json
// which is a workspace placeholder permanently pinned at "0.0.0".
declare const __APP_VERSION__: string;

type LinkItem =
  | { title: string; url: string; icon: React.ReactNode; onClick?: never }
  | { title: string; onClick: () => void; icon: React.ReactNode; url?: never };

const AboutModalContent: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const isElectron = isElectronDesktop();

  const [dataPath, setDataPath] = useState<{ root: string; database: string } | null>(null);
  useEffect(() => {
    const bridge = (window as unknown as { kelAPI?: { request: (route: string, payload: unknown) => Promise<{ root: string; database: string }> } }).kelAPI;
    void bridge?.request('/api/data-path', {}).then(setDataPath).catch(() => {});
  }, []);

  const [includePrerelease, setIncludePrerelease] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [updateReadyState, setLocalUpdateReadyState] = useState<UpdateReadyState>(() => getUpdateReadyState());
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('update.includePrerelease');
    setIncludePrerelease(saved === 'true');
  }, []);

  useEffect(() => subscribeUpdateReadyState(setLocalUpdateReadyState), []);

  const handlePrereleaseChange = (val: boolean) => {
    setIncludePrerelease(val);
    localStorage.setItem('update.includePrerelease', String(val));
  };

  const openLink = async (url: string) => {
    try {
      await openExternalUrl(url);
    } catch (error) {
      console.log('Failed to open link:', error);
    }
  };

  const checkUpdate = async () => {
    // Discontinued build: guide to the AionPro website instead of any in-app
    // version detection. Dead-branched out of normal builds by the flag.
    if (IS_DISCONTINUED_BUILD) {
      window.dispatchEvent(new CustomEvent(OPEN_MIGRATION_DIALOG_EVENT));
      return;
    }

    if (updateReadyState.ready) {
      if (updateReadyState.preparing) return;
      if (updateReadyState.filePath) {
        void ipcBridge.shell.openFile.invoke(updateReadyState.filePath);
        return;
      }
      setUpdateReadyState({ ...updateReadyState, preparing: true });
      void ipcBridge.autoUpdate.quitAndInstall.invoke().catch(() => {
        Message.error(t('update.errors.prepareInstallFailed'));
        setUpdateReadyState({ ...updateReadyState, preparing: false });
      });
      return;
    }

    if (checking) return;
    setChecking(true);
    try {
      const outcome = await runUpdateCheck({
        includePrerelease: getIncludePrerelease(),
        fallbackVersion: __APP_VERSION__,
        checkFailedLabel: t('update.checkFailed'),
      });
      if (outcome.kind === 'available') {
        // Only reveal the bottom-right card once an update is confirmed; hand
        // over the already-fetched outcome so the card skips the checking flash.
        window.dispatchEvent(new CustomEvent(UPDATE_AVAILABLE_EVENT, { detail: outcome }));
      } else if (outcome.kind === 'upToDate') {
        Message.info(t('update.alreadyLatest'));
      } else {
        Message.error(outcome.message || t('update.checkFailed'));
      }
    } finally {
      setChecking(false);
    }
  };

  const linkItems: LinkItem[] = [
    {
      title: t('settings.updateLog'),
      url: 'https://github.com/BeardedBats/Kel/releases',
      icon: <Right theme='outline' size='16' className='rtl-mirror' />,
    },
    {
      title: t('settings.bugReport'),
      onClick: () => setShowFeedbackModal(true),
      icon: <Right theme='outline' size='16' className='rtl-mirror' />,
    },
  ];

  return (
    <div className='kel-shell-about'>
      <KelCard title='Kel'>
        <div className='kel-shell-preference-row'><span>Version</span><span>v{__APP_VERSION__}</span></div>
        <div className='kel-shell-preference-row'><span>Runtime</span><span>{`${isElectron ? `Electron ${navigator.userAgent.match(/Electron\/(\d+)/)?.[1] ?? 'desktop'}` : 'WebUI'} · React ${React.version.split('.')[0]} · Arco Design`}</span></div>
        <div className='kel-shell-preference-row'><div><div>Data folder</div><div className='kel-meta'>{dataPath?.root ?? 'Unavailable in WebUI'}</div></div><Button disabled={!dataPath} onClick={() => dataPath && void ipcBridge.shell.showItemInFolder.invoke(dataPath.database)}>Show in folder</Button></div>
        {isElectron && <>
          <Button className='kel-shell-about-update' loading={checking || updateReadyState.preparing} disabled={updateReadyState.preparing} onClick={() => void checkUpdate()}>
            {updateReadyState.preparing ? t('update.preparingInstall') : updateReadyState.ready ? t('settings.updateReadyInstall', { version: updateReadyState.version }) : checking ? t('settings.checkingForUpdates') : t('settings.checkForUpdates')}
          </Button>
        </>}
      </KelCard>
      <FeedbackReportModal visible={showFeedbackModal} onCancel={() => setShowFeedbackModal(false)} />
    </div>
  );
};

export default AboutModalContent;
