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
    <SettingsPageWrapper contentClassName='max-w-920px'>
      <div className='kel-shell-model-settings flex flex-col gap-12px'>
        <KelDefaultModelCard compact />
        <ModelModalContent />
      </div>
    </SettingsPageWrapper>
  );
};

export default ModeSettings;
