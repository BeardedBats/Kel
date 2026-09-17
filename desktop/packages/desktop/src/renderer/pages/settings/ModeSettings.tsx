/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import ModelModalContent from '@/renderer/components/settings/SettingsModal/contents/ModelModalContent';
import { KelDefaultModelCard } from '@/renderer/components/kel/KelModelControl';
import SettingsPageWrapper from './components/SettingsPageWrapper';

const ModeSettings: React.FC = () => {
  return (
    <SettingsPageWrapper contentClassName='max-w-1100px'>
      <KelDefaultModelCard />
      <ModelModalContent />
    </SettingsPageWrapper>
  );
};

export default ModeSettings;
