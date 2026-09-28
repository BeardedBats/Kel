import { KelCard } from '@renderer/components/kel/KelPrimitives';
import AionModal from '@renderer/components/base/AionModal';
import thirdPartyNotices from '../../../../../../../../../THIRD_PARTY_NOTICES.md?raw';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import { Button } from '@arco-design/web-react';
import { Right } from '@icon-park/react';
import React, { useEffect, useState } from 'react';
import { isElectronDesktop, openExternalUrl } from '@/renderer/utils/platform';
import { ipcBridge } from '@/common';

// __APP_VERSION__ is injected by electron.vite.config.ts `define:` from the
// repo-root package.json. The previous `import packageJson from
// '../../../../../../package.json'` resolved to packages/desktop/package.json
// which is a workspace placeholder permanently pinned at "0.0.0".
declare const __APP_VERSION__: string;
// The source commit the package was built from (electron.vite.config.ts); empty when unknown.
declare const __APP_BUILD__: string;
const appBuild = typeof __APP_BUILD__ === 'string' ? __APP_BUILD__ : '';

// Kel has no consumer updater (handoff §26, D-56): About shows the version and
// build only. Upgrades are manual installs of a new App build.
const AboutModalContent: React.FC = () => {
  const isElectron = isElectronDesktop();

  const [dataPath, setDataPath] = useState<{ root: string; database: string } | null>(null);
  useEffect(() => {
    const bridge = (window as unknown as { kelAPI?: { request: (route: string, payload: unknown) => Promise<{ root: string; database: string }> } }).kelAPI;
    void bridge?.request('/api/data-path', {}).then(setDataPath).catch(() => {});
  }, []);

  const [showNotices, setShowNotices] = useState(false);

  return (
    <div className='kel-shell-about'>
      <KelCard title='Kel'>
        <div className='kel-shell-preference-row'><span>Version</span><span><span className='kel-desktop-only'>v{__APP_VERSION__}</span><span className='kel-phone-only'>{__APP_VERSION__.replace(/-/, ' · ')}</span></span></div>
        <div className='kel-shell-preference-row' data-testid='about-build'><span>Build</span><span>{appBuild || 'Not recorded'}</span></div>
        <div className='kel-shell-preference-row'><span>Runtime</span><span>{isElectron ? `Electron ${navigator.userAgent.match(/Electron\/(\d+)/)?.[1] ?? 'desktop'}` : 'WebUI'}<span className='kel-shell-about-runtime-detail'>{` · React ${React.version.split('.')[0]}`}</span></span></div>
        <div className='kel-shell-preference-row kel-shell-about-data-row'><div><div>Data folder</div><div className='kel-meta'>{dataPath?.root ?? 'Unavailable in WebUI'}</div></div><Button disabled={!dataPath} onClick={() => dataPath && void ipcBridge.shell.showItemInFolder.invoke(dataPath.database)}>Show in folder</Button></div>
        <div className='kel-shell-preference-row kel-desktop-only kel-shell-about-notices-inline'><span>Third-party notices</span><button type='button' onClick={() => setShowNotices(true)}>View</button></div>
      </KelCard>
      <div className='kel-shell-about-licenses'>
        <KelCard title='Licenses'>
          <button type='button' className='kel-shell-about-notices-row' onClick={() => setShowNotices(true)}>Third-party notices <Right theme='outline' size='16' /></button>
        </KelCard>
      </div>
      <AionModal visible={showNotices} onCancel={() => setShowNotices(false)} variant='standard' header={{ title: 'Third-party notices', showClose: true }} footer={null} aria-label='Third-party notices'>
        <div className='kel-shell-about-notices-content'>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ table: ({ children }) =>
            <div className='kel-shell-about-notices-table'><table>{children}</table></div>, a: ({ href, children }) =>
            <a href={href} onClick={(event) => {
              event.preventDefault();
              if (href && /^https?:\/\//i.test(href)) void openExternalUrl(href);
            }}>{children}</a>
          }}>{thirdPartyNotices}</ReactMarkdown>
        </div>
      </AionModal>
    </div>
  );
};

export default AboutModalContent;
