import React from 'react';
import { KelCard, KelLoading } from './KelPrimitives';
import ShellWorkspaceLink from './ShellWorkspaceLink';
import './kel-desktop-pending-states.css';

export const KelSkeletonRows: React.FC<{ rows: number }> = ({ rows }) => <div className='kel-skeleton-rows' aria-hidden='true'>
  {Array.from({ length: rows }, (_, index) => <div key={index} className='kel-skeleton-row'><i /><span /><span /></div>)}
</div>;

export const KelActivityLoading: React.FC = () => <>
  <div className='kel-page kel-shell-activity kel-activity-loading-desktop' aria-busy='true' role='status' aria-label='Loading activity'>
    <div className='kel-page__head'><div><ShellWorkspaceLink /><h1 className='kel-h1'>Activity</h1></div></div>
    <KelCard title='Happening now'><KelSkeletonRows rows={2} /></KelCard>
    <KelCard title='Waiting on you'><KelSkeletonRows rows={2} /></KelCard>
    <KelCard title='Recently finished'><KelSkeletonRows rows={3} /></KelCard>
  </div>
  <div className='kel-activity-loading-mobile'><KelLoading /></div>
</>;
