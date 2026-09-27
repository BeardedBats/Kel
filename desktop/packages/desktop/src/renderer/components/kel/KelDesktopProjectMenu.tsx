import React, { useState } from 'react';
import check from '@renderer/assets/figma/chat-pickers/project-check.svg';
import folder from '@renderer/assets/figma/chat-pickers/project-folder.svg';
import search from '@renderer/assets/figma/chat-pickers/project-search.svg';
import plus from '@renderer/assets/figma/chat-pickers/project-plus.svg';

export type KelProjectChoice = { id: string; name: string; root?: string | null };

const GENERAL_ID = 'default';

/**
 * The composer's project picker (Figma "Work in a project"). Rows are the engine's live projects;
 * General — the default project, with no folder — keeps the old "No project" row's place.
 */
export const KelDesktopProjectMenu: React.FC<{
  projects: KelProjectChoice[];
  /** The selected project id. */
  selected: string;
  onSelect: (project: KelProjectChoice) => void;
  onBrowse: () => void;
}> = ({ projects, selected, onSelect, onBrowse }) => {
  const [query, setQuery] = useState('');
  const needle = query.trim().toLowerCase();
  const general = projects.find(project => project.id === GENERAL_ID) ?? { id: GENERAL_ID, name: 'General', root: null };
  const seen = new Set<string>();
  const choices = projects
    .filter(project => project.id !== GENERAL_ID && !seen.has(project.id) && Boolean(seen.add(project.id)))
    .filter(project => !needle || project.name.toLowerCase().includes(needle) || (project.root ?? '').toLowerCase().includes(needle));
  return <div className='kel-desktop-project-menu kel-desktop-picker' data-testid='kel-desktop-project-menu' role='dialog' aria-label='Project picker'>
    <p className='kel-desktop-project-menu__label'>Work in a project</p>
    <div className='kel-desktop-project-menu__search-wrap'><label className='kel-desktop-project-menu__search'>
      <img src={search} alt='' /><input autoFocus aria-label='Search projects' placeholder='Search projects…' value={query} onChange={event => setQuery(event.target.value)} />
    </label></div>
    {choices.map(project => <button type='button' key={project.id} className='kel-desktop-picker__row' aria-pressed={selected === project.id} onClick={() => onSelect(project)} title={project.root ?? undefined}>
      <img src={folder} alt='' /><span>{project.name}</span>{selected === project.id && <img src={check} alt='' />}
    </button>)}
    {!choices.length && needle && <p className='kel-desktop-project-menu__empty'>No matching projects.</p>}
    <button type='button' className='kel-desktop-picker__row' aria-pressed={selected === GENERAL_ID} onClick={() => onSelect(general)}><img src={folder} alt='' /><span>{general.name}</span>{selected === GENERAL_ID && <img src={check} alt='' />}</button>
    <div className='kel-desktop-picker__divider' />
    <button type='button' className='kel-desktop-picker__row' onClick={onBrowse}><img src={plus} alt='' /><span>Choose a different folder</span></button>
  </div>;
};
