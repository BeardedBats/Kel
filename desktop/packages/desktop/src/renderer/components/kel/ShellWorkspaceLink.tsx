import React from 'react';
import { useNavigate } from 'react-router-dom';
import workspaceIcon from '@renderer/assets/figma/chat-shell/workspace.svg';
import chevronIcon from '@renderer/assets/figma/chat-shell/workspace-chevron.svg';

export default function ShellWorkspaceLink() {
  const navigate = useNavigate();
  return <button type='button' className='kel-shell-workspace-link' onClick={() => navigate('/projects')}>
    <img src={workspaceIcon} alt='' /><span>Workspace</span><img src={chevronIcon} alt='' />
  </button>;
}
