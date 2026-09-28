import ShellSettingsIcon from '@renderer/components/kel/ShellSettingsIcon';
import classNames from 'classnames';
import React from 'react';
import { useLayoutContext } from '@/renderer/hooks/context/LayoutContext';
import {
  SettingsTabNavigateProvider,
  SettingsViewModeProvider,
} from '@/renderer/components/settings/SettingsModal/settingsViewContext';
import { isElectronDesktop } from '@/renderer/utils/platform';
import {
  Communication,
  Computer,
  Earth,
  Inbox,
  Info,
  LinkCloud,
  Puzzle,
  System,
  Toolkit,
} from '@icon-park/react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import './settings.css';

/**
 * Settings tab ids in display order (must match router paths). D-60: only what Kel has built —
 * no assistant catalog and no extension tabs.
 */
export const BUILTIN_TAB_IDS = ['model', 'tools', 'skills', 'appearance', 'webui', 'system', 'archived', 'about'] as const;

interface SettingsPageWrapperProps {
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
}

type NavItem = { label: string; icon: React.ReactElement; path: string; id: string };

type TranslateFn = (key: string, options?: { defaultValue?: string }) => string;

export function getBuiltinSettingsNavItems(isDesktop: boolean, t: TranslateFn): NavItem[] {
  const builtinMap: Record<(typeof BUILTIN_TAB_IDS)[number], NavItem> = {
    model: { id: 'model', label: t('settings.model'), icon: <LinkCloud theme='outline' size='16' />, path: 'model' },
    tools: {
      id: 'tools',
      label: t('settings.tools', { defaultValue: 'Tools' }),
      icon: <Toolkit theme='outline' size='16' />,
      path: 'tools',
    },
    skills: {
      id: 'skills',
      label: t('settings.skills', { defaultValue: 'Skills' }),
      icon: <Puzzle theme='outline' size='16' />,
      path: 'skills',
    },
    appearance: {
      id: 'appearance',
      label: t('settings.appearancePanel'),
      icon: <Computer theme='outline' size='16' />,
      path: 'appearance',
    },
    webui: {
      id: 'webui',
      label: t('settings.webui'),
      icon: isDesktop ? <Earth theme='outline' size='16' /> : <Communication theme='outline' size='16' />,
      path: 'webui',
    },
    system: { id: 'system', label: t('settings.system'), icon: <System theme='outline' size='16' />, path: 'system' },
    archived: {
      id: 'archived',
      label: t('settings.archived.navLabel'),
      icon: <Inbox theme='outline' size='16' />,
      path: 'archived',
    },
    about: { id: 'about', label: t('settings.about'), icon: <Info theme='outline' size='16' />, path: 'about' },
  };

  return BUILTIN_TAB_IDS.map((id) => ({ ...builtinMap[id], icon: <ShellSettingsIcon name={id} /> }));
}

const SettingsPageWrapper: React.FC<SettingsPageWrapperProps> = ({ children, className, contentClassName }) => {
  const layout = useLayoutContext();
  const isMobile = layout?.isMobile ?? false;
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const isDesktop = isElectronDesktop();

  const menuItems = React.useMemo(() => getBuiltinSettingsNavItems(isDesktop, t), [isDesktop, t]);

  // Keep only horizontal padding on the scroll container — vertical padding is
  // moved to the content layer below. A sticky header inside a scroll container
  // with top padding would otherwise stick 32px down, letting content peek
  // through the gap above it.
  const containerClass = classNames(
    'settings-page-wrapper w-full min-h-full box-border overflow-y-auto',
    isMobile ? 'px-16px' : 'px-12px md:px-40px',
    className
  );

  const contentClass = classNames(
    'settings-page-content mx-auto w-full md:max-w-1024px py-14px md:py-32px',
    contentClassName
  );

  const navigateToTab = React.useCallback(
    (tabId: string) => {
      void navigate(`/settings/${tabId}`, { replace: true });
    },
    [navigate]
  );

  return (
    <SettingsViewModeProvider value='page'>
      <SettingsTabNavigateProvider value={navigateToTab}>
        <div className={containerClass}>
          {isMobile && (
            <div className='settings-mobile-top-nav'>
              {menuItems.map((item) => {
                const active = pathname.includes(`/settings/${item.path}`);
                return (
                  <button
                    key={item.path}
                    type='button'
                    className={classNames('settings-mobile-top-nav__item', {
                      'settings-mobile-top-nav__item--active': active,
                    })}
                    onClick={() => {
                      void navigate(`/settings/${item.path}`, { replace: true });
                    }}
                  >
                    <span className='settings-mobile-top-nav__icon'>{item.icon}</span>
                    <span className='settings-mobile-top-nav__label'>{item.label}</span>
                  </button>
                );
              })}
            </div>
          )}
          <div className={contentClass}>
            <header className='kel-shell-settings-header'>
              <p>{pathname.endsWith('/model') || pathname.endsWith('/staff') ? 'Model' : pathname.endsWith('/about') ? 'Other' : /\/(model|tools|webui)$/.test(pathname) ? 'Settings' : pathname.endsWith('/archived') ? 'History' : 'Application'}</p>
              <h1>{pathname.endsWith('/model') ? 'Model' : pathname.endsWith('/staff') ? 'Staff & models' : pathname.endsWith('/skills') ? 'Skills' : pathname.endsWith('/webui') ? 'WebUI' : pathname.endsWith('/archived') ? <><span className='kel-desktop-only'>Archived</span><span className='kel-phone-only'>Archived conversations</span></> : menuItems.find((item) => pathname.includes(`/settings/${item.path}`))?.label ?? 'Settings'}</h1>
            </header>
            {pathname.endsWith('/model') && <p className='kel-shell-model-description'>Kel uses this model for normal conversations. A chat can still pick its own model from the chat header, and Automatic keeps Kel's routing across every available provider.</p>}
            {children}
          </div>
        </div>
      </SettingsTabNavigateProvider>
    </SettingsViewModeProvider>
  );
};

export default SettingsPageWrapper;
