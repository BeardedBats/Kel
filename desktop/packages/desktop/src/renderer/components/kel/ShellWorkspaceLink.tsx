import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Layers, Down } from '@icon-park/react';

export default function ShellWorkspaceLink() {
  const navigate = useNavigate();
  return <button type='button' className='kel-shell-workspace-link' onClick={() => navigate('/projects')}>
    <Layers size={16} aria-hidden='true' /><span>Workspace</span><Down size={12} aria-hidden='true' />
  </button>;
}
