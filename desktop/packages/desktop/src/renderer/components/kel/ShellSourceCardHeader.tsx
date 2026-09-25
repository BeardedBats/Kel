import React from 'react';

// Audit 2 reads effective visibility, including all Figma ancestors.
// Hidden component defaults are not screen copy.
const TITLES = ['Available now', 'Default model', 'Custom models', 'Jobs', 'Waiting to continue', 'Team assignments', 'Active permissions', 'Access requests', 'Permission check', 'Knowledge', 'Project map', 'Recipes', 'Integrations', 'Readiness preflight', 'Credential metadata', 'Health', 'Measured performance', 'Maintenance', 'Kel', 'Archived', 'Kel runs on this machine', 'Connect a model', 'Where work happens', 'How much Kel does on its own', "You're set"];
const DESCRIPTIONS: Record<string, string> = {
  'Credential metadata': 'Values are never stored here.',
  'Kel runs on this machine': 'Nothing leaves your computer unless you connect a provider.',
  'Where work happens': 'Choose the folder Kel treats as your workspace.',
};
export function sourceCard(title?: string) {
  const key = title?.split(' · ')[0];
  return key && TITLES.includes(key) ? { description: DESCRIPTIONS[key] } : undefined;
}
export default function ShellSourceCardHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return <header className='kel-shell-source-card-head'>
    <h2 className='kel-h2'>{title}</h2>
    {description && <p className='kel-meta'>{description}</p>}
    {actions && <div className='kel-shell-source-card-actions'>{actions}</div>}
  </header>;
}
