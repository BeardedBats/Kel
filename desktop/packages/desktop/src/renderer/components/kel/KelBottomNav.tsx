import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import kibbleIcon from '@renderer/assets/figma/refresh/kibble.svg';
import rambleIcon from '@renderer/assets/figma/refresh/ramble.svg';
import recipesIcon from '@renderer/assets/figma/refresh/recipes.svg';
import projectsIcon from '@renderer/assets/figma/refresh/projects.svg';
import workspacesIcon from '@renderer/assets/figma/refresh/workspaces.svg';
import settingsIcon from '@renderer/assets/figma/refresh/settings.svg';

const links = [
  { label: 'Kibble', path: '/dogfood', icon: kibbleIcon, active: (path: string) => path === '/dogfood' },
  { label: 'Ramble', path: '/transcription', icon: rambleIcon, active: (path: string) => path.startsWith('/transcription') },
  { label: 'Recipes', path: '/projects/recipes', icon: recipesIcon, active: (path: string) => path === '/projects/recipes' },
  { label: 'Projects', path: '/projects', icon: projectsIcon, active: (path: string) => /^(\/projects(?!\/recipes)|\/work|\/activity|\/autonomy|\/scheduled|\/providers|\/diagnostics)(\/|$)/.test(path) },
  { label: 'Workspaces', path: '/onboarding', icon: workspacesIcon, active: (path: string) => path === '/onboarding' },
  { label: 'Settings', path: '/settings/appearance', icon: settingsIcon, active: (path: string) => path.startsWith('/settings') || path === '/connections' },
] as const;

export default function KelBottomNav({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return <nav className='kel-bottom-nav' aria-label='Kel sections'>
    {links.map(link => <button
      key={link.label}
      type='button'
      className='kel-bottom-nav__item'
      data-section={link.label.toLowerCase()}
      aria-current={link.active(pathname) ? 'page' : undefined}
      onClick={() => { void navigate(link.path); onNavigate?.(); }}
    >
      <span className='kel-bottom-nav__icon'><img src={link.icon} alt='' width={15} height={15} /></span>
      <span className='kel-bottom-nav__label'>{link.label}</span>
    </button>)}
  </nav>;
}
