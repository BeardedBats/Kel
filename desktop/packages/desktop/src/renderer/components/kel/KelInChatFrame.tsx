import React, { useEffect, useState } from 'react';
import { activeProjectLabel, useProjects } from './activeProject';
import { useLocation, useNavigate } from 'react-router-dom';
import ShellWorkspaceLink from './ShellWorkspaceLink';
import ShellSettingsIcon from './ShellSettingsIcon';
import { configService } from '@/common/config/configService';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import activityIcon from '@renderer/assets/figma/refresh/activity.svg';
import permissionsIcon from '@renderer/assets/figma/refresh/permissions.svg';
import knowledgeIcon from '@renderer/assets/figma/refresh/knowledge.svg';
import scheduledIcon from '@renderer/assets/figma/refresh/scheduled.svg';
import providersIcon from '@renderer/assets/figma/refresh/providers.svg';
import diagnosticsIcon from '@renderer/assets/figma/refresh/diagnostics.svg';
import transcriptionIcon from '@renderer/assets/figma/refresh/transcriptions.svg';
import setupIcon from '@renderer/assets/figma/refresh/setup.svg';
import projectsIcon from '@renderer/assets/figma/refresh/projects.svg';
import mobileMenuIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconMenu.svg';
import mobileActivityIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconActivity.svg';
import mobilePermissionsIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconLock.svg';
import mobileKnowledgeIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconFolder1.svg';
import mobileScheduledIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconClock.svg';
import mobileProvidersIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconFile.svg';
import mobileDiagnosticsIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconSparkle.svg';
import mobileChevronIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconChevronDown.svg';
import mobileProjectBackIcon from '@renderer/assets/figma/refresh/mobile-project-back.svg';

type Item = { label: string; path: string; icon: string; sourceIcon?: boolean };
type Group = { label: string; items: Item[] };

// D-70 item 5: Projects keeps what belongs to a project — its chats and folder (All projects),
// Knowledge, Scheduled tasks and Activity. The Work page is retired (the work cards replace it),
// Recipes has one entry (the sidebar), and Permissions, Providers and Diagnostics moved to Settings.
const projectGroups: Group[] = [
  { label: 'Projects', items: [
    { label: 'All projects', path: '/projects/list', icon: projectsIcon, sourceIcon: true },
    { label: 'Activity', path: '/activity', icon: activityIcon, sourceIcon: true },
    { label: 'Knowledge', path: '/projects/knowledge', icon: knowledgeIcon, sourceIcon: true },
    { label: 'Scheduled tasks', path: '/scheduled', icon: scheduledIcon, sourceIcon: true },
  ] },
  // ST-20: no second Ramble library here — Transcriptions open Ramble itself.
];
const mobileProjectItems: Item[] = [
  { label: 'All projects', path: '/projects/list', icon: mobileKnowledgeIcon, sourceIcon: true },
  { label: 'Activity', path: '/activity', icon: mobileActivityIcon, sourceIcon: true },
  { label: 'Knowledge', path: '/projects/knowledge', icon: mobileKnowledgeIcon, sourceIcon: true },
  { label: 'Scheduled tasks', path: '/scheduled', icon: mobileScheduledIcon, sourceIcon: true },
];

const settingsGroups: Group[] = [
  { label: 'Kel', items: [
    { label: 'Model', path: '/settings/model', icon: 'model' },
    { label: 'Staff & models', path: '/settings/staff', icon: 'assistants' },
    { label: 'Permissions', path: '/settings/permissions', icon: permissionsIcon, sourceIcon: true },
    { label: 'Providers', path: '/settings/providers', icon: providersIcon, sourceIcon: true },
    { label: 'Tools', path: '/settings/tools', icon: 'tools' },
    { label: 'Skills', path: '/settings/skills', icon: 'skills' },
    { label: 'Connections', path: '/connections', icon: 'connections' },
    { label: 'Set up Kel', path: '/onboarding', icon: setupIcon, sourceIcon: true },
  ] },
  { label: 'Application', items: [
    { label: 'Appearance', path: '/settings/appearance', icon: 'appearance' },
    { label: 'System', path: '/settings/system', icon: 'system' },
    { label: 'Diagnostics', path: '/settings/diagnostics', icon: diagnosticsIcon, sourceIcon: true },
    { label: 'Remote / WebUI', path: '/settings/webui', icon: 'webui' },
  ] },
  { label: 'Data', items: [
    { label: 'Archived', path: '/settings/archived', icon: 'archived' },
    { label: 'Ramble', path: '/transcription', icon: transcriptionIcon, sourceIcon: true },
  ] },
  { label: 'Other', items: [{ label: 'About', path: '/settings/about', icon: 'about' }] },
];
const mobileSettingsGroups: Group[] = [
  { label: 'Kel', items: settingsGroups[0].items.map((item) =>
    item.path === '/settings/permissions' ? { ...item, icon: mobilePermissionsIcon }
      : item.path === '/settings/providers' ? { ...item, icon: mobileProvidersIcon } : item) },
  { label: 'Application', items: [
    ...settingsGroups[1].items.map((item) => item.path === '/settings/diagnostics' ? { ...item, icon: mobileDiagnosticsIcon } : item),
    { label: 'Ramble', path: '/transcription', icon: transcriptionIcon, sourceIcon: true },
  ] },
  { label: 'Data', items: [settingsGroups[2].items[0]] },
  settingsGroups[3],
];

const matches = (pathname: string, path: string) => pathname === path || pathname.startsWith(`${path}/`) || (path === '/projects/knowledge' && ['/projects', '/projects/map'].includes(pathname));

