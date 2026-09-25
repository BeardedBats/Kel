/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * ToolsSettings — standalone settings page for MCP servers and built-in tools
 * (e.g. image generation). Split out of the former combined "Capabilities" page
 * so Tools has its own top-level entry in the settings sidebar.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import ToolsModalContent from '@/renderer/components/settings/SettingsModal/contents/ToolsModalContent';
import SettingsPageWrapper from '../components/SettingsPageWrapper';

const ToolsSettings: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <SettingsPageWrapper contentClassName='max-w-1200px'>
      <div className='flex flex-col gap-16px'>
        <p className='kel-meta' data-testid='tools-header'>{t('settings.toolsDescription', { defaultValue: 'Configure MCP servers and built-in tools such as image generation.' })}</p>
        <ToolsModalContent />
        <button className='kel-tools-kibble-entry' type='button' onClick={() => void navigate('/dogfood')}>
          <span>Kibble</span><span>Review captured fixes</span><span aria-hidden='true'>›</span>
        </button>
      </div>
    </SettingsPageWrapper>
  );
};

export default ToolsSettings;
