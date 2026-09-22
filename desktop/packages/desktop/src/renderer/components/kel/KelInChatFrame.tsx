import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ShellWorkspaceLink from './ShellWorkspaceLink';
import ShellSettingsIcon from './ShellSettingsIcon';
import { useExtensionSettingsTabs } from '@renderer/hooks/system/useExtensionSettingsTabs';
import { useExtI18n } from '@renderer/hooks/system/useExtI18n';
import { resolveExtensionAssetUrl } from '@renderer/utils/platform';
import workIcon from '@renderer/assets/figma/refresh/work.svg';
import activityIcon from '@renderer/assets/figma/refresh/activity.svg';
import permissionsIcon from '@renderer/assets/figma/refresh/permissions.svg';
import knowledgeIcon from '@renderer/assets/figma/refresh/knowledge.svg';
import scheduledIcon from '@renderer/assets/figma/refresh/scheduled.svg';
import providersIcon from '@renderer/assets/figma/refresh/providers.svg';
import diagnosticsIcon from '@renderer/assets/figma/refresh/diagnostics.svg';
import transcriptionIcon from '@renderer/assets/figma/refresh/transcriptions.svg';
import setupIcon from '@renderer/assets/figma/refresh/setup.svg';

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

const settingsGroups: Group[] = [
  { label: 'Kel', items: [
    { label: 'Model', path: '/settings/model', icon: 'model' },
    { label: 'Tools', path: '/settings/tools', icon: 'tools' },
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

const matches = (pathname: string, path: string) => pathname === path || pathname.startsWith(`${path}/`) || (path === '/projects/knowledge' && ['/projects', '/projects/map'].includes(pathname));

export default function KelInChatFrame({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const extensionTabs = useExtensionSettingsTabs();
  const { resolveExtTabName } = useExtI18n();
  const settings = pathname.startsWith('/settings') || pathname === '/connections';
  const heading = settings ? 'Settings' : pathname === '/onboarding' ? 'Workspaces' : pathname === '/transcription/library' ? 'Ramble' : pathname === '/projects/recipes' ? 'Recipes' : 'Projects';
  const groups = settings ? [...settingsGroups, ...(extensionTabs.length ? [{ label: 'Extensions', items: extensionTabs.map(tab => {
    const icon = resolveExtensionAssetUrl(tab.icon) || tab.icon;
    return { label: resolveExtTabName(tab), path: `/settings/ext/${tab.id}`, icon: icon || 'tools', sourceIcon: Boolean(icon) };
  }) }] : [])] : projectGroups;

  return <div className='kel-in-chat-frame' data-kind={settings ? 'settings' : 'projects'}>
    <header className='kel-in-chat-frame__header'>
      <ShellWorkspaceLink />
      <h1>{heading}</h1>
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
      <div className='kel-in-chat-frame__pane'>{children}</div>
    </div>
  </div>;
}
