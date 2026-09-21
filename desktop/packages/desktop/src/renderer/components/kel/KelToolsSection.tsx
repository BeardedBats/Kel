import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLayoutContext } from '@renderer/hooks/context/LayoutContext';
import { ShellNavRow } from './ShellNavRow';
import mic from '@renderer/assets/figma/mic.svg';

/** Focused utilities share existing routes, permissions, and persisted state. */
export const KEL_TOOLS = [
  { id: 'ramble', label: 'Ramble', path: '/transcription' },
  { id: 'kibble', label: 'Kibble', path: '/dogfood' },
] as const;

export default function KelToolsSection({ collapsed = false }: { collapsed?: boolean }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const layout = useLayoutContext();
  return (
    <nav className='kel-shell-tools' aria-label='Tools'>
      {!collapsed && <h2 className='kel-shell-section-label'>Tools</h2>}
      {KEL_TOOLS.map(tool => (
        <ShellNavRow key={tool.id} label={tool.label} collapsed={collapsed}
          active={pathname === tool.path}
          icon={tool.id === 'ramble' ? <img src={mic} alt='' /> : <span className='kel-shell-status-dot' />}
          onClick={() => { void navigate(tool.path); if (layout?.isMobile) layout.setSiderCollapsed(true); }} />
      ))}
    </nav>
  );
}