export default function KelInChatFrame({ children }: { children: React.ReactNode }) {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const layout = useLayoutContext();
  // D-54: Set up Kel lives with the Settings pages (JR-14).
  const settings = pathname.startsWith('/settings') || pathname === '/connections' || pathname === '/onboarding';
  const mobileIndex = pathname === '/settings' || pathname === '/projects';
  const [setupOpen, setSetupOpen] = useState(false);
  // The phone index names the active project (the engine's, not a guess).
  const projectName = activeProjectLabel(useProjects()) || 'Projects';
  useEffect(() => {
    let cancelled = false;
    void configService.initialize().then(() => {
      if (!cancelled) setSetupOpen(!Boolean(configService.get('kel.onboardingCompleted_v1')));
    }).catch(() => {
      if (!cancelled) setSetupOpen(true);
    });
    return () => { cancelled = true; };
  }, [pathname]);
  const heading = pathname === '/onboarding' ? 'Set up Kel' : settings ? 'Settings' : pathname === '/transcription/library' ? 'Ramble' : pathname === '/projects/recipes' ? 'Recipes' : 'Projects';
  const mobileProjectGroups: Group[] = [
    { label: projectName, items: mobileProjectItems },
  ];
  const activeItem = [...settingsGroups, ...mobileProjectGroups].flatMap(group => group.items).find(item => matches(pathname, item.path));
  const selectedMcpName = pathname === '/settings/tools' && new URLSearchParams(search).has('mcp')
    ? new URLSearchParams(search).get('name')
    : null;
  const mobileTitle = selectedMcpName || (mobileIndex ? heading : pathname === '/onboarding' ? 'Set up Kel' : pathname === '/connections' ? 'Connections' : pathname === '/projects/map' ? 'Project map' : pathname === '/settings/skills' ? 'Skills' : pathname === '/settings/webui' ? 'WebUI' : activeItem?.label || heading);
  // D-60: Settings list only what Kel has built — no assistant catalog and no extension tabs.
  const groups = settings ? settingsGroups : projectGroups;

  return <div className='kel-in-chat-frame' data-kind={settings ? 'settings' : 'projects'} data-mobile-index={mobileIndex}>
    <header className='kel-in-chat-frame__header'>
      <ShellWorkspaceLink />
      <h1>{heading}</h1>
    </header>
    <header className='kel-in-chat-frame__mobile-header'>
      <button type='button' aria-label={selectedMcpName ? 'Back to Tools' : mobileIndex ? 'Open chats' : `Back to ${heading}`} onClick={() => selectedMcpName ? void navigate('/settings/tools') : mobileIndex ? layout?.setSiderCollapsed(false) : void navigate(settings ? '/settings' : '/projects')}>
        {mobileIndex && !settings ? <img src={mobileMenuIcon} alt='' width={22} height={22} /> : mobileIndex ? <span aria-hidden='true'>☰</span> : !settings ? <img src={mobileProjectBackIcon} alt='' width={20} height={20} /> : <span aria-hidden='true'>←</span>}
      </button>
      <h1>{mobileTitle}</h1>
    </header>
    <div className='kel-in-chat-frame__card'>
      <nav className='kel-in-chat-frame__nav' aria-label={`${heading} pages`}>
        {groups.map(group => <div className='kel-in-chat-frame__nav-group' key={group.label}>
          <div className='kel-in-chat-frame__nav-label'>{group.label}</div>
          {group.items.map(item => <button
            key={`${group.label}-${item.label}`}
            type='button'
            className='kel-in-chat-frame__nav-row'
            aria-current={matches(pathname, item.path) ? 'page' : undefined}
            onClick={() => void navigate(item.path)}
          >
            <span className='kel-in-chat-frame__nav-icon'>
              {item.sourceIcon ? <img src={item.icon} alt='' width={14} height={14} /> : <ShellSettingsIcon name={item.icon} />}
            </span>
            <span>{item.label}</span>
          </button>)}
        </div>)}
      </nav>
      {mobileIndex && <nav className='kel-in-chat-frame__mobile-index' aria-label={`${heading} pages`}>
        {(settings ? mobileSettingsGroups : mobileProjectGroups).map(group => <section key={group.label}>
          <h2>{group.label}</h2>
          <div className='kel-in-chat-frame__mobile-index-card'>
            {group.items.map(item => <button key={item.path} type='button' onClick={() => void navigate(item.path)}>
              <span className='kel-in-chat-frame__nav-icon'>{item.sourceIcon ? <img src={item.icon} alt='' width={16} height={16} /> : <ShellSettingsIcon name={item.icon} />}</span>
              <span>{item.label}</span>{settings ? <svg aria-hidden='true' width='14' height='14' viewBox='0 0 14 14' fill='none' stroke='currentColor' strokeWidth='1.3'><path d='m5 3.5 3.5 3.5L5 10.5' /></svg> : <img className='kel-in-chat-frame__mobile-chevron' src={mobileChevronIcon} alt='' width={16} height={16} />}
            </button>)}
          </div>
        </section>)}
      </nav>}
      <div className='kel-in-chat-frame__pane'>
        {setupOpen && pathname !== '/onboarding' && <div className='kel-setup-return' role='status'>
          <span>{layout?.isMobile ? 'Setup is still open. Finish setup before starting a chat.' : <><span className='kel-setup-return-icon' aria-hidden='true'>⚠</span>Setup is still open. Finish it before starting a chat.</>}</span>
          <button type='button' onClick={() => void navigate('/onboarding')}>Continue setup</button>
        </div>}
        {children}
      </div>
    </div>
  </div>;
}
