import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import kibbleIcon from '@renderer/assets/figma/refresh/kibble.svg';
import rambleIcon from '@renderer/assets/figma/refresh/ramble.svg';
import projectsIcon from '@renderer/assets/figma/refresh/projects.svg';
import settingsIcon from '@renderer/assets/figma/refresh/settings.svg';

type Tab = { label: string; path: string; icon: string | null; active: (path: string) => boolean };
const tabs: Tab[] = [
  { label: 'Chats', path: '/guid', icon: null, active: (path: string) => path === '/guid' || path.startsWith('/conversation/') },
  { label: 'Kibble', path: '/dogfood', icon: kibbleIcon, active: (path: string) => path === '/dogfood' },
  { label: 'Ramble', path: '/transcription', icon: rambleIcon, active: (path: string) => path.startsWith('/transcription') },
  { label: 'Projects', path: '/projects', icon: projectsIcon, active: (path: string) => /^(\/projects|\/work|\/activity|\/autonomy|\/scheduled|\/providers|\/diagnostics)(\/|$)/.test(path) },
  { label: 'Settings', path: '/settings', icon: settingsIcon, active: (path: string) => path.startsWith('/settings') || path === '/connections' },
];

export default function KelMobileTabs() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return <nav className='kel-mobile-tabs' aria-label='Kel tabs'>
    {tabs.map(tab => <button
      key={tab.label}
      type='button'
      className='kel-mobile-tabs__item'
      aria-current={tab.active(pathname) ? 'page' : undefined}
      onClick={() => void navigate(tab.path)}
    >
      {tab.icon ? <img src={tab.icon} alt='' width={20} height={20} /> : <svg aria-hidden='true' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='1.5'><path d='M20 11.5a8 8 0 0 1-8 8 8.5 8.5 0 0 1-3.4-.7L4 20l1.2-4.6A8.5 8.5 0 0 1 4 11.5a8 8 0 0 1 16 0Z' /></svg>}
      <span>{tab.label}</span>
    </button>)}
  </nav>;
}
