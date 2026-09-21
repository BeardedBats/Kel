import React from 'react';

/** Figma 143:87 Nav row v2. The caller owns routing and state. */
export const ShellNavRow: React.FC<{
  label: string;
  active?: boolean;
  collapsed?: boolean;
  icon?: React.ReactNode;
  onClick: () => void;
}> = ({ label, active, collapsed, icon, onClick }) => (
  <button type='button' className='kel-shell-nav-row' aria-label={label}
    aria-current={active ? 'page' : undefined} onClick={onClick}>
    {icon && <span className='kel-shell-nav-icon' aria-hidden='true'>{icon}</span>}
    {!collapsed && <span className='kel-shell-nav-label'>{label}</span>}
  </button>
);
