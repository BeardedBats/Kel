import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ShellWorkspaceLink from './ShellWorkspaceLink';
import ShellSettingsIcon from './ShellSettingsIcon';
import { useExtensionSettingsTabs } from '@renderer/hooks/system/useExtensionSettingsTabs';
import { useExtI18n } from '@renderer/hooks/system/useExtI18n';
import { resolveExtensionAssetUrl } from '@renderer/utils/platform';
import { configService } from '@/common/config/configService';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import { kelState } from './kelApi';
import workIcon from '@renderer/assets/figma/refresh/work.svg';
import activityIcon from '@renderer/assets/figma/refresh/activity.svg';
import permissionsIcon from '@renderer/assets/figma/refresh/permissions.svg';
import knowledgeIcon from '@renderer/assets/figma/refresh/knowledge.svg';
import scheduledIcon from '@renderer/assets/figma/refresh/scheduled.svg';
import providersIcon from '@renderer/assets/figma/refresh/providers.svg';
import diagnosticsIcon from '@renderer/assets/figma/refresh/diagnostics.svg';
import transcriptionIcon from '@renderer/assets/figma/refresh/transcriptions.svg';
import setupIcon from '@renderer/assets/figma/refresh/setup.svg';
import recipesIcon from '@renderer/assets/figma/refresh/recipes.svg';
import workspacesIcon from '@renderer/assets/figma/refresh/workspaces.svg';
import mobileMenuIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconMenu.svg';
import mobileWorkIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconProjects.svg';
import mobileActivityIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconActivity.svg';
import mobilePermissionsIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconLock.svg';
import mobileKnowledgeIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconFolder1.svg';
import mobileRecipesIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconStar.svg';
import mobileScheduledIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconClock.svg';
import mobileProvidersIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconFile.svg';
import mobileDiagnosticsIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconSparkle.svg';
import mobileChevronIcon from '@renderer/assets/figma/refresh/mobile-project-imgIconChevronDown.svg';
import mobileProjectBackIcon from '@renderer/assets/figma/refresh/mobile-project-back.svg';

type Item = { label: string; path: string; icon: string; sourceIcon?: boolean };
type Group = { label: string; items: Item[] };

const projectGroups: Group[] = [
  { label: 'Projects', items: [
    { label: 'Work', path: '/work', icon: workIcon, sourceIcon: true },
    { label: 'Activity', path: '/activity', icon: activityIcon, sourceIcon: true },
    { label: 'Permissions', path: '/autonomy', icon: permissionsIcon, sourceIcon: true },
    { label: 'Knowledge', path: '/projects/knowledge', icon: knowledgeIcon, sourceIcon: true },
    { label: 'Scheduled tasks', path: '/scheduled', icon: scheduledIcon, sourceIcon: true },
    { label: 'Providers', path: '/providers', icon: providersIcon, sourceIcon: true },
    { label: 'Diagnostics', path: '/diagnostics', icon: diagnosticsIcon, sourceIcon: true },
  ] },
  { label: 'Ramble', items: [{ label: 'Transcriptions', path: '/transcription/library', icon: transcriptionIcon, sourceIcon: true }] },
  { label: 'Workspaces', items: [{ label: 'Set up Kel', path: '/onboarding', icon: setupIcon, sourceIcon: true }] },
];
const mobileProjectItems: Item[] = [
  { label: 'Work', path: '/work', icon: mobileWorkIcon, sourceIcon: true },
  { label: 'Activity', path: '/activity', icon: mobileActivityIcon, sourceIcon: true },
  { label: 'Permissions', path: '/autonomy', icon: mobilePermissionsIcon, sourceIcon: true },
  { label: 'Knowledge', path: '/projects/knowledge', icon: mobileKnowledgeIcon, sourceIcon: true },
  { label: 'Recipes', path: '/projects/recipes', icon: mobileRecipesIcon, sourceIcon: true },
  { label: 'Scheduled tasks', path: '/scheduled', icon: mobileScheduledIcon, sourceIcon: true },
];
const mobileKelItems: Item[] = [
  { label: 'Providers', path: '/providers', icon: mobileProvidersIcon, sourceIcon: true },
  { label: 'Diagnostics', path: '/diagnostics', icon: mobileDiagnosticsIcon, sourceIcon: true },
  { label: 'Workspaces', path: '/onboarding', icon: mobileWorkIcon, sourceIcon: true },
];

