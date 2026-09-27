import { ipcBridge } from '@/common';
import ShellSourceCardHeader from '@renderer/components/kel/ShellSourceCardHeader';
import emptyIcon from '@renderer/assets/figma/empty-skills.svg';
import rowIcon from '@renderer/assets/figma/nav-skills.svg';
import React from 'react';
import useSWR from 'swr';
import SettingsPageWrapper from '../components/SettingsPageWrapper';

type Skill = Awaited<ReturnType<typeof ipcBridge.fs.listAvailableSkills.invoke>>[number];

/**
 * D-60: Skills shows only what Kel actually has — the skills Kel ships and the ones the person added
 * on this computer. There is no hub, store or "install from" flow.
 */
const SkillList: React.FC<{ title: string; skills: Skill[]; empty: string; testId: string }> = ({ title, skills, empty, testId }) => (
  <section className='kel-card kel-shell-catalog-card' data-testid={testId}>
    <ShellSourceCardHeader title={title} />
    {skills.length === 0 ? <div className='kel-shell-catalog-empty'>
      <span className='kel-shell-catalog-empty-icon' aria-hidden='true'><img src={emptyIcon} alt='' /></span>
      <p>{empty}</p>
    </div>
      : <div className='kel-shell-catalog-list'>
        {skills.map((skill) => <div className='kel-shell-catalog-row' key={`${skill.source}-${skill.name}`}>
          <img className='kel-shell-catalog-row-icon' src={rowIcon} alt='' />
          <span className='kel-shell-catalog-row-copy'><strong>{skill.name}</strong>
          {skill.description && <span>{skill.description}</span>}</span>
        </div>)}
      </div>}
  </section>
);

const SkillsOverviewSettings: React.FC = () => {
  const { data, error, isLoading } = useSWR<Skill[]>('kel.settings.skills', () => ipcBridge.fs.listAvailableSkills.invoke());
  const builtIn = (data ?? []).filter((skill) => skill.source === 'builtin');
  const mine = (data ?? []).filter((skill) => skill.source === 'custom');

  return <SettingsPageWrapper>
    <div className='kel-shell-catalog-stack' data-testid='kel-settings-skills'>
      {isLoading ? <section className='kel-card kel-shell-catalog-card'><p className='kel-shell-catalog-status'>Loading skills…</p></section>
        : error ? <section className='kel-card kel-shell-catalog-card'><p className='kel-shell-catalog-status'>Kel couldn't load its skills. Try again in a moment.</p></section>
        : <>
          <SkillList title='Built into Kel' skills={builtIn} empty='No built-in skills found' testId='kel-settings-skills-builtin' />
          <SkillList title='Added by you' skills={mine} empty='You haven’t added any skills' testId='kel-settings-skills-custom' />
        </>}
      <section className='kel-card kel-shell-catalog-tip'>
        <ShellSourceCardHeader title='How skills work' />
        <p>Skills are ready-made instructions Kel can follow for particular kinds of work.</p>
      </section>
    </div>
  </SettingsPageWrapper>;
};

export default SkillsOverviewSettings;
