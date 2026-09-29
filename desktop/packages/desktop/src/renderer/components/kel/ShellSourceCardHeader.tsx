import React from 'react';

// Audit 2 reads effective visibility, including all Figma ancestors.
// Hidden component defaults are not screen copy.
const TITLES = ['Available now', 'Default model', 'Staff','Custom models', 'Jobs', 'Waiting to continue', 'Team assignments', 'Active permissions', 'Access requests', 'Permission check', 'Safety rules', 'Knowledge', 'Project map', 'Recipes', 'Integrations', 'Readiness preflight', 'Credential metadata', 'Health', 'Measured performance', 'Maintenance', 'Kel', 'Archived', 'Kel runs on this machine', 'Connect a model', 'Where work happens', 'How much Kel does on its own', "You're set"];
// D-87: these cards carry no descriptive subtitle; the title and the content say it.
export function sourceCard(title?: string): { description?: string } | undefined {
  const key = title?.split(' · ')[0];
  return key && TITLES.includes(key) ? {} : undefined;
}
export default function ShellSourceCardHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return <header className='kel-shell-source-card-head'>
    <h2 className='kel-h2'>{title}</h2>
    {description && <p className='kel-meta'>{description}</p>}
    {actions && <div className='kel-shell-source-card-actions'>{actions}</div>}
  </header>;
}
