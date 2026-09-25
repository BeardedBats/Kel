import { ipcBridge } from '@/common';
import type { Assistant } from '@/common/types/agent/assistantTypes';
import ShellSourceCardHeader from '@renderer/components/kel/ShellSourceCardHeader';
import emptyIcon from '@renderer/assets/figma/empty-assistants.svg';
import rowIcon from '@renderer/assets/figma/nav-assistants.svg';
import React from 'react';
import useSWR from 'swr';
import SettingsPageWrapper from '../components/SettingsPageWrapper';

const AssistantsOverviewSettings: React.FC = () => {
  const { data, error, isLoading } = useSWR<Assistant[]>('assistants.list', () => ipcBridge.assistants.list.invoke());
  const mine = (data ?? []).filter((assistant) => assistant.source === 'user');

  return <SettingsPageWrapper>
    <section className='kel-card kel-shell-catalog-card' data-testid='kel-settings-assistants'>
      <ShellSourceCardHeader title='Your assistants' />
      {isLoading ? <p className='kel-shell-catalog-status'>Loading assistants…</p>
        : error ? <p className='kel-shell-catalog-status'>Assistants are unavailable.</p>
        : mine.length === 0 ? <div className='kel-shell-catalog-empty'>
          <span className='kel-shell-catalog-empty-icon' aria-hidden='true'><img src={emptyIcon} alt='' /></span>
          <p>No assistants here yet</p>
        </div>
        : <div className='kel-shell-catalog-list'>
          {mine.map((assistant) => <div className='kel-shell-catalog-row' key={assistant.id}>
            <img className='kel-shell-catalog-row-icon' src={rowIcon} alt='' />
            <span className='kel-shell-catalog-row-copy'><strong>{assistant.name}</strong>
            {assistant.description && <span>{assistant.description}</span>}</span>
          </div>)}
        </div>}
    </section>
  </SettingsPageWrapper>;
};

export default AssistantsOverviewSettings;
