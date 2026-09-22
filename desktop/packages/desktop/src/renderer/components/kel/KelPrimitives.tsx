/**
 * Kel design-system primitives (Direction "Desk").
 * Class names come from renderer/styles/kel-tokens.css — components never carry ad-hoc values.
 */
import React from 'react';
import ShellSourceCardHeader, { sourceCard } from './ShellSourceCardHeader';
import '@renderer/styles/kel-tokens.css';

export type KelStatus =
  | 'running'
  | 'waiting'
  | 'verified'
  | 'uncertain'
  | 'failed'
  | 'blocked'
  | 'queued';

const CHIP_CLASS: Record<KelStatus, string> = {
  running: 'kel-chip--run',
  waiting: 'kel-chip--wait',
  verified: 'kel-chip--ok',
  uncertain: 'kel-chip--uncertain',
  failed: 'kel-chip--failed',
  blocked: 'kel-chip--blocked',
  queued: '',
};

const CHIP_LABEL: Record<KelStatus, string> = {
  running: 'Running…',
  waiting: 'Waiting on you',
  verified: 'Verified',
  uncertain: 'Uncertain — needs evidence',
  failed: 'Failed — see cause',
  blocked: 'Blocked by guardrail',
  queued: 'Queued',
};

/** Engine state (derived server-side) mapped to a Kel status — never authored by the UI. */
export function statusFromDerived(state: string): KelStatus {
  switch (state) {
    case 'ACTIVE':
      return 'running';
    case 'WAITING':
      return 'waiting';
    case 'DONE':
      return 'verified';
    case 'UNCERTAIN':
      return 'uncertain';
    case 'FAILED':
      return 'failed';
    case 'BLOCKED':
      return 'blocked';
    default:
      return 'queued';
  }
}

export const KelStatusChip: React.FC<{ status: KelStatus }> = ({ status }) => (
  <span className={`kel-chip ${CHIP_CLASS[status]}`}>
    <span className="kel-chip__dot" aria-hidden="true" />
    {CHIP_LABEL[status]}
  </span>
);

export const KelButton: React.FC<
  React.PropsWithChildren<{
    variant?: 'primary' | 'secondary' | 'quiet';
    onClick?: () => void;
    disabled?: boolean;
    ariaLabel?: string;
  }>
> = ({ variant = 'secondary', onClick, disabled, ariaLabel, children }) => (
  <button
    type="button"
    className={`kel-btn kel-btn--${variant}`}
    onClick={onClick}
    disabled={disabled}
    aria-label={ariaLabel}
  >
    {children}
  </button>
);

export const KelTabs: React.FC<{
  tabs: Array<{ id: string; label: string }>;
  active: string;
  onSelect: (id: string) => void;
}> = ({ tabs, active, onSelect }) => (
  <div className="kel-tabs" role="tablist">
    {tabs.map((tab) => (
      <button
        key={tab.id}
        type="button"
        role="tab"
        aria-selected={tab.id === active}
        className={`kel-tab${tab.id === active ? ' kel-tab--on' : ''}`}
        onClick={() => onSelect(tab.id)}
      >
        {tab.label}
      </button>
    ))}
  </div>
);

export const KelCard: React.FC<
  React.PropsWithChildren<{ id?: string; title?: string; chip?: React.ReactNode; actions?: React.ReactNode; className?: string }>
> = ({ title, chip, actions, className, children, ...rest }) => (
  <section className={`kel-card${sourceCard(title) ? ' kel-card--source' : ''}${className ? ` ${className}` : ''}`} {...(rest as Record<string, unknown>)}>
    {sourceCard(title) ? <ShellSourceCardHeader title={title!} {...sourceCard(title)!} /> : (title || chip || actions) && (
      <div className="kel-row">
        {title && <h2 className="kel-h2">{title}</h2>}
        {chip}
        <span className="kel-grow" />
        {actions}
      </div>
    )}
    {children}
  </section>
);

export const KelSection: React.FC<React.PropsWithChildren<{ title: string }>> = ({ title, children }) => (
  <div className="kel-card">
    <h2 className="kel-h2">{title}</h2>
    <div className="kel-divider" />
    {children}
  </div>
);

export const KelMeter: React.FC<{ used: number; total: number }> = ({ used, total }) => {
  const pct = total > 0 ? Math.min(100, Math.round((used / total) * 100)) : 0;
  return (
    <span className="kel-row">
      <span className="kel-meter" aria-hidden="true">
        <i style={{ width: `${pct}%` }} />
      </span>
      <span className="kel-meta">
        {used} of {total} steps used
      </span>
    </span>
  );
};

export const KelEmpty: React.FC<{ title: string; why: string; actionLabel?: string; onAction?: () => void }> = ({
  title,
  why,
  actionLabel,
  onAction,
}) => (
  <div className="kel-empty">
    <strong>{title}</strong>
    <span className='kel-empty-description'>{why}</span>
    {actionLabel && onAction && (
      <div className="kel-row" style={{ marginTop: 12 }}>
        <KelButton variant="primary" onClick={onAction}>
          {actionLabel}
        </KelButton>
      </div>
    )}
  </div>
);

/** Static skeleton rows: no shimmer, final row rhythm, no reflow when data arrives. */
export const KelLoading: React.FC<{ rows?: number }> = ({ rows = 3 }) => (
  <div aria-busy="true" aria-live="polite">
    {Array.from({ length: rows }).map((_, index) => (
      <div className="kel-divider" key={index} />
    ))}
    <span className="kel-meta">Loading…</span>
  </div>
);

export const KelTable: React.FC<{
  head: string[];
  rows: React.ReactNode[][];
  caption?: string;
}> = ({ head, rows, caption }) => (
  <table className="kel-table">
    {caption && <caption className="kel-meta">{caption}</caption>}
    <thead>
      <tr>
        {head.map((cell) => (
          <th key={cell} scope="col">
            {cell}
          </th>
        ))}
      </tr>
    </thead>
    <tbody>
      {rows.map((row, index) => (
        <tr key={index}>
          {row.map((cell, cellIndex) => (
            <td key={cellIndex}>{cell}</td>
          ))}
        </tr>
      ))}
    </tbody>
  </table>
);

export function formatWhen(seconds: number | null | undefined): string {
  if (!seconds) return '—';
  const delta = Math.max(0, Math.round(Date.now() / 1000 - seconds));
  if (delta < 60) return `${delta}s ago`;
  if (delta < 3600) return `${Math.round(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.round(delta / 3600)}h ago`;
  return `${Math.round(delta / 86400)}d ago`;
}

/* Human-visual repair: expiry timestamps are in the FUTURE — formatWhen() clamps any future time to
   '0s ago' (the 'Expires: 0s ago' defect). This formats time-until instead. */
export function formatUntil(seconds: number | null | undefined): string {
  if (!seconds) return '—';
  const delta = Math.round(seconds - Date.now() / 1000);
  if (delta <= 0) return 'in <1m';
  if (delta < 60) return `in ${delta}s`;
  if (delta < 3600) return `in ${Math.round(delta / 60)}m`;
  if (delta < 86400) return `in ${Math.round(delta / 3600)}h`;
  return `in ${Math.round(delta / 86400)}d`;
}
