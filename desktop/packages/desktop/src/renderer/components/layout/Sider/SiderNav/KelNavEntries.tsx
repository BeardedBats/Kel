/**
 * Kel navigation entries — the primary nav is only the places a user *does* something
 * (Work, Projects) plus the two review surfaces that unblock them (Permissions) and the optional
 * high-level Activity view (D14).
 * Configuration surfaces (Providers, Team, Diagnostics) live in Settings.
 * Rendered in the fixed nav slot above the scrollable history area. Real buttons, Kel labels,
 * active state from the route.
 */
import React from 'react';
import { Tooltip } from '@arco-design/web-react';
import { AllApplication, Folder, ListView, Lock, Voice } from '@icon-park/react';
import classNames from 'classnames';
import { useLocation, useNavigate } from 'react-router-dom';
import type { SiderTooltipProps } from '@renderer/utils/ui/siderTooltip';

const ENTRIES = [
  { id: 'work', path: '/work', label: 'Work', Icon: ListView },
  { id: 'projects', path: '/projects', label: 'Projects', Icon: Folder },
  { id: 'activity', path: '/activity', label: 'Activity', Icon: AllApplication },
  { id: 'autonomy', path: '/autonomy', label: 'Permissions', Icon: Lock },
  { id: 'transcription', path: '/transcription', label: 'Transcription', Icon: Voice },
] as const;

const KelNavEntries: React.FC<{
  collapsed: boolean;
  isMobile: boolean;
  siderTooltipProps: SiderTooltipProps;
}> = ({ collapsed, isMobile, siderTooltipProps }) => {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <>
      {ENTRIES.map(({ id, path, label, Icon }) => {
        const active = pathname === path;
        return (
          <Tooltip key={id} {...siderTooltipProps} content={label} position='right'>
            <button
              type='button'
              aria-label={label}
              aria-current={active ? 'page' : undefined}
              className={classNames(
                'box-border h-34px w-full flex items-center cursor-pointer rd-8px transition-colors text-t-primary bg-transparent border-none',
                collapsed ? 'justify-center' : 'justify-start gap-8px ps-10px pe-8px',
                isMobile && 'sider-action-btn-mobile',
                active ? 'bg-fill-3' : 'hover:bg-fill-3 active:bg-fill-4'
              )}
              onClick={() => navigate(path)}
            >
              <span className='size-22px flex items-center justify-center shrink-0 text-t-primary'>
                <Icon
                  theme='outline'
                  size='16'
                  fill='currentColor'
                  className='block leading-none'
                  style={{ lineHeight: 0 }}
                />
              </span>
              {!collapsed && <span className='text-t-primary text-14px font-[500] leading-24px'>{label}</span>}
            </button>
          </Tooltip>
        );
      })}
    </>
  );
};

export default KelNavEntries;