const settingsGroups: Group[] = [
  { label: 'Kel', items: [
    { label: 'Model', path: '/settings/model', icon: 'model' },
    { label: 'Assistants', path: '/settings/assistants', icon: 'assistants' },
    { label: 'Tools', path: '/settings/tools', icon: 'tools' },
    { label: 'Skills', path: '/settings/skills', icon: 'skills' },
  ] },
  { label: 'Application', items: [
    { label: 'Appearance', path: '/settings/appearance', icon: 'appearance' },
    { label: 'System', path: '/settings/system', icon: 'system' },
    { label: 'Desktop Pet', path: '/settings/pet', icon: 'pet' },
    { label: 'Remote / WebUI', path: '/settings/webui', icon: 'webui' },
  ] },
  { label: 'Data', items: [
    { label: 'Archived', path: '/settings/archived', icon: 'archived' },
    { label: 'Transcriptions', path: '/transcription/library', icon: transcriptionIcon, sourceIcon: true },
  ] },
  { label: 'Other', items: [{ label: 'About', path: '/settings/about', icon: 'about' }] },
];
const mobileSettingsGroups: Group[] = [
  settingsGroups[0],
  { label: 'Application', items: [
    ...settingsGroups[1].items,
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
  const extensionTabs = useExtensionSettingsTabs();
  const { resolveExtTabName } = useExtI18n();
  const settings = pathname.startsWith('/settings') || pathname === '/connections';
  const mobileIndex = pathname === '/settings' || pathname === '/projects';
  const [setupOpen, setSetupOpen] = useState(false);
  const [projectName, setProjectName] = useState('Projects');
  useEffect(() => {
    if (pathname !== '/projects') return;
    let cancelled = false;
    void kelState('main').then(state => {
      const named = state.projects.filter(item => item.id !== 'default');
      const project = named.length === 1 ? named[0] : state.projects.length === 1 ? state.projects[0] : null;
      if (!cancelled) setProjectName(project?.name || 'Projects');
    }).catch(() => {
      if (!cancelled) setProjectName('Projects');
    });
    return () => { cancelled = true; };
  }, [pathname]);
  useEffect(() => {
    let cancelled = false;
    void configService.initialize().then(() => {
      if (!cancelled) setSetupOpen(!Boolean(configService.get('kel.onboardingCompleted_v1')));
    }).catch(() => {
      if (!cancelled) setSetupOpen(true);
    });
    return () => { cancelled = true; };
  }, [pathname]);
  const heading = settings ? 'Settings' : pathname === '/onboarding' ? 'Workspaces' : pathname === '/transcription/library' ? 'Ramble' : pathname === '/projects/recipes' ? 'Recipes' : 'Projects';
  const mobileProjectGroups: Group[] = [
    { label: projectName, items: mobileProjectItems },
    { label: 'Kel', items: mobileKelItems },
  ];
  const activeItem = [...settingsGroups, ...mobileProjectGroups].flatMap(group => group.items).find(item => matches(pathname, item.path));
  const selectedMcpName = pathname === '/settings/tools' && new URLSearchParams(search).has('mcp')
    ? new URLSearchParams(search).get('name')
    : null;
  const mobileTitle = selectedMcpName || (mobileIndex ? heading : pathname === '/onboarding' ? 'Set up Kel' : pathname === '/connections' ? 'Connections' : pathname === '/projects/map' ? 'Project map' : pathname === '/settings/skills' ? 'Skills Hub' : pathname === '/settings/webui' ? 'WebUI' : activeItem?.label || heading);
  const groups = settings ? [...settingsGroups, ...(extensionTabs.length ? [{ label: 'Extensions', items: extensionTabs.map(tab => {
    const icon = resolveExtensionAssetUrl(tab.icon) || tab.icon;
    return { label: resolveExtTabName(tab), path: `/settings/ext/${tab.id}`, icon: icon || 'tools', sourceIcon: Boolean(icon) };
  }) }] : [])] : projectGroups;

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
          <span>Setup is still open. Finish setup before starting a chat.</span>
          <button type='button' onClick={() => void navigate('/onboarding')}>Continue setup</button>
        </div>}
        {children}
      </div>
    </div>
  </div>;
}
