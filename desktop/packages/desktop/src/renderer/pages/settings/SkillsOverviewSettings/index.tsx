import { ipcBridge } from '@/common';
import ShellSourceCardHeader from '@renderer/components/kel/ShellSourceCardHeader';
import emptyIcon from '@renderer/assets/figma/empty-skills.svg';
import React from 'react';
import useSWR from 'swr';
import SettingsPageWrapper from '../components/SettingsPageWrapper';

type Skill = Awaited<ReturnType<typeof ipcBridge.fs.listAvailableSkills.invoke>>[number];

const SkillsOverviewSettings: React.FC = () => {
  const { data, error, isLoading } = useSWR<Skill[]>('kel.settings.skills', () => ipcBridge.fs.listAvailableSkills.invoke());
  const mine = (data ?? []).filter((skill) => skill.source === 'custom');

  return <SettingsPageWrapper>
    <div className='kel-shell-catalog-stack' data-testid='kel-settings-skills'>
      <section className='kel-card kel-shell-catalog-card'>
        <ShellSourceCardHeader title='My Skills' />
        {isLoading ? <p className='kel-shell-catalog-status'>Loading skills…</p>
          : error ? <p className='kel-shell-catalog-status'>Skills are unavailable.</p>
          : mine.length === 0 ? <div className='kel-shell-catalog-empty'>
            <span className='kel-shell-catalog-empty-icon' aria-hidden='true'><img src={emptyIcon} alt='' /></span>
            <p>No skills installed</p>
          </div>
          : <div className='kel-shell-catalog-list'>
            {mine.map((skill) => <div className='kel-shell-catalog-row' key={skill.name}>
              <strong>{skill.name}</strong>
              {skill.description && <span>{skill.description}</span>}
            </div>)}
          </div>}
      </section>
      <section className='kel-card kel-shell-catalog-tip'>
        <ShellSourceCardHeader title='Usage Tip' />
        <p>Skills work across assistants. Enable a skill on an assistant to let it use the pack.</p>
      </section>
    </div>
  </SettingsPageWrapper>;
};

export default SkillsOverviewSettings;
