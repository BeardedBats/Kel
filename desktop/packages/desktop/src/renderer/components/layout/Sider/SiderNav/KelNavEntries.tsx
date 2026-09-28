/**
 * Kel navigation entries — the primary nav is only the places a user *does* something (Projects)
 * plus the optional high-level Activity view (D14). D-70: the Work page is retired (the work cards
 * at the top of the chat replace it) and Permissions moved to Settings with the other configuration
 * surfaces (Providers, Diagnostics).
 * Rendered in the fixed nav slot above the scrollable history area. Real buttons, Kel labels,
 * active state from the route.
 */
import React from 'react';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import { Tooltip } from '@arco-design/web-react';
import { AllApplication, Folder } from '@icon-park/react';
import classNames from 'classnames';
import { useLocation, useNavigate } from 'react-router-dom';
import type { SiderTooltipProps } from '@renderer/utils/ui/siderTooltip';

const ENTRIES = [
  { id: 'projects', path: '/projects', label: 'Projects', Icon: Folder },
  { id: 'activity', path: '/activity', label: 'Activity', Icon: AllApplication },
] as const;

const KelNavEntries: React.FC<{
  collapsed: boolean;
  isMobile: boolean;
  siderTooltipProps: SiderTooltipProps;
}> = ({ collapsed, isMobile, siderTooltipProps }) => {
  const navigate = useNavigate();
  const layout = useLayoutContext();
  const { pathname } = useLocation();

  return (
    <>
      {ENTRIES.map(({ id, path, label, Icon }) => {
        const active = pathname === path || pathname.startsWith(path + '/');
        return (
          <Tooltip key={id} {...siderTooltipProps} content={label} position='right'>
            <button
              type='button'
              aria-label={label}
              aria-current={active ? 'page' : undefined}
              className={classNames(
                'kel-shell-primary-row box-border h-34px w-full flex items-center cursor-pointer rd-8px transition-colors text-t-primary bg-transparent border-none',
                collapsed ? 'justify-center' : 'justify-start gap-8px ps-10px pe-8px',
                isMobile && 'sider-action-btn-mobile',
                active ? 'bg-fill-3' : 'hover:bg-fill-3 active:bg-fill-4'
              )}
              onClick={() => { void navigate(path); if (isMobile) layout?.setSiderCollapsed(true); }}
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
