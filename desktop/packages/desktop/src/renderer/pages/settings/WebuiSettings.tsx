/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import WebuiModalContent from '@/renderer/components/settings/SettingsModal/contents/WebuiModalContent';
import { KelButton, KelCard } from '@/renderer/components/kel/KelPrimitives';
import { useBrowserSignOut } from '@/renderer/hooks/system/useBrowserSignOut';
import SettingsPageWrapper from './components/SettingsPageWrapper';

/** CP-12: in a browser, signing out is a visible button here (not a hidden keyboard chord). */
export const BrowserSignOutCard: React.FC = () => {
  const { available, signOut } = useBrowserSignOut();
  if (!available) return null;
  return (
    <KelCard title='This browser' data-testid='kel-browser-sign-out'>
      <div className='kel-row'>
        <span className='kel-meta'>You are signed in to Kel in this browser.</span>
        <span className='kel-grow' />
        <KelButton onClick={() => void signOut()}>Sign out</KelButton>
      </div>
    </KelCard>
  );
};

const WebuiSettings: React.FC = () => {
  return (
    <SettingsPageWrapper>
      <BrowserSignOutCard />
      <WebuiModalContent />
    </SettingsPageWrapper>
  );
};

export default WebuiSettings;
