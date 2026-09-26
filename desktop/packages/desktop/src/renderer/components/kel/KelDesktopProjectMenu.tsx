import React, { useState } from 'react';
import check from '@renderer/assets/figma/chat-pickers/project-check.svg';
import folder from '@renderer/assets/figma/chat-pickers/project-folder.svg';
import search from '@renderer/assets/figma/chat-pickers/project-search.svg';
import close from '@renderer/assets/figma/chat-pickers/project-close.svg';
import plus from '@renderer/assets/figma/chat-pickers/project-plus.svg';

export const KelDesktopProjectMenu: React.FC<{
  paths: string[];
  selected: string;
  onSelect: (path: string) => void;
  onClear: () => void;
  onBrowse: () => void;
}> = ({ paths, selected, onSelect, onClear, onBrowse }) => {
  const [query, setQuery] = useState('');
  const name = (path: string) => path.split(/[\\/]/).pop() || path;
  const choices = [...new Set([...paths, ...(selected ? [selected] : [])])].filter(path => path.toLowerCase().includes(query.trim().toLowerCase()));
  return <div className='kel-desktop-project-menu kel-desktop-picker' data-testid='kel-desktop-project-menu' role='dialog' aria-label='Project picker'>
    <p className='kel-desktop-project-menu__label'>Work in a project</p>
    <div className='kel-desktop-project-menu__search-wrap'><label className='kel-desktop-project-menu__search'>
      <img src={search} alt='' /><input autoFocus aria-label='Search projects' placeholder='Search projects…' value={query} onChange={event => setQuery(event.target.value)} />
    </label></div>
    {choices.map(path => <button type='button' key={path} className='kel-desktop-picker__row' aria-pressed={selected === path} onClick={() => onSelect(path)} title={path}>
      <img src={folder} alt='' /><span>{name(path)}</span>{selected === path && <img src={check} alt='' />}
    </button>)}
    {!choices.length && query && <p className='kel-desktop-project-menu__empty'>No matching projects.</p>}
    <button type='button' className='kel-desktop-picker__row' aria-pressed={!selected} onClick={onClear}><img src={close} alt='' /><span>No project</span>{!selected && <img src={check} alt='' />}</button>
    <div className='kel-desktop-picker__divider' />
    <button type='button' className='kel-desktop-picker__row' onClick={onBrowse}><img src={plus} alt='' /><span>Choose a different folder</span></button>
  </div>;
};
