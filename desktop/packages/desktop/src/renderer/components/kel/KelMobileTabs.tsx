import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import chatsIcon from '@renderer/assets/figma/refresh/mobile-tab-chats.svg';
import rambleIcon from '@renderer/assets/figma/refresh/mobile-tab-ramble.svg';
import projectsIcon from '@renderer/assets/figma/refresh/mobile-tab-projects.svg';
import settingsIcon from '@renderer/assets/figma/refresh/mobile-tab-settings.svg';

type Tab = { label: string; path: string; icon: string; active: (path: string) => boolean };
const tabs: Tab[] = [
  { label: 'Chats', path: '/guid', icon: chatsIcon, active: (path: string) => path === '/guid' || path.startsWith('/conversation/') },
  { label: 'Ramble', path: '/transcription', icon: rambleIcon, active: (path: string) => path.startsWith('/transcription') },
  { label: 'Projects', path: '/projects', icon: projectsIcon, active: (path: string) => /^(\/projects|\/work|\/activity|\/autonomy|\/scheduled|\/providers|\/diagnostics)(\/|$)/.test(path) },
  { label: 'Settings', path: '/settings', icon: settingsIcon, active: (path: string) => path.startsWith('/settings') || path === '/connections' || path === '/dogfood' },
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
      <img src={tab.icon} alt='' width={22} height={22} />
      <span>{tab.label}</span>
    </button>)}
  </nav>;
}
